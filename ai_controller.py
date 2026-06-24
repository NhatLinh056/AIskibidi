# pyrefly: ignore [missing-import]
import cv2
# pyrefly: ignore [missing-import]
import mediapipe as mp
import math
import socket
import json
import threading
import joblib
# pyrefly: ignore [missing-import]
import numpy as np

from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# Cài đặt kích thước màn hình và deadzone
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720
DEADZONE_RADIUS = 100

# Điểm trung tâm của khung hình
CENTER_X = FRAME_WIDTH // 2
CENTER_Y = FRAME_HEIGHT // 2

# Thiết lập UDP Socket để gửi dữ liệu siêu tốc
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
TARGET_ADDR = ("127.0.0.1", 5005)

#  CAMERA MODE - Mỗi game gửi lệnh đổi mode qua port 5006

current_mode = "default"

def mode_listener():
    global current_mode
    mode_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    mode_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        mode_sock.bind(("127.0.0.1", 5006))
    except OSError:
        return
    mode_sock.setblocking(False)
    while True:
        try:
            data, _ = mode_sock.recvfrom(256)
            msg = data.decode('utf-8').strip()
            if msg in ("pacman", "spooky", "tank", "default"):
                current_mode = msg
        except BlockingIOError:
            pass
        except Exception:
            pass
        import time
        time.sleep(0.05)

mode_thread = threading.Thread(target=mode_listener, daemon=True)
mode_thread.start()


def is_fist(hand_landmarks):
    wrist = hand_landmarks[0]
    wx, wy, wz = wrist.x * FRAME_WIDTH, wrist.y * FRAME_HEIGHT, wrist.z * FRAME_WIDTH
    
    fingers_folded = 0
    tips = [8, 12, 16, 20]
    pips = [6, 10, 14, 18]
    
    for tip, pip in zip(tips, pips):
        tip_lm = hand_landmarks[tip]
        pip_lm = hand_landmarks[pip]
        
        tx, ty, tz = tip_lm.x * FRAME_WIDTH, tip_lm.y * FRAME_HEIGHT, tip_lm.z * FRAME_WIDTH
        px, py, pz = pip_lm.x * FRAME_WIDTH, pip_lm.y * FRAME_HEIGHT, pip_lm.z * FRAME_WIDTH
        
        dist_tip = (tx - wx)**2 + (ty - wy)**2 + (tz - wz)**2
        dist_pip = (px - wx)**2 + (py - wy)**2 + (pz - wz)**2
        
        if dist_tip < dist_pip:
            fingers_folded += 1
            
    return fingers_folded >= 3

def is_pointing(hand_landmarks):
    wrist = hand_landmarks[0]
    wx, wy, wz = wrist.x * FRAME_WIDTH, wrist.y * FRAME_HEIGHT, wrist.z * FRAME_WIDTH
    
    tips = [8, 12, 16, 20]
    pips = [6, 10, 14, 18]
    
    folded = []
    for tip, pip in zip(tips, pips):
        tip_lm = hand_landmarks[tip]
        pip_lm = hand_landmarks[pip]
        
        tx, ty, tz = tip_lm.x * FRAME_WIDTH, tip_lm.y * FRAME_HEIGHT, tip_lm.z * FRAME_WIDTH
        px, py, pz = pip_lm.x * FRAME_WIDTH, pip_lm.y * FRAME_HEIGHT, pip_lm.z * FRAME_WIDTH
        
        dist_tip = (tx - wx)**2 + (ty - wy)**2 + (tz - wz)**2
        dist_pip = (px - wx)**2 + (py - wy)**2 + (pz - wz)**2
        
        folded.append(dist_tip < dist_pip)
        
    # Index NOT folded, Middle, Ring, Pinky ARE folded
    return (not folded[0]) and folded[1] and folded[2] and folded[3]

def send_data(direction, action, hand_y=-1.0, gesture="NONE"):
    payload = {"dir": direction, "action": action, "hand_y": round(hand_y, 3), "gesture": gesture}
    sock.sendto(json.dumps(payload).encode('utf-8'), TARGET_ADDR)

#  OVERLAY DRAWING - Tùy theo mode

