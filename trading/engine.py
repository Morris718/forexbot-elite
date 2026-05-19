import random
from trading.tick_engine import BASE, PIPS, get_snapshot

PATTERNS = [
    "Bullish Engulfing","Bearish Engulfing","Morning Star","Evening Star",
    "Hammer","Shooting Star","Doji","Three White Soldiers","Three Black Crows",
    "Gartley Pattern","Bat Pattern","Head & Shoulders","Double Bottom","Rising Wedge",
]

def generate_signal(pair, user=None):
    snap = get_snapshot()
    price = snap[pair]["mid"] if pair in snap else BASE[pair]
    t_s = random.uniform(45,95); s_s = random.uniform(40,90)
    m_s = random.uniform(50,95); f_s = random.uniform(40,88)
    tw,sw,mw = (0.4,0.3,0.2) if not user else (user.tech_weight/100, user.sentiment_weight/100, user.ml_weight/100)
    fw = max(0,1-tw-sw-mw)
    conf = round(t_s*tw + s_s*sw + m_s*mw + f_s*fw, 1)
    dir_ = "BUY" if conf>62 or (conf>50 and random.random()>0.45) else "SELL"
    dp = PIPS.get(pair,5); atr = price*0.005
    sl = round(price - atr*1.5 if dir_=="BUY" else price + atr*1.5, dp)
    tp = round(price + atr*3.0 if dir_=="BUY" else price - atr*3.0, dp)
    pats = random.sample(PATTERNS, k=random.randint(1,3))
    stype = random.choice(["consensus","consensus","divergence"])
    reasons = []
    if t_s>70: reasons.append(f"Strong TA ({', '.join(pats[:2])})")
    if s_s>70: reasons.append("Positive sentiment")
    if m_s>75: reasons.append("ML high confidence")
    if not reasons: reasons.append("Moderate confluence")
    return {
        "pair":pair,"direction":dir_,"confidence":conf,
        "entry_price":round(price,dp),"stop_loss":sl,"take_profit":tp,
        "tech_score":round(t_s,1),"sentiment_score":round(s_s,1),
        "ml_score":round(m_s,1),"fundamental_score":round(f_s,1),
        "signal_type":stype,"patterns":pats,"reasoning":" | ".join(reasons),
        "risk_reward":round(abs(tp-price)/max(abs(price-sl),0.0001),2),
    }

def get_top_signals(n=6, user=None):
    pairs = random.sample(list(BASE.keys()), k=min(n, len(BASE)))
    return [generate_signal(p, user) for p in pairs]

def get_performance_data():
    months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    return {
        "monthly_pnl":[round(random.uniform(-800,2000),2) for _ in months],"months":months,
        "win_rate":round(random.uniform(72,91),1),"profit_factor":round(random.uniform(1.8,3.2),2),
        "sharpe_ratio":round(random.uniform(1.2,2.8),2),"max_drawdown":round(random.uniform(3,12),2),
        "avg_rr":round(random.uniform(1.5,3.0),2),"total_signals":random.randint(180,420),
    }
