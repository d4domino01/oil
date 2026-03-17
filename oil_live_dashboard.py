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
# LOAD DATA (ULTRA SAFE)
# ==============================

@st.cache_data
def load_data():
    tickers = ["USO", "XLE", "BNO"]  # reliable set

    try:
        data = yf.download(tickers, period="3mo", interval="1d")

        if data is None or data.empty:
            return None

        if "Close" not in data:
            return None

        data = data["Close"].dropna()

        if data is None or data.empty:
            return None

        return data

    except Exception:
        return None


data = load_data()

# ==============================
# DATA SAFETY CHECK
# ==============================

if data is None:
    st.error("❌ Failed to load market data. Try refreshing.")
    st.stop()

if len(data) < 10:
    st.warning("⚠️ Not enough market data yet.")
    st.stop()

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

    # Brent proxy
    bno_change = (row["BNO"] - prev_row["BNO"]) / prev_row["BNO"]
    if bno_change > 0.02:
        score += 5
    elif bno_change < -0.02:
        score -= 5

    # Volatility boost
    uso_change = abs((row["USO"] - prev_row["USO"]) / prev_row["USO"])
    if uso_change > 0.03:
        score += 5

    return score

# ==============================
# BUILD SIGNALS
# ==============================

position = 0
signals = []

for i in range(2, len(data)):
    try:
        yesterday = data.iloc[i-1]
        day_before = data.iloc[i-2]

        score = calculate_score(yesterday, day_before)

        # ENTRY
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

    except Exception:
        continue

# ==============================
# CREATE DF SAFELY
# ==============================

df = pd.DataFrame(signals)

if df is None or df.empty:
    st.warning("⚠️ No signals generated yet (data issue).")
    st.stop()

if len(df) < 2:
    st.warning("⚠️ Not enough signal history yet.")
    st.stop()

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

# ACTION
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
