import unittest
from pathlib import Path

from scripts.phase8m_5950x_research_worker import (
    gcloud_scp,
    gcloud_ssh,
    remote_claim_job_command,
    run_once,
)


class TestPhase8MWorkerContract(unittest.TestCase):
    def test_worker_dry_run_does_not_touch_alpha(self):
        res = run_once(
            project="fxg-ai-trading",
            zone="us-central1-a",
            vm="fxg-paper-e2-small-main-2026",
            alpha_repo="/opt/ai-quant",
            local_root=Path("C:/tmp/phase8m_dry_run"),
            dry_run=True,
        )
        self.assertTrue(res["dry_run"])
        cmd = res["would_list_jobs"]["command"]
        self.assertIn("compute ssh", cmd)
        self.assertRegex(cmd.lower(), r"gcloud|cloud sdk")

    def test_worker_helpers_use_gcloud_compute_not_raw_ssh(self):
        ssh_cmd = gcloud_ssh(
            project="p",
            zone="z",
            vm="vm",
            command="echo ok",
            dry_run=True,
        )
        scp_cmd = gcloud_scp(
            project="p",
            zone="z",
            source="a",
            dest="b",
            dry_run=True,
        )
        self.assertIn("compute ssh", ssh_cmd)
        self.assertIn("compute scp", scp_cmd)
        self.assertRegex(ssh_cmd.lower(), r"gcloud|cloud sdk")
        self.assertRegex(scp_cmd.lower(), r"gcloud|cloud sdk")

    def test_remote_claim_command_uses_queue_not_execution(self):
        cmd = remote_claim_job_command("/opt/ai-quant", "job-1")
        self.assertIn("phase8m_contract", cmd)
        self.assertNotIn("order", cmd.lower())
        self.assertNotIn("trade_signal", cmd.lower())

    def test_phase8m_scripts_do_not_restart_runner_or_edit_runtime_config(self):
        root = Path(__file__).resolve().parents[1]
        for p in (root / "scripts").glob("phase8m*"):
            if not p.is_file():
                continue
            text = p.read_text(encoding="utf-8")
            self.assertNotIn("ai-quant-runner", text.lower(), p.name)
            self.assertNotIn("runtime/config.yaml", text, p.name)

    def test_prepare_data_script_has_no_execution_order_imports(self):
        root = Path(__file__).resolve().parents[1]
        text = (root / "scripts" / "phase8m_prepare_job_data_export.py").read_text(encoding="utf-8")
        self.assertNotIn("import v20", text)
        self.assertNotIn("from v20", text)
        self.assertNotIn("order_manager", text)
        self.assertNotIn("src.core.execution", text)


if __name__ == "__main__":
    unittest.main()