def draw_overlay_pacman(image):
    """Mode Pacman: 4 vùng hướng (UP/DOWN/LEFT/RIGHT) + deadzone giữa"""
    overlay = image.copy()
    
    # 4 tam giác hướng
    
    # Trên - UP (xanh lá)
    pts_up = np.array([(0, 0), (FRAME_WIDTH, 0), (CENTER_X, CENTER_Y)])
    cv2.drawContours(overlay, [pts_up], 0, (0, 200, 100), -1)
    
    # Dưới - DOWN (cam)
    pts_down = np.array([(0, FRAME_HEIGHT), (FRAME_WIDTH, FRAME_HEIGHT), (CENTER_X, CENTER_Y)])
    cv2.drawContours(overlay, [pts_down], 0, (0, 140, 230), -1)
    
    # Trái - LEFT (vàng)
    pts_left = np.array([(0, 0), (0, FRAME_HEIGHT), (CENTER_X, CENTER_Y)])
    cv2.drawContours(overlay, [pts_left], 0, (0, 230, 230), -1)
    
    # Phải - RIGHT (vàng)
    pts_right = np.array([(FRAME_WIDTH, 0), (FRAME_WIDTH, FRAME_HEIGHT), (CENTER_X, CENTER_Y)])
    cv2.drawContours(overlay, [pts_right], 0, (0, 230, 230), -1)
    
    # Blend mờ
    cv2.addWeighted(overlay, 0.15, image, 0.85, 0, image)
    
    # Deadzone circle
    cv2.circle(image, (CENTER_X, CENTER_Y), DEADZONE_RADIUS, (0, 255, 255), 2)
    
    # Đường chia
    shrink = int(DEADZONE_RADIUS * 0.7)
    cv2.line(image, (0, 0), (CENTER_X - shrink, CENTER_Y - shrink), (200, 200, 200), 1)
    cv2.line(image, (FRAME_WIDTH, 0), (CENTER_X + shrink, CENTER_Y - shrink), (200, 200, 200), 1)
    cv2.line(image, (0, FRAME_HEIGHT), (CENTER_X - shrink, CENTER_Y + shrink), (200, 200, 200), 1)
    cv2.line(image, (FRAME_WIDTH, FRAME_HEIGHT), (CENTER_X + shrink, CENTER_Y + shrink), (200, 200, 200), 1)
    
    # Labels
    cv2.putText(image, 'UP', (CENTER_X - 20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 100), 2, cv2.LINE_AA)
    cv2.putText(image, 'DOWN', (CENTER_X - 40, FRAME_HEIGHT - 20), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 160, 255), 2, cv2.LINE_AA)
    cv2.putText(image, 'LEFT', (20, CENTER_Y + 5), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 230, 230), 2, cv2.LINE_AA)
    cv2.putText(image, 'RIGHT', (FRAME_WIDTH - 160, CENTER_Y + 5), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 230, 230), 2, cv2.LINE_AA)
    cv2.putText(image, 'STAY', (CENTER_X - 30, CENTER_Y + 8), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2, cv2.LINE_AA)


def draw_overlay_spooky(image):
    """Mode Spooky: Chia đôi trên/dưới"""
    overlay = image.copy()
    cv2.rectangle(overlay, (0, 0), (FRAME_WIDTH, CENTER_Y), (0, 200, 100), -1)
    cv2.rectangle(overlay, (0, CENTER_Y), (FRAME_WIDTH, FRAME_HEIGHT), (0, 140, 230), -1)
    cv2.addWeighted(overlay, 0.15, image, 0.85, 0, image)
    cv2.line(image, (0, CENTER_Y), (FRAME_WIDTH, CENTER_Y), (255, 255, 255), 2)
    cv2.putText(image, 'JUMP', (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 100), 2, cv2.LINE_AA)
    cv2.putText(image, 'DUCK', (20, FRAME_HEIGHT - 20), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 160, 255), 2, cv2.LINE_AA)


def draw_overlay_default(image):
    """Mode mặc định: chia đôi + deadzone"""
    draw_overlay_spooky(image)
    cv2.circle(image, (CENTER_X, CENTER_Y), DEADZONE_RADIUS, (255, 255, 0), 1)

