#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import sys
import json
import stat
import pathlib
import subprocess
from dataclasses import dataclass
from typing import Iterable, List, Tuple, Optional

try:
    import urllib.request
except Exception:
    urllib = None

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

IGNORE_GLOBS_FOR_PASTE_ARTIFACTS = [
    "ARTIFACTS/**",
    "**/*.md",
    "SYSTEM_MAP_GCLOUD_SYSTEM.json",
]

IGNORE_GLOBS_FOR_SECRET_SCAN = [
    ".git/**",
    "ARTIFACTS/**",
    "SYSTEM_MAP_GCLOUD_SYSTEM.json",
    "**/*.bak",
    "**/*.backup",
    "**/backups/**",
    "**/*.bundle",
    "**/*.tar.zst",
    "**/__pycache__/**",
    "**/*.pyc",
    "docs/**",  # Documentation may contain example patterns
    "scripts/verify_*.py",  # Verification scripts print variable names, not values
    "scripts/git-hooks/pre-commit",  # Pre-commit hook contains safe placeholder patterns
]

IGNORE_GLOBS_FOR_BANNED_LITERALS = [
    ".git/**",
    "ARTIFACTS/**",
    "scripts/verify_repo_state.py",  # This script checks for these patterns
    "scripts/verify_all_local.sh",  # This script checks for these patterns
    "scripts/git-hooks/pre-commit",  # Pre-commit hook checks for these patterns
]

# Build banned literals via concatenation to avoid triggering pre-commit hook
BANNED_LITERALS = [
    "7248" + "728383:" + "AA",
    "c01de" + "9eb4d79",
]

