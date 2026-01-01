#!/usr/bin/env python3
import json
import csv
import argparse
from datetime import datetime
from pathlib import Path

def load_json(input_path: str):
    try:
    # read JSON file
        with open(input_path, "r") as f:
            return json.load(f)
    except Exception:
        return None

def ensure_dirs(base: Path) -> Path:
    export_dir = base / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    return export_dir

def save_json(report: dict, path: Path):
    with open(path, "w") as f:
        json.dump(report, f, indent=2)

def save_csv(report: dict, path: Path):
    # Create two sections: duplicates and mismatches
    with open(path, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["type", "name_or_file", "detail", "endpoint", "issue"])
        # duplicates
        duplicates = report.get("duplicates_by_name", {})
        for name, files in duplicates.items():
            for file_path in files:
                writer.writerow(["duplicate", name, "", file_path, ""])
        # mismatches
        for mismatch in report.get("mismatches", []):
            file_path = mismatch.get("file", "")
            endpoint_str = json.dumps(mismatch.get("endpoint", {}))
            issue = mismatch.get("issue", "")
            writer.writerow(["mismatch", "", file_path, endpoint_str, issue])

def main():
    parser = argparse.ArgumentParser(description="Export latest config issues to JSON and CSV.")
    parser.add_argument("--input", default="/tmp/config_issues.json", help="Input JSON path from identify_config_issues.py")
    args = parser.parse_args()

    data = load_json(args.input)
    if not isinstance(data, dict):
        print(json.dumps({"error": "Invalid input JSON"}, indent=2))
        raise SystemExit(1)

    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_dir = Path("data") / "exports"
    base_dir.mkdir(parents=True, exist_ok=True)

    json_path = base_dir / f"config_issues_{now}.json"
    csv_path = base_dir / f"config_issues_{now}.csv"

    save_json(data, json_path)
    save_csv(data, csv_path)

    result = {"json": str(json_path), "csv": str(csv_path)}
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()





























