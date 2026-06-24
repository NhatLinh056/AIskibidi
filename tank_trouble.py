# pyrefly: ignore [missing-import]
import pygame
import sys
import socket
import json
import threading
import math
import random

pygame.init()

# Screen & Constants 
WIDTH, HEIGHT = 800, 600
CELL_SIZE = 40
ROWS = HEIGHT // CELL_SIZE
COLS = WIDTH // CELL_SIZE

# Colors 
BLACK = (10, 10, 15)
WHITE = (240, 240, 240)
WALL_COLOR = (40, 50, 80)
PLAYER_COLOR = (0, 255, 100)
ENEMY_COLOR = (255, 50, 50)
BULLET_COLOR = (255, 255, 0)
TEXT_COLOR = (200, 200, 200)

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Tank Trouble")
clock = pygame.time.Clock()

try:
    font_large = pygame.font.SysFont('courier', 48, bold=True)
    font_medium = pygame.font.SysFont('courier', 28, bold=True)
    font_small = pygame.font.SysFont('courier', 16, bold=True)
except:
    font_large = pygame.font.Font(None, 48)
    font_medium = pygame.font.Font(None, 28)
    font_small = pygame.font.Font(None, 16)

#  UDP LISTENER

current_ai_state = {"gesture": "NONE"}

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
            data, _ = sock.recvfrom(1024)
            current_ai_state = json.loads(data.decode('utf-8'))
        except BlockingIOError:
            pass
        except Exception:
            pass
        pygame.time.wait(5)

listener_thread = threading.Thread(target=udp_listener, daemon=True)
listener_thread.start()

def build_maze():
    walls = []
    T = 10 # Wall thickness
    # Outer boundaries
    walls.append(pygame.Rect(0, 0, WIDTH, T))
    walls.append(pygame.Rect(0, HEIGHT - T, WIDTH, T))
    walls.append(pygame.Rect(0, 0, T, HEIGHT))
    walls.append(pygame.Rect(WIDTH - T, 0, T, HEIGHT))
    
    # Internal walls to resemble Tank Trouble
    # Vertical walls
    walls.append(pygame.Rect(150, 150, T, 300))
    walls.append(pygame.Rect(300, 0, T, 150))
    walls.append(pygame.Rect(450, 150, T, 300))
    walls.append(pygame.Rect(600, 300, T, 300))
    walls.append(pygame.Rect(600, 0, T, 150))
    
    # Horizontal walls
    walls.append(pygame.Rect(0, 150, 150, T))
    walls.append(pygame.Rect(150, 450, 150, T))
    walls.append(pygame.Rect(300, 300, 150, T))
    walls.append(pygame.Rect(450, 150, 150, T))
    walls.append(pygame.Rect(450, 450, 150, T))
    walls.append(pygame.Rect(600, 300, 200, T))
    
    return walls


class Bullet:
    def __init__(self, x, y, angle, owner):
        self.x = x
        self.y = y
        self.angle = angle
        self.speed = 2
        self.radius = 4
        self.bounces = 0
        self.max_bounces = 4
        self.owner = owner # "player" or "enemy"
        self.active = True
        
        rad = math.radians(self.angle)
        self.dx = math.cos(rad) * self.speed
        self.dy = -math.sin(rad) * self.speed

    def update(self, walls):
        if not self.active: return
        
        # Next pos
        nx = self.x + self.dx
        ny = self.y + self.dy
        
        # Check collision
        rect = pygame.Rect(nx - self.radius, ny - self.radius, self.radius*2, self.radius*2)
        hit_wall = None
        for w in walls:
            if w.colliderect(rect):
                hit_wall = w
                break
                
        if hit_wall:
            self.bounces += 1
            if self.bounces > self.max_bounces:
                self.active = False
                return
                
            # Determine bounce direction
            # Check horizontal vs vertical collision
            overlap_left = rect.right - w.left
            overlap_right = w.right - rect.left
            overlap_top = rect.bottom - w.top
            overlap_bottom = w.bottom - rect.top
            
            min_overlap = min(overlap_left, overlap_right, overlap_top, overlap_bottom)
            
            if min_overlap == overlap_left or min_overlap == overlap_right:
                self.dx *= -1
                self.x += self.dx
            else:
                self.dy *= -1
                self.y += self.dy
        else:
            self.x = nx
            self.y = ny

    def draw(self, surface):
        if self.active:
            pygame.draw.circle(surface, BULLET_COLOR, (int(self.x), int(self.y)), self.radius)
            # glow
            glow = pygame.Surface((16, 16), pygame.SRCALPHA)
            pygame.draw.circle(glow, (255, 255, 0, 100), (8, 8), 8)
            surface.blit(glow, (int(self.x) - 8, int(self.y) - 8))


