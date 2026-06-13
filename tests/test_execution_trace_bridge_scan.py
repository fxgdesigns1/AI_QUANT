"""Tests for full-file bridge log scan (no tail-only, no stale gate)."""

import json
from pathlib import Path

from src.control_plane.execution_trace import (
    CANONICAL_BRIDGE_LOG_STR,
    scan_jsonl_for_signal_id,
)


def test_canonical_bridge_log_path_is_vm_absolute() -> None:
    assert CANONICAL_BRIDGE_LOG_STR == "/home/aiquant/gcloud-system/logs/ftmo_demo2_bridge_log.jsonl"


def test_scan_finds_signal_in_middle_of_file(tmp_path: Path) -> None:
    sid = "97afdeff-becb-4932-858d-6b28a9a0c871"
    log = tmp_path / "ftmo_demo2_bridge_log.jsonl"
    filler = {"type": "EA_START", "msg": "x", "signal_id": "", "ts": "2026.01.01 00:00:01"}
    hit = {"type": "EXECUTED", "msg": "ok", "signal_id": sid, "ts": "2026.01.02 00:00:02"}
    lines = []
    for i in range(50):
        row = dict(filler)
        row["msg"] = f"fill-{i}"
        lines.append(json.dumps(row))
    lines.append(json.dumps(hit))
    for i in range(50):
        row = dict(filler)
        row["msg"] = f"tail-{i}"
        lines.append(json.dumps(row))
    log.write_text("\n".join(lines) + "\n", encoding="utf-8")

    r = scan_jsonl_for_signal_id(log, sid)
    assert r["file_exists"] is True
    assert r["lines_scanned"] == 101
    assert r["signal_id_matched"] is True
    assert r["first_match_line_number"] == 51
    assert r["first_match_event_type"] == "EXECUTED"
    # Timestamp taken from the last non-empty line that exposes a ts (tail filler rows).
    assert r["last_line_timestamp"] == "2026.01.01 00:00:01"
