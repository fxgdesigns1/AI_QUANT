import hashlib
import json
import tarfile
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.phase8m_contract import (
    ContractError,
    build_job,
    job_file_for,
    validate_job,
    verify_research_result_pack,
    write_json,
)
from scripts.phase8m_create_research_job import create_job
from scripts.phase8m_import_research_result import import_research_result
from scripts.phase8m_list_research_jobs import list_research_jobs


def _safe_summary(job_id: str = "job-1") -> dict:
    return {
        "generated_at_utc": "2026-01-01T00:00:00Z",
        "job_id": job_id,
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
        "max_loss_streak": 1,
        "drawdown_proxy_r": -0.5,
        "recommendation_label": "CONTINUE_FORWARD_PAPER_REVIEW",
        "paper_review_only": True,
        "live_permission": False,
        "ny_live_enabled": False,
        "send_trade_unlock_changed": False,
        "execution_paths_changed": False,
    }


def _safe_recommendation(job_id: str = "job-1") -> dict:
    return {
        "generated_at_utc": "2026-01-01T00:00:00Z",
        "phase": "Phase 8M",
        "job_id": job_id,
        "job_type": "phase8l_backtest",
        "classification": "RESEARCH_JOB_RESULT",
        "recommendation_label": "CONTINUE_FORWARD_PAPER_REVIEW",
        "paper_review_only": True,
        "live_permission": False,
        "ny_live_enabled": False,
        "send_trade_unlock_changed": False,
        "execution_paths_changed": False,
    }


def _build_result_pack(root: Path, *, job_id: str = "job-1", live_permission: bool = False, forbidden: bool = False) -> Path:
    payload = root / "payload"
    payload.mkdir(parents=True, exist_ok=True)
    summary = _safe_summary(job_id)
    summary["live_permission"] = live_permission
    files = {
        "backtest_summary.json": summary,
        "recommendation.json": _safe_recommendation(job_id),
        "monthly_persistence.json": {"months": []},
        "daily_persistence.json": {"daily": []},
        "research_job_result_manifest.json": {
            "phase": "Phase 8M",
            "job_id": job_id,
            "paper_review_only": True,
            "live_permission": False,
            "ny_live_enabled": False,
            "send_trade_unlock_changed": False,
            "execution_paths_changed": False,
        },
    }
    for name, obj in files.items():
        (payload / name).write_text(json.dumps(obj), encoding="utf-8")
    (payload / "replay_samples_compact.jsonl").write_text("{}\n", encoding="utf-8")
    lines = []
    for p in sorted(payload.iterdir()):
        if p.name == "checksums.sha256":
            continue
        h = hashlib.sha256()
        h.update(p.read_bytes())
        lines.append(f"{h.hexdigest()}  {p.name}")
    (payload / "checksums.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
    if forbidden:
        (payload / ".env").write_text("SHOULD_NOT_EXIST", encoding="utf-8")
    archive = root / "research_job_result_pack.tar.gz"
    with tarfile.open(archive, mode="w:gz") as tf:
        for p in sorted(payload.iterdir()):
            tf.add(p, arcname=p.name)
    return archive


class TestPhase8MResearchJobs(unittest.TestCase):
    def test_job_creation_writes_valid_pending_job(self):
        with TemporaryDirectory() as td:
            root = Path(td) / "jobs"
            res = create_job(
                job_root=root,
                job_type="phase8l_backtest",
                instrument="EUR_USD",
                granularity="M15",
                lookback_days=14,
                session_bucket="NY_OPEN_SECONDARY_PROPOSED",
                session_window_utc="13:30-16:00",
                requested_by="test",
            )
            self.assertTrue(res["ok"])
            p = Path(res["job_path"])
            self.assertTrue(p.is_file())
            job = json.loads(p.read_text(encoding="utf-8"))
            validate_job(job)
            self.assertFalse(job["safety"]["live_permission"])

    def test_invalid_live_permission_job_rejected(self):
        job = build_job(job_type="phase8l_backtest")
        job["safety"]["live_permission"] = True
        with self.assertRaises(ContractError):
            validate_job(job)

    def test_list_jobs_reads_all_queues(self):
        with TemporaryDirectory() as td:
            root = Path(td) / "jobs"
            job = build_job(job_type="phase8l_backtest", job_id="job-list-test")
            write_json(job_file_for(root, "PENDING", job["job_id"]), job)
            res = list_research_jobs(job_root=root, latest_result_pointer=Path(td) / "missing.json")
            self.assertEqual(res["counts"]["pending"], 1)
            self.assertEqual(res["jobs"]["pending"][0]["job_id"], "job-list-test")

    def test_result_pack_verifier_accepts_safe_pack(self):
        with TemporaryDirectory() as td:
            pack = _build_result_pack(Path(td))
            res = verify_research_result_pack(pack)
            self.assertTrue(res.ok)
            self.assertEqual(res.job_id, "job-1")

    def test_result_pack_verifier_rejects_forbidden_path(self):
        with TemporaryDirectory() as td:
            pack = _build_result_pack(Path(td), forbidden=True)
            with self.assertRaises(ContractError):
                verify_research_result_pack(pack)

    def test_result_pack_verifier_rejects_live_permission(self):
        with TemporaryDirectory() as td:
            pack = _build_result_pack(Path(td), live_permission=True)
            with self.assertRaises(ContractError):
                verify_research_result_pack(pack)

    def test_importer_writes_latest_result_pointer(self):
        with TemporaryDirectory() as td:
            td_path = Path(td)
            job_root = td_path / "jobs"
            job = build_job(job_type="phase8l_backtest", job_id="job-import-test")
            job["status"] = "RUNNING"
            write_json(job_file_for(job_root, "RUNNING", job["job_id"]), job)
            pack = _build_result_pack(td_path, job_id=job["job_id"])
            latest = td_path / "latest_research_job_result.json"
            res = import_research_result(
                archive=pack,
                job_root=job_root,
                import_root=td_path / "imports",
                latest_pointer=latest,
            )
            self.assertTrue(res["ok"])
            self.assertTrue(latest.is_file())
            latest_obj = json.loads(latest.read_text(encoding="utf-8"))
            self.assertEqual(latest_obj["job_id"], "job-import-test")
            self.assertTrue(job_file_for(job_root, "DONE", job["job_id"]).is_file())


if __name__ == "__main__":
    unittest.main()

