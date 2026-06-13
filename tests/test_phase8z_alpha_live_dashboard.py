"""Phase 8Z: ALPHA-hosted Stitch dashboard routes and read-only batch progress API."""

from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from pathlib import Path

import httpx
from httpx import ASGITransport


class TestPhase8ZAlphaLiveDashboard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from src.control_plane import api as api_mod

        cls.api_mod = api_mod

    async def _aget(self, path: str, *, follow_redirects: bool = True):
        transport = ASGITransport(app=self.api_mod.app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test", follow_redirects=follow_redirects
        ) as ac:
            return await ac.get(path)

    def test_batch_progress_endpoint_returns_truth_wrap_and_safety_flags(self):
        r = asyncio.run(self._aget("/api/phase8/batch-progress"))
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertIn("data", body)
        self.assertIn("truth", body)
        data = body["data"]
        self.assertTrue(data.get("ok"))
        for k in (
            "pending",
            "running",
            "done",
            "failed",
            "total",
            "percent_complete",
            "paper_review_only",
            "live_permission",
            "ny_live_enabled",
            "send_trade_unlock_changed",
            "execution_paths_changed",
        ):
            self.assertIn(k, data, msg=f"missing {k}")
        self.assertIs(data.get("paper_review_only"), True)
        self.assertIs(data.get("ny_live_enabled"), False)

    def test_research_dashboard_endpoint_json(self):
        r = asyncio.run(self._aget("/api/phase8/research-dashboard"))
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertIn("data", body)

    def test_phase8_dashboard_routes(self):
        r0 = asyncio.run(self._aget("/phase8/dashboard", follow_redirects=False))
        self.assertIn(r0.status_code, (307, 308))

        r = asyncio.run(self._aget("/phase8/dashboard/"))
        if r.status_code == 404:
            self.skipTest("phase8 static dashboard dir missing in this workspace checkout")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"Phase 8", r.content)

        rjs = asyncio.run(self._aget("/phase8/dashboard/app.js"))
        self.assertEqual(rjs.status_code, 200)

    def test_build_phase8_batch_progress_payload_counts_disk(self):
        """Direct queue JSON counts override optional progress file."""
        api_mod = self.api_mod
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pending_d = root / "ARTIFACTS" / "research_jobs" / "queue" / "pending"
            running_d = root / "ARTIFACTS" / "research_jobs" / "queue" / "running"
            done_d = root / "ARTIFACTS" / "research_jobs" / "queue" / "done"
            failed_d = root / "ARTIFACTS" / "research_jobs" / "queue" / "failed"
            for d in (pending_d, running_d, done_d, failed_d):
                d.mkdir(parents=True, exist_ok=True)
            (pending_d / "a.json").write_text('{"job_id":"a","status":"PENDING"}', encoding="utf-8")
            (done_d / "b.json").write_text('{"job_id":"b","status":"DONE"}', encoding="utf-8")
            progress = root / "ARTIFACTS" / "performance" / "latest_phase8x_batch_progress.json"
            progress.parent.mkdir(parents=True, exist_ok=True)
            progress.write_text(
                json.dumps(
                    {
                        "pending": 99,
                        "running": 0,
                        "done": 0,
                        "failed": 0,
                        "current_job_id": "from_file",
                    }
                ),
                encoding="utf-8",
            )
            out = api_mod.build_phase8_batch_progress_payload(root)
            self.assertEqual(out["pending"], 1, "disk count must win over progress file")
            self.assertEqual(out["done"], 1)
            self.assertEqual(out["current_job_id"], "from_file")

    def test_unwrap_href_in_index_uses_trailing_slash_routes(self):
        """index is served at /phase8/dashboard/ so relative app.js resolves to /phase8/dashboard/app.js."""
        idx = Path(__file__).resolve().parents[1] / "dashboard" / "phase8_stitch_dashboard" / "index.html"
        if not idx.is_file():
            self.skipTest("missing index.html")
        text = idx.read_text(encoding="utf-8")
        self.assertIn('src="app.js"', text)


if __name__ == "__main__":
    unittest.main()
