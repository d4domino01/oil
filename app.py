import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

st.write("VERSION 3")

ENTRY_THRESHOLD = 85
EXIT_THRESHOLD = 55

# ==============================
# DATA LOADER (BULLETPROOF)
# ==============================

@st.cache_data
def load_data():
    # Try bulk first
    try:
        data = yf.download(["USO", "XLE", "BNO"], period="3mo")["Close"]

        if data is not None and not data.empty:
            return data.dropna()

    except:
        pass

    # Fallback (much more reliable)
    try:
        uso = yf.download("USO", period="3mo")["Close"]
        xle = yf.download("XLE", period="3mo")["Close"]
        bno = yf.download("BNO", period="3mo")["Close"]

        df = pd.concat([uso, xle, bno], axis=1)
        df.columns = ["USO", "XLE", "BNO"]

        return df.dropna()

    except:
        return None


data = load_data()

# ==============================
# SAFETY CHECKS
# ==============================

if data is None:
    st.error("❌ Data failed to load (Yahoo issue)")
    st.stop()

if data.empty:
    st.error("❌ Data is empty (Yahoo blocked or slow)")
    st.stop()

if len(data) < 10:
    st.warning("⚠️ Not enough data yet")
    st.stop()

# ==============================
# SIGNAL ENGINE
# ==============================

def calc_score(a, b):
    score = 50

    # USO momentum
    score += 15 if a["USO"] > b["USO"] else -15

    # XLE confirmation
    score += 10 if a["XLE"] > b["XLE"] else -10

    # Brent proxy (BNO)
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
        yesterday = data.iloc[i-1]
        day_before = data.iloc[i-2]

        score = calc_score(yesterday, day_before)

        # ENTRY
        if position == 0:
            if score >= ENTRY_THRESHOLD:
                position = 1
            elif score <= 15:
                position = -1

        # HOLD / EXIT
        elif position == 1:
            if score < EXIT_THRESHOLD:
                position = 0

        elif position == -1:
            if score > 45:
                position = 0

        signals.append({
            "date": data.index[i],
            "score": score,
            "position": position
        })

    except:
        continue


df = pd.DataFrame(signals)

# ==============================
# FINAL SAFETY
# ==============================

if df is None or df.empty:
    st.error("❌ No signals generated")
    st.write("Data preview:", data.tail())
    st.stop()

if len(df) < 2:
    st.warning("⚠️ Not enough signals yet")
    st.stop()

# ==============================
# CURRENT SIGNAL
# ==============================

latest = df.iloc[-1]
previous = df.iloc[-2]

# ACTION LOGIC
if latest["position"] != previous["position"]:
    if latest["position"] == 1:
        action = "🚀 ENTER LONG"
    elif latest["position"] == -1:
        action = "🔻 ENTER SHORT"
    else:
        action = "❌ EXIT"
else:
    action = "⏳ HOLD"

confidence = int(abs(latest["score"] - 50) * 2)

# ==============================
# UI
# ==============================

st.title("🛢️ Oil Trading System")

col1, col2, col3 = st.columns(3)

col1.metric("Score", int(latest["score"]))
col2.metric("Confidence", f"{confidence}%")

if latest["position"] == 1:
    col3.metric("Position", "LONG")
elif latest["position"] == -1:
    col3.metric("Position", "SHORT")
else:
    col3.metric("Position", "NONE")

st.markdown(f"## 🔥 ACTION: {action}")

# ==============================
# SIGNAL STRENGTH
# ==============================

if latest["score"] >= ENTRY_THRESHOLD:
    st.success("Strong BULLISH signal (EXTREME)")
elif latest["score"] <= 15:
    st.error("Strong BEARISH signal (EXTREME)")
else:
    st.info("No trade zone")

# ==============================
# TIME
# ==============================

st.caption(f"Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# ==============================
# HISTORY
# ==============================

st.subheader("Recent Signals")
st.dataframe(df.tail(10))

# ==============================
# RULES
# ==============================

st.subheader("Rules")

st.write("""
- Trade ONLY when score ≥ 85 or ≤ 15  
- Enter at 15:30 CET  
- Hold until:
    - Score drops below 55  
    - OR opposite signal  
- Ignore weak signals  
""")
