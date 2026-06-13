import { test, expect } from '@playwright/test';

// NOTE:
// This file used to assert a pixel-perfect match with the legacy
// `forensic_command.html` template (including TradingView widget, glass cards,
// and old nav IDs). The canonical dashboard is now the React SPA served at
// the control plane root. These tests have been rewritten to assert the
// **React forensic dashboard** structure instead of the legacy HTML shell.

const DASHBOARD_URL = process.env.DASHBOARD_URL || 'http://127.0.0.1:8787/';

test.describe('React Forensic Dashboard UI verification', () => {
  test('header + sidebar match React forensic layout', async ({ page }) => {
    await page.goto(DASHBOARD_URL, { waitUntil: 'networkidle' });

    // Header: AI-QUANT V2.6 + FORENSIC COMMAND + status badges
    const header = page.locator('header');
    await expect(header).toBeVisible();

    await expect(header.locator('text=AI-QUANT')).toBeVisible();
    await expect(header.locator('text=V2.6')).toBeVisible();
    await expect(header.locator('text=FORENSIC COMMAND')).toBeVisible();

    // Status text should mention execution + mode
    const headerText = await header.textContent();
    expect(headerText).toMatch(/EXECUTION (ON|OFF)/);
    expect(headerText).toMatch(/PAPER|LIVE/);

    // Truth Envelope notice in sidebar
    const sidebar = page.locator('nav');
    await expect(sidebar).toBeVisible();
    await expect(sidebar.locator('text=TRUTH ENVELOPE')).toBeVisible();
    await expect(
      sidebar.locator(
        'text=All data rendered is strictly sourced from backend snapshots. No frontend simulation.'
      )
    ).toBeVisible();

    // React tabs: Terminal / Mesh / Signals / News
    const tabs = ['Terminal', 'Mesh', 'Signals', 'News'];
    for (const label of tabs) {
      await expect(sidebar.locator(`button:has-text("${label}")`).first()).toBeVisible();
    }

    // Active tab indicator (green dot) should appear on selected tab
    const activeIndicator = sidebar.locator('div[class*="bg-[#00ff88]"]').last();
    await expect(activeIndicator).toBeVisible();
  });

  test('Terminal tab shows Session Gate, System Health, Market Overview cards', async ({ page }) => {
    await page.goto(DASHBOARD_URL, { waitUntil: 'networkidle' });

    // Ensure we are on Terminal tab
    await page.click('button:has-text("Terminal")');
    await page.waitForTimeout(1000);

    await expect(page.locator('text=Session Regime Gate').first()).toBeVisible();
    await expect(page.locator('text=System Health').first()).toBeVisible();
    await expect(page.locator('text=Market Overview').first()).toBeVisible();
  });

  test('Mesh / Signals / News tabs render expected shells', async ({ page }) => {
    await page.goto(DASHBOARD_URL, { waitUntil: 'networkidle' });

    // Mesh → Active Accounts table
    await page.click('button:has-text("Mesh")');
    await page.waitForTimeout(750);
    await expect(page.locator('text=Active Accounts').first()).toBeVisible();

    // Signals → Recent Signals card
    await page.click('button:has-text("Signals")');
    await page.waitForTimeout(750);
    await expect(page.locator('text=Recent Signals').first()).toBeVisible();

    // News → Market News card and at least one item (or empty state)
    await page.click('button:has-text("News")');
    await page.waitForTimeout(750);
    await expect(page.locator('text=Market News').first()).toBeVisible();
    const hasItemsOrEmptyState = await page
      .locator('text=No news items available, text=/\\bMarket News\\b/')
      .count();
    expect(hasItemsOrEmptyState).toBeGreaterThanOrEqual(1);
  });

  test('no legacy forensic HTML shell is present', async ({ page }) => {
    await page.goto(DASHBOARD_URL, { waitUntil: 'networkidle' });

    // These were specific to the old forensic_command.html implementation.
    await expect(page.locator('#tradingview_terminal')).toHaveCount(0);
    await expect(page.locator('#tab-terminal')).toHaveCount(0);
    await expect(page.locator('text=/Forensic Pre-Flight/i')).toHaveCount(0);
    await expect(page.locator('.legacy-dashboard')).toHaveCount(0);
  });

  test('basic sanity: no console errors on load', async ({ page }) => {
    const consoleErrors: string[] = [];

    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    page.on('pageerror', (err) => {
      consoleErrors.push(err.message);
    });

    await page.goto(DASHBOARD_URL, { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // Allow benign network warnings but fail on React/runtime errors
    const criticalErrors = consoleErrors.filter(
      (msg) =>
        !/NetworkError|net::ERR/i.test(msg) &&
        !/favicon\.ico/.test(msg)
    );
    expect(criticalErrors).toEqual([]);
  });
});
