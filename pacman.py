# pyrefly: ignore [missing-import]
import pygame
import sys
import socket
import json
import threading
import random
import math

pygame.init()

# Screen 
WIDTH, HEIGHT = 600, 710
CELL_SIZE = 30
ROWS = 21
COLS = WIDTH // CELL_SIZE

# Colors 
BLACK       = (0, 0, 0)
WHITE       = (255, 255, 255)
YELLOW      = (255, 255, 0)
NEON_YELLOW = (255, 230, 50)
BLUE        = (0, 0, 255)
WALL_BLUE   = (30, 50, 180)
WALL_GLOW   = (60, 80, 220)
WALL_DARK   = (15, 25, 90)
RED         = (255, 0, 0)
PINK        = (255, 184, 255)
CYAN        = (0, 255, 255)
ORANGE      = (255, 184, 82)
NEON_GREEN  = (50, 255, 100)
NEON_PURPLE = (180, 80, 255)
GOLD        = (255, 215, 0)
DARK_BG     = (5, 5, 15)
FRIGHTENED_COLOR = (0, 0, 150)
FRIGHTENED_BLUE  = (20, 20, 200)

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Pacman - Neon Edition")
clock = pygame.time.Clock()

# Fonts 
try:
    font_tiny   = pygame.font.SysFont("courier", 14, bold=True)
    font_small  = pygame.font.SysFont("courier", 22, bold=True)
    font_medium = pygame.font.SysFont("courier", 32, bold=True)
    font_large  = pygame.font.SysFont("courier", 52, bold=True)
    font_huge   = pygame.font.SysFont("courier", 68, bold=True)
except:
    font_tiny   = pygame.font.Font(None, 14)
    font_small  = pygame.font.Font(None, 22)
    font_medium = pygame.font.Font(None, 32)
    font_large  = pygame.font.Font(None, 52)
    font_huge   = pygame.font.Font(None, 68)


current_ai_state = {"dir": "NONE", "action": False}

def udp_listener():
    global current_ai_state
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", 5005))
    sock.setblocking(False)
    while True:
        try:
            data, addr = sock.recvfrom(1024)
            current_ai_state = json.loads(data.decode('utf-8'))
        except BlockingIOError:
            pass
        except Exception as e:
            pass
        pygame.time.wait(5)

listener_thread = threading.Thread(target=udp_listener, daemon=True)
listener_thread.start()


MAZE = [
    "####################",
    "#*.......##.......*#",
    "#.##.###.##.###.##.#",
    "#..................#",
    "#.##.#.######.#.##.#",
    "#....#...##...#....#",
    "####.### ## ###.####",
    "   #.#        #.#   ",
    "####.# ##--## #.####",
    "       #    #       ",
    "####.# ###### #.####",
    "   #.#        #.#   ",
    "####.# ###### #.####",
    "#........##........#",
    "#.##.###.##.###.##.#",
    "#..#.....P......#..#",
    "##.#.#.######.#.#.##",
    "#....#...##...#....#",
    "#*######.##.######*#",
    "#..................#",
    "####################"
]

class PacParticle:
    def __init__(self, x, y, color, vx=0, vy=0, life=30, size=3):
        self.x = x
        self.y = y
        self.color = color
        self.vx = vx + (random.random() - 0.5) * 2
        self.vy = vy + (random.random() - 0.5) * 2
        self.life = life
        self.max_life = life
        self.size = size

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vx *= 0.95
        self.vy *= 0.95
        self.life -= 1
        return self.life > 0

    def draw(self, surface):
        alpha = self.life / self.max_life
        s = max(1, int(self.size * alpha))
        pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), s)


particles = []

def spawn_eat_particles(x, y, color=NEON_YELLOW):
    for _ in range(5):
        particles.append(PacParticle(x, y, color, life=15, size=2))

def spawn_ghost_eat_particles(x, y):
    for _ in range(12):
        particles.append(PacParticle(x, y, NEON_PURPLE, life=25, size=4))

