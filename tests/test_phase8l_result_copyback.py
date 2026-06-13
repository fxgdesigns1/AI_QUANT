import json
import tarfile
import unittest
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Dict, Optional

from scripts.phase8l_verify_result_pack import VerificationError, verify_result_pack


def _minimal_summary() -> dict:
    return {
        "generated_at_utc": "2026-01-01T00:00:00Z",
        "phase": "Phase 8L",
        "classification": "RESEARCH_ONLY",
        "machine_role": "5950X",
        "dataset_start_utc": "2025-01-01T00:00:00Z",
        "dataset_end_utc": "2025-06-30T00:00:00Z",
        "instruments": ["EUR_USD"],
        "granularities": ["M15"],
        "session_window_utc": "13:30-16:00",
        "replay_mode": "best_available_proxy_reconstruction",
        "candidate_count": 5,
        "resolved_count": 5,
        "win_count": 2,
        "loss_count": 2,
        "breakeven_count": 1,
        "win_rate": 0.4,
        "expectancy_r": 0.05,
        "profit_factor_r": 1.1,
        "max_loss_streak": 1,
        "drawdown_proxy_r": -0.5,
        "news_reconstruction_available": False,
        "calendar_reconstruction_available": False,
        "recommendation_label": "CONTINUE_FORWARD_PAPER_REVIEW",
        "paper_review_only": True,
        "live_permission": False,
        "ny_live_enabled": False,
        "send_trade_unlock_changed": False,
        "execution_paths_changed": False,
    }


def _minimal_rec() -> dict:
    return {
        "generated_at_utc": "2026-01-01T00:00:00Z",
        "phase": "Phase 8L",
        "classification": "RESEARCH_ONLY",
        "recommendation_label": "CONTINUE_FORWARD_PAPER_REVIEW",
        "paper_review_only": True,
        "live_permission": False,
        "ny_live_enabled": False,
        "send_trade_unlock_changed": False,
        "execution_paths_changed": False,
    }


def _build_pack(tmp: Path, *, summary: Optional[Dict[str, Any]] = None) -> Path:
    root = tmp / "payload"
    root.mkdir(parents=True, exist_ok=True)
    s = summary if summary is not None else _minimal_summary()
    (root / "phase8l_backtest_summary.json").write_text(json.dumps(s), encoding="utf-8")
    (root / "phase8l_monthly_persistence.json").write_text(json.dumps({"months": []}), encoding="utf-8")
    (root / "phase8l_daily_persistence.json").write_text(json.dumps({"daily": []}), encoding="utf-8")
    (root / "phase8l_recommendation.json").write_text(json.dumps(_minimal_rec()), encoding="utf-8")
    (root / "phase8l_run_manifest.json").write_text(json.dumps({"phase": "Phase 8L"}), encoding="utf-8")
    (root / "phase8l_replay_samples_compact.jsonl").write_text('{"x":1}\n', encoding="utf-8")
    lines = []
    for name in sorted(
        [
            "phase8l_backtest_summary.json",
            "phase8l_monthly_persistence.json",
            "phase8l_daily_persistence.json",
            "phase8l_recommendation.json",
            "phase8l_run_manifest.json",
            "phase8l_replay_samples_compact.jsonl",
        ]
    ):
        h = hashlib.sha256()
        h.update((root / name).read_bytes())
        lines.append(f"{h.hexdigest()}  {name}")
    (root / "checksums.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")

    arc = tmp / "phase8l_result_pack.tar.gz"
    with tarfile.open(arc, mode="w:gz") as tf:
        for p in sorted(root.iterdir()):
            tf.add(p, arcname=p.name)
    return arc


class TestPhase8LResultCopyback(unittest.TestCase):
    def test_verifier_accepts_valid_pack(self):
        with TemporaryDirectory() as td:
            p = _build_pack(Path(td))
            res = verify_result_pack(p)
            self.assertTrue(res.ok)

    def test_verifier_rejects_oversize(self):
        with TemporaryDirectory() as td:
            p = _build_pack(Path(td))
            with self.assertRaises(VerificationError):
                verify_result_pack(p, max_size_mb=0)

    def test_verifier_rejects_forbidden_path(self):
        with TemporaryDirectory() as td:
            root = Path(td) / "bad"
            root.mkdir()
            (root / ".env").write_text("x", encoding="utf-8")
            arc = Path(td) / "bad.tar.gz"
            with tarfile.open(arc, mode="w:gz") as tf:
                tf.add(root / ".env", arcname=".env")
            with self.assertRaises(VerificationError):
                verify_result_pack(arc)

    def test_verifier_rejects_live_permission(self):
        with TemporaryDirectory() as td:
            s = _minimal_summary()
            s["live_permission"] = True
            p = _build_pack(Path(td), summary=s)
            with self.assertRaises(VerificationError):
                verify_result_pack(p)

    def test_importer_emits_macbook_pull_commands_helper(self):
        from scripts.phase8l_import_result_pack_to_alpha import _macbook_pull_commands

        cmds = _macbook_pull_commands()
        self.assertTrue(any("latest_phase8l_backtest_summary.json" in c for c in cmds))


if __name__ == "__main__":
    unittest.main()
