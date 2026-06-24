# pyrefly: ignore [missing-import]
import pygame
import sys
import socket
import json
import threading
import math
import random
from collections import deque

pygame.init()

#  SCREEN & CONSTANTS
WIDTH, HEIGHT = 800, 650
ARENA_W, ARENA_H = 800, 600
HUD_H = HEIGHT - ARENA_H
CELL = 40
ROWS = ARENA_H // CELL
COLS = ARENA_W // CELL

#  NEON COLOR PALETTE
DARK_BG      = (5, 5, 15)
BLACK        = (0, 0, 0)
WHITE        = (240, 240, 245)

# Wall colors
WALL_DARK    = (15, 25, 55)
WALL_CORE    = (25, 40, 90)
WALL_GLOW    = (50, 80, 200)
WALL_EDGE    = (70, 110, 240)

# Player (neon green/cyan)
PLAYER_BODY  = (0, 230, 120)
PLAYER_GLOW  = (0, 255, 140)
PLAYER_DARK  = (0, 150, 80)
PLAYER_TURRET = (180, 255, 220)

# Enemy (neon red/orange)
ENEMY_BODY   = (230, 50, 60)
ENEMY_GLOW   = (255, 70, 80)
ENEMY_DARK   = (160, 30, 40)
ENEMY_TURRET = (255, 180, 160)

# Effects
BULLET_CORE  = (255, 255, 100)
BULLET_GLOW  = (255, 200, 50)
NEON_YELLOW  = (255, 230, 50)
NEON_PURPLE  = (160, 80, 255)
NEON_CYAN    = (0, 230, 255)
NEON_ORANGE  = (255, 160, 40)
GOLD         = (255, 215, 0)
EXPLOSION_1  = (255, 255, 150)
EXPLOSION_2  = (255, 180, 50)
EXPLOSION_3  = (255, 80, 30)
EXPLOSION_4  = (150, 30, 10)

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Tank Trouble - Neon Edition")
clock = pygame.time.Clock()

#  FONTS
try:
    font_huge   = pygame.font.SysFont('courier', 64, bold=True)
    font_large  = pygame.font.SysFont('courier', 48, bold=True)
    font_medium = pygame.font.SysFont('courier', 28, bold=True)
    font_small  = pygame.font.SysFont('courier', 18, bold=True)
    font_tiny   = pygame.font.SysFont('courier', 14, bold=True)
except:
    font_huge   = pygame.font.Font(None, 64)
    font_large  = pygame.font.Font(None, 48)
    font_medium = pygame.font.Font(None, 28)
    font_small  = pygame.font.Font(None, 18)
    font_tiny   = pygame.font.Font(None, 14)


#  UDP LISTENER (Camera)
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


#  PARTICLE SYSTEM
class Particle:
    __slots__ = ['x', 'y', 'vx', 'vy', 'color', 'size', 'life', 'max_life', 'gravity', 'friction']
    
    def __init__(self, x, y, vx, vy, color, size=3, life=1.0, gravity=0, friction=0.98):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.size = size
        self.life = life
        self.max_life = life
        self.gravity = gravity
        self.friction = friction

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += self.gravity
        self.vx *= self.friction
        self.vy *= self.friction
        self.life -= 0.03
        return self.life > 0

    def draw(self, surface):
        alpha = self.life / self.max_life
        s = max(1, int(self.size * alpha))
        pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), s)


def spawn_explosion(particles, x, y, count=25):
    """Spawn a big tank explosion"""
    for _ in range(count):
        angle = random.random() * math.pi * 2
        speed = random.random() * 5 + 1
        color = random.choice([EXPLOSION_1, EXPLOSION_2, EXPLOSION_3, NEON_ORANGE, NEON_YELLOW])
        particles.append(Particle(
            x, y,
            math.cos(angle) * speed,
            math.sin(angle) * speed,
            color, random.uniform(2, 6), random.uniform(0.6, 1.2),
            gravity=0.05, friction=0.96
        ))

def spawn_bullet_spark(particles, x, y, count=8):
    """Spark when bullet bounces off wall"""
    for _ in range(count):
        angle = random.random() * math.pi * 2
        speed = random.random() * 3 + 1
        color = random.choice([BULLET_CORE, BULLET_GLOW, WHITE])
        particles.append(Particle(
            x, y,
            math.cos(angle) * speed,
            math.sin(angle) * speed,
            color, random.uniform(1, 3), random.uniform(0.2, 0.5),
            friction=0.92
        ))

def spawn_exhaust(particles, x, y, angle_deg):
    """Tank exhaust when moving"""
    rad = math.radians(angle_deg + 180)  # Behind tank
    for _ in range(2):
        spread = (random.random() - 0.5) * 0.8
        speed = random.random() * 1.5 + 0.5
        particles.append(Particle(
            x + math.cos(rad) * 12,
            y - math.sin(rad) * 12,
            math.cos(rad + spread) * speed,
            -math.sin(rad + spread) * speed,
            random.choice([(80, 80, 100), (60, 60, 80), (100, 100, 120)]),
            random.uniform(1.5, 3), random.uniform(0.2, 0.4),
            friction=0.95
        ))