def spawn_death_particles(x, y):
    for _ in range(20):
        particles.append(PacParticle(x, y, NEON_YELLOW, 
                                     vx=(random.random()-0.5)*6, 
                                     vy=(random.random()-0.5)*6, 
                                     life=40, size=5))

class Ghost:
    def __init__(self, x, y, color):
        self.start_x = x
        self.start_y = y
        self.x = x
        self.y = y
        self.grid_x = int(x) // CELL_SIZE
        self.grid_y = int(y) // CELL_SIZE
        self.dir_x = 0
        self.dir_y = 1
        self.speed = 2
        self.color = color
        self.radius = CELL_SIZE // 2 - 2
        self.mode = "SCATTER"
        self.frightened_timer = 0
        self.active = False

    def update(self, walls):
        if not self.active:
            self.y += self.dir_y * self.speed
            if self.y < self.start_y - 10: self.dir_y = 1
            elif self.y > self.start_y + 10: self.dir_y = -1
            return

        if self.mode == "FRIGHTENED":
            self.frightened_timer -= 1
            if self.frightened_timer <= 0:
                self.mode = "SCATTER"

        if self.grid_y >= 8 and 8 <= self.grid_x <= 11:
            door_left = 9 * CELL_SIZE + CELL_SIZE // 2
            door_right = 10 * CELL_SIZE + CELL_SIZE // 2
            
            target_x = self.x
            if self.x < door_left:
                target_x = door_left
            elif self.x > door_right:
                target_x = door_right
                
            if abs(self.x - target_x) > self.speed:
                self.x += self.speed if self.x < target_x else -self.speed
                self.dir_x, self.dir_y = (1 if self.x < target_x else -1), 0
            else:
                self.x = target_x
                self.y -= self.speed
                self.dir_x, self.dir_y = 0, -1
                
            self.grid_x = int(self.x) // CELL_SIZE
            self.grid_y = int(self.y) // CELL_SIZE
            return
                
        center_x = self.grid_x * CELL_SIZE + CELL_SIZE // 2
        center_y = self.grid_y * CELL_SIZE + CELL_SIZE // 2

        if abs(self.x - center_x) < self.speed and abs(self.y - center_y) < self.speed:
            valid_dirs = []
            for dx, dy in [(0,1), (0,-1), (1,0), (-1,0)]:
                if dx == -self.dir_x and dy == -self.dir_y and (self.dir_x!=0 or self.dir_y!=0):
                    continue
                if self.can_move(dx, dy, walls):
                    valid_dirs.append((dx, dy))
            
            if not valid_dirs:
                self.dir_x *= -1
                self.dir_y *= -1
            else:
                self.dir_x, self.dir_y = random.choice(valid_dirs)
            
            self.x = center_x
            self.y = center_y

        if self.mode == "FRIGHTENED" and pygame.time.get_ticks() % 2 == 0:
            pass
        else:
            self.x += self.dir_x * self.speed
            self.y += self.dir_y * self.speed
            
        self.grid_x = int(self.x) // CELL_SIZE
        self.grid_y = int(self.y) // CELL_SIZE
        
        if self.x < 0: self.x = WIDTH
        if self.x > WIDTH: self.x = 0

    def can_move(self, dx, dy, walls):
        next_grid_x = self.grid_x + dx
        next_grid_y = self.grid_y + dy
        if next_grid_x < 0 or next_grid_x >= COLS:
            return True
        return (next_grid_x, next_grid_y) not in walls

    def draw(self, surface):
        color = self.color
        is_frightened = self.mode == "FRIGHTENED"
        
        if is_frightened:
            color = FRIGHTENED_BLUE
            if self.frightened_timer < 120 and (self.frightened_timer // 10) % 2 == 0:
                color = WHITE

        r = self.radius
        x, y = int(self.x), int(self.y)
        
        # Ghost glow
        glow_surf = pygame.Surface((r*4, r*4), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*color, 30), (r*2, r*2), r*2)
        surface.blit(glow_surf, (x - r*2, y - r*2))
        
        # Body dome
        pygame.draw.circle(surface, color, (x, y - 2), r, draw_top_left=True, draw_top_right=True)
        pygame.draw.rect(surface, color, (x - r, y - 2, r*2, r + 2))
        
        # Wavy bottom tentacles
        time_offset = pygame.time.get_ticks() * 0.012
        pts = [(x - r, y + r)]
        for i in range(1, 6):
            dx = (r * 2) * (i / 5)
            dy = math.sin(time_offset + i * 1.5) * 3
            pts.append((x - r + dx, y + r + dy))
        pts.append((x + r, y - 2))
        pts.append((x - r, y - 2))
        pygame.draw.polygon(surface, color, pts)

        # Eyes
        eye_offset_x = self.dir_x * 2
        eye_offset_y = self.dir_y * 2
        
        if is_frightened:
            # Scared face
            pygame.draw.circle(surface, PINK, (x - 4, y - 2), 2)
            pygame.draw.circle(surface, PINK, (x + 4, y - 2), 2)
            pygame.draw.lines(surface, PINK, False, [
                (x - 5, y + 3), (x - 2, y + 1), (x, y + 3),
                (x + 2, y + 1), (x + 5, y + 3)
            ], 1)
        else:
            # Normal eyes with pupils
            pygame.draw.circle(surface, WHITE, (x - 4 + eye_offset_x, y - 3 + eye_offset_y), 4)
            pygame.draw.circle(surface, WHITE, (x + 4 + eye_offset_x, y - 3 + eye_offset_y), 4)
            pygame.draw.circle(surface, (10,10,40), (x - 4 + int(eye_offset_x*1.5), y - 3 + int(eye_offset_y*1.5)), 2)
            pygame.draw.circle(surface, (10,10,40), (x + 4 + int(eye_offset_x*1.5), y - 3 + int(eye_offset_y*1.5)), 2)
        
    def respawn(self):
        self.x = self.start_x
        self.y = self.start_y
        self.grid_x = int(self.x) // CELL_SIZE
        self.grid_y = int(self.y) // CELL_SIZE
        self.mode = "SCATTER"
        self.frightened_timer = 0
        self.active = False
        self.dir_x, self.dir_y = 0, 1

