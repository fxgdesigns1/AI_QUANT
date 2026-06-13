#!/usr/bin/env python3
"""
Phase 8R: normalize operator API key material into .secrets/phase8r_providers.env.

Never prints secret values. Never logs raw keys. Output uses canonical plural *_API_KEYS only.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Set, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]

UTC = timezone.utc

PHASE = "Phase 8R-KEY-FORMAT"

# Values merge into these canonical env names (CSV, no spaces after commas).
CANONICAL_TARGETS: Tuple[str, ...] = (
    "NEWSAPI_API_KEYS",
    "TRADINGECONOMICS_API_KEYS",
    "FINNHUB_API_KEYS",
    "MARKETAUX_API_KEYS",
    "POLYGON_API_KEYS",
    "ALPHAVANTAGE_API_KEYS",
    "FRED_API_KEYS",
    "FMP_API_KEYS",
)

# Source alias (normalized UPPER_WITH_UNDERSCORES) -> canonical bucket.
ALIAS_TO_CANONICAL: Dict[str, str] = {}
for canonical in CANONICAL_TARGETS:
    ALIAS_TO_CANONICAL[canonical] = canonical

_news = (
    "NEWSAPI_API_KEYS",
    "NEWSAPI_API_KEY",
    "NEWS_API_KEY",
    "NEWSAPI_KEY",
)
_te = (
    "TRADINGECONOMICS_API_KEYS",
    "TRADINGECONOMICS_API_KEY",
    "TRADING_ECONOMICS_KEY",
    "TRADINGECONOMICS_KEY",
    "TE_API_KEY",
    "TRADING_ECONOMICS_CLIENT",
)
_finnhub = ("FINNHUB_API_KEYS", "FINNHUB_API_KEY", "FINNHUB_KEY")
_marketaux = ("MARKETAUX_API_KEYS", "MARKETAUX_API_KEY", "MARKETAUX_KEY", "MARKETAUX_KEYS")
_polygon = ("POLYGON_API_KEYS", "POLYGON_API_KEY", "POLYGON_KEY")
_av = ("ALPHAVANTAGE_API_KEYS", "ALPHAVANTAGE_API_KEY", "ALPHA_VANTAGE_API_KEY")
_fred = ("FRED_API_KEYS", "FRED_API_KEY")
_fmp = ("FMP_API_KEYS", "FMP_API_KEY", "FINANCIAL_MODELING_PREP_API_KEY")

for a in _news:
    ALIAS_TO_CANONICAL[a] = "NEWSAPI_API_KEYS"
for a in _te:
    ALIAS_TO_CANONICAL[a] = "TRADINGECONOMICS_API_KEYS"
for a in _finnhub:
    ALIAS_TO_CANONICAL[a] = "FINNHUB_API_KEYS"
for a in _marketaux:
    ALIAS_TO_CANONICAL[a] = "MARKETAUX_API_KEYS"
for a in _polygon:
    ALIAS_TO_CANONICAL[a] = "POLYGON_API_KEYS"
for a in _av:
    ALIAS_TO_CANONICAL[a] = "ALPHAVANTAGE_API_KEYS"
for a in _fred:
    ALIAS_TO_CANONICAL[a] = "FRED_API_KEYS"
for a in _fmp:
    ALIAS_TO_CANONICAL[a] = "FMP_API_KEYS"

PROVIDER_SLUG_BY_CANONICAL = {
    "NEWSAPI_API_KEYS": "newsapi",
    "TRADINGECONOMICS_API_KEYS": "tradingeconomics",
    "FINNHUB_API_KEYS": "finnhub",
    "MARKETAUX_API_KEYS": "marketaux",
    "POLYGON_API_KEYS": "polygon",
    "ALPHAVANTAGE_API_KEYS": "alphavantage",
    "FRED_API_KEYS": "fred",
    "FMP_API_KEYS": "fmp",
}

AUTO_DETECT_REL_DIRS = (
    ".secrets",
    "secrets",
    "config",
    "configs",
    "credentials",
    "private",
    ".",
)

FILENAME_GLOBS = (
    "*api*key*",
    "*apikey*",
    "*provider*key*",
    "*news*key*",
    "*calendar*key*",
    "*credential*",
    "*secret*",
    "*.env",
    "*.txt",
    "*.json",
    "*.yaml",
    "*.yml",
    "*.md",
)

SKIP_NAMES = {
    "phase8r_providers.env",
    ".gitignore",
}
SKIP_SUFFIXES = (".bak",)

# Exclude noisy historical folders from automatic discovery (paths only; never contents).
SKIP_DIR_PARTS_LOWER = frozenset(
    {
        "backups",
        "backup",
        ".backups",
        "archive",
        "archives",
        "node_modules",
        ".git",
        "__pycache__",
        ".venv",
        "venv",
        "dist",
        "build",
    }
)

# Hidden top-level dirs are skipped except allowlist (never traverse `.cursor`, `.BACKUPS`, etc.).
ALLOWED_HIDDEN_DIRS = frozenset({".secrets"})


def _utc_stamp_compact() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def _normalize_alias(key: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", key.strip()).upper()


def _split_csv_values(val: str) -> List[str]:
    parts = []
    for segment in val.replace("\n", ",").split(","):
        s = segment.strip().strip('"').strip("'")
        if s:
            parts.append(s)
    return parts


def _dedupe_preserve(seq: Iterable[str]) -> List[str]:
    seen: Set[str] = set()
    out: List[str] = []
    for x in seq:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def _canonical_bucket(raw_key: str) -> Optional[str]:
    nk = _normalize_alias(raw_key)
    return ALIAS_TO_CANONICAL.get(nk)


def ingest_kv_into(buckets: Dict[str, List[str]], raw_key: str, raw_val: str) -> None:
    """Merge parsed key/value into canonical buckets; expands CSV and comma lists."""
    variants = [raw_key, raw_key.rsplit(".", 1)[-1] if "." in raw_key else raw_key]
    canonical: Optional[str] = None
    for vk in variants:
        canonical = _canonical_bucket(vk)
        if canonical:
            break
    if not canonical:
        return
    chunks = _split_csv_values(raw_val)
    if not chunks:
        return
    buckets.setdefault(canonical, [])
    buckets[canonical].extend(chunks)


def parse_dotenv_text(text: str, buckets: Dict[str, List[str]]) -> None:
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith(";"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        ingest_kv_into(buckets, k, v)


def _flatten_json(obj: Any, prefix: str, buckets: Dict[str, List[str]]) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            nk = f"{prefix}.{k}" if prefix else str(k)
            if isinstance(v, (dict, list)):
                _flatten_json(v, nk, buckets)
            else:
                ingest_kv_into(buckets, nk, str(v))
                ingest_kv_into(buckets, str(k), str(v))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            _flatten_json(item, f"{prefix}[{i}]", buckets)


def parse_json_text(text: str, buckets: Dict[str, List[str]]) -> bool:
    text_stripped = text.strip()
    if not text_stripped.startswith("{"):
        return False
    try:
        data = json.loads(text_stripped)
    except json.JSONDecodeError:
        return False
    _flatten_json(data, "", buckets)
    return True


def parse_yaml_like_text(text: str, buckets: Dict[str, List[str]]) -> None:
    """Minimal top-level `Key: value` / key: value lines without PyYAML."""
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_\.]*)\s*[:=]\s*(.+)$", line)
        if not m:
            continue
        k, v = m.group(1), m.group(2).strip()
        if v.startswith('"') and v.endswith('"'):
            v = v[1:-1]
        elif v.startswith("'") and v.endswith("'"):
            v = v[1:-1]
        ingest_kv_into(buckets, k, v)


def parse_file(path: Path, buckets: Dict[str, List[str]]) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    suf = path.suffix.lower()
    if suf == ".json" or text.strip().startswith("{"):
        if parse_json_text(text, buckets):
            return
    if suf in (".yaml", ".yml"):
        parse_yaml_like_text(text, buckets)
        parse_dotenv_text(text, buckets)
        return
    parse_dotenv_text(text, buckets)
    parse_yaml_like_text(text, buckets)
    if parse_json_text(text, buckets):
        return


def _fn_matches(name: str, pattern: str) -> bool:
    return fnmatch.fnmatch(name.lower(), pattern.lower())


def _score_candidate(path: Path) -> Tuple[int, float]:
    name = path.name.lower()
    score = 0
    if name == ".env":
        score += 55
    elif "api" in name and "key" in name:
        score += 40
    elif "apikey" in name:
        score += 35
    elif "credential" in name or "secret" in name:
        score += 25
    elif "provider" in name:
        score += 15
    elif name.endswith(".env"):
        score += 22
    elif name.endswith(".json") or name.endswith(".yaml") or name.endswith(".yml"):
        score += 8
    elif name.endswith(".md"):
        score -= 15
    try:
        mtime = path.stat().st_mtime
    except OSError:
        mtime = 0.0
    return (score, mtime)


def _should_skip_candidate(path: Path, repo_root: Path) -> bool:
    try:
        path.resolve().relative_to(repo_root.resolve())
    except ValueError:
        return True
    name = path.name.lower()
    if name in SKIP_NAMES:
        return True
    if name.endswith(".bak"):
        return True
    if name == "phase8r_providers.env":
        return True
    parts_lower = [p.lower() for p in path.parts]
    for p in parts_lower:
        if p in SKIP_DIR_PARTS_LOWER:
            return True
    if ".git" in parts_lower or "__pycache__" in parts_lower or "node_modules" in parts_lower:
        return True
    return False


def discover_candidates(repo_root: Path, max_depth: int = 4) -> List[Path]:
    repo_root = repo_root.resolve()
    found: List[Path] = []
    for rel in AUTO_DETECT_REL_DIRS:
        base = (repo_root / rel).resolve()
        if not base.exists() or not base.is_dir():
            continue
        for root, dirs, files in os.walk(base, topdown=True):
            depth = Path(root).relative_to(base).parts
            if len(depth) > max_depth:
                dirs[:] = []
                continue
            filtered: List[str] = []
            for d in dirs:
                if d in (".git", "__pycache__", "node_modules", ".venv", "venv"):
                    continue
                dl = d.lower()
                if d.startswith(".") and d not in ALLOWED_HIDDEN_DIRS:
                    continue
                if dl in SKIP_DIR_PARTS_LOWER:
                    continue
                if dl in {"backups", "backup", "archive"}:
                    continue
                filtered.append(d)
            dirs[:] = filtered
            for fn in files:
                path = Path(root) / fn
                if _should_skip_candidate(path, repo_root):
                    continue
                ok = False
                for pat in FILENAME_GLOBS:
                    if _fn_matches(fn, pat):
                        ok = True
                        break
                if ok:
                    found.append(path)
    uniq = sorted(set(found))
    return uniq


def pick_best_candidate(paths: List[Path]) -> Optional[Path]:
    if not paths:
        return None
    return sorted(
        paths,
        key=lambda p: (-_score_candidate(p)[0], -_score_candidate(p)[1]),
    )[0]


def rank_candidates(paths: List[Path]) -> List[Path]:
    if not paths:
        return []
    return sorted(
        paths,
        key=lambda p: (-_score_candidate(p)[0], -_score_candidate(p)[1]),
    )


def first_candidate_with_parsed_keys(paths: List[Path]) -> Tuple[Optional[Path], Dict[str, List[str]]]:
    """Try ranked sources until canonical buckets contain at least one key."""
    ranked = rank_candidates(paths)
    empty: Dict[str, List[str]] = {c: [] for c in CANONICAL_TARGETS}
    for path in ranked:
        buckets: Dict[str, List[str]] = {c: [] for c in CANONICAL_TARGETS}
        parse_file(path, buckets)
        for c in CANONICAL_TARGETS:
            buckets[c] = _dedupe_preserve(buckets[c])
        if any(buckets[c] for c in CANONICAL_TARGETS):
            return path, buckets
    return (ranked[0] if ranked else None), empty


def build_env_lines(buckets: Dict[str, List[str]]) -> List[str]:
    lines: List[str] = []
    for canon in CANONICAL_TARGETS:
        vals = _dedupe_preserve(buckets.get(canon, []))
        if not vals:
            continue
        joined = ",".join(vals)
        lines.append(f"{canon}={joined}")
    return sorted(lines)


def write_redacted_report(
    *,
    classification: str,
    source_path: Optional[str],
    candidate_paths: List[str],
    buckets_final: Dict[str, List[str]],
    backup_path: Optional[str],
    output_path: str,
    env_written: bool,
    artifacts_dir: Path,
    stamp: str,
    secrets_printed: bool,
) -> Tuple[Path, Path]:
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    providers_detected: Dict[str, Dict[str, Any]] = {}
    key_counts_by_provider: Dict[str, int] = {}
    canonical_env_names_written: List[str] = []

    for canon in CANONICAL_TARGETS:
        vals = buckets_final.get(canon, [])
        slug = PROVIDER_SLUG_BY_CANONICAL.get(canon, canon.lower())
        n = len(_dedupe_preserve(vals))
        key_counts_by_provider[slug] = n
        providers_detected[slug] = {"present": n > 0, "key_count": n}
        if n > 0:
            canonical_env_names_written.append(canon)

    latest_path = artifacts_dir / "PHASE8R_KEY_FORMAT_REPORT_LATEST.json"
    stamped = artifacts_dir / f"PHASE8R_KEY_FORMAT_REPORT_{stamp}.json"
    payload = {
        "phase": PHASE,
        "classification": classification,
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "source_file_detected": source_path is not None,
        "source_file_path": source_path,
        "candidate_paths_total": len(candidate_paths),
        "candidate_paths_considered": candidate_paths[:120],
        "providers_detected": providers_detected,
        "canonical_env_names_written": sorted(canonical_env_names_written),
        "key_counts_by_provider": key_counts_by_provider,
        "env_file_written": env_written,
        "env_output_path": output_path,
        "backup_created": backup_path,
        "secrets_printed": secrets_printed,
        "ny_live_enabled": False,
        "send_trade_unlock_changed": False,
        "execution_paths_changed": False,
    }
    text = json.dumps(payload, indent=2)
    stamped.write_text(text, encoding="utf-8")
    latest_path.write_text(text, encoding="utf-8")
    return stamped, latest_path


def run_format(
    *,
    repo_root: Path,
    source_file: Optional[Path],
    auto_detect: bool,
    output_path: Path,
    write_report: bool,
    artifacts_dir: Path,
) -> Tuple[int, Dict[str, Any]]:
    stamp = _utc_stamp_compact()
    candidates = discover_candidates(repo_root)
    candidate_strs = [str(p.resolve()) for p in sorted(set(candidates))]
    buckets_prefill: Dict[str, List[str]] = {c: [] for c in CANONICAL_TARGETS}

    chosen: Optional[Path] = None
    if source_file:
        p = source_file.expanduser().resolve()
        if not p.is_file():
            meta = {
                "classification": "FAIL_CLOSED_KEY_FILE_NOT_FOUND",
                "message": "SOURCE_FILE_MISSING",
                "source_file": str(p),
            }
            if write_report:
                write_redacted_report(
                    classification="FAIL_CLOSED_KEY_FILE_NOT_FOUND",
                    source_path=str(p),
                    candidate_paths=candidate_strs,
                    buckets_final={c: [] for c in CANONICAL_TARGETS},
                    backup_path=None,
                    output_path=str(output_path),
                    env_written=False,
                    artifacts_dir=artifacts_dir,
                    stamp=stamp,
                    secrets_printed=False,
                )
            return 2, meta
        chosen = p
    elif auto_detect:
        chosen, buckets_prefill = first_candidate_with_parsed_keys(candidates)
        if chosen is None:
            meta = {
                "classification": "FAIL_CLOSED_KEY_FILE_NOT_FOUND",
                "message": "KEY_FILE_NOT_FOUND",
                "searched_dirs": list(AUTO_DETECT_REL_DIRS),
            }
            if write_report:
                write_redacted_report(
                    classification="FAIL_CLOSED_KEY_FILE_NOT_FOUND",
                    source_path=None,
                    candidate_paths=candidate_strs,
                    buckets_final={c: [] for c in CANONICAL_TARGETS},
                    backup_path=None,
                    output_path=str(output_path),
                    env_written=False,
                    artifacts_dir=artifacts_dir,
                    stamp=stamp,
                    secrets_printed=False,
                )
            return 2, meta
    else:
        meta = {"classification": "FAIL_CLOSED", "message": "USE_SOURCE_FILE_OR_AUTO_DETECT"}
        if write_report:
            write_redacted_report(
                classification="FAIL_CLOSED",
                source_path=None,
                candidate_paths=candidate_strs,
                buckets_final={c: [] for c in CANONICAL_TARGETS},
                backup_path=None,
                output_path=str(output_path),
                env_written=False,
                artifacts_dir=artifacts_dir,
                stamp=stamp,
                secrets_printed=False,
            )
            return 2, meta

    buckets: Dict[str, List[str]] = {c: [] for c in CANONICAL_TARGETS}
    if auto_detect and any(buckets_prefill[c] for c in CANONICAL_TARGETS):
        buckets = buckets_prefill
    else:
        parse_file(chosen, buckets)

    for c in CANONICAL_TARGETS:
        buckets[c] = _dedupe_preserve(buckets[c])

    lines = build_env_lines(buckets)
    any_key = any(buckets[c] for c in CANONICAL_TARGETS)
    classification = "PASS_KEY_FORMAT" if any_key else "FAIL_CLOSED_NO_KEYS_PARSED"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    backup_path: Optional[str] = None
    env_written = False
    if any_key:
        if output_path.is_file():
            backup = output_path.with_name(output_path.name + f".{stamp}.bak")
            shutil.copy2(output_path, backup)
            backup_path = str(backup.resolve())
        output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        env_written = True
    elif classification == "FAIL_CLOSED_NO_KEYS_PARSED":
        pass

    meta_out = {
        "classification": classification,
        "source_file_used": str(chosen.resolve()),
        "canonical_lines_written": len(lines),
        "env_file_written": env_written,
    }
    if write_report:
        write_redacted_report(
            classification=classification,
            source_path=str(chosen.resolve()),
            candidate_paths=candidate_strs,
            buckets_final=buckets,
            backup_path=backup_path,
            output_path=str(output_path.resolve()),
            env_written=env_written,
            artifacts_dir=artifacts_dir,
            stamp=stamp,
            secrets_printed=False,
        )
    exit_code = 0 if classification == "PASS_KEY_FORMAT" else 3
    return exit_code, meta_out


def main() -> int:
    parser = argparse.ArgumentParser(description="Format provider keys into Phase 8R .env (secret-safe).")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--source-file", type=Path, default=None)
    parser.add_argument("--auto-detect", action="store_true")
    parser.add_argument("--output", type=Path, default=REPO_ROOT / ".secrets" / "phase8r_providers.env")
    parser.add_argument("--artifacts-dir", type=Path, default=REPO_ROOT / "artifacts")
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()

    if not args.source_file and not args.auto_detect:
        print(
            json.dumps(
                {
                    "ok": False,
                    "exit_code": 2,
                    "classification": "FAIL_CLOSED",
                    "message": "REQUIRE_SOURCE_FILE_OR_AUTO_DETECT",
                },
                indent=2,
            )
        )
        return 2

    code, meta = run_format(
        repo_root=args.repo_root.expanduser().resolve(),
        source_file=args.source_file,
        auto_detect=bool(args.auto_detect),
        output_path=args.output.expanduser().resolve(),
        write_report=bool(args.write_report),
        artifacts_dir=args.artifacts_dir.expanduser().resolve(),
    )
    safe = {k: v for k, v in meta.items() if k != "secrets"}
    print(json.dumps({"ok": code == 0, "exit_code": code, **safe}, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
