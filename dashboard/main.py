from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from dashboard.config import (
    AUTO_REFRESH_SECONDS,
    DATA_DIR,
    HISTORY_LIMIT,
    SAMPLE_INTERVAL_SECONDS,
    STATIC_DIR,
    TEMPLATES_DIR,
    UPTIME_LOG_PATH,
)
from dashboard.services.device import collect_device_status
from dashboard.services.runtime import collect_service_status, read_recent_log_entries
from dashboard.services.uptime_log import UptimeLogWorker, build_history_summary, build_recent_events
from dashboard.utils import format_memory_mb, format_percent, format_storage_gb, rows_from_mapping


templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@asynccontextmanager
async def lifespan(app: FastAPI):
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    worker = UptimeLogWorker(
        log_path=UPTIME_LOG_PATH,
        sample_interval_seconds=SAMPLE_INTERVAL_SECONDS,
    )
    worker.start()
    app.state.uptime_log_worker = worker

    try:
        yield
    finally:
        worker.stop()
        worker.join(timeout=2)


app = FastAPI(title="Android Termux Dashboard", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def build_dashboard_payload() -> dict[str, Any]:
    device_status = collect_device_status()
    services = collect_service_status()
    history_entries = read_recent_log_entries(str(UPTIME_LOG_PATH), HISTORY_LIMIT)
    history_summary = build_history_summary(history_entries)
    recent_events = build_recent_events(history_entries)

    online_services = sum(1 for service in services if service.get("is_online"))
    service_count = len(services)
    memory = device_status["memory"]
    storage = device_status["storage"]
    battery = device_status["battery"]
    device = device_status["device"]
    battery_level = battery.get("percentage")

    headline_stats = [
        {
            "label": "Services online",
            "value": f"{online_services}/{service_count}",
            "tone": "neutral",
        },
        {
            "label": "Device uptime",
            "value": device.get("uptime", "N/A"),
            "tone": "neutral",
        },
        {
            "label": "Battery",
            "value": f"{battery_level if battery_level is not None else 'N/A'}%",
            "tone": "good" if isinstance(battery_level, (int, float)) and battery_level >= 50 else "warn",
        },
        {
            "label": "Memory used",
            "value": format_percent(memory.get("used_pct")),
            "tone": "warn" if (memory.get("used_pct") or 0) >= 80 else "neutral",
        },
    ]

    sections = {
        "device_rows": rows_from_mapping(
            {
                "hostname": device.get("hostname"),
                "local_ip": device.get("local_ip"),
                "external_ip": device.get("external_ip"),
                "uptime": device.get("uptime"),
            }
        ),
        "battery_rows": rows_from_mapping(
            {
                "percentage": battery.get("percentage"),
                "status": battery.get("status"),
                "plugged": battery.get("plugged"),
                "temperature_c": battery.get("temperature"),
                "health": battery.get("health"),
                "voltage_mv": battery.get("voltage"),
                "current_ma": battery.get("current"),
            }
        ),
        "memory_rows": rows_from_mapping(
            {
                "total": format_memory_mb(memory.get("total_mb")),
                "available": format_memory_mb(memory.get("available_mb")),
                "used": format_memory_mb(memory.get("used_mb")),
                "used_pct": format_percent(memory.get("used_pct")),
            }
        ),
        "storage_rows": rows_from_mapping(
            {
                "path": storage.get("path"),
                "total": format_storage_gb(storage.get("total_gb")),
                "used": format_storage_gb(storage.get("used_gb")),
                "free": format_storage_gb(storage.get("free_gb")),
                "used_pct": format_percent(storage.get("used_pct")),
            }
        ),
        "network_rows": rows_from_mapping(device_status["wifi"]),
        "telephony_rows": rows_from_mapping(device_status["telephony"]),
        "load_rows": rows_from_mapping(device_status["loadavg"]),
    }

    return {
        "timestamp": device_status["timestamp"],
        "device_status": device_status,
        "services": services,
        "history_summary": history_summary,
        "recent_events": recent_events,
        "headline_stats": headline_stats,
        "sections": sections,
        "auto_refresh_seconds": AUTO_REFRESH_SECONDS,
    }


@app.get("/health", response_class=PlainTextResponse)
def health() -> str:
    return "ok"


@app.get("/api/status", response_class=JSONResponse)
def api_status() -> JSONResponse:
    return JSONResponse(build_dashboard_payload())


@app.get("/api/uptime-log", response_class=JSONResponse)
def api_uptime_log() -> JSONResponse:
    entries = read_recent_log_entries(str(UPTIME_LOG_PATH), HISTORY_LIMIT)
    return JSONResponse(
        {
            "entries": entries,
            "summary": build_history_summary(entries),
            "events": build_recent_events(entries),
        }
    )


@app.get("/")
def dashboard(request: Request):
    context = build_dashboard_payload()
    context["request"] = request
    return templates.TemplateResponse("dashboard.html", context)