class Pacman:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.grid_x = x // CELL_SIZE
        self.grid_y = y // CELL_SIZE
        self.dir_x = 0
        self.dir_y = 0
        self.next_dir_x = 0
        self.next_dir_y = 0
        self.speed = 2
        self.radius = CELL_SIZE // 2 - 2

    def update(self, walls):
        center_x = self.grid_x * CELL_SIZE + CELL_SIZE // 2
        center_y = self.grid_y * CELL_SIZE + CELL_SIZE // 2

        if abs(self.x - center_x) < self.speed and abs(self.y - center_y) < self.speed:
            if self.can_move(self.next_dir_x, self.next_dir_y, walls):
                self.x = center_x
                self.y = center_y
                self.dir_x = self.next_dir_x
                self.dir_y = self.next_dir_y
            elif not self.can_move(self.dir_x, self.dir_y, walls):
                self.dir_x = 0
                self.dir_y = 0

        self.x += self.dir_x * self.speed
        self.y += self.dir_y * self.speed

        self.grid_x = int(self.x) // CELL_SIZE
        self.grid_y = int(self.y) // CELL_SIZE
        
        if self.x < 0: self.x = WIDTH
        if self.x > WIDTH: self.x = 0

    def can_move(self, dx, dy, walls):
        if dx == 0 and dy == 0:
            return True
        next_grid_x = self.grid_x + dx
        next_grid_y = self.grid_y + dy
        if next_grid_x < 0 or next_grid_x >= COLS:
            return True
        return (next_grid_x, next_grid_y) not in walls

    def draw(self, surface):
        t = pygame.time.get_ticks()
        x, y = int(self.x), int(self.y)
        r = self.radius
        
        # Glow effect
        glow_surf = pygame.Surface((r*4, r*4), pygame.SRCALPHA)
        glow_alpha = 25 + int(math.sin(t * 0.005) * 10)
        pygame.draw.circle(glow_surf, (*NEON_YELLOW, glow_alpha), (r*2, r*2), r*2)
        surface.blit(glow_surf, (x - r*2, y - r*2))
        
        # Mouth animation
        if self.dir_x == 0 and self.dir_y == 0:
            mouth_angle = 30
        else:
            mouth_angle = (math.sin(t * 0.02) + 1) / 2 * 45

        # Body
        pygame.draw.circle(surface, NEON_YELLOW, (x, y), r)
        
        # Mouth cutout
        base_angle = 0
        if self.dir_x == 1: base_angle = 0
        elif self.dir_x == -1: base_angle = 180
        elif self.dir_y == 1: base_angle = 90
        elif self.dir_y == -1: base_angle = 270
        elif self.next_dir_x == 1: base_angle = 0
        elif self.next_dir_x == -1: base_angle = 180
        elif self.next_dir_y == 1: base_angle = 90
        elif self.next_dir_y == -1: base_angle = 270

        angle_rad = math.radians(mouth_angle)
        angle_1 = math.radians(base_angle) - angle_rad
        angle_2 = math.radians(base_angle) + angle_rad
        
        p1 = (x, y)
        p2 = (x + r * 1.5 * math.cos(angle_1), y + r * 1.5 * math.sin(angle_1))
        p3 = (x + r * 1.5 * math.cos(angle_2), y + r * 1.5 * math.sin(angle_2))
        
        if mouth_angle > 2:
            pygame.draw.polygon(surface, DARK_BG, [p1, p2, p3])

        # Eye
        eye_x = x + int(math.cos(math.radians(base_angle - 40)) * r * 0.4)
        eye_y = y + int(math.sin(math.radians(base_angle - 40)) * r * 0.4)
        pygame.draw.circle(surface, DARK_BG, (eye_x, eye_y), 2)


