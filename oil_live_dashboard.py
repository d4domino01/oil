import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

# ==============================
# SETTINGS
# ==============================

entry_threshold = 85
exit_threshold = 55

# ==============================
# LOAD DATA
# ==============================

@st.cache_data
def load_data():
    tickers = ["USO", "XLE", "BWET"]
    data = yf.download(tickers, period="3mo", interval="1d")["Close"]
    return data.dropna()

data = load_data()

# ==============================
# SIGNAL ENGINE
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
# BUILD SIGNALS (HOLD SYSTEM)
# ==============================

position = 0
signals = []

for i in range(2, len(data)):
    today = data.iloc[i]
    yesterday = data.iloc[i-1]
    day_before = data.iloc[i-2]

    score = calculate_score(yesterday, day_before)

    prev_position = position

    # ENTRY (EXTREME ONLY)
    if position == 0:
        if score >= entry_threshold:
            position = 1
        elif score <= (100 - entry_threshold):
            position = -1

    # HOLD / EXIT
    elif position == 1:
        if score < exit_threshold:
            position = 0
        elif score <= (100 - entry_threshold):
            position = -1

    elif position == -1:
        if score > (100 - exit_threshold):
            position = 0
        elif score >= entry_threshold:
            position = 1

    signals.append({
        "date": data.index[i],
        "score": score,
        "position": position
    })

df = pd.DataFrame(signals)

# ==============================
# LATEST SIGNAL
# ==============================

latest = df.iloc[-1]
previous = df.iloc[-2]

signal_map = {
    1: "🟢 LONG (BUY / HOLD)",
    -1: "🔴 SHORT (SELL / HOLD)",
    0: "⚪ NO POSITION"
}

# Detect action change
if latest["position"] != previous["position"]:
    if latest["position"] == 1:
        action = "🚀 ENTER LONG"
    elif latest["position"] == -1:
        action = "🔻 ENTER SHORT"
    else:
        action = "❌ EXIT POSITION"
else:
    action = "⏳ HOLD"

# Confidence
confidence = int(abs(latest["score"] - 50) * 2)

# ==============================
# UI
# ==============================

st.title("🛢️ Oil Trading System")

st.subheader("📊 TODAY'S SIGNAL (Check at 15:25 CET)")

st.metric("Score", int(latest["score"]))
st.metric("Confidence", f"{confidence}%")
st.metric("Position", signal_map[latest["position"]])

st.markdown(f"### 🔥 ACTION: {action}")

# ==============================
# STATUS WARNING
# ==============================

if latest["score"] >= entry_threshold:
    st.success("Strong BULLISH signal (EXTREME)")
elif latest["score"] <= (100 - entry_threshold):
    st.error("Strong BEARISH signal (EXTREME)")
else:
    st.info("No extreme signal → No new trade")

# ==============================
# TIME INFO
# ==============================

st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# ==============================
# HISTORY
# ==============================

st.subheader("Recent Signals")
st.dataframe(df.tail(10))

# ==============================
# RULES
# ==============================

st.subheader("Trading Rules")

st.write("""
- Trade ONLY when score ≥ 85 or ≤ 15  
- Enter at market open (15:30 CET)  
- Hold until:
  - Score drops below 55 OR
  - Opposite extreme appears  
- Ignore noise between signals  
""")