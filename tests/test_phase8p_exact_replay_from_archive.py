import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from scripts.local_research.phase8p_replay_snapshot_schema import build_replay_snapshot
from scripts.phase8p_exact_replay_from_archive import build_readiness, run_replay_from_archive


def _ready_snapshot():
    return build_replay_snapshot(
        {
            "instrument": "EUR_USD",
            "session_bucket": "NY_OPEN_SECONDARY_PROPOSED",
            "side": "BUY",
            "entry": 1.1,
            "stop_loss": 1.099,
            "take_profit": 1.102,
            "score": 91,
        },
        news_snapshot={"ok": True, "data": {"items": [{"title": "EUR"}]}},
        news_assess_snapshot={"ok": True, "data": {"risk": "low"}},
        calendar_snapshot={"ok": True, "events": []},
        provider_status_snapshot={"ok": True, "providers": {"fixture": "ok"}},
        generated_at_utc="2026-01-01T00:00:00Z",
    )


def _write_jsonl(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True) + "\n")


class TestPhase8PExactReplayFromArchive(unittest.TestCase):
    def test_replay_loader_refuses_mutated_snapshot_hash(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            snap = _ready_snapshot()
            snap["entry"] = 1.2
            input_path = root / "archive.jsonl"
            _write_jsonl(input_path, [{"phase8p_replay_snapshot": snap, "future_bars": [{"h": 1.103, "l": 1.0995, "c": 1.102}]}])
            result = run_replay_from_archive(
                input_path=input_path,
                output_path=root / "out.json",
                readiness_path=root / "readiness.json",
                instrument="EUR_USD",
                session_bucket="NY_OPEN_SECONDARY_PROPOSED",
                limit=None,
                strict=True,
            )
        self.assertFalse(result["ok"])
        self.assertEqual(result["status_counts"]["REPLAY_REFUSED_INVALID_SNAPSHOT_HASH"], 1)

    def test_replay_loader_does_not_call_external_network(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            row = {
                "phase8p_replay_snapshot": _ready_snapshot(),
                "future_bars": [{"h": 1.103, "l": 1.0995, "c": 1.102}],
            }
            input_path = root / "archive.jsonl"
            _write_jsonl(input_path, [row])
            with patch("socket.create_connection", side_effect=AssertionError("network forbidden")):
                result = run_replay_from_archive(
                    input_path=input_path,
                    output_path=root / "out.json",
                    readiness_path=root / "readiness.json",
                    instrument="EUR_USD",
                    session_bucket="NY_OPEN_SECONDARY_PROPOSED",
                    limit=1,
                    strict=True,
                )
        self.assertTrue(result["ok"])
        self.assertEqual(result["status_counts"]["REPLAY_COMPLETE"], 1)

    def test_replay_loader_blocks_when_outcome_data_missing(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            input_path = root / "archive.jsonl"
            _write_jsonl(input_path, [{"phase8p_replay_snapshot": _ready_snapshot()}])
            result = run_replay_from_archive(
                input_path=input_path,
                output_path=root / "out.json",
                readiness_path=root / "readiness.json",
                instrument="EUR_USD",
                session_bucket="NY_OPEN_SECONDARY_PROPOSED",
                limit=None,
                strict=True,
            )
        self.assertTrue(result["ok"])
        self.assertEqual(result["status_counts"]["REPLAY_BLOCKED_MISSING_OUTCOME_DATA"], 1)

    def test_readiness_counts_missing_fields_and_ready_window(self):
        ready = _ready_snapshot()
        not_ready = build_replay_snapshot(
            {"instrument": "EUR_USD", "side": "BUY"},
            news_snapshot={},
            news_assess_snapshot={"ok": True},
            calendar_snapshot={},
            provider_status_snapshot={"ok": True},
            generated_at_utc="2026-01-02T00:00:00Z",
        )
        readiness = build_readiness(
            [{"phase8p_replay_snapshot": ready}, {"phase8p_replay_snapshot": not_ready}],
            generated_at_utc="2026-01-03T00:00:00Z",
        )
        self.assertEqual(readiness["replay_ready_exact_count"], 1)
        self.assertEqual(readiness["first_replay_ready_at_utc"], "2026-01-01T00:00:00Z")
        self.assertIn("entry", readiness["missing_fields_histogram"])
        self.assertIn("missing_required_fields", readiness["blocking_reasons"])


if __name__ == "__main__":
    unittest.main()