class Tank:
    def __init__(self, x, y, color, is_player=False):
        self.x = x
        self.y = y
        self.color = color
        self.is_player = is_player
        self.angle = 0
        self.speed = 2
        self.rot_speed = 2
        self.size = 20
        self.cooldown = 0
        self.alive = True
        
        # Enemy AI state
        self.ai_timer = 0
        self.ai_state = "ROTATE"

    def update(self, gesture, walls, bullets, target=None):
        if not self.alive: return
        
        if self.cooldown > 0:
            self.cooldown -= 1

        if self.is_player:
            if gesture == "FIST":
                self.angle = (self.angle + self.rot_speed) % 360
            elif gesture == "OPEN":
                # Move forward (sliding collision)
                rad = math.radians(self.angle)
                nx = self.x + math.cos(rad) * self.speed
                rect_x = pygame.Rect(nx - self.size//2, self.y - self.size//2, self.size, self.size)
                if not any(w.colliderect(rect_x) for w in walls):
                    self.x = nx
                    
                ny = self.y - math.sin(rad) * self.speed
                rect_y = pygame.Rect(self.x - self.size//2, ny - self.size//2, self.size, self.size)
                if not any(w.colliderect(rect_y) for w in walls):
                    self.y = ny
            elif gesture == "POINT":
                # Shoot
                if self.cooldown <= 0:
                    self.shoot(bullets)
                    self.cooldown = 30
        else:
            # Enemy AI
            self.ai_timer -= 1
            if self.ai_timer <= 0:
                if target and target.alive:
                    dx = target.x - self.x
                    dy = target.y - self.y
                    target_angle = math.degrees(math.atan2(-dy, dx)) % 360
                    angle_diff = (target_angle - self.angle + 180) % 360 - 180
                    
                    if abs(angle_diff) < 15:
                        self.ai_state = "SHOOT"
                        self.ai_timer = random.randint(10, 30)
                    elif abs(angle_diff) < 60:
                        self.ai_state = "MOVE"
                        self.ai_timer = random.randint(20, 50)
                    else:
                        self.ai_state = "ROTATE"
                        self.rot_dir = 1 if angle_diff > 0 else -1
                        self.ai_timer = random.randint(5, 15)
                else:
                    self.ai_state = random.choice(["ROTATE", "MOVE", "SHOOT"])
                    self.ai_timer = random.randint(30, 90)
                
            if self.ai_state == "ROTATE":
                if hasattr(self, 'rot_dir'):
                    self.angle = (self.angle + self.rot_speed * self.rot_dir) % 360
                else:
                    self.angle = (self.angle + self.rot_speed) % 360
            elif self.ai_state == "MOVE":
                rad = math.radians(self.angle)
                nx = self.x + math.cos(rad) * self.speed * 0.7
                rect_x = pygame.Rect(nx - self.size//2, self.y - self.size//2, self.size, self.size)
                hit_x = any(w.colliderect(rect_x) for w in walls)
                if not hit_x:
                    self.x = nx
                    
                ny = self.y - math.sin(rad) * self.speed * 0.7
                rect_y = pygame.Rect(self.x - self.size//2, ny - self.size//2, self.size, self.size)
                hit_y = any(w.colliderect(rect_y) for w in walls)
                if not hit_y:
                    self.y = ny
                    
                if hit_x or hit_y:
                    self.ai_state = "ROTATE"
                    self.rot_dir = random.choice([1, -1])
                    self.ai_timer = 20
            elif self.ai_state == "SHOOT":
                if self.cooldown <= 0:
                    self.shoot(bullets)
                    self.cooldown = 60
                    self.ai_state = "MOVE"
                    self.ai_timer = 40

    def shoot(self, bullets):
        rad = math.radians(self.angle)
        bx = self.x + math.cos(rad) * (self.size / 2 + 2)
        by = self.y - math.sin(rad) * (self.size / 2 + 2)
        owner = "player" if self.is_player else "enemy"
        bullets.append(Bullet(bx, by, self.angle, owner))

    def draw(self, surface):
        if not self.alive: return
        
        # Tank body
        rect = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
        pygame.draw.rect(rect, self.color, (0, 0, self.size, self.size), border_radius=4)
        
        # Rotate body
        rotated_body = pygame.transform.rotate(rect, self.angle)
        body_rect = rotated_body.get_rect(center=(int(self.x), int(self.y)))
        surface.blit(rotated_body, body_rect)
        
        # Barrel
        rad = math.radians(self.angle)
        end_x = self.x + math.cos(rad) * (self.size)
        end_y = self.y - math.sin(rad) * (self.size)
        pygame.draw.line(surface, WHITE, (self.x, self.y), (end_x, end_y), 4)

def check_bullet_collisions(tanks, bullets):
    for b in bullets:
        if not b.active: continue
        for t in tanks:
            if not t.alive: continue
            if t.is_player and b.owner == "player" and b.bounces == 0:
                continue 
            if not t.is_player and b.owner == "enemy" and b.bounces == 0:
                continue
                
            dist = math.sqrt((b.x - t.x)**2 + (b.y - t.y)**2)
            if dist < t.size:
                t.alive = False
                b.active = False
                return t # Return destroyed tank


def main():
    # Send camera mode switch
    try:
        mode_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        mode_sock.sendto(b"tank", ("127.0.0.1", 5006))
        mode_sock.close()
    except:
        pass

    walls = build_maze()
    
    game_state = "START"
    score = 0
    wave = 1
    
    player = Tank(CELL_SIZE * 1.5, CELL_SIZE * 1.5, PLAYER_COLOR, is_player=True)
    enemies = []
    bullets = []
    
    def spawn_enemies(count):
        valid_spawns = [(700, 100), (700, 500), (400, 300), (100, 500), (250, 450), (550, 150)]
        
        spawned = []
        for _ in range(count):
            if valid_spawns:
                pos = random.choice(valid_spawns)
                spawned.append(Tank(pos[0], pos[1], ENEMY_COLOR))
                valid_spawns.remove(pos)
        return spawned

    running = True
    while running:
        # Keyboard fallback
        gesture = current_ai_state.get("gesture", "NONE")
        keys = pygame.key.get_pressed()
        if keys[pygame.K_SPACE]: gesture = "OPEN"
        elif keys[pygame.K_RETURN]: gesture = "POINT"
        elif gesture == "NONE": gesture = "FIST"

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

        screen.fill(BLACK)

        if game_state == "START":
            surf = font_large.render("TANK TROUBLE", True, PLAYER_COLOR)
            screen.blit(surf, surf.get_rect(center=(WIDTH//2, HEIGHT//2 - 50)))
            
            sub = font_medium.render("OPEN HAND = START", True, TEXT_COLOR)
            screen.blit(sub, sub.get_rect(center=(WIDTH//2, HEIGHT//2 + 20)))
            
            if gesture == "OPEN":
                enemies = spawn_enemies(wave)
                game_state = "PLAYING"
                
        elif game_state == "PLAYING":
            # Update
            player.update(gesture, walls, bullets)
            for e in enemies:
                e.update("FIST", walls, bullets, target=player)
                
            for b in bullets:
                b.update(walls)
                
            # Collisions
            destroyed = check_bullet_collisions([player] + enemies, bullets)
            if destroyed:
                if destroyed.is_player:
                    game_state = "GAME_OVER"
                else:
                    score += 100
                    
            # Cleanup
            bullets = [b for b in bullets if b.active]
            enemies = [e for e in enemies if e.alive]
            if len(enemies) == 0 and game_state != "GAME_OVER":
                game_state = "WAVE_COMPLETE"

            # Draw
            for w in walls:
                pygame.draw.rect(screen, WALL_COLOR, w)
                
            player.draw(screen)
            for e in enemies:
                e.draw(screen)
            for b in bullets:
                b.draw(screen)
                
            # HUD
            score_txt = font_small.render(f"SCORE: {score}  WAVE: {wave}", True, TEXT_COLOR)
            screen.blit(score_txt, (10, 10))
            
            # Gesture Hint
            hint_txt = font_small.render(f"GESTURE: {gesture}", True, PLAYER_COLOR)
            screen.blit(hint_txt, (WIDTH - 150, 10))
            
        elif game_state == "WAVE_COMPLETE":
            for w in walls:
                pygame.draw.rect(screen, WALL_COLOR, w)
            player.draw(screen)
            for b in bullets:
                b.draw(screen)
                
            surf = font_large.render("WAVE CLEARED!", True, PLAYER_COLOR)
            screen.blit(surf, surf.get_rect(center=(WIDTH//2, HEIGHT//2 - 50)))
            
            sub = font_medium.render("OPEN HAND TO CONTINUE", True, TEXT_COLOR)
            screen.blit(sub, sub.get_rect(center=(WIDTH//2, HEIGHT//2 + 20)))
            
            if gesture == "OPEN":
                wave += 1
                enemies = spawn_enemies(min(wave, 5))
                player.x = CELL_SIZE * 1.5
                player.y = CELL_SIZE * 1.5
                bullets = []
                game_state = "PLAYING"
            
        elif game_state == "GAME_OVER":
            for w in walls:
                pygame.draw.rect(screen, WALL_COLOR, w)
            player.draw(screen)
            for e in enemies:
                e.draw(screen)
                
            surf = font_large.render("GAME OVER", True, ENEMY_COLOR)
            screen.blit(surf, surf.get_rect(center=(WIDTH//2, HEIGHT//2 - 50)))
            
            score_txt = font_medium.render(f"FINAL SCORE: {score}", True, PLAYER_COLOR)
            screen.blit(score_txt, score_txt.get_rect(center=(WIDTH//2, HEIGHT//2 + 10)))
            
            sub = font_small.render("OPEN HAND TO RESTART", True, TEXT_COLOR)
            screen.blit(sub, sub.get_rect(center=(WIDTH//2, HEIGHT//2 + 60)))
            
            if gesture == "OPEN":
                score = 0
                wave = 1
                player = Tank(CELL_SIZE * 1.5, CELL_SIZE * 1.5, PLAYER_COLOR, is_player=True)
                enemies = spawn_enemies(wave)
                bullets = []
                game_state = "PLAYING"

        pygame.display.flip()
        clock.tick(60)

    # Reset camera mode on exit
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
