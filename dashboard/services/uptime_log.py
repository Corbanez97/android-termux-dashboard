from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path
from time import sleep
from typing import Any

from dashboard.services.runtime import collect_service_status


def take_snapshot() -> dict[str, Any]:
    return {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "services": collect_service_status(),
    }


def append_snapshot(log_path: Path) -> dict[str, Any]:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot = take_snapshot()

    with open(log_path, "a", encoding="utf-8") as file_handle:
        file_handle.write(json.dumps(snapshot, separators=(",", ":")))
        file_handle.write("\n")

    return snapshot


def build_history_summary(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summary_by_key: dict[str, dict[str, Any]] = {}

    for entry in entries:
        timestamp = entry.get("timestamp")
        services = entry.get("services", [])
        if not isinstance(services, list):
            continue

        for service in services:
            if not isinstance(service, dict):
                continue

            key = str(service.get("key", service.get("name", "unknown")))
            item = summary_by_key.setdefault(
                key,
                {
                    "name": service.get("name", "unknown"),
                    "group": service.get("group", "Unknown"),
                    "samples": 0,
                    "online_samples": 0,
                    "restart_events": 0,
                    "last_restart_at": None,
                    "last_status_change_at": None,
                    "_last_status": None,
                    "_last_uptime_seconds": None,
                    "_last_restart_counter": None,
                    "latest_status": "unknown",
                    "latest_uptime": "N/A",
                    "latest_timestamp": None,
                },
            )

            item["samples"] += 1
            if service.get("is_online"):
                item["online_samples"] += 1

            uptime_seconds = service.get("uptime_seconds")
            restart_counter = service.get("restarts")
            last_uptime_seconds = item["_last_uptime_seconds"]
            last_restart_counter = item["_last_restart_counter"]

            if (
                isinstance(uptime_seconds, (int, float))
                and isinstance(last_uptime_seconds, (int, float))
                and uptime_seconds + 5 < last_uptime_seconds
            ):
                item["restart_events"] += 1
                item["last_restart_at"] = timestamp

            if (
                isinstance(restart_counter, int)
                and isinstance(last_restart_counter, int)
                and restart_counter > last_restart_counter
            ):
                item["restart_events"] += restart_counter - last_restart_counter
                item["last_restart_at"] = timestamp

            status = service.get("status", "unknown")
            if item["_last_status"] is not None and status != item["_last_status"]:
                item["last_status_change_at"] = timestamp

            item["_last_status"] = status
            item["_last_uptime_seconds"] = uptime_seconds
            item["_last_restart_counter"] = restart_counter
            item["latest_status"] = status
            item["latest_uptime"] = service.get("uptime", "N/A")
            item["latest_timestamp"] = timestamp

    summary: list[dict[str, Any]] = []
    for item in summary_by_key.values():
        samples = item["samples"] or 1
        summary.append(
            {
                "name": item["name"],
                "group": item["group"],
                "samples": item["samples"],
                "online_pct": round((item["online_samples"] / samples) * 100, 1),
                "restart_events": item["restart_events"],
                "last_restart_at": item["last_restart_at"] or "Not observed",
                "last_status_change_at": item["last_status_change_at"] or "Not observed",
                "latest_status": item["latest_status"],
                "latest_uptime": item["latest_uptime"],
                "latest_timestamp": item["latest_timestamp"] or "N/A",
            }
        )

    summary.sort(key=lambda item: item["name"])
    return summary


def build_recent_events(entries: list[dict[str, Any]], max_events: int = 12) -> list[dict[str, Any]]:
    state_by_key: dict[str, dict[str, Any]] = {}
    events: list[dict[str, Any]] = []

    for entry in entries:
        timestamp = entry.get("timestamp", "N/A")
        services = entry.get("services", [])
        if not isinstance(services, list):
            continue

        for service in services:
            if not isinstance(service, dict):
                continue

            key = str(service.get("key", service.get("name", "unknown")))
            previous = state_by_key.get(key)

            if previous:
                previous_status = previous.get("status")
                current_status = service.get("status")
                if previous_status != current_status:
                    events.append(
                        {
                            "timestamp": timestamp,
                            "service": service.get("name", "unknown"),
                            "event": "Status changed",
                            "detail": f"{previous_status} -> {current_status}",
                        }
                    )

                previous_uptime = previous.get("uptime_seconds")
                current_uptime = service.get("uptime_seconds")
                if (
                    isinstance(previous_uptime, (int, float))
                    and isinstance(current_uptime, (int, float))
                    and current_uptime + 5 < previous_uptime
                ):
                    events.append(
                        {
                            "timestamp": timestamp,
                            "service": service.get("name", "unknown"),
                            "event": "Restart observed",
                            "detail": f"uptime reset to {service.get('uptime', 'N/A')}",
                        }
                    )

                previous_restart_count = previous.get("restarts")
                current_restart_count = service.get("restarts")
                if (
                    isinstance(previous_restart_count, int)
                    and isinstance(current_restart_count, int)
                    and current_restart_count > previous_restart_count
                ):
                    events.append(
                        {
                            "timestamp": timestamp,
                            "service": service.get("name", "unknown"),
                            "event": "Restart count increased",
                            "detail": f"{previous_restart_count} -> {current_restart_count}",
                        }
                    )

            state_by_key[key] = service

    return list(reversed(events[-max_events:]))


class UptimeLogWorker(threading.Thread):
    def __init__(self, log_path: Path, sample_interval_seconds: int) -> None:
        super().__init__(name="uptime-log-worker", daemon=True)
        self.log_path = log_path
        self.sample_interval_seconds = max(15, sample_interval_seconds)
        self.stop_event = threading.Event()

    def stop(self) -> None:
        self.stop_event.set()

    def run(self) -> None:
        append_snapshot(self.log_path)

        while not self.stop_event.wait(self.sample_interval_seconds):
            try:
                append_snapshot(self.log_path)
            except OSError:
                sleep(1)
