import json
import unittest

from scripts.local_research.phase8p_replay_snapshot_schema import (
    build_replay_snapshot,
    compute_snapshot_hash,
    redact_secrets,
    validate_snapshot_hash,
)


class TestPhase8PReplaySnapshotSchema(unittest.TestCase):
    def test_canonical_hash_is_stable_for_key_order(self):
        row = {
            "instrument": "EUR_USD",
            "session_bucket": "NY_OPEN_SECONDARY_PROPOSED",
            "side": "BUY",
            "entry": 1.1,
            "stop_loss": 1.099,
            "take_profit": 1.102,
            "score": 91,
        }
        context = {"ok": True, "data": {"b": 2, "a": 1}}
        snap1 = build_replay_snapshot(
            row,
            news_snapshot=context,
            news_assess_snapshot={"data": {"a": 1, "b": 2}, "ok": True},
            calendar_snapshot={"ok": True, "rows": [1]},
            provider_status_snapshot={"ok": True, "providers": {"x": "ok"}},
            generated_at_utc="2026-01-01T00:00:00Z",
        )
        snap2 = build_replay_snapshot(
            dict(reversed(list(row.items()))),
            news_snapshot={"data": {"a": 1, "b": 2}, "ok": True},
            news_assess_snapshot={"ok": True, "data": {"b": 2, "a": 1}},
            calendar_snapshot={"rows": [1], "ok": True},
            provider_status_snapshot={"providers": {"x": "ok"}, "ok": True},
            generated_at_utc="2026-01-01T00:00:00Z",
        )
        self.assertEqual(snap1["snapshot_hash"], snap2["snapshot_hash"])
        self.assertTrue(validate_snapshot_hash(snap1))

    def test_redacts_secrets_from_provider_payloads(self):
        payload = {
            "ok": True,
            "headers": {"Authorization": "Bearer secret-token"},
            "data": {"api_key": "secret-key", "headline": "EUR update"},
        }
        redacted = redact_secrets(payload)
        dumped = json.dumps(redacted)
        self.assertNotIn("secret-token", dumped)
        self.assertNotIn("secret-key", dumped)
        self.assertIn("EUR update", dumped)

    def test_replay_ready_false_when_trade_or_context_fields_missing(self):
        snap = build_replay_snapshot(
            {"instrument": "EUR_USD", "side": "BUY"},
            news_snapshot={},
            news_assess_snapshot={"ok": True},
            calendar_snapshot={},
            provider_status_snapshot={"ok": True},
            generated_at_utc="2026-01-01T00:00:00Z",
        )
        self.assertFalse(snap["replay_ready_exact"])
        self.assertIn("entry", snap["missing_fields"])
        self.assertIn("stop_loss", snap["missing_fields"])
        self.assertIn("take_profit", snap["missing_fields"])
        self.assertIn("news_snapshot", snap["missing_fields"])
        self.assertIn("calendar_snapshot", snap["missing_fields"])

    def test_hash_validation_detects_mutation(self):
        snap = build_replay_snapshot(
            {
                "instrument": "EUR_USD",
                "session_bucket": "NY_OPEN_SECONDARY_PROPOSED",
                "side": "BUY",
                "entry": 1.1,
                "stop_loss": 1.099,
                "take_profit": 1.102,
            },
            news_snapshot={"ok": True},
            news_assess_snapshot={"ok": True},
            calendar_snapshot={"ok": True},
            provider_status_snapshot={"ok": True},
            generated_at_utc="2026-01-01T00:00:00Z",
        )
        self.assertEqual(snap["snapshot_hash"], compute_snapshot_hash(snap))
        snap["entry"] = 1.2
        self.assertFalse(validate_snapshot_hash(snap))


if __name__ == "__main__":
    unittest.main()
