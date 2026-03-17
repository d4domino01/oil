import streamlit as st
import pandas as pd
from datetime import datetime, time

st.write("VERSION 6 (EDGE MODEL)")

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

        df = df.sort_index().dropna()

        return df.tail(120)

    except:
        return None


data = load_data()

if data is None or data.empty or len(data) < 30:
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
# CORE SCORE
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
# PRE-OPEN SIGNAL (KEY EDGE)
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
# EARLY MOMENTUM
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
# SIGNAL ENGINE
# ==============================

signals = []
position = 0

for i in range(50, len(data)):
    try:
        y = data.iloc[i-1]
        d = data.iloc[i-2]

        trend = get_trend(y)
        score = calc_score(y, d, trend)

        # NO TRADE ZONE
        if abs(score - 50) < 15:
            new_position = 0

        else:
            if position == 0:
                if score >= ENTRY_THRESHOLD and trend == 1:
                    new_position = 1
                elif score <= (100 - ENTRY_THRESHOLD) and trend == -1:
                    new_position = -1
                else:
                    new_position = 0

            elif position == 1:
                if score < EXIT_THRESHOLD:
                    new_position = 0
                else:
                    new_position = 1

            elif position == -1:
                if score > (100 - EXIT_THRESHOLD):
                    new_position = 0
                else:
                    new_position = -1

        position = new_position

        signals.append({
            "date": data.index[i],
            "score": score,
            "trend": trend,
            "position": position
        })

    except:
        continue

df = pd.DataFrame(signals)

if df.empty or len(df) < 2:
    st.warning("⚠️ Not enough signals")
    st.stop()

latest = df.iloc[-1]
previous = df.iloc[-2]

# ==============================
# EXTRA EDGE SIGNALS
# ==============================

pre_signal = pre_open_signal(data)
momentum = early_momentum(data)

# ==============================
# FINAL DECISION LOGIC
# ==============================

confidence = int(abs(latest["score"] - 50) * 2)

if confidence > 70 and momentum != "WEAK":
    if latest["trend"] == 1:
        action = "🚀 HIGH PROBABILITY BUY"
    elif latest["trend"] == -1:
        action = "🔻 HIGH PROBABILITY SELL"
else:
    action = "⏳ NO TRADE"

# ==============================
# UI
# ==============================

st.title("🛢️ Oil Trading System (EDGE)")

col1, col2, col3 = st.columns(3)

col1.metric("Score", int(latest["score"]))
col2.metric("Confidence", f"{confidence}%")
col3.metric("Trend", "UP" if latest["trend"] == 1 else "DOWN")

st.markdown(f"## 🔥 ACTION: {action}")

# ==============================
# EDGE DISPLAY
# ==============================

st.subheader("Pre-Open Signal (15:25 CET)")
st.write(pre_signal)

st.subheader("Early Momentum")
st.write(momentum)

# ==============================
# QUALITY
# ==============================

if action.startswith("🚀") or action.startswith("🔻"):
    st.success("🔥 TRADE ALLOWED")
else:
    st.info("NO TRADE CONDITIONS")

# ==============================
# INFO
# ==============================

st.caption(f"Updated: {datetime.now()}")

st.subheader("Recent Signals")
st.dataframe(df.tail(10))

st.subheader("How to Use")

st.write("""
15:25 → Check Pre-Open Signal  
15:30 → Watch open  
15:35 → Confirm momentum  

ONLY trade when:
- Confidence > 70
- Momentum not WEAK
- Trend aligns
""")
