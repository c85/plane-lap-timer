# Orange Team Plane Lap Timer

A Streamlit web application for timing and recording laps during the Orange Team plane project. Lap data is persisted to a Snowflake cloud data warehouse for historical tracking and analysis.

## Features

- **Live timer** with real-time MM:SS.cc display and animated glow effect
- **Operator selection** — each lap is attributed to a named team member
- **Automatic Snowflake logging** — every completed lap is written to the cloud database
- **Session lap table** — view all laps recorded in the current session
- Visual status badges: IDLE / RUNNING / STOPPED

## Requirements

- Python 3.8+
- A Snowflake account with an accessible database and schema

## Installation

```bash
# 1. Clone the repo
git clone <repo-url>
cd plane-lap-timer

# 2. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install streamlit snowflake-connector-python
```

## Configuration

Create `.streamlit/secrets.toml` with your Snowflake credentials:

```toml
[snowflake]
account   = "YOUR_ACCOUNT_IDENTIFIER"
user      = "YOUR_USERNAME"
password  = "YOUR_PASSWORD"
database  = "YOUR_DATABASE"
schema    = "YOUR_SCHEMA"
warehouse = "YOUR_WAREHOUSE"
```

> This file is listed in `.gitignore` — never commit credentials to version control.

The app automatically creates the `OT_PLANE_LAP_TIMES` table on first run if it does not already exist.

## Running the App

```bash
streamlit run lap_timer.py
```

The app opens at `http://localhost:8501`.

## Database Schema

```sql
CREATE TABLE OT_PLANE_LAP_TIMES (
    PLANE_ID  INTEGER,   -- Lap number (session-scoped)
    OPERATOR  VARCHAR,   -- Operator who recorded the lap
    TIME      VARCHAR,   -- Formatted time (MM:SS.cc)
    SECONDS   FLOAT,     -- Raw elapsed seconds
    LOGGED_AT VARCHAR    -- Timestamp when the lap was logged
);
```

## Usage

1. Select your name from the **Operator** dropdown.
2. Press **Start** to begin timing.
3. Press **Lap / Stop** to record the lap — the time is saved to Snowflake automatically.
4. Repeat from step 1 for subsequent laps.
5. Press **Clear** to reset the session.
