import streamlit as st
import pandas as pd
from datetime import datetime

st.write("VERSION 5 (PRO MODEL)")

ENTRY_THRESHOLD = 80
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
# TREND FILTER (KEY EDGE)
# ==============================

data["MA20"] = data["USO"].rolling(20).mean()
data["MA50"] = data["USO"].rolling(50).mean()

def get_trend(row):
    if row["MA20"] > row["MA50"]:
        return 1  # uptrend
    elif row["MA20"] < row["MA50"]:
        return -1  # downtrend
    else:
        return 0

# ==============================
# SIGNAL ENGINE
# ==============================

def calc_score(a, b, trend):
    score = 50

    # Core momentum
    score += 20 if a["USO"] > b["USO"] else -20
    score += 15 if a["XLE"] > b["XLE"] else -15

    # Brent strength
    change = (a["BNO"] - b["BNO"]) / b["BNO"]
    if change > 0.015:
        score += 10
    elif change < -0.015:
        score -= 10

    # Trend alignment boost
    if trend == 1:
        score += 10
    elif trend == -1:
        score -= 10

    return score

signals = []
position = 0

for i in range(50, len(data)):
    try:
        y = data.iloc[i-1]
        d = data.iloc[i-2]

        trend = get_trend(y)
        score = calc_score(y, d, trend)

        # 🚨 NO TRADE FILTER
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
# ACTION
# ==============================

if latest["position"] != previous["position"]:
    if latest["position"] == 1:
        action = "🚀 STRONG BUY"
    elif latest["position"] == -1:
        action = "🔻 STRONG SELL"
    else:
        action = "❌ EXIT"
else:
    action = "⏳ HOLD"

confidence = int(abs(latest["score"] - 50) * 2)

# ==============================
# UI
# ==============================

st.title("🛢️ Oil Trading System (PRO)")

col1, col2, col3 = st.columns(3)

col1.metric("Score", int(latest["score"]))
col2.metric("Confidence", f"{confidence}%")

trend_label = "UPTREND" if latest["trend"] == 1 else "DOWNTREND"
col3.metric("Trend", trend_label)

st.markdown(f"## 🔥 ACTION: {action}")

# ==============================
# SIGNAL QUALITY
# ==============================

if confidence > 70:
    st.success("🔥 HIGH PROBABILITY TRADE")
elif confidence > 50:
    st.warning("⚠️ Medium strength")
else:
    st.info("No trade zone")

# ==============================
# INFO
# ==============================

st.caption(f"Updated: {datetime.now()}")

st.subheader("Recent Signals")
st.dataframe(df.tail(10))

st.subheader("Rules")

st.write("""
ONLY trade when:
- Confidence > 70
- Trend aligns
- Score extreme

Avoid:
- Low confidence (<50)
- Mixed trend
- Choppy markets
""")
