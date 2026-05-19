import random
from datetime import datetime, timezone
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from database import db
from auth.models import Position
from trading import trading_bp
from trading.tick_engine import get_snapshot, get_session_status, BASE, PIPS

PAIRS = list(BASE.keys())

NEWS_EVENTS = [
    {"time":"08:30","currency":"USD","event":"Non-Farm Payrolls","impact":"high"},
    {"time":"10:00","currency":"EUR","event":"ECB Rate Decision","impact":"high"},
    {"time":"09:30","currency":"GBP","event":"UK GDP m/m","impact":"medium"},
    {"time":"14:00","currency":"USD","event":"FOMC Minutes","impact":"high"},
    {"time":"01:30","currency":"AUD","event":"RBA Statement","impact":"medium"},
    {"time":"12:30","currency":"CAD","event":"Canada CPI m/m","impact":"medium"},
    {"time":"15:30","currency":"USD","event":"US Core CPI m/m","impact":"high"},
]

def _calc_pnl(pos, current):
    dp = PIPS.get(pos.pair, 5)
    diff = (current - pos.entry_price) if pos.direction=="BUY" else (pos.entry_price - current)
    pip_move = diff / (0.0001 if dp>=4 else 0.01 if dp==3 else 1.0)
    return round(pip_move * pos.pip_value * pos.lot_size * 100, 2)

# ── LIVE TRADING (with URL-safe pair handling) ────────────────────
@trading_bp.route("/live")
@login_required
def live_default():
    return redirect(url_for("trading.live", pair="EUR_USD"))

@trading_bp.route("/live/<path:pair>")
@login_required
def live(pair):
    # Convert URL-safe format (EUR_USD) back to standard (EUR/USD)
    pair = pair.replace("_", "/")
    if pair not in BASE:
        pair = "EUR/USD"

    snap = get_snapshot()
    sessions = get_session_status()
    positions = current_user.positions.filter_by(status="open").all()

    for p in positions:
        if p.pair in snap:
            p.current_price = snap[p.pair]["mid"]
            p.profit_loss = _calc_pnl(p, p.current_price)

    return render_template("trading/live.html",
        snap=snap, sessions=sessions, pairs=PAIRS,
        positions=positions, news=NEWS_EVENTS, active_pair=pair)

# ── POSITIONS PAGE ────────────────────────────────────────────────
@trading_bp.route("/positions")
@login_required
def positions_page():
    snap = get_snapshot()
    open_pos = current_user.positions.filter_by(status="open").all()
    closed_pos = current_user.positions.filter_by(status="closed").order_by(Position.closed_at.desc()).limit(50).all()

    total_open_pnl = 0
    for p in open_pos:
        if p.pair in snap:
            p.current_price = snap[p.pair]["mid"]
            p.profit_loss = _calc_pnl(p, p.current_price)
            total_open_pnl += p.profit_loss

    total_closed_pnl = sum(p.profit_loss for p in closed_pos)

    return render_template("positions/positions.html",
        open_pos=open_pos, closed_pos=closed_pos,
        total_open_pnl=total_open_pnl, total_closed_pnl=total_closed_pnl,
        snap=snap, pairs=PAIRS)

# ── OPEN POSITION ────────────────────────────────────────────────
@trading_bp.route("/positions/open", methods=["POST"])
@login_required
def open_position():
    pair = request.form.get("pair","EUR/USD")
    direction = request.form.get("direction","BUY").upper()
    try:
        lot_size = float(request.form.get("lot_size", 0.10))
        sl_raw = request.form.get("stop_loss","").strip()
        tp_raw = request.form.get("take_profit","").strip()
        snap = get_snapshot()
        if pair not in snap:
            flash("Invalid pair.","danger")
            return redirect(url_for("trading.positions_page"))
        entry = snap[pair]["ask"] if direction=="BUY" else snap[pair]["bid"]
        margin_needed = lot_size * 1000
        bal = current_user.demo_balance if current_user.demo_mode else current_user.balance
        if margin_needed > bal:
            flash(f"Insufficient margin. Need ${margin_needed:,.0f}.","danger")
            return redirect(url_for("trading.positions_page"))
        pos = Position(
            user_id=current_user.id, pair=pair, direction=direction,
            lot_size=lot_size, entry_price=entry, current_price=entry,
            stop_loss=float(sl_raw) if sl_raw else None,
            take_profit=float(tp_raw) if tp_raw else None,
            pip_value=10.0, is_demo=current_user.demo_mode,
        )
        db.session.add(pos); db.session.commit()
        icon = "🟢" if direction=="BUY" else "🔴"
        flash(f"{icon} {direction} {lot_size} lot {pair} opened @ {entry}","success")
    except Exception as e:
        flash(f"Error: {e}","danger")
    safe_pair = pair.replace("/","_")
    return redirect(request.form.get("redirect", url_for("trading.live", pair=safe_pair)))