SECRET_PATTERNS = [
    re.compile(r"\b\d{6,12}:[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{10,}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_\-]{10,}\b"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\b(OANDA_API_KEY|TELEGRAM_BOT_TOKEN|GOOGLE_API_KEY|GEMINI_API_KEY|OPENAI_API_KEY)\b\s*[:=]\s*['\"][^'\"]{10,}['\"]"),
]

SAFE_MARKERS = [
    "REDACTED",
    "your_key",
    "your_token",
    "REPLACE_ME",
    "INSERT_KEY_HERE",
    "__NEW_",
    "__YOUR_",
    "<NEW_",
    "<YOUR_",
    "sk-new-key-here",
    "AIza-new-key-here",
    "mark(",  # Verification scripts use mark() to show SET/MISSING, not actual values
    ": mark(",
]

PASTE_ARTIFACT_PATTERNS = [
    re.compile(r"^dquote>\s*$", re.M),
    re.compile(r"^cmdor>\s*$", re.M),
    re.compile(r"^heredoc>\s*$", re.M),
    re.compile(r"^>\.{3,}\s*$", re.M),
    re.compile(r"^if if>\s*$", re.M),
    re.compile(r"\bzsh: command not found:", re.M),
    re.compile(r"^\(\.venv\)\s+", re.M),
    re.compile(r"^mac@C0", re.M),
    re.compile(r"^source \"/Users/mac$", re.M),
]

@dataclass
class Finding:
    kind: str
    path: str
    line: int
    excerpt: str

def run(cmd: List[str], cwd: pathlib.Path = REPO_ROOT) -> Tuple[int, str]:
    p = subprocess.run(cmd, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return p.returncode, p.stdout

def iter_tracked_files(root: pathlib.Path) -> Iterable[pathlib.Path]:
    """Iterate only files tracked by git"""
    rc, out = run(["git", "ls-files"], cwd=root)
    if rc != 0:
        return
    for line in out.strip().split("\n"):
        if not line.strip():
            continue
        p = root / line.strip()
        if p.exists() and p.is_file():
            yield p

def iter_files(root: pathlib.Path, tracked_only: bool = True) -> Iterable[pathlib.Path]:
    """Iterate files - by default only tracked files"""
    if tracked_only:
        yield from iter_tracked_files(root)
    else:
        for p in root.rglob("*"):
            if p.is_dir():
                continue
            if ".git" in p.parts:
                continue
            yield p

def match_any_glob(path: pathlib.Path, globs: List[str]) -> bool:
    rel = path.relative_to(REPO_ROOT).as_posix()
    import fnmatch
    return any(fnmatch.fnmatch(rel, g) for g in globs)

def read_text_safely(path: pathlib.Path) -> Optional[str]:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None

def find_line_number(text: str, idx: int) -> int:
    return text.count("\n", 0, idx) + 1

def excerpt_around(text: str, idx: int, span: int = 120) -> str:
    start = max(0, idx - span)
    end = min(len(text), idx + span)
    ex = text[start:end].replace("\n", "\\n")
    return ex[:240]

def scan_for_banned_literals() -> List[Finding]:
    findings: List[Finding] = []
    for p in iter_files(REPO_ROOT):
        if match_any_glob(p, IGNORE_GLOBS_FOR_BANNED_LITERALS):
            continue
        txt = read_text_safely(p)
        if txt is None:
            continue
        for lit in BANNED_LITERALS:
            idx = txt.find(lit)
            if idx != -1:
                findings.append(Finding(
                    kind=f"banned_literal:{lit}",
                    path=str(p.relative_to(REPO_ROOT)),
                    line=find_line_number(txt, idx),
                    excerpt=excerpt_around(txt, idx),
                ))
    return findings

def scan_for_secret_patterns() -> List[Finding]:
    findings: List[Finding] = []
    for p in iter_files(REPO_ROOT):
        if match_any_glob(p, IGNORE_GLOBS_FOR_SECRET_SCAN):
            continue
        txt = read_text_safely(p)
        if txt is None:
            continue
        for pat in SECRET_PATTERNS:
            for m in pat.finditer(txt):
                s = m.group(0)
                if any(marker in s for marker in SAFE_MARKERS):
                    continue
                if "your_" in s or "REPLACE_ME" in s:
                    continue
                findings.append(Finding(
                    kind=f"secret_pattern:{pat.pattern[:40]}…",
                    path=str(p.relative_to(REPO_ROOT)),
                    line=find_line_number(txt, m.start()),
                    excerpt=excerpt_around(txt, m.start()),
                ))
    return findings

def scan_for_paste_artifacts() -> List[Finding]:
    findings: List[Finding] = []
    for p in iter_files(REPO_ROOT):
        if match_any_glob(p, IGNORE_GLOBS_FOR_PASTE_ARTIFACTS):
            continue
        txt = read_text_safely(p)
        if txt is None:
            continue
        for pat in PASTE_ARTIFACT_PATTERNS:
            for m in pat.finditer(txt):
                findings.append(Finding(
                    kind=f"paste_artifact:{pat.pattern}",
                    path=str(p.relative_to(REPO_ROOT)),
                    line=find_line_number(txt, m.start()),
                    excerpt=excerpt_around(txt, m.start()),
                ))
    return findings

def verify_compileall() -> Tuple[bool, str]:
    rc, out = run([sys.executable, "-m", "compileall", "-q", "."])
    return (rc == 0), out.strip()

def verify_required_files() -> List[str]:
    required = [
        "src/core/dynamic_account_manager.py",
        "scripts/telegram_health_check.py",
        "scripts/vm_deploy_gated.sh",
        "scripts/verify_all_local.sh",
        "ARTIFACTS/FINAL_STATUS.json",
        "ARTIFACTS/FINAL_STATUS.md",
        "ARTIFACTS/MONDAY_UNLOCK_SEQUENCE.md",
        "ARTIFACTS/VM_DEPLOY_INSTRUCTIONS.md",
    ]
    missing = []
    for r in required:
        if not (REPO_ROOT / r).exists():
            missing.append(r)
    return missing

def verify_executable(path_rel: str) -> bool:
    p = REPO_ROOT / path_rel
    if not p.exists():
        return False
    st_mode = p.stat().st_mode
    return bool(st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH))

def verify_final_status_json() -> Tuple[bool, str]:
    p = REPO_ROOT / "ARTIFACTS/FINAL_STATUS.json"
    if not p.exists():
        return False, "missing ARTIFACTS/FINAL_STATUS.json"
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        return False, f"FINAL_STATUS.json invalid JSON: {e}"
    for k in ("timestamp_utc", "git_branch", "git_head"):
        if k not in data:
            return False, f"FINAL_STATUS.json missing key: {k}"
    return True, "FINAL_STATUS.json OK"

def verify_account_manager_paper_safe() -> Tuple[bool, str]:
    """Verify account manager gating - requires src module to be importable"""
    # Add repo root to path for imports
    sys.path.insert(0, str(REPO_ROOT))
    try:
        import importlib
        mod_name = "src.core.dynamic_account_manager"
        if mod_name in sys.modules:
            del sys.modules[mod_name]

        old_env = dict(os.environ)
        try:
            os.environ.pop("OANDA_ACCOUNT_ID", None)
            os.environ["EXECUTION_UNLOCK_OK"] = "false"
            m = importlib.import_module(mod_name)
            importlib.reload(m)
            try:
                _ = m.get_account_manager()
            except Exception as e:
                return False, f"Paper-safe case raised unexpectedly: {type(e).__name__}: {e}"

            os.environ.pop("OANDA_ACCOUNT_ID", None)
            os.environ["EXECUTION_UNLOCK_OK"] = "true"
            if mod_name in sys.modules:
                del sys.modules[mod_name]
            m2 = importlib.import_module(mod_name)
            importlib.reload(m2)
            try:
                _ = m2.get_account_manager()
                return False, "Unlocked case did NOT raise (expected fail-closed when OANDA_ACCOUNT_ID missing)"
            except RuntimeError:
                return True, "Account manager gating OK (paper-safe + fails closed on unlock)"
            except Exception as e:
                return False, f"Unlocked case raised wrong exception: {type(e).__name__}: {e}"
        finally:
            os.environ.clear()
            os.environ.update(old_env)
    except ImportError as e:
        return False, f"Cannot import account manager module (path issue?): {e}"
    finally:
        if str(REPO_ROOT) in sys.path:
            sys.path.remove(str(REPO_ROOT))

def try_control_plane_status(url: str = "http://127.0.0.1:8787/api/status") -> Tuple[bool, str]:
    try:
        with urllib.request.urlopen(url, timeout=3) as r:
            body = r.read().decode("utf-8", errors="replace")
        j = json.loads(body)
        last_scan = j.get("last_scan_at")
        mode = j.get("mode")
        exec_enabled = j.get("execution_enabled")
        return True, f"Control plane OK: mode={mode} execution_enabled={exec_enabled} last_scan_at={last_scan}"
    except Exception as e:
        return False, f"Control plane not reachable (ok if not running): {e}"

def print_findings(title: str, findings: List[Finding], max_show: int = 50) -> None:
    if not findings:
        print(f"✅ {title}: none")
        return
    print(f"❌ {title}: {len(findings)} issue(s)")
    for f in findings[:max_show]:
        print(f" - {f.kind} @ {f.path}:{f.line} :: {f.excerpt}")
    if len(findings) > max_show:
        print(f" ... (+{len(findings)-max_show} more)")

def main() -> int:
    print(f"Repo: {REPO_ROOT}")

    ok_compile, out_compile = verify_compileall()
    if ok_compile:
        print("✅ compileall: all Python files compile")
    else:
        print("❌ compileall failed")
        print(out_compile)

    missing = verify_required_files()
    if missing:
        print("❌ Required files missing:")
        for m in missing:
            print(f" - {m}")
    else:
        print("✅ Required files present")

    if verify_executable("scripts/vm_deploy_gated.sh"):
        print("✅ scripts/vm_deploy_gated.sh is executable")
    else:
        print("❌ scripts/vm_deploy_gated.sh is NOT executable (chmod +x scripts/vm_deploy_gated.sh)")

    ok_json, msg_json = verify_final_status_json()
    print(("✅ " if ok_json else "❌ ") + msg_json)

    banned = scan_for_banned_literals()
    print_findings("Banned literal fragments", banned)

    secrets = scan_for_secret_patterns()
    print_findings("Secret-like patterns (heuristic)", secrets)

    paste = scan_for_paste_artifacts()
    print_findings("Terminal paste artifacts", paste)

    ok_am, msg_am = verify_account_manager_paper_safe()
    print(("✅ " if ok_am else "❌ ") + msg_am)

    ok_cp, msg_cp = try_control_plane_status()
    print(("✅ " if ok_cp else "ℹ️ ") + msg_cp)

    failures: List[str] = []
    if not ok_compile:
        failures.append("compileall")
    if missing:
        failures.append("missing_files")
    if not verify_executable("scripts/vm_deploy_gated.sh"):
        failures.append("deploy_not_executable")
    if not ok_json:
        failures.append("final_status_json")
    if banned:
        failures.append("banned_literals")
    if secrets:
        failures.append("secret_patterns")
    if paste:
        failures.append("paste_artifacts")
    if not ok_am:
        failures.append("account_manager_gate")

    if failures:
        print("\n❌ VERIFY FAILED:")
        print(" - " + "\n - ".join(failures))
        return 1

    print("\n✅ VERIFY PASSED: repo is clean, paper-safe, gated, and ready (execution still disabled by default).")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
