import streamlit as st
import time
from datetime import datetime
import snowflake.connector
import msal
import requests

# ── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="Orange Team Plane Lap Timer", page_icon="⏱️", layout="wide")

# ── Snowflake ─────────────────────────────────────────────────────────────────
@st.cache_resource
def get_snowflake_conn():
    sf = st.secrets["snowflake"]
    return snowflake.connector.connect(
        account=sf["account"],
        user=sf["user"],
        password=sf["password"],
        database=sf["database"],
        schema=sf["schema"],
        warehouse=sf["warehouse"],
    )

def _init_snowflake_table():
    get_snowflake_conn().cursor().execute("""
        CREATE TABLE IF NOT EXISTS OT_PLANE_LAP_TIMES (
            PLANE_ID  INTEGER,
            OPERATOR  VARCHAR,
            TIME      VARCHAR,
            SECONDS   FLOAT,
            LOGGED_AT VARCHAR
        )
    """)

def _write_lap_to_snowflake(lap):
    get_snowflake_conn().cursor().execute(
        "INSERT INTO OT_PLANE_LAP_TIMES (PLANE_ID, OPERATOR, TIME, SECONDS, LOGGED_AT) "
        "VALUES (%s, %s, %s, %s, %s)",
        (lap["PLANE_ID"], lap["OPERATOR"], lap["TIME"], lap["SECONDS"], lap["LOGGED_AT"]),
    )

if "sf_initialized" not in st.session_state:
    _init_snowflake_table()
    st.session_state["sf_initialized"] = True

# ── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;600;700&family=Share+Tech+Mono&display=swap');

html, body, [class*="css"] {
    font-family: 'Rajdhani', sans-serif;
}

/* Dark background */
.stApp {
    background: #0d0f14;
    color: #e0e6f0;
}

/* Timer display */
.timer-display {
    font-family: 'Share Tech Mono', monospace;
    font-size: 5.5rem;
    font-weight: 400;
    letter-spacing: 0.05em;
    color: #00e5ff;
    text-align: center;
    padding: 1.5rem 0 0.5rem;
    text-shadow: 0 0 20px rgba(0, 229, 255, 0.4), 0 0 60px rgba(0, 229, 255, 0.15);
    line-height: 1;
}

.timer-display.running {
    animation: pulse-glow 1.5s ease-in-out infinite;
}

@keyframes pulse-glow {
    0%, 100% { text-shadow: 0 0 20px rgba(0, 229, 255, 0.4), 0 0 60px rgba(0, 229, 255, 0.15); }
    50%       { text-shadow: 0 0 35px rgba(0, 229, 255, 0.7), 0 0 90px rgba(0, 229, 255, 0.3); }
}

.lap-counter {
    font-family: 'Rajdhani', sans-serif;
    font-size: 1rem;
    font-weight: 600;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: #5c6b80;
    text-align: center;
    margin-bottom: 0.25rem;
}

