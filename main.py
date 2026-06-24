# pyrefly: ignore [missing-import]
import pygame
import sys
import subprocess
import time

pygame.init()

WIDTH, HEIGHT = 600, 520
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Game Hub")

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
YELLOW = (255, 255, 0)
CYAN = (0, 255, 255)
GRAY = (50, 50, 50)

try:
    font_large = pygame.font.SysFont('courier', 48, bold=True)
    font_medium = pygame.font.SysFont('courier', 32, bold=True)
    font_small = pygame.font.SysFont('courier', 20)
except:
    font_large = pygame.font.Font(None, 48)
    font_medium = pygame.font.Font(None, 32)
    font_small = pygame.font.Font(None, 20)

def draw_text_centered(text, font, color, y):
    surface = font.render(text, True, color)
    rect = surface.get_rect(center=(WIDTH//2, y))
    screen.blit(surface, rect)

def main():
    # Khởi động Controller
    print("Starting Camera...")
    ai_process = subprocess.Popen([sys.executable, "ai_controller.py"])
    
    clock = pygame.time.Clock()
    
    # Định nghĩa vùng bấm của các nút
    pacman_btn = pygame.Rect(150, 150, 300, 60)
    spooky_btn = pygame.Rect(150, 240, 300, 60)
    tank_btn = pygame.Rect(150, 330, 300, 60)
    
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1: # Click chuột trái
                    pos = pygame.mouse.get_pos()
                    if pacman_btn.collidepoint(pos):
                        print("Launching Pacman...")
                        # Chạy game và đợi game kết thúc
                        subprocess.run([sys.executable, "pacman.py"])
                    elif spooky_btn.collidepoint(pos):
                        print("Launching Spooky Spikes...")
                        subprocess.run([sys.executable, "spooky_spikes.py"])
                    elif tank_btn.collidepoint(pos):
                        print("Launching Tank Trouble...")
                        subprocess.run([sys.executable, "tank_trouble.py"])
        
        screen.fill(BLACK)
        
        draw_text_centered("GAME HUB", font_large, YELLOW, 60)
        draw_text_centered("Select a Game", font_small, WHITE, 100)
        
        # Vẽ nút bấm
        mx, my = pygame.mouse.get_pos()
        
        # Pacman btn
        color1 = CYAN if pacman_btn.collidepoint((mx, my)) else GRAY
        pygame.draw.rect(screen, color1, pacman_btn, border_radius=10)
        draw_text_centered("PACMAN", font_medium, BLACK, pacman_btn.centery)
        
        # Spooky Spikes btn
        ORANGE = (255, 165, 0)
        color2 = ORANGE if spooky_btn.collidepoint((mx, my)) else GRAY
        pygame.draw.rect(screen, color2, spooky_btn, border_radius=10)
        draw_text_centered("SPOOKY SPIKES", font_medium, BLACK, spooky_btn.centery)
        
        # Tank Trouble btn
        GREEN = (0, 255, 100)
        color3 = GREEN if tank_btn.collidepoint((mx, my)) else GRAY
        pygame.draw.rect(screen, color3, tank_btn, border_radius=10)
        draw_text_centered("TANK TROUBLE", font_medium, BLACK, tank_btn.centery)
        
        pygame.display.flip()
        clock.tick(60)

    print("Closing Camera...")
    ai_process.terminate()
    try:
        ai_process.wait(timeout=2)
    except:
        ai_process.kill()
        
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
