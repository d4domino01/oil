import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

# ==============================
# SETTINGS
# ==============================

ENTRY_THRESHOLD = 85
EXIT_THRESHOLD = 55

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

    # Oil momentum
    if row["USO"] > prev_row["USO"]:
        score += 15
    else:
        score -= 15

    # Energy confirmation
    if row["XLE"] > prev_row["XLE"]:
        score += 10
    else:
        score -= 10

    # BWET (light)
    bwet_change = (row["BWET"] - prev_row["BWET"]) / prev_row["BWET"]
    if bwet_change > 0.03:
        score += 5
    elif bwet_change < -0.03:
        score -= 5

    # Volatility boost
    uso_change = abs((row["USO"] - prev_row["USO"]) / prev_row["USO"])
    if uso_change > 0.03:
        score += 5

    return score

# ==============================
# BUILD SIGNALS (BIAS-FREE HOLD)
# ==============================

position = 0
signals = []

for i in range(2, len(data)):
    today = data.iloc[i]
    yesterday = data.iloc[i-1]
    day_before = data.iloc[i-2]

    # IMPORTANT: use past data only
    score = calculate_score(yesterday, day_before)

    prev_position = position

    # ENTRY (EXTREME ONLY)
    if position == 0:
        if score >= ENTRY_THRESHOLD:
            position = 1
        elif score <= (100 - ENTRY_THRESHOLD):
            position = -1

    # HOLD / EXIT
    elif position == 1:
        if score < EXIT_THRESHOLD:
            position = 0
        elif score <= (100 - ENTRY_THRESHOLD):
            position = -1

    elif position == -1:
        if score > (100 - EXIT_THRESHOLD):
            position = 0
        elif score >= ENTRY_THRESHOLD:
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

# Detect action
if latest["position"] != previous["position"]:
    if latest["position"] == 1:
        action = "🚀 ENTER LONG"
    elif latest["position"] == -1:
        action = "🔻 ENTER SHORT"
    else:
        action = "❌ EXIT POSITION"
else:
    action = "⏳ HOLD"

confidence = int(abs(latest["score"] - 50) * 2)

# ==============================
# UI
# ==============================

st.title("🛢️ Oil Trading System (EXTREME MODEL)")

st.subheader("📊 TODAY'S SIGNAL (Check at 15:25 CET)")

col1, col2, col3 = st.columns(3)

col1.metric("Score", int(latest["score"]))
col2.metric("Confidence", f"{confidence}%")
col3.metric("Position", signal_map[latest["position"]])

st.markdown(f"## 🔥 ACTION: {action}")

# ==============================
# SIGNAL STRENGTH
# ==============================

if latest["score"] >= ENTRY_THRESHOLD:
    st.success("Strong BULLISH signal (EXTREME)")
elif latest["score"] <= (100 - ENTRY_THRESHOLD):
    st.error("Strong BEARISH signal (EXTREME)")
else:
    st.info("No extreme signal → NO TRADE")

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
- Enter at 15:30 CET  
- Hold until:
    - Score < 55 OR
    - Opposite extreme signal  
- Ignore noise  
""")
