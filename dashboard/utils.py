from __future__ import annotations

from typing import Any


def format_duration(seconds: float | None) -> str:
    if seconds is None:
        return "N/A"

    total_seconds = max(0, int(seconds))
    days, rem = divmod(total_seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)

    if days > 0:
        return f"{days}d {hours:02d}:{minutes:02d}:{secs:02d}"

    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def format_percent(value: float | int | None) -> str:
    if value is None:
        return "N/A"
    return f"{value}%"


def format_memory_mb(value: float | int | None) -> str:
    if value is None:
        return "N/A"
    return f"{value} MB"


def format_storage_gb(value: float | int | None) -> str:
    if value is None:
        return "N/A"
    return f"{value} GB"


def present(value: Any) -> str:
    if value in (None, "", []):
        return "N/A"
    return str(value)


def rows_from_mapping(mapping: dict[str, Any], labels: dict[str, str] | None = None) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    labels = labels or {}

    for key, value in mapping.items():
        rows.append(
            {
                "label": labels.get(key, key.replace("_", " ").title()),
                "value": present(value),
            }
        )

    return rows
