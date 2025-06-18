// --- Configuration ---
// !!! IMPORTANT: Replace with the actual public IP/domain and port of your Python server !!!
// If your Python server runs on your home PC with public IP 192.168.1.100 and port 5000:
// const WS_SERVER_URL = 'ws://192.168.1.100:5000';
// If deployed to a cloud server with a domain:
// const WS_SERVER_URL = 'wss://your-cloud-server.com:5000'; // Use wss for HTTPS if server supports it
// For local testing (if client and server are on the same machine):
const WS_SERVER_URL = 'ws://localhost:5000'; // Default for local testing

// These must match the dimensions used in style.css for the game-display element
const CLIENT_DISPLAY_WIDTH = 320;
const CLIENT_DISPLAY_HEIGHT = 240;

// These must match the dimensions used by the Pygame server
const SERVER_SCREEN_WIDTH = 800;
const SERVER_SCREEN_HEIGHT = 600;

// --- DOM Elements ---
let socket;
const statusDiv = document.getElementById('status');
const scoreSpan = document.getElementById('score');
const livesSpan = document.getElementById('lives');
const paddleElement = document.getElementById('paddle');
const squaresContainer = document.getElementById('squares-container');
const gameOverlay = document.getElementById('game-overlay');
const overlayText = gameOverlay.querySelector('p:last-child'); // The message below "GAME OVER!"

// --- WebSocket Connection Logic ---
function connectWebSocket() {
    // If socket exists and is open, no need to reconnect
    if (socket && socket.readyState === WebSocket.OPEN) {
        return;
    }

    statusDiv.textContent = 'Connecting...';
    // Attempt to connect to the WebSocket server
    socket = new WebSocket(WS_SERVER_URL);

    socket.onopen = (event) => {
        statusDiv.textContent = 'Connected to game server.';
        gameOverlay.classList.add('hidden'); // Hide overlay on connect
        console.log('WebSocket opened:', event);
    };

    socket.onmessage = (event) => {
        const gameState = JSON.parse(event.data);
        updateGameDisplay(gameState);
    };

    socket.onclose = (event) => {
        statusDiv.textContent = `Disconnected. Code: ${event.code}. Reason: ${event.reason || 'Unknown'}. Retrying...`;
        gameOverlay.classList.remove('hidden'); // Show overlay on disconnect
        overlayText.textContent = 'Disconnected. Retrying...';
        console.log('WebSocket closed:', event);
        // Attempt to reconnect after a delay
        setTimeout(connectWebSocket, 3000);
    };

    socket.onerror = (error) => {
        statusDiv.textContent = 'Connection error. Retrying...';
        gameOverlay.classList.remove('hidden'); // Show overlay on error
        overlayText.textContent = 'Connection error. Retrying...';
        console.error('WebSocket error:', error);
        socket.close(); // Force close to trigger onclose and retry
    };
}

// --- Send Control Input to Server ---
function sendControl(direction) {
    if (socket && socket.readyState === WebSocket.OPEN) {
        // Send a JSON message with the control type and direction
        socket.send(JSON.stringify({ type: 'control', direction: direction }));
    } else {
        console.warn('WebSocket not open. Cannot send control:', direction);
        statusDiv.textContent = 'Not connected. Trying to reconnect...';
    }
}

// --- Update Client Display Based on Server Game State ---
function updateGameDisplay(gameState) {
    scoreSpan.textContent = gameState.score;
    livesSpan.textContent = gameState.lives;

    // Scale server's paddle X coordinate to client's display width
    // Server paddle_x is relative to SERVER_SCREEN_WIDTH (800)
    // Client paddle should be relative to CLIENT_DISPLAY_WIDTH (320)
    const scaledPaddleX = (gameState.paddle_x / SERVER_SCREEN_WIDTH) * CLIENT_DISPLAY_WIDTH;
    paddleElement.style.left = `${scaledPaddleX}px`;

    // Clear old squares from the display
    squaresContainer.innerHTML = '';

    // Add new squares based on the game state received from the server
    gameState.squares.forEach(sq => {
        const squareDiv = document.createElement('div');
        squareDiv.className = 'square';

        // Scale square X and Y coordinates to client's display dimensions
        const scaledSquareX = (sq.x / SERVER_SCREEN_WIDTH) * CLIENT_DISPLAY_WIDTH;
        const scaledSquareY = (sq.y / SERVER_SCREEN_HEIGHT) * CLIENT_DISPLAY_HEIGHT;

        squareDiv.style.left = `${scaledSquareX}px`;
        squareDiv.style.top = `${scaledSquareY}px`;
        squaresContainer.appendChild(squareDiv);
    });

    // Show/hide game over overlay
    if (gameState.game_over) {
        gameOverlay.classList.remove('hidden');
        overlayText.textContent = 'Press "R" on desktop server to restart';
    } else {
        gameOverlay.classList.add('hidden');
    }
}

// --- Event Listeners for Controls ---
document.getElementById('leftButton').addEventListener('mousedown', () => sendControl('left'));
document.getElementById('rightButton').addEventListener('mousedown', () => sendControl('right'));

// Add touch events for mobile devices
document.getElementById('leftButton').addEventListener('touchstart', (e) => {
    e.preventDefault(); // Prevent default touch behavior (like zooming)
    sendControl('left');
});
document.getElementById('rightButton').addEventListener('touchstart', (e) => {
    e.preventDefault(); // Prevent default touch behavior
    sendControl('right');
});

// Initial connection attempt when the script loads
connectWebSocket();