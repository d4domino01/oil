import streamlit as st
import pandas as pd
from datetime import datetime

st.write("VERSION 9 (REAL EDGE UPGRADE)")

ENTRY_THRESHOLD = 75

# ==============================
# DATA (STOOQ)
# ==============================

@st.cache_data
def load_data():
    try:
        uso = pd.read_csv(
            "https://stooq.com/q/d/l/?s=uso.us&i=d",
            parse_dates=["Date"]
        ).set_index("Date")["Close"]

        xle = pd.read_csv(
            "https://stooq.com/q/d/l/?s=xle.us&i=d",
            parse_dates=["Date"]
        ).set_index("Date")["Close"]

        bno = pd.read_csv(
            "https://stooq.com/q/d/l/?s=bno.us&i=d",
            parse_dates=["Date"]
        ).set_index("Date")["Close"]

        dxy = pd.read_csv(
            "https://stooq.com/q/d/l/?s=dx-y.ny&i=d",
            parse_dates=["Date"]
        ).set_index("Date")["Close"]

        df = pd.concat([uso, xle, bno, dxy], axis=1)
        df.columns = ["USO", "XLE", "BNO", "DXY"]

        return df.sort_index().dropna().tail(150)

    except:
        return None


data = load_data()

if data is None or len(data) < 60:
    st.error("❌ Data issue")
    st.stop()

# ==============================
# TREND
# ==============================

data["MA20"] = data["USO"].rolling(20).mean()
data["MA50"] = data["USO"].rolling(50).mean()

def get_trend(row):
    if row["MA20"] > row["MA50"]:
        return 1
    elif row["MA20"] < row["MA50"]:
        return -1
    return 0

# ==============================
# VOLATILITY (IMPROVED)
# ==============================

data["RET"] = data["USO"].pct_change()
data["VOL"] = data["RET"].rolling(10).std()

def volatility_state(row):
    if row["VOL"] > 0.028:
        return "HIGH"
    elif row["VOL"] > 0.015:
        return "NORMAL"
    else:
        return "LOW"

# ==============================
# BREAKOUT STRUCTURE
# ==============================

data["HIGH_10"] = data["USO"].rolling(10).max()
data["LOW_10"] = data["USO"].rolling(10).min()

def breakout_signal(row):
    if row["USO"] >= row["HIGH_10"]:
        return "BULLISH"
    elif row["USO"] <= row["LOW_10"]:
        return "BEARISH"
    return "NONE"

# ==============================
# FUTURES PROXY (BNO vs USO)
# ==============================

def futures_lead(a, b):
    uso_move = (a["USO"] - b["USO"]) / b["USO"]
    bno_move = (a["BNO"] - b["BNO"]) / b["BNO"]

    divergence = bno_move - uso_move

    if divergence > 0.01:
        return "BULLISH"
    elif divergence < -0.01:
        return "BEARISH"
    return "NEUTRAL"

# ==============================
# DXY PRESSURE
# ==============================

def dxy_pressure(a, b):
    move = (a["DXY"] - b["DXY"]) / b["DXY"]

    if move > 0.002:
        return "BEARISH"
    elif move < -0.002:
        return "BULLISH"
    return "NEUTRAL"

# ==============================
# SCORE ENGINE (UPGRADED)
# ==============================

def calc_score(a, b, trend):
    score = 50

    # Price momentum
    if a["USO"] > b["USO"]:
        score += 18
    else:
        score -= 18

    # Energy confirmation
    if a["XLE"] > b["XLE"]:
        score += 12
    else:
        score -= 12

    # Futures lead
    lead = futures_lead(a, b)
    if lead == "BULLISH":
        score += 12
    elif lead == "BEARISH":
        score -= 12

    # DXY pressure
    dxy = dxy_pressure(a, b)
    if dxy == "BULLISH":
        score += 10
    elif dxy == "BEARISH":
        score -= 10

    # Trend bias
    if trend == 1:
        score += 8
    elif trend == -1:
        score -= 8

    # Conflict penalty (IMPORTANT)
    if lead != "NEUTRAL" and dxy != "NEUTRAL":
        if lead != dxy:
            score -= 10  # conflicting macro vs flow

    return score

# ==============================
# SIGNAL BUILD
# ==============================

signals = []

for i in range(60, len(data)):
    try:
        y = data.iloc[i-1]
        d = data.iloc[i-2]

        trend = get_trend(y)
        score = calc_score(y, d, trend)
        vol = volatility_state(y)
        lead = futures_lead(y, d)
        breakout = breakout_signal(y)
        dxy = dxy_pressure(y, d)

        signals.append({
            "date": data.index[i],
            "score": score,
            "trend": trend,
            "vol": vol,
            "lead": lead,
            "breakout": breakout,
            "dxy": dxy
        })

    except:
        continue

df = pd.DataFrame(signals)

if df.empty:
    st.stop()

latest = df.iloc[-1]

confidence = int(abs(latest["score"] - 50) * 2)

# ==============================
# FINAL DECISION ENGINE
# ==============================

# 🚀 TREND TRADE
if (
    confidence > 70 and
    latest["vol"] != "LOW" and
    latest["lead"] != "NEUTRAL" and
    latest["dxy"] != "NEUTRAL"
):
    if latest["trend"] == 1:
        action = "🚀 TREND BUY"
    elif latest["trend"] == -1:
        action = "🔻 TREND SELL"
    else:
        action = "⏳ NO TRADE"

# ⚡ BREAKOUT TRADE (STRUCTURE BASED)
elif (
    latest["breakout"] != "NONE" and
    latest["vol"] == "HIGH"
):
    if latest["breakout"] == "BULLISH":
        action = "⚡ BREAKOUT BUY"
    else:
        action = "⚡ BREAKOUT SELL"

# ❌ NO TRADE
else:
    action = "⏳ NO TRADE"

# ==============================
# UI
# ==============================

st.title("🛢️ Oil Trading System (REAL EDGE)")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Score", int(latest["score"]))
col2.metric("Confidence", f"{confidence}%")
col3.metric("Trend", "UP" if latest["trend"] == 1 else "DOWN")
col4.metric("Volatility", latest["vol"])

st.markdown(f"## 🔥 ACTION: {action}")

# ==============================
# EXTRA SIGNALS
# ==============================

st.subheader("Signal Breakdown")

st.write(f"Futures Lead: {latest['lead']}")
st.write(f"DXY Pressure: {latest['dxy']}")
st.write(f"Breakout: {latest['breakout']}")

# ==============================
# INTERPRETATION
# ==============================

if "TREND" in action:
    st.success("HIGH QUALITY TREND TRADE")

elif "BREAKOUT" in action:
    st.warning("FAST MOVE → MANAGE QUICKLY")

else:
    st.info("NO EDGE → STAY OUT")

# ==============================
# INFO
# ==============================

st.caption(f"Updated: {datetime.now()}")

st.subheader("Recent Signals")
st.dataframe(df.tail(10))

st.subheader("Trading Rules")

st.write("""
TREND TRADE:
- Confidence > 70
- Full position
- Macro aligned (DXY + Futures)

BREAKOUT TRADE:
- High volatility + structure break
- Smaller size
- Fast exits

NO TRADE:
- Conflicting signals
- Low volatility
""")
