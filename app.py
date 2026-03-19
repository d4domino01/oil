import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(layout="wide")

st.title("🛢️ Oil Strategy (FINAL — Backtest Matched)")

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
    df.columns = ["USO", "XLE", "BWET"]  # keep naming consistent

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
# SIGNAL ENGINE (CORRECT TIMING)
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
        "date": t.name,  # execution date
        "score": score,
        "confidence": int(min(confidence, 100)),
        "action": action
    })

signals_df = pd.DataFrame(signals)

if signals_df.empty:
    st.error("❌ No signals generated")
    st.stop()

# ==============================
# SIGNAL EXPLANATION (NEW)
# ==============================

st.subheader("🧠 Signal Explanation")

# Use same rows as signal logic
y = data.iloc[-2]
d = data.iloc[-3]

explanation = []
score_parts = []

# --- USO ---
if y["USO"] > d["USO"]:
    explanation.append("✔ USO rising")
    score_parts.append("+15 USO up")
else:
    explanation.append("✖ USO falling")
    score_parts.append("-15 USO down")

# --- XLE ---
if y["XLE"] > d["XLE"]:
    explanation.append("✔ XLE rising")
    score_parts.append("+10 XLE up")
else:
    explanation.append("✖ XLE falling")
    score_parts.append("-10 XLE down")

# --- BWET / BNO ---
bwet_change = (y["BWET"] - d["BWET"]) / d["BWET"]

if bwet_change > 0.03:
    explanation.append("✔ Strong oil move (BNO/BWET)")
    score_parts.append("+5 oil strength")
elif bwet_change < -0.03:
    explanation.append("✖ Oil weakness")
    score_parts.append("-5 oil weakness")
else:
    explanation.append("• Oil neutral")
    score_parts.append("0 oil neutral")

# --- MOMENTUM ---
uso_change = abs((y["USO"] - d["USO"]) / d["USO"])

if uso_change > 0.03:
    explanation.append("✔ Strong momentum spike")
    score_parts.append("+5 momentum")
else:
    explanation.append("• No strong momentum")
    score_parts.append("0 momentum")

# ==============================
# DISPLAY
# ==============================

st.markdown("### 🔍 Why this signal?")

for item in explanation:
    st.write(item)

st.markdown("### 📊 Score Breakdown")

for part in score_parts:
    st.write(part)

# ==============================
# FINAL DECISION LOGIC DISPLAY
# ==============================

st.markdown("### ⚙️ Decision Logic")

if latest["action"] == "BUY":
    st.success("BUY triggered: Score ≥ 75")
elif latest["action"] == "EXIT":
    st.warning("EXIT triggered: Score < 55")
else:
    st.info("HOLD: Score between 55 and 75")

# ==============================
# CURRENT SIGNAL (TODAY)
# ==============================

latest = signals_df.iloc[-1]

st.markdown("## 🛢️ TODAY’S TRADE DECISION")

col1, col2, col3 = st.columns(3)

col1.metric("Action", latest["action"])
col2.metric("Score", int(latest["score"]))
col3.metric("Confidence", f"{latest['confidence']}%")

# ==============================
# INTERPRETATION
# ==============================

if latest["action"] == "BUY":
    st.success("🚀 Enter trade at market open")
elif latest["action"] == "EXIT":
    st.warning("⚠️ Exit position at market open")
else:
    st.info("⏳ No action — hold / stay out")

# ==============================
# SIGNAL HISTORY
# ==============================

st.subheader("📅 Signal History (Execution Days)")
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
# DEBUG (OPTIONAL)
# ==============================

with st.expander("🔍 Debug (Signal Inputs)"):
    st.write("Yesterday (signal):")
    st.write(data.iloc[-2])

    st.write("Day before:")
    st.write(data.iloc[-3])
