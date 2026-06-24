# pyrefly: ignore [missing-import]
import pygame
import sys
import socket
import json
import threading
import random
import math
import os

pygame.init()

# Screen Setup 
WIDTH, HEIGHT = 800, 500
GROUND_Y = HEIGHT - 80
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Spooky Spikes")
clock = pygame.time.Clock()
FPS = 60

# Colors 
BLACK      = (0, 0, 0)
WHITE      = (255, 255, 255)
YELLOW     = (255, 255, 0)
RED        = (239, 68, 68)
DARK_RED   = (180, 40, 40)
PURPLE     = (139, 92, 246)
DARK_PURPLE= (109, 40, 217)
PINK       = (255, 184, 255)
CYAN       = (0, 255, 255)
ORANGE     = (245, 158, 11)
GREEN      = (34, 197, 94)
GOLD       = (251, 191, 36)
GRAY       = (50, 50, 50)
DARK_BG    = (10, 10, 20)
GROUND_COL = (26, 26, 53)
SKY_TOP    = (7, 7, 20)
SKY_MID    = (13, 13, 43)
SKY_BOT    = (21, 21, 48)

# Fonts 
try:
    font_title = pygame.font.SysFont('courier', 56, bold=True)
    font_large = pygame.font.SysFont('courier', 40, bold=True)
    font_medium = pygame.font.SysFont('courier', 28, bold=True)
    font_small = pygame.font.SysFont('courier', 20, bold=True)
    font_tiny  = pygame.font.SysFont('courier', 14)
except:
    font_title = pygame.font.Font(None, 56)
    font_large = pygame.font.Font(None, 40)
    font_medium = pygame.font.Font(None, 28)
    font_small = pygame.font.Font(None, 20)
    font_tiny  = pygame.font.Font(None, 14)


