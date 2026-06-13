#!/usr/bin/env python3
"""
Auto-fix common .env format mistakes.

Fixes known patterns like KEYhttps://... by converting to KEY= plus commented doc link.
Creates a backup before making changes.
"""
import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

# Known patterns that need fixing: KEY followed by URL without =
FIX_PATTERNS = [
    (r'^(FINNHUB_API_KEYS)https://github\.com/Finnhub-Stock-API/finnhub-python', 
     'FINNHUB_API_KEYS', 
     'https://github.com/Finnhub-Stock-API/finnhub-python'),
    # Add more patterns as needed
]

def fix_env_file(env_path: Path, dry_run: bool = False) -> tuple[bool, list[str]]:
    """Fix .env file format issues. Returns (was_fixed, list_of_changes)."""
    if not env_path.exists():
        return False, [f"File not found: {env_path}"]
    
    with open(env_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    changes = []
    new_lines = []
    fixed = False
    
    for line_num, line in enumerate(lines, start=1):
        original_line = line
        modified_line = line
        
        # Check each fix pattern
        for pattern, key_name, doc_url in FIX_PATTERNS:
            if re.search(pattern, line):
                # Replace with KEY= and add comment
                modified_line = f"{key_name}=\n"
                # Check if next line is already the comment
                if line_num < len(lines) and not lines[line_num].strip().startswith(f'# (optional) docs: {doc_url}'):
                    # We'll add comment after this line
                    pass
                changes.append(f"Line {line_num}: Fixed {key_name} (was: {original_line.strip()[:50]})")
                fixed = True
                break
        
        new_lines.append(modified_line)
        
        # Add comment after fixed line if needed
        if fixed and line_num == len(lines):
            # Add comment on next line if it's the last line
            for pattern, key_name, doc_url in FIX_PATTERNS:
                if re.search(pattern, original_line):
                    new_lines.append(f"# (optional) docs: {doc_url}\n")
                    break
    
    # Remove duplicate comment lines
    final_lines = []
    prev_comment = None
    for line in new_lines:
        if line.strip().startswith('# (optional) docs:'):
            if line.strip() != prev_comment:
                final_lines.append(line)
                prev_comment = line.strip()
        else:
            final_lines.append(line)
            prev_comment = None
    
    # Ensure file ends with newline
    if final_lines and not final_lines[-1].endswith('\n'):
        final_lines[-1] += '\n'
    
    if fixed and not dry_run:
        # Create backup
        backup_path = env_path.parent / f"{env_path.name}.bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        
        # Write fixed version
        with open(env_path, 'w', encoding='utf-8') as f:
            f.writelines(final_lines)
        
        changes.append(f"Backup created: {backup_path}")
    
    return fixed, changes

def main():
    parser = argparse.ArgumentParser(description='Auto-fix common .env format mistakes')
    parser.add_argument('--env', default='.env', help='Path to .env file (default: .env)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be fixed without making changes')
    args = parser.parse_args()
    
    env_path = Path(args.env)
    if not env_path.is_absolute():
        # Resolve relative to script's parent directory (repo root)
        script_dir = Path(__file__).parent.parent
        env_path = script_dir / env_path
    
    was_fixed, changes = fix_env_file(env_path, dry_run=args.dry_run)
    
    if was_fixed:
        if args.dry_run:
            print(f"Would fix {env_path}:")
        else:
            print(f"Fixed {env_path}:")
        for change in changes:
            print(f"  {change}")
        return 0
    else:
        print(f"No fixes needed for {env_path}")
        return 0

if __name__ == '__main__':
    sys.exit(main())
