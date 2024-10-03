import random
from fastapi import FastAPI, WebSocket
from fastapi.responses import FileResponse
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import asyncio
import time
import os
import pandas as pd
from datetime import datetime, timedelta


tm = time.time()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins, you can restrict this to specific URLs if needed
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)

@app.get('/leaderboard')
async def send_leaderboard():
    data = {
        "all_time": all_time_leaderboard.to_dict(orient="records"), 
        "weekly": weekly_leaderboard.to_dict(orient="records"), 
        "daily": daily_leaderboard.to_dict(orient="records")
    }
    return JSONResponse(content=data)

# Initialize global variables
players = {}
enemies = [
    {"x": 200, "y": 200, "dx": 2, "dy": 2},
    {"x": 400, "y": 400, "dx": -3, "dy": -3},
    {"x": 300, "y": 300, "dx": -2, "dy": -2}
]

leaderboard_file = "leaderboard.csv"
all_time_leaderboard = pd.DataFrame(columns=["name", "score"])
weekly_leaderboard = pd.DataFrame(columns=["name", "score"])
daily_leaderboard = pd.DataFrame(columns=["name", "score"])

# Setup the reset times
weekly_reset_date = datetime(2024, 9, 25)
daily_reset_time = datetime.combine(datetime.now(), datetime.min.time()) + timedelta(hours=12)

# Ensure leaderboard file exists
if not os.path.exists(leaderboard_file):
    pd.DataFrame(columns=["name", "score", "type"]).to_csv(leaderboard_file, index=False)

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

async def reset_leaderboards():
    global weekly_leaderboard, daily_leaderboard, weekly_reset_date, daily_reset_time

    while True:
        now = datetime.now()

        # Reset weekly leaderboard if needed
        if now >= weekly_reset_date:
            weekly_leaderboard = pd.DataFrame(columns=["name", "score"])
            weekly_reset_date += timedelta(weeks=1)  # Schedule next reset

        # Reset daily leaderboard if needed
        if now >= daily_reset_time:
            daily_leaderboard = pd.DataFrame(columns=["name", "score"])
            daily_reset_time = datetime.combine(now, datetime.min.time()) + timedelta(hours=12)  # Next reset at 12:00 PM

        await asyncio.sleep(60)  # Check once a minute

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

            if move["direction"] == "left" and players[player_id]["x"] > 0:
                players[player_id]["x"] -= 5
            elif move["direction"] == "right" and players[player_id]["x"] < 780:
                players[player_id]["x"] += 5
            elif move["direction"] == "up" and players[player_id]["y"] > 0:
                players[player_id]["y"] -= 5
            elif move["direction"] == "down" and players[player_id]["y"] < 580:
                players[player_id]["y"] += 5

            if check_collision(players[player_id]):
                # Save player score and update leaderboards
                save_score(player_name, players[player_id]["score"])
                del players[player_id]

                await websocket.send_text(json.dumps({"action": "redirect", "url": "/index.html"}))
                await websocket.close()
                break

            await broadcast_positions()

    except Exception as e:
        print(f"Error: {e}")
        if player_id in players:
            # Save player score and update leaderboards
            save_score(players[player_id]["name"], players[player_id]["score"])
            del players[player_id]
        await websocket.close()

async def update_score(player_id):
    while player_id in players:
        players[player_id]["score"] += 1
        await asyncio.sleep(1)

async def spawn_enemies():
    while True:
        print(len(players))
        if len(players) > 0:
            enemies.append({
                "x": random.randint(100, 500),
                "y": random.randint(100, 500),
                "dx": random.randint(-3, 3),
                "dy": random.randint(-3, 3)
            })
            print(f"Enemy spawned. Total enemies: {len(enemies)}")
        elif len(enemies) > 2:
            del enemies[3:]
        await asyncio.sleep(10)

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

def check_collision(player):
    player_radius = 10
    for enemy in enemies:
        enemy_radius = 10
        if (abs((player["x"] + player_radius) - (enemy["x"])) <= (player_radius + enemy_radius) and
            abs((player["y"] + player_radius) - (enemy["y"])) <= (player_radius + enemy_radius)):
            return True
    return False

def save_score(name, score):
    global all_time_leaderboard, weekly_leaderboard, daily_leaderboard

    # Update leaderboards
    all_time_leaderboard = update_leaderboard(all_time_leaderboard, name, score)
    weekly_leaderboard = update_leaderboard(weekly_leaderboard, name, score)
    daily_leaderboard = update_leaderboard(daily_leaderboard, name, score)

    # Save to CSV
    leaderboard = pd.DataFrame({"name": [name], "score": [score], "type": ["all-time"]})
    if os.path.exists(leaderboard_file):
        leaderboard.to_csv(leaderboard_file, mode='a', header=False, index=False)
    else:
        leaderboard.to_csv(leaderboard_file, index=False)

def update_leaderboard(leaderboard, name, score):
    if name in leaderboard['name'].values:
        leaderboard.loc[leaderboard['name'] == name, 'score'] = max(leaderboard.loc[leaderboard['name'] == name, 'score'].values[0], score)
    else:
        leaderboard = leaderboard.append({"name": name, "score": score}, ignore_index=True)
    
    return leaderboard.sort_values(by="score", ascending=False).head(3)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(move_enemies())
    asyncio.create_task(spawn_enemies())
    asyncio.create_task(reset_leaderboards())



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
