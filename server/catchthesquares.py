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
INITIAL_LIVES = 3
FONT_SIZE = 36
FPS = 60 # Game frames per second and WebSocket update rate

# --- Colors ---
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)

# --- Game State (shared between Pygame thread and WebSocket server) ---
# This dictionary holds the current state of the game
# It must be defined AFTER its dependent constants like SCREEN_WIDTH, INITIAL_LIVES
game_state = {
    'paddle_x': SCREEN_WIDTH // 2 - PADDLE_WIDTH // 2,
    'squares': [], # List of dictionaries: [{'x': int, 'y': int, 'id': str}]
    'score': 0,
    'lives': INITIAL_LIVES,
    'game_over': False
}
# A lock to ensure thread-safe access to game_state
game_state_lock = threading.Lock()

# --- Game Control Input Queue ---
# Stores control inputs received from web clients, to be processed by Pygame thread
control_queue = []

# --- Pygame Classes ---
class Paddle(pygame.sprite.Sprite):
    """Player-controlled paddle at the bottom of the screen."""
    def __init__(self):
        super().__init__()
        self.image = pygame.Surface([PADDLE_WIDTH, PADDLE_HEIGHT])
        self.image.fill(BLUE)
        self.rect = self.image.get_rect()
        self.rect.centerx = SCREEN_WIDTH // 2
        self.rect.bottom = SCREEN_HEIGHT - 10
        self.speed = 8

        # Initialize the shared game_state with the paddle's initial position
        with game_state_lock:
            game_state['paddle_x'] = self.rect.x

    def update(self):
        """Updates paddle position based on keyboard input (desktop) and WebSocket input."""
        global game_state, game_state_lock, control_queue

        # 1. Handle Keyboard Input (for direct desktop play)
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            self.rect.x -= self.speed
        if keys[pygame.K_RIGHT]:
            self.rect.x += self.speed

        # 2. Handle WebSocket Input (from web clients)
        with game_state_lock:
            # Process all pending controls from the queue
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

        # Update the shared game_state with the paddle's current position
        with game_state_lock:
            game_state['paddle_x'] = self.rect.x

class FallingSquare(pygame.sprite.Sprite):
    """A single falling square."""
    def __init__(self, square_id):
        super().__init__()
        self.image = pygame.Surface([SQUARE_SIZE, SQUARE_SIZE])
        self.image.fill(GREEN)
        self.rect = self.image.get_rect()
        # Random initial X position, starting above the screen
        self.rect.x = random.randrange(0, SCREEN_WIDTH - SQUARE_SIZE)
        self.rect.y = random.randrange(-100, -SQUARE_SIZE)
        self.speed = FALL_SPEED
        self.id = square_id # Unique ID to help client track individual squares

    def update(self):
        """Moves the square downwards."""
        self.rect.y += self.speed
        # Squares that go off-screen will be handled by the game loop, not here.

# --- WebSocket Server Logic ---
connected_clients = set() # To keep track of all connected WebSocket clients

# IMPORTANT: All functions involving 'await' or 'async for' MUST be 'async def'
async def register(websocket):
    """Registers a new WebSocket client."""
    connected_clients.add(websocket)
    print(f"Client connected: {websocket.remote_address}. Total clients: {len(connected_clients)}")

async def unregister(websocket):
    """Unregisters a disconnected WebSocket client."""
    connected_clients.remove(websocket)
    print(f"Client disconnected: {websocket.remote_address}. Total clients: {len(connected_clients)}")

async def websocket_handler(websocket, path):
    """Handles incoming WebSocket messages from a client."""
    await register(websocket) # Register the new client
    try:
        # Loop indefinitely to receive messages from this client
        async for message in websocket:
            data = json.loads(message)
            if data.get('type') == 'control':
                direction = data.get('direction')
                # Add the control input to the shared queue for the Pygame thread
                with game_state_lock:
                    control_queue.append(direction)
            # You could add handling for other message types here (e.g., 'restart_request')
    except websockets.exceptions.ConnectionClosedOK:
        # This exception is raised when a client closes the connection normally
        print(f"Client {websocket.remote_address} connection closed normally.")
    except Exception as e:
        # Catch any other unexpected errors during WebSocket communication
        print(f"WebSocket error with {websocket.remote_address}: {e}")
    finally:
        # Ensure client is unregistered when connection closes for any reason
        await unregister(websocket)

async def send_game_state_to_clients():
    """Continuously sends the current game state to all connected clients."""
    global game_state
    while True:
        # Send updates at the defined FPS rate
        await asyncio.sleep(1/FPS)

        if connected_clients:
            with game_state_lock:
                # Prepare the game state for JSON serialization.
                # Convert Pygame sprite objects into simple dictionaries.
                client_squares = [{'x': sq.rect.x, 'y': sq.rect.y, 'id': sq.id} for sq in game_state['squares']]
                current_state_for_client = {
                    'paddle_x': game_state['paddle_x'],
                    'squares': client_squares,
                    'score': game_state['score'],
                    'lives': game_state['lives'],
                    'game_over': game_state['game_over']
                }
            message = json.dumps(current_state_for_client)

            # Send the message to all currently connected clients concurrently
            await asyncio.wait([client.send(message) for client in connected_clients], return_when=asyncio.ALL_COMPLETED)