def spawn_muzzle_flash(particles, x, y, angle_deg, color):
    """Flash when tank shoots"""
    rad = math.radians(angle_deg)
    for _ in range(6):
        spread = (random.random() - 0.5) * 0.6
        speed = random.random() * 4 + 2
        particles.append(Particle(
            x, y,
            math.cos(rad + spread) * speed,
            -math.sin(rad + spread) * speed,
            random.choice([color, WHITE, NEON_YELLOW]),
            random.uniform(2, 4), random.uniform(0.15, 0.35),
            friction=0.9
        ))


#  MAZE BUILDER
def build_maze(extra_walls=0):
    """Build maze with wall rects. extra_walls adds random internal walls per wave."""
    walls = []
    T = 10  # Wall thickness

    # Outer boundaries
    walls.append(pygame.Rect(0, 0, ARENA_W, T))
    walls.append(pygame.Rect(0, ARENA_H - T, ARENA_W, T))
    walls.append(pygame.Rect(0, 0, T, ARENA_H))
    walls.append(pygame.Rect(ARENA_W - T, 0, T, ARENA_H))

    # Core internal walls (always present)
    # Vertical walls
    walls.append(pygame.Rect(160, 120, T, 200))
    walls.append(pygame.Rect(160, 400, T, 120))
    walls.append(pygame.Rect(320, 0, T, 160))
    walls.append(pygame.Rect(320, 280, T, 140))
    walls.append(pygame.Rect(480, 160, T, 200))
    walls.append(pygame.Rect(480, 440, T, 160))
    walls.append(pygame.Rect(640, 0, T, 120))
    walls.append(pygame.Rect(640, 240, T, 200))

    # Horizontal walls
    walls.append(pygame.Rect(0, 200, 80, T))
    walls.append(pygame.Rect(160, 320, 160, T))
    walls.append(pygame.Rect(80, 440, 80, T))
    walls.append(pygame.Rect(320, 160, 160, T))
    walls.append(pygame.Rect(480, 440, 160, T))
    walls.append(pygame.Rect(640, 120, 160, T))
    walls.append(pygame.Rect(560, 520, 80, T))

    # Extra random walls for higher waves
    extra_options = [
        pygame.Rect(240, 80, T, 80),
        pygame.Rect(400, 400, 80, T),
        pygame.Rect(560, 320, T, 120),
        pygame.Rect(80, 320, 80, T),
        pygame.Rect(720, 400, T, 120),
        pygame.Rect(240, 520, 80, T),
        pygame.Rect(400, 80, T, 80),
        pygame.Rect(560, 160, 80, T),
    ]
    random.shuffle(extra_options)
    for i in range(min(extra_walls, len(extra_options))):
        walls.append(extra_options[i])

    return walls


#  WALL GRID (for pathfinding)
def build_nav_grid(walls):
    """Create a grid for BFS pathfinding. True = passable."""
    grid = [[True] * COLS for _ in range(ROWS)]
    margin = 12  # Tank half-size buffer
    for r in range(ROWS):
        for c in range(COLS):
            cx = c * CELL + CELL // 2
            cy = r * CELL + CELL // 2
            test_rect = pygame.Rect(cx - margin, cy - margin, margin * 2, margin * 2)
            for w in walls:
                if w.colliderect(test_rect):
                    grid[r][c] = False
                    break
    return grid


def bfs_path(grid, start_cell, end_cell):
    """BFS from start_cell (col, row) to end_cell. Returns list of (col, row) cells."""
    sc, sr = start_cell
    ec, er = end_cell
    if not (0 <= sr < ROWS and 0 <= sc < COLS and 0 <= er < ROWS and 0 <= ec < COLS):
        return []
    if not grid[sr][sc] or not grid[er][ec]:
        return []

    visited = set()
    visited.add((sc, sr))
    queue = deque()
    queue.append((sc, sr, []))

    while queue:
        cx, cy, path = queue.popleft()
        if cx == ec and cy == er:
            return path + [(cx, cy)]

        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < COLS and 0 <= ny < ROWS and (nx, ny) not in visited and grid[ny][nx]:
                visited.add((nx, ny))
                queue.append((nx, ny, path + [(cx, cy)]))

    return []


def line_of_sight(x1, y1, x2, y2, walls):
    """Raycast from (x1,y1) to (x2,y2). Returns True if no wall blocks the path."""
    dist = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
    if dist < 1:
        return True
    steps = int(dist / 5) + 1
    dx = (x2 - x1) / steps
    dy = (y2 - y1) / steps
    for i in range(steps + 1):
        px = x1 + dx * i
        py = y1 + dy * i
        point_rect = pygame.Rect(px - 2, py - 2, 4, 4)
        for w in walls:
            if w.colliderect(point_rect):
                return False
    return True


