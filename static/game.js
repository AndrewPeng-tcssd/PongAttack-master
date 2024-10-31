let isRedirected = false; // player is alive
const canvas = document.getElementById('gameCanvas'); // Get the game canvas
const ctx = canvas.getContext('2d'); // Get the 2D context for drawing on the canvas

let players = []; // Array to hold player dada
let enemies = []; // Array to hold enemy data
let direction = { x: 0, y: 0 }; // player direction
const speed = 5;
let shield = false; 

// Get player's name from the url 
const urlParams = new URLSearchParams(window.location.search);
const playerName = urlParams.get('name') || 'Player';

// connect to the server
let socket = new WebSocket(`https://coderlab.work/ws/${encodeURIComponent(playerName)}`); // ws://localhost:8000/ws/${encodeURIComponent(playerName)} https://coderlab.work/ws/${encodeURIComponent(playerName)}

socket.onmessage = function(event) {
    const data = JSON.parse(event.data);
    if (data.action === "redirect") {
        // if the server sends a redirect action, redirect back to the main page
        isRedirected = true;
        window.location.href = data.url;
    } else {
        // Update data
        players = data.players;
        enemies = data.enemies;
        updateLeaderboard(); // Update leaderboard
    }
};

// Render the game on the canvas
function renderGame() {
    ctx.clearRect(0, 0, canvas.width, canvas.height); // Clear the canvas

    // Draw each player
    players.forEach(player => {
        ctx.fillStyle = player.color; // color (random)
        ctx.fillRect(player.x, player.y, 20, 20); // Draw player as a square
        ctx.fillStyle = "black"; // Set color for the text for the player's name
        ctx.font = "14px Arial"; // text font
        ctx.textAlign = "center"; // center the name
        ctx.fillText(player.name, player.x + 10, player.y - 5); // Render player's name above itself
        if (player.shield_active) {
            // Draw a shield around the player if it's activated
            ctx.beginPath();
            ctx.strokeStyle = "#0000FF"; // color blue
            ctx.arc(player.x + 10, player.y + 10, 20, 0, 2 * Math.PI); // circle
            ctx.stroke();
        }
    });

    // Draw enemies
    enemies.forEach(enemy => {
        ctx.beginPath();
        ctx.arc(enemy.x, enemy.y, 10, 0, Math.PI * 2); // Draw enemies as a red circle
        ctx.fillStyle = "red";
        ctx.fill();
        ctx.closePath();
    });
}

// Handle moving
document.addEventListener('keydown', function(e) {
    if (e.key === 'ArrowLeft') direction = { x: -speed, y: 0 }; // Move left
    if (e.key === 'ArrowRight') direction = { x: speed, y: 0 }; // Move right
    if (e.key === 'ArrowUp') direction = { x: 0, y: -speed }; // Move up
    if (e.key === 'ArrowDown') direction = { x: 0, y: speed }; // Move down
    if (e.key === " ") shield = true; // Activate shield
});

document.addEventListener('keyup', function(e) {
    if (e.key === " ") shield = false; // Deactivate shield when space bar is released
});

// Update the player's position and send updated data to the server
function update() {
    if (isRedirected) return; // Stop updating if the player has been redirected (out)

    if (players.length > 0) {
        // Find the current player in the players array
        let player = players.find(p => p.name === playerName);
        if (player) {
            // Update player's position based on direction
            player.x += direction.x;
            player.y += direction.y;

            // Ensure the player stays within the canvas boundaries or it will disappear
            player.x = Math.max(0, Math.min(canvas.width - 20, player.x));
            player.y = Math.max(0, Math.min(canvas.height - 20, player.y));

            // send status to the server
            socket.send(JSON.stringify({ direction: getDirectionKey(), score: player.score, shield_active: shield }));
        }
    }

    renderGame(); // render the updated game
    requestAnimationFrame(update);
}

// Get the current movement direction
function getDirectionKey() {
    if (direction.x < 0) return 'left';
    if (direction.x > 0) return 'right';
    if (direction.y < 0) return 'up';
    if (direction.y > 0) return 'down';
    return null;
}

// Update the leaderboard based on the scores
function updateLeaderboard() {
    const leaderboardBody = document.getElementById('leaderboard-body');
    leaderboardBody.innerHTML = ''; // Clear the leaderboard

    // Sort players by score
    const sortedPlayers = players.sort((a, b) => b.score - a.score);

    // Add each player to the leaderboard
    sortedPlayers.forEach(player => {
        const row = document.createElement('tr');
        row.innerHTML = `<td>${player.name}</td><td>${player.score}</td>`;
        leaderboardBody.appendChild(row);
    });
}

update(); // Start the game loop