# THIS IS THE CORRECTED FUNCTION
def run_websocket_server(loop):
    """Function to run the WebSocket server and state sender in a separate thread."""
    asyncio.set_event_loop(loop) # Set the event loop for this specific thread

    async def start_all_async_tasks():
        """
        Main asynchronous entry point for the WebSocket server thread.
        This function will start the server and schedule background tasks.
        """
        try:
            # Start the WebSocket server. 'await' here ensures that the server
            # is fully initialized within the context of a running loop.
            server = await websockets.serve(websocket_handler, "0.0.0.0", 5000)
            print(f"WebSocket server successfully started on {server.sockets[0].getsockname()}")

            # Create and schedule the game state sender task.
            # This task will run concurrently with the WebSocket server.
            asyncio.create_task(send_game_state_to_clients())

            # Keep this async function alive indefinitely. This ensures the
            # WebSocket server and sender task continue running.
            await server.wait_closed() # This blocks until the server is explicitly closed
            # (e.g., when the program terminates)
        except Exception as e:
            print(f"Error starting WebSocket server tasks: {e}")
            # Optionally, re-raise or handle cleanup if server fails to start
            raise # Re-raise to ensure the thread's exception is seen

    try:
        # Run the main asynchronous entry point for this thread's loop.
        # This call will block until `start_all_async_tasks` completes,
        # which, because of `await server.wait_closed()`, means it runs indefinitely.
        loop.run_until_complete(start_all_async_tasks())
    except Exception as e:
        print(f"Fatal error in WebSocket thread's asyncio loop: {e}")
        # The thread will likely terminate here.

# --- Pygame Game Loop Function ---
def game():
    """Main Pygame game loop, runs on the main thread."""
    global game_state, game_state_lock, control_queue

    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Catch the Falling Squares (Desktop Server)")
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, FONT_SIZE)

    # Pygame sprite groups for managing game objects
    all_sprites = pygame.sprite.Group()
    falling_squares_pygame_group = pygame.sprite.Group() # Dedicated group for falling squares

    paddle = Paddle() # Create the player's paddle
    all_sprites.add(paddle) # Add paddle to the all_sprites group

    # Custom event to trigger spawning new squares
    SPAWN_SQUARE = pygame.USEREVENT + 1
    pygame.time.set_timer(SPAWN_SQUARE, 1000) # Spawn a new square every 1000ms (1 second)

    square_id_counter = 0 # Unique ID counter for new squares (for client tracking)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False # Exit game if window is closed
            if event.type == SPAWN_SQUARE and not game_state['game_over']:
                # Spawn a new square and add it to sprite groups
                square_id_counter += 1
                new_square = FallingSquare(f"sq_{square_id_counter}")
                all_sprites.add(new_square)
                falling_squares_pygame_group.add(new_square)

        # Game logic updates (only if game is not over)
        with game_state_lock: # Ensure thread safety when accessing shared game_state
            if not game_state['game_over']:
                all_sprites.update() # Call update() method on all sprites

                # Check for collisions between paddle and falling squares
                # 'True' means the square will be removed from the group if caught
                caught_squares = pygame.sprite.spritecollide(paddle, falling_squares_pygame_group, True)
                for square in caught_squares:
                    game_state['score'] += 1 # Increase score for each caught square

                # Check for squares that went off screen (missed)
                missed_squares_to_remove = []
                for square in falling_squares_pygame_group:
                    if square.rect.top > SCREEN_HEIGHT:
                        game_state['lives'] -= 1 # Lose a life if square is missed
                        missed_squares_to_remove.append(square) # Mark for removal
                        if game_state['lives'] <= 0:
                            game_state['game_over'] = True # Game over if no lives left
                for square in missed_squares_to_remove:
                    square.kill() # Remove missed squares from all sprite groups

                # Update the 'squares' list in shared game_state for the client
                # Convert Pygame sprite objects back into simple dictionaries for JSON
                game_state['squares'] = [{'x': sq.rect.x, 'y': sq.rect.y, 'id': sq.id} for sq in falling_squares_pygame_group]

                if game_state['lives'] <= 0:
                    game_state['game_over'] = True

        # --- Drawing ---
        screen.fill(BLACK) # Clear screen with black background
        all_sprites.draw(screen) # Draw all sprites

        # Display score and lives on the desktop screen
        score_text = font.render(f"Score: {game_state['score']}", True, WHITE)
        lives_text = font.render(f"Lives: {game_state['lives']}", True, WHITE)
        screen.blit(score_text, (10, 10))
        screen.blit(lives_text, (SCREEN_WIDTH - lives_text.get_width() - 10, 10))

        # Game Over screen logic
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
                    game_state['squares'] = [] # Clear client's squares too

                # Reset Pygame sprite groups and re-create paddle
                all_sprites.empty()
                falling_squares_pygame_group.empty()
                paddle = Paddle() # Create a new paddle instance
                all_sprites.add(paddle)
                # No need to explicitly update game_state['paddle_x'] here, Paddle.__init__ handles it

            elif keys[pygame.K_q]:
                running = False # Quit game on 'Q' press

        pygame.display.flip() # Update the full display Surface to the screen
        clock.tick(FPS) # Control frame rate

    pygame.quit() # Uninitialize Pygame modules

if __name__ == "__main__":
    # 1. Create a new event loop for the WebSocket thread
    websocket_loop = asyncio.new_event_loop()
    # 2. Start the WebSocket server in a separate daemon thread
    websocket_thread = threading.Thread(target=run_websocket_server, args=(websocket_loop,))
    websocket_thread.daemon = True # Daemon threads exit when the main program exits
    websocket_thread.start()

    # 3. Give the WebSocket server a small moment to initialize and start its loop
    time.sleep(0.1)

    # 4. Run the Pygame game loop in the main thread
    game()