def draw_overlay_tank(image):
    """Mode Tank Trouble: Chỉ hiện trạng thái gesture"""
    overlay = image.copy()
    cv2.addWeighted(overlay, 0.15, image, 0.85, 0, image)
    
    cv2.circle(image, (CENTER_X, CENTER_Y), DEADZONE_RADIUS, (0, 255, 255), 2)
    cv2.putText(image, 'FIST(OUT) = ROTATE', (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 100), 2, cv2.LINE_AA)
    cv2.putText(image, 'OPEN = MOVE', (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(image, 'FIST(IN) = SHOOT', (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 160, 255), 2, cv2.LINE_AA)


def main():
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

    gesture_history = []
    print('Loading SVM Model...')
    svm_model = joblib.load('svm_model.pkl')

    base_options = python.BaseOptions(model_asset_path='hand_landmarker.task')
    options = vision.HandLandmarkerOptions(base_options=base_options, num_hands=1)
    with vision.HandLandmarker.create_from_options(options) as detector:
        
        while cap.isOpened():
            success, image = cap.read()
            if not success:
                continue

            image = cv2.flip(image, 1)
            
            image.flags.writeable = False
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image_rgb)
            results = detector.detect(mp_image)
            image.flags.writeable = True

            action_text = "NONE"
            current_dir = "NONE"
            current_action = False
            current_hand_y = -1.0
            current_gesture = "NONE"

            # Vẽ overlay theo mode hiện tại 
            mode = current_mode
            if mode == "pacman":
                draw_overlay_pacman(image)
            elif mode == "spooky":
                draw_overlay_spooky(image)
            elif mode == "tank":
                draw_overlay_tank(image)
            else:
                draw_overlay_default(image)

            if results.hand_landmarks:
                hand_landmarks = results.hand_landmarks[0]
                for lm in hand_landmarks:
                    cx, cy = int(lm.x * FRAME_WIDTH), int(lm.y * FRAME_HEIGHT)
                    cv2.circle(image, (cx, cy), 3, (0, 0, 255), -1)

                hx = int(hand_landmarks[9].x * FRAME_WIDTH)
                hy = int(hand_landmarks[9].y * FRAME_HEIGHT)
                
                current_hand_y = hand_landmarks[9].y
                
                cv2.circle(image, (hx, hy), 10, (0, 0, 255), -1)

                wrist = hand_landmarks[0]
                features = []
                for lm in hand_landmarks:
                    features.extend([lm.x - wrist.x, lm.y - wrist.y, lm.z - wrist.z])
                
                prediction = svm_model.predict([features])[0]
                raw_gesture = prediction
                
                dist_to_center = math.hypot(hx - CENTER_X, hy - CENTER_Y)
                    
                gesture_history.append(raw_gesture)
                if len(gesture_history) > 5:
                    gesture_history.pop(0)
                    
                current_gesture = max(set(gesture_history), key=gesture_history.count)
                
                if current_gesture == "OPEN":
                    current_action = True
                else:
                    current_action = False
                
                if current_action:
                    if hy < CENTER_Y:
                        action_text = "JUMP" if mode == "spooky" else "ACTION"
                        cv2.circle(image, (hx, hy), 30, (0, 255, 100), 3)
                    else:
                        action_text = "DUCK" if mode == "spooky" else "ACTION"
                        cv2.circle(image, (hx, hy), 30, (0, 160, 255), 3)
                
                if current_gesture == "POINT":
                    action_text = "SHOOT"
                    cv2.circle(image, (hx, hy), 30, (0, 0, 255), 3)

                # Logic hướng (dùng cho Pacman - nắm tay + di chuyển)
                dist_from_center = math.sqrt((hx - CENTER_X)**2 + (hy - CENTER_Y)**2)
                
                if current_gesture == 'FIST' and dist_from_center > DEADZONE_RADIUS:
                    angle = math.atan2(hy - CENTER_Y, hx - CENTER_X) * 180 / math.pi
                    if -45 <= angle <= 45:
                        current_dir = "RIGHT"
                    elif 45 < angle <= 135:
                        current_dir = "DOWN"
                    elif -135 <= angle < -45:
                        current_dir = "UP"
                    else:
                        current_dir = "LEFT"
                    
                    action_text = current_dir
                    # Vẽ vòng tròn highlight hướng
                    dir_colors = {"UP": (0,255,100), "DOWN": (0,160,255), "LEFT": (0,230,230), "RIGHT": (0,230,230)}
                    cv2.circle(image, (hx, hy), 25, dir_colors.get(current_dir, (255,255,0)), 3)

            send_data(current_dir, current_action, current_hand_y, current_gesture)

            # Hiện action text + mode
            cv2.putText(image, f'{action_text}', (FRAME_WIDTH // 2 - 60, 50),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3, cv2.LINE_AA)
            
            mode_label = f'Mode: {mode.upper()}'
            cv2.putText(image, mode_label, (FRAME_WIDTH - 300, 40),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 1, cv2.LINE_AA)
            cv2.putText(image, 'ESC to exit', (FRAME_WIDTH - 250, FRAME_HEIGHT - 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1, cv2.LINE_AA)

            display_frame = cv2.resize(image, (640, 360))
            cv2.imshow('Camera Controller', display_frame)
            
            if cv2.waitKey(1) & 0xFF == 27:
                break

    cap.release()
    cv2.destroyAllWindows()
    send_data("NONE", False, -1.0, "NONE")

if __name__ == '__main__':
    main()