def create_spritesheet():
    CELL = 48
    sheet_w = CELL * 8
    sheet_h = CELL * 4
    sheet = pygame.Surface((sheet_w, sheet_h), pygame.SRCALPHA)
    sheet.fill((0, 0, 0, 0))

    #  Row 0: Player 
    def draw_ghost(surface, x, y, w, h, color1, color2, state='stand', frame=0):
        body_rect = pygame.Rect(x + 4, y + 8, w - 8, h - 12)
        
        # Body gradient simulation
        for i in range(body_rect.height):
            t = i / body_rect.height
            r = int(color1[0] * (1 - t) + color2[0] * t)
            g = int(color1[1] * (1 - t) + color2[1] * t)
            b = int(color1[2] * (1 - t) + color2[2] * t)
            pygame.draw.line(surface, (r, g, b),
                           (body_rect.left, body_rect.top + i),
                           (body_rect.right, body_rect.top + i))

        # Rounded top (head)
        pygame.draw.ellipse(surface, color1,
                          (x + 4, y + 2, w - 8, 24))

        # Wavy bottom
        if state != 'duck':
            wave_y = y + h - 6
            for i in range(4):
                wx = x + 6 + i * ((w - 12) // 4)
                ww = (w - 12) // 4
                offset = (3 if (i + frame) % 2 == 0 else -2)
                pygame.draw.ellipse(surface, color2,
                                  (wx, wave_y + offset, ww, 8))

        # Eyes
        eye_y = y + 14 if state != 'duck' else y + h // 2 - 2
        eye_size = 5 if state != 'dead' else 3
        
        if state == 'dead':
            # X eyes
            cx1, cy1 = x + w // 2 - 7, eye_y
            cx2, cy2 = x + w // 2 + 7, eye_y
            pygame.draw.line(surface, WHITE, (cx1 - 3, cy1 - 3), (cx1 + 3, cy1 + 3), 2)
            pygame.draw.line(surface, WHITE, (cx1 + 3, cy1 - 3), (cx1 - 3, cy1 + 3), 2)
            pygame.draw.line(surface, WHITE, (cx2 - 3, cy2 - 3), (cx2 + 3, cy2 + 3), 2)
            pygame.draw.line(surface, WHITE, (cx2 + 3, cy2 - 3), (cx2 - 3, cy2 + 3), 2)
        else:
            # Normal eyes
            pygame.draw.circle(surface, WHITE, (x + w // 2 - 7, eye_y), eye_size)
            pygame.draw.circle(surface, WHITE, (x + w // 2 + 7, eye_y), eye_size)
            # Pupils
            px_offset = 1 if frame % 2 == 0 else -1
            pygame.draw.circle(surface, (20, 20, 40),
                             (x + w // 2 - 7 + px_offset, eye_y + 1), eye_size // 2 + 1)
            pygame.draw.circle(surface, (20, 20, 40),
                             (x + w // 2 + 7 + px_offset, eye_y + 1), eye_size // 2 + 1)

        # Blush for duck state
        if state == 'duck':
            pygame.draw.ellipse(surface, (239, 68, 68, 80),
                              (x + w // 2 - 14, eye_y + 6, 8, 4))
            pygame.draw.ellipse(surface, (239, 68, 68, 80),
                              (x + w // 2 + 6, eye_y + 6, 8, 4))

        # Highlight
        pygame.draw.ellipse(surface, (255, 255, 255, 60),
                          (x + 10, y + 6, 8, 12))

    # Player stand frame 0 & 1
    draw_ghost(sheet, 0, 0, CELL, CELL, PURPLE, DARK_PURPLE, 'stand', 0)
    draw_ghost(sheet, CELL, 0, CELL, CELL, PURPLE, DARK_PURPLE, 'stand', 1)
    # Player jump frame 0 & 1
    draw_ghost(sheet, CELL*2, 0, CELL, CELL, (167, 139, 250), PURPLE, 'jump', 0)
    draw_ghost(sheet, CELL*3, 0, CELL, CELL, (167, 139, 250), PURPLE, 'jump', 1)
    # Player duck frame 0 & 1 (shorter)
    draw_ghost(sheet, CELL*4, 0 + CELL//2, CELL, CELL//2, PURPLE, DARK_PURPLE, 'duck', 0)
    draw_ghost(sheet, CELL*5, 0 + CELL//2, CELL, CELL//2, PURPLE, DARK_PURPLE, 'duck', 1)
    # Player dead frame 0 & 1
    draw_ghost(sheet, CELL*6, 0, CELL, CELL, (100, 60, 60), (60, 30, 30), 'dead', 0)
    draw_ghost(sheet, CELL*7, 0, CELL, CELL, (80, 50, 50), (50, 25, 25), 'dead', 1)

    # Row 1: Spikes 
    def draw_spike_up(surface, x, y, w, h, frame=0):
        num_spikes = 3
        sw = w // num_spikes
        for i in range(num_spikes):
            sx = x + i * sw
            # Main spike triangle
            color = RED if (i + frame) % 2 == 0 else DARK_RED
            points = [(sx + 2, y + h), (sx + sw // 2, y + 4), (sx + sw - 2, y + h)]
            pygame.draw.polygon(surface, color, points)
            # Highlight
            highlight = [(sx + 4, y + h - 2), (sx + sw // 2, y + 6), (sx + sw // 2 + 2, y + h - 2)]
            pygame.draw.polygon(surface, (255, 120, 120), highlight)
        # Base bar
        pygame.draw.rect(surface, (127, 29, 29), (x, y + h - 8, w, 8))
        pygame.draw.rect(surface, (160, 40, 40), (x, y + h - 8, w, 3))

    def draw_spike_down(surface, x, y, w, h, frame=0):
        num_spikes = 3
        sw = w // num_spikes
        for i in range(num_spikes):
            sx = x + i * sw
            color = RED if (i + frame) % 2 == 0 else DARK_RED
            points = [(sx + 2, y), (sx + sw // 2, y + h - 4), (sx + sw - 2, y)]
            pygame.draw.polygon(surface, color, points)
            highlight = [(sx + 4, y + 2), (sx + sw // 2, y + h - 6), (sx + sw // 2 + 2, y + 2)]
            pygame.draw.polygon(surface, (255, 120, 120), highlight)
        # Base bar
        pygame.draw.rect(surface, (127, 29, 29), (x, y, w, 8))
        pygame.draw.rect(surface, (160, 40, 40), (x, y + 5, w, 3))

    # Ground spikes (frame 0 & 1)
    draw_spike_up(sheet, 0, CELL, CELL, CELL, 0)
    draw_spike_up(sheet, CELL, CELL, CELL, CELL, 1)
    # Ceiling spikes (frame 0 & 1)
    draw_spike_down(sheet, CELL*2, CELL, CELL, CELL, 0)
    draw_spike_down(sheet, CELL*3, CELL, CELL, CELL, 1)
    # Wider ground spikes
    draw_spike_up(sheet, CELL*4, CELL, CELL, CELL, 0)
    draw_spike_up(sheet, CELL*5, CELL, CELL, CELL, 1)
    # Wider ceiling spikes
    draw_spike_down(sheet, CELL*6, CELL, CELL, CELL, 0)
    draw_spike_down(sheet, CELL*7, CELL, CELL, CELL, 1)

    # Row 2: Explosion frames 
    for i in range(4):
        cx = i * CELL + CELL // 2
        cy = CELL * 2 + CELL // 2
        radius = CELL // 2 - 4 - i * 2
        if i < 3:
            # Expanding explosion
            colors = [(255, 200, 50), (255, 100, 30), (200, 50, 20), (100, 20, 10)]
            for j, col in enumerate(colors[:3-i]):
                r = radius + (3 - i - j) * 5
                pygame.draw.circle(sheet, col, (cx, cy), max(1, r))
        else:
            # Smoke
            for j in range(5):
                sx = cx + random.randint(-10, 10)
                sy = cy + random.randint(-10, 10)
                pygame.draw.circle(sheet, (80, 80, 80), (sx, sy), random.randint(3, 6))

    # Spark particles (remaining cells in row 2)
    for i in range(4, 8):
        cx = i * CELL + CELL // 2
        cy = CELL * 2 + CELL // 2
        num_sparks = 8 - i + 4
        for j in range(num_sparks):
            angle = j * (2 * math.pi / num_sparks)
            dist = (i - 3) * 8
            sx = int(cx + math.cos(angle) * dist)
            sy = int(cy + math.sin(angle) * dist)
            spark_col = GOLD if j % 2 == 0 else ORANGE
            pygame.draw.circle(sheet, spark_col, (sx, sy), 3)

    #  Row 3: UI Elements 
    # Heart
    def draw_heart(surface, x, y, size):
        cx, cy = x + size // 2, y + size // 2
        pygame.draw.circle(surface, RED, (cx - size // 5, cy - size // 6), size // 4)
        pygame.draw.circle(surface, RED, (cx + size // 5, cy - size // 6), size // 4)
        points = [
            (cx - size // 3, cy),
            (cx, cy + size // 3),
            (cx + size // 3, cy)
        ]
        pygame.draw.polygon(surface, RED, points)

    draw_heart(sheet, 4, CELL * 3 + 4, CELL - 8)

    # Star
    def draw_star(surface, cx, cy, r):
        points = []
        for i in range(10):
            angle = math.pi * 2 * i / 10 - math.pi / 2
            radius = r if i % 2 == 0 else r * 0.4
            points.append((cx + math.cos(angle) * radius, cy + math.sin(angle) * radius))
        pygame.draw.polygon(surface, GOLD, points)

    draw_star(sheet, CELL + CELL // 2, CELL * 3 + CELL // 2, 16)

    # Skull
    skull_x, skull_y = CELL * 2, CELL * 3
    pygame.draw.ellipse(sheet, WHITE, (skull_x + 8, skull_y + 4, 32, 28))
    pygame.draw.rect(sheet, WHITE, (skull_x + 14, skull_y + 26, 20, 12))
    pygame.draw.circle(sheet, BLACK, (skull_x + 18, skull_y + 16), 5)
    pygame.draw.circle(sheet, BLACK, (skull_x + 30, skull_y + 16), 5)
    pygame.draw.polygon(sheet, BLACK, [(skull_x + 22, skull_y + 22), (skull_x + 24, skull_y + 27), (skull_x + 26, skull_y + 22)])
    for i in range(4):
        pygame.draw.line(sheet, BLACK, (skull_x + 16 + i * 5, skull_y + 32), (skull_x + 16 + i * 5, skull_y + 38), 2)

    return sheet

# Tạo spritesheet 
sprites = create_spritesheet()

sprite_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'spooky_spikes')
os.makedirs(sprite_dir, exist_ok=True)
sprite_path = os.path.join(sprite_dir, 'sprites.png')
try:
    pygame.image.save(sprites, sprite_path)
except:
    pass

#  Sprite Constants 
CELL = 48

current_ai_state = {"dir": "NONE", "action": False}

def udp_listener():
    global current_ai_state
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind(("127.0.0.1", 5005))
    except OSError:
        return
    sock.setblocking(False)
    while True:
        try:
            data, addr = sock.recvfrom(1024)
            current_ai_state = json.loads(data.decode('utf-8'))
        except BlockingIOError:
            pass
        except Exception:
            pass
        pygame.time.wait(5)

listener_thread = threading.Thread(target=udp_listener, daemon=True)
listener_thread.start()


class Particle:
    """Hạt hiệu ứng (jump, death, dodge)"""
    def __init__(self, x, y, vx, vy, color, size, life=1.0, gravity=0.15):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.size = size
        self.life = life
        self.max_life = life
        self.gravity = gravity

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += self.gravity
        self.vx *= 0.98
        self.life -= 0.025
        return self.life > 0

    def draw(self, surface):
        alpha = max(0, min(255, int(255 * (self.life / self.max_life))))
        s = max(1, int(self.size * (self.life / self.max_life)))
        color = (*self.color[:3], alpha) if len(self.color) == 4 else self.color
        pygame.draw.circle(surface, color[:3], (int(self.x), int(self.y)), s)


class ScorePopup:
    """Hiệu ứng +score bay lên"""
    def __init__(self, x, y, text, color=GREEN):
        self.x = x
        self.y = y
        self.text = text
        self.color = color
        self.life = 1.0
        self.vy = -1.5

    def update(self):
        self.y += self.vy
        self.life -= 0.02
        return self.life > 0

    def draw(self, surface):
        alpha = max(0, int(255 * self.life))
        text_surf = font_small.render(self.text, True, self.color)
        text_surf.set_alpha(alpha)
        surface.blit(text_surf, (int(self.x), int(self.y)))



class Explosion:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.frame = 0
        self.frame_timer = 0
        self.frame_interval = 6  # frames between anim frames
        self.active = True
        self.max_frames = 4

        # Cắt explosion frames từ spritesheet (Row 2)
        self.images = []
        for i in range(self.max_frames):
            img = sprites.subsurface(i * CELL, CELL * 2, CELL, CELL).copy()
            self.images.append(img)

    def update(self):
        self.frame_timer += 1
        if self.frame_timer >= self.frame_interval:
            self.frame_timer = 0
            self.frame += 1
            if self.frame >= self.max_frames:
                self.active = False

    def draw(self, surface):
        if self.active and self.frame < len(self.images):
            img = self.images[self.frame]
            # Scale lên cho dễ thấy
            scaled = pygame.transform.scale(img, (CELL * 2, CELL * 2))
            surface.blit(scaled, (self.x - CELL, self.y - CELL))


class Player:
    PLAYER_W = 40
    PLAYER_H_STAND = 56
    PLAYER_H_DUCK = 28
    GRAVITY = 0.65
    JUMP_FORCE = -13.5
    MAX_JUMPS = 2

    def __init__(self):
        self.x = 150
        self.y = GROUND_Y - self.PLAYER_H_STAND
        self.w = self.PLAYER_W
        self.h = self.PLAYER_H_STAND
        self.vy = 0
        self.is_jumping = False
        self.is_ducking = False
        self.is_on_ground = True
        self.jump_count = 0
        self.state = 'stand'  # stand, jump, duck, dead
        self.anim_frame = 0
        self.anim_timer = 0
        self.ghost_trail = []  # [(x, y, w, h, alpha), ...]
        self.invincible = 0

        # Cắt sprite frames từ spritesheet (Row 0)
        self.sprites = {
            'stand': [
                sprites.subsurface(0, 0, CELL, CELL),
                sprites.subsurface(CELL, 0, CELL, CELL),
            ],
            'jump': [
                sprites.subsurface(CELL * 2, 0, CELL, CELL),
                sprites.subsurface(CELL * 3, 0, CELL, CELL),
            ],
            'duck': [
                sprites.subsurface(CELL * 4, CELL // 2, CELL, CELL // 2),
                sprites.subsurface(CELL * 5, CELL // 2, CELL, CELL // 2),
            ],
            'dead': [
                sprites.subsurface(CELL * 6, 0, CELL, CELL),
                sprites.subsurface(CELL * 7, 0, CELL, CELL),
            ],
        }

    def reset(self):
        self.y = GROUND_Y - self.PLAYER_H_STAND
        self.h = self.PLAYER_H_STAND
        self.vy = 0
        self.is_jumping = False
        self.is_ducking = False
        self.is_on_ground = True
        self.jump_count = 0
        self.state = 'stand'
        self.ghost_trail = []
        self.invincible = 0

    def jump(self):
        if self.jump_count < self.MAX_JUMPS:
            self.vy = self.JUMP_FORCE
            self.is_jumping = True
            self.is_on_ground = False
            self.jump_count += 1
            self.state = 'jump'
            return True
        return False

    def duck(self, ducking):
        self.is_ducking = ducking
        if ducking and self.is_on_ground:
            self.state = 'duck'

    def update(self):
        if self.state == 'dead':
            return

        # Ducking logic
        if self.is_ducking and self.is_on_ground:
            self.h = self.PLAYER_H_DUCK
            self.y = GROUND_Y - self.PLAYER_H_DUCK
            self.state = 'duck'
        elif not self.is_ducking and self.is_on_ground and not self.is_jumping:
            self.h = self.PLAYER_H_STAND
            self.y = GROUND_Y - self.PLAYER_H_STAND
            if self.state != 'jump':
                self.state = 'stand'

        # Gravity
        self.vy += self.GRAVITY
        self.y += self.vy

        # Ground check
        current_h = self.PLAYER_H_DUCK if (self.is_ducking and self.is_on_ground) else self.PLAYER_H_STAND
        if self.y + current_h >= GROUND_Y:
            self.y = GROUND_Y - current_h
            self.vy = 0
            self.is_jumping = False
            self.is_on_ground = True
            self.jump_count = 0
            self.h = current_h
            if not self.is_ducking:
                self.state = 'stand'
        else:
            self.is_on_ground = False
            self.h = self.PLAYER_H_STAND
            self.state = 'jump'

        # Animation timer
        self.anim_timer += 1
        if self.anim_timer >= 10:
            self.anim_timer = 0
            self.anim_frame = (self.anim_frame + 1) % 2

        # Ghost trail
        self.ghost_trail.append((self.x, self.y, self.w, self.h))
        if len(self.ghost_trail) > 6:
            self.ghost_trail.pop(0)

        # Invincibility
        if self.invincible > 0:
            self.invincible -= 1

    def get_rect(self):
        shrink = 6
        return pygame.Rect(self.x + shrink, self.y + shrink,
                          self.w - shrink * 2, self.h - shrink * 2)

    def draw(self, surface):
        # Ghost trail effect
        for i, (tx, ty, tw, th) in enumerate(self.ghost_trail):
            alpha = int(40 * (i / len(self.ghost_trail)))
            trail_surf = pygame.Surface((tw, th), pygame.SRCALPHA)
            trail_surf.fill((*PURPLE, alpha))
            surface.blit(trail_surf, (tx, ty))

        # Player glow
        glow_size = 30 + int(math.sin(pygame.time.get_ticks() * 0.003) * 8)
        glow_surf = pygame.Surface((self.w + glow_size * 2, self.h + glow_size * 2), pygame.SRCALPHA)
        pygame.draw.ellipse(glow_surf, (*PURPLE, 25),
                          (0, 0, self.w + glow_size * 2, self.h + glow_size * 2))
        surface.blit(glow_surf, (self.x - glow_size, self.y - glow_size))

        # Sprite rendering
        state = self.state
        frame = self.anim_frame

        # Flash khi invincible
        if self.invincible > 0 and (self.invincible // 3) % 2 == 0:
            return

        sprite = self.sprites[state][frame]

        # Scale sprite to match hitbox
        if state == 'duck':
            scaled = pygame.transform.scale(sprite, (self.w, self.PLAYER_H_DUCK))
        else:
            scaled = pygame.transform.scale(sprite, (self.w, self.PLAYER_H_STAND))

        surface.blit(scaled, (self.x, self.y))



class Spike:
    # Loại gai
    TYPE_GROUND = 'ground'    # Gai hướng lên (cần nhảy)
    TYPE_CEILING = 'ceiling'  # Gai hướng xuống (cần cúi)
    TYPE_MID = 'mid'          # Gai giữa (cần cúi hoặc đứng yên)

    SPIKE_W = 48
    SPIKE_H = 48

    def __init__(self, spike_type, speed):
        self.type = spike_type
        self.speed = speed
        self.w = self.SPIKE_W
        self.h = self.SPIKE_H
        self.x = WIDTH + 20
        self.passed = False
        self.anim_frame = 0
        self.anim_timer = 0

        # Vị trí Y dựa trên loại gai
        if spike_type == self.TYPE_GROUND:
            self.y = GROUND_Y - self.SPIKE_H
        elif spike_type == self.TYPE_CEILING:
            self.y = GROUND_Y - Player.PLAYER_H_STAND - self.SPIKE_H + 12
        else:  # MID
            self.y = GROUND_Y - Player.PLAYER_H_STAND - 15
            self.h = int(self.SPIKE_H * 0.7)

        # Cắt sprite (Row 1)
        if spike_type in (self.TYPE_GROUND, self.TYPE_MID):
            self.sprite_frames = [
                sprites.subsurface(0, CELL, CELL, CELL),
                sprites.subsurface(CELL, CELL, CELL, CELL),
            ]
        else:
            self.sprite_frames = [
                sprites.subsurface(CELL * 2, CELL, CELL, CELL),
                sprites.subsurface(CELL * 3, CELL, CELL, CELL),
            ]

    def update(self):
        self.x -= self.speed
        self.anim_timer += 1
        if self.anim_timer >= 8:
            self.anim_timer = 0
            self.anim_frame = (self.anim_frame + 1) % 2
        return self.x > -self.w - 20

    def get_rect(self):
        shrink = 6
        return pygame.Rect(self.x + shrink, self.y + shrink,
                          self.w - shrink * 2, self.h - shrink * 2)

    def draw(self, surface):
        # Spike glow
        glow_surf = pygame.Surface((self.w + 20, self.h + 20), pygame.SRCALPHA)
        pygame.draw.ellipse(glow_surf, (*RED, 30),
                          (0, 0, self.w + 20, self.h + 20))
        surface.blit(glow_surf, (self.x - 10, self.y - 10))

        # Sprite
        sprite = self.sprite_frames[self.anim_frame]
        scaled = pygame.transform.scale(sprite, (self.w, self.h))
        surface.blit(scaled, (self.x, self.y))

    def draw_warning(self, surface, frame_count):
        """Vẽ cảnh báo khi gai sắp xuất hiện"""
        if self.x > WIDTH - 80 and self.x <= WIDTH + 20:
            alpha = int(abs(math.sin(frame_count * 0.15)) * 150)
            warn_surf = pygame.Surface((4, self.h), pygame.SRCALPHA)
            warn_surf.fill((*RED, alpha))
            surface.blit(warn_surf, (WIDTH - 20, self.y))
            # Warning icon
            icon_surf = font_small.render("!", True, RED)
            icon_surf.set_alpha(alpha)
            surface.blit(icon_surf, (WIDTH - 18, self.y + self.h // 2 - 8))


class Background:
    def __init__(self):
        self.stars = []
        for _ in range(50):
            self.stars.append({
                'x': random.random() * WIDTH,
                'y': random.random() * (GROUND_Y - 30),
                'size': random.random() * 2 + 0.5,
                'speed': random.random() * 0.3 + 0.1,
                'phase': random.random() * 6.28,
            })
        self.ground_offset = 0
        
        # Pre-render sky gradient
        self.sky_surface = pygame.Surface((WIDTH, GROUND_Y))
        for y in range(GROUND_Y):
            t = y / GROUND_Y
            if t < 0.5:
                t2 = t / 0.5
                r = int(SKY_TOP[0] * (1 - t2) + SKY_MID[0] * t2)
                g = int(SKY_TOP[1] * (1 - t2) + SKY_MID[1] * t2)
                b = int(SKY_TOP[2] * (1 - t2) + SKY_MID[2] * t2)
            else:
                t2 = (t - 0.5) / 0.5
                r = int(SKY_MID[0] * (1 - t2) + SKY_BOT[0] * t2)
                g = int(SKY_MID[1] * (1 - t2) + SKY_BOT[1] * t2)
                b = int(SKY_MID[2] * (1 - t2) + SKY_BOT[2] * t2)
            pygame.draw.line(self.sky_surface, (r, g, b), (0, y), (WIDTH, y))

    def draw(self, surface, spike_speed, frame_count):
        # Sky
        surface.blit(self.sky_surface, (0, 0))

        # Stars
        for star in self.stars:
            star['x'] -= star['speed'] * (spike_speed / 4)
            if star['x'] < 0:
                star['x'] = WIDTH
            alpha = int(80 + math.sin(frame_count * 0.02 + star['phase']) * 70)
            alpha = max(0, min(255, alpha))
            pygame.draw.circle(surface, (200, 180, 255),
                             (int(star['x']), int(star['y'])),
                             max(1, int(star['size'])))

        # Moon
        moon_x, moon_y = 650, 70
        moon_surf = pygame.Surface((80, 80), pygame.SRCALPHA)
        pygame.draw.circle(moon_surf, (200, 180, 255, 40), (40, 40), 40)
        pygame.draw.circle(moon_surf, (200, 190, 255, 25), (40, 40), 25)
        pygame.draw.circle(moon_surf, (220, 210, 255, 15), (40, 40), 15)
        surface.blit(moon_surf, (moon_x - 40, moon_y - 40))

        # Ground
        ground_surf = pygame.Surface((WIDTH, HEIGHT - GROUND_Y))
        for y in range(HEIGHT - GROUND_Y):
            t = y / (HEIGHT - GROUND_Y)
            r = int(GROUND_COL[0] * (1 - t) + DARK_BG[0] * t)
            g = int(GROUND_COL[1] * (1 - t) + DARK_BG[1] * t)
            b = int(GROUND_COL[2] * (1 - t) + DARK_BG[2] * t)
            pygame.draw.line(ground_surf, (r, g, b), (0, y), (WIDTH, y))
        surface.blit(ground_surf, (0, GROUND_Y))

        # Ground line glow
        pygame.draw.line(surface, PURPLE, (0, GROUND_Y), (WIDTH, GROUND_Y), 2)
        glow_surf = pygame.Surface((WIDTH, 10), pygame.SRCALPHA)
        pygame.draw.rect(glow_surf, (*PURPLE, 30), (0, 0, WIDTH, 10))
        surface.blit(glow_surf, (0, GROUND_Y - 5))

        # Ground scrolling pattern
        self.ground_offset = (self.ground_offset + spike_speed * 0.5) % 40
        for i in range(0, WIDTH + 40, 40):
            x = i - self.ground_offset
            pygame.draw.line(surface, (*PURPLE[:3],), 
                           (int(x), GROUND_Y + 10), (int(x), HEIGHT), 1)

        # Vignette corners (subtle darkening)
        vignette = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for corner in [(0, 0), (WIDTH, 0), (0, HEIGHT), (WIDTH, HEIGHT)]:
            pygame.draw.circle(vignette, (0, 0, 0, 0), corner, int(WIDTH * 0.6))
        # Simple vignette - dark edges
        edge_w = 80
        for i in range(edge_w):
            alpha = int(40 * (1 - i / edge_w))
            pygame.draw.line(vignette, (0, 0, 0, alpha), (i, 0), (i, HEIGHT))
            pygame.draw.line(vignette, (0, 0, 0, alpha), (WIDTH - i, 0), (WIDTH - i, HEIGHT))
        surface.blit(vignette, (0, 0))


class Game:
    def __init__(self):
        self.background = Background()
        self.player = Player()
        self.spikes = []
        self.particles = []
        self.popups = []
        self.explosions = []

        self.score = 0
        self.best_score = self._load_best()
        self.wave = 1
        self.spike_speed = 4.0
        self.spawn_rate = 90  # frames
        self.frame_count = 0
        self.last_spawn = 0
        self.combo = 0

        self.state = 'START'  # START, PLAYING, GAME_OVER
        self.screen_shake = 0
        self.shake_offset = (0, 0)
        self.flash_alpha = 0

        # UI sprites
        self.heart_sprite = sprites.subsurface(0, CELL * 3, CELL, CELL)
        self.star_sprite = sprites.subsurface(CELL, CELL * 3, CELL, CELL)
        self.skull_sprite = sprites.subsurface(CELL * 2, CELL * 3, CELL, CELL)

    def _load_best(self):
        try:
            path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.spooky_best')
            with open(path, 'r') as f:
                return int(f.read().strip())
        except:
            return 0

    def _save_best(self):
        try:
            path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.spooky_best')
            with open(path, 'w') as f:
                f.write(str(self.best_score))
        except:
            pass

    def reset(self):
        self.player.reset()
        self.spikes = []
        self.particles = []
        self.popups = []
        self.explosions = []
        self.score = 0
        self.wave = 1
        self.spike_speed = 4.0
        self.spawn_rate = 90
        self.frame_count = 0
        self.last_spawn = 0
        self.combo = 0
        self.screen_shake = 0
        self.flash_alpha = 0
        self.state = 'PLAYING'

    def spawn_spike(self):
        types = [Spike.TYPE_GROUND, Spike.TYPE_CEILING]
        if self.wave >= 3:
            types.append(Spike.TYPE_MID)

        rand = random.random()
        if self.wave <= 2:
            spike_type = Spike.TYPE_GROUND if rand < 0.65 else Spike.TYPE_CEILING
        elif self.wave <= 5:
            if rand < 0.4:
                spike_type = Spike.TYPE_GROUND
            elif rand < 0.75:
                spike_type = Spike.TYPE_CEILING
            else:
                spike_type = Spike.TYPE_MID
        else:
            if rand < 0.35:
                spike_type = Spike.TYPE_GROUND
            elif rand < 0.65:
                spike_type = Spike.TYPE_CEILING
            else:
                spike_type = Spike.TYPE_MID

        self.spikes.append(Spike(spike_type, self.spike_speed))

        # Wave 4+: đôi khi spawn gai đôi
        if self.wave >= 4 and random.random() < 0.25:
            second_type = Spike.TYPE_GROUND if spike_type == Spike.TYPE_CEILING else Spike.TYPE_CEILING
            extra = Spike(second_type, self.spike_speed)
            extra.x += 60
            self.spikes.append(extra)

    def spawn_jump_particles(self):
        for _ in range(8):
            self.particles.append(Particle(
                self.player.x + self.player.w // 2,
                GROUND_Y,
                (random.random() - 0.5) * 6,
                -random.random() * 4 - 1,
                PURPLE, random.random() * 3 + 2
            ))

    def spawn_death_particles(self):
        for _ in range(25):
            color = PURPLE if random.random() > 0.5 else RED
            self.particles.append(Particle(
                self.player.x + self.player.w // 2,
                self.player.y + self.player.h // 2,
                (random.random() - 0.5) * 12,
                (random.random() - 0.5) * 12,
                color, random.random() * 6 + 3,
                life=1.5, gravity=0.1
            ))

    def game_over(self):
        self.state = 'GAME_OVER'
        self.player.state = 'dead'
        self.spawn_death_particles()
        self.explosions.append(Explosion(
            self.player.x + self.player.w // 2,
            self.player.y + self.player.h // 2
        ))
        self.screen_shake = 15
        self.flash_alpha = 200

        if self.score > self.best_score:
            self.best_score = self.score
            self._save_best()

    def update(self):
        if self.state != 'PLAYING':
            self.particles = [p for p in self.particles if p.update()]
            for exp in self.explosions:
                exp.update()
            self.explosions = [e for e in self.explosions if e.active]
            if self.flash_alpha > 0:
                self.flash_alpha = max(0, self.flash_alpha - 8)
            if self.screen_shake > 0:
                self.screen_shake -= 1
                self.shake_offset = (
                    random.randint(-4, 4) if self.screen_shake > 0 else 0,
                    random.randint(-4, 4) if self.screen_shake > 0 else 0
                )
            else:
                self.shake_offset = (0, 0)
            return

        self.frame_count += 1

        # Player
        self.player.update()

        # Spawn spikes
        if self.frame_count - self.last_spawn >= self.spawn_rate:
            self.spawn_spike()
            self.last_spawn = self.frame_count

        # Update spikes
        alive_spikes = []
        for spike in self.spikes:
            if spike.update():
                # Check pass player
                if not spike.passed and spike.x + spike.w < self.player.x:
                    spike.passed = True
                    self.score += 1
                    self.combo += 1
                    
                    # Combo text
                    if self.combo >= 5:
                        text = f"+1 x{self.combo}🔥"
                        color = GOLD if self.combo >= 10 else ORANGE
                    else:
                        text = "+1"
                        color = GREEN
                    self.popups.append(ScorePopup(
                        self.player.x + self.player.w + 10,
                        self.player.y, text, color
                    ))

                    # Combo bonus
                    if self.combo % 10 == 0:
                        self.score += 5
                        self.popups.append(ScorePopup(
                            self.player.x, self.player.y - 25,
                            "+5 COMBO!", GOLD
                        ))

                # Collision
                if self.player.get_rect().colliderect(spike.get_rect()):
                    if self.player.invincible <= 0:
                        self.game_over()
                        return

                alive_spikes.append(spike)
        self.spikes = alive_spikes

        # Difficulty scaling
        if self.frame_count % 300 == 0:  # Mỗi 5 giây
            self.spike_speed = min(12, self.spike_speed + 0.3)
            self.spawn_rate = max(30, self.spawn_rate - 4)

        if self.frame_count % 600 == 0:  # Mỗi 10 giây
            self.wave += 1

        # Update effects
        self.particles = [p for p in self.particles if p.update()]
        self.popups = [p for p in self.popups if p.update()]
        for exp in self.explosions:
            exp.update()
        self.explosions = [e for e in self.explosions if e.active]

        # Screen effects
        if self.flash_alpha > 0:
            self.flash_alpha = max(0, self.flash_alpha - 8)
        if self.screen_shake > 0:
            self.screen_shake -= 1
            self.shake_offset = (random.randint(-3, 3), random.randint(-3, 3))
        else:
            self.shake_offset = (0, 0)

    def draw(self):
        # Render surface (để áp dụng screen shake)
        render_surf = pygame.Surface((WIDTH, HEIGHT))

        # Background
        self.background.draw(render_surf, self.spike_speed, self.frame_count)

        if self.state == 'START':
            self._draw_start_screen(render_surf)
        elif self.state == 'PLAYING':
            self._draw_gameplay(render_surf)
        elif self.state == 'GAME_OVER':
            self._draw_game_over(render_surf)

        # Screen flash
        if self.flash_alpha > 0:
            flash = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            flash.fill((239, 68, 68, self.flash_alpha))
            render_surf.blit(flash, (0, 0))

        # Apply shake
        screen.fill(BLACK)
        screen.blit(render_surf, self.shake_offset)

    def _draw_start_screen(self, surface):
        # Player idle animation
        self.player.anim_timer += 1
        if self.player.anim_timer >= 10:
            self.player.anim_timer = 0
            self.player.anim_frame = (self.player.anim_frame + 1) % 2
        self.player.draw(surface)

        # Overlay
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((10, 10, 18, 200))
        surface.blit(overlay, (0, 0))

        # Title with floating animation
        t = pygame.time.get_ticks()
        title_y = 120 + int(math.sin(t * 0.002) * 8)

        # Ghost emoji + Title
        title_text = "SPOOKY SPIKES"
        title_surf = font_title.render(title_text, True, PURPLE)
        title_rect = title_surf.get_rect(center=(WIDTH // 2, title_y))
        surface.blit(title_surf, title_rect)

        # Subtitle
        sub_text = "Dodge the spikes. Survive!"
        sub_surf = font_small.render(sub_text, True, (148, 163, 184))
        sub_rect = sub_surf.get_rect(center=(WIDTH // 2, title_y + 50))
        surface.blit(sub_surf, sub_rect)

        # Skull sprite
        skull_scaled = pygame.transform.scale(self.skull_sprite, (64, 64))
        surface.blit(skull_scaled, (WIDTH // 2 - 32, title_y - 90))

        # Blinking "Press" text
        if (t // 500) % 2 == 0:
            start_text = "OPEN HAND / SPACE TO START"
            start_surf = font_small.render(start_text, True, YELLOW)
            start_rect = start_surf.get_rect(center=(WIDTH // 2, 320))
            surface.blit(start_surf, start_rect)

        # Controls hint
        controls = [
            ("SPACE / UP", "Jump"),
            ("DOWN / S", "Duck"),
            ("Open hand", "Action"),
        ]
        y_offset = 370
        for key, desc in controls:
            key_surf = font_tiny.render(f"[{key}]", True, PURPLE)
            desc_surf = font_tiny.render(f" {desc}", True, (148, 163, 184))
            total_w = key_surf.get_width() + desc_surf.get_width()
            x = WIDTH // 2 - total_w // 2
            surface.blit(key_surf, (x, y_offset))
            surface.blit(desc_surf, (x + key_surf.get_width(), y_offset))
            y_offset += 22

        # Best score
        if self.best_score > 0:
            best_text = f"BEST: {self.best_score}"
            best_surf = font_small.render(best_text, True, GREEN)
            best_rect = best_surf.get_rect(center=(WIDTH // 2, 460))
            surface.blit(best_surf, best_rect)

    def _draw_gameplay(self, surface):
        # Warning lines
        for spike in self.spikes:
            spike.draw_warning(surface, self.frame_count)

        # Spikes
        for spike in self.spikes:
            spike.draw(surface)

        # Player
        self.player.draw(surface)

        # Particles
        for p in self.particles:
            p.draw(surface)

        # Explosions
        for exp in self.explosions:
            exp.draw(surface)

        # Score popups
        for popup in self.popups:
            popup.draw(surface)

        # HUD
        self._draw_hud(surface)

    def _draw_game_over(self, surface):
        # Still draw game elements
        for spike in self.spikes:
            spike.draw(surface)

        # Particles & explosions
        for p in self.particles:
            p.draw(surface)
        for exp in self.explosions:
            exp.draw(surface)

        # Overlay
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((10, 10, 18, 180))
        surface.blit(overlay, (0, 0))

        # Game Over text
        t = pygame.time.get_ticks()
        go_y = 130 + int(math.sin(t * 0.003) * 5)

        # Skull
        skull_scaled = pygame.transform.scale(self.skull_sprite, (80, 80))
        surface.blit(skull_scaled, (WIDTH // 2 - 40, go_y - 100))

        go_surf = font_title.render("GAME OVER!", True, RED)
        go_rect = go_surf.get_rect(center=(WIDTH // 2, go_y))
        surface.blit(go_surf, go_rect)

        # Score
        score_text = f"Score: {self.score}"
        score_surf = font_large.render(score_text, True, GOLD)
        score_rect = score_surf.get_rect(center=(WIDTH // 2, go_y + 60))
        surface.blit(score_surf, score_rect)

        # Best
        best_text = f"Best: {self.best_score}"
        best_color = GREEN if self.score >= self.best_score else (148, 163, 184)
        best_surf = font_medium.render(best_text, True, best_color)
        best_rect = best_surf.get_rect(center=(WIDTH // 2, go_y + 100))
        surface.blit(best_surf, best_rect)

        # New record!
        if self.score >= self.best_score and self.score > 0:
            if (t // 300) % 2 == 0:
                nr_surf = font_medium.render("NEW RECORD!", True, GOLD)
                nr_rect = nr_surf.get_rect(center=(WIDTH // 2, go_y + 140))
                surface.blit(nr_surf, nr_rect)

        # Restart hint
        if (t // 500) % 2 == 0:
            restart_surf = font_small.render("OPEN HAND / R TO RESTART", True, YELLOW)
            restart_rect = restart_surf.get_rect(center=(WIDTH // 2, go_y + 190))
            surface.blit(restart_surf, restart_rect)

    def _draw_hud(self, surface):
        # Score panel (top left)
        panel = pygame.Surface((200, 40), pygame.SRCALPHA)
        panel.fill((18, 18, 31, 180))
        pygame.draw.rect(panel, (*PURPLE, 80), (0, 0, 200, 40), 1, border_radius=8)
        surface.blit(panel, (10, 10))

        # Star icon
        star_small = pygame.transform.scale(self.star_sprite, (24, 24))
        surface.blit(star_small, (18, 18))

        score_surf = font_medium.render(f"Score: {self.score}", True, GOLD)
        surface.blit(score_surf, (46, 14))

        # Wave & Speed (top right)
        info_panel = pygame.Surface((220, 40), pygame.SRCALPHA)
        info_panel.fill((18, 18, 31, 180))
        pygame.draw.rect(info_panel, (*PURPLE, 80), (0, 0, 220, 40), 1, border_radius=8)
        surface.blit(info_panel, (WIDTH - 230, 10))

        wave_surf = font_small.render(f"Wave {self.wave}", True, CYAN)
        surface.blit(wave_surf, (WIDTH - 220, 18))

        speed_text = f"Spd {self.spike_speed:.1f}"
        speed_color = ORANGE if self.spike_speed > 8 else WHITE
        speed_surf = font_small.render(speed_text, True, speed_color)
        surface.blit(speed_surf, (WIDTH - 130, 18))

        # Difficulty dots
        dot_x = WIDTH // 2 - 30
        dot_y = 18
        diff_level = min(5, int(self.wave / 2) + 1)
        for i in range(5):
            color = RED if i < diff_level else (60, 60, 60)
            pygame.draw.circle(surface, color, (dot_x + i * 14, dot_y + 5), 4)
            if i < diff_level:
                # Glow
                glow = pygame.Surface((12, 12), pygame.SRCALPHA)
                pygame.draw.circle(glow, (*RED, 60), (6, 6), 6)
                surface.blit(glow, (dot_x + i * 14 - 6, dot_y + 5 - 6))

        # Best score (top center)
        best_surf = font_tiny.render(f"Best: {self.best_score}", True, GREEN)
        best_rect = best_surf.get_rect(center=(WIDTH // 2, 36))
        surface.blit(best_surf, best_rect)



def main():
    try:
        mode_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        mode_sock.sendto(b"spooky", ("127.0.0.1", 5006))
        mode_sock.close()
    except:
        pass

    game = Game()
    running = True
    last_ai_action = False

    while running:
        space_pressed = False
        r_pressed = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

                if event.key == pygame.K_SPACE:
                    space_pressed = True

                if game.state == 'PLAYING':
                    if event.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w):
                        if game.player.jump():
                            game.spawn_jump_particles()

                    if event.key in (pygame.K_DOWN, pygame.K_s):
                        game.player.duck(True)

                elif game.state == 'GAME_OVER':
                    if event.key == pygame.K_r:
                        r_pressed = True

            elif event.type == pygame.KEYUP:
                if event.key in (pygame.K_DOWN, pygame.K_s):
                    game.player.duck(False)

        ai_hand_y = current_ai_state.get("hand_y", -1.0)
        ai_hand_open = current_ai_state.get("action", False)  # xòe tay = action = True

        trigger_action = space_pressed or r_pressed or (ai_hand_open and not last_ai_action)
        last_ai_action = ai_hand_open

        if game.state == 'START':
            if trigger_action:
                game.reset()

        elif game.state == 'PLAYING':
            if ai_hand_open and ai_hand_y >= 0:
                if ai_hand_y < 0.5:
                    # Tay ở nửa TRÊN → NHẢY
                    if game.player.is_on_ground:
                        if game.player.jump():
                            game.spawn_jump_particles()
                else:
                    # Tay ở nửa DƯỚI → CÚI
                    game.player.duck(True)
            else:
                # Nắm tay hoặc không có tay → thả cúi (nếu keyboard không giữ)
                if not pygame.key.get_pressed()[pygame.K_DOWN] and not pygame.key.get_pressed()[pygame.K_s]:
                    game.player.duck(False)

        elif game.state == 'GAME_OVER':
            if trigger_action:
                game.reset()

        # Update 
        game.update()

        # Draw 
        game.draw()
        pygame.display.flip()
        clock.tick(FPS)

    # Reset camera mode khi thoát
    try:
        mode_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        mode_sock.sendto(b"default", ("127.0.0.1", 5006))
        mode_sock.close()
    except:
        pass

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