# ── CLOSE POSITION ───────────────────────────────────────────────
@trading_bp.route("/positions/close/<int:pos_id>", methods=["POST"])
@login_required
def close_position(pos_id):
    pos = Position.query.filter_by(id=pos_id, user_id=current_user.id, status="open").first()
    if not pos:
        flash("Position not found.","danger")
        return redirect(url_for("trading.positions_page"))
    snap = get_snapshot()
    close = snap[pos.pair]["bid"] if pos.direction=="BUY" else snap[pos.pair]["ask"]
    pnl = _calc_pnl(pos, close)
    pos.status = "closed"
    pos.close_price = close
    pos.closed_at = datetime.now(timezone.utc)
    pos.profit_loss = pnl
    if pos.is_demo:
        current_user.demo_balance += pnl
    else:
        current_user.balance += pnl
    current_user.total_trades += 1
    if pnl > 0: current_user.winning_trades += 1
    if current_user.total_trades > 0:
        current_user.win_rate = round(current_user.winning_trades/current_user.total_trades*100, 1)
    current_user.total_profit_loss += pnl
    db.session.commit()
    col = "success" if pnl>=0 else "danger"
    flash(f"Position closed. P&L: {'+'if pnl>=0 else ''}{pnl:.2f}",col)
    return redirect(request.form.get("redirect", url_for("trading.positions_page")))

# ── CLOSE ALL ────────────────────────────────────────────────────
@trading_bp.route("/positions/close-all", methods=["POST"])
@login_required
def close_all_positions():
    snap = get_snapshot()
    open_pos = current_user.positions.filter_by(status="open").all()
    total_pnl = 0
    for pos in open_pos:
        close = snap[pos.pair]["bid"] if pos.direction=="BUY" else snap[pos.pair]["ask"]
        pnl = _calc_pnl(pos, close)
        pos.status = "closed"
        pos.close_price = close
        pos.closed_at = datetime.now(timezone.utc)
        pos.profit_loss = pnl
        if pos.is_demo: current_user.demo_balance += pnl
        else: current_user.balance += pnl
        current_user.total_trades += 1
        if pnl > 0: current_user.winning_trades += 1
        total_pnl += pnl
    if current_user.total_trades > 0:
        current_user.win_rate = round(current_user.winning_trades/current_user.total_trades*100, 1)
    current_user.total_profit_loss += total_pnl
    db.session.commit()
    col = "success" if total_pnl>=0 else "danger"
    flash(f"All {len(open_pos)} positions closed. Total P&L: {'+'if total_pnl>=0 else ''}{total_pnl:.2f}",col)
    return redirect(url_for("trading.positions_page"))

# ── API ENDPOINTS ────────────────────────────────────────────────
@trading_bp.route("/api/snapshot")
@login_required
def api_snapshot():
    return jsonify(get_snapshot())

@trading_bp.route("/api/positions")
@login_required
def api_positions():
    snap = get_snapshot()
    positions = current_user.positions.filter_by(status="open").all()
    out = []
    for p in positions:
        mid = snap[p.pair]["mid"] if p.pair in snap else p.entry_price
        pnl = _calc_pnl(p, mid)
        out.append({
            "id":p.id,"pair":p.pair,"direction":p.direction,
            "lot_size":p.lot_size,"entry_price":p.entry_price,
            "current_price":mid,"stop_loss":p.stop_loss,
            "take_profit":p.take_profit,"profit_loss":pnl,
            "is_demo":p.is_demo,"opened_at":p.opened_at.strftime("%H:%M:%S"),
        })
    return jsonify(out)

# ── OTHER PAGES ──────────────────────────────────────────────────
@trading_bp.route("/signals")
@login_required
def signals():
    from trading.engine import get_top_signals
    sigs = get_top_signals(9, current_user)
    sessions = get_session_status()
    return render_template("trading/signals.html", signals=sigs, sessions=sessions, news=NEWS_EVENTS, pairs=PAIRS)

@trading_bp.route("/markets")
@login_required
def markets():
    snap = get_snapshot(); sessions = get_session_status()
    return render_template("trading/markets.html", prices=snap, sessions=sessions, pairs=PAIRS)

@trading_bp.route("/analytics")
@login_required
def analytics():
    from trading.engine import get_performance_data
    return render_template("analytics/analytics.html", perf=get_performance_data())

@trading_bp.route("/backtest")
@login_required
def backtest():
    return render_template("analytics/backtest.html", pairs=PAIRS)

@trading_bp.route("/settings")
@login_required
def settings():
    return render_template("settings/settings.html", pairs=PAIRS)

@trading_bp.route("/settings/save", methods=["POST"])
@login_required
def save_settings():
    current_user.risk_appetite = request.form.get("risk_appetite","moderate")
    current_user.preferred_session = request.form.get("preferred_session","all")
    try:
        tw=int(request.form.get("tech_weight",40))
        sw=int(request.form.get("sentiment_weight",30))
        mw=int(request.form.get("ml_weight",30))
        if tw+sw+mw!=100:
            flash("Weights must sum to 100%.","warning"); return redirect(url_for("trading.settings"))
        current_user.tech_weight=tw; current_user.sentiment_weight=sw; current_user.ml_weight=mw
    except ValueError: pass
    db.session.commit(); flash("Settings saved.","success")
    return redirect(url_for("trading.settings"))