def draw_neon_walls(surface, walls, t):
    for w in walls:
        wx, wy = w[0] * CELL_SIZE, w[1] * CELL_SIZE
        
        # Dark fill
        pygame.draw.rect(surface, WALL_DARK, (wx, wy, CELL_SIZE, CELL_SIZE))
        
        # Check which sides are exposed (adjacent to non-wall)
        for dx, dy in [(0,-1), (0,1), (-1,0), (1,0)]:
            nx, ny = w[0]+dx, w[1]+dy
            if (nx, ny) not in walls:
                # Draw glowing border on exposed side
                if dy == -1:  # top exposed
                    pygame.draw.line(surface, WALL_GLOW, (wx, wy), (wx+CELL_SIZE, wy), 2)
                elif dy == 1:  # bottom exposed
                    pygame.draw.line(surface, WALL_GLOW, (wx, wy+CELL_SIZE), (wx+CELL_SIZE, wy+CELL_SIZE), 2)
                elif dx == -1:  # left exposed
                    pygame.draw.line(surface, WALL_GLOW, (wx, wy), (wx, wy+CELL_SIZE), 2)
                elif dx == 1:  # right exposed
                    pygame.draw.line(surface, WALL_GLOW, (wx+CELL_SIZE, wy), (wx+CELL_SIZE, wy+CELL_SIZE), 2)


def draw_pellet(surface, x, y, t):
    px = x * CELL_SIZE + CELL_SIZE // 2
    py = y * CELL_SIZE + CELL_SIZE // 2
    # Glow
    glow_surf = pygame.Surface((12, 12), pygame.SRCALPHA)
    pygame.draw.circle(glow_surf, (255, 255, 200, 40), (6, 6), 6)
    surface.blit(glow_surf, (px - 6, py - 6))
    # Dot
    pygame.draw.circle(surface, (255, 255, 220), (px, py), 2)


