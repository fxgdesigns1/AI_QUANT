# Graphify on ALPHA VM and Windows VM

Graphify adds **local** `graphify-out/` (gitignored) plus **git hooks** to keep an AST code graph fresh. It complements **code-review-graph** (MCP), which is separate.

Committed helpers:

- `scripts/fxg_graphify_setup_vm.sh` — install `graphifyy` into `.venv` and run `scripts/install_git_hooks.sh`
- `scripts/git-hooks/post-commit`, `post-checkout` — tracked copies of Graphify hooks
- `.gitignore` — ignores `graphify-out/`

## ALPHA owner VM (`fxg-paper-e2-small-main-2026`)

**SSH:**

```bash
gcloud compute ssh --zone "us-central1-a" "fxg-paper-e2-small-main-2026" --project "fxg-ai-trading"
```

**On the VM** (repo canonical path is `/opt/ai-quant`; run as `aiquant` if that user owns the tree):

```bash
cd /opt/ai-quant
git pull   # ensure this runbook + scripts are present
bash scripts/fxg_graphify_setup_vm.sh
```

**Optional first graph** (long on large trees; runs in foreground):

```bash
cd /opt/ai-quant
FXG_GRAPHIFY_INITIAL_UPDATE=1 bash scripts/fxg_graphify_setup_vm.sh
```

Rebuilds also run **after commits** in the background (see `~/.cache/graphify-rebuild.log` on Linux).

**Not required for production:** Cursor, Claude Code, and Codex IDE hooks are for developer workstations. The VM only needs the **Python package + git hooks** if you want Graphify there.

## Windows VM (Git for Windows + full repo clone)

Use this only where the **same git repository** is checked out (not telemetry-only trees).

1. Install **Python 3.10+** and **Git for Windows** (includes Git Bash).
2. Open **Git Bash**, `cd` to the repo root (path with spaces is fine if quoted).
3. Ensure `.venv` exists (Windows uses `.venv/Scripts/`; the setup script supports that). Example:

```bash
python -m venv .venv
source .venv/Scripts/activate
python -m pip install -U pip wheel
bash scripts/fxg_graphify_setup_vm.sh
```

Git hooks use `#!/bin/sh` and `nohup`; they run under Git Bash’s environment. If `graphify` import fails in the hook, install `graphifyy` into `.venv` (re-run the script) or into the same interpreter `python` / `python3` uses.

**Optional first graph:**

```bash
FXG_GRAPHIFY_INITIAL_UPDATE=1 bash scripts/fxg_graphify_setup_vm.sh
```

## After setup

- `graphify-out/` stays local; regenerate with `source .venv/bin/activate && graphify update .` (Linux) or `.venv/Scripts/graphify.exe update .` (Windows Git Bash), or rely on hooks.
- HTML viz is skipped automatically for very large graphs (see Graphify messages).
