import streamlit as st
import pandas as pd
from datetime import datetime

st.write("VERSION 8 (VOL + FUTURES EDGE)")

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

        df = pd.concat([uso, xle, bno], axis=1)
        df.columns = ["USO", "XLE", "BNO"]

        return df.sort_index().dropna().tail(120)

    except:
        return None


data = load_data()

if data is None or len(data) < 50:
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
# VOLATILITY FILTER (OVX STYLE)
# ==============================

data["USO_RET"] = data["USO"].pct_change()
data["VOL"] = data["USO_RET"].rolling(10).std()

def volatility_state(row):
    if row["VOL"] > 0.025:
        return "HIGH"
    elif row["VOL"] > 0.015:
        return "NORMAL"
    else:
        return "LOW"

# ==============================
# FUTURES LEAD (BNO MOMENTUM)
# ==============================

def futures_lead(a, b):
    move = (a["BNO"] - b["BNO"]) / b["BNO"]

    if move > 0.01:
        return "BULLISH"
    elif move < -0.01:
        return "BEARISH"
    else:
        return "NEUTRAL"

# ==============================
# SCORE
# ==============================

def calc_score(a, b, trend):
    score = 50

    score += 20 if a["USO"] > b["USO"] else -20
    score += 15 if a["XLE"] > b["XLE"] else -15

    bno_change = (a["BNO"] - b["BNO"]) / b["BNO"]
    if bno_change > 0.015:
        score += 10
    elif bno_change < -0.015:
        score -= 10

    if trend == 1:
        score += 10
    elif trend == -1:
        score -= 10

    return score

# ==============================
# SIGNAL BUILD
# ==============================

signals = []

for i in range(50, len(data)):
    try:
        y = data.iloc[i-1]
        d = data.iloc[i-2]

        trend = get_trend(y)
        score = calc_score(y, d, trend)
        vol = volatility_state(y)
        lead = futures_lead(y, d)

        signals.append({
            "date": data.index[i],
            "score": score,
            "trend": trend,
            "vol": vol,
            "lead": lead
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
    latest["lead"] != "NEUTRAL"
):
    if latest["trend"] == 1:
        action = "🚀 TREND BUY"
    elif latest["trend"] == -1:
        action = "🔻 TREND SELL"
    else:
        action = "⏳ NO TRADE"

# ⚡ BREAKOUT TRADE
elif (
    latest["vol"] == "HIGH" and
    latest["lead"] != "NEUTRAL"
):
    if latest["lead"] == "BULLISH":
        action = "⚡ BREAKOUT BUY (FAST MOVE)"
    else:
        action = "⚡ BREAKOUT SELL (FAST MOVE)"

# ❌ NO TRADE
else:
    action = "⏳ NO TRADE"

# ==============================
# UI
# ==============================

st.title("🛢️ Oil Trading System (PRO EDGE)")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Score", int(latest["score"]))
col2.metric("Confidence", f"{confidence}%")
col3.metric("Trend", "UP" if latest["trend"] == 1 else "DOWN")
col4.metric("Volatility", latest["vol"])

st.markdown(f"## 🔥 ACTION: {action}")

# ==============================
# EXTRA SIGNALS
# ==============================

st.subheader("Futures Lead (BNO)")
st.write(latest["lead"])

# ==============================
# INTERPRETATION
# ==============================

if "TREND" in action:
    st.success("HIGH QUALITY TREND TRADE")

elif "BREAKOUT" in action:
    st.warning("FAST MOVE → QUICK MANAGEMENT REQUIRED")

else:
    st.info("NO EDGE → DO NOTHING")

# ==============================
# INFO
# ==============================

st.caption(f"Updated: {datetime.now()}")

st.subheader("Recent Signals")
st.dataframe(df.tail(10))

st.subheader("Trading Rules")

st.write("""
TREND TRADE:
- Full size
- Confidence > 70
- Normal or High volatility

BREAKOUT TRADE:
- Smaller size
- High volatility required
- Quick exits

NO TRADE:
- Stay out
""")