def draw_power_pellet(surface, x, y, t):
    px = x * CELL_SIZE + CELL_SIZE // 2
    py = y * CELL_SIZE + CELL_SIZE // 2
    
    if (t // 250) % 2 == 0:
        pulse = 2 + math.sin(t * 0.008) * 2
        # Glow
        glow_surf = pygame.Surface((30, 30), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*NEON_YELLOW, 40), (15, 15), 15)
        surface.blit(glow_surf, (px - 15, py - 15))
        # Core
        pygame.draw.circle(surface, NEON_YELLOW, (px, py), int(6 + pulse))
        pygame.draw.circle(surface, (255, 255, 200), (px, py), int(3 + pulse * 0.5))


def draw_ghost_house(surface, t):
    gx = 8 * CELL_SIZE
    gy = 8 * CELL_SIZE
    gw = CELL_SIZE * 4
    
    # Pulsing gate
    alpha = 150 + int(math.sin(t * 0.003) * 50)
    gate_surf = pygame.Surface((gw, 4), pygame.SRCALPHA)
    gate_surf.fill((*PINK, alpha))
    surface.blit(gate_surf, (gx, gy))
    # Glow below gate
    glow_surf = pygame.Surface((gw, 8), pygame.SRCALPHA)
    glow_surf.fill((*PINK, 30))
    surface.blit(glow_surf, (gx, gy + 4))


def draw_hud(surface, score, lives_or_state=""):
    # HUD background
    hud_y = 21 * CELL_SIZE
    hud_rect = pygame.Rect(0, hud_y, WIDTH, HEIGHT - hud_y)
    pygame.draw.rect(surface, (8, 8, 20), hud_rect)
    pygame.draw.line(surface, WALL_GLOW, (0, hud_y), (WIDTH, hud_y), 1)
    
    # Score
    score_surf = font_medium.render(f"SCORE", True, (100, 100, 150))
    surface.blit(score_surf, (20, hud_y + 8))
    score_val = font_medium.render(f"{score}", True, GOLD)
    surface.blit(score_val, (20, hud_y + 32))
    
    # Controls hint (right side)
    hint = font_tiny.render("Fist=Move | Open=Action", True, (80, 80, 120))
    surface.blit(hint, (WIDTH - 260, hud_y + 42))


