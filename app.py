import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(layout="wide")

st.title("🛢️ Oil Strategy (Final — Explained & Backtest Matched)")

# ==============================
# LOAD DATA (STOOQ)
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
    df.columns = ["USO", "XLE", "BWET"]

    df = df.sort_index().dropna()

    # SHIFT (REMOVE LOOKAHEAD)
    df["USO_prev"] = df["USO"].shift(1)
    df["XLE_prev"] = df["XLE"].shift(1)
    df["BWET_prev"] = df["BWET"].shift(1)

    df = df.dropna()

    return df

data = load_data()

# ==============================
# FAIL SAFE
# ==============================

if data is None or len(data) < 10:
    st.error("❌ Data issue")
    st.stop()

# ==============================
# SCORE FUNCTION (UNCHANGED)
# ==============================

def calculate_score(row, prev_row):
    score = 50

    if row["USO"] > prev_row["USO"]:
        score += 15
    else:
        score -= 15

    if row["XLE"] > prev_row["XLE"]:
        score += 10
    else:
        score -= 10

    bwet_change = (row["BWET"] - prev_row["BWET"]) / prev_row["BWET"]
    if bwet_change > 0.03:
        score += 5
    elif bwet_change < -0.03:
        score -= 5

    uso_change = abs((row["USO"] - prev_row["USO"]) / prev_row["USO"])
    if uso_change > 0.03:
        score += 5

    return score

# ==============================
# SIGNAL ENGINE (BACKTEST MATCH)
# ==============================

entry_threshold = 75
exit_threshold = 55

signals = []

for i in range(3, len(data)):
    t = data.iloc[i]       # TODAY (execution)
    y = data.iloc[i-1]     # YESTERDAY (signal)
    d = data.iloc[i-2]     # DAY BEFORE

    score = calculate_score(
        pd.Series({
            "USO": y["USO_prev"],
            "XLE": y["XLE_prev"],
            "BWET": y["BWET_prev"]
        }),
        pd.Series({
            "USO": d["USO_prev"],
            "XLE": d["XLE_prev"],
            "BWET": d["BWET_prev"]
        })
    )

    confidence = abs(score - 50) * 2

    if score >= entry_threshold:
        action = "BUY"
    elif score < exit_threshold:
        action = "EXIT"
    else:
        action = "HOLD"

    signals.append({
        "date": t.name,
        "score": score,
        "confidence": int(min(confidence, 100)),
        "action": action
    })

signals_df = pd.DataFrame(signals)

if signals_df.empty:
    st.error("❌ No signals generated")
    st.stop()

# ==============================
# CURRENT SIGNAL
# ==============================

latest = signals_df.iloc[-1]

st.markdown("## 🛢️ TODAY’S TRADE DECISION")

col1, col2, col3 = st.columns(3)

col1.metric("Action", latest["action"])
col2.metric("Score", int(latest["score"]))
col3.metric("Confidence", f"{latest['confidence']}%")

# ==============================
# SIGNAL EXPLANATION (FIXED)
# ==============================

st.subheader("🧠 Signal Explanation")

# IMPORTANT: use SAME DATA as scoring
y = data.iloc[-2]
d = data.iloc[-3]

y_prev = pd.Series({
    "USO": y["USO_prev"],
    "XLE": y["XLE_prev"],
    "BWET": y["BWET_prev"]
})

d_prev = pd.Series({
    "USO": d["USO_prev"],
    "XLE": d["XLE_prev"],
    "BWET": d["BWET_prev"]
})

explanation = []
score_parts = []

# USO
if y_prev["USO"] > d_prev["USO"]:
    explanation.append("✔ USO rising")
    score_parts.append("+15 USO up")
else:
    explanation.append("✖ USO falling")
    score_parts.append("-15 USO down")

# XLE
if y_prev["XLE"] > d_prev["XLE"]:
    explanation.append("✔ XLE rising")
    score_parts.append("+10 XLE up")
else:
    explanation.append("✖ XLE falling")
    score_parts.append("-10 XLE down")

# BWET
bwet_change = (y_prev["BWET"] - d_prev["BWET"]) / d_prev["BWET"]

if bwet_change > 0.03:
    explanation.append("✔ Strong oil move")
    score_parts.append("+5 oil strength")
