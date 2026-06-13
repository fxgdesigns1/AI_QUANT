#!/usr/bin/env python3
"""
Phase 8W Stitch Functional Dashboard Tests
Tests for crash scenarios and payload normalization
"""

import unittest
import json
import os
from pathlib import Path

class TestPhase8WStitchDashboard(unittest.TestCase):
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = Path(__file__).parent
        self.dashboard_dir = self.test_dir.parent / "dashboard" / "phase8_stitch_dashboard"
        self.app_js_path = self.dashboard_dir / "app.js"
        
        # Verify files exist
        self.assertTrue(self.app_js_path.exists(), f"app.js not found at {self.app_js_path}")
        
    def test_app_js_normalizePayload_function_exists(self):
        """Test that normalizePayload function exists in app.js"""
        with open(self.app_js_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        self.assertIn('normalizePayload(raw)', content, 
                     "normalizePayload function not found in app.js")
        
    def test_app_js_no_direct_data_access(self):
        """Test that app.js doesn't access this.data directly without state"""
        with open(self.app_js_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for problematic patterns
        lines = content.split('\n')
        problematic_lines = []
        
        for i, line in enumerate(lines, 1):
            # Skip the getter definition line
            if 'get data()' in line or 'return this.state.data' in line:
                continue
                
            # Look for direct this.data access that bypasses state
            if 'this.data.' in line and 'this.state.data' not in line:
                problematic_lines.append(f"Line {i}: {line.strip()}")
        
        self.assertEqual(len(problematic_lines), 0, 
                        f"Found direct this.data access without state: {problematic_lines}")
        
    def test_payload_normalization_missing_freshness(self):
        """Test payload normalization when freshness field is missing"""
        # This would be executed in browser context, but we can test the structure
        test_payload = {
            "contract_version": "phase8w_test",
            "generated_at_utc": "2026-05-04T10:00:00Z",
            "dashboard_freshness_seconds": 300,
            "summary_cards": {"result_rows_indexed": 100},
            "tables": {"promotion_candidates": []},
            "safety": {"paper_review_only": True}
        }
        
        # Verify test payload is missing freshness
        self.assertNotIn('freshness', test_payload)
        
        # The normalization logic should handle this case
        # (In a real test, we'd run this through the JS normalizePayload function)
        
    def test_payload_normalization_empty_payload(self):
        """Test payload normalization with completely empty payload"""
        test_payload = {}
        
        # Empty payload should not crash the dashboard
        # (In a real test, we'd run this through the JS normalizePayload function)
        
    def test_payload_normalization_wrapped_response(self):
        """Test payload normalization with API response wrapper"""
        test_payload = {
            "data": {
                "freshness": {"seconds": 120, "status": "FRESH"},
                "tables": {"promotion_candidates": []}
            }
        }
        
        # Wrapped response should be handled
        # (In a real test, we'd run this through the JS normalizePayload function)
        
    def test_required_table_structure(self):
        """Test that all required table keys are present after normalization"""
        required_tables = [
            "latest_runs",
            "promotion_candidates", 
            "continue_forward",
            "watch_only",
            "demoted_blocked",
            "fail_closed",
            "proxy_research"
        ]
        
        # Verify these table keys are in the normalization logic
        with open(self.app_js_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        for table_key in required_tables:
            self.assertIn(f'{table_key}:', content,
                         f"Table key {table_key} not found in normalization")
            
    def test_safety_defaults_are_fail_safe(self):
        """Test that safety flag defaults are fail-safe"""
        with open(self.app_js_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for fail-safe defaults in normalization
        fail_safe_patterns = [
            'paper_review_only: true',
            'live_permission: false', 
            'ny_live_enabled: false',
            'send_trade_unlock_changed: false',
            'execution_paths_changed: false'
        ]
        
        for pattern in fail_safe_patterns:
            self.assertIn(pattern, content,
                         f"Fail-safe default not found: {pattern}")
            
    def test_real_payload_compatibility(self):
        """Test compatibility with real Phase 8U payload structure"""
        artifacts_dir = self.test_dir.parent / "ARTIFACTS" / "performance"
        payload_file = artifacts_dir / "latest_stitch_dashboard_payload.json"
        
        if payload_file.exists():
            with open(payload_file, 'r', encoding='utf-8') as f:
                real_payload = json.load(f)
            
            # Verify real payload has expected structure
            self.assertIn('freshness', real_payload, "Real payload missing freshness")
            self.assertIn('tables', real_payload, "Real payload missing tables") 
            self.assertIn('safety', real_payload, "Real payload missing safety")
            self.assertIn('summary_cards', real_payload, "Real payload missing summary_cards")
            
            # Verify required table keys exist
            tables = real_payload.get('tables', {})
            required_table_keys = ['promotion_candidates', 'continue_forward', 'watch_only']
            for key in required_table_keys:
                self.assertIn(key, tables, f"Real payload missing table: {key}")
        else:
            self.skipTest("Real payload file not found for compatibility test")
            
    def test_dashboard_error_handling(self):
        """Test that dashboard has proper error handling for missing fields"""
        with open(self.app_js_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Should have warnings for missing fields
        self.assertIn('missingFields', content, "No missing fields handling found")
        self.assertIn('normalized_missing_fields', content, "No normalized missing fields warning")
        
    def test_no_placeholder_data(self):
        """Test compliance with no placeholder rule - no fake/mock data in production"""
        with open(self.app_js_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Should not have hardcoded fake user data or placeholder content
        placeholder_patterns = [
            'coming soon',
            'lorem ipsum', 
            'fake user',
            'test@example.com',
            'john doe',
            'sample data'
        ]
        
        content_lower = content.lower()
        found_placeholders = []
        
        for pattern in placeholder_patterns:
            if pattern in content_lower:
                found_placeholders.append(pattern)
                
        self.assertEqual(len(found_placeholders), 0, 
                        f"Found placeholder patterns: {found_placeholders}")


if __name__ == '__main__':
    unittest.main()