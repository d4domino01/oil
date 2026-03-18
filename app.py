import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(layout="wide")

st.title("🛢️ Oil Trading System (TRUE CORE EDGE)")

# ==============================
# DATA (STOOQ)
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

# ==============================
# FUNCTIONS (IDENTICAL TO BACKTEST)
# ==============================

def get_trend(row):
    return 1 if row["MA20"] > row["MA50"] else -1

def volatility_state(row):
    if row["VOL"] > 0.028:
        return "HIGH"
    elif row["VOL"] > 0.015:
        return "NORMAL"
    return "LOW"

def futures_lead(a, b):
    uso_move = (a["USO"] - b["USO"]) / b["USO"]
    bno_move = (a["BNO"] - b["BNO"]) / b["BNO"]

    divergence = bno_move - uso_move

    if divergence > 0.01:
        return "BULLISH"
    elif divergence < -0.01:
        return "BEARISH"
    return "NEUTRAL"

def calculate_score(a, b, trend):
    score = 50

    score += 20 if a["USO"] > b["USO"] else -20
    score += 15 if a["XLE"] > b["XLE"] else -15

    lead = futures_lead(a, b)

    if lead == "BULLISH":
        score += 10
    elif lead == "BEARISH":
        score -= 10

    if trend == 1:
        score += 10
    else:
        score -= 10

    return score, lead

# ==============================
# SIGNAL BUILD
# ==============================

signals = []

for i in range(50, len(data)):
    y = data.iloc[i-1]
    d = data.iloc[i-2]

    trend = get_trend(y)
    score, lead = calculate_score(y, d, trend)
    vol = volatility_state(y)

    signals.append({
        "date": data.index[i],
        "score": score,
        "trend": trend,
        "vol": vol,
        "lead": lead
    })

df = pd.DataFrame(signals)

if df.empty:
    st.error("No signals generated")
    st.stop()

latest = df.iloc[-1]

confidence = int(abs(latest["score"] - 50) * 2)

# ==============================
# DECISION ENGINE (LOCKED)
# ==============================

if (
    confidence > 70 and
    latest["vol"] != "LOW" and
    latest["lead"] != "NEUTRAL"
):
    if latest["trend"] == 1:
        action = "🚀 TREND BUY"
    else:
        action = "🔻 TREND SELL"
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
# SIGNAL DETAILS
# ==============================

st.subheader("Signal Breakdown")

st.write(f"Futures Lead: {latest['lead']}")
st.write(f"Volatility: {latest['vol']}")

# ==============================
# INTERPRETATION
# ==============================

if "TREND" in action:
    st.success("High-confidence setup → Full position")

else:
    st.info("No edge → Stay out")

# ==============================
# HISTORY
# ==============================

st.subheader("Recent Signals")
st.dataframe(df.tail(10))

st.caption(f"Updated: {datetime.now()}")
