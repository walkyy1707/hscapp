from fastapi import FastAPI, HTTPException, Depends, Query, Form, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
import sqlite3
import hashlib
import hmac
from datetime import date
import os
import json
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

app = FastAPI()

# Serve frontend
app.mount("/static", StaticFiles(directory="build/static"), name="static")

@app.get("/", include_in_schema=False)
async def serve_index():
    return FileResponse("build/index.html")

@app.get("/{path:path}", include_in_schema=False)
async def serve_frontend(path: str):
    return FileResponse("build/index.html")

# Database setup
conn = sqlite3.connect('abmc.db', check_same_thread=False)
cursor = conn.cursor()

# Create tables
cursor.executescript('''
CREATE TABLE IF NOT EXISTS users (
    telegram_id TEXT PRIMARY KEY,
    points INTEGER DEFAULT 0,
    tickets INTEGER DEFAULT 1,
    last_ticket_date DATE,
    referrer_id TEXT
);
CREATE TABLE IF NOT EXISTS missions (
    mission_id INTEGER PRIMARY KEY AUTOINCREMENT,
    description TEXT,
    link TEXT,
    points_reward INTEGER
);
CREATE TABLE IF NOT EXISTS user_missions (
    user_id TEXT,
    mission_id INTEGER,
    PRIMARY KEY (user_id, mission_id)
);
''')
conn.commit()

# Pydantic models
class User(BaseModel):
    telegram_id: str
    points: int
    tickets: int
    last_ticket_date: str
    referrer_id: str | None

class Mission(BaseModel):
    mission_id: int
    description: str
    link: str
    points_reward: int

# Authentication
security = HTTPBearer()
BOT_TOKEN = "7583620870:AAEY03Ni_wyZX0HTPfHP6LJ8PqGJJtdMND0"

def verify_init_data(init_data: str):
    params = dict(p.split('=') for p in init_data.split('&'))
    check_hash = params.pop('hash')
    data_check_string = '\n'.join(f"{k}={v}" for k, v in sorted(params.items()))
    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return calculated_hash == check_hash

def get_user_id_for_rate_limit(request: Request):
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        init_data = auth_header[7:]
        params = dict(p.split('=') for p in init_data.split('&'))
        user_str = params.get('user')
        if user_str:
            user_data = json.loads(user_str)
            return user_data['id']
    return "anonymous"

limiter = Limiter(key_func=get_user_id_for_rate_limit)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    init_data = credentials.credentials
    if not verify_init_data(init_data):
        raise HTTPException(status_code=401, detail="Invalid initData")
    params = dict(p.split('=') for p in init_data.split('&'))
    user_data = json.loads(params['user'])  # Replaced eval with json.loads
    return user_data['id']

# Admin authentication
admin_security = HTTPBasic()

def verify_admin(credentials: HTTPBasicCredentials = Depends(admin_security)):
    correct_username = "admin"
    correct_password = "password123"  # Use environment variables in production
    if credentials.username != correct_username or credentials.password != correct_password:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True

# APIs
@app.get("/user")
async def get_user(current_user: str = Depends(get_current_user), start_param: str = Query(None)):
    cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (current_user,))
    user = cursor.fetchone()
    if not user:
        referrer_id = None
        if start_param and start_param.startswith("ref_") and start_param[4:] != current_user:
            referrer_id = start_param[4:]
            cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (referrer_id,))
            if not cursor.fetchone():
                referrer_id = None
        cursor.execute("INSERT INTO users (telegram_id, last_ticket_date, referrer_id) VALUES (?, ?, ?)",
                       (current_user, date.today().isoformat(), referrer_id))
        conn.commit()
        user = (current_user, 0, 1, date.today().isoformat(), referrer_id)
    return User(telegram_id=user[0], points=user[1], tickets=user[2], last_ticket_date=user[3], referrer_id=user[4])

@app.post("/claim_ticket")
async def claim_ticket(current_user: str = Depends(get_current_user)):
    cursor.execute("SELECT last_ticket_date, tickets FROM users WHERE telegram_id = ?", (current_user,))
    user = cursor.fetchone()
    today = date.today()
    if date.fromisoformat(user[0]) < today:
        new_tickets = min(user[1] + 1, 7)
        cursor.execute("UPDATE users SET tickets = ?, last_ticket_date = ? WHERE telegram_id = ?",
                       (new_tickets, today.isoformat(), current_user))
        conn.commit()
        return {"tickets": new_tickets}
    return {"tickets": user[1]}

@app.post("/play_game")
@limiter.limit("10/minute")
async def play_game(request: Request, current_user: str = Depends(get_current_user)):
    cursor.execute("SELECT tickets FROM users WHERE telegram_id = ?", (current_user,))
    tickets = cursor.fetchone()[0]
    if tickets > 0:
        cursor.execute("UPDATE users SET tickets = tickets - 1 WHERE telegram_id = ?", (current_user,))
        conn.commit()
        return {"message": "Game started"}
    raise HTTPException(status_code=400, detail="No tickets")