/* Status badge */
.status-badge {
    display: inline-block;
    padding: 0.2rem 0.75rem;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    margin: 0 auto 1rem;
    display: block;
    text-align: center;
}
.status-running  { color: #39ff14; background: rgba(57,255,20,0.1);  border: 1px solid rgba(57,255,20,0.3);  }
.status-stopped  { color: #ff4b4b; background: rgba(255,75,75,0.1);  border: 1px solid rgba(255,75,75,0.3);  }
.status-idle     { color: #5c6b80; background: rgba(92,107,128,0.1); border: 1px solid rgba(92,107,128,0.3); }

/* Buttons */
div[data-testid="stButton"] > button {
    font-family: 'Rajdhani', sans-serif;
    font-weight: 700;
    font-size: 1.05rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    border-radius: 4px;
    padding: 0.6rem 1.2rem;
    transition: all 0.15s ease;
    border: 1px solid transparent;
}

/* Start button */
div[data-testid="stButton"]:nth-of-type(1) > button {
    background: #00e5ff;
    color: #0d0f14;
    border-color: #00e5ff;
}
div[data-testid="stButton"]:nth-of-type(1) > button:hover {
    background: #00b8d4;
    box-shadow: 0 0 15px rgba(0, 229, 255, 0.4);
}

/* Stop button */
div[data-testid="stButton"]:nth-of-type(1) > button[kind="primary"] {
    background: #ff4b4b;
    color: #fff;
    border-color: #ff4b4b;
}



/* Selectbox label */
.stSelectbox label {
    font-family: 'Rajdhani', sans-serif;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    font-size: 0.8rem;
    color: #5c6b80 !important;
}

/* Divider */
hr { border-color: #1e2433; margin: 1.5rem 0; }

/* Laps table header */
.laps-header {
    font-family: 'Rajdhani', sans-serif;
    font-size: 0.8rem;
    font-weight: 700;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: #5c6b80;
    margin-bottom: 0.5rem;
}

/* Dataframe */
.stDataFrame {
    border-radius: 6px;
    overflow: hidden;
}
</style>
""", unsafe_allow_html=True)

# ── Session State ─────────────────────────────────────────────────────────────
defaults = {
    "running": False,
    "start_time": None,
    "laps": [],
    "lap_num": 0,
    "current_operator": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Helpers ───────────────────────────────────────────────────────────────────
def fmt(seconds: float) -> str:
    """Format seconds → MM:SS.cc"""
    if seconds < 0:
        seconds = 0.0
    cs = int((seconds % 1) * 100)
    s  = int(seconds) % 60
    m  = int(seconds) // 60
    return f"{m:02d}:{s:02d}.{cs:02d}"

# ── Azure SSO ─────────────────────────────────────────────────────────────────
@st.cache_resource
def _get_msal_app():
    az = st.secrets["azure"]
    return msal.ConfidentialClientApplication(
        az["client_id"],
        authority=f"https://login.microsoftonline.com/{az['tenant_id']}",
        client_credential=az["client_secret"],
    )

def _get_auth_url() -> str:
    return _get_msal_app().get_authorization_request_url(
        scopes=["User.Read"],
        redirect_uri=st.secrets["azure"]["redirect_uri"],
    )

def _fetch_first_name(code: str):
    result = _get_msal_app().acquire_token_by_authorization_code(
        code,
        scopes=["User.Read"],
        redirect_uri=st.secrets["azure"]["redirect_uri"],
    )
    if "access_token" not in result:
        return None
    data = requests.get(
        "https://graph.microsoft.com/v1.0/me",
        headers={"Authorization": f"Bearer {result['access_token']}"},
    ).json()
    return data.get("givenName") or data.get("displayName")

if "operator" not in st.session_state:
    params = st.query_params
    if "code" in params:
        first_name = _fetch_first_name(params["code"])
        if first_name:
            st.session_state["operator"] = first_name
            st.query_params.clear()
            st.rerun()
        else:
            st.error("Authentication failed. Please try again.")
            st.stop()
    else:
        st.markdown("<h2 style='text-align:center; font-family:Rajdhani; font-weight:700; "
                    "letter-spacing:0.18em; color:#e0e6f0; text-transform:uppercase; "
                    "margin-bottom:0;'>⏱ Orange Team Plane Lap Timer</h2>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.link_button("Sign in with Microsoft", _get_auth_url(), use_container_width=True)
        st.stop()

operator = st.session_state["operator"]

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("<h2 style='text-align:center; font-family:Rajdhani; font-weight:700; "
            "letter-spacing:0.18em; color:#e0e6f0; text-transform:uppercase; "
            "margin-bottom:0;'>⏱ Orange Team Plane Lap Timer</h2>", unsafe_allow_html=True)

st.markdown("<hr>", unsafe_allow_html=True)

# ── Compute elapsed ───────────────────────────────────────────────────────────
if st.session_state.running and st.session_state.start_time:
    elapsed = time.time() - st.session_state.start_time
else:
    elapsed = 0.0

# ── Lap counter label ─────────────────────────────────────────────────────────
lap_label = f"LAP {st.session_state.lap_num}" if st.session_state.lap_num > 0 else "READY"
st.markdown(f"<div class='lap-counter'>{lap_label}</div>", unsafe_allow_html=True)

# ── Timer display ─────────────────────────────────────────────────────────────
timer_slot = st.empty()
running_class = "running" if st.session_state.running else ""
timer_slot.markdown(
    f"<div class='timer-display {running_class}'>{fmt(elapsed)}</div>",
    unsafe_allow_html=True,
)

# ── Status badge ──────────────────────────────────────────────────────────────
if st.session_state.running:
    badge = "<div class='status-badge status-running'>● RUNNING</div>"
elif st.session_state.lap_num > 0:
    badge = "<div class='status-badge status-stopped'>■ STOPPED</div>"
else:
    badge = "<div class='status-badge status-idle'>○ IDLE</div>"
st.markdown(badge, unsafe_allow_html=True)

# ── Control buttons ───────────────────────────────────────────────────────────
col1 = st.container()

with col1:
    if not st.session_state.running:
        btn_label = "▶  START" if st.session_state.lap_num == 0 else "▶  NEW LAP"
        if st.button(btn_label, width='stretch'):
            st.session_state.running    = True
            st.session_state.start_time = time.time()
            st.session_state.lap_num   += 1
            st.session_state.current_operator = operator
            st.rerun()
    else:
        if st.button("⏹  STOP", width='stretch', type="primary"):
            elapsed_final = time.time() - st.session_state.start_time
            lap_row = {
                "PLANE_ID":  st.session_state.lap_num,
                "OPERATOR":  st.session_state.current_operator,
                "TIME":      fmt(elapsed_final),
                "SECONDS":   round(elapsed_final, 3),
                "LOGGED_AT": datetime.now().strftime("%I:%M:%S %p"),
            }
            st.session_state.laps.append(lap_row)
            _write_lap_to_snowflake(lap_row)
            st.session_state.running    = False
            st.session_state.start_time = None
            st.rerun()


# ── Lap history ───────────────────────────────────────────────────────────────
if st.session_state.laps:
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("<div class='laps-header'>Lap History</div>", unsafe_allow_html=True)
    st.dataframe(
        st.session_state.laps,
        width='stretch',
        hide_index=True,
        column_config={
            "PLANE_ID":        st.column_config.NumberColumn(width="small"),
            "OPERATOR": st.column_config.TextColumn(width="medium"),
            "TIME":     st.column_config.TextColumn(width="medium"),
            "SECONDS":  st.column_config.NumberColumn(format="%.3f s", width="medium"),
            "LOGGED_AT":st.column_config.TextColumn(width="medium"),
        },
    )

# ── Live refresh while running ────────────────────────────────────────────────
if st.session_state.running:
    time.sleep(0.05)
    st.rerun()
