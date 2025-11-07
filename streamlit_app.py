# streamlit_app.py
# Streamlit app untuk menampilkan data potensiometer dari Flask (endpoint /value)
# Install: pip install streamlit requests pandas
# streamlit run streamlit_app.py
import streamlit as st
import requests
import pandas as pd
import time
from collections import deque
from datetime import datetime

# ========== UBAH DI SINI ========== #
BASE_URL = "http://10.33.82.18:5000"   # ganti dengan IP Flask Anda
POLL_DEFAULT_S = 1.0                   # interval polling default (detik)
HISTORY_MAX = 200                      # maksimal jumlah data yg disimpan
# ================================== #

st.set_page_config(page_title="Project ua ESP32 Pot Live", layout="centered")
st.title("ESP32 Potensiometer ua — Live (Streamlit)")
st.write("Alur: ESP32 → Flask (/post_value) → Streamlit (GET /value)")

# Sidebar controls
with st.sidebar:
    st.header("Settings")
    poll_s = st.slider("Polling interval (detik)", min_value=0.5, max_value=5.0, value=float(POLL_DEFAULT_S), step=0.5)
    auto_start = st.checkbox("Auto start polling", value=True)
    clear_btn = st.button("Clear history")

# Persistent history in session state
if "history" not in st.session_state:
    st.session_state.history = deque(maxlen=HISTORY_MAX)  # holds tuples (timestamp, raw, volt)

if clear_btn:
    st.session_state.history.clear()

# Controls
col1, col2, col3 = st.columns([1,1,1])
with col1:
    start = st.button("Start") if not auto_start else False
with col2:
    stop = st.button("Stop")
with col3:
    refresh_now = st.button("Refresh now")

# Display area
metrics_col = st.empty()
chart_col = st.empty()
table_col = st.empty()
status_col = st.empty()

running = auto_start or start
if stop:
    running = False
    st.session_state["running"] = False
else:
    # persist running flag
    if "running" not in st.session_state:
        st.session_state["running"] = auto_start
    if start:
        st.session_state["running"] = True
    running = st.session_state["running"]

# Helper to fetch value from Flask
def fetch_value():
    try:
        resp = requests.get(f"{BASE_URL}/value", timeout=2)
        if resp.status_code == 200:
            d = resp.json()
            # normalize
            ts = d.get("time") or datetime.utcnow().isoformat()
            raw = d.get("raw")
            volt = d.get("voltage")
            return True, (ts, raw, volt)
        else:
            return False, f"HTTP {resp.status_code}"
    except Exception as e:
        return False, str(e)

# One-off refresh
if refresh_now:
    ok, data = fetch_value()
    if ok:
        st.session_state.history.append(data)
    else:
        st.error(f"Refresh failed: {data}")

# Poll loop (server-side)
if running:
    # run polling loop but yield control to streamlit UI periodically
    stop_time = time.time() + 5  # loop for up to 5 seconds per rerun to keep UI responsive
    # Single fetch each rerun usually enough; here we fetch once
    ok, data = fetch_value()
    if ok:
        st.session_state.history.append(data)
        status_col.success(f"Last fetched: {data[0]}")
    else:
        status_col.error(f"Fetch error: {data}")

# Build dataframe from history
hist = list(st.session_state.history)
if hist:
    df = pd.DataFrame(hist, columns=["time","raw","voltage"])
    df["time"] = pd.to_datetime(df["time"])
    df = df.set_index("time")
else:
    df = pd.DataFrame(columns=["raw","voltage"])

# Show metrics
if not df.empty:
    latest_raw = int(df["raw"].iloc[-1]) if pd.notna(df["raw"].iloc[-1]) else None
    latest_volt = float(df["voltage"].iloc[-1]) if pd.notna(df["voltage"].iloc[-1]) else None
else:
    latest_raw = None
    latest_volt = None

with metrics_col.container():
    c1, c2, c3 = st.columns(3)
    c1.metric("Raw (12-bit)", latest_raw if latest_raw is not None else "—")
    c2.metric("Voltage (V)", f"{latest_volt:.3f}" if latest_volt is not None else "—")
    c3.metric("History length", len(df))

# Chart
with chart_col.container():
    st.subheader("Voltage (V) over time")
    if not df.empty:
        st.line_chart(df["voltage"])
    else:
        st.info("No data yet. Start polling or send a POST from ESP32.")

# Table (last 20)
with table_col.container():
    st.subheader("Recent values")
    if not df.empty:
        st.dataframe(df.tail(20))
    else:
        st.write("—")

# Auto re-run after poll_s seconds if running
if running:
    # store running flag to session_state so buttons persist next run
    st.session_state["running"] = True
    st.experimental_rerun()  # immediately rerun to reflect latest fetch
else:
    st.session_state["running"] = False
    st.write("Polling stopped. Click Start or enable Auto start.")
