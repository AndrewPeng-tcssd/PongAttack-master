const socket = io('http://127.0.0.1:8000');
const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');
canvas.width = window.innerWidth;
canvas.height = window.innerHeight;

let players = {};

// Listen for updates from the server
socket.on('players_update', (data) => {
    players = data;
});

// Function to draw the players on the canvas
function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    for (let playerId in players) {
        const player = players[playerId];
        ctx.fillStyle = 'blue';
        ctx.fillRect(player.x, player.y, 20, 20); // Draw each player as a square
    }

    // Keep updating the canvas
    requestAnimationFrame(draw);
}

// Start the game loop
requestAnimationFrame(draw);

// Handle player movement with arrow keys
document.addEventListener('keydown', (e) => {
    const move = { dx: 0, dy: 0 };
    if (e.key === 'ArrowUp') move.dy = -10;
    if (e.key === 'ArrowDown') move.dy = 10;
    if (e.key === 'ArrowLeft') move.dx = -10;
    if (e.key === 'ArrowRight') move.dx = 10;
    socket.emit('move', move);
});
 