def draw_text_centered(surface, text, font, color, y_offset=0):
    text_surface = font.render(text, True, color)
    text_rect = text_surface.get_rect(center=(WIDTH // 2, HEIGHT // 2 + y_offset))
    surface.blit(text_surface, text_rect)


def draw_text_glow(surface, text, font, color, center_x, center_y):
    # Glow layer (blurred via larger text offset)
    glow_color = (color[0]//3, color[1]//3, color[2]//3)
    for dx, dy in [(-1,-1), (1,-1), (-1,1), (1,1), (0,-2), (0,2), (-2,0), (2,0)]:
        glow_surf = font.render(text, True, glow_color)
        glow_rect = glow_surf.get_rect(center=(center_x + dx, center_y + dy))
        surface.blit(glow_surf, glow_rect)
    
    # Main text
    text_surf = font.render(text, True, color)
    text_rect = text_surf.get_rect(center=(center_x, center_y))
    surface.blit(text_surf, text_rect)


def reset_game():
    pacman_walls = set()
    ghost_walls = set()
    pellets, power_pellets = set(), set()
    pacman = None
    ghosts = []

    for r in range(len(MAZE)):
        for c in range(len(MAZE[r])):
            if MAZE[r][c] == '#':
                pacman_walls.add((c, r))
                ghost_walls.add((c, r))
            elif MAZE[r][c] == '-':
                pacman_walls.add((c, r))
                ghost_walls.add((c, r))
            elif MAZE[r][c] == '.':
                pellets.add((c, r))
            elif MAZE[r][c] == '*':
                power_pellets.add((c, r))
            elif MAZE[r][c] == 'P':
                pacman = Pacman(c * CELL_SIZE + CELL_SIZE//2, r * CELL_SIZE + CELL_SIZE//2)

    ghost_colors = [RED, PINK, ORANGE, CYAN]
    # Tất cả ở hàng 9 (bên trong chuồng), cột 8, 9, 10, 11
    start_positions = [(9, 9), (10, 9), (8, 9), (11, 9)]
    for i in range(4):
        gx = start_positions[i][0] * CELL_SIZE + CELL_SIZE//2
        gy = start_positions[i][1] * CELL_SIZE + CELL_SIZE//2
        ghosts.append(Ghost(gx, gy, ghost_colors[i]))
    
    ghosts[0].active = True
    ghosts[0].dir_x, ghosts[0].dir_y = random.choice([(1,0), (-1,0)])

    return pacman_walls, ghost_walls, pellets, power_pellets, pacman, ghosts, 0


def main():
    try:
        mode_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        mode_sock.sendto(b"pacman", ("127.0.0.1", 5006))
        mode_sock.close()
    except:
        pass

    global particles
    running = True
    game_state = "START"
    
    pacman_walls, ghost_walls, pellets, power_pellets, pacman, ghosts, score = reset_game()
    last_ai_action = False
    death_timer = 0
    screen_shake = 0
    shake_offset = (0, 0)

    while running:
        t = pygame.time.get_ticks()
        ai_action = current_ai_state.get("action", False)
        ai_dir = current_ai_state.get("dir", "NONE")
        
        space_pressed = False
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                if event.key == pygame.K_SPACE:
                    space_pressed = True
                if game_state == "PLAYING":
                    if event.key == pygame.K_UP:
                        pacman.next_dir_x, pacman.next_dir_y = 0, -1
                    elif event.key == pygame.K_DOWN:
                        pacman.next_dir_x, pacman.next_dir_y = 0, 1
                    elif event.key == pygame.K_LEFT:
                        pacman.next_dir_x, pacman.next_dir_y = -1, 0
                    elif event.key == pygame.K_RIGHT:
                        pacman.next_dir_x, pacman.next_dir_y = 1, 0

        trigger_action = space_pressed or (ai_action and not last_ai_action)
        last_ai_action = ai_action

        # Render 
        render_surf = pygame.Surface((WIDTH, HEIGHT))
        render_surf.fill(DARK_BG)

        if game_state == "START":
            # Animated background dots
            for i in range(20):
                dx = int((t * 0.02 + i * 30) % WIDTH)
                dy = int((math.sin(t * 0.001 + i) + 1) * 0.5 * 400 + 100)
                pygame.draw.circle(render_surf, (20, 20, 50), (dx, dy), 3)
            
            # Title
            title_y = HEIGHT // 2 - 120 + int(math.sin(t * 0.002) * 8)
            draw_text_glow(render_surf, "PACMAN", font_huge, NEON_YELLOW, WIDTH//2, title_y)
            
            # Subtitle
            draw_text_glow(render_surf, "NEON EDITION", font_medium, NEON_GREEN, WIDTH//2, title_y + 60)
            
            # Blinking start text
            if (t // 500) % 2 == 0:
                draw_text_centered(render_surf, "OPEN HAND / PRESS SPACE", font_small, WHITE, 80)
                draw_text_centered(render_surf, "TO START", font_small, WHITE, 110)
            
            # Pacman icon
            pac_x = WIDTH // 2
            pac_y = title_y + 130
            pac_mouth = (math.sin(t * 0.015) + 1) / 2 * 40
            pygame.draw.circle(render_surf, NEON_YELLOW, (pac_x, pac_y), 20)
            if pac_mouth > 2:
                angle_rad = math.radians(pac_mouth)
                p1 = (pac_x, pac_y)
                p2 = (pac_x + 30 * math.cos(-angle_rad), pac_y + 30 * math.sin(-angle_rad))
                p3 = (pac_x + 30 * math.cos(angle_rad), pac_y + 30 * math.sin(angle_rad))
                pygame.draw.polygon(render_surf, DARK_BG, [p1, p2, p3])
            
            # Ghost icons
            colors = [RED, PINK, CYAN, ORANGE]
            for i, col in enumerate(colors):
                gx = WIDTH//2 - 60 + i * 40
                gy = pac_y + 50
                pygame.draw.circle(render_surf, col, (gx, gy - 2), 10, draw_top_left=True, draw_top_right=True)
                pygame.draw.rect(render_surf, col, (gx-10, gy-2, 20, 12))
                # Eyes
                pygame.draw.circle(render_surf, WHITE, (gx-3, gy-3), 3)
                pygame.draw.circle(render_surf, WHITE, (gx+3, gy-3), 3)
                pygame.draw.circle(render_surf, (10,10,40), (gx-3, gy-3), 1)
                pygame.draw.circle(render_surf, (10,10,40), (gx+3, gy-3), 1)
                
            if trigger_action:
                pacman_walls, ghost_walls, pellets, power_pellets, pacman, ghosts, score = reset_game()
                particles = []
                game_state = "PLAYING"

        elif game_state == "PLAYING":
            # AI Camera direction control
            if ai_dir == "UP":
                pacman.next_dir_x, pacman.next_dir_y = 0, -1
            elif ai_dir == "DOWN":
                pacman.next_dir_x, pacman.next_dir_y = 0, 1
            elif ai_dir == "LEFT":
                pacman.next_dir_x, pacman.next_dir_y = -1, 0
            elif ai_dir == "RIGHT":
                pacman.next_dir_x, pacman.next_dir_y = 1, 0

            pacman.update(pacman_walls)
            
            # Release ghosts based on score
            if not ghosts[0].active: ghosts[0].active = True
            if score >= 100 and not ghosts[1].active: ghosts[1].active = True
            if score >= 300 and not ghosts[2].active: ghosts[2].active = True
            if score >= 500 and not ghosts[3].active: ghosts[3].active = True

            for g in ghosts:
                g.update(ghost_walls)

            # Collision detection
            for g in ghosts:
                dist = math.sqrt((pacman.x - g.x)**2 + (pacman.y - g.y)**2)
                if dist < CELL_SIZE - 5: 
                    if g.mode == "FRIGHTENED":
                        spawn_ghost_eat_particles(g.x, g.y)
                        g.respawn()
                        score += 200
                    else:
                        spawn_death_particles(pacman.x, pacman.y)
                        screen_shake = 15
                        death_timer = 60
                        game_state = "DYING"

            # Eat pellets
            pac_grid = (pacman.grid_x, pacman.grid_y)
            if pac_grid in pellets:
                pellets.remove(pac_grid)
                score += 10
                spawn_eat_particles(
                    pac_grid[0] * CELL_SIZE + CELL_SIZE//2,
                    pac_grid[1] * CELL_SIZE + CELL_SIZE//2
                )
                
            if pac_grid in power_pellets:
                power_pellets.remove(pac_grid)
                score += 50
                spawn_eat_particles(
                    pac_grid[0] * CELL_SIZE + CELL_SIZE//2,
                    pac_grid[1] * CELL_SIZE + CELL_SIZE//2,
                    NEON_PURPLE
                )
                for g in ghosts:
                    if g.active:
                        g.mode = "FRIGHTENED"
                        g.frightened_timer = 60 * 10

            # --- Draw gameplay ---
            draw_neon_walls(render_surf, pacman_walls, t)
            draw_ghost_house(render_surf, t)
            
            for p in pellets:
                draw_pellet(render_surf, p[0], p[1], t)
            for pp in power_pellets:
                draw_power_pellet(render_surf, pp[0], pp[1], t)

            pacman.draw(render_surf)
            for g in ghosts:
                g.draw(render_surf)

            # Particles
            particles = [p for p in particles if p.update()]
            for p in particles:
                p.draw(render_surf)

            # HUD
            draw_hud(render_surf, score)
            
            # Win check
            if not pellets and not power_pellets:
                game_state = "VICTORY"

        elif game_state == "DYING":
            death_timer -= 1
            
            # Still draw the map
            draw_neon_walls(render_surf, pacman_walls, t)
            draw_ghost_house(render_surf, t)
            for p_pos in pellets:
                draw_pellet(render_surf, p_pos[0], p_pos[1], t)
            for pp in power_pellets:
                draw_power_pellet(render_surf, pp[0], pp[1], t)
            for g in ghosts:
                g.draw(render_surf)
            
            # Death animation - shrinking pacman
            if death_timer > 0:
                shrink = max(0, int(pacman.radius * (death_timer / 60)))
                if shrink > 0:
                    pygame.draw.circle(render_surf, NEON_YELLOW, (int(pacman.x), int(pacman.y)), shrink)
            
            particles = [p for p in particles if p.update()]
            for p in particles:
                p.draw(render_surf)
            
            draw_hud(render_surf, score)
            
            if death_timer <= 0:
                game_state = "GAME_OVER"

        elif game_state == "GAME_OVER":
            # Dark overlay with animated dots
            for i in range(15):
                dx = int((t * 0.01 + i * 40) % WIDTH)
                dy = int((math.sin(t * 0.001 + i * 0.5) + 1) * 0.5 * HEIGHT)
                pygame.draw.circle(render_surf, (15, 15, 35), (dx, dy), 4)
            
            go_y = HEIGHT // 2 - 80
            draw_text_glow(render_surf, "GAME OVER", font_huge, RED, WIDTH//2, go_y)
            draw_text_glow(render_surf, f"SCORE: {score}", font_large, GOLD, WIDTH//2, go_y + 70)
            
            if (t // 500) % 2 == 0:
                draw_text_centered(render_surf, "OPEN HAND / SPACE", font_small, NEON_YELLOW, 130)
                
            if trigger_action:
                pacman_walls, ghost_walls, pellets, power_pellets, pacman, ghosts, score = reset_game()
                particles = []
                game_state = "PLAYING"
                
        elif game_state == "VICTORY":
            for i in range(15):
                dx = int((t * 0.02 + i * 40) % WIDTH)
                dy = int((math.sin(t * 0.002 + i) + 1) * 0.5 * HEIGHT)
                color = [NEON_YELLOW, NEON_GREEN, CYAN, NEON_PURPLE][i % 4]
                pygame.draw.circle(render_surf, color, (dx, dy), 5)
            
            win_y = HEIGHT // 2 - 80
            draw_text_glow(render_surf, "YOU WIN!", font_huge, NEON_GREEN, WIDTH//2, win_y)
            draw_text_glow(render_surf, f"SCORE: {score}", font_large, GOLD, WIDTH//2, win_y + 70)
            
            if (t // 500) % 2 == 0:
                draw_text_centered(render_surf, "OPEN HAND / SPACE", font_small, CYAN, 130)
                
            if trigger_action:
                pacman_walls, ghost_walls, pellets, power_pellets, pacman, ghosts, score = reset_game()
                particles = []
                game_state = "PLAYING"

        # Screen shake
        if screen_shake > 0:
            screen_shake -= 1
            shake_offset = (random.randint(-3, 3), random.randint(-3, 3))
        else:
            shake_offset = (0, 0)

        screen.fill(BLACK)
        screen.blit(render_surf, shake_offset)
        pygame.display.flip()
        clock.tick(60)

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
