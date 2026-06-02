#!/usr/bin/env bash
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
mkdir -p "$ROOT/.git/hooks"
cp -f "$ROOT/scripts/git-hooks/pre-commit" "$ROOT/.git/hooks/pre-commit"
chmod +x "$ROOT/.git/hooks/pre-commit"
echo "Installed pre-commit hook into .git/hooks/pre-commit"

for hook in post-commit post-checkout; do
  if [ -f "$ROOT/scripts/git-hooks/$hook" ]; then
    cp -f "$ROOT/scripts/git-hooks/$hook" "$ROOT/.git/hooks/$hook"
    chmod +x "$ROOT/.git/hooks/$hook"
    echo "Installed $hook hook into .git/hooks/$hook (graphify)"
  fi
done
