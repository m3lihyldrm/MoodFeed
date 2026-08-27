"""Tests for Data Export and CSV Formula Injection Protection."""

import json
from pathlib import Path
from backend.export import export_pilot_session_json, export_pilot_tasks_csv, sanitize_csv_cell


def test_sanitize_csv_cell_formula_injection_defense():
    # 1. Formula prefixes must be neutralised with leading single quote
    assert sanitize_csv_cell("=1+1") == '"\'=1+1"'
    assert sanitize_csv_cell("+cmd|' /C calc'!A0") == '"\'+cmd|\' /C calc\'!A0"'
    assert sanitize_csv_cell("-2+3") == '"\'-2+3"'
    assert sanitize_csv_cell("@SUM(A1:A10)") == '"\'@SUM(A1:A10)"'
    assert sanitize_csv_cell("\tTAB_INJECT") == '"\'\tTAB_INJECT"'
    assert sanitize_csv_cell("\rCR_INJECT") == '"\'\rCR_INJECT"'

    # 2. Regular strings and numbers
    assert sanitize_csv_cell("Normal Text") == '"Normal Text"'
    assert sanitize_csv_cell(42) == '"42"'
    assert sanitize_csv_cell(75.5) == '"75.5"'
    assert sanitize_csv_cell(None) == '""'

    # 3. Quotes within string must be escaped
    assert sanitize_csv_cell('Hello "World"') == '"Hello ""World"""'


def test_json_export_structure():
    sample_data = {
        "report_type": "exploratory_prototype_feedback",
        "session_id": "pilot-test-123",
        "duration_seconds": 120,
        "tasks_completed": {"changeProfile": True, "fillSurvey": True},
        "sus_score": 82.5,
        "completed_at": 1740000000000,
    }
    json_out = export_pilot_session_json(sample_data)
    parsed = json.loads(json_out)
    assert parsed["session_id"] == "pilot-test-123"
    assert parsed["sus_score"] == 82.5
    assert parsed["tasks_completed"]["changeProfile"] is True


def test_csv_export_structure_and_sanitization():
    metrics = {
        "task1": {
            "name": "=HYPERLINK(\"http://evil.com\",\"Click\")",
            "durationMs": 2500,
            "errorCount": 0,
            "retryCount": 0,
        },
        "task2": {
            "name": "Profili Değiştir",
            "durationMs": 4100,
            "errorCount": 1,
            "retryCount": 0,
        },
    }
    completed = {"task1": True, "task2": True}

    csv_out = export_pilot_tasks_csv(metrics, completed)
    lines = csv_out.strip().split("\n")

    assert lines[0] == "Gorev,Durum,Sure_sn,Hata,Tekrar"
    # Verify injected formula is sanitized with single quote
    assert lines[1].startswith('"\'=HYPERLINK')
    assert '"Tamamlandi"' in lines[1]
    assert '"2.5"' in lines[1]
    assert '"Profili Değiştir"' in lines[2]


def test_frontend_contains_sanitize_csv_cell_and_formula_protection():
    html_path = Path("frontend/index.html")
    assert html_path.exists()
    content = html_path.read_text(encoding="utf-8")

    assert "function sanitizeCSVCell" in content
    assert "/^[=+\\-@\\t\\r]/" in content or "[=+\\-@\\t\\r]" in content
    assert "exportPilotJSON" in content
    assert "exportPilotCSV" in content
    assert "susScore" in content or "sus_score" in content
