import pygame
import random
import asyncio
import websockets
import json
import threading
import time

# --- Game Constants ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
PADDLE_WIDTH = 100
PADDLE_HEIGHT = 20
SQUARE_SIZE = 30
FALL_SPEED = 3
INITIAL_LIVES = 3  # <-- Make sure this is defined HERE
FONT_SIZE = 36
FPS = 60

# --- Colors ---
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)

# --- Game State (shared between Pygame thread and WebSocket server) ---
# This must be defined AFTER INITIAL_LIVES and other constants it uses
game_state = {
    'paddle_x': SCREEN_WIDTH // 2 - PADDLE_WIDTH // 2,
    'squares': [], # list of {'x': int, 'y': int, 'id': str}
    'score': 0,
    'lives': INITIAL_LIVES, # <--- Now INITIAL_LIVES is defined!
    'game_over': False
}
# To protect game_state when accessed by multiple threads
game_state_lock = threading.Lock()

# --- Game Control Input Queue ---
control_queue = []

# --- Pygame Classes ---
class Paddle(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = pygame.Surface([PADDLE_WIDTH, PADDLE_HEIGHT])
        self.image.fill(BLUE)
        self.rect = self.image.get_rect()
        # Initialize position based on constants
        self.rect.centerx = SCREEN_WIDTH // 2
        self.rect.bottom = SCREEN_HEIGHT - 10
        self.speed = 8
        # Ensure initial paddle_x in game_state reflects this
        with game_state_lock:
            game_state['paddle_x'] = self.rect.x

    def update(self):
        global game_state, game_state_lock, control_queue
        # Handle keyboard input (for desktop play)
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            self.rect.x -= self.speed
        if keys[pygame.K_RIGHT]:
            self.rect.x += self.speed

        # Handle WebSocket input
        with game_state_lock:
            while control_queue:
                control = control_queue.pop(0) # Get the oldest control
                if control == 'left':
                    self.rect.x -= self.speed
                elif control == 'right':
                    self.rect.x += self.speed

        # Keep paddle within screen bounds
        if self.rect.left < 0:
            self.rect.left = 0
        if self.rect.right > SCREEN_WIDTH:
            self.rect.right = SCREEN_WIDTH

        # Update shared game_state for paddle position
        with game_state_lock:
            game_state['paddle_x'] = self.rect.x

class FallingSquare(pygame.sprite.Sprite):
    def __init__(self, square_id):
        super().__init__()
        self.image = pygame.Surface([SQUARE_SIZE, SQUARE_SIZE])
        self.image.fill(GREEN)
        self.rect = self.image.get_rect()
        self.rect.x = random.randrange(0, SCREEN_WIDTH - SQUARE_SIZE)
        self.rect.y = random.randrange(-100, -SQUARE_SIZE) # Start above screen
        self.speed = FALL_SPEED
        self.id = square_id # Unique ID for client to track

    def update(self):
        self.rect.y += self.speed
        # The game() loop will handle off-screen removal based on rect.top > SCREEN_HEIGHT

# --- WebSocket Server Logic ---
connected_clients = set()

async def register(websocket):
    connected_clients.add(websocket)
    print(f"Client connected: {websocket.remote_address}. Total clients: {len(connected_clients)}")

async def unregister(websocket):
    connected_clients.remove(websocket)
    print(f"Client disconnected: {websocket.remote_address}. Total clients: {len(connected_clients)}")

async def websocket_handler(websocket, path):
    await register(websocket)
    try:
        async for message in websocket:
            data = json.loads(message)
            if data.get('type') == 'control':
                direction = data.get('direction')
                with game_state_lock:
                    control_queue.append(direction)
        except websockets.exceptions.ConnectionClosedOK:
        print(f"Client {websocket.remote_address} connection closed normally.")
    except Exception as e:
        print(f"WebSocket error with {websocket.remote_address}: {e}")
    finally:
        await unregister(websocket)

async def send_game_state_to_clients():
    global game_state
    while True:
        # Send updates at approximately game FPS, but ensure smooth loop
        # A simple sleep for FPS interval might not align perfectly with game ticks
        # but is sufficient for this example.
        await asyncio.sleep(1/FPS)
        if connected_clients:
            with game_state_lock:
                # Create a serializable state for the client
                client_squares = [{'x': sq['x'], 'y': sq['y'], 'id': sq['id']} for sq in game_state['squares']]
                current_state = {
                    'paddle_x': game_state['paddle_x'],
                    'squares': client_squares,
                    'score': game_state['score'],
                    'lives': game_state['lives'],
                    'game_over': game_state['game_over']
                }
            message = json.dumps(current_state)
            # Send to all connected clients
            await asyncio.wait([client.send(message) for client in connected_clients], return_when=asyncio.ALL_COMPLETED)

def run_websocket_server(loop):
    asyncio.set_event_loop(loop)
    start_server = websockets.serve(websocket_handler, "0.0.0.0", 5000) # Listen on all interfaces
    loop.run_until_complete(start_server)
    loop.run_until_complete(send_game_state_to_clients()) # Start sending state in parallel
    loop.run_forever()

# --- Pygame Game Loop Function ---
def game():
    global game_state, game_state_lock, control_queue

    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Catch the Falling Squares (Desktop Server)")
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, FONT_SIZE)

    all_sprites = pygame.sprite.Group()
    falling_squares_pygame_group = pygame.sprite.Group() # Pygame's internal group

    paddle = Paddle()
    all_sprites.add(paddle)

    # Event for spawning new squares
    SPAWN_SQUARE = pygame.USEREVENT + 1
    pygame.time.set_timer(SPAWN_SQUARE, 1000) # Spawn a new square every second

    square_id_counter = 0 # To give unique IDs to squares

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == SPAWN_SQUARE and not game_state['game_over']:
                square_id_counter += 1
                new_square = FallingSquare(f"sq_{square_id_counter}")
                all_sprites.add(new_square)
                falling_squares_pygame_group.add(new_square) # Add to Pygame's group

        with game_state_lock:
            if not game_state['game_over']:
                all_sprites.update() # Update Pygame sprites (including paddle and squares)

                # Check for collisions between paddle and falling squares
                caught_squares = pygame.sprite.spritecollide(paddle, falling_squares_pygame_group, True)
                for square in caught_squares:
                    game_state['score'] += 1

                # Check for squares that went off screen (missed)
                missed_squares_to_remove = []
                for square in falling_squares_pygame_group: # Iterate directly over Pygame group
                    if square.rect.top > SCREEN_HEIGHT:
                        game_state['lives'] -= 1
                        missed_squares_to_remove.append(square)
                        if game_state['lives'] <= 0:
                            game_state['game_over'] = True
                for square in missed_squares_to_remove:
                    square.kill() # Remove from all_sprites and falling_squares_pygame_group

                # Update the shared game_state['squares'] list for the client
                # Convert Pygame sprite objects to simple dicts for JSON serialization
                game_state['squares'] = [{'x': sq.rect.x, 'y': sq.rect.y, 'id': sq.id} for sq in falling_squares_pygame_group]

                if game_state['lives'] <= 0:
                    game_state['game_over'] = True

        # Drawing (for desktop display)
        screen.fill(BLACK)
        all_sprites.draw(screen)

        # Display score and lives
        score_text = font.render(f"Score: {game_state['score']}", True, WHITE)
        lives_text = font.render(f"Lives: {game_state['lives']}", True, WHITE)
        screen.blit(score_text, (10, 10))
        screen.blit(lives_text, (SCREEN_WIDTH - lives_text.get_width() - 10, 10))

        if game_state['game_over']:
            game_over_text = font.render("GAME OVER!", True, RED)
            restart_text = font.render("Press 'R' to Restart or 'Q' to Quit", True, WHITE)
            text_rect = game_over_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 20))
            restart_rect = restart_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 20))
            screen.blit(game_over_text, text_rect)
            screen.blit(restart_text, restart_rect)

            keys = pygame.key.get_pressed()
            if keys[pygame.K_r]:
                # Reset game state
                with game_state_lock:
                    game_state['score'] = 0
                    game_state['lives'] = INITIAL_LIVES
                    game_state['game_over'] = False
                    game_state['squares'] = [] # Clear client's squares

                # Clear Pygame sprite groups and re-create paddle
                all_sprites.empty()
                falling_squares_pygame_group.empty()
                paddle = Paddle()
                all_sprites.add(paddle)
                # No need to update game_state['paddle_x'] here, Paddle.__init__ does it
            elif keys[pygame.K_q]:
                running = False


        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()

if __name__ == "__main__":
    # Start the WebSocket server in a separate thread
    websocket_loop = asyncio.new_event_loop()
    websocket_thread = threading.Thread(target=run_websocket_server, args=(websocket_loop,))
    websocket_thread.daemon = True # Allow the main program to exit gracefully
    websocket_thread.start()

    # Give the WebSocket thread a moment to start its event loop
    time.sleep(1)

    # Run the Pygame game loop in the main thread
    game()