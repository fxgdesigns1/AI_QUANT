#!/usr/bin/env python3
import json
from pathlib import Path
from typing import Dict, List, Any

try:
    import yaml
    HAS_YAML = True
except Exception:
    HAS_YAML = False

def load_yaml_file(path: Path) -> Any:
    if not HAS_YAML:
        return None
    try:
        with open(path, "r") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return None

def main() -> None:
    root = Path(".")
    yaml_files = sorted(list(root.rglob("*.yaml")) + list(root.rglob("*.yml")))
    endpoint_index: Dict[str, List[str]] = {}
    mismatches: List[Dict[str, Any]] = []

    for fpath in yaml_files:
        data = load_yaml_file(fpath)
        if not isinstance(data, dict):
            continue
        endpoints = data.get("endpoints")
        if not isinstance(endpoints, list):
            continue
        for ep in endpoints:
            if not isinstance(ep, dict):
                continue
            name = ep.get("name")
            host = ep.get("host")
            port = ep.get("port")
            if name:
                endpoint_index.setdefault(name, []).append(str(fpath))
            if host is None or port is None:
                mismatches.append({"file": str(fpath), "endpoint": ep, "issue": "missing_field"})
            else:
                try:
                    int(port)
                except Exception:
                    mismatches.append({"file": str(fpath), "endpoint": ep, "issue": "port_not_int"})

    duplicates_by_name = {n: files for n, files in endpoint_index.items() if len(files) > 1}
    report = {
        "duplicates_by_name": duplicates_by_name,
        "mismatches": mismatches,
        "summary": {
            "files_scanned": len(yaml_files),
            "endpoints_found": sum(len(v) for v in endpoint_index.values()),
            "duplicates_count": len(duplicates_by_name),
            "mismatches_count": len(mismatches),
        }
    }
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()


