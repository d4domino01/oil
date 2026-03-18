import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(layout="wide")

st.title("🛢️ Oil Trading System (CORE + EXPLAINABLE ENGINE)")

# ==============================
# LOAD DATA
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
# DATA CHECK
# ==============================

st.subheader("📊 Data Status")

latest_date = data.index[-1]
days_old = (datetime.now() - latest_date).days

st.write(f"Latest data date: {latest_date}")

if days_old > 3:
    st.warning(f"⚠️ Data is {days_old} days old")
else:
    st.success("✅ Data is recent")

# ==============================
# INDICATORS
# ==============================

data["MA20"] = data["USO"].rolling(20).mean()
data["MA50"] = data["USO"].rolling(50).mean()

data["RET"] = data["USO"].pct_change()
data["VOL"] = data["RET"].rolling(10).std()

# ==============================
# FUNCTIONS
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
# DAILY DECISION
# ==============================

y = data.iloc[-1]
d = data.iloc[-2]

trend = get_trend(y)
score, lead = calculate_score(y, d, trend)
vol = volatility_state(y)

confidence = int(abs(score - 50) * 2)

# ==============================
# CONDITION CHECKS
# ==============================

cond_conf = confidence > 70
cond_vol = vol != "LOW"
cond_lead = lead != "NEUTRAL"

# ==============================
# DECISION
# ==============================

if cond_conf and cond_vol and cond_lead:
    if trend == 1:
        action = "🚀 TREND BUY"
    else:
        action = "🔻 TREND SELL"
    reason = "All conditions aligned"
else:
    action = "⏳ NO TRADE"

    # Explain WHY
    failed = []

    if not cond_conf:
        failed.append("Confidence too low")

    if not cond_vol:
        failed.append("Volatility too low")

    if not cond_lead:
        failed.append("Missing futures confirmation")

    reason = " | ".join(failed)

# ==============================
# DISPLAY
# ==============================

st.markdown("## 🛢️ TODAY’S TRADE DECISION")

col1, col2, col3 = st.columns(3)

col1.metric("Action", action)
col2.metric("Confidence", f"{confidence}%")
col3.metric("Trend", "UP" if trend == 1 else "DOWN")

st.markdown(f"### 🧠 Reason: {reason}")

# ==============================
# SIGNAL BREAKDOWN
# ==============================

st.subheader("Signal Breakdown")

st.write(f"Score: {score}")
st.write(f"Volatility: {vol}")
st.write(f"Futures Lead: {lead}")

# ==============================
# VISUAL CONDITION CHECK
# ==============================

st.subheader("Condition Check")

st.write(f"Confidence > 70: {'✅' if cond_conf else '❌'}")
st.write(f"Volatility OK: {'✅' if cond_vol else '❌'}")
st.write(f"Futures Confirmed: {'✅' if cond_lead else '❌'}")

# ==============================
# HISTORY
# ==============================

signals = []

for i in range(50, len(data)):
    y = data.iloc[i-1]
    d = data.iloc[i-2]

    trend = get_trend(y)
    score, lead = calculate_score(y, d, trend)
    vol = volatility_state(y)

    confidence = abs(score - 50) * 2

    signals.append({
        "date": data.index[i],
        "score": score,
        "confidence": confidence,
        "trend": trend,
        "vol": vol,
        "lead": lead
    })

df = pd.DataFrame(signals)

st.subheader("Recent Signals")
st.dataframe(df.tail(10))

st.caption(f"Updated: {datetime.now()}")
