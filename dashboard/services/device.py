from __future__ import annotations

import json
import os
import shutil
import socket
import time
from datetime import datetime
from subprocess import DEVNULL, CalledProcessError, check_output
from typing import Any

import requests

from dashboard.utils import format_duration


def run_command(command: str) -> str | None:
    try:
        return check_output(command, shell=True, text=True, stderr=DEVNULL).strip()
    except (CalledProcessError, OSError):
        return None


def run_command_json(command: str) -> dict[str, Any]:
    output = run_command(command)
    if not output:
        return {}

    try:
        payload = json.loads(output)
    except json.JSONDecodeError:
        return {}

    return payload if isinstance(payload, dict) else {}


def get_battery() -> dict[str, Any]:
    return run_command_json("termux-battery-status")


def get_wifi_connectioninfo() -> dict[str, Any]:
    return run_command_json("termux-wifi-connectioninfo")


def get_telephony() -> dict[str, Any]:
    return run_command_json("termux-telephony-deviceinfo")


def get_device_uptime_seconds() -> float | None:
    try:
        with open("/proc/uptime", "r", encoding="utf-8") as file_handle:
            return float(file_handle.read().split()[0])
    except (OSError, ValueError, IndexError):
        return None


def get_loadavg() -> dict[str, float]:
    try:
        one, five, fifteen = os.getloadavg()
    except OSError:
        return {}

    return {"1m": round(one, 2), "5m": round(five, 2), "15m": round(fifteen, 2)}


def get_memory_info() -> dict[str, float]:
    fields: dict[str, str] = {}

    try:
        with open("/proc/meminfo", "r", encoding="utf-8") as file_handle:
            for line in file_handle:
                key, value = line.split(":", 1)
                fields[key.strip()] = value.strip()
    except OSError:
        return {}

    def parse_kb(field: str) -> int | None:
        raw_value = fields.get(field)
        if not raw_value:
            return None

        try:
            return int(raw_value.split()[0])
        except (ValueError, IndexError):
            return None

    total = parse_kb("MemTotal")
    available = parse_kb("MemAvailable")
    if total is None or available is None or total == 0:
        return {}

    used = total - available

    return {
        "total_mb": round(total / 1024, 1),
        "available_mb": round(available / 1024, 1),
        "used_mb": round(used / 1024, 1),
        "used_pct": round((used / total) * 100, 1),
    }


def get_storage_info(path: str = "/data/data/com.termux/files/home") -> dict[str, float | str]:
    try:
        usage = shutil.disk_usage(path)
    except OSError:
        return {}

    return {
        "path": path,
        "total_gb": round(usage.total / (1024**3), 2),
        "used_gb": round(usage.used / (1024**3), 2),
        "free_gb": round(usage.free / (1024**3), 2),
        "used_pct": round((usage.used / usage.total) * 100, 1) if usage.total else None,
    }


def get_local_ip() -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return "N/A"
    finally:
        sock.close()


def get_external_ip() -> str:
    for url in ("https://api.ipify.org", "https://ifconfig.me/ip"):
        try:
            response = requests.get(url, timeout=3)
            if response.ok:
                return response.text.strip()
        except requests.RequestException:
            continue

    return "N/A"


def check_url(url: str) -> dict[str, Any]:
    started_at = time.time()

    try:
        response = requests.get(url, timeout=4)
        return {
            "url": url,
            "ok": True,
            "status_code": response.status_code,
            "latency_ms": round((time.time() - started_at) * 1000, 1),
            "error": "",
        }
    except requests.RequestException as exc:
        return {
            "url": url,
            "ok": False,
            "status_code": None,
            "latency_ms": round((time.time() - started_at) * 1000, 1),
            "error": str(exc),
        }


def collect_device_status() -> dict[str, Any]:
    uptime_seconds = get_device_uptime_seconds()
    battery = get_battery()

    return {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "device": {
            "hostname": socket.gethostname(),
            "local_ip": get_local_ip(),
            "external_ip": get_external_ip(),
            "uptime": format_duration(uptime_seconds),
            "uptime_seconds": uptime_seconds,
        },
        "battery": battery,
        "memory": get_memory_info(),
        "storage": get_storage_info(),
        "loadavg": get_loadavg(),
        "wifi": get_wifi_connectioninfo(),
        "telephony": get_telephony(),
        "connectivity_checks": [
            check_url("https://google.com"),
            check_url("https://github.com"),
            check_url("https://cloudflare.com"),
        ],
    }
