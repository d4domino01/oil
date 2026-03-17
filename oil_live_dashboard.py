import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

ENTRY_THRESHOLD = 85
EXIT_THRESHOLD = 55

# ==============================
# LOAD DATA
# ==============================

@st.cache_data
def load_data():
    try:
        data = yf.download(["USO", "XLE", "BNO"], period="3mo")["Close"]
        return data
    except:
        return None

data = load_data()

# ==============================
# HARD STOPS (IMPORTANT)
# ==============================

if data is None:
    st.error("❌ Data failed to load")
    st.stop()

if data.empty:
    st.error("❌ Data is empty")
    st.stop()

data = data.dropna()

if len(data) < 10:
    st.warning("⚠️ Not enough data yet")
    st.stop()

# ==============================
# BUILD SIGNALS
# ==============================

def calc_score(a, b):
    score = 50

    score += 15 if a["USO"] > b["USO"] else -15
    score += 10 if a["XLE"] > b["XLE"] else -10

    change = (a["BNO"] - b["BNO"]) / b["BNO"]
    if change > 0.02:
        score += 5
    elif change < -0.02:
        score -= 5

    return score

signals = []
position = 0

for i in range(2, len(data)):
    try:
        y = data.iloc[i-1]
        d = data.iloc[i-2]

        score = calc_score(y, d)

        if position == 0:
            if score >= ENTRY_THRESHOLD:
                position = 1
            elif score <= 15:
                position = -1

        elif position == 1:
            if score < EXIT_THRESHOLD:
                position = 0

        elif position == -1:
            if score > 45:
                position = 0

        signals.append({
            "score": score,
            "position": position
        })

    except:
        continue

df = pd.DataFrame(signals)

# ==============================
# FINAL SAFETY (CRITICAL)
# ==============================

if df is None:
    st.error("❌ df is None")
    st.stop()

if df.empty:
    st.error("❌ No signals generated")
    st.write("Data preview:", data.tail())
    st.stop()

if len(df) < 2:
    st.warning("⚠️ Not enough signals yet")
    st.stop()

# ==============================
# NOW SAFE
# ==============================

latest = df.iloc[-1]
previous = df.iloc[-2]

# ==============================
# UI
# ==============================

st.title("🛢️ Oil System")

st.metric("Score", int(latest["score"]))

if latest["position"] == 1:
    st.success("🚀 LONG")
elif latest["position"] == -1:
    st.error("🔻 SHORT")
else:
    st.info("NO TRADE")

st.write("Last updated:", datetime.now())
