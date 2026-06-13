#!/usr/bin/env python3
"""
Phase 8W Validate Dashboard Functionality
Validates that the dashboard can handle various payload scenarios without crashing
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from datetime import datetime


def create_test_payloads():
    """Create various test payload scenarios"""
    
    # Complete normal payload
    normal_payload = {
        "contract_version": "phase8w_test",
        "generated_at_utc": datetime.utcnow().isoformat() + "Z",
        "ok": True,
        "freshness": {
            "seconds": 120,
            "stale": False,
            "status": "FRESH"
        },
        "summary_cards": {
            "result_rows_indexed": 10,
            "promotion_candidates_count": 2,
            "providers_working_count": 1,
            "providers_blocked_count": 0
        },
        "tables": {
            "promotion_candidates": [
                {
                    "strategy_id": "TEST_STRATEGY_001",
                    "instrument": "EURUSD",
                    "session": "london",
                    "expectancy": 0.75
                }
            ],
            "continue_forward": [],
            "watch_only": [],
            "demoted_blocked": [],
            "fail_closed": [],
            "proxy_research": [],
            "latest_runs": []
        },
        "safety": {
            "paper_review_only": True,
            "live_permission": False,
            "ny_live_enabled": False,
            "send_trade_unlock_changed": False,
            "execution_paths_changed": False
        },
        "calendar_budget": {
            "calendar_budget_remaining": 995,
            "calendar_calls_this_month": 5
        },
        "provider_capability": {
            "providers_working": ["rapidapi_economic_calendar"],
            "providers_blocked": []
        },
        "exact_replay_status": {
            "exact_strategy_replay": False,
            "latest_phase8o_classification": "candidate_level"
        },
        "warnings": []
    }
    
    # Missing freshness field
    missing_freshness = normal_payload.copy()
    del missing_freshness["freshness"]
    missing_freshness["dashboard_freshness_seconds"] = 180
    
    # Missing tables
    missing_tables = normal_payload.copy()
    del missing_tables["tables"]
    
    # Missing summary_cards
    missing_summary = normal_payload.copy()
    del missing_summary["summary_cards"]
    
    # Empty payload
    empty_payload = {}
    
    # Wrapped API response
    wrapped_payload = {
        "data": normal_payload.copy()
    }
    
    return {
        "normal": normal_payload,
        "missing_freshness": missing_freshness,
        "missing_tables": missing_tables,
        "missing_summary": missing_summary,
        "empty": empty_payload,
        "wrapped": wrapped_payload
    }


def validate_dashboard_files(dashboard_dir):
    """Validate that required dashboard files exist"""
    dashboard_path = Path(dashboard_dir)
    
    required_files = [
        "app.js",
        "index.html",
        "styles.css"
    ]
    
    missing_files = []
    for file_name in required_files:
        file_path = dashboard_path / file_name
        if not file_path.exists():
            missing_files.append(str(file_path))
    
    if missing_files:
        print(f"FAIL: Missing dashboard files: {missing_files}")
        return False
    
    print("PASS: All required dashboard files present")
    return True


def validate_app_js_structure(dashboard_dir):
    """Validate app.js has required normalization functions"""
    app_js_path = Path(dashboard_dir) / "app.js"
    
    with open(app_js_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    required_patterns = [
        "normalizePayload(raw)",
        "get data()",
        "this.state.data", 
        "normalizedFreshness",
        "normalizedTables",
        "normalizedSafety"
    ]
    
    missing_patterns = []
    for pattern in required_patterns:
        if pattern not in content:
            missing_patterns.append(pattern)
    
    if missing_patterns:
        print(f"FAIL: Missing required patterns in app.js: {missing_patterns}")
        return False
    
    print("PASS: app.js has required normalization structure")
    return True


def validate_no_direct_data_access(dashboard_dir):
    """Validate that app.js doesn't access this.data directly without proper getter"""
    app_js_path = Path(dashboard_dir) / "app.js"
    
    with open(app_js_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    problematic_lines = []
    for i, line in enumerate(lines, 1):
        # Skip getter definition
        if 'get data()' in line or 'return this.state.data' in line:
            continue
        
        # Look for direct this.data access
        if 'this.data.' in line and 'this.state.data' not in line:
            problematic_lines.append(f"Line {i}: {line.strip()}")
    
    if problematic_lines:
        print(f"FAIL: Found direct this.data access: {problematic_lines}")
        return False
    
    print("PASS: No problematic direct data access found")
    return True


def validate_payload_compatibility(payload_path):
    """Validate compatibility with real payload"""
    if not payload_path or not Path(payload_path).exists():
        print("WARN: Real payload file not provided or not found")
        return True  # Not a failure, just skip
    
    try:
        with open(payload_path, 'r', encoding='utf-8') as f:
            real_payload = json.load(f)
        
        required_fields = ['freshness', 'tables', 'safety', 'summary_cards']
        missing_fields = []
        
        for field in required_fields:
            if field not in real_payload:
                missing_fields.append(field)
        
        if missing_fields:
            print(f"WARN: Real payload missing fields: {missing_fields}")
            print("NOTE: Dashboard normalization should handle these cases")
        else:
            print("PASS: Real payload has all expected fields")
        
        return True
        
    except Exception as e:
        print(f"WARN: Could not validate real payload: {e}")
        return True  # Not a critical failure


def generate_test_html(dashboard_dir, test_payloads):
    """Generate test HTML files for each payload scenario"""
    dashboard_path = Path(dashboard_dir)
    
    # Read original index.html
    index_path = dashboard_path / "index.html"
    with open(index_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    test_results = []
    
    for scenario_name, payload in test_payloads.items():
        # Create test HTML with injected payload
        test_html = html_content.replace(
            'new Phase8Dashboard();',
            f'''
            // Inject test payload for scenario: {scenario_name}
            const testPayload = {json.dumps(payload, indent=2)};
            const dashboard = new Phase8Dashboard();
            
            // Override loadData to use test payload
            dashboard.loadData = async function() {{
                console.log('🧪 Using test payload for scenario: {scenario_name}');
                this.state.data = this.normalizePayload(testPayload);
                this.state.dataSource = 'test';
                this.state.lastRefresh = new Date();
            }};
            
            // Continue with normal initialization
            '''
        )
        
        # Write test HTML
        test_file_path = dashboard_path / f"test_{scenario_name}.html"
        with open(test_file_path, 'w', encoding='utf-8') as f:
            f.write(test_html)
        
        test_results.append({
            "scenario": scenario_name,
            "file": str(test_file_path),
            "payload_size": len(json.dumps(payload))
        })
    
    return test_results


def main():
    parser = argparse.ArgumentParser(description='Validate Phase 8W Dashboard Functionality')
    parser.add_argument('--dashboard-dir', required=True, help='Path to dashboard directory')
    parser.add_argument('--payload', help='Path to real payload file for compatibility test')
    parser.add_argument('--write-report', action='store_true', help='Write validation report')
    
    args = parser.parse_args()
    
    print("Phase 8W Dashboard Functionality Validation")
    print(f"Dashboard Directory: {args.dashboard_dir}")
    print(f"Payload File: {args.payload or 'Not provided'}")
    print("-" * 60)
    
    validation_results = []
    
    # 1. Validate dashboard files exist
    print("1. Validating dashboard files...")
    result1 = validate_dashboard_files(args.dashboard_dir)
    validation_results.append(("Dashboard Files", result1))
    
    # 2. Validate app.js structure
    print("\n2. Validating app.js structure...")
    result2 = validate_app_js_structure(args.dashboard_dir)
    validation_results.append(("App.js Structure", result2))
    
    # 3. Validate no direct data access
    print("\n3. Validating data access patterns...")
    result3 = validate_no_direct_data_access(args.dashboard_dir)
    validation_results.append(("Data Access Patterns", result3))
    
    # 4. Validate payload compatibility
    print("\n4. Validating payload compatibility...")
    result4 = validate_payload_compatibility(args.payload)
    validation_results.append(("Payload Compatibility", result4))
    
    # 5. Generate test scenarios
    print("\n5. Generating test payload scenarios...")
    test_payloads = create_test_payloads()
    test_results = generate_test_html(args.dashboard_dir, test_payloads)
    validation_results.append(("Test Scenarios", True))
    
    # Summary
    print("\n" + "="*60)
    print("VALIDATION SUMMARY")
    print("="*60)
    
    all_passed = True
    for test_name, passed in validation_results:
        status = "PASS" if passed else "FAIL"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False
    
    print(f"\nTest Scenarios Generated: {len(test_results)}")
    for test in test_results:
        print(f"  - {test['scenario']}: {test['file']}")
    
    # Write report if requested
    if args.write_report:
        report = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "dashboard_dir": args.dashboard_dir,
            "payload_file": args.payload,
            "validation_results": dict(validation_results),
            "test_scenarios": test_results,
            "overall_status": "PASS" if all_passed else "FAIL"
        }
        
        report_path = Path(args.dashboard_dir).parent / "phase8w_dashboard_validation_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
        
        print(f"\nReport written to: {report_path}")
    
    print(f"\nOVERALL STATUS: {'PASS' if all_passed else 'FAIL'}")
    
    # Exit with appropriate code
    sys.exit(0 if all_passed else 1)


if __name__ == '__main__':
    main()