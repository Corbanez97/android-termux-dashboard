from __future__ import annotations

import json
import os
import time
from collections import deque
from subprocess import DEVNULL, CalledProcessError, run
from typing import Any

from dashboard.utils import format_duration


def run_command(command: list[str]) -> str | None:
    try:
        completed = run(command, check=True, stdout=-1, stderr=DEVNULL, text=True)
    except (CalledProcessError, OSError):
        return None

    return completed.stdout.strip()


def run_command_json(command: list[str]) -> Any:
    output = run_command(command)
    if not output:
        return None

    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return None


def get_device_uptime_seconds() -> float | None:
    try:
        with open("/proc/uptime", "r", encoding="utf-8") as file_handle:
            return float(file_handle.read().split()[0])
    except (OSError, ValueError, IndexError):
        return None


def get_process_uptime_seconds(pid: int | None) -> float | None:
    if not pid:
        return None

    try:
        with open(f"/proc/{pid}/stat", "r", encoding="utf-8") as file_handle:
            fields = file_handle.read().split()
    except OSError:
        return None

    try:
        start_ticks = int(fields[21])
    except (IndexError, ValueError):
        return None

    try:
        ticks_per_second = os.sysconf(os.sysconf_names["SC_CLK_TCK"])
    except (AttributeError, KeyError, ValueError):
        ticks_per_second = 100

    system_uptime = get_device_uptime_seconds()
    if system_uptime is None:
        return None

    return max(0.0, system_uptime - (start_ticks / ticks_per_second))


def get_pm2_processes() -> list[dict[str, Any]]:
    payload = run_command_json(["pm2", "jlist"])
    if not isinstance(payload, list):
        return []

    services: list[dict[str, Any]] = []

    for item in payload:
        env = item.get("pm2_env", {}) if isinstance(item, dict) else {}
        pid = item.get("pid") if isinstance(item.get("pid"), int) and item.get("pid") > 0 else None
        uptime_seconds = get_process_uptime_seconds(pid)

        if uptime_seconds is None:
            pm_uptime_ms = env.get("pm_uptime")
            if isinstance(pm_uptime_ms, (int, float)):
                uptime_seconds = max(0.0, time.time() - (pm_uptime_ms / 1000))

        status = str(env.get("status", "unknown"))
        name = str(item.get("name", "unknown"))

        services.append(
            {
                "key": f"pm2:{name}",
                "name": name,
                "group": "PM2",
                "status": status,
                "is_online": status == "online",
                "status_class": "status-up" if status == "online" else "status-down",
                "pid": pid,
                "uptime": format_duration(uptime_seconds),
                "uptime_seconds": uptime_seconds,
                "restarts": env.get("restart_time", 0),
                "details": f"cwd: {env.get('pm_cwd', 'N/A')}",
            }
        )

    services.sort(key=lambda service: service["name"])
    return services


def find_sshd_pid() -> int | None:
    output = run_command(["ps", "-ef"]) or run_command(["ps"])
    if not output:
        return None

    for line in output.splitlines():
        if "sshd -D -e" not in line or "sshd-session" in line:
            continue

        columns = line.split()
        if len(columns) < 2:
            continue

        try:
            return int(columns[1])
        except ValueError:
            continue

    return None


def get_sshd_service() -> dict[str, Any]:
    service_status = (
        run_command(["sv", "status", "/data/data/com.termux/files/usr/var/service/sshd"])
        or "unknown"
    )
    pid = find_sshd_pid()
    uptime_seconds = get_process_uptime_seconds(pid)
    is_online = service_status.startswith("run:")

    return {
        "key": "service:sshd",
        "name": "sshd",
        "group": "Runit",
        "status": "online" if is_online else service_status,
        "is_online": is_online,
        "status_class": "status-up" if is_online else "status-down",
        "pid": pid,
        "uptime": format_duration(uptime_seconds),
        "uptime_seconds": uptime_seconds,
        "restarts": None,
        "details": service_status,
    }


def collect_service_status() -> list[dict[str, Any]]:
    services = get_pm2_processes()
    services.append(get_sshd_service())
    return services


def read_recent_log_entries(log_path: str, limit: int) -> list[dict[str, Any]]:
    entries: deque[str] = deque(maxlen=limit)

    try:
        with open(log_path, "r", encoding="utf-8") as file_handle:
            for line in file_handle:
                if line.strip():
                    entries.append(line)
    except OSError:
        return []

    parsed_entries: list[dict[str, Any]] = []
    for line in entries:
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue

        if isinstance(payload, dict):
            parsed_entries.append(payload)

    return parsed_entries
