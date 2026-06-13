"""Phase 8X batch progress JSON (ALPHA queue snapshot + worker cycle merge)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.phase8x_write_batch_progress import (
    build_progress_document,
    counts_from_alpha_list,
    parse_last_worker,
    write_progress,
)


class TestPhase8XBatchProgress(unittest.TestCase):
    def test_counts_from_alpha_list(self):
        c = counts_from_alpha_list({"ok": True, "counts": {"pending": 2, "running": 1, "done": 5, "failed": 0}})
        self.assertEqual(c, {"pending": 2, "running": 1, "done": 5, "failed": 0})

    def test_build_progress_document_totals(self):
        alpha = {"ok": True, "counts": {"pending": 10, "running": 0, "done": 40, "failed": 0}, "job_root": "/opt/ai-quant/ARTIFACTS/research_jobs"}
        doc = build_progress_document(
            alpha_list=alpha,
            last_worker={"ok": True, "job_id": "job_a"},
            stop_reason="RUNNING",
            previous=None,
        )
        self.assertEqual(doc["total"], 50)
        self.assertEqual(doc["percent_complete"], 80.0)
        self.assertEqual(doc["current_job_id"], "job_a")
        self.assertEqual(doc["last_result_job_id"], "job_a")

    def test_write_progress_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            alpha_path = root / "alpha.json"
            alpha_path.write_text(
                json.dumps({"ok": True, "counts": {"pending": 1, "running": 0, "done": 0, "failed": 0}}),
                encoding="utf-8",
            )
            out = root / "ARTIFACTS" / "performance" / "latest_phase8x_batch_progress.json"
            r = write_progress(
                repo_root=root,
                alpha_list_json=alpha_path,
                last_worker_json='{"ok":true,"job_id":"x1"}',
                stop_reason="RUNNING",
                output_path=out,
            )
            self.assertTrue(r["ok"])
            data = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(data["pending"], 1)
            self.assertEqual(data["stop_reason"], "RUNNING")
            self.assertFalse(out.read_bytes().startswith(b"\xef\xbb\xbf"), "progress JSON must not start with UTF-8 BOM")

    def test_write_progress_reads_bom_prefixed_alpha_and_previous(self):
        """Simulates PowerShell/Windows JSON saved with UTF-8 BOM."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            alpha_path = root / "alpha_bom.json"
            body = json.dumps({"ok": True, "counts": {"pending": 3, "running": 0, "done": 0, "failed": 0}})
            alpha_path.write_bytes(b"\xef\xbb\xbf" + body.encode("utf-8"))

            out = root / "progress.json"
            out.write_bytes(
                b"\xef\xbb\xbf"
                + json.dumps(
                    {"ok": True, "started_at_utc": "2020-01-01T00:00:00Z", "current_job_id": "old"}
                ).encode("utf-8")
            )

            r = write_progress(
                repo_root=root,
                alpha_list_json=alpha_path,
                last_worker_json=None,
                stop_reason="RUNNING",
                output_path=out,
            )
            self.assertTrue(r["ok"])
            self.assertEqual(r["progress"]["pending"], 3)
            raw = out.read_bytes()
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            data = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(data["pending"], 3)

    def test_parse_last_worker_inline_with_bom(self):
        doc = parse_last_worker('\ufeff{"ok":true,"job_id":"b1"}')
        self.assertEqual(doc, {"ok": True, "job_id": "b1"})


if __name__ == "__main__":
    unittest.main()
