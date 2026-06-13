import { test, expect } from '@playwright/test';

/**
 * Dashboard Truth Verification Tests
 * 
 * Verifies that the ALPHA dashboard:
 * 1. Renders nothing not present in backend truth files
 * 2. Shows MISSING for missing fields
 * 3. Shows STALE for stale data
 * 4. Makes no requests to non-backend endpoints
 * 5. Displays embargo state verbatim
 * 6. Shows explicit error states when truth sources are missing
 */

const DASHBOARD_URL = process.env.DASHBOARD_URL || 'https://alpha-dashboard.fxg.internal';
const BACKEND_API_PATTERN = /^\/api\//;

test.describe('Dashboard Truth Lockdown', () => {
  test('page loads without auth redirect', async ({ page }) => {
    await page.goto(DASHBOARD_URL, { waitUntil: 'networkidle' });
    
    // Check URL is still the dashboard URL (no redirect to google login)
    const url = page.url();
    expect(url).not.toContain('accounts.google.com');
    expect(url).not.toContain('cloudflareaccess.com');
    expect(url).toContain(new URL(DASHBOARD_URL).hostname);
    
    // Verify dashboard header is visible (confirms we're on the dashboard, not login page)
    await expect(page.locator('text=AI-QUANT')).toBeVisible();
  });

  test('all network requests go to backend API endpoints only', async ({ page }) => {
    const nonBackendRequests: string[] = [];
    
    // Intercept all network requests
    page.on('request', (request) => {
      const url = new URL(request.url());
      const path = url.pathname;
      
      // Allow backend API calls, static assets, and same-origin requests
      if (
        !BACKEND_API_PATTERN.test(path) &&
        !path.startsWith('/static/') &&
        !path.startsWith('/assets/') &&
        !path.endsWith('.js') &&
        !path.endsWith('.css') &&
        !path.endsWith('.json') &&
        !path.endsWith('.ico') &&
        !path.endsWith('.svg') &&
        !path.endsWith('.png') &&
        !path.endsWith('.jpg') &&
        !path.endsWith('.woff') &&
        !path.endsWith('.woff2') &&
        !path.endsWith('.ttf') &&
        path !== '/' &&
        !path.startsWith('/_') &&
        !url.hostname.includes(new URL(DASHBOARD_URL).hostname) &&
        !url.hostname.includes('localhost') &&
        !url.hostname.includes('127.0.0.1')
      ) {
        // External API call detected
        nonBackendRequests.push(`${request.method()} ${url.toString()}`);
      }
    });

    await page.goto(DASHBOARD_URL, { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000); // Wait for all initial requests

    // Fail if any non-backend requests were made
    expect(nonBackendRequests).toEqual([]);
  });

  test('missing fields show MISSING indicator', async ({ page }) => {
    await page.goto(DASHBOARD_URL, { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // Mock API responses with missing fields
    await page.route('**/api/status', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          data: {
            mode: null, // Missing
            execution_enabled: false,
            active_strategy_key: null, // Missing
            accounts_loaded: null, // Missing
            last_scan_at: null, // Missing
          },
          truth: {
            complete: true,
            source: 'status_snapshot',
          },
        }),
      });
    });

    await page.reload({ waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);

    // Check that MISSING appears in the UI
    const pageText = await page.textContent('body');
    expect(pageText).toContain('MISSING');
  });

  test('stale data shows STALE indicator', async ({ page }) => {
    await page.goto(DASHBOARD_URL, { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // Mock API response with stale data (freshness_ms > 120000)
    await page.route('**/api/status', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          data: {
            mode: 'paper',
            execution_enabled: false,
            active_strategy_key: 'test_strategy',
            accounts_loaded: 1,
            last_scan_at: '2024-01-01T00:00:00Z',
          },
          truth: {
            complete: true,
            source: 'status_snapshot',
            freshness_ms: 300000, // 5 minutes - stale
          },
        }),
      });
    });

    await page.reload({ waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);

    // Check that STALE appears in the UI
    const pageText = await page.textContent('body');
    expect(pageText).toContain('STALE');
  });

  test('news panel shows NO_NEWS_INGESTED when snapshot.recent_news is empty', async ({ page }) => {
    await page.goto(DASHBOARD_URL, { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // Mock news API response with empty news array and snapshot source
    await page.route('**/api/news', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          data: {
            news: [],
            source_mode: 'snapshot',
          },
          truth: {
            complete: true,
            source: 'status_snapshot',
          },
        }),
      });
    });

    // Navigate to News tab
    await page.click('button:has-text("News")');
    await page.waitForTimeout(1000);

    // Check that NO_NEWS_INGESTED appears
    const pageText = await page.textContent('body');
    expect(pageText).toContain('NO_NEWS_INGESTED');
  });

  test('news panel rejects non-snapshot sources', async ({ page }) => {
    await page.goto(DASHBOARD_URL, { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // Mock news API response with provider source (not snapshot)
    await page.route('**/api/news', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          data: {
            news: [{ title: 'Test News', summary: 'Test', ts_utc: Date.now() / 1000 }],
            source_mode: 'provider_registry_cached', // Not snapshot
          },
          truth: {
            complete: true,
            source: 'news_provider',
          },
        }),
      });
    });

    // Navigate to News tab
    await page.click('button:has-text("News")');
    await page.waitForTimeout(1000);

    // Check that NON-SNAPSHOT SOURCE warning appears
    const pageText = await page.textContent('body');
    expect(pageText).toContain('NON-SNAPSHOT SOURCE');
  });

  test('execution_reason displayed when execution_enabled=false', async ({ page }) => {
    await page.goto(DASHBOARD_URL, { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // Mock status API with execution disabled and reason
    await page.route('**/api/status', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          data: {
            mode: 'paper',
            execution_enabled: false,
            execution_guard: {
              allowed: false,
              reason_code: 'PAPER_MODE_ONLY',
              mode: 'paper',
            },
            active_strategy_key: 'test_strategy',
            accounts_loaded: 1,
            last_scan_at: new Date().toISOString(),
          },
          truth: {
            complete: true,
            source: 'status_snapshot',
          },
        }),
      });
    });

    await page.reload({ waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);

    // Check that reason code appears
    const pageText = await page.textContent('body');
    expect(pageText).toContain('REASON');
    expect(pageText).toContain('PAPER_MODE_ONLY');
  });

  test('embargo state displayed verbatim', async ({ page }) => {
    await page.goto(DASHBOARD_URL, { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // Mock session API with embargo active
    await page.route('**/api/session-regime-gate/snapshot', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          data: {
            readiness: 'BLOCKED',
            readiness_score: 30,
            current_session: 'london',
            last_known_regime: 'TRENDING',
            block_details: {
              is_embargo: true,
              embargo_triggers: 'High impact news event in 15 minutes',
              news_state: 'embargo',
              roadmap_aligned: false,
            },
            trade_block_reason: 'Embargo active',
            next_session: {
              next_tradable_session: 'new_york',
              countdown_seconds: 3600,
            },
          },
          truth: {
            complete: true,
            source: 'session_regime_gate_panel',
          },
        }),
      });
    });

    await page.reload({ waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);

    // Check that embargo state appears verbatim
    const pageText = await page.textContent('body');
    expect(pageText).toContain('EMBARGO ACTIVE');
    expect(pageText).toContain('High impact news event in 15 minutes');
  });

  test('strategy readiness shows READINESS_FILE_MISSING when file missing', async ({ page }) => {
    await page.goto(DASHBOARD_URL, { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // Mock readiness API with no data
    await page.route('**/api/readiness', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          data: null,
          truth: {
            complete: false,
            source: 'control_plane',
          },
        }),
      });
    });

    // Navigate to Readiness tab
    await page.click('button:has-text("Readiness")');
    await page.waitForTimeout(1000);

    // Check that READINESS_FILE_MISSING appears
    const pageText = await page.textContent('body');
    expect(pageText).toContain('READINESS_FILE_MISSING');
  });

  test('negative truth test: missing status snapshot shows explicit error', async ({ page }) => {
    await page.goto(DASHBOARD_URL, { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // Mock status API to return null/empty
    await page.route('**/api/status', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          data: null,
          truth: {
            complete: false,
            source: 'status_snapshot',
            warnings: ['No status snapshot available'],
          },
        }),
      });
    });

    await page.reload({ waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);

    // Check that explicit error state is shown
    const pageText = await page.textContent('body');
    expect(pageText).toContain('NO BACKEND FACT AVAILABLE');
    expect(pageText).toContain('Status endpoint returned no data');
  });

  test('all visible values match snapshot JSON structure', async ({ page }) => {
    await page.goto(DASHBOARD_URL, { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // Capture actual API responses
    const apiResponses: Record<string, any> = {};

    page.on('response', async (response) => {
      const url = response.url();
      if (BACKEND_API_PATTERN.test(new URL(url).pathname)) {
        try {
          const json = await response.json();
          apiResponses[new URL(url).pathname] = json;
        } catch (e) {
          // Not JSON, skip
        }
      }
    });

    await page.waitForTimeout(3000); // Wait for all API calls

    // Verify that status data is displayed correctly
    if (apiResponses['/api/status']?.data) {
      const statusData = apiResponses['/api/status'].data;
      const pageText = await page.textContent('body');

      // If mode exists in snapshot, it should appear in UI (or MISSING if null)
      if (statusData.mode !== undefined) {
        expect(pageText).toMatch(new RegExp(statusData.mode.toUpperCase() + '|MISSING'));
      }

      // If execution_enabled exists, it should appear
      if (statusData.execution_enabled !== undefined) {
        expect(pageText).toMatch(/EXECUTION (ON|OFF)/);
      }
    }
  });

  test('no frontend-computed state or optimistic loading', async ({ page }) => {
    await page.goto(DASHBOARD_URL, { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // Check that no mock/sample data is present
    const pageText = await page.textContent('body');

    // These should NOT appear (they would indicate frontend simulation)
    const forbiddenPatterns = [
      /Sample Account/i,
      /Demo Trade/i,
      /Mock Signal/i,
      /Placeholder/i,
      /Coming Soon/i,
      /Example/i,
    ];

    for (const pattern of forbiddenPatterns) {
      expect(pageText).not.toMatch(pattern);
    }

    // Verify truth envelope notice is present
    expect(pageText).toContain('TRUTH ENVELOPE');
    expect(pageText).toContain('strictly sourced from backend snapshots');
  });
});
