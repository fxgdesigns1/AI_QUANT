#!/usr/bin/env python3
"""
Phase 8V Stitch Visual Dashboard Validation Tests
Ensures the real Stitch-style dashboard meets all Phase 8V requirements
"""

import json
import os
import re
import sys
import unittest
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add project root to Python path
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

class Phase8VStitchVisualDashboardTests(unittest.TestCase):
    """Test suite for Phase 8V Stitch visual dashboard validation"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test class with paths and configurations"""
        cls.repo_root = REPO_ROOT
        cls.dashboard_path = cls.repo_root / "dashboard" / "phase8_stitch_dashboard"
        cls.payload_path = cls.repo_root / "ARTIFACTS" / "performance" / "latest_stitch_dashboard_payload.json"
        cls.old_preview_path = cls.repo_root / "scripts" / "phase8u_open_stitch_dashboard_preview.py"
        
        # Load payload for validation
        cls.payload_data = None
        if cls.payload_path.exists():
            with open(cls.payload_path, 'r', encoding='utf-8') as f:
                cls.payload_data = json.load(f)
    
    def test_dashboard_directory_exists(self):
        """Test that the Stitch dashboard directory exists"""
        self.assertTrue(
            self.dashboard_path.exists(),
            f"Dashboard directory does not exist: {self.dashboard_path}"
        )
        self.assertTrue(
            self.dashboard_path.is_dir(),
            f"Dashboard path is not a directory: {self.dashboard_path}"
        )
    
    def test_required_dashboard_files_exist(self):
        """Test that all required dashboard files exist"""
        required_files = ["index.html", "styles.css", "app.js"]
        
        for filename in required_files:
            file_path = self.dashboard_path / filename
            with self.subTest(file=filename):
                self.assertTrue(
                    file_path.exists(),
                    f"Required dashboard file missing: {filename}"
                )
                self.assertGreater(
                    file_path.stat().st_size,
                    0,
                    f"Dashboard file is empty: {filename}"
                )
    
    def test_html_contains_stitch_markers(self):
        """Test that HTML contains required Stitch-style markers"""
        html_path = self.dashboard_path / "index.html"
        self.assertTrue(html_path.exists(), "index.html not found")
        
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Required visual markers
        required_markers = [
            "REAL STITCH-STYLE PHASE 8 DASHBOARD",
            "DATA SOURCE = PHASE 8U PAYLOAD/API",
            "BACKTEST ENVIRONMENT AUTOMATION",
            "Quant-Focus Design System"
        ]
        
        for marker in required_markers:
            with self.subTest(marker=marker):
                self.assertIn(
                    marker,
                    html_content,
                    f"Required marker not found in HTML: {marker}"
                )
    
    def test_html_does_not_contain_old_preview_markers(self):
        """Test that HTML does not contain old diagnostic preview markers"""
        html_path = self.dashboard_path / "index.html"
        self.assertTrue(html_path.exists(), "index.html not found")
        
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Markers that should NOT be present (old diagnostic preview)
        forbidden_markers = [
            "REAL PHASE 8U STITCH PAYLOAD PREVIEW",
            "payload preview",
            "diagnostic preview",
            "phase8u_stitch_dashboard_preview.html"
        ]
        
        for marker in forbidden_markers:
            with self.subTest(marker=marker):
                self.assertNotIn(
                    marker,
                    html_content,
                    f"Old preview marker found in HTML (should not be present): {marker}"
                )
    
    def test_css_implements_stitch_design_system(self):
        """Test that CSS implements the Stitch design system colors"""
        css_path = self.dashboard_path / "styles.css"
        self.assertTrue(css_path.exists(), "styles.css not found")
        
        with open(css_path, 'r', encoding='utf-8') as f:
            css_content = f.read()
        
        # Required Stitch color system variables
        required_colors = [
            "--bg-primary: #111317",           # Exact Stitch background
            "--primary: #b8c3ff",             # Stitch primary color
            "--secondary: #4edea3",           # Stitch secondary (emerald green)
            "--primary-container: #2e5bff",   # Stitch primary container
        ]
        
        for color_def in required_colors:
            with self.subTest(color=color_def):
                self.assertIn(
                    color_def,
                    css_content,
                    f"Required Stitch color not found in CSS: {color_def}"
                )
    
    def test_css_implements_stitch_typography(self):
        """Test that CSS implements the Stitch typography system"""
        css_path = self.dashboard_path / "styles.css"
        self.assertTrue(css_path.exists(), "styles.css not found")
        
        with open(css_path, 'r', encoding='utf-8') as f:
            css_content = f.read()
        
        # Required Stitch typography
        required_fonts = [
            "--font-headline: 'Space Grotesk'",   # Stitch headline font
            "--font-body: 'Inter'",               # Stitch body font
            "--font-mono:",                       # Monospace for data
        ]
        
        for font_def in required_fonts:
            with self.subTest(font=font_def):
                self.assertIn(
                    font_def,
                    css_content,
                    f"Required Stitch typography not found in CSS: {font_def}"
                )
    
    def test_javascript_contains_phase8_integration(self):
        """Test that JavaScript contains Phase 8 data integration"""
        js_path = self.dashboard_path / "app.js"
        self.assertTrue(js_path.exists(), "app.js not found")
        
        with open(js_path, 'r', encoding='utf-8') as f:
            js_content = f.read()
        
        # Required Phase 8 integration markers
        required_features = [
            "Phase8Dashboard",
            "phase8/research-dashboard",
            "REAL STITCH-STYLE PHASE 8 DASHBOARD",
            "DATA SOURCE = PHASE 8U PAYLOAD/API",
            "contract_version",
            "safety"
        ]
        
        for feature in required_features:
            with self.subTest(feature=feature):
                self.assertIn(
                    feature,
                    js_content,
                    f"Required Phase 8 feature not found in JavaScript: {feature}"
                )
    
    def test_javascript_does_not_contain_mock_data_markers(self):
        """Test that JavaScript does not contain tournament/mock data markers"""
        js_path = self.dashboard_path / "app.js"
        self.assertTrue(js_path.exists(), "app.js not found")
        
        with open(js_path, 'r', encoding='utf-8') as f:
            js_content = f.read()
        
        # Forbidden mock/tournament markers
        forbidden_markers = [
            "tournament",
            "mock_tournament",
            "dummy_data",
            "fake_data",
            "test_tournament"
        ]
        
        for marker in forbidden_markers:
            with self.subTest(marker=marker):
                self.assertNotIn(
                    marker.lower(),
                    js_content.lower(),
                    f"Mock/tournament marker found in JavaScript (should not be present): {marker}"
                )
    
    def test_dashboard_supports_required_phase8_sections(self):
        """Test that dashboard supports all required Phase 8 sections"""
        html_path = self.dashboard_path / "index.html"
        self.assertTrue(html_path.exists(), "index.html not found")
        
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Required Phase 8 sections from specification
        required_sections = [
            "System Monitor",
            "Research Summary",
            "Promotion Candidates",
            "Continue Forward", 
            "Watch Only",
            "Demoted", 
            "Fail-Closed",
            "Exact Replay",
            "Calendar API",
            "Provider",
            "Safety Flag"
        ]
        
        for section in required_sections:
            with self.subTest(section=section):
                # Use regex to be flexible with exact text matching
                pattern = section.replace(" ", r"\s*")
                self.assertTrue(
                    re.search(pattern, html_content, re.IGNORECASE),
                    f"Required Phase 8 section not found: {section}"
                )
    
    def test_safety_flags_are_properly_implemented(self):
        """Test that safety flags are properly implemented"""
        js_path = self.dashboard_path / "app.js"
        self.assertTrue(js_path.exists(), "app.js not found")
        
        with open(js_path, 'r', encoding='utf-8') as f:
            js_content = f.read()
        
        # Required safety flag fields from Phase 8U specification
        required_safety_flags = [
            "paper_review_only",
            "ny_live_enabled", 
            "send_trade_unlock_changed",
            "execution_paths_changed"
        ]
        
        for flag in required_safety_flags:
            with self.subTest(flag=flag):
                self.assertIn(
                    flag,
                    js_content,
                    f"Required safety flag not found in JavaScript: {flag}"
                )
    
    def test_phase8u_payload_structure_is_supported(self):
        """Test that the dashboard supports Phase 8U payload structure"""
        if not self.payload_data:
            self.skipTest("Phase 8U payload file not available for testing")
        
        js_path = self.dashboard_path / "app.js"
        self.assertTrue(js_path.exists(), "app.js not found")
        
        with open(js_path, 'r', encoding='utf-8') as f:
            js_content = f.read()
        
        # Required payload fields that should be handled
        required_payload_fields = [
            "summary_cards",
            "calendar_budget",
            "provider_capability",
            "exact_replay_status",
            "tables",
            "phase8x_batch_progress"
        ]
        
        for field in required_payload_fields:
            with self.subTest(field=field):
                self.assertIn(
                    field,
                    js_content,
                    f"Required payload field not handled in JavaScript: {field}"
                )
    
    def test_old_diagnostic_preview_is_not_referenced(self):
        """Test that old diagnostic preview script is not referenced"""
        dashboard_files = [
            self.dashboard_path / "index.html",
            self.dashboard_path / "app.js"
        ]
        
        # Old preview script name and markers
        old_preview_markers = [
            "phase8u_open_stitch_dashboard_preview.py",
            "phase8u_stitch_dashboard_preview.html",
            "REAL PHASE 8U STITCH PAYLOAD PREVIEW",
            "NOT FALLBACK STATIC HTML"
        ]
        
        for file_path in dashboard_files:
            if not file_path.exists():
                continue
                
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            for marker in old_preview_markers:
                with self.subTest(file=file_path.name, marker=marker):
                    self.assertNotIn(
                        marker,
                        content,
                        f"Old preview reference found in {file_path.name}: {marker}"
                    )
    
    def test_dashboard_title_indicates_real_dashboard(self):
        """Test that dashboard title clearly indicates it's the real dashboard"""
        html_path = self.dashboard_path / "index.html"
        self.assertTrue(html_path.exists(), "index.html not found")
        
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Check HTML title tag
        title_match = re.search(r'<title>(.*?)</title>', html_content, re.IGNORECASE)
        self.assertTrue(title_match, "No title tag found in HTML")
        
        title_text = title_match.group(1)
        
        # Title should NOT indicate it's a preview
        forbidden_title_words = ["preview", "diagnostic", "test", "mock"]
        for word in forbidden_title_words:
            self.assertNotIn(
                word.lower(),
                title_text.lower(),
                f"Title contains forbidden word indicating preview: {word}"
            )
        
        # Title should indicate it's the real dashboard
        required_title_indicators = ["Phase 8", "Backtest", "Automation"]
        title_has_indicator = any(
            indicator.lower() in title_text.lower() 
            for indicator in required_title_indicators
        )
        self.assertTrue(
            title_has_indicator,
            f"Title does not contain real dashboard indicators: {title_text}"
        )
    
    def test_no_static_fallback_references(self):
        """Test that there are no references to old static fallback files"""
        dashboard_files = list(self.dashboard_path.glob("*"))
        
        # Static fallback paths that should not be referenced
        forbidden_references = [
            "ARTIFACTS/performance/research_dashboard/index.html",
            "research_dashboard/index.html",
            "static fallback",
            "fallback static HTML"
        ]
        
        for file_path in dashboard_files:
            if file_path.suffix not in ['.html', '.js', '.css']:
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                for reference in forbidden_references:
                    with self.subTest(file=file_path.name, reference=reference):
                        self.assertNotIn(
                            reference,
                            content,
                            f"Forbidden static fallback reference found in {file_path.name}: {reference}"
                        )
            except (UnicodeDecodeError, PermissionError):
                # Skip binary or inaccessible files
                continue

