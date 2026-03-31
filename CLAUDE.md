# CLAUDE.md

## Project Overview

Orange Team Plane Lap Timer — a Streamlit web app for recording and logging lap times during plane project runs. Lap data is persisted to Snowflake for historical tracking.

## Tech Stack

- **Python 3.8+**
- **Streamlit** — web UI framework
- **Snowflake** — cloud data warehouse for lap storage
- **Dependencies**: `streamlit`, `snowflake-connector-python`

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Snowflake credentials** go in `.streamlit/secrets.toml` (gitignored):

```toml
[snowflake]
account   = "..."
user      = "..."
password  = "..."
database  = "..."
schema    = "..."
warehouse = "..."
```

## Running the App

```bash
streamlit run lap_timer.py
```

Opens at `http://localhost:8501`. No build step required.

## Key Files

- `lap_timer.py` — entire application (UI, timer logic, Snowflake integration)
- `requirements.txt` — Python dependencies
- `.streamlit/secrets.toml` — credentials (not committed)

## Notes

- The Snowflake table is created automatically on first run if it doesn't exist.
- The app refreshes every 50ms while the timer is running.
- No test framework is configured.
