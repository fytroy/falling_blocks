# Catch the Falling Squares Online

## Project Description

Catch the Falling Squares Online is a simple yet engaging real-time web-based game. Players control a paddle at the bottom of the screen with the objective of catching green squares that fall from the top. Missing a square results in losing a life. The game ends when the player runs out of lives. The game features a client-server architecture, where the game logic is managed by a Python server, and players interact through a web browser client.

## Features

*   **Real-time Gameplay:** Game state is synchronized between the server and clients using WebSockets.
*   **Simple Controls:** Players move the paddle left or right.
*   **Score and Lives System:** Track your performance with a score and a limited number of lives.
*   **Game Over & Restart:** Clear indication of game over, with server-side restart capability (desktop server window).
*   **Web-Based Client:** Playable in any modern web browser.
*   **Pygame-Powered Server:** The backend game logic is handled by a Python application using Pygame.

## Technologies Used

*   **Backend (Server):**
    *   Python 3.x
    *   Pygame (for game loop and local server display)
    *   WebSockets (`websockets` library for client-server communication)
*   **Frontend (Client):**
    *   HTML5
    *   CSS3
    *   JavaScript (vanilla)
*   **Deployment (Client):**
    *   The `web_client` is configured for easy deployment on Netlify (see `netlify.toml`).

## Project Structure

```
.
├── server/
│   ├── catchthesquares.py  # Main Python game server logic (Pygame + WebSockets)
│   └── requirements.txt    # Python dependencies for the server
├── web_client/
│   ├── index.html          # HTML structure for the game client
│   ├── style.css           # CSS for styling the game client
│   └── script.js           # JavaScript for client-side logic and server communication
├── netlify.toml            # Configuration for deploying the web_client to Netlify
└── README.md               # This file
```

## Setup and Running Instructions

### 1. Server Setup

The server runs the game logic and communicates with the web clients.

*   **Prerequisites:**
    *   Python 3.7+
*   **Clone the Repository:**
    ```bash
    git clone https://github.com/username/repository.git
    cd repository-name
    ```
*   **Set Up a Virtual Environment (Recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```
*   **Install Dependencies:**
    Navigate to the `server` directory and install the required Python packages:
    ```bash
    cd server
    pip install -r requirements.txt
    ```
*   **Run the Server:**
    ```bash
    python catchthesquares.py
    ```
    By default, the WebSocket server will start on `0.0.0.0:5000`.
    A Pygame window will also open, displaying the server-side view of the game. This window can be used to restart the game by pressing 'R' when the game is over.

*   **Important Server Accessibility:**
    *   If you are running the client on a different device than the server (even on the same network), ensure your server's firewall allows incoming connections on port 5000.
    *   If you want to play over the internet, the server machine needs to be accessible via a public IP address or domain, and port forwarding might be required on your router.

### 2. Client Setup

The client is a web application that connects to the game server.

*   **Configure Server Address:**
    *   Open `web_client/script.js` in a text editor.
    *   **Crucially, you MUST update the `WS_SERVER_URL` constant** to point to the address of your running Python server.
        *   **Local Testing (Server and Client on the same machine):**
            ```javascript
            const WS_SERVER_URL = 'ws://localhost:5000';
            ```
            or
            ```javascript
            const WS_SERVER_URL = 'ws://127.0.0.1:5000';
            ```
        *   **Local Network Testing (Server on one machine, Client on another in the same network):**
            Replace `your-server-local-ip` with the local IP address of the machine running the Python server (e.g., `192.168.1.10`).
            ```javascript
            const WS_SERVER_URL = 'ws://your-server-local-ip:5000';
            ```
        *   **Internet/Deployed Server:**
            Replace `your-server-public-ip-or-domain` with the public IP address or domain name of your server. If your server is behind a firewall or NAT, ensure port 5000 is correctly forwarded.
            ```javascript
            const WS_SERVER_URL = 'ws://your-server-public-ip-or-domain:5000';
            // If you set up SSL/TLS on your WebSocket server, use 'wss://'
            // const WS_SERVER_URL = 'wss://your-server-public-ip-or-domain:your-ssl-port';
            ```

*   **Running the Client:**
    *   **Option A: Local File Access (for testing with a local server)**
        Simply open the `web_client/index.html` file in your web browser.
    *   **Option B: Deploying to Netlify (or any static site host)**
        1.  Push your configured `web_client` folder to a Git repository (e.g., GitHub, GitLab).
        2.  Connect your Git repository to Netlify.
        3.  Netlify will use `netlify.toml` to publish the `web_client` directory.
        4.  Access the game via the URL provided by Netlify. (Ensure `WS_SERVER_URL` in your deployed `script.js` points to your publicly accessible game server).

## How to Play

1.  Ensure the Python server is running and accessible.
2.  Ensure the `WS_SERVER_URL` in `web_client/script.js` is correctly configured to point to your server.
3.  Open `web_client/index.html` in your browser or access the deployed client URL.
4.  The game should connect to the server.
5.  Use the "◀️ Left" and "Right ▶️" buttons on the screen (or touch controls on mobile) to move your paddle.
6.  Catch the green squares that fall from the top.
7.  Avoid missing squares. You have a limited number of lives.
8.  The game ends when you run out of lives.
9.  To restart the game after a "Game Over", press 'R' in the Pygame window running on the server.

## Future Enhancements (Ideas)

*   Client-side "Restart" button that sends a request to the server.
*   Persistent high scores.
*   Different types of falling objects (e.g., power-ups, obstacles).
*   Increasing difficulty over time (e.g., faster squares, more squares).
*   Improved visual feedback and animations.