def run_tests() -> Tuple[bool, List[str]]:
    """
    Run all Phase 8V validation tests
    
    Returns:
        Tuple of (all_passed, error_messages)
    """
    # Capture test output
    import io
    from contextlib import redirect_stderr, redirect_stdout
    
    test_output = io.StringIO()
    test_errors = io.StringIO()
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(Phase8VStitchVisualDashboardTests)
    
    # Run tests with custom result collector
    with redirect_stdout(test_output), redirect_stderr(test_errors):
        runner = unittest.TextTestRunner(
            stream=test_output,
            verbosity=2,
            failfast=False
        )
        result = runner.run(suite)
    
    # Collect error messages
    error_messages = []
    if result.failures:
        for test, traceback in result.failures:
            error_messages.append(f"FAIL: {test} - {traceback}")
    
    if result.errors:
        for test, traceback in result.errors:
            error_messages.append(f"ERROR: {test} - {traceback}")
    
    # Add captured output to errors if there were issues
    captured_output = test_output.getvalue()
    captured_errors = test_errors.getvalue()
    
    if captured_errors:
        error_messages.append(f"Test Errors: {captured_errors}")
    
    all_passed = result.wasSuccessful()
    
    return all_passed, error_messages


if __name__ == "__main__":
    print("🧪 Running Phase 8V Stitch Visual Dashboard Validation Tests...")
    print("=" * 70)
    
    # Run the tests
    all_passed, errors = run_tests()
    
    print("\n" + "=" * 70)
    if all_passed:
        print("✅ ALL TESTS PASSED - Phase 8V dashboard validation successful!")
        print("\n✅ VERIFICATION COMPLETE:")
        print("   • Real Stitch-style dashboard implemented")
        print("   • Old diagnostic preview markers absent")
        print("   • Phase 8U payload integration verified")
        print("   • Stitch design system colors/typography confirmed")
        print("   • Safety flags properly implemented")
        print("   • No static fallback references found")
        sys.exit(0)
    else:
        print("❌ TESTS FAILED - Phase 8V dashboard validation issues found!")
        print("\n❌ VALIDATION ERRORS:")
        for i, error in enumerate(errors, 1):
            print(f"   {i}. {error}")
        print("\n🛠️  Please fix these issues before proceeding with Phase 8V.")
        sys.exit(1)