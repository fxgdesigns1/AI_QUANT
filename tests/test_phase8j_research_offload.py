import json
import tarfile
import unittest
from pathlib import Path

from scripts.phase8j_verify_5950x_result_pack import verify_result_pack, VerificationError


def _write_json(p: Path, obj) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def _minimal_safe_summary() -> dict:
    return {
        "generated_at_utc": "2026-01-01T00:00:00Z",
        "phase": "Phase 8J",
        "classification": "RESEARCH_ONLY",
        "machine_role": "5950X",
        "instrument": "EUR_USD",
        "session_bucket": "NY",
        "session_window_utc": "13:30-16:00",
        "data_source": "oanda",
        "dataset_start_utc": "2025-01-01T00:00:00Z",
        "dataset_end_utc": "2025-06-30T00:00:00Z",
        "granularity": "M15",
        "lookback_days": 180,
        "candidate_source": "archived",
        "replay_mode": "best_available_proxy_reconstruction",
        "candidate_count": 1,
        "resolved_count": 1,
        "win_count": 10,
        "loss_count": 5,
        "breakeven_count": 0,
        "win_rate": 0.6667,
        "expectancy_r": 0.12,
        "profit_factor_r": 1.3,
        "max_loss_streak": 3,
        "drawdown_proxy_r": -1.0,
        "month_by_month_stats": [],
        "spread_slippage_assumptions": {"spread_pips": 1.0, "slippage_pips_per_side": 0.5, "pip_size": 0.0001},
        "news_reconstruction_available": False,
        "exact_replay_possible": True,
        "approximation_notes": "",
        "recommendation_label": "CONTINUE_FORWARD_PAPER_REVIEW",
        "paper_review_only": True,
        "live_permission": False,
        "ny_live_enabled": False,
        "send_trade_unlock_changed": False,
        "execution_paths_changed": False,
    }


def _minimal_safe_recommendation() -> dict:
    return {
        "generated_at_utc": "2026-01-01T00:00:00Z",
        "phase": "Phase 8J",
        "classification": "RESEARCH_ONLY",
        "recommendation_label": "CONTINUE_FORWARD_PAPER_REVIEW",
        "paper_review_only": True,
        "live_permission": False,
        "ny_live_enabled": False,
        "send_trade_unlock_changed": False,
        "execution_paths_changed": False,
    }


def _build_result_pack(tmp_path: Path, *, include_samples: bool = True) -> Path:
    root = tmp_path / "payload"
    root.mkdir(parents=True, exist_ok=True)
    _write_json(root / "phase8j_replay_summary.json", _minimal_safe_summary())
    _write_json(root / "phase8j_monthly_persistence.json", {"ok": True, "phase": "Phase 8J"})
    _write_json(root / "phase8j_recommendation.json", _minimal_safe_recommendation())
    _write_json(root / "phase8j_run_manifest.json", {"phase": "Phase 8J", "machine_role": "5950X"})
    if include_samples:
        (root / "phase8j_replay_samples_compact.jsonl").write_text("{}", encoding="utf-8")
    (root / "checksums.sha256").write_text("", encoding="utf-8")

    archive = tmp_path / "phase8j_5950x_result_pack.tar.gz"
    with tarfile.open(archive, mode="w:gz") as tf:
        for p in sorted(root.iterdir()):
            tf.add(p, arcname=p.name)
    return archive


class TestPhase8JResultPackVerifier(unittest.TestCase):
    def test_verify_accepts_minimal_safe_pack(self):
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as td:
            tmp_path = Path(td)
            archive = _build_result_pack(tmp_path, include_samples=False)
            res = verify_result_pack(archive)
            self.assertTrue(res.ok)
            self.assertGreater(res.pack_size_bytes, 0)

    def test_verify_rejects_live_permission_true(self):
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as td:
            tmp_path = Path(td)
            payload = tmp_path / "bad_payload"
            payload.mkdir(parents=True, exist_ok=True)
            bad = _minimal_safe_summary()
            bad["live_permission"] = True
            _write_json(payload / "phase8j_replay_summary.json", bad)
            _write_json(payload / "phase8j_monthly_persistence.json", {"ok": True, "phase": "Phase 8J"})
            _write_json(payload / "phase8j_recommendation.json", _minimal_safe_recommendation())
            _write_json(payload / "phase8j_run_manifest.json", {"phase": "Phase 8J", "machine_role": "5950X"})
            (payload / "checksums.sha256").write_text("", encoding="utf-8")
            bad_archive = tmp_path / "bad.tar.gz"
            with tarfile.open(bad_archive, mode="w:gz") as tf:
                for p in sorted(payload.iterdir()):
                    tf.add(p, arcname=p.name)

            with self.assertRaises(VerificationError):
                verify_result_pack(bad_archive)

    def test_verify_rejects_unexpected_file(self):
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as td:
            tmp_path = Path(td)
            payload = tmp_path / "payload2"
            payload.mkdir(parents=True, exist_ok=True)
            _write_json(payload / "phase8j_replay_summary.json", _minimal_safe_summary())
            _write_json(payload / "phase8j_monthly_persistence.json", {"ok": True, "phase": "Phase 8J"})
            _write_json(payload / "phase8j_recommendation.json", _minimal_safe_recommendation())
            _write_json(payload / "phase8j_run_manifest.json", {"phase": "Phase 8J", "machine_role": "5950X"})
            (payload / "checksums.sha256").write_text("", encoding="utf-8")
            (payload / "raw_dump.jsonl").write_text("x" * 10, encoding="utf-8")
            bad_archive = tmp_path / "unexpected.tar.gz"
            with tarfile.open(bad_archive, mode="w:gz") as tf:
                for p in sorted(payload.iterdir()):
                    tf.add(p, arcname=p.name)

            with self.assertRaises(VerificationError):
                verify_result_pack(bad_archive)


if __name__ == "__main__":
    unittest.main()

