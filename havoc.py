import pygame

# --- Constants ---
WIDTH, HEIGHT = 800, 600
FPS = 60
GRAVITY = 1
JUMP_POWER = 15
SPEED = 5
KNOCKBACK_MULTIPLIER = 0.2
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
DARK_BLUE = (0, 0, 128)
GOLD = (255, 215, 0)
GRAY = (100, 100, 100)
RED = (255, 0, 0)
BLUE = (0, 0, 255)

# --- Initialize Pygame ---
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Havoc Engine")
clock = pygame.time.Clock()

# --- Fonts ---
title_font = pygame.font.Font(None, 100)
menu_font = pygame.font.Font(None, 50)
info_font = pygame.font.Font(None, 30)

# --- Player Class ---
class Player(pygame.sprite.Sprite):
    def __init__(self, x, y, color, controls):
        super().__init__()
        self.image = pygame.Surface((40, 60))
        self.image.fill(color)
        self.rect = self.image.get_rect(topleft=(x, y))
        self.controls = controls
        self.x_speed = 0
        self.y_speed = 0
        self.damage = 0
        self.jumping = False
        self.attacking = False

    def update(self):
        self.x_speed = 0
        keys = pygame.key.get_pressed()

        # Movement
        if keys[self.controls['left']]:
            self.x_speed = -SPEED
        if keys[self.controls['right']]:
            self.x_speed = SPEED
        if keys[self.controls['jump']] and not self.jumping:
            self.y_speed = -JUMP_POWER
            self.jumping = True

        # Attack
        if keys[self.controls['attack']]:
            self.attacking = True
        else:
            self.attacking = False

        # Apply gravity
        self.y_speed += GRAVITY

        # Update position
        self.rect.x += self.x_speed
        self.rect.y += self.y_speed

        # Ground collision
        if self.rect.bottom > HEIGHT - 100:
            self.rect.bottom = HEIGHT - 100
            self.y_speed = 0
            self.jumping = False

        # Screen boundaries
        if self.rect.left < 0:
            self.rect.left = 0
        if self.rect.right > WIDTH:
            self.rect.right = WIDTH

    def hit(self, damage):
        self.damage += damage
        knockback = damage * KNOCKBACK_MULTIPLIER * (self.damage / 10 + 1)
        direction = -1 if self.rect.centerx < WIDTH / 2 else 1
        self.x_speed += knockback * direction
        self.y_speed = -knockback / 2
        self.jumping = True

# --- Main Menu ---
def main_menu():
    menu_options = ["Start Game", "Options", "Exit"]
    selected = 0
    menu_running = True

    while menu_running:
        screen.fill(DARK_BLUE)

        # Title
        title_text = title_font.render("HAVOC ENGINE", True, GOLD)
        title_rect = title_text.get_rect(center=(WIDTH // 2, HEIGHT // 4))
        screen.blit(title_text, title_rect)

        # Menu Options
        for i, option in enumerate(menu_options):
            if i == selected:
                option_color = GOLD
            else:
                option_color = GRAY
            option_text = menu_font.render(option, True, option_color)
            option_rect = option_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + i * 60))
            screen.blit(option_text, option_rect)

        pygame.display.flip()
        clock.tick(FPS)

        # Event Handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    selected = (selected - 1) % len(menu_options)
                elif event.key == pygame.K_DOWN:
                    selected = (selected + 1) % len(menu_options)
                elif event.key == pygame.K_RETURN:
                    if menu_options[selected] == "Start Game":
                        menu_running = False
                    elif menu_options[selected] == "Options":
                        options_menu()
                    elif menu_options[selected] == "Exit":
                        pygame.quit()
                        exit()

def options_menu():
    options_running = True
    while options_running:
        screen.fill(DARK_BLUE)

        # Options Title
        options_title = menu_font.render("OPTIONS", True, GOLD)
        options_rect = options_title.get_rect(center=(WIDTH // 2, HEIGHT // 4))
        screen.blit(options_title, options_rect)

        # Back Option
        back_text = menu_font.render("Press ESC to return", True, GRAY)
        back_rect = back_text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        screen.blit(back_text, back_rect)

        pygame.display.flip()
        clock.tick(FPS)

        # Event Handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    options_running = False

# --- Players ---
player1_controls = {
    'left': pygame.K_a,
    'right': pygame.K_d,
    'jump': pygame.K_w,
    'attack': pygame.K_s
}
player2_controls = {
    'left': pygame.K_LEFT,
    'right': pygame.K_RIGHT,
    'jump': pygame.K_UP,
    'attack': pygame.K_DOWN
}

player1 = Player(100, 400, RED, player1_controls)
player2 = Player(660, 400, BLUE, player2_controls)
all_sprites = pygame.sprite.Group(player1, player2)

# --- Game Loop ---
def game_loop():
    running = True
    while running:
        # --- Event Handling ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # --- Game Logic ---
        all_sprites.update()

        # Attack collision
        if player1.attacking and player1.rect.colliderect(player2.rect):
            player2.hit(5)
            player1.attacking = False
        if player2.attacking and player2.rect.colliderect(player1.rect):
            player1.hit(5)
            player2.attacking = False

        # --- Drawing ---
        screen.fill(WHITE)
        pygame.draw.rect(screen, BLACK, (0, HEIGHT - 100, WIDTH, 10))  # Ground
        all_sprites.draw(screen)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    exit()

# --- Start Game ---
main_menu()
game_loop()
