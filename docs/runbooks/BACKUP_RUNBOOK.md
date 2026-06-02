# FXG AI-QUANT — Backup Runbook

## Overview

This runbook documents the backup system for the FXG AI-QUANT trading platform. The system creates categorized, verifiable backups that separate sensitive data from core code.

## What Gets Backed Up

### CORE Bundle (Always Created)
- All source code (`src/`, `scripts/`, `templates/`, etc.)
- Configuration files (excluding `.env` and secrets)
- Documentation (`docs/`, `*.md`)
- Test files (`tests/`)
- Runner and control plane code
- `__BACKUP_META__/` directory with:
  - Redacted environment snapshot (no secret values)
  - System information
  - Git status and HEAD reference

### SENSITIVE Bundle (Optional, Encrypted)
- `.env` files
- Private keys (`*.key`, `*.pem`)
- Credential files
- Any files matching sensitive patterns

### Git Bundle (If .git exists)
- Complete git repository as a portable bundle
- Named: `<repo>_<host>_<timestamp>_<sha>.git.bundle`

### Exclusions (Always)
- `.venv/`, `venv/`, `__pycache__/`, `*.pyc`
- `node_modules/`, `.cache/`, `.pytest_cache/`
- `BACKUPS/` (to prevent recursive backups)
- `.DS_Store`, `*.swp`, `*.swo`
- Large binary files (`*.tar.gz`, `*.zip` over 100MB)

## Backup Location

```
BACKUPS/
└── <hostname>/
    └── <repo-name>/
        └── <timestamp>/
            ├── CORE_<repo>_<timestamp>.tar.gz
            ├── SENSITIVE_<repo>_<timestamp>.tar.gz.enc  (if encrypted)
            ├── <repo>_<host>_<timestamp>_<sha>.git.bundle
            ├── SENSITIVE_FILES_LIST.txt
            ├── SHA256SUMS
            ├── MANIFEST.json
            └── NOTE.txt
```

## How to Run Backups

### Basic Backup (Core Only)
```bash
bash scripts/backup/full_backup.sh
```

### Include ARTIFACTS Directory
```bash
INCLUDE_ARTIFACTS=1 bash scripts/backup/full_backup.sh
```

### Create Encrypted Sensitive Bundle
```bash
BACKUP_PASSPHRASE="your-secure-passphrase" bash scripts/backup/full_backup.sh
```

### Custom Backup Directory
```bash
BACKUP_DIR=/path/to/external/drive bash scripts/backup/full_backup.sh
```

## Verifying Backups

### Verify Checksum Integrity
```bash
bash scripts/backup/verify_backup.sh BACKUPS/<host>/<repo>/<timestamp>
```

This will:
1. Verify SHA256 checksums for all files
2. Validate presence of required files (CORE, MANIFEST, NOTE)
3. Optionally list archive contents (first 50 entries)

### Manual Checksum Verification
```bash
cd BACKUPS/<host>/<repo>/<timestamp>
sha256sum -c SHA256SUMS
```

## Restoring from Backup

### Dry-Run (Default, Safe)
```bash
bash scripts/backup/restore_backup.sh BACKUPS/<host>/<repo>/<timestamp>
```
This prints what would be restored without making changes.

### Actual Restore
```bash
DRY_RUN=0 bash scripts/backup/restore_backup.sh BACKUPS/<host>/<repo>/<timestamp> /path/to/restore/target
```

### Force Overwrite Existing
```bash
DRY_RUN=0 FORCE=1 bash scripts/backup/restore_backup.sh BACKUPS/<host>/<repo>/<timestamp> /path/to/existing/dir
```

### Decrypt Sensitive Bundle
The restore script will prompt for passphrase interactively if a `.enc` file exists and `DRY_RUN=0`.

### Restore from Git Bundle
```bash
git clone BACKUPS/<host>/<repo>/<timestamp>/*.git.bundle restored-repo
```

## Encryption Details

### Algorithm
- AES-256-CBC via OpenSSL
- PBKDF2 key derivation with 100,000 iterations

### Encrypting (Automatic)
Set `BACKUP_PASSPHRASE` environment variable before running backup.

### Decrypting (Manual)
```bash
openssl enc -d -aes-256-cbc -pbkdf2 -iter 100000 \
  -in SENSITIVE_<repo>_<timestamp>.tar.gz.enc \
  -out SENSITIVE_<repo>_<timestamp>.tar.gz
```

## Safety Notes

### Secrets Hygiene
- **NO secrets are ever printed** to console or log files
- Environment snapshots are redacted (values replaced with `***REDACTED***`)
- Sensitive files are listed but not displayed

### Trading System Invariants
- Backup operations do NOT affect:
  - `TRADING_MODE` (remains paper)
  - `execution_enabled` (remains false)
  - Running services or daemons
  - Network/firewall configuration

### Idempotency
- Safe to run multiple times
- Each backup gets a unique timestamp directory
- Existing backups are never modified or deleted

## Recommended Backup Schedule

| Frequency | Trigger | Include |
|-----------|---------|---------|
| Before Deployment | Manual | CORE + SENSITIVE |
| Before Audit | Manual | CORE + ARTIFACTS |
| Daily (if active) | Cron | CORE only |
| Weekly | Cron | CORE + SENSITIVE + ARTIFACTS |

### Example Cron Entry
```cron
# Weekly full backup every Sunday at 2 AM
0 2 * * 0 cd /path/to/repo && INCLUDE_ARTIFACTS=1 bash scripts/backup/full_backup.sh >> /var/log/fxg-backup.log 2>&1
```

## Troubleshooting

### "Permission denied" on backup directory
```bash
mkdir -p BACKUPS && chmod 755 BACKUPS
```

### "No space left on device"
```bash
# Check disk usage
df -h
# Clean old backups (manual review first!)
ls -lt BACKUPS/*/*/ | tail -n +10
```

### Backup too large
```bash
# Exclude large directories
EXCLUDE_EXTRA="data,logs,archives" bash scripts/backup/full_backup.sh
```

### OpenSSL not available
The script will skip encrypted sensitive bundle creation and warn. Install OpenSSL:
```bash
# macOS
brew install openssl

# Debian/Ubuntu
sudo apt-get install openssl
```

## Manifest Format

`MANIFEST.json` contains:
```json
{
  "version": "1.0.0",
  "timestamp_utc": "2026-01-04T21:45:00Z",
  "hostname": "fxg-quant-paper-e2-micro",
  "repo_name": "gcloud-system",
  "git_sha": "b4f68c236aff...",
  "files": {
    "core": "CORE_gcloud-system_20260104T214500Z.tar.gz",
    "sensitive": "SENSITIVE_gcloud-system_20260104T214500Z.tar.gz.enc",
    "git_bundle": "gcloud-system_fxg-quant_20260104T214500Z_b4f68c2.git.bundle"
  },
  "checksums": "SHA256SUMS",
  "include_artifacts": false,
  "encrypted": true
}
```

## Quick Reference

| Command | Purpose |
|---------|---------|
| `bash scripts/backup/full_backup.sh` | Create backup |
| `bash scripts/backup/verify_backup.sh <dir>` | Verify backup |
| `bash scripts/backup/restore_backup.sh <dir>` | Dry-run restore |
| `DRY_RUN=0 bash scripts/backup/restore_backup.sh <dir> <target>` | Actual restore |
