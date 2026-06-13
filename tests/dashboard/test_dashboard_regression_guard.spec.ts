import { test, expect } from '@playwright/test';

const DASHBOARD_URL = process.env.DASHBOARD_URL || 'http://127.0.0.1:8787';

test.describe('Dashboard Regression Guard', () => {
  test('MUST serve only React dashboard - block legacy HTML', async ({ page }) => {
    // Navigate to dashboard
    await page.goto(DASHBOARD_URL);
    await page.waitForLoadState('networkidle');

    // CRITICAL: Verify React app is loaded
    const root = page.locator('#root');
    await expect(root).toBeVisible({ timeout: 10000 });

    // CRITICAL: Verify React dashboard structure
    const header = page.locator('header');
    await expect(header).toBeVisible();
    
    // CRITICAL: Verify PAPER mode badge exists
    const paperBadge = page.locator('text=/PAPER/i').first();
    await expect(paperBadge).toBeVisible();

    // CRITICAL: Verify navigation tabs exist (React uses buttons)
    const navButtons = page.locator('button').filter({ hasText: /Terminal|Mesh|Signals|News/i });
    const buttonCount = await navButtons.count();
    expect(buttonCount).toBeGreaterThan(0);

    // CRITICAL: Verify legacy dashboard elements DO NOT exist
    const oldDashboardSelectors = [
      'text=FXG AI TRADING',  // Old dashboard title
      '#old-dashboard-root',  // Legacy HTML dashboard
      '.legacy-dashboard',    // Legacy HTML dashboard class
      'forensic_command',     // Legacy HTML file reference
      '#forensic-command',    // Legacy HTML ID
    ];

    for (const selector of oldDashboardSelectors) {
      const element = page.locator(selector);
      const count = await element.count();
      expect(count).toBe(0);
    }

    // Verify page title (React dashboard)
    const title = await page.title();
    expect(title).toBeTruthy();
    // Should NOT be old dashboard title
    expect(title.toLowerCase()).not.toContain('fxg ai trading');
    // Should be React app title
    expect(title.toLowerCase()).toContain('fxg-dashboard');
    
    // Verify no MockBackend in bundle
    const pageContent = await page.content();
    expect(pageContent.toLowerCase()).not.toContain('mockbackend');
    expect(pageContent.toLowerCase()).not.toContain('forensic_command.html');
  });

  test('MUST return correct no-cache headers', async ({ page }) => {
    const response = await page.goto(DASHBOARD_URL);
    
    if (!response) {
      throw new Error('No response received');
    }

    // Verify critical no-cache headers
    const headers = response.headers();
    
    expect(headers['cache-control']).toContain('no-store');
    expect(headers['cache-control']).toContain('no-cache');
    expect(headers['cache-control']).toContain('max-age=0');
    expect(headers['pragma']).toBe('no-cache');
    
    // Verify UI version header exists (content hash)
    expect(headers['x-ui-version']).toBeTruthy();
  });

  test('MUST contain transparency features', async ({ page }) => {
    await page.goto(DASHBOARD_URL);
    await page.waitForLoadState('networkidle');

    // Verify React dashboard transparency features are present
    // React dashboard shows transparency in a different structure
    const transparencyElements = [
      'text=/READY|WAITING|BLOCKED/i',  // Readiness status text
      'text=/SESSION REGIME GATE/i',    // Session gate section
      'text=/SYSTEM HEALTH/i',          // System health section
      'text=/PAPER|LIVE/i',             // Mode indicator
    ];

    for (const selector of transparencyElements) {
      const element = page.locator(selector);
      await expect(element.first()).toBeVisible({ timeout: 5000 });
    }
  });

  test('MUST respond correctly to API endpoint', async ({ page }) => {
    // Check session-regime-gate snapshot endpoint
    const response = await page.request.get(`${DASHBOARD_URL}/api/session-regime-gate/snapshot`);
    
    expect(response.status()).toBe(200);
    
    const data = await response.json();
    
    // Verify response structure
    expect(data).toHaveProperty('data');
    expect(data).toHaveProperty('truth');
    
    const payload = data.data;
    
    // Verify transparency fields exist
    expect(payload).toHaveProperty('readiness');
    expect(payload).toHaveProperty('trade_block_reason');
    expect(payload).toHaveProperty('block_details');
    expect(payload).toHaveProperty('next_session');
    
    // Verify readiness is valid
    expect(['READY', 'WAITING', 'BLOCKED']).toContain(payload.readiness || 'WAITING');
  });
});