#  BULLET
class Bullet:
    def __init__(self, x, y, angle, owner, color):
        self.x = x
        self.y = y
        self.angle = angle
        self.speed = 3.5
        self.radius = 4
        self.bounces = 0
        self.max_bounces = 4
        self.owner = owner
        self.active = True
        self.color = color
        self.trail = []  # Trail positions

        rad = math.radians(self.angle)
        self.dx = math.cos(rad) * self.speed
        self.dy = -math.sin(rad) * self.speed

    def update(self, walls, particles):
        if not self.active:
            return

        # Save trail
        self.trail.append((self.x, self.y))
        if len(self.trail) > 12:
            self.trail.pop(0)

        nx = self.x + self.dx
        ny = self.y + self.dy

        rect = pygame.Rect(nx - self.radius, ny - self.radius, self.radius * 2, self.radius * 2)
        hit_wall = None
        for w in walls:
            if w.colliderect(rect):
                hit_wall = w
                break

        if hit_wall:
            self.bounces += 1
            if self.bounces > self.max_bounces:
                self.active = False
                spawn_bullet_spark(particles, self.x, self.y, 5)
                return

            # Bounce
            overlap_left = rect.right - hit_wall.left
            overlap_right = hit_wall.right - rect.left
            overlap_top = rect.bottom - hit_wall.top
            overlap_bottom = hit_wall.bottom - rect.top
            min_overlap = min(overlap_left, overlap_right, overlap_top, overlap_bottom)

            if min_overlap == overlap_left or min_overlap == overlap_right:
                self.dx *= -1
                self.x += self.dx * 2
            else:
                self.dy *= -1
                self.y += self.dy * 2

            # Spark on bounce
            spawn_bullet_spark(particles, self.x, self.y, 6)
        else:
            self.x = nx
            self.y = ny

    def draw(self, surface):
        if not self.active:
            return

        # Trail
        for i, (tx, ty) in enumerate(self.trail):
            alpha_f = (i + 1) / len(self.trail)
            s = max(1, int(self.radius * alpha_f * 0.7))
            r = int(self.color[0] * alpha_f)
            g = int(self.color[1] * alpha_f)
            b = int(self.color[2] * alpha_f)
            pygame.draw.circle(surface, (r, g, b), (int(tx), int(ty)), s)

        # Glow
        glow_surf = pygame.Surface((24, 24), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*self.color, 60), (12, 12), 12)
        surface.blit(glow_surf, (int(self.x) - 12, int(self.y) - 12))

        # Core
        pygame.draw.circle(surface, BULLET_CORE, (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(surface, WHITE, (int(self.x), int(self.y)), max(1, self.radius - 2))


#  TANK
class Tank:
    def __init__(self, x, y, is_player=False):
        self.x = x
        self.y = y
        self.is_player = is_player
        self.angle = random.uniform(0, 360)
        self.speed = 2.2
        self.rot_speed = 2.5
        self.size = 20
        self.cooldown = 0
        self.alive = True
        self.death_timer = 0  # For death animation

        # Colors
        if is_player:
            self.body_color = PLAYER_BODY
            self.glow_color = PLAYER_GLOW
            self.dark_color = PLAYER_DARK
            self.turret_color = PLAYER_TURRET
            self.bullet_color = PLAYER_GLOW
        else:
            self.body_color = ENEMY_BODY
            self.glow_color = ENEMY_GLOW
            self.dark_color = ENEMY_DARK
            self.turret_color = ENEMY_TURRET
            self.bullet_color = ENEMY_GLOW

        # Enemy AI state
        self.ai_path = []
        self.ai_path_timer = 0
        self.ai_target_angle = self.angle
        self.ai_state = "PATROL"
        self.ai_state_timer = 0
        self.ai_shoot_delay = 0
        self.ai_accuracy = 0.85  # How accurate the aim is (1.0 = perfect)
        self.ai_reaction = 30    # Frames before reacting
        self.ai_patrol_target = None

        # Tread animation
        self.tread_offset = 0

    def _try_move(self, dx, dy, walls):
        """Try to move by (dx, dy), sliding along walls."""
        nx = self.x + dx
        rect_x = pygame.Rect(nx - self.size // 2, self.y - self.size // 2, self.size, self.size)
        if not any(w.colliderect(rect_x) for w in walls):
            self.x = nx

        ny = self.y + dy
        rect_y = pygame.Rect(self.x - self.size // 2, ny - self.size // 2, self.size, self.size)
        if not any(w.colliderect(rect_y) for w in walls):
            self.y = ny

    def _angle_diff(self, target_angle):
        """Shortest angle difference from self.angle to target_angle."""
        diff = (target_angle - self.angle + 180) % 360 - 180
        return diff

    def _rotate_towards(self, target_angle, speed):
        """Smoothly rotate towards target angle."""
        diff = self._angle_diff(target_angle)
        if abs(diff) < speed:
            self.angle = target_angle
        elif diff > 0:
            self.angle = (self.angle + speed) % 360
        else:
            self.angle = (self.angle - speed) % 360

    def update_player(self, gesture, walls, bullets, particles):
        """Player update with gesture controls."""
        if self.cooldown > 0:
            self.cooldown -= 1

        moved = False
        if gesture == "FIST":
            self.angle = (self.angle + self.rot_speed) % 360
        elif gesture == "OPEN":
            rad = math.radians(self.angle)
            self._try_move(math.cos(rad) * self.speed, -math.sin(rad) * self.speed, walls)
            moved = True
        elif gesture == "POINT":
            if self.cooldown <= 0:
                self.shoot(bullets, particles)
                self.cooldown = 25

        if moved:
            self.tread_offset = (self.tread_offset + 1) % 4
            spawn_exhaust(particles, self.x, self.y, self.angle)

    def update_ai(self, walls, bullets, particles, target, nav_grid, wave):
        if self.cooldown > 0:
            self.cooldown -= 1

        if not target or not target.alive:
            return

        # Difficulty scaling 
        base_speed = 1.4
        self.speed = min(2.5, base_speed + wave * 0.12)
        self.ai_accuracy = min(0.97, 0.78 + wave * 0.025)
        self.ai_reaction = max(8, 35 - wave * 3)
        shoot_cooldown = max(30, 70 - wave * 5)

        dist_to_player = math.sqrt((target.x - self.x) ** 2 + (target.y - self.y) ** 2)
        has_los = line_of_sight(self.x, self.y, target.x, target.y, walls)

        # Check for incoming bullets (dodge) 
        dodge_dir = self._check_dodge(bullets)

        self.ai_state_timer -= 1

        if dodge_dir != 0:
            # DODGE: move perpendicular to incoming bullet
            dodge_angle = self.angle + 90 * dodge_dir
            rad = math.radians(dodge_angle)
            self._try_move(math.cos(rad) * self.speed * 1.3, -math.sin(rad) * self.speed * 1.3, walls)
            spawn_exhaust(particles, self.x, self.y, self.angle)
            self.tread_offset = (self.tread_offset + 1) % 4
            return

        if has_los and dist_to_player < 350:
            #  CAN SEE PLAYER: Aim and shoot 
            target_angle = math.degrees(math.atan2(-(target.y - self.y), target.x - self.x)) % 360

            # Add inaccuracy
            error = (1.0 - self.ai_accuracy) * 25
            target_angle += random.uniform(-error, error)

            self._rotate_towards(target_angle, self.rot_speed * 1.2)

            angle_diff = abs(self._angle_diff(target_angle))

            if angle_diff < 12 and self.cooldown <= 0:
                self.ai_shoot_delay += 1
                if self.ai_shoot_delay >= max(5, self.ai_reaction // 3):
                    self.shoot(bullets, particles)
                    self.cooldown = shoot_cooldown
                    self.ai_shoot_delay = 0
            else:
                self.ai_shoot_delay = 0

            # Strafe or approach
            if dist_to_player > 150:
                rad = math.radians(self.angle)
                self._try_move(math.cos(rad) * self.speed * 0.6, -math.sin(rad) * self.speed * 0.6, walls)
                spawn_exhaust(particles, self.x, self.y, self.angle)
                self.tread_offset = (self.tread_offset + 1) % 4
            elif dist_to_player < 80:
                # Too close, back up
                rad = math.radians(self.angle + 180)
                self._try_move(math.cos(rad) * self.speed * 0.5, -math.sin(rad) * self.speed * 0.5, walls)

        else:
            #  CAN'T SEE PLAYER: Pathfind towards them 
            self.ai_shoot_delay = 0
            self.ai_path_timer -= 1

            if self.ai_path_timer <= 0 or not self.ai_path:
                # Recalculate path
                my_cell = (int(self.x) // CELL, int(self.y) // CELL)
                target_cell = (int(target.x) // CELL, int(target.y) // CELL)
                self.ai_path = bfs_path(nav_grid, my_cell, target_cell)
                self.ai_path_timer = random.randint(20, 40)

            if self.ai_path:
                # Remove reached waypoints
                while self.ai_path:
                    wp = self.ai_path[0]
                    wp_x = wp[0] * CELL + CELL // 2
                    wp_y = wp[1] * CELL + CELL // 2
                    if math.sqrt((self.x - wp_x) ** 2 + (self.y - wp_y) ** 2) < CELL * 0.6:
                        self.ai_path.pop(0)
                    else:
                        break

                if self.ai_path:
                    wp = self.ai_path[0]
                    wp_x = wp[0] * CELL + CELL // 2
                    wp_y = wp[1] * CELL + CELL // 2

                    target_angle = math.degrees(math.atan2(-(wp_y - self.y), wp_x - self.x)) % 360
                    self._rotate_towards(target_angle, self.rot_speed * 1.5)

                    angle_diff = abs(self._angle_diff(target_angle))
                    if angle_diff < 40:
                        rad = math.radians(self.angle)
                        self._try_move(math.cos(rad) * self.speed, -math.sin(rad) * self.speed, walls)
                        spawn_exhaust(particles, self.x, self.y, self.angle)
                        self.tread_offset = (self.tread_offset + 1) % 4
            else:
                # No path found: random patrol
                if self.ai_state_timer <= 0:
                    self.ai_state = random.choice(["ROTATE", "MOVE"])
                    self.ai_state_timer = random.randint(30, 70)
                    if self.ai_state == "ROTATE":
                        self.ai_target_angle = random.uniform(0, 360)

                if self.ai_state == "ROTATE":
                    self._rotate_towards(self.ai_target_angle, self.rot_speed)
                elif self.ai_state == "MOVE":
                    rad = math.radians(self.angle)
                    old_x, old_y = self.x, self.y
                    self._try_move(math.cos(rad) * self.speed * 0.7, -math.sin(rad) * self.speed * 0.7, walls)
                    if abs(self.x - old_x) < 0.1 and abs(self.y - old_y) < 0.1:
                        self.ai_state = "ROTATE"
                        self.ai_target_angle = (self.angle + random.choice([90, -90, 180])) % 360
                        self.ai_state_timer = 15

    def _check_dodge(self, bullets):
        """Check if any bullet is heading towards us. Returns dodge direction (-1, 0, 1)."""
        for b in bullets:
            if not b.active:
                continue
            # Only dodge opponent bullets
            if self.is_player and b.owner == "player":
                continue
            if not self.is_player and b.owner == "enemy":
                continue

            # Distance to bullet
            dist = math.sqrt((b.x - self.x) ** 2 + (b.y - self.y) ** 2)
            if dist > 150:
                continue

            # Check if bullet is heading towards us
            # Project bullet velocity towards tank
            to_tank_x = self.x - b.x
            to_tank_y = self.y - b.y
            dot = b.dx * to_tank_x + b.dy * to_tank_y
            if dot <= 0:
                continue  # Bullet moving away

            # Perpendicular distance
            bullet_speed = math.sqrt(b.dx ** 2 + b.dy ** 2)
            if bullet_speed < 0.1:
                continue
            cross = abs(b.dx * to_tank_y - b.dy * to_tank_x) / bullet_speed
            if cross < self.size * 2:
                # Dodge! Choose direction perpendicular to bullet path
                perp = b.dx * (self.y - b.y) - b.dy * (self.x - b.x)
                return 1 if perp > 0 else -1

        return 0

    def shoot(self, bullets, particles):
        rad = math.radians(self.angle)
        bx = self.x + math.cos(rad) * (self.size + 4)
        by = self.y - math.sin(rad) * (self.size + 4)
        owner = "player" if self.is_player else "enemy"
        bullets.append(Bullet(bx, by, self.angle, owner, self.bullet_color))
        spawn_muzzle_flash(particles, bx, by, self.angle, self.glow_color)

    def draw(self, surface, t):
        if not self.alive:
            return

        x, y = int(self.x), int(self.y)
        s = self.size

        # GLOW 
        glow_pulse = 20 + int(math.sin(t * 0.004) * 8)
        glow_surf = pygame.Surface((s * 4, s * 4), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*self.glow_color, glow_pulse), (s * 2, s * 2), s * 2)
        surface.blit(glow_surf, (x - s * 2, y - s * 2))

        # BODY 
        body_surf = pygame.Surface((s * 2 + 4, s * 2 + 4), pygame.SRCALPHA)
        body_center = (s + 2, s + 2)

        # Treads (two rectangles on sides)
        rad = math.radians(self.angle)
        perp_x = math.sin(rad)
        perp_y = math.cos(rad)
        for side in [-1, 1]:
            tx = body_center[0] + perp_x * (s * 0.7) * side
            ty = body_center[1] + perp_y * (s * 0.7) * side
            tread_surf = pygame.Surface((s * 1.2, 6), pygame.SRCALPHA)
            tread_surf.fill(self.dark_color)
            # Tread marks
            for i in range(0, int(s * 1.2), 4):
                off = (i + self.tread_offset * 2) % 8
                if off < 4:
                    pygame.draw.line(tread_surf, (*self.body_color,), (i, 0), (i, 5), 1)
            rotated_tread = pygame.transform.rotate(tread_surf, self.angle)
            tread_rect = rotated_tread.get_rect(center=(tx, ty))
            body_surf.blit(rotated_tread, tread_rect)

        # Main body rectangle
        hull = pygame.Surface((s * 1.4, s * 1.4), pygame.SRCALPHA)
        # Gradient-ish fill
        pygame.draw.rect(hull, self.body_color, (0, 0, s * 1.4, s * 1.4), border_radius=4)
        # Inner highlight
        pygame.draw.rect(hull, self.glow_color, (3, 3, s * 1.4 - 6, s * 1.4 - 6), border_radius=3, width=1)
        rotated_hull = pygame.transform.rotate(hull, self.angle)
        hull_rect = rotated_hull.get_rect(center=body_center)
        body_surf.blit(rotated_hull, hull_rect)

        # Turret circle
        pygame.draw.circle(body_surf, self.dark_color, body_center, int(s * 0.4))
        pygame.draw.circle(body_surf, self.body_color, body_center, int(s * 0.35))
        # Turret highlight
        pygame.draw.circle(body_surf, self.glow_color, 
                          (body_center[0] - 1, body_center[1] - 1), int(s * 0.15))

        surface.blit(body_surf, (x - s - 2, y - s - 2))

        # === BARREL ===
        barrel_len = s * 1.3
        end_x = x + math.cos(rad) * barrel_len
        end_y = y - math.sin(rad) * barrel_len

        # Barrel shadow
        pygame.draw.line(surface, self.dark_color, (x, y), (end_x, end_y), 6)
        # Barrel main
        pygame.draw.line(surface, self.turret_color, (x, y), (end_x, end_y), 4)
        # Barrel tip glow
        pygame.draw.circle(surface, self.glow_color, (int(end_x), int(end_y)), 3)


#  RENDERING HELPERS
def draw_neon_walls(surface, walls, t):
    """Draw walls with neon glow edges."""
    for w in walls:
        # Dark fill
        pygame.draw.rect(surface, WALL_CORE, w)

        # Subtle inner gradient
        inner = w.inflate(-4, -4)
        if inner.width > 0 and inner.height > 0:
            pygame.draw.rect(surface, WALL_DARK, inner)

    # Glow edges (draw on top)
    for w in walls:
        # Check exposed sides
        for w2 in walls:
            if w2 is w:
                continue

        # Draw glow on all edges
        pulse = 0.7 + math.sin(t * 0.002) * 0.3
        edge_color = (
            int(WALL_EDGE[0] * pulse),
            int(WALL_EDGE[1] * pulse),
            int(WALL_EDGE[2] * pulse),
        )

        # Top
        pygame.draw.line(surface, edge_color, (w.left, w.top), (w.right, w.top), 1)
        # Bottom
        pygame.draw.line(surface, edge_color, (w.left, w.bottom - 1), (w.right, w.bottom - 1), 1)
        # Left
        pygame.draw.line(surface, edge_color, (w.left, w.top), (w.left, w.bottom), 1)
        # Right
        pygame.draw.line(surface, edge_color, (w.right - 1, w.top), (w.right - 1, w.bottom), 1)


def draw_floor_grid(surface, t):
    """Subtle grid pattern on the arena floor."""
    alpha_surf = pygame.Surface((ARENA_W, ARENA_H), pygame.SRCALPHA)
    pulse = int(10 + math.sin(t * 0.001) * 5)
    color = (WALL_GLOW[0], WALL_GLOW[1], WALL_GLOW[2], pulse)

    for x in range(0, ARENA_W, CELL):
        pygame.draw.line(alpha_surf, color, (x, 0), (x, ARENA_H), 1)
    for y in range(0, ARENA_H, CELL):
        pygame.draw.line(alpha_surf, color, (0, y), (ARENA_W, y), 1)

    surface.blit(alpha_surf, (0, 0))


def draw_text_glow(surface, text, font, color, cx, cy):
    """Draw text with a glow effect."""
    glow_color = (color[0] // 3, color[1] // 3, color[2] // 3)
    for dx, dy in [(-1, -1), (1, -1), (-1, 1), (1, 1), (0, -2), (0, 2), (-2, 0), (2, 0)]:
        glow_surf = font.render(text, True, glow_color)
        glow_rect = glow_surf.get_rect(center=(cx + dx, cy + dy))
        surface.blit(glow_surf, glow_rect)

    text_surf = font.render(text, True, color)
    text_rect = text_surf.get_rect(center=(cx, cy))
    surface.blit(text_surf, text_rect)


def draw_hud(surface, score, wave, gesture, t):
    """Draw the HUD bar at the bottom."""
    hud_y = ARENA_H
    hud_rect = pygame.Rect(0, hud_y, WIDTH, HUD_H)
    pygame.draw.rect(surface, (8, 8, 20), hud_rect)
    pygame.draw.line(surface, WALL_GLOW, (0, hud_y), (WIDTH, hud_y), 2)

    # Score
    score_label = font_small.render("SCORE", True, (80, 100, 150))
    surface.blit(score_label, (15, hud_y + 5))
    score_val = font_medium.render(str(score), True, GOLD)
    surface.blit(score_val, (15, hud_y + 22))

    # Wave
    wave_label = font_small.render("WAVE", True, (80, 100, 150))
    surface.blit(wave_label, (180, hud_y + 5))
    wave_val = font_medium.render(str(wave), True, NEON_CYAN)
    surface.blit(wave_val, (180, hud_y + 22))

    # Gesture indicator
    gest_label = font_small.render("GESTURE", True, (80, 100, 150))
    surface.blit(gest_label, (WIDTH - 180, hud_y + 5))
    gest_color = PLAYER_GLOW if gesture != "NONE" else (60, 60, 80)
    gest_val = font_medium.render(gesture, True, gest_color)
    surface.blit(gest_val, (WIDTH - 180, hud_y + 22))

    # Controls hint
    hint = font_tiny.render("FIST=Rotate  OPEN=Move  POINT=Shoot", True, (50, 55, 80))
    surface.blit(hint, (WIDTH // 2 - 140, hud_y + 32))


def draw_tank_icon(surface, x, y, color, angle_offset, t):
    """Draw a small animated tank icon for menus."""
    angle = (t * 0.05 + angle_offset) % 360
    s = 12
    rad = math.radians(angle)

    # Glow
    glow_surf = pygame.Surface((40, 40), pygame.SRCALPHA)
    pygame.draw.circle(glow_surf, (*color, 30), (20, 20), 20)
    surface.blit(glow_surf, (x - 20, y - 20))

    # Body
    body = pygame.Surface((s * 2, s * 2), pygame.SRCALPHA)
    pygame.draw.rect(body, color, (2, 2, s * 2 - 4, s * 2 - 4), border_radius=3)
    rotated = pygame.transform.rotate(body, angle)
    rect = rotated.get_rect(center=(x, y))
    surface.blit(rotated, rect)

    # Barrel
    end_x = x + math.cos(rad) * s * 1.5
    end_y = y - math.sin(rad) * s * 1.5
    pygame.draw.line(surface, WHITE, (x, y), (int(end_x), int(end_y)), 3)


def check_bullet_collisions(tanks, bullets, particles):
    """Check bullet-tank collisions."""
    for b in bullets:
        if not b.active:
            continue
        for t in tanks:
            if not t.alive:
                continue
            # Skip self-hits on first frame (no bounces)
            if t.is_player and b.owner == "player" and b.bounces == 0:
                continue
            if not t.is_player and b.owner == "enemy" and b.bounces == 0:
                continue

            dist = math.sqrt((b.x - t.x) ** 2 + (b.y - t.y) ** 2)
            if dist < t.size:
                t.alive = False
                b.active = False
                spawn_explosion(particles, t.x, t.y, 30)
                return t
    return None


#  MAIN GAME LOOP
def main():
    # Send camera mode switch
    try:
        mode_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        mode_sock.sendto(b"tank", ("127.0.0.1", 5006))
        mode_sock.close()
    except:
        pass

    game_state = "START"
    score = 0
    wave = 1
    particles = []

    walls = build_maze(0)
    nav_grid = build_nav_grid(walls)

    player = Tank(CELL * 1.5, CELL * 1.5, is_player=True)
    enemies = []
    bullets = []

    screen_shake = 0
    shake_offset = (0, 0)
    flash_alpha = 0
    transition_timer = 0
    bg_particles = []  # Background ambient particles

    # Spawn ambient background particles
    for _ in range(15):
        bg_particles.append(Particle(
            random.random() * ARENA_W, random.random() * ARENA_H,
            (random.random() - 0.5) * 0.3, (random.random() - 0.5) * 0.3,
            (30, 40, 80), random.uniform(1, 2), random.uniform(5, 15),
            friction=1.0
        ))

    def spawn_enemies(count):
        """Spawn enemies at valid positions far from player."""
        valid_spawns = []
        for r in range(ROWS):
            for c in range(COLS):
                if nav_grid[r][c]:
                    sx = c * CELL + CELL // 2
                    sy = r * CELL + CELL // 2
                    dist = math.sqrt((sx - player.x) ** 2 + (sy - player.y) ** 2)
                    if dist > 200:
                        valid_spawns.append((sx, sy))

        random.shuffle(valid_spawns)
        spawned = []
        for i in range(min(count, len(valid_spawns))):
            spawned.append(Tank(valid_spawns[i][0], valid_spawns[i][1], is_player=False))
        return spawned

    running = True
    while running:
        t = pygame.time.get_ticks()

        # Input
        gesture = current_ai_state.get("gesture", "NONE")
        keys = pygame.key.get_pressed()
        if keys[pygame.K_SPACE]:
            gesture = "OPEN"
        elif keys[pygame.K_RETURN]:
            gesture = "POINT"
        elif gesture == "NONE" and not any([keys[pygame.K_SPACE], keys[pygame.K_RETURN]]):
            gesture = "FIST"

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

        # Render surface 
        render_surf = pygame.Surface((WIDTH, HEIGHT))
        render_surf.fill(DARK_BG)

        # START SCREEN
        if game_state == "START":
            # Animated background dots
            for i in range(30):
                dx = int((t * 0.015 + i * 27) % ARENA_W)
                dy = int((math.sin(t * 0.0008 + i * 0.7) + 1) * 0.5 * ARENA_H)
                pygame.draw.circle(render_surf, (15, 20, 45), (dx, dy), 3)

            # Floor grid (subtle)
            draw_floor_grid(render_surf, t)

            # Title
            title_y = HEIGHT // 2 - 140 + int(math.sin(t * 0.002) * 6)
            draw_text_glow(render_surf, "TANK TROUBLE", font_huge, PLAYER_GLOW, WIDTH // 2, title_y)

            # Subtitle
            draw_text_glow(render_surf, "NEON EDITION", font_medium, NEON_CYAN, WIDTH // 2, title_y + 55)

            # Tank icons
            draw_tank_icon(render_surf, WIDTH // 2 - 80, title_y + 120, PLAYER_GLOW, 0, t)
            draw_tank_icon(render_surf, WIDTH // 2, title_y + 120, ENEMY_GLOW, 120, t)
            draw_tank_icon(render_surf, WIDTH // 2 + 80, title_y + 120, NEON_ORANGE, 240, t)

            # Versus text
            draw_text_glow(render_surf, "VS", font_medium, NEON_YELLOW, WIDTH // 2 - 40, title_y + 120)
            draw_text_glow(render_surf, "VS", font_medium, NEON_YELLOW, WIDTH // 2 + 40, title_y + 120)

            # Blinking start text
            if (t // 500) % 2 == 0:
                draw_text_glow(render_surf, "OPEN HAND / PRESS SPACE", font_small, WHITE, WIDTH // 2, title_y + 190)
                draw_text_glow(render_surf, "TO START", font_small, WHITE, WIDTH // 2, title_y + 210)

            # Controls
            draw_text_glow(render_surf, "FIST = Rotate   OPEN = Move   POINT = Shoot", font_tiny, (80, 90, 130), WIDTH // 2, HEIGHT - 40)

            if gesture == "OPEN":
                player = Tank(CELL * 1.5, CELL * 1.5, is_player=True)
                walls = build_maze(0)
                nav_grid = build_nav_grid(walls)
                enemies = spawn_enemies(wave)
                bullets = []
                particles = []
                game_state = "PLAYING"

        #  PLAYING
        elif game_state == "PLAYING":
            # Update player
            player.update_player(gesture, walls, bullets, particles)

            # Update enemies
            for e in enemies:
                e.update_ai(walls, bullets, particles, player, nav_grid, wave)

            # Update bullets
            for b in bullets:
                b.update(walls, particles)

            # Collisions
            destroyed = check_bullet_collisions([player] + enemies, bullets, particles)
            if destroyed:
                screen_shake = 15
                flash_alpha = 120
                if destroyed.is_player:
                    game_state = "GAME_OVER"
                else:
                    score += 100 + wave * 20

            # Cleanup
            bullets = [b for b in bullets if b.active]
            enemies = [e for e in enemies if e.alive]

            if len(enemies) == 0 and game_state == "PLAYING":
                game_state = "WAVE_COMPLETE"
                transition_timer = 120

            # ─── Draw ───
            draw_floor_grid(render_surf, t)
            draw_neon_walls(render_surf, walls, t)

            # Ambient particles
            for bp in bg_particles:
                if not bp.update():
                    bp.x = random.random() * ARENA_W
                    bp.y = random.random() * ARENA_H
                    bp.life = bp.max_life
                bp.draw(render_surf)

            player.draw(render_surf, t)
            for e in enemies:
                e.draw(render_surf, t)
            for b in bullets:
                b.draw(render_surf)

            # Particles
            particles = [p for p in particles if p.update()]
            for p in particles:
                p.draw(render_surf)

            # HUD
            draw_hud(render_surf, score, wave, gesture, t)

        #  WAVE COMPLETE
        elif game_state == "WAVE_COMPLETE":
            transition_timer -= 1

            # Still draw the arena
            draw_floor_grid(render_surf, t)
            draw_neon_walls(render_surf, walls, t)
            player.draw(render_surf, t)
            for b in bullets:
                b.draw(render_surf)

            # Celebration particles
            if transition_timer > 60 and random.random() < 0.3:
                particles.append(Particle(
                    random.random() * ARENA_W, random.random() * ARENA_H,
                    (random.random() - 0.5) * 3, (random.random() - 0.5) * 3,
                    random.choice([PLAYER_GLOW, NEON_CYAN, GOLD, NEON_YELLOW]),
                    random.uniform(2, 5), random.uniform(0.5, 1.0)
                ))

            particles = [p for p in particles if p.update()]
            for p in particles:
                p.draw(render_surf)

            # Overlay
            overlay = pygame.Surface((ARENA_W, ARENA_H), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 80))
            render_surf.blit(overlay, (0, 0))

            # Text
            win_y = ARENA_H // 2 - 60
            draw_text_glow(render_surf, "WAVE CLEARED!", font_large, PLAYER_GLOW, WIDTH // 2, win_y)
            draw_text_glow(render_surf, f"SCORE: {score}", font_medium, GOLD, WIDTH // 2, win_y + 50)

            if (t // 500) % 2 == 0:
                draw_text_glow(render_surf, "OPEN HAND TO CONTINUE", font_small, NEON_CYAN, WIDTH // 2, win_y + 100)

            draw_hud(render_surf, score, wave, gesture, t)

            if gesture == "OPEN" and transition_timer < 80:
                wave += 1
                extra = min(wave - 1, 6)
                walls = build_maze(extra)
                nav_grid = build_nav_grid(walls)
                player.x = CELL * 1.5
                player.y = CELL * 1.5
                player.angle = 0
                enemies = spawn_enemies(min(wave, 5))
                bullets = []
                particles = []
                game_state = "PLAYING"

        #  GAME OVER
        elif game_state == "GAME_OVER":
            # Draw arena still
            draw_floor_grid(render_surf, t)
            draw_neon_walls(render_surf, walls, t)
            for e in enemies:
                e.draw(render_surf, t)
            for b in bullets:
                b.draw(render_surf)

            particles = [p for p in particles if p.update()]
            for p in particles:
                p.draw(render_surf)

            # Dark overlay
            overlay = pygame.Surface((ARENA_W, ARENA_H), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 120))
            render_surf.blit(overlay, (0, 0))

            # Animated background dots
            for i in range(10):
                dx = int((t * 0.01 + i * 50) % ARENA_W)
                dy = int((math.sin(t * 0.001 + i) + 1) * 0.5 * ARENA_H)
                pygame.draw.circle(render_surf, (30, 10, 10), (dx, dy), 4)

            # Text
            go_y = ARENA_H // 2 - 80
            draw_text_glow(render_surf, "GAME OVER", font_huge, ENEMY_GLOW, WIDTH // 2, go_y)
            draw_text_glow(render_surf, f"SCORE: {score}", font_large, GOLD, WIDTH // 2, go_y + 70)
            draw_text_glow(render_surf, f"WAVE: {wave}", font_medium, NEON_CYAN, WIDTH // 2, go_y + 110)

            if (t // 500) % 2 == 0:
                draw_text_glow(render_surf, "OPEN HAND / SPACE TO RESTART", font_small, NEON_YELLOW, WIDTH // 2, go_y + 160)

            draw_hud(render_surf, score, wave, gesture, t)

            if gesture == "OPEN":
                score = 0
                wave = 1
                walls = build_maze(0)
                nav_grid = build_nav_grid(walls)
                player = Tank(CELL * 1.5, CELL * 1.5, is_player=True)
                enemies = spawn_enemies(wave)
                bullets = []
                particles = []
                game_state = "PLAYING"

        # Screen effects 
        # Screen shake
        if screen_shake > 0:
            screen_shake -= 1
            shake_offset = (random.randint(-4, 4), random.randint(-4, 4))
        else:
            shake_offset = (0, 0)

        # Flash
        if flash_alpha > 0:
            flash_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            flash_surf.fill((255, 255, 255, int(flash_alpha)))
            render_surf.blit(flash_surf, (0, 0))
            flash_alpha = max(0, flash_alpha - 8)

        # Final blit
        screen.fill(BLACK)
        screen.blit(render_surf, shake_offset)
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
