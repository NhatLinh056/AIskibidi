import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import csv
import os

import argparse

def init_csv(csv_file):
    # Khởi tạo file CSV nếu chưa tồn tại
    if not os.path.exists(csv_file):
        with open(csv_file, mode='w', newline='') as f:
            writer = csv.writer(f)
            header = []
            # 21 điểm (x, y, z)
            for i in range(21):
                header.extend([f'x_{i}', f'y_{i}', f'z_{i}'])
            header.append('label')
            writer.writerow(header)

def normalize_landmarks(hand_landmarks):
    wrist_x = hand_landmarks[0].x
    wrist_y = hand_landmarks[0].y
    wrist_z = hand_landmarks[0].z
    
    normalized = []
    for lm in hand_landmarks:
        normalized.extend([lm.x - wrist_x, lm.y - wrist_y, lm.z - wrist_z])
    return normalized

def main():
    parser = argparse.ArgumentParser(description="Collect hand gesture data.")
    parser.add_argument("csv_file", nargs='?', default="gesture_dataset.csv", help="Name of the CSV file to save data to (e.g., train_1.csv)")
    args = parser.parse_args()
    
    csv_file = args.csv_file
    init_csv(csv_file)
    print(f"Data will be saved to: {csv_file}")

    base_options = python.BaseOptions(model_asset_path='hand_landmarker.task')
    options = vision.HandLandmarkerOptions(base_options=base_options, num_hands=1)
    detector = vision.HandLandmarker.create_from_options(options)

    cap = cv2.VideoCapture(0)
    
    counts = {'OPEN': 0, 'FIST': 0, 'POINT': 0}
    
    print("=========================================")
    print("HƯỚNG DẪN THU THẬP DỮ LIỆU:")
    print("- Đưa tay lên trước camera.")
    print("- Nhấn giữ 'o' để ghi lại cử chỉ OPEN (Mở tay).")
    print("- Nhấn giữ 'f' để ghi lại cử chỉ FIST (Nắm tay).")
    print("- Nhấn giữ 'p' để ghi lại cử chỉ POINT (Chỉ ngón trỏ).")
    print("- Nhấn 'q' để thoát.")
    print("=========================================")

    # Mở file sẵn để ghi liên tục (tránh lag/giật camera)
    csv_file_handle = open(csv_file, mode='a', newline='')
    csv_writer = csv.writer(csv_file_handle)

    while cap.isOpened():
        success, image = cap.read()
        if not success:
            continue
            
        image = cv2.flip(image, 1)
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Nhận diện tay bằng Tasks API
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image_rgb)
        detection_result = detector.detect(mp_image)
        
        # Xử lý phím bấm
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
            
        label = None
        if key == ord('o'):
            label = 'OPEN'
        elif key == ord('f'):
            label = 'FIST'
        elif key == ord('p'):
            label = 'POINT'

        if detection_result.hand_landmarks:
            hand_landmarks = detection_result.hand_landmarks[0]
            
            # Vẽ các điểm lên màn hình để dễ nhìn
            h, w, _ = image.shape
            for lm in hand_landmarks:
                cv2.circle(image, (int(lm.x * w), int(lm.y * h)), 3, (0, 0, 255), -1)
            
            if label is not None:
                features = normalize_landmarks(hand_landmarks)
                row = features + [label]
                csv_writer.writerow(row)
                counts[label] += 1
        
        # Hiển thị HUD
        cv2.putText(image, "Press & Hold: 'o'(OPEN), 'f'(FIST), 'p'(POINT), 'q'(QUIT)", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        status_text = f"Collected - OPEN: {counts['OPEN']} | FIST: {counts['FIST']} | POINT: {counts['POINT']}"
        cv2.putText(image, status_text, (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        
        cv2.imshow('Data Collection - Thu thap du lieu tay', image)
        
    cap.release()
    cv2.destroyAllWindows()
    csv_file_handle.close()
    print("Đã đóng camera và lưu file CSV.")

if __name__ == '__main__':
    main()
