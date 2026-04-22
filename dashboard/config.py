from __future__ import annotations

import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "dashboard" / "templates"
STATIC_DIR = BASE_DIR / "dashboard" / "static"
DATA_DIR = BASE_DIR / "data"
UPTIME_LOG_PATH = DATA_DIR / "uptime-log.jsonl"
WATCHDOG_LOG_PATH = DATA_DIR / "service-watch.log"

AUTO_REFRESH_SECONDS = int(os.getenv("DASHBOARD_AUTO_REFRESH_SECONDS", "15"))
SAMPLE_INTERVAL_SECONDS = int(os.getenv("DASHBOARD_SAMPLE_INTERVAL_SECONDS", "60"))
HISTORY_LIMIT = int(os.getenv("DASHBOARD_HISTORY_LIMIT", "1440"))
