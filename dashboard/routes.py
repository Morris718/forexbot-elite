from datetime import datetime, timezone
from flask import render_template
from flask_login import login_required, current_user
from dashboard import dashboard_bp
from trading.tick_engine import get_snapshot, get_session_status
from trading.engine import get_top_signals, get_performance_data
from trading.routes import NEWS_EVENTS

@dashboard_bp.route("/")
@login_required
def index():
    open_pos = current_user.positions.filter_by(status="open").all()
    return render_template("dashboard/index.html",
        signals=get_top_signals(3, current_user),
        prices=get_snapshot(), sessions=get_session_status(),
        perf=get_performance_data(), news=NEWS_EVENTS[:4],
        now=datetime.now(timezone.utc), open_pos_count=len(open_pos))
