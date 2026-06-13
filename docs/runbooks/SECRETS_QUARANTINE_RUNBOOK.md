# Secrets Quarantine Runbook

## Overview

This runbook documents the quarantine process for sensitive artifacts in the FXG AI-QUANT repository. The goal is to ensure no hardcoded secrets exist in runtime code paths while preserving historical artifacts safely.

## Quarantine Process

### What Gets Quarantined

Files are copied (never deleted) to `QUARANTINE/<timestamp>/` with the following categories:

| Category | Description | Action |
|----------|-------------|--------|
| `ssh_keys/` | SSH private key files | Critical - rotate immediately |
| `service/` | Systemd service files with `Environment=` directives | Replace with template |
| `historical/` | Forensic audit JSON files with code snapshots | Safe to archive |
| `env/` | Environment files with credentials | Should be gitignored |
| `yaml_creds/` | YAML configs with embedded credentials | Should be gitignored |
| `other/` | Any other sensitive artifacts | Review case-by-case |

### Running the Quarantine Script

```bash
# Preview mode (no changes)
DRY_RUN=1 bash scripts/security/quarantine_sensitive_artifacts.sh

# Execute quarantine
bash scripts/security/quarantine_sensitive_artifacts.sh
```

The script:
1. Creates `QUARANTINE/<UTC_TIMESTAMP>/` with subfolders
2. Copies (never moves) sensitive files
3. Generates `MANIFEST.json` with SHA256 hashes (no file contents)
4. Updates `.gitignore` with quarantine patterns

### Manifest Format

```json
{
  "quarantine_timestamp": "20260104T221934Z",
  "repo_root": "/path/to/repo",
  "files": [
    {
      "source": "./path/to/file",
      "category": "ssh_keys",
      "dest": "QUARANTINE/.../ssh_keys/file",
      "sha256": "abc123..."
    }
  ]
}
```

## Verification

### Running the Secrets Scanner

```bash
# Standard scan
bash scripts/security/verify_repo_no_secrets.sh

# Verbose mode (show all matches)
VERBOSE=1 bash scripts/security/verify_repo_no_secrets.sh
```

**Exit codes:**
- `0` = PASS - No high-risk patterns outside quarantine
- `1` = FAIL - High-risk patterns detected

### Patterns Scanned

**HIGH-RISK (cause failure):**
- `sk-[A-Za-z0-9]{20,}` - OpenAI API keys
- `AIza[0-9A-Za-z\-_]{30,}` - Google API keys
- `-----BEGIN * PRIVATE KEY-----` - Private keys
- Hardcoded `OANDA_API_KEY=REDACTED assignments
- Hardcoded `TELEGRAM_BOT_TOKEN=REDACTED assignments

**MEDIUM-RISK (warnings):**
- Service files with `Environment=*_KEY=...`
- `.env` files outside gitignore

## Post-Quarantine Steps

### 1. Rotate Exposed Credentials

If any real credentials were found in quarantined files:

1. **OANDA**: Generate new API key at [OANDA Portal](https://www.oanda.com/demo-account/)
2. **Telegram**: Create new bot token via [@BotFather](https://t.me/BotFather)
3. **OpenAI**: Rotate key at [OpenAI Dashboard](https://platform.openai.com/api-keys)
4. **Google**: Rotate at [Google Cloud Console](https://console.cloud.google.com/apis/credentials)

See `docs/runbooks/ROTATION_CHECKLIST.md` for detailed steps.

### 2. Update Environment Configuration

Deploy new credentials to runtime environment:

```bash
# VM deployment
sudo nano /etc/ai-quant/ai-quant.env  # edit values
sudo systemctl restart ai-quant-control-plane.service

# Local development
cp .env.example .env
nano .env  # fill in rotated values
```

### 3. Verify Clean State

```bash
# Must pass
bash scripts/security/verify_repo_no_secrets.sh

# Check runtime status
curl -s http://127.0.0.1:8787/api/status | jq '{mode, execution_enabled}'
# Expected: {"mode": "paper", "execution_enabled": false}
```

## .gitignore Coverage

The quarantine script adds these patterns if missing:

```gitignore
# Quarantine (sensitive artifacts)
QUARANTINE/
forensic_snapshot/
cloud_declutter_v2/Oracle/
```

Verify existing coverage:
```bash
grep -E "(QUARANTINE|forensic_snapshot|cloud_declutter)" .gitignore
```

## Troubleshooting

### Scanner Shows Hits in Gitignored Files

The scanner excludes `QUARANTINE/**` and `ARTIFACTS/**`. If hits appear in other gitignored paths:

1. Add explicit excludes to `.gitignore`
2. Or add glob excludes to the scanner script

### Cannot Copy Files (Permission Denied)

Files in gitignore may not be readable. This is expected - those files are already protected from accidental commits.

### Manifest is Empty

If `MANIFEST.json` shows empty files array, the sensitive files are already gitignored and couldn't be read. This is the intended protection state.

## Related Documentation

- `docs/runbooks/ROTATION_CHECKLIST.md` - Credential rotation procedures
- `VM_RUNBOOK.md` - VM deployment guide
- `systemd/ai-quant-control-plane.service.template` - Canonical service template
- `ARTIFACTS/remediation/REMEDIATION_EVIDENCE_INDEX.md` - Evidence artifacts

---

**Last Updated**: 2026-01-04
**Status**: Active
