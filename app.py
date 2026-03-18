import streamlit as st
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt

st.set_page_config(layout="wide")

st.title("🛢️ Oil Trading System (PRO COMPLETE)")

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

    return df.sort_index().dropna().tail(200)

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

    if divergence > 0.01:
        return "BULLISH"
    elif divergence < -0.01:
        return "BEARISH"
    return "NEUTRAL"

def calculate_score(a, b, trend):
    score = 50
    score += 20 if a["USO"] > b["USO"] else -20
    score += 15 if a["XLE"] > b["XLE"] else -15

    lead = futures_lead(a, b)

    if lead == "BULLISH":
        score += 10
    elif lead == "BEARISH":
        score -= 10

    if trend == 1:
        score += 10
    else:
        score -= 10

    return score, lead

# ==============================
# DAILY DECISION
# ==============================

y = data.iloc[-1]
d = data.iloc[-2]

trend = get_trend(y)
score, lead = calculate_score(y, d, trend)
vol = volatility_state(y)

confidence = int(abs(score - 50) * 2)

cond_conf = confidence > 70
cond_vol = vol != "LOW"
cond_lead = lead != "NEUTRAL"

conditions_passed = sum([cond_conf, cond_vol, cond_lead])

# ==============================
# DECISION ENGINE
# ==============================

if conditions_passed == 3:
    action = "🚀 TRADE"
    action_detail = "TREND BUY" if trend == 1 else "TREND SELL"
    reason = "All conditions aligned"

elif conditions_passed == 2:
    action = "🟡 ALMOST TRADE"
    action_detail = "WAIT / WATCH"
    failed = []
    if not cond_conf: failed.append("Confidence")
    if not cond_vol: failed.append("Volatility")
    if not cond_lead: failed.append("Futures")
    reason = f"Missing: {', '.join(failed)}"

else:
    action = "⏳ NO TRADE"
    action_detail = "STAY OUT"
    failed = []
    if not cond_conf: failed.append("Confidence")
    if not cond_vol: failed.append("Volatility")
    if not cond_lead: failed.append("Futures")
    reason = f"Weak setup: {', '.join(failed)}"

# ==============================
# DISPLAY MAIN
# ==============================

st.markdown("## 🛢️ TODAY’S TRADE DECISION")

col1, col2, col3 = st.columns(3)

col1.metric("Action", action)
col2.metric("Confidence", f"{confidence}%")
col3.metric("Trend", "UP" if trend == 1 else "DOWN")

st.markdown(f"### 👉 {action_detail}")
st.markdown(f"### 🧠 Reason: {reason}")

# ALERTS
if conditions_passed == 3:
    st.success("🔔 TRADE SIGNAL ACTIVE — TAKE TRADE")
elif conditions_passed == 2:
    st.warning("🟡 CLOSE — monitor next session")

# ==============================
# AI INSIGHT
# ==============================

st.subheader("🧠 AI Market Insight")

if conditions_passed == 3:
    st.success("Strong confirmed setup — execute trade")

elif conditions_passed == 2:
    if not cond_lead:
        st.warning("Trend strong + volatility good → waiting for futures confirmation (likely soon)")
    elif not cond_conf:
        st.warning("Structure good but momentum not strong enough yet")
    elif not cond_vol:
        st.warning("Market quiet — breakout possible if volatility expands")

else:
    st.info("No meaningful setup forming")

# ==============================
# CONDITION CHECK
# ==============================

st.subheader("Condition Check")

st.write(f"Confidence > 70: {'✅' if cond_conf else '❌'}")
st.write(f"Volatility OK: {'✅' if cond_vol else '❌'}")
st.write(f"Futures Confirmed: {'✅' if cond_lead else '❌'}")

# ==============================
# TRADE TRACKER
# ==============================

st.subheader("📊 Trade Performance Tracker")

capital = 10000
position = 0
entry_price = 0

equity_curve = []
trade_log = []

for i in range(50, len(data)):
    y = data.iloc[i-1]
    d = data.iloc[i-2]
    t = data.iloc[i]

    trend = get_trend(y)
    score, lead = calculate_score(y, d, trend)
    vol = volatility_state(y)

    confidence = abs(score - 50) * 2

    c = confidence > 70
    v = vol != "LOW"
    l = lead != "NEUTRAL"

    prev_position = position

    if position == 0 and c and v and l:
        position = 1 if trend == 1 else -1
        entry_price = t["USO"]

        trade_log.append({
            "Date": data.index[i],
            "Type": "BUY" if position == 1 else "SELL",
            "Entry": entry_price
        })

    elif position != 0:
        if not (c and v and l):
            exit_price = t["USO"]
            pnl = (exit_price - entry_price) / entry_price
            if position == -1:
                pnl *= -1

            capital *= (1 + pnl)

            trade_log[-1]["Exit"] = exit_price
            trade_log[-1]["PnL %"] = round(pnl * 100, 2)

            position = 0

    equity_curve.append(capital)

# DISPLAY TRADES
if trade_log:
    trades_df = pd.DataFrame(trade_log)
    st.dataframe(trades_df.tail(10))

    total_return = (capital / 10000 - 1) * 100
    st.metric("Total Return", f"{round(total_return,2)}%")

# EQUITY CURVE
fig, ax = plt.subplots()
ax.plot(equity_curve)
ax.set_title("Equity Curve")
st.pyplot(fig)

# ==============================
# FILTER STATS
# ==============================

stats = {"confidence": 0, "vol": 0, "lead": 0}

for i in range(50, len(data)):
    y = data.iloc[i-1]
    d = data.iloc[i-2]

    trend = get_trend(y)
    score, lead = calculate_score(y, d, trend)
    vol = volatility_state(y)

    confidence = abs(score - 50) * 2

    if not (confidence > 70): stats["confidence"] += 1
    if not (vol != "LOW"): stats["vol"] += 1
    if not (lead != "NEUTRAL"): stats["lead"] += 1

st.subheader("📊 Filter Blocking Stats")

st.write(f"Confidence blocked: {stats['confidence']}")
st.write(f"Volatility blocked: {stats['vol']}")
st.write(f"Futures blocked: {stats['lead']}")

# ==============================
# FOOTER
# ==============================

st.caption(f"Updated: {datetime.now()}")
