async function fetchLeaderboards() {
    const response = await fetch('https://coderlab.work/leaderboard');  // Fetch leaderboard from FastAPI
    const data = await response.json();

    updateLeaderboard('all-time-leaderboard', data.all_time);
}

function updateLeaderboard(elementId, leaderboardData) {
    const leaderboardBody = document.getElementById(elementId).querySelector('tbody');
    leaderboardBody.innerHTML = '';  // Clear existing entries

    leaderboardData.forEach(player => {
        const row = document.createElement('tr');
        row.innerHTML = `<td>${player.name}</td><td>${player.score}</td>`;
        leaderboardBody.appendChild(row);
    });
}

// Fetch leaderboards when the page loads
fetchLeaderboards();

// Reload leaderboards every 10000 miliseconds (10 seconds)
setInterval(fetchLeaderboards, 10000);

// Join Game button
document.getElementById('joinGame').addEventListener('click', function() {
    const playerName = prompt("Enter your name:");
    if (playerName) {
        // Redirect to the game
        window.location.href = `game.html?name=${encodeURIComponent(playerName)}`;
    }
});