import unittest
from pathlib import Path


class TestPhase8OOneClickExactReplay(unittest.TestCase):
    def test_one_click_uses_gcloud_compute_not_raw_ssh(self):
        src = Path("scripts/phase8o_one_click_exact_replay.ps1").read_text(encoding="utf-8")
        self.assertIn("gcloud compute ssh", src)
        self.assertIn("gcloud compute scp", src)
        self.assertNotIn("\nssh ", src)
        self.assertNotIn(" plink ", src.lower())

    def test_one_click_does_not_touch_forbidden_runtime_controls(self):
        src = Path("scripts/phase8o_one_click_exact_replay.ps1").read_text(encoding="utf-8").lower()
        self.assertNotIn("ai-quant-runner", src)
        self.assertNotIn("runtime/config.yaml", src)
        self.assertNotIn("send trade", src)
        self.assertNotIn("mt5 trade signal bridge", src)
        self.assertNotIn("lane 010", src)
        self.assertNotIn("lane 011", src)

    def test_one_click_prints_required_final_fields(self):
        src = Path("scripts/phase8o_one_click_exact_replay.ps1").read_text(encoding="utf-8")
        required = [
            "PHASE8O_EXACT_REPLAY_COMPLETE",
            "exact_strategy_replay=",
            "strategy_paths_found=",
            "news_reconstruction_available=",
            "calendar_reconstruction_available=",
            "candidate_count=",
            "expectancy_r=",
            "profit_factor_r=",
            "max_loss_streak=",
            "drawdown_proxy_r=",
            "recommendation_label=",
            "ny_live_enabled=false",
            "send_trade_unlock_changed=false",
            "execution_paths_changed=false",
            "MacBook pull commands:",
        ]
        for text in required:
            self.assertIn(text, src)


if __name__ == "__main__":
    unittest.main()
