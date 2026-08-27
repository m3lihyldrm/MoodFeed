"""MoodFeed Data Export & CSV Sanitization Utilities.

Protects against CSV formula injection (OWASP ASVS compliance).
"""

from __future__ import annotations

import json
from typing import Any


def sanitize_csv_cell(val: Any) -> str:
    """Sanitizes a single cell to prevent spreadsheet formula injection.

    If value begins with =, +, -, @, tab, or carriage return, prepends a single quote.
    Wraps result in double quotes and escapes internal double quotes.
    """
    if val is None:
        return '""'
    s = str(val)
    if s and s[0] in ("=", "+", "-", "@", "\t", "\r"):
        s = "'" + s
    s = s.replace('"', '""')
    return f'"{s}"'


def export_pilot_session_json(session_data: dict[str, Any]) -> str:
    """Serializes pilot session data to formatted JSON."""
    return json.dumps(session_data, indent=2, ensure_ascii=False)


def export_pilot_tasks_csv(tasks_metrics: dict[str, dict[str, Any]], completed_tasks: dict[str, bool]) -> str:
    """Builds sanitized CSV table from pilot tasks and metrics."""
    rows = ["Gorev,Durum,Sure_sn,Hata,Tekrar"]
    for key, metric in tasks_metrics.items():
        name = sanitize_csv_cell(metric.get("name", key))
        status = sanitize_csv_cell("Tamamlandi" if completed_tasks.get(key) else "Bekliyor")
        duration = sanitize_csv_cell(f"{(metric.get('durationMs', 0) / 1000.0):.1f}")
        errors = sanitize_csv_cell(metric.get("errorCount", 0))
        retries = sanitize_csv_cell(metric.get("retryCount", 0))
        rows.append(f"{name},{status},{duration},{errors},{retries}")
    return "\n".join(rows) + "\n"
