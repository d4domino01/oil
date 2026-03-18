import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(layout="wide")

st.title("🛢️ Oil Trading System (FINAL CORE EDGE)")

# ==============================
# DATA (STOOQ - STABLE)
# ==============================

@st.cache_data
def load_data():
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

    df = pd.concat([uso, xle, bno], axis=1)
    df.columns = ["USO", "XLE", "BNO"]

    return df.sort_index().dropna().tail(120)

data = load_data()

# ==============================
# INDICATORS
# ==============================

data["MA20"] = data["USO"].rolling(20).mean()
data["MA50"] = data["USO"].rolling(50).mean()

data["RET"] = data["USO"].pct_change()
data["VOL"] = data["RET"].rolling(10).std()

data["HIGH_10"] = data["USO"].rolling(10).max()
data["LOW_10"] = data["USO"].rolling(10).min()

# ==============================
# FUNCTIONS
# ==============================

def get_trend(row):
    if row["MA20"] > row["MA50"]:
        return 1
    elif row["MA20"] < row["MA50"]:
        return -1
    return 0

def volatility_state(row):
    if row["VOL"] > 0.025:
        return "HIGH"
    elif row["VOL"] > 0.012:
        return "NORMAL"
    return "LOW"

def futures_lead(a, b):
    uso_move = (a["USO"] - b["USO"]) / b["USO"]
    bno_move = (a["BNO"] - b["BNO"]) / b["BNO"]

    divergence = bno_move - uso_move

    if divergence > 0.006:
        return "BULLISH"
    elif divergence < -0.006:
        return "BEARISH"
    return "NEUTRAL"

def breakout_signal(row):
    if row["USO"] >= row["HIGH_10"]:
        return "BULLISH"
    elif row["USO"] <= row["LOW_10"]:
        return "BEARISH"
    return "NONE"

def calculate_score(a, b, trend):
    score = 50

    score += 15 if a["USO"] > b["USO"] else -15
    score += 10 if a["XLE"] > b["XLE"] else -10

    lead = futures_lead(a, b)
    if lead == "BULLISH":
        score += 10
    elif lead == "BEARISH":
        score -= 10

    if trend == 1:
        score += 8
    elif trend == -1:
        score -= 8

    return score

# ==============================
# SIGNAL BUILD
# ==============================

signals = []

for i in range(20, len(data)):
    y = data.iloc[i-1]
    d = data.iloc[i-2]

    trend = get_trend(y)
    score = calculate_score(y, d, trend)
    vol = volatility_state(y)
    lead = futures_lead(y, d)
    breakout = breakout_signal(y)

    signals.append({
        "date": data.index[i],
        "score": score,
        "trend": trend,
        "vol": vol,
        "lead": lead,
        "breakout": breakout
    })

df = pd.DataFrame(signals)
latest = df.iloc[-1]

confidence = int(abs(latest["score"] - 50) * 2)

# ==============================
# DECISION ENGINE (LOCKED)
# ==============================

if (
    confidence > 60 and
    latest["vol"] != "LOW"
):
    if latest["trend"] == 1:
        action = "🚀 TREND BUY"
    else:
        action = "🔻 TREND SELL"

elif (
    latest["breakout"] != "NONE" and
    latest["vol"] == "HIGH"
):
    if latest["breakout"] == "BULLISH":
        action = "⚡ BREAKOUT BUY"
    else:
        action = "⚡ BREAKOUT SELL"

else:
    action = "⏳ NO TRADE"

# ==============================
# UI
# ==============================

col1, col2, col3, col4 = st.columns(4)

col1.metric("Score", int(latest["score"]))
col2.metric("Confidence", f"{confidence}%")
col3.metric("Trend", "UP" if latest["trend"] == 1 else "DOWN")
col4.metric("Volatility", latest["vol"])

st.markdown(f"## 🔥 ACTION: {action}")

# ==============================
# BREAKDOWN
# ==============================

st.subheader("Signal Breakdown")

st.write(f"Futures Lead: {latest['lead']}")
st.write(f"Breakout: {latest['breakout']}")

# ==============================
# INTERPRETATION
# ==============================

if "TREND" in action:
    st.success("High-quality trend trade")

elif "BREAKOUT" in action:
    st.warning("Fast breakout — manage tightly")

else:
    st.info("No edge — stay out")

# ==============================
# HISTORY
# ==============================

st.subheader("Recent Signals")
st.dataframe(df.tail(10))

st.caption(f"Updated: {datetime.now()}")
