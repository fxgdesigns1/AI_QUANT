#!/usr/bin/env python3
"""
Utility to detect duplicate strategy config files and rename duplicates
to make separations explicit (e.g., append _DUP1, _DUP2, ...).
This helps ensure a single canonical config is used when TRADE_CANONICAL_CONFIG_PATH is set.
Note: This is a best-effort utility; it does not modify the content, only filenames.
"""
import os
import sys
import hashlib
from pathlib import Path

def file_md5(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def rename_duplicates(config_dir: Path) -> int:
    if not config_dir.exists() or not config_dir.is_dir():
        print(f"Config dir not found: {config_dir}")
        return 0
    md5_map = {}
    dup_count = 0
    for p in sorted(config_dir.glob("*.yaml")):
        if not p.is_file():
            continue
        digest = file_md5(p)
        if digest in md5_map:
            # Found a duplicate - rename it
            base = p.stem
            ext = p.suffix
            new_name = f"{base}_DUP{md5_map[digest]}{ext}"
            new_path = p.with_name(new_name)
            # avoid collisions
            counter = 1
            while new_path.exists():
                new_path = p.with_name(f"{base}_DUP{md5_map[digest]}_{counter}{ext}")
                counter += 1
            p.rename(new_path)
            dup_count += 1
            print(f"Renamed duplicate {p.name} -> {new_path.name}")
        else:
            md5_map[digest] = 1
    return dup_count

def main():
    if len(sys.argv) < 2:
        print("Usage: rename_duplicate_configs.py <config_directory>")
        sys.exit(2)
    config_dir = Path(sys.argv[1]).resolve()
    count = rename_duplicates(config_dir)
    print(f"Done. {count} duplicates renamed.")

if __name__ == "__main__":
    main()































