# Settings Module Quick Reference

## Import Pattern
```python
from src.core.settings import settings
```

## Available Settings

### OANDA (Trading)
```python
settings.oanda_api_key       # Optional[str] - API key
settings.oanda_account_id    # Optional[str] - Account ID
settings.oanda_env           # str - "practice" or "live" (default: practice)
settings.require_oanda()     # Raises if API key/account missing
```

### Telegram (Notifications)
```python
settings.telegram_bot_token  # Optional[str] - Bot token
settings.telegram_chat_id    # Optional[str] - Chat ID
settings.telegram_configured()  # bool - True if both set
settings.require_telegram()  # Raises if either missing
```

### News/Data Providers
```python
settings.newsapi_api_key        # Optional[str] - NewsAPI key
settings.marketaux_keys         # List[str] - MarketAux keys (CSV)
settings.alphavantage_api_key   # Optional[str] - Alpha Vantage key
```

## Environment Variables

### Required (no defaults)
- `OANDA_API_KEY`
- `OANDA_ACCOUNT_ID`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

### Optional (with defaults)
- `OANDA_ENV` (default: `"practice"`)

### Data Providers (optional)
- `NEWSAPI_API_KEY`
- `MARKETAUX_KEYS` (CSV: "key1,key2,key3")
- `MARKETAUX_KEY` (legacy single key)
- `ALPHAVANTAGE_API_KEY`

## Where to Set Environment Variables

### Local Development
```bash
# Create .env in repo root (gitignored)
OANDA_API_KEY=your_key
OANDA_ACCOUNT_ID=your_account
OANDA_ENV=practice
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id
```

### VM Production
```bash
# /etc/ai_quant/ai_quant.env
# Referenced by systemd EnvironmentFile directive
```

### CI/CD
```
GitHub → Repo Settings → Secrets and variables → Actions
Add: OANDA_API_KEY, TELEGRAM_BOT_TOKEN, etc.
```

## Usage Examples

### Basic Access
```python
from src.core.settings import settings

api_key = settings.oanda_api_key
if api_key:
    # Use it
    pass
```

### Fail-Closed Validation
```python
from src.core.settings import settings

# Will raise RuntimeError if missing
settings.require_oanda()

# Now safe to use
api = OandaAPI(settings.oanda_api_key, settings.oanda_account_id)
```

### Optional Features
```python
from src.core.settings import settings

if settings.telegram_configured():
    send_telegram_notification()
else:
    print("Telegram not configured, skipping notification")
```

### MarketAux Keys (Multiple)
```python
from src.core.settings import settings

# Iterate through all keys (rate limiting friendly)
for key in settings.marketaux_keys:
    try:
        data = fetch_news(key)
        break  # Success
    except RateLimitError:
        continue  # Try next key
```

## Verification Script

### Check Environment (No Secret Leaks)
```bash
# From repo root
PYTHONPATH="$PWD:$PYTHONPATH" python3 scripts/verify_env_no_leak.py
```

**Output:**
```
OANDA_API_KEY: SET
OANDA_ACCOUNT_ID: SET
OANDA_ENV: practice
TELEGRAM_BOT_TOKEN: SET
TELEGRAM_CHAT_ID: SET
NEWSAPI_API_KEY: SET
MARKETAUX_KEYS: SET
ALPHAVANTAGE_API_KEY: SET
```

## Migration from Old Code

### Before (Unsafe)
```python
import os
api_key = os.getenv("OANDA_API_KEY", "fallback_value")  # BAD: fallback
api_key = os.environ["OANDA_API_KEY"]  # BAD: crashes if missing
api_key = "hardcoded_value"  # VERY BAD: secret in code
```

### After (Safe)
```python
from src.core.settings import settings

# Explicit requirement
settings.require_oanda()
api_key = settings.oanda_api_key

# Or graceful handling
if settings.oanda_api_key:
    # Use it
    pass
else:
    # Skip feature
    pass
```

## Troubleshooting

### ModuleNotFoundError: No module named 'src'
```bash
# Solution: Set PYTHONPATH
export PYTHONPATH="$PWD:$PYTHONPATH"
# Or run from repo root
cd /path/to/repo && python3 your_script.py
```

### RuntimeError: Missing OANDA_API_KEY
```bash
# Solution: Set environment variable
export OANDA_API_KEY="your_key_here"
# Or create .env file with key=value pairs
```

### RuntimeError: OANDA_ENV must be 'practice' or 'live'
```bash
# Solution: Fix typo in environment variable
export OANDA_ENV="practice"  # Not "prod" or "production"
```

## Security Notes

- ✅ **DO:** Set secrets in environment files (`.env`, systemd `EnvironmentFile`)
- ✅ **DO:** Use `settings.require_*()` methods for fail-closed validation
- ✅ **DO:** Verify with `verify_env_no_leak.py` (never prints secrets)
- ❌ **DON'T:** Hardcode secrets in code
- ❌ **DON'T:** Commit `.env` files (already gitignored)
- ❌ **DON'T:** Print secret values in logs or stdout

## File Locations

Both repos have identical structure:

```
<repo>/
├── src/
│   └── core/
│       └── settings.py          ← Import from here
├── scripts/
│   └── verify_env_no_leak.py   ← Verification tool
└── .env                          ← Local secrets (gitignored)
```

## Git Hooks (Recommended)

Add to `.git/hooks/pre-commit`:
```bash
#!/bin/bash
# Fail if secrets detected in staged changes
git diff --cached | grep -E 'api.*key.*=.*["\x27][^"]*["\x27]' && exit 1
exit 0
```

---

**Documentation:** See `SETTINGS_CENTRALIZATION_REPORT.md` for full details.
