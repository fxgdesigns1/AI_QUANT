import json
import unittest
from pathlib import Path

from scripts.phase8n_one_click_status import normalize_latest_import_manifest


class TestPhase8NOneClickFullResearchRun(unittest.TestCase):
    def test_one_click_ps1_has_no_unbraced_variable_colon_patterns(self):
        """
        PowerShell parses `$Var:` as a scoped/drive-qualified variable unless braced.
        This test enforces `${Var}:` whenever a variable is followed by ':'.
        """
        root = Path(__file__).resolve().parents[1]
        ps1 = root / "scripts" / "phase8n_one_click_full_research_run.ps1"
        text = ps1.read_text(encoding="utf-8")

        # Allowed special case: $env:XYZ is correct PowerShell syntax and should not be braced.
        import re

        hits = []
        for m in re.finditer(r"\$[A-Za-z_][A-Za-z0-9_]*:", text):
            if m.group(0).lower().startswith("$env:"):
                continue
            hits.append(m.group(0))
        self.assertEqual(hits, [], f"unbraced variable-colon patterns found: {hits}")

    def test_one_click_ps1_has_required_parameters_and_uses_gcloud(self):
        root = Path(__file__).resolve().parents[1]
        ps1 = root / "scripts" / "phase8n_one_click_full_research_run.ps1"
        text = ps1.read_text(encoding="utf-8")

        # Must accept parameters called out in spec.
        for name in (
            "Instrument",
            "Granularity",
            "LookbackDays",
            "SessionBucket",
            "SessionWindowUtc",
            "JobType",
            "MaxWaitMinutes",
            "PollSeconds",
            "WorkerCyclesMax",
        ):
            self.assertIn(f"${name}", text, f"missing parameter: {name}")

        # Must use gcloud compute ssh/scp (no raw ssh/scp).
        self.assertIn("gcloud", text.lower())
        self.assertIn("compute", text.lower())
        # Implementation may use token arrays: "compute", "ssh" / "compute", "scp".
        self.assertTrue(
            ("compute ssh" in text.lower()) or ('"compute", "ssh"' in text.lower()) or ("'compute', 'ssh'" in text.lower()),
            "missing gcloud compute ssh usage",
        )
        self.assertTrue(
            ("compute scp" in text.lower()) or ('"compute", "scp"' in text.lower()) or ("'compute', 'scp'" in text.lower()),
            "missing gcloud compute scp usage",
        )
        scrub = text.lower().replace("compute ssh", "").replace("compute scp", "")
        self.assertNotRegex(scrub, r"(^|\s)ssh(\s|$)")
        self.assertNotRegex(scrub, r"(^|\s)scp(\s|$)")

    def test_one_click_ps1_does_not_restart_runner_or_edit_runtime_config(self):
        root = Path(__file__).resolve().parents[1]
        ps1 = root / "scripts" / "phase8n_one_click_full_research_run.ps1"
        text = ps1.read_text(encoding="utf-8").lower()
        self.assertNotIn("ai-quant-runner", text)
        self.assertNotIn("runtime/config.yaml", text)
        self.assertNotIn("restart", text)

    def test_status_normalizer_fails_closed_on_safety_violation(self):
        bad = {
            "job_id": "job-x",
            "phase": "Phase 8M",
            "classification": "IMPORTED_RESEARCH_JOB_RESULT",
            "result_pack_size_bytes": 1,
            "paper_review_only": True,
            "live_permission": True,  # violation
            "ny_live_enabled": False,
            "send_trade_unlock_changed": False,
            "execution_paths_changed": False,
            "summary": {
                "generated_at_utc": "2026-01-01T00:00:00Z",
                "job_id": "job-x",
                "phase": "Phase 8M",
                "job_type": "phase8l_backtest",
                "classification": "RESEARCH_JOB_RESULT",
                "machine_role": "5950X",
                "instrument": "EUR_USD",
                "granularity": "M15",
                "lookback_days": 14,
                "session_bucket": "NY_OPEN_SECONDARY_PROPOSED",
                "session_window_utc": "13:30-16:00",
                "replay_mode": "best_available_proxy_reconstruction",
                "candidate_count": 1,
                "expectancy_r": 0.0,
                "profit_factor_r": 1.0,
                "max_loss_streak": 1,
                "drawdown_proxy_r": -1.0,
                "recommendation_label": "CONTINUE_FORWARD_PAPER_REVIEW",
                "paper_review_only": True,
                "live_permission": True,  # violation
                "ny_live_enabled": False,
                "send_trade_unlock_changed": False,
                "execution_paths_changed": False,
            },
        }
        with self.assertRaises(Exception):
            normalize_latest_import_manifest(bad)

    def test_status_normalizer_emits_expected_fields(self):
        safe = {
            "job_id": "job-ok",
            "phase": "Phase 8M",
            "classification": "IMPORTED_RESEARCH_JOB_RESULT",
            "result_pack_size_bytes": 123,
            "paper_review_only": True,
            "live_permission": False,
            "ny_live_enabled": False,
            "send_trade_unlock_changed": False,
            "execution_paths_changed": False,
            "summary": {
                "generated_at_utc": "2026-01-01T00:00:00Z",
                "job_id": "job-ok",
                "phase": "Phase 8M",
                "job_type": "phase8l_backtest",
                "classification": "RESEARCH_JOB_RESULT",
                "machine_role": "5950X",
                "instrument": "EUR_USD",
                "granularity": "M15",
                "lookback_days": 14,
                "session_bucket": "NY_OPEN_SECONDARY_PROPOSED",
                "session_window_utc": "13:30-16:00",
                "replay_mode": "best_available_proxy_reconstruction",
                "candidate_count": 3,
                "expectancy_r": 0.1,
                "profit_factor_r": 1.2,
                "max_loss_streak": 2,
                "drawdown_proxy_r": -0.5,
                "recommendation_label": "CONTINUE_FORWARD_PAPER_REVIEW",
                "paper_review_only": True,
                "live_permission": False,
                "ny_live_enabled": False,
                "send_trade_unlock_changed": False,
                "execution_paths_changed": False,
            },
        }
        out = normalize_latest_import_manifest(safe)
        self.assertTrue(out["ok"])
        for k in (
            "job_id",
            "replay_mode",
            "candidate_count",
            "expectancy_r",
            "profit_factor_r",
            "max_loss_streak",
            "drawdown_proxy_r",
            "recommendation_label",
            "ny_live_enabled",
            "send_trade_unlock_changed",
            "execution_paths_changed",
            "result_pack_size_bytes",
        ):
            self.assertIn(k, out)
        self.assertEqual(out["job_id"], "job-ok")


if __name__ == "__main__":
    unittest.main()