elif bwet_change < -0.03:
    explanation.append("✖ Oil weakness")
    score_parts.append("-5 oil weakness")
else:
    explanation.append("• Oil neutral")
    score_parts.append("0 oil neutral")

# Momentum
uso_change = abs((y_prev["USO"] - d_prev["USO"]) / d_prev["USO"])

if uso_change > 0.03:
    explanation.append("✔ Strong momentum")
    score_parts.append("+5 momentum")
else:
    explanation.append("• No momentum")
    score_parts.append("0 momentum")

# DISPLAY
st.markdown("### 🔍 Why this signal?")
for item in explanation:
    st.write(item)

st.markdown("### 📊 Score Breakdown")
for part in score_parts:
    st.write(part)

# ==============================
# 🟡 EARLY SIGNAL + PROBABILITY
# ==============================

st.subheader("🧠 Predictive Insight (Next-Day Edge)")

# Use latest available confirmed + current forming structure
y = data.iloc[-2]
d = data.iloc[-3]

y_prev = pd.Series({
    "USO": y["USO_prev"],
    "XLE": y["XLE_prev"],
    "BWET": y["BWET_prev"]
})

d_prev = pd.Series({
    "USO": d["USO_prev"],
    "XLE": d["XLE_prev"],
    "BWET": d["BWET_prev"]
})

# ==============================
# EARLY BUILDING BLOCKS
# ==============================

early_score = 0
signals = []

# USO direction (strongest weight)
if y_prev["USO"] > d_prev["USO"]:
    early_score += 30
    signals.append("USO building upward pressure")
else:
    early_score -= 30
    signals.append("USO showing weakness")

# XLE confirmation
if y_prev["XLE"] > d_prev["XLE"]:
    early_score += 20
    signals.append("Energy sector confirming")
else:
    early_score -= 20
    signals.append("Energy sector not confirming")

# Oil move (BNO/BWET)
bwet_change = (y_prev["BWET"] - d_prev["BWET"]) / d_prev["BWET"]

if bwet_change > 0.02:
    early_score += 15
    signals.append("Oil strength building")
elif bwet_change < -0.02:
    early_score -= 15
    signals.append("Oil weakening")

# Momentum
uso_change = (y_prev["USO"] - d_prev["USO"]) / d_prev["USO"]

if uso_change > 0.015:
    early_score += 15
    signals.append("Momentum increasing")

# ==============================
# NORMALIZE PROBABILITY
# ==============================

probability = max(min(50 + early_score, 100), 0)

# ==============================
# INTERPRETATION
# ==============================

st.markdown("### 📊 Tomorrow Probability")

st.metric("Follow-through Probability", f"{int(probability)}%")

# Visual interpretation
if probability > 70:
    st.success("🔥 Strong probability of continuation")
elif probability > 55:
    st.info("📈 Moderate bullish pressure building")
elif probability > 45:
    st.warning("⚖️ Unclear direction")
else:
    st.error("📉 Weak / likely no follow-through")

# ==============================
# EARLY SIGNAL
# ==============================

st.markdown("### 🟡 Early Signal")

if probability > 65 and latest["action"] != "BUY":
    st.warning("⚡ Early BUY forming (not confirmed yet)")
elif probability < 35 and latest["action"] == "BUY":
    st.error("⚠️ Weak follow-through risk")
else:
    st.info("No early signal")

# ==============================
# SIGNAL DETAILS
# ==============================

st.markdown("### 🔍 What’s Driving This")

for s in signals:
    st.write(f"• {s}")

# ==============================
# SIGNAL HISTORY
# ==============================

st.subheader("📅 Signal History")
st.dataframe(signals_df.tail(20))

# ==============================
# DATA STATUS
# ==============================

st.subheader("📊 Data Status")

latest_date = data.index[-1]
st.write(f"Latest data available: {latest_date}")

if (datetime.now() - latest_date).days > 3:
    st.warning("⚠️ Data may be slightly delayed")
else:
    st.success("✅ Data is up to date")

# ==============================
# DEBUG PANEL
# ==============================

with st.expander("🔍 Debug Data"):
    st.write("Yesterday (signal):")
    st.write(data.iloc[-2])

    st.write("Day before:")
    st.write(data.iloc[-3])
