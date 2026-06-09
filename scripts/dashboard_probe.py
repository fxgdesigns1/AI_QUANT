import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from playwright.async_api import async_playwright, Page

# Use the public URL for authenticated probing
BASE_URL = "https://alpha.fxgdesigns.co.uk"

# Endpoints required for dashboard health
REQUIRED_ENDPOINTS = [
    "/api/status",
    "/api/market/prices",
    "/api/news/status",
    "/api/news",
    "/api/trades/active",
    "/api/trades/pending",
    "/api/signals/pending",
    "/api/strategies/overview",
    "/api/performance/summary",
    "/api/v1/outlook/daily",
    "/api/v1/scanner/structural",
    "/api/v1/audit",
    "/api/journal/trades",
]

# Dashboard tabs (DOM IDs)
DASHBOARD_TABS = [
    "terminal",
    "outlook",
    "scanner",
    "mesh",
    "journal",
    "audit",
    "news",
    "reports",
    "strategies",
    "trades",  # This maps to "Active Trades" tab
]

class DashboardProbe:
    def __init__(self, base_url: str = BASE_URL, headless: bool = False, storage_state: Optional[str] = None, save_storage_state: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.headless = headless
        self.storage_state = storage_state
        self.save_storage_state = save_storage_state

        ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        self.run_id = ts
        self.artifacts_dir = Path("artifacts") / "dashboard_probe" / ts
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

        self.console_errors: List[Dict] = []
        self.console_warnings: List[Dict] = []
        self.page_errors: List[str] = []
        self.request_failures: List[Dict] = []
        self.api_responses: Dict[str, Dict] = {}

        self.results: Dict = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "run_id": self.run_id,
            "base_url": self.base_url,
            "endpoints": {},
            "dashboard_sections": {},
            "console": {"errors": [], "warnings": [], "page_errors": []},
            "network": {"request_failures": [], "api_responses": {}},
            "screenshots": {},
            "issues": [],
            "summary": {},
        }

    def _attach_listeners(self, page: Page):
        # Console messages
        def on_console(msg):
            entry = {
                "type": msg.type,
                "text": msg.text,
                "location": getattr(msg, "location", None),
            }
            if msg.type == "error":
                self.console_errors.append(entry)
            elif msg.type == "warning":
                self.console_warnings.append(entry)

        page.on("console", on_console)

        # Unhandled exceptions
        page.on("pageerror", lambda exc: self.page_errors.append(str(exc)))

        # Request failures
        def on_request_failed(req):
            url = req.url
            if "/api/" in url or url.rstrip("/").endswith("/api"):
                self.request_failures.append({
                    "url": url,
                    "method": req.method,
                    "failure": (req.failure or {}),
                })

        page.on("requestfailed", on_request_failed)

        # Track API response statuses for /api
        async def on_response(resp):
            try:
                url = resp.url
                if "/api/" not in url and not url.rstrip("/").endswith("/api"):
                    return
                status = resp.status
                # store only first-seen response per path+query to keep results bounded
                key = url
                if key not in self.api_responses:
                    self.api_responses[key] = {"status": status}
                    if status >= 400:
                        # try capture short body for diagnostics
                        try:
                            body = await resp.text()
                            self.api_responses[key]["body_preview"] = body[:500]
                        except Exception:
                            pass
            except Exception:
                return

        page.on("response", on_response)

    async def _wait_for_dashboard_ready(self, page: Page) -> bool:
        """Returns True if dashboard nav appears."""
        try:
            await page.wait_for_selector("#nav-terminal", timeout=8000)
            return True
        except Exception:
            return False

    async def _ensure_logged_in(self, page: Page):
        """Navigate and pause for user login if required."""
        await page.goto(self.base_url, wait_until="domcontentloaded", timeout=45000)
        await asyncio.sleep(1)

        # If we don't see the dashboard nav quickly, we assume auth gate.
        if not await self._wait_for_dashboard_ready(page):
            print("⚠️  Auth gate detected (Cloudflare/Google). When you see the dashboard after login, return here and press Enter.")
            if not self.headless:
                input()
            else:
                print("Headless mode: cannot pause for login. Continuing and hoping storage_state works...")
            
            # After user confirms, wait for nav
            if not await self._wait_for_dashboard_ready(page):
                raise RuntimeError("Dashboard nav not detected after login. Still blocked by auth or page not loaded.")

        # Save storage state if requested (enables headless runs later)
        if self.save_storage_state:
            try:
                state_path = Path(self.save_storage_state)
                state_path.parent.mkdir(parents=True, exist_ok=True)
                await page.context.storage_state(path=str(state_path))
                print(f"✅ Saved storage_state to {state_path}")
            except Exception as e:
                print(f"⚠️  Failed to save storage_state: {e}")

    async def test_endpoint_via_fetch(self, page: Page, endpoint: str) -> Dict:
        """Test endpoint via JS fetch, returning status + parsed JSON (or text preview)."""
        try:
            result = await page.evaluate(
                """
                async (endpoint) => {
                  try {
                    const resp = await fetch(endpoint, { credentials: 'same-origin' });
                    const ct = resp.headers.get('content-type') || '';
                    let payload = null;
                    if (ct.includes('application/json')) {
                      payload = await resp.json();
                      return { ok: resp.ok, status: resp.status, content_type: ct, data: payload };
                    }
                    const text = await resp.text();
                    return { ok: resp.ok, status: resp.status, content_type: ct, text_preview: text.slice(0, 500) };
                  } catch (e) {
                    return { ok: false, error: String(e) };
                  }
                }
                """,
                endpoint,
            )
            return result
        except Exception as e:
            return {"ok": False, "error": str(e)[:200]}

    async def _click_tab(self, page: Page, tab_id: str):
        # Primary selector convention
        tab_selector = f"#nav-{tab_id}"
        if await page.query_selector(tab_selector):
            await page.click(tab_selector)
            return

        # Fallback: try data-tab attribute
        fallback = f"[data-tab='{tab_id}']"
        if await page.query_selector(fallback):
            await page.click(fallback)
            return

        raise RuntimeError(f"Tab nav not found for '{tab_id}' using selectors {tab_selector} or {fallback}")

    async def test_dashboard_section(self, page: Page, tab_id: str) -> Dict:
        """Click into a tab, wait, snapshot state, and detect common failure patterns."""
        try:
            await self._click_tab(page, tab_id)
            await asyncio.sleep(1.5)

            content_selector = f"#tab-{tab_id}"
            try:
                await page.wait_for_selector(content_selector, timeout=8000)
            except:
                return {"ok": False, "error": f"Tab content {content_selector} not found"}
                
            content = await page.query_selector(content_selector)
            if not content:
                return {"ok": False, "error": f"Tab content {content_selector} not found"}

            # Look for common inline error banners
            error_elements = await page.query_selector_all(".text-red-500, .text-red-400, .chip-danger, .border-red-500")
            errors = []
            for el in error_elements[:8]:
                try:
                    t = (await el.inner_text()).strip()
                    if t:
                        errors.append(t)
                except Exception:
                    continue

            # Look for obvious loading indicators
            loading_elements = await page.query_selector_all(".animate-spin")
            is_loading = len(loading_elements) > 0

            # Pull a short preview of visible text
            content_text = (await content.inner_text()) or ""
            preview = content_text.replace("\n", " ").strip()[:600]

            # Screenshot
            shot_path = self.artifacts_dir / f"tab_{tab_id}.png"
            try:
                await page.screenshot(path=str(shot_path), full_page=True)
                self.results["screenshots"][tab_id] = str(shot_path)
            except Exception:
                pass

            return {
                "ok": True,
                "loaded": not is_loading,
                "errors": errors or None,
                "content_preview": preview,
            }
        except Exception as e:
            return {"ok": False, "error": str(e)[:300]}

    def _derive_issues(self):
        """Infer actionable issues from endpoint/tab outputs."""
        issues = []

        # Endpoint-level failures
        for ep, r in self.results.get("endpoints", {}).items():
            if not r.get("ok"):
                issues.append({
                    "severity": "critical",
                    "area": "endpoint",
                    "id": f"endpoint:{ep}",
                    "symptom": f"Endpoint failed: {ep}",
                    "detail": r.get("error") or f"HTTP {r.get('status')}",
                })

        # Specific known dashboard problems
        active = self.results.get("endpoints", {}).get("/api/trades/active", {})
        if active.get("ok") and isinstance(active.get("data"), dict):
            data = active.get("data")
            # Heuristic: if accounts array exists, check if identifiers exist
            accounts = None
            for k in ("accounts", "data", "items"):
                if isinstance(data.get(k), list):
                    accounts = data.get(k)
                    break
            if accounts is not None and len(accounts) > 0:
                sample = accounts[0]
                if isinstance(sample, dict):
                    if not any(key in sample for key in ("account_id_masked", "account_id", "account_suffix")):
                        issues.append({
                            "severity": "critical",
                            "area": "active_trades",
                            "id": "active_trades:missing_account_identifier",
                            "symptom": "Active trades data missing account identifier fields",
                            "detail": f"Sample keys: {sorted(list(sample.keys()))[:30]}",
                        })

        news = self.results.get("endpoints", {}).get("/api/news", {})
        if news.get("ok") and isinstance(news.get("data"), dict):
            nd = news.get("data")
            enabled = nd.get("enabled")
            if enabled is False or nd.get("integration_disabled") is True:
                issues.append({
                    "severity": "warning",
                    "area": "news",
                    "id": "news:disabled",
                    "symptom": "News integration disabled via config",
                    "detail": "Backend reports news disabled; enable flag in runtime config.",
                })

        scanner = self.results.get("endpoints", {}).get("/api/v1/scanner/structural", {})
        if scanner.get("ok") and isinstance(scanner.get("data"), dict):
            sd = scanner.get("data")
            # Look for repeated insufficient history markers
            txt = json.dumps(sd)[:4000].lower()
            if "insufficient history" in txt:
                issues.append({
                    "severity": "warning",
                    "area": "structural_scanner",
                    "id": "scanner:insufficient_history",
                    "symptom": "Structural scanner reports insufficient history",
                    "detail": "Likely candle history fetch/requirements mismatch.",
                })

        self.results["issues"] = issues

    def _write_markdown_report(self):
        report_path = Path("docs") / "DASHBOARD_PROBE_REPORT.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)

        s = self.results.get("summary", {})
        lines = []
        lines.append("# Dashboard Probe Report\n")
        lines.append(f"**Run ID:** {self.run_id}\n")
        lines.append(f"**Timestamp (UTC):** {self.results.get('timestamp')}\n")
        lines.append(f"**Base URL:** {self.base_url}\n")
        lines.append("\n---\n")

        lines.append("## Summary\n")
        lines.append(f"- Endpoints OK: **{s.get('endpoints_ok', 0)}**/**{s.get('endpoints_total', 0)}** ({s.get('endpoints_pct', 0)}%)\n")
        lines.append(f"- Tabs OK: **{s.get('sections_ok', 0)}**/**{s.get('sections_total', 0)}** ({s.get('sections_pct', 0)}%)\n")
        lines.append(f"- Console errors: **{s.get('console_errors_count', 0)}**\n")
        lines.append(f"- Page errors: **{s.get('page_errors_count', 0)}**\n")
        lines.append(f"- Network request failures: **{s.get('request_failures_count', 0)}**\n")

        lines.append("\n## Issues (Derived)\n")
        if self.results.get("issues"):
            for it in self.results["issues"]:
                lines.append(f"- **{it['severity'].upper()}** `{it['id']}` — {it['symptom']}\n  - {it.get('detail','')}\n")
        else:
            lines.append("- No derived issues (check raw artifacts).\n")

        lines.append("\n## Endpoint Results\n")
        for ep, r in self.results.get("endpoints", {}).items():
            ok = r.get("ok")
            status = r.get("status", "N/A")
            lines.append(f"- {'✅' if ok else '❌'} `{ep}` — {status}\n")
            if not ok:
                lines.append(f"  - Error: {r.get('error')}\n")

        lines.append("\n## Tab Results + Screenshots\n")
        for tab, r in self.results.get("dashboard_sections", {}).items():
            ok = r.get("ok")
            lines.append(f"- {'✅' if ok else '❌'} `{tab}`\n")
            if ok:
                if r.get("errors"):
                    lines.append(f"  - UI Errors: {r['errors'][:5]}\n")
                if tab in self.results.get("screenshots", {}):
                    lines.append(f"  - Screenshot: `{self.results['screenshots'][tab]}`\n")
            else:
                lines.append(f"  - Error: {r.get('error')}\n")

        lines.append("\n## Evidence Artifacts\n")
        lines.append(f"- Raw JSON: `{self.artifacts_dir / 'dashboard_probe_results.json'}`\n")
        lines.append("\n## Console + Network\n")
        lines.append(f"- Console errors captured: {len(self.console_errors)}\n")
        lines.append(f"- Console warnings captured: {len(self.console_warnings)}\n")
        lines.append(f"- Page errors captured: {len(self.page_errors)}\n")
        lines.append(f"- Request failures captured: {len(self.request_failures)}\n")

        report_path.write_text("".join(lines), encoding="utf-8")
        return report_path

    async def probe(self) -> Dict:
        """Run comprehensive probe."""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context_kwargs = {}
            if self.storage_state:
                context_kwargs["storage_state"] = self.storage_state
            context = await browser.new_context(**context_kwargs)
            page = await context.new_page()

            # Attach listeners BEFORE navigating
            self._attach_listeners(page)

            print(f"Navigating to {self.base_url}...")
            await self._ensure_logged_in(page)

            # Smoke screenshot after login
            try:
                shot_path = self.artifacts_dir / "dashboard_after_login.png"
                await page.screenshot(path=str(shot_path), full_page=True)
                self.results["screenshots"]["after_login"] = str(shot_path)
            except Exception:
                pass

            print("\n=== Testing API Endpoints (fetch, same-origin) ===")
            for endpoint in REQUIRED_ENDPOINTS:
                print(f"Testing {endpoint}...")
                result = await self.test_endpoint_via_fetch(page, endpoint)
                # bound payload size in results to keep JSON manageable
                if isinstance(result, dict) and isinstance(result.get("data"), (dict, list)):
                    # truncate very large payloads
                    try:
                        raw = json.dumps(result["data"])
                        if len(raw) > 20000:
                            result["data_truncated"] = True
                            result["data_preview"] = raw[:20000]
                            result.pop("data", None)
                    except Exception:
                        pass
                self.results["endpoints"][endpoint] = result

                status_icon = "✅" if result.get("ok") else "❌"
                msg = result.get("error") or "OK"
                print(f"  {status_icon} {endpoint}: {result.get('status', 'N/A')} - {str(msg)[:80]}")

            print("\n=== Testing Dashboard Tabs ===")
            for tab_id in DASHBOARD_TABS:
                print(f"Testing {tab_id} tab...")
                result = await self.test_dashboard_section(page, tab_id)
                self.results["dashboard_sections"][tab_id] = result
                status_icon = "✅" if result.get("ok") else "❌"
                print(f"  {status_icon} {tab_id}: {result.get('error', 'OK')[:80]}")

            # Finalize console/network capture
            self.results["console"]["errors"] = self.console_errors
            self.results["console"]["warnings"] = self.console_warnings
            self.results["console"]["page_errors"] = self.page_errors
            self.results["network"]["request_failures"] = self.request_failures
            self.results["network"]["api_responses"] = self.api_responses

            # Summaries
            endpoint_ok = sum(1 for r in self.results["endpoints"].values() if r.get("ok"))
            endpoint_total = len(self.results["endpoints"])
            sections_ok = sum(1 for r in self.results["dashboard_sections"].values() if r.get("ok"))
            sections_total = len(self.results["dashboard_sections"])

            self.results["summary"] = {
                "endpoints_ok": endpoint_ok,
                "endpoints_total": endpoint_total,
                "endpoints_pct": round((endpoint_ok / endpoint_total * 100), 1) if endpoint_total else 0,
                "sections_ok": sections_ok,
                "sections_total": sections_total,
                "sections_pct": round((sections_ok / sections_total * 100), 1) if sections_total else 0,
                "console_errors_count": len(self.console_errors),
                "page_errors_count": len(self.page_errors),
                "request_failures_count": len(self.request_failures),
                "api_non2xx_count": sum(1 for _, v in self.api_responses.items() if v.get("status", 200) >= 400),
            }

            # Derive issues + write outputs
            self._derive_issues()

            # Save raw JSON
            raw_path = self.artifacts_dir / "dashboard_probe_results.json"
            raw_path.write_text(json.dumps(self.results, indent=2), encoding="utf-8")
            print(f"\n✅ Raw results saved: {raw_path}")

            # Write markdown report
            report_path = self._write_markdown_report()
            print(f"✅ Report written: {report_path}")

            await browser.close()

        return self.results

async def main():
    parser = argparse.ArgumentParser(description="Dashboard Probe Script")
    parser.add_argument("--url", default=BASE_URL, help="Dashboard URL")
    parser.add_argument("--headless", action="store_true", help="Run headless (requires storage_state)")
    parser.add_argument("--storage-state", default=None, help="Path to Playwright storage_state.json to reuse auth")
    parser.add_argument("--save-storage-state", default="artifacts/dashboard_probe/storage_state.json", help="Where to save storage_state after interactive login")
    args = parser.parse_args()

    probe = DashboardProbe(
        base_url=args.url,
        headless=args.headless,
        storage_state=args.storage_state,
        save_storage_state=args.save_storage_state if not args.headless else None,
    )
    results = await probe.probe()

    # Exit non-zero if any endpoints failed or console/page errors occurred
    s = results.get("summary", {})
    hard_fail = (s.get("endpoints_ok", 0) < s.get("endpoints_total", 0)) or (s.get("console_errors_count", 0) > 0) or (s.get("page_errors_count", 0) > 0)
    return 1 if hard_fail else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
