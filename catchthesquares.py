import pygame
import random

# --- Game Constants ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
PADDLE_WIDTH = 100
PADDLE_HEIGHT = 20
SQUARE_SIZE = 30
FALL_SPEED = 3
INITIAL_LIVES = 3
FONT_SIZE = 36
FPS = 60

# --- Colors ---
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)

class Paddle(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = pygame.Surface([PADDLE_WIDTH, PADDLE_HEIGHT])
        self.image.fill(BLUE)
        self.rect = self.image.get_rect()
        self.rect.centerx = SCREEN_WIDTH // 2
        self.rect.bottom = SCREEN_HEIGHT - 10
        self.speed = 8

    def update(self):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            self.rect.x -= self.speed
        if keys[pygame.K_RIGHT]:
            self.rect.x += self.speed

        # Keep paddle within screen bounds
        if self.rect.left < 0:
            self.rect.left = 0
        if self.rect.right > SCREEN_WIDTH:
            self.rect.right = SCREEN_WIDTH

class FallingSquare(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = pygame.Surface([SQUARE_SIZE, SQUARE_SIZE])
        self.image.fill(GREEN)
        self.rect = self.image.get_rect()
        self.rect.x = random.randrange(0, SCREEN_WIDTH - SQUARE_SIZE)
        self.rect.y = random.randrange(-100, -SQUARE_SIZE) # Start above screen
        self.speed = FALL_SPEED

    def update(self):
        self.rect.y += self.speed
        if self.rect.top > SCREEN_HEIGHT:
            self.kill() # Remove square if it goes off screen

def game():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Catch the Falling Squares")
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, FONT_SIZE)

    all_sprites = pygame.sprite.Group()
    falling_squares = pygame.sprite.Group()

    paddle = Paddle()
    all_sprites.add(paddle)

    score = 0
    lives = INITIAL_LIVES
    game_over = False

    # Event for spawning new squares
    SPAWN_SQUARE = pygame.USEREVENT + 1
    pygame.time.set_timer(SPAWN_SQUARE, 1000) # Spawn a new square every second

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == SPAWN_SQUARE and not game_over:
                new_square = FallingSquare()
                all_sprites.add(new_square)
                falling_squares.add(new_square)

        if not game_over:
            all_sprites.update()

            # Check for collisions between paddle and falling squares
            caught_squares = pygame.sprite.spritecollide(paddle, falling_squares, True)
            for square in caught_squares:
                score += 1

            # Check for squares that went off screen (missed)
            for square in list(falling_squares): # Iterate over a copy to allow modification
                if square.rect.top > SCREEN_HEIGHT:
                    lives -= 1
                    square.kill() # Remove the missed square
                    if lives <= 0:
                        game_over = True

            # Game Over check
            if lives <= 0:
                game_over = True

        # Drawing
        screen.fill(BLACK)
        all_sprites.draw(screen)

        # Display score and lives
        score_text = font.render(f"Score: {score}", True, WHITE)
        lives_text = font.render(f"Lives: {lives}", True, WHITE)
        screen.blit(score_text, (10, 10))
        screen.blit(lives_text, (SCREEN_WIDTH - lives_text.get_width() - 10, 10))

        if game_over:
            game_over_text = font.render("GAME OVER!", True, RED)
            restart_text = font.render("Press 'R' to Restart or 'Q' to Quit", True, WHITE)
            text_rect = game_over_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 20))
            restart_rect = restart_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 20))
            screen.blit(game_over_text, text_rect)
            screen.blit(restart_text, restart_rect)

            keys = pygame.key.get_pressed()
            if keys[pygame.K_r]:
                # Reset game
                score = 0
                lives = INITIAL_LIVES
                game_over = False
                all_sprites.empty()
                falling_squares.empty()
                paddle = Paddle()
                all_sprites.add(paddle)
            elif keys[pygame.K_q]:
                running = False

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()

if __name__ == "__main__":
    game()