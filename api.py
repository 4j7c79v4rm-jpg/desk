"""Plan B JSON writer. Writes state.json / chart.json / activity.json every 15s under the secret path."""

import json
from pathlib import Path
from datetime import datetime, timezone

DATA_PATH = "RzghZp5CgxFY1YcYcYq151PVnf5ldz2j_E-bY2KX8-M"
OUT_DIR = Path("/tmp/desk_data") / DATA_PATH
OUT_DIR.mkdir(parents=True, exist_ok=True)


def write_state(balance: float, mode: str = "PAPER", agents=None):
    state = {
        "balance": round(balance, 2),
        "today_pct": 0.0,
        "multiplier": round(balance / 200.0, 3),
        "mode": mode,
        "agents": agents or [],
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    (OUT_DIR / "state.json").write_text(json.dumps(state, indent=2))


def write_activity(rows):
    (OUT_DIR / "activity.json").write_text(json.dumps(rows, indent=2))


def write_chart(points):
    (OUT_DIR / "chart.json").write_text(json.dumps(points, indent=2))
