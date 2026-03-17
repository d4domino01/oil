import streamlit as st
import pandas as pd
from datetime import datetime

st.write("VERSION 7 (FINAL MODEL)")

ENTRY_THRESHOLD = 75
EXIT_THRESHOLD = 55

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

        df = pd.concat([uso, xle, bno], axis=1)
        df.columns = ["USO", "XLE", "BNO"]

        return df.sort_index().dropna().tail(120)

    except:
        return None


data = load_data()

if data is None or data.empty or len(data) < 50:
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
# SCORE
# ==============================

def calc_score(a, b, trend):
    score = 50

    score += 20 if a["USO"] > b["USO"] else -20
    score += 15 if a["XLE"] > b["XLE"] else -15

    change = (a["BNO"] - b["BNO"]) / b["BNO"]
    if change > 0.015:
        score += 10
    elif change < -0.015:
        score -= 10

    if trend == 1:
        score += 10
    elif trend == -1:
        score -= 10

    return score

# ==============================
# PRE-OPEN
# ==============================

def pre_open_signal(df):
    last = df.iloc[-1]
    prev = df.iloc[-2]

    move = (last["USO"] - prev["USO"]) / prev["USO"]

    if move > 0.01:
        return "BULLISH"
    elif move < -0.01:
        return "BEARISH"
    else:
        return "NEUTRAL"

# ==============================
# MOMENTUM
# ==============================

def early_momentum(df):
    last = df.iloc[-1]
    prev = df.iloc[-2]

    strength = abs((last["USO"] - prev["USO"]) / prev["USO"])

    if strength > 0.02:
        return "STRONG"
    elif strength > 0.01:
        return "MEDIUM"
    else:
        return "WEAK"

# ==============================
# BUILD SIGNALS
# ==============================

signals = []

for i in range(50, len(data)):
    try:
        y = data.iloc[i-1]
        d = data.iloc[i-2]

        trend = get_trend(y)
        score = calc_score(y, d, trend)

        signals.append({
            "date": data.index[i],
            "score": score,
            "trend": trend
        })

    except:
        continue

df = pd.DataFrame(signals)

if df.empty or len(df) < 2:
    st.warning("⚠️ Not enough signals")
    st.stop()

latest = df.iloc[-1]

# ==============================
# EXTRA SIGNALS
# ==============================

pre_signal = pre_open_signal(data)
momentum = early_momentum(data)

confidence = int(abs(latest["score"] - 50) * 2)

# ==============================
# FINAL DECISION ENGINE
# ==============================

# TREND TRADE
if (
    confidence > 70 and
    ((latest["trend"] == 1 and latest["score"] > 70) or
     (latest["trend"] == -1 and latest["score"] < 30))
):
    if latest["trend"] == 1:
        action = "🚀 TREND BUY"
    else:
        action = "🔻 TREND SELL"

# BREAKOUT TRADE
elif (
    (pre_signal == "BULLISH" and momentum == "STRONG") or
    (pre_signal == "BEARISH" and momentum == "STRONG")
):
    if pre_signal == "BULLISH":
        action = "⚡ BREAKOUT BUY (smaller size)"
    else:
        action = "⚡ BREAKOUT SELL (smaller size)"

# NO TRADE
else:
    action = "⏳ NO TRADE"

# ==============================
# UI
# ==============================

st.title("🛢️ Oil Trading System (FINAL)")

col1, col2, col3 = st.columns(3)

col1.metric("Score", int(latest["score"]))
col2.metric("Confidence", f"{confidence}%")

trend_label = "UP" if latest["trend"] == 1 else "DOWN"
col3.metric("Trend", trend_label)

st.markdown(f"## 🔥 ACTION: {action}")

# ==============================
# EXTRA INFO
# ==============================

st.subheader("Pre-Open Signal (15:25)")
st.write(pre_signal)

st.subheader("Early Momentum")
st.write(momentum)

# ==============================
# TRADE TYPE INFO
# ==============================

if "TREND" in action:
    st.success("SAFE TREND TRADE")

elif "BREAKOUT" in action:
    st.warning("BREAKOUT TRADE → USE SMALL SIZE")

else:
    st.info("NO EDGE → DO NOTHING")

# ==============================
# INFO
# ==============================

st.caption(f"Updated: {datetime.now()}")

st.subheader("Recent Signals")
st.dataframe(df.tail(10))

st.subheader("How to Trade This")

st.write("""
TREND TRADE:
- Full size
- High confidence

BREAKOUT TRADE:
- Half size
- Watch first 5–10 min
- Exit quickly if fails

NO TRADE:
- Stay out
""")
