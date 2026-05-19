import time, math, random, threading
from datetime import datetime, timezone

BASE = {
    "EUR/USD":1.08420,"GBP/USD":1.27340,"USD/JPY":149.820,
    "AUD/USD":0.65210,"USD/CAD":1.36120,"NZD/USD":0.59870,
    "EUR/GBP":0.85110,"EUR/JPY":162.450,"GBP/JPY":190.760,
    "USD/CHF":0.89340,"XAU/USD":2312.50,"XAG/USD":27.430,
    "BTC/USD":67420.0,"ETH/USD":3521.0,"US30":39850.0,"SPX500":5234.0,
}

PIPS = {
    "EUR/USD":5,"GBP/USD":5,"USD/JPY":3,"AUD/USD":5,"USD/CAD":5,
    "NZD/USD":5,"EUR/GBP":5,"EUR/JPY":3,"GBP/JPY":3,"USD/CHF":5,
    "XAU/USD":2,"XAG/USD":3,"BTC/USD":1,"ETH/USD":2,"US30":1,"SPX500":2,
}

SPREAD = {
    "EUR/USD":0.00015,"GBP/USD":0.00018,"USD/JPY":0.018,
    "AUD/USD":0.00022,"USD/CAD":0.00025,"NZD/USD":0.00025,
    "EUR/GBP":0.00016,"EUR/JPY":0.025,"GBP/JPY":0.030,
    "USD/CHF":0.00020,"XAU/USD":0.35,"XAG/USD":0.04,
    "BTC/USD":8.0,"ETH/USD":1.2,"US30":2.0,"SPX500":0.5,
}

VOLATILITY = {
    "EUR/USD":0.00008,"GBP/USD":0.00012,"USD/JPY":0.012,
    "AUD/USD":0.00010,"USD/CAD":0.00010,"NZD/USD":0.00010,
    "EUR/GBP":0.00008,"EUR/JPY":0.018,"GBP/JPY":0.022,
    "USD/CHF":0.00009,"XAU/USD":0.28,"XAG/USD":0.032,
    "BTC/USD":28.0,"ETH/USD":2.8,"US30":12.0,"SPX500":1.8,
}

SESSIONS = {
    "Sydney":{"open":21,"close":6},
    "Tokyo":{"open":0,"close":9},
    "London":{"open":8,"close":17},
    "New York":{"open":13,"close":22},
}

_prices = {p: {"mid":BASE[p], "history":[BASE[p]]*120} for p in BASE}
_lock = threading.Lock()
_running = False
_thread = None
_socketio = None

def _session_mult():
    h = datetime.now(timezone.utc).hour
    active = sum(
        1 for s in SESSIONS.values()
        if (s["open"]<s["close"] and s["open"]<=h<s["close"])
        or (s["open"]>=s["close"] and (h>=s["open"] or h<s["close"]))
    )
    return 0.6 + active * 0.35

def _tick():
    mult = _session_mult()
    with _lock:
        result = {}
        for pair, vol in VOLATILITY.items():
            state = _prices[pair]
            mid = state["mid"]
            base = BASE[pair]
            revert = (base - mid) * 0.0008
            shock = random.gauss(0, vol * mult)
            mid = max(base*0.97, min(base*1.03, mid + revert + shock))
            spread = SPREAD[pair]
            dp = PIPS[pair]
            bid = round(mid - spread/2, dp)
            ask = round(mid + spread/2, dp)
            change_pct = round((mid - base) / base * 100, 3)
            hist = state["history"][-179:] + [round(mid, dp)]
            state["mid"] = mid
            state["history"] = hist
            result[pair] = {
                "pair":pair,"bid":bid,"ask":ask,"mid":round(mid,dp),
                "spread":round(spread,dp),"change_pct":change_pct,
                "trend":"up" if change_pct>=0 else "down",
                "high":round(max(hist[-60:]),dp),"low":round(min(hist[-60:]),dp),
                "history":hist,"ts":int(time.time()*1000),
            }
        return result

def get_snapshot():
    with _lock:
        result = {}
        for pair in BASE:
            state = _prices[pair]
            mid = state["mid"]
            base = BASE[pair]
            spread = SPREAD[pair]
            dp = PIPS[pair]
            hist = state["history"]
            result[pair] = {
                "pair":pair,
                "bid":round(mid-spread/2,dp),"ask":round(mid+spread/2,dp),
                "mid":round(mid,dp),"spread":round(spread,dp),
                "change_pct":round((mid-base)/base*100,3),
                "trend":"up" if mid>=base else "down",
                "high":round(max(hist[-60:]),dp),"low":round(min(hist[-60:]),dp),
                "history":hist,"ts":int(time.time()*1000),
            }
        return result

def get_pair_price(pair):
    snap = get_snapshot()
    return snap.get(pair, None)

def get_session_status():
    h = datetime.now(timezone.utc).hour
    out = {}
    for name, s in SESSIONS.items():
        if s["open"]<s["close"]:
            active = s["open"]<=h<s["close"]
        else:
            active = h>=s["open"] or h<s["close"]
        out[name] = {"active":active,"open":s["open"],"close":s["close"]}
    return out

def _run_loop(interval=0.8):
    global _running
    while _running:
        tick_data = _tick()
        if _socketio:
            _socketio.emit("tick", tick_data, namespace="/live")
        time.sleep(interval)

def start(socketio_instance, interval=0.8):
    global _running, _thread, _socketio
    _socketio = socketio_instance
    if not _running:
        _running = True
        _thread = threading.Thread(target=_run_loop, args=(interval,), daemon=True)
        _thread.start()

def stop():
    global _running
    _running = False