@app.post("/submit_score")
@limiter.limit("10/minute")
async def submit_score(score: int, request: Request, current_user: str = Depends(get_current_user)):
    if score < 0 or score > 500:  # Reasonable limit for 25s game
        raise HTTPException(status_code=400, detail="Invalid score")
    cursor.execute("UPDATE users SET points = points + ? WHERE telegram_id = ?", (score, current_user))
    cursor.execute("SELECT referrer_id FROM users WHERE telegram_id = ?", (current_user,))
    referrer_id = cursor.fetchone()[0]
    if referrer_id:
        referral_points = score // 10
        cursor.execute("UPDATE users SET points = points + ? WHERE telegram_id = ?", (referral_points, referrer_id))
    conn.commit()
    return {"points_added": score}

@app.get("/missions")
async def get_missions():
    cursor.execute("SELECT * FROM missions")
    missions = cursor.fetchall()
    return [Mission(mission_id=m[0], description=m[1], link=m[2], points_reward=m[3]) for m in missions]

@app.get("/user_missions")
async def get_user_missions(current_user: str = Depends(get_current_user)):
    cursor.execute("SELECT mission_id FROM user_missions WHERE user_id = ?", (current_user,))
    return [m[0] for m in cursor.fetchall()]

@app.post("/complete_mission")
@limiter.limit("20/minute")
async def complete_mission(mission_id: int, request: Request, current_user: str = Depends(get_current_user)):
    cursor.execute("SELECT points_reward FROM missions WHERE mission_id = ?", (mission_id,))
    mission = cursor.fetchone()
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    cursor.execute("SELECT * FROM user_missions WHERE user_id = ? AND mission_id = ?", (current_user, mission_id))
    if cursor.fetchone():
        raise HTTPException(status_code=400, detail="Mission already completed")
    points_reward = mission[0]
    cursor.execute("UPDATE users SET points = points + ? WHERE telegram_id = ?", (points_reward, current_user))
    cursor.execute("INSERT INTO user_missions (user_id, mission_id) VALUES (?, ?)", (current_user, mission_id))
    cursor.execute("SELECT referrer_id FROM users WHERE telegram_id = ?", (current_user,))
    referrer_id = cursor.fetchone()[0]
    if referrer_id:
        referral_points = points_reward // 10
        cursor.execute("UPDATE users SET points = points + ? WHERE telegram_id = ?", (referral_points, referrer_id))
    conn.commit()
    return {"points_awarded": points_reward}

@app.get("/referrals")
async def get_referrals(current_user: str = Depends(get_current_user)):
    cursor.execute("SELECT COUNT(*) FROM users WHERE referrer_id = ?", (current_user,))
    return {"referrals": cursor.fetchone()[0]}

@app.get("/leaderboard")
async def get_leaderboard(limit: int = 10):
    cursor.execute("SELECT telegram_id, points FROM users ORDER BY points DESC LIMIT ?", (limit,))
    leaders = cursor.fetchall()
    return [{"telegram_id": l[0], "points": l[1]} for l in leaders]

# Admin routes
@app.get("/admin", dependencies=[Depends(verify_admin)])
async def admin_panel():
    cursor.execute("SELECT * FROM missions")
    missions = cursor.fetchall()
    mission_list = "".join([f"<li>{m[1]} - {m[2]} - {m[3]} points <a href='/admin/delete_mission?mission_id={m[0]}'>Delete</a></li>" for m in missions])
    return HTMLResponse(f"""
    <html>
    <body>
    <h1>Admin Panel</h1>
    <form action="/admin/add_mission" method="post">
        <input type="text" name="description" placeholder="Description" />
        <input type="text" name="link" placeholder="Link" />
        <input type="number" name="points_reward" placeholder="Points" />
        <button type="submit">Add Mission</button>
    </form>
    <h2>Existing Missions</h2>
    <ul>{mission_list}</ul>
    </body>
    </html>
    """)

@app.post("/admin/add_mission", dependencies=[Depends(verify_admin)])
async def add_mission(description: str = Form(...), link: str = Form(...), points_reward: int = Form(...)):
    cursor.execute("INSERT INTO missions (description, link, points_reward) VALUES (?, ?, ?)", (description, link, points_reward))
    conn.commit()
    return {"message": "Mission added"}

@app.get("/admin/delete_mission", dependencies=[Depends(verify_admin)])
async def delete_mission(mission_id: int):
    cursor.execute("DELETE FROM missions WHERE mission_id = ?", (mission_id,))
    conn.commit()
    return {"message": "Mission deleted"}