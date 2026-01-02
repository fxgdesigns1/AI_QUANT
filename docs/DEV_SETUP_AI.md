# AI Provider Setup (Repo-local venv)

## One-time

```bash
cd "$(git rev-parse --show-toplevel)" || exit 1
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -U openai google-genai
```

## Configure

- Set `AI_PROVIDER_CHAIN=openai,gemini`
- Set `GEMINI_MODEL=gemini-2.0-flash-lite`

## Smoke test

Using `scripts/venv_run.sh` helper (recommended):
```bash
set -a; source .env; set +a
scripts/venv_run.sh AI_INSIGHTS_CALL_SMOKE=1 PYTHONPATH=. python3 scripts/verify_ai_providers_no_leak.py
```

Or manually activate venv:
```bash
source .venv/bin/activate
set -a; source .env; set +a
AI_INSIGHTS_CALL_SMOKE=1 PYTHONPATH=. python3 scripts/verify_ai_providers_no_leak.py
```

## Helper Script

`scripts/venv_run.sh` automatically activates the repo-local venv and supports environment variable prefixes:
```bash
# Simple command
scripts/venv_run.sh python --version

# With environment variables
scripts/venv_run.sh VAR=value python script.py

# Multiple env vars
scripts/venv_run.sh VAR1=val1 VAR2=val2 python script.py
```
