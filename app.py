import os, sys, eventlet
# monkey_patch removed

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path: sys.path.insert(0, ROOT)

from flask import Flask, redirect, url_for
from flask_socketio import SocketIO, emit, join_room, leave_room
from database import db, login_manager

socketio = SocketIO(async_mode='gevent', cors_allowed_origins="*",
                    logger=False, engineio_logger=False, ping_timeout=20, ping_interval=10)

def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY","forex-elite-2024-change-me")
    db_url = os.getenv("DATABASE_URL","sqlite:///forex_bot.db")
    # Fix for Render's postgres:// URLs
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app); login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "warning"
    socketio.init_app(app)
    from auth import auth_bp
    from trading import trading_bp
    from dashboard import dashboard_bp
    from support import support_bp
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(trading_bp, url_prefix="/trading")
    app.register_blueprint(dashboard_bp, url_prefix="/dashboard")
    app.register_blueprint(support_bp, url_prefix="/support")
    @app.route("/")
    def index(): return redirect(url_for("auth.login"))
    @app.route("/health")
    def health(): return {"status":"ok"}, 200
    with app.app_context():
        db.create_all(); print("[+] Database ready.")
    return app

app = create_app()

from trading.tick_engine import start as start_ticks, get_snapshot, get_session_status

# Start tick engine at module load for gunicorn
_engine_started = False
def _ensure_engine():
    global _engine_started
    if not _engine_started:
        start_ticks(socketio, interval=0.8)
        _engine_started = True
        print("[+] Tick engine started.")
_ensure_engine()

@socketio.on("connect", namespace="/live")
def live_connect():
    try:
        emit("snapshot", get_snapshot())
        emit("sessions", get_session_status())
    except Exception as e: print(f"[WS] error: {e}")

@socketio.on("subscribe", namespace="/live")
def live_subscribe(data): join_room((data or {}).get("pair","EUR/USD"))

@socketio.on("unsubscribe", namespace="/live")
def live_unsubscribe(data): leave_room((data or {}).get("pair","EUR/USD"))

_rooms = {}

@socketio.on("connect", namespace="/support")
def sup_connect(): emit("history", [])

@socketio.on("join_support", namespace="/support")
def sup_join(data):
    room = (data or {}).get("room","general"); join_room(room)
    emit("history", _rooms.get(room, []))

@socketio.on("message", namespace="/support")
def sup_message(data):
    import time, random, threading
    if not isinstance(data, dict): return
    room = data.get("room","general")
    msg = {"sender":data.get("sender","User"),"text":data.get("text",""),
           "role":data.get("role","user"),"ts":int(time.time()*1000)}
    _rooms.setdefault(room,[]).append(msg)
    socketio.emit("message", msg, namespace="/support", room=room)
    if msg["role"]=="user":
        def _reply():
            time.sleep(random.uniform(1.5,3.5))
            replies = [
                "Thanks! Let me check that for you right away.",
                "Great question. I'm reviewing your account now.",
                "Could you provide more details about the issue?",
                "Your request has been logged. Response time < 2 min.",
                "I'm pulling up your trade history now.",
                "That issue is being tracked. A fix is coming shortly.",
                "Your withdrawal is processing. Funds arrive in 1-3 days.",
                "The AI engine is running optimally.",
            ]
            agent = {"sender":"Support Agent","text":random.choice(replies),
                     "role":"agent","ts":int(time.time()*1000)}
            _rooms.setdefault(room,[]).append(agent)
            socketio.emit("message", agent, namespace="/support", room=room)
        threading.Thread(target=_reply, daemon=True).start()

if __name__ == "__main__":
    import socket
    def find_free_port(start=5000, end=5020):
        for c in range(start, end):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                try: s.bind(("0.0.0.0", c)); return c
                except OSError: continue
        return 5000
    port = int(os.environ.get("PORT", find_free_port()))
    print(f"\n  FOREXBOT ELITE on http://0.0.0.0:{port}\n")
    socketio.run(app, host="0.0.0.0", port=port, debug=False, use_reloader=False, log_output=False)

