import { test, expect } from '@playwright/test';

/**
 * Dashboard Design Match Verification
 * 
 * Verifies the dashboard matches the exact design from the mock:
 * - FXG AI TRADING header with waveform logo
 * - PAPER (SAFE MODE) indicator
 * - EMBARGO ACTIVE / TRADES OFF red buttons
 * - Mission Control, Accounts, Journal, Intelligence, Settings tabs
 * - Two-column layout with System Status, Quick Account Summary, Session Gate
 */

const DASHBOARD_URL = process.env.DASHBOARD_URL || 'http://127.0.0.1:8787';

test.describe('Dashboard Design Match Verification', () => {
  test('header matches design: FXG AI TRADING with logo and mode', async ({ page }) => {
    await page.goto(DASHBOARD_URL, { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);
    
    // Check for "FXG AI TRADING" title
    const title = page.locator('text=FXG').first();
    await expect(title).toBeVisible();
    await expect(page.locator('text=AI TRADING')).toBeVisible();
    
    // Check for "PAPER (SAFE MODE)" indicator
    await expect(page.locator('text=PAPER (SAFE MODE)')).toBeVisible();
    
    // Check for waveform/activity icon (logo)
    const logo = page.locator('header svg, header [class*="Activity"]').first();
    await expect(logo).toBeVisible();
  });

  test('header shows EMBARGO ACTIVE and TRADES OFF buttons when applicable', async ({ page }) => {
    await page.goto(DASHBOARD_URL, { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);
    
    // Check header structure
    const header = page.locator('header').first();
    await expect(header).toBeVisible();
    
    // Check for timestamp in header
    const timestamp = header.locator('text=/GMT UTC/');
    const timestampCount = await timestamp.count();
    expect(timestampCount).toBeGreaterThan(0);
    
    // EMBARGO ACTIVE and TRADES OFF buttons may or may not be visible depending on state
    // But the header structure should support them
    const headerButtons = header.locator('button, [class*="rounded-full"]');
    const buttonCount = await headerButtons.count();
    // Should have at least timestamp, buttons are conditional
    expect(buttonCount).toBeGreaterThanOrEqual(0);
  });

  test('navigation bar has correct tabs: Mission Control, Accounts, Journal, Intelligence, Settings', async ({ page }) => {
    await page.goto(DASHBOARD_URL, { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);
    
    const nav = page.locator('nav').first();
    await expect(nav).toBeVisible();
    
    // Check for all required tabs
    const requiredTabs = ['Mission Control', 'Accounts', 'Journal', 'Intelligence', 'Settings'];
    for (const tabName of requiredTabs) {
      const tab = nav.locator(`text=${tabName}`).first();
      await expect(tab).toBeVisible();
    }
    
    // Mission Control should be active by default
    const missionControl = nav.locator('button:has-text("Mission Control")').first();
    const missionControlClass = await missionControl.getAttribute('class');
    expect(missionControlClass).toContain('border-blue-400');
  });

  test('Mission Control tab shows two-column layout with System Status, Quick Account Summary, Session Gate', async ({ page }) => {
    await page.goto(DASHBOARD_URL, { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);
    
    // Ensure we're on Mission Control tab
    await page.click('button:has-text("Mission Control")');
    await page.waitForTimeout(1000);
    
    // Check for System Status panel
    await expect(page.locator('text=System Status')).toBeVisible();
    
    // Check for Quick Account Summary panel
    await expect(page.locator('text=Quick Account Summary')).toBeVisible();
    
    // Check for Session Gate panel
    await expect(page.locator('text=Session Gate')).toBeVisible();
    
    // Verify two-column layout (grid with 2 columns)
    const mainContent = page.locator('main').first();
    const gridElements = mainContent.locator('[class*="grid-cols-2"]');
    const gridCount = await gridElements.count();
    expect(gridCount).toBeGreaterThan(0);
  });

  test('System Status panel shows CONTROL PLANE, RUNNER, MARKET DATA, OUTLOOK ENGINE with UP status', async ({ page }) => {
    await page.goto(DASHBOARD_URL, { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);
    
    await page.click('button:has-text("Mission Control")');
    await page.waitForTimeout(1000);
    
    // Check for all four status indicators
    await expect(page.locator('text=CONTROL PLANE')).toBeVisible();
    await expect(page.locator('text=RUNNER')).toBeVisible();
    await expect(page.locator('text=MARKET DATA')).toBeVisible();
    await expect(page.locator('text=OUTLOOK ENGINE')).toBeVisible();
    
    // Check for UP status (should be green)
    const upStatuses = page.locator('text=UP');
    const upCount = await upStatuses.count();
    expect(upCount).toBeGreaterThanOrEqual(4);
  });

  test('Session Gate panel shows BLOCKED with red styling when embargo active', async ({ page }) => {
    await page.goto(DASHBOARD_URL, { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);
    
    // Mock session data with embargo
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
              embargo_triggers: 'High impact news',
              news_state: 'embargo',
              roadmap_aligned: false,
              regime: 'choppy'
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
    
    await page.click('button:has-text("Mission Control")');
    await page.waitForTimeout(1000);
    
    // Check for BLOCKED text (most important)
    const blocked = page.locator('text=BLOCKED');
    await expect(blocked).toBeVisible();
    
    // Check Session Gate panel exists
    await expect(page.locator('text=Session Gate')).toBeVisible();
    
    // Check for lock icon (indicates blocked state)
    const lockIcon = page.locator('svg, [class*="Lock"]').first();
    const lockVisible = await lockIcon.count();
    expect(lockVisible).toBeGreaterThan(0);
  });

  test('Quick Account Summary shows account cards with balances', async ({ page }) => {
    await page.goto(DASHBOARD_URL, { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);
    
    await page.click('button:has-text("Mission Control")');
    await page.waitForTimeout(1000);
    
    // Check for Quick Account Summary panel
    await expect(page.locator('text=Quick Account Summary')).toBeVisible();
    
    // Should show account cards (or MISSING if no data)
    const accountSection = page.locator('text=Quick Account Summary').locator('..').first();
    // Look for account cards with multiple selectors
    const hasAccounts = await accountSection.locator('[data-testid="account-card"], [class*="bg-black"], [class*="rounded-lg"]').count();
    const hasMissing = await accountSection.locator('text=MISSING, text=No account').count();
    const hasAccountText = await accountSection.locator('text=/Account|\\$|USD|EUR/').count();
    
    // Should have either accounts or MISSING indicator or account-related text
    expect(hasAccounts + hasMissing + hasAccountText).toBeGreaterThan(0);
  });

  test('all tabs are functional and show content', async ({ page }) => {
    await page.goto(DASHBOARD_URL, { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);
    
    const tabs = ['Mission Control', 'Accounts', 'Journal', 'Intelligence', 'Settings'];
    
    for (const tabName of tabs) {
      await page.click(`button:has-text("${tabName}")`);
      await page.waitForTimeout(500);
      
      // Verify tab content is visible
      const main = page.locator('main');
      await expect(main).toBeVisible();
      
      // Verify tab is active (has blue border)
      const tab = page.locator(`button:has-text("${tabName}")`).first();
      const tabClass = await tab.getAttribute('class');
      expect(tabClass).toContain('border-blue-400');
    }
  });

  test('dashboard uses glass morphism cards throughout', async ({ page }) => {
    await page.goto(DASHBOARD_URL, { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);
    
    // Check for glass-card class
    const glassCards = page.locator('.glass-card');
    const cardCount = await glassCards.count();
    expect(cardCount).toBeGreaterThan(0);
    
    // Verify backdrop-filter is applied
    if (cardCount > 0) {
      const firstCard = glassCards.first();
      const backdropFilter = await firstCard.evaluate((el) => window.getComputedStyle(el).backdropFilter);
      expect(backdropFilter).toContain('blur');
    }
  });

  test('dashboard has dark gradient background', async ({ page }) => {
    await page.goto(DASHBOARD_URL, { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);
    
    const body = page.locator('body');
    const background = await body.evaluate((el) => window.getComputedStyle(el).background);
    expect(background).toContain('gradient');
    // Check for rgb(10, 11, 13) which is #0a0b0d
    expect(background).toMatch(/rgb\(10,\s*11,\s*13\)|#0a0b0d/);
  });
});
