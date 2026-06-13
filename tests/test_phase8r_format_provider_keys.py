import json
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.phase8r_format_provider_keys import (
    CANONICAL_TARGETS,
    build_env_lines,
    discover_candidates,
    ingest_kv_into,
    parse_file,
    pick_best_candidate,
    run_format,
)


class TestPhase8RFormatProviderKeys(unittest.TestCase):
    def test_alias_maps_news_to_plural_bucket(self):
        b = {c: [] for c in CANONICAL_TARGETS}
        ingest_kv_into(b, "NEWS_API_KEY", "fake_news_only")
        ingest_kv_into(b, "NEWSAPI_API_KEY", "fake_news_two")
        lines = build_env_lines(b)
        self.assertEqual(len(lines), 1)
        self.assertTrue(lines[0].startswith("NEWSAPI_API_KEYS="))
        self.assertIn("fake_news_only", lines[0])
        self.assertIn("fake_news_two", lines[0])

    def test_csv_merge_and_dedupe(self):
        b = {c: [] for c in CANONICAL_TARGETS}
        ingest_kv_into(b, "NEWSAPI_API_KEYS", "a,b,a")
        lines = build_env_lines(b)
        self.assertEqual(lines, ["NEWSAPI_API_KEYS=a,b"])

    def test_parse_json_nested_last_segment(self):
        b = {c: [] for c in CANONICAL_TARGETS}
        p = Path(tempfile.mkdtemp()) / "x.json"
        try:
            p.write_text(
                json.dumps({"nested": {"NEWSAPI_API_KEY": "fake_from_json"}}),
                encoding="utf-8",
            )
            parse_file(p, b)
            self.assertIn("fake_from_json", b["NEWSAPI_API_KEYS"])
        finally:
            shutil.rmtree(p.parent, ignore_errors=True)

    def test_backup_then_overwrite(self):
        repo = Path(tempfile.mkdtemp())
        try:
            out = repo / ".secrets"
            out.mkdir(parents=True)
            target = out / "phase8r_providers.env"
            target.write_text("NEWSAPI_API_KEYS=old_fake\n", encoding="utf-8")
            src = repo / "keys.env"
            src.write_text("NEWSAPI_API_KEY=new_fake\n", encoding="utf-8")
            code, meta = run_format(
                repo_root=repo,
                source_file=src,
                auto_detect=False,
                output_path=target,
                write_report=False,
                artifacts_dir=repo / "artifacts",
            )
            self.assertEqual(code, 0)
            self.assertTrue(meta.get("env_file_written"))
            backs = list(out.glob("phase8r_providers.env.*.bak"))
            self.assertEqual(len(backs), 1)
            txt = target.read_text(encoding="utf-8")
            self.assertIn("new_fake", txt)
            self.assertNotIn("old_fake", txt)
        finally:
            shutil.rmtree(repo, ignore_errors=True)

    def test_run_format_no_keys_exit(self):
        repo = Path(tempfile.mkdtemp())
        try:
            src = repo / "empty.env"
            src.write_text("# nothing\n", encoding="utf-8")
            code, _meta = run_format(
                repo_root=repo,
                source_file=src,
                auto_detect=False,
                output_path=repo / ".secrets" / "phase8r_providers.env",
                write_report=False,
                artifacts_dir=repo / "artifacts",
            )
            self.assertEqual(code, 3)
        finally:
            shutil.rmtree(repo, ignore_errors=True)

    def test_pick_best_prefers_api_key_filename(self):
        d = Path(tempfile.mkdtemp())
        try:
            low = d / "readme.md"
            low.write_text("x", encoding="utf-8")
            high = d / "my_api_keys.txt"
            high.write_text("y", encoding="utf-8")
            picked = pick_best_candidate([low, high])
            self.assertEqual(picked.name, "my_api_keys.txt")
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_discover_respects_skip_phase8r_output_name(self):
        repo = Path(tempfile.mkdtemp())
        try:
            sec = repo / ".secrets"
            sec.mkdir(parents=True)
            keep = sec / "credentials.env"
            keep.write_text("NEWSAPI_API_KEY=x\n", encoding="utf-8")
            skip = sec / "phase8r_providers.env"
            skip.write_text("NEWSAPI_API_KEY=z\n", encoding="utf-8")
            cands = discover_candidates(repo)
            names = {p.name for p in cands}
            self.assertIn("credentials.env", names)
            self.assertNotIn("phase8r_providers.env", names)
        finally:
            shutil.rmtree(repo, ignore_errors=True)

    def test_report_json_contains_no_raw_secret_lengths_only_counts(self):
        repo = Path(tempfile.mkdtemp())
        try:
            art = repo / "artifacts"
            src = repo / "in.env"
            src.write_text("NEWSAPI_API_KEY=secret_token_xyz\n", encoding="utf-8")
            code, _ = run_format(
                repo_root=repo,
                source_file=src,
                auto_detect=False,
                output_path=repo / ".secrets" / "phase8r_providers.env",
                write_report=True,
                artifacts_dir=art,
            )
            self.assertEqual(code, 0)
            rep = json.loads((art / "PHASE8R_KEY_FORMAT_REPORT_LATEST.json").read_text(encoding="utf-8"))
            blob = json.dumps(rep)
            self.assertNotIn("secret_token_xyz", blob)
            self.assertFalse(rep.get("secrets_printed"))
            self.assertGreater(rep["key_counts_by_provider"].get("newsapi", 0), 0)
        finally:
            shutil.rmtree(repo, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
