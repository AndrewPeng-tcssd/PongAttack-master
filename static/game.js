let isRedirected = false;
        const canvas = document.getElementById('gameCanvas');
        const ctx = canvas.getContext('2d');

        let players = [];
        let enemies = [];
        let direction = { x: 0, y: 0 };
        const speed = 5;
        let shield = false

        const urlParams = new URLSearchParams(window.location.search);
        const playerName = urlParams.get('name') || 'Player';

        let socket = new WebSocket(`ws://localhost:8000/ws/${encodeURIComponent(playerName)}`); // ws://localhost:8000/ws/${encodeURIComponent(playerName)} https://coderlab.work/ws/${encodeURIComponent(playerName)}

        socket.onmessage = function(event) {
            const data = JSON.parse(event.data);
            if (data.action === "redirect") {
                isRedirected = true;
                window.location.href = data.url;
            } else {
                players = data.players;
                enemies = data.enemies;
                updateLeaderboard();
            }
        };

        function renderGame() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);

            players.forEach(player => {
                ctx.fillStyle = player.color;
                ctx.fillRect(player.x, player.y, 20, 20);
                ctx.fillStyle = "black";
                ctx.font = "14px Arial";
                ctx.textAlign = "center";
                ctx.fillText(player.name, player.x + 10, player.y - 5);
                if (player.shield_active){
                    ctx.beginPath()
                    ctx.strokeStyle = "#0000FF";
                    ctx.arc(player.x + 10, player.y + 10, 20, 0, 2 * Math.PI)
                    ctx.stroke()
                }
            });

            enemies.forEach(enemy => {
                ctx.beginPath();
                ctx.arc(enemy.x, enemy.y, 10, 0, Math.PI * 2);
                ctx.fillStyle = "red";
                ctx.fill();
                ctx.closePath();
            });
        }

        document.addEventListener('keydown', function(e) {
            if (e.key === 'ArrowLeft') direction = { x: -speed, y: 0 };
            if (e.key === 'ArrowRight') direction = { x: speed, y: 0 };
            if (e.key === 'ArrowUp') direction = { x: 0, y: -speed };
            if (e.key === 'ArrowDown') direction = { x: 0, y: speed };
            if (e.key === " ") shield = true;
        });

        document.addEventListener('keyup', function(e) {
            if (e.key === " ") shield = false;  // reset the shield when the space bar is released
        });

        function update() {
            if (isRedirected) return;

            if (players.length > 0) {
                let player = players.find(p => p.name === playerName);
                if (player) {
                    player.x += direction.x;
                    player.y += direction.y;

                    player.x = Math.max(0, Math.min(canvas.width - 20, player.x));
                    player.y = Math.max(0, Math.min(canvas.height - 20, player.y));

                    socket.send(JSON.stringify({ direction: getDirectionKey(), score: player.score, shield_active: shield}));

                }
            }

            renderGame();
            requestAnimationFrame(update);
        }

        function getDirectionKey() {
            if (direction.x < 0) return 'left';
            if (direction.x > 0) return 'right';
            if (direction.y < 0) return 'up';
            if (direction.y > 0) return 'down';
            return null;
        }

        function updateLeaderboard() {
            const leaderboardBody = document.getElementById('leaderboard-body');
            leaderboardBody.innerHTML = '';

            const sortedPlayers = players.sort((a, b) => b.score - a.score);

            sortedPlayers.forEach(player => {
                const row = document.createElement('tr');
                row.innerHTML = `<td>${player.name}</td><td>${player.score}</td>`;
                leaderboardBody.appendChild(row);
            });
        }

        update();