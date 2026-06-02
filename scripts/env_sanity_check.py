#!/usr/bin/env python3
"""
Validate .env file format.

Scans ENV_FILE (default .env) and fails if any non-empty, non-comment line
is not in KEY=VALUE format.
"""
import argparse
import re
import sys
from pathlib import Path

def validate_env_file(env_path: Path) -> tuple[bool, list[str]]:
    """Validate .env file format. Returns (is_valid, list_of_errors)."""
    errors = []
    
    if not env_path.exists():
        return False, [f"File not found: {env_path}"]
    
    with open(env_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Pattern: valid KEY=VALUE (with optional value, including empty)
    # Also allows: KEY="value with spaces" or KEY='value'
    valid_line_pattern = re.compile(r'^\s*([A-Z0-9_]+)\s*=\s*(.*)$|^\s*#.*$|^\s*$')
    
    for line_num, line in enumerate(lines, start=1):
        line_stripped = line.rstrip('\n\r')
        
        # Skip empty lines and comments
        if not line_stripped.strip() or line_stripped.strip().startswith('#'):
            continue
        
        # Check if line matches valid format
        if not valid_line_pattern.match(line_stripped):
            errors.append(f"Line {line_num}: Invalid format (expected KEY=VALUE or comment): {line_stripped[:60]}")
    
    return len(errors) == 0, errors

def main():
    parser = argparse.ArgumentParser(description='Validate .env file format')
    parser.add_argument('--env', default='.env', help='Path to .env file (default: .env)')
    args = parser.parse_args()
    
    env_path = Path(args.env)
    if not env_path.is_absolute():
        # Resolve relative to script's parent directory (repo root)
        script_dir = Path(__file__).parent.parent
        env_path = script_dir / env_path
    
    is_valid, errors = validate_env_file(env_path)
    
    if is_valid:
        print(f"✓ {env_path} format is valid")
        return 0
    else:
        print(f"✗ {env_path} has format errors:", file=sys.stderr)
        for error in errors:
            print(f"  {error}", file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())
