import streamlit as st
import pandas as pd
from datetime import datetime
import yfinance as yf

st.set_page_config(layout="wide")

st.title("🛢️ Oil Strategy (Clean Long-Only System)")

# ==============================
# LOAD DATA (ROBUST + FALLBACK)
# ==============================

@st.cache_data
def load_data():
    try:
        # Try BWET first (your original system)
        df = yf.download(["USO", "XLE", "BWET"], period="2y")["Close"]

        if df is None or df.empty or "BWET" not in df.columns:
            raise Exception("BWET failed")

        df = df.dropna(subset=["USO", "XLE"])

        # Forward fill BWET gaps
        df["BWET"] = df["BWET"].ffill()

        source = "BWET"

    except:
        # Fallback to BNO (stable)
        df = yf.download(["USO", "XLE", "BNO"], period="2y")["Close"]
        df = df.dropna()

        df.rename(columns={"BNO": "BWET"}, inplace=True)

        source = "BNO (fallback)"

    # SHIFT (no lookahead)
    df["USO_prev"] = df["USO"].shift(1)
    df["XLE_prev"] = df["XLE"].shift(1)
    df["BWET_prev"] = df["BWET"].shift(1)

    df = df.dropna()

    return df, source


data, source = load_data()

# ==============================
# FAIL SAFE
# ==============================

if data is None or len(data) < 10:
    st.error("❌ Data still invalid")
    st.stop()

st.caption(f"Data source: {source}")

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
# SIGNAL ENGINE
# ==============================

entry_threshold = 75
exit_threshold = 55

signals = []

for i in range(2, len(data)):
    y = data.iloc[i-1]
    d = data.iloc[i-2]

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
        "date": data.index[i],
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

st.markdown("## 🛢️ TODAY’S SIGNAL")

col1, col2, col3 = st.columns(3)

col1.metric("Action", latest["action"])
col2.metric("Score", int(latest["score"]))
col3.metric("Confidence", f"{latest['confidence']}%")

# ==============================
# INTERPRETATION
# ==============================

if latest["action"] == "BUY":
    st.success("🚀 Enter trade")
elif latest["action"] == "EXIT":
    st.warning("⚠️ Exit position")
else:
    st.info("⏳ Hold")

# ==============================
# HISTORY
# ==============================

st.subheader("📅 Signal History")
st.dataframe(signals_df.tail(20))

# ==============================
# DATA STATUS
# ==============================

st.subheader("📊 Data Status")

latest_date = data.index[-1]
st.write(f"Latest data: {latest_date}")

if (datetime.now() - latest_date).days > 3:
    st.warning("⚠️ Data may be outdated")
else:
    st.success("✅ Data is recent")
