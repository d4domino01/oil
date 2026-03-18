import streamlit as st
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt

st.set_page_config(layout="wide")

st.title("🛢️ Oil Trading System (FULL PLATFORM)")

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

    df = df.sort_index().dropna()

    # 🔒 LOCK DATA
    df = df.iloc[:-1]

    return df

data = load_data()

# ==============================
# DATA STATUS
# ==============================

latest_date = data.index[-1]
st.subheader("📊 Data Status")
st.write(f"Using confirmed data up to: {latest_date}")

# ==============================
# INDICATORS
# ==============================

data["MA20"] = data["USO"].rolling(20).mean()
data["MA50"] = data["USO"].rolling(50).mean()
data["RET"] = data["USO"].pct_change()
data["VOL"] = data["RET"].rolling(10).std()

data = data.dropna()

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

    if divergence > 0.012:
        return "BULLISH"
    elif divergence < -0.012:
        return "BEARISH"
    return "NEUTRAL"

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
# SIGNAL ENGINE
# ==============================

signals = []

for i in range(50, len(data)):
    y = data.iloc[i-1]
    d = data.iloc[i-2]

    trend = get_trend(y)
    lead = futures_lead(y, d)
    vol = volatility_state(y)

    score = calculate_score(y, d, trend, lead)
    confidence = int(min(abs(score - 50) * 2, 100))

    cond_conf = confidence > 70
    cond_vol = vol != "LOW"
    cond_lead = lead != "NEUTRAL"

    if cond_conf and cond_vol and cond_lead:
        action = "BUY" if trend == 1 else "SELL"
    else:
        action = "NO TRADE"

    signals.append({
        "date": data.index[i],
        "action": action,
        "score": score,
        "confidence": confidence
    })

signals_df = pd.DataFrame(signals)

# ==============================
# CURRENT SIGNAL
# ==============================

latest = signals_df.iloc[-1]

st.markdown("## 🛢️ TODAY’S SIGNAL")

st.metric("Action", latest["action"])
st.metric("Confidence", f"{latest['confidence']}%")

# ==============================
# TRADE SIMULATION
# ==============================

capital = 10000
position = 0
entry_price = 0

trade_log = []
equity = []

for i in range(1, len(signals_df)):
    row = signals_df.iloc[i]
    price = data.iloc[i]["USO"]

    prev_position = position

    if position == 0:
        if row["action"] == "BUY":
            position = 1
            entry_price = price
            trade_log.append({"Date": row["date"], "Type": "BUY", "Entry": price})

        elif row["action"] == "SELL":
            position = -1
            entry_price = price
            trade_log.append({"Date": row["date"], "Type": "SELL", "Entry": price})

    else:
        if row["action"] == "NO TRADE":
            exit_price = price
            pnl = (exit_price - entry_price) / entry_price
            if position == -1:
                pnl *= -1

            capital *= (1 + pnl)

            trade_log[-1]["Exit"] = exit_price
            trade_log[-1]["PnL %"] = round(pnl * 100, 2)

            position = 0

    equity.append(capital)

# ==============================
# PERFORMANCE
# ==============================

st.subheader("📊 Performance")

if trade_log:
    trades_df = pd.DataFrame(trade_log)

    wins = len(trades_df[trades_df["PnL %"] > 0])
    total = len(trades_df)

    win_rate = (wins / total) * 100 if total > 0 else 0
    total_return = (capital / 10000 - 1) * 100

    col1, col2, col3 = st.columns(3)

    col1.metric("Total Return", f"{round(total_return,2)}%")
    col2.metric("Trades", total)
    col3.metric("Win Rate", f"{round(win_rate,2)}%")

    st.subheader("📅 Trade Log")
    st.dataframe(trades_df.tail(10))

# ==============================
# EQUITY CURVE
# ==============================

st.subheader("📈 Equity Curve")

fig, ax = plt.subplots()
ax.plot(equity)
ax.set_title("Equity Curve")
st.pyplot(fig)

# ==============================
# SIGNAL HISTORY
# ==============================

st.subheader("📅 Signal History")
st.dataframe(signals_df.tail(20))

# ==============================
# FOOTER
# ==============================

st.caption(f"Updated: {datetime.now()}")
