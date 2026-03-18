import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(layout="wide")

st.title("🛢️ Oil Trading System (FINAL CORE SYSTEM)")

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

    return df.sort_index().dropna()

data = load_data()

# ==============================
# DATA STATUS
# ==============================

latest_date = data.index[-1]
days_old = (datetime.now() - latest_date).days

st.subheader("📊 Data Status")
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

data = data.dropna()

# ==============================
# FUNCTIONS (LOCKED)
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

    if divergence > 0.012:
        return "BULLISH", divergence
    elif divergence < -0.012:
        return "BEARISH", divergence
    return "NEUTRAL", divergence

def calculate_score(a, b, trend, lead):
    score = 50

    score += 20 if a["USO"] > b["USO"] else -20
    score += 15 if a["XLE"] > b["XLE"] else -15

    if lead == "BULLISH":
        score += 10
    elif lead == "BEARISH":
        score -= 10

    if trend == 1:
        score += 10
    else:
        score -= 10

    return score

# ==============================
# DAILY DECISION (CORRECT)
# ==============================

y = data.iloc[-1]   # yesterday
d = data.iloc[-2]   # day before

trend = get_trend(y)
lead, divergence = futures_lead(y, d)
vol = volatility_state(y)

score = calculate_score(y, d, trend, lead)

# FIXED CONFIDENCE
confidence = int(min(abs(score - 50) * 2, 100))

# CONDITIONS
cond_conf = confidence > 70
cond_vol = vol != "LOW"
cond_lead = lead != "NEUTRAL"

# FINAL DECISION
if cond_conf and cond_vol and cond_lead:
    action = "🚀 TREND BUY" if trend == 1 else "🔻 TREND SELL"
    reason = "All conditions aligned"
else:
    action = "⏳ NO TRADE"

    failed = []
    if not cond_conf: failed.append("Confidence < 70")
    if not cond_vol: failed.append("Low volatility")
    if not cond_lead: failed.append("No futures confirmation")

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
# BREAKDOWN
# ==============================

st.subheader("Signal Breakdown")

st.write(f"Score: {score}")
st.write(f"Volatility: {vol}")
st.write(f"Futures Lead: {lead}")
st.write(f"Divergence: {round(divergence, 5)}")

# ==============================
# CONDITION CHECK
# ==============================

st.subheader("Condition Check")

st.write(f"Confidence > 70: {'✅' if cond_conf else '❌'}")
st.write(f"Volatility OK: {'✅' if cond_vol else '❌'}")
st.write(f"Futures Confirmed: {'✅' if cond_lead else '❌'}")

# ==============================
# DEBUG PANEL
# ==============================

with st.expander("🔍 Debug"):
    st.write("Score:", score)
    st.write("Confidence:", confidence)
    st.write("Divergence:", divergence)
    st.write("Lead:", lead)

# ==============================
# FOOTER
# ==============================

st.caption(f"Updated: {datetime.now()}")
