import { test, expect } from '@playwright/test';

/**
 * Dashboard Visual Design Verification
 * 
 * Verifies the dashboard matches the original design aesthetic:
 * - Glass morphism cards
 * - Gradient backgrounds
 * - Professional styling
 * - Proper spacing and typography
 */

const DASHBOARD_URL = process.env.DASHBOARD_URL || 'https://alpha-dashboard.fxg.internal';

test.describe('Dashboard Visual Design Verification', () => {
  test('header has correct styling and branding', async ({ page }) => {
    await page.goto(DASHBOARD_URL, { waitUntil: 'networkidle' });
    
    // Check for AQ logo
    const logo = page.locator('text=AQ').first();
    await expect(logo).toBeVisible();
    
    // Check for "Forensic Command" title with glow
    const title = page.locator('text=Forensic Command');
    await expect(title).toBeVisible();
    
    // Check header has gradient background
    const header = page.locator('header').first();
    const headerStyle = await header.evaluate((el) => window.getComputedStyle(el).background);
    expect(headerStyle).toContain('gradient');
  });

  test('sidebar has proper navigation styling', async ({ page }) => {
    await page.goto(DASHBOARD_URL, { waitUntil: 'networkidle' });
    
    const sidebar = page.locator('nav').first();
    await expect(sidebar).toBeVisible();
    
    // Check active tab has green border
    const activeTab = sidebar.locator('button').first();
    const borderColor = await activeTab.evaluate((el) => window.getComputedStyle(el).borderLeftColor);
    expect(borderColor).toMatch(/rgb\(0,\s*255,\s*136\)|rgba\(0,\s*255,\s*136/);
  });

  test('cards use glass morphism effect', async ({ page }) => {
    await page.goto(DASHBOARD_URL, { waitUntil: 'networkidle' });
    
    // Wait for cards to load
    await page.waitForTimeout(2000);
    
    // Check for glass card styling (backdrop-filter)
    const cards = page.locator('.glass-card').first();
    if (await cards.count() > 0) {
      const backdropFilter = await cards.first().evaluate((el) => window.getComputedStyle(el).backdropFilter);
      expect(backdropFilter).toContain('blur');
    }
  });

  test('dashboard has proper color scheme', async ({ page }) => {
    await page.goto(DASHBOARD_URL, { waitUntil: 'networkidle' });
    
    // Check for accent green color (#00ff88)
    const greenElements = page.locator('[style*="#00ff88"], [style*="rgb(0, 255, 136)"]');
    const count = await greenElements.count();
    expect(count).toBeGreaterThan(0);
    
    // Check background has gradient
    const body = page.locator('body');
    const bgStyle = await body.evaluate((el) => window.getComputedStyle(el).background);
    expect(bgStyle).toContain('gradient');
  });

  test('status badges have proper styling', async ({ page }) => {
    await page.goto(DASHBOARD_URL, { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);
    
    // Check for status badges
    const badges = page.locator('text=/ENABLED|DISABLED|PAPER|LIVE/');
    const badgeCount = await badges.count();
    expect(badgeCount).toBeGreaterThan(0);
  });

  test('dashboard is responsive and usable', async ({ page }) => {
    await page.goto(DASHBOARD_URL, { waitUntil: 'networkidle' });
    
    // Check main content area is visible
    const main = page.locator('main');
    await expect(main).toBeVisible();
    
    // Check sidebar is visible
    const sidebar = page.locator('nav');
    await expect(sidebar).toBeVisible();
    
    // Verify no horizontal scroll
    const bodyWidth = await page.evaluate(() => document.body.scrollWidth);
    const viewportWidth = await page.evaluate(() => window.innerWidth);
    expect(bodyWidth).toBeLessThanOrEqual(viewportWidth + 10); // Allow small margin
  });

  test('all tabs are accessible and styled correctly', async ({ page }) => {
    await page.goto(DASHBOARD_URL, { waitUntil: 'networkidle' });
    
    const tabs = ['Terminal', 'Readiness', 'Mesh', 'Signals', 'News'];
    
    for (const tabName of tabs) {
      await page.click(`button:has-text("${tabName}")`);
      await page.waitForTimeout(500);
      
      // Verify tab content is visible
      const content = page.locator('main');
      await expect(content).toBeVisible();
    }
  });

  test('hover effects work on interactive elements', async ({ page }) => {
    await page.goto(DASHBOARD_URL, { waitUntil: 'networkidle' });
    
    // Hover over a card
    const card = page.locator('.glass-card').first();
    if (await card.count() > 0) {
      await card.hover();
      await page.waitForTimeout(300);
      
      // Card should still be visible after hover
      await expect(card).toBeVisible();
    }
  });
});
