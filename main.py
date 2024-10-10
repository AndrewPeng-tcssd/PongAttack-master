import random
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import pandas as pd
import asyncio
import json

app = FastAPI()

# CORS settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

leaderboard_file = "leaderboard.csv"
all_time_leaderboard = pd.DataFrame(columns=["name", "score"])

# Ensure leaderboard file exists
if not os.path.exists(leaderboard_file):
    pd.DataFrame(columns=["name", "score"]).to_csv(leaderboard_file, index=False)
else:
    all_time_leaderboard = pd.read_csv(leaderboard_file)

@app.get('/leaderboard')
async def send_leaderboard():
    # Load the leaderboard and return top 10 players
    leaderboard_df = pd.read_csv(leaderboard_file)
    top_10 = leaderboard_df.sort_values(by="score", ascending=False).head(10).to_dict(orient="records")
    return JSONResponse(content={"all_time": top_10})

# Initialize global variables
players = {}
enemies = [
    {"x": 200, "y": 200, "dx": 2, "dy": 2},
    {"x": 400, "y": 400, "dx": -3, "dy": -3},
    {"x": 300, "y": 300, "dx": -2, "dy": -2}
]

# Helper functions
def random_color():
    return "#{:06x}".format(random.randint(0, 0xFFFFFF))

async def move_enemies():
    while True:
        for enemy in enemies:
            enemy["x"] += enemy["dx"]
            enemy["y"] += enemy["dy"]

            if enemy["x"] <= 0 or enemy["x"] >= 780:
                enemy["dx"] *= -1

            if enemy["y"] <= 0 or enemy["y"] >= 580:
                enemy["dy"] *= -1

        await broadcast_positions()
        await asyncio.sleep(0.016)

@app.websocket("/ws/{player_name}")
async def websocket_endpoint(websocket: WebSocket, player_name: str):
    await websocket.accept()
    player_id = id(websocket)
    players[player_id] = {
        "x": 100,
        "y": 100,
        "id": player_id,
        "color": random_color(),
        "name": player_name,
        "score": 0,
        "websocket": websocket
    }
    asyncio.create_task(update_score(player_id))

    await send_initial_positions(websocket)

    try:
        while True:
            data = await websocket.receive_text()
            move = json.loads(data)

            # Update player's direction
            if move.get("direction") == "left" and players[player_id]["x"] > 0:
                players[player_id]["x"] -= 5
            elif move.get("direction") == "right" and players[player_id]["x"] < 780:
                players[player_id]["x"] += 5
            elif move.get("direction") == "up" and players[player_id]["y"] > 0:
                players[player_id]["y"] -= 5
            elif move.get("direction") == "down" and players[player_id]["y"] < 580:
                players[player_id]["y"] += 5

            # Update player's score
            if "score" in move:
                players[player_id]["score"] = move["score"]

            # Check for collision and redirect player
            if check_collision(players[player_id]):
                await handle_player_disconnect(player_id, websocket)
                break

            await broadcast_positions()

    except WebSocketDisconnect:
        await handle_player_disconnect(player_id, websocket)

async def update_score(player_id):
    while player_id in players:
        players[player_id]["score"] += 1
        await broadcast_positions()
        await asyncio.sleep(1)

async def send_initial_positions(websocket: WebSocket):
    safe_players = [
        {"x": player["x"], "y": player["y"], "color": player["color"], "name": player["name"], "score": player["score"]}
        for player in players.values()
    ]
    data = json.dumps({"players": safe_players, "enemies": enemies})
    await websocket.send_text(data)

async def broadcast_positions():
    safe_players = [
        {"x": player["x"], "y": player["y"], "color": player["color"], "name": player["name"], "score": player["score"]}
        for player in players.values()
    ]
    data = json.dumps({"players": safe_players, "enemies": enemies})

    for player in list(players.values()):
        try:
            await player["websocket"].send_text(data)
        except Exception as e:
            print(f"Error sending data to player: {e}")

            # Ensure player is removed if an error occurs
            await handle_player_disconnect(player["id"], player["websocket"])

async def handle_player_disconnect(player_id, websocket):
    if player_id in players:
        save_score(players[player_id]["name"], players[player_id]["score"])
        del players[player_id]
        try:
            await websocket.send_text(json.dumps({"action": "redirect", "url": "https://coderlab.work/pong"}))
        except Exception as e:
            print(f"Error redirecting player: {e}")
        finally:
            await websocket.close()

def check_collision(player):
    player_radius = 10
    for enemy in enemies:
        enemy_radius = 10
        if (abs((player["x"] + player_radius) - (enemy["x"])) <= (player_radius + enemy_radius) and
            abs((player["y"] + player_radius) - (enemy["y"])) <= (player_radius + enemy_radius)):
            return True
    return False

async def spawn_enemies():
    while True:
        if len(players) > 0:
            enemies.append({
                "x": random.randint(100, 500),
                "y": random.randint(100, 500),
                "dx": random.choice([-3, -2, 2, 3]),
                "dy": random.choice([-3, -2, 2, 3])
            })
        elif len(enemies) > 3:
            del enemies[3:]
        await asyncio.sleep(10)

def save_score(name, score):
    global all_time_leaderboard

    leaderboard_df = pd.read_csv(leaderboard_file)
    if name in leaderboard_df['name'].values:
        leaderboard_df.loc[leaderboard_df['name'] == name, 'score'] = leaderboard_df.loc[leaderboard_df['name'] == name, 'score'].combine(score, max)
    else:
        leaderboard_df = pd.concat([leaderboard_df, pd.DataFrame([{"name": name, "score": score}])], ignore_index=True)

    leaderboard_df.to_csv(leaderboard_file, index=False)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(move_enemies())
    asyncio.create_task(spawn_enemies())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
