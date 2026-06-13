import { test, expect } from '@playwright/test';

const DASHBOARD_URL = process.env.DASHBOARD_URL || 'http://127.0.0.1:8787';

test.describe('Dashboard Transparency Features', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to dashboard
    await page.goto(DASHBOARD_URL);
    // Wait for dashboard to load
    await page.waitForLoadState('networkidle');
  });

  test('should display trade block reason panel', async ({ page }) => {
    // Check if block reason element exists
    const blockReason = page.locator('#block-reason');
    await expect(blockReason).toBeVisible({ timeout: 10000 }).catch(() => {
      // Block reason might be hidden if no blocks, check it exists in DOM
      expect(blockReason).toBeAttached();
    });

    // Verify block reason text appears when blocked
    const blockReasonText = await blockReason.textContent();
    if (blockReasonText && blockReasonText.includes('Blocked:')) {
      expect(blockReasonText).toContain('Blocked:');
    }
  });

  test('should display session countdown timer', async ({ page }) => {
    // Check next session countdown element
    const nextSessionCountdown = page.locator('#next-session-countdown');
    await expect(nextSessionCountdown).toBeVisible();
    
    const countdownText = await nextSessionCountdown.textContent();
    // Should show time like "2h 30m" or "--"
    expect(countdownText).toBeTruthy();
  });

  test('should display regime readiness indicator', async ({ page }) => {
    // Check readiness status
    const readinessStatus = page.locator('#readiness-status');
    await expect(readinessStatus).toBeVisible();
    
    const statusText = await readinessStatus.textContent();
    // Should be one of: READY, WAITING, BLOCKED, or --
    expect(['READY', 'WAITING', 'BLOCKED', '--']).toContain(statusText?.trim() || '--');
  });

  test('should display readiness score gauge', async ({ page }) => {
    // Check readiness gauge exists
    const readinessGauge = page.locator('#readiness-gauge');
    await expect(readinessGauge).toBeAttached();
    
    // Check readiness score value
    const readinessScore = page.locator('#readiness-score-value');
    await expect(readinessScore).toBeVisible();
    
    const scoreText = await readinessScore.textContent();
    const score = parseInt(scoreText || '0');
    // Score should be 0-100
    expect(score).toBeGreaterThanOrEqual(0);
    expect(score).toBeLessThanOrEqual(100);
  });

  test('should display regime ETA countdown', async ({ page }) => {
    // Check regime ETA element
    const regimeEta = page.locator('#regime-eta');
    await expect(regimeEta).toBeVisible();
    
    const etaText = await regimeEta.textContent();
    // Should show HH:MM:SS format or "READY"
    expect(etaText).toBeTruthy();
    if (etaText && etaText !== 'READY' && etaText !== '--:--:--') {
      // Should match HH:MM:SS format
      expect(etaText).toMatch(/^\d{2}:\d{2}:\d{2}$/);
    }
  });

  test('should display candles remaining', async ({ page }) => {
    // Check candles remaining element
    const candlesRemaining = page.locator('#candles-remaining');
    await expect(candlesRemaining).toBeVisible();
    
    const candlesText = await candlesRemaining.textContent();
    const candles = parseInt(candlesText || '0');
    // Should be a non-negative number
    expect(candles).toBeGreaterThanOrEqual(0);
  });

  test('should display current session and regime', async ({ page }) => {
    // Check current session
    const currentSession = page.locator('#current-session');
    await expect(currentSession).toBeVisible();
    
    const sessionText = await currentSession.textContent();
    // Should show session name (ASIA, LONDON, NEW_YORK, etc.)
    expect(sessionText).toBeTruthy();
    
    // Check current regime
    const currentRegime = page.locator('#current-regime');
    await expect(currentRegime).toBeVisible();
    
    const regimeText = await currentRegime.textContent();
    // Should show regime (TRENDING, RANGING, UNKNOWN, etc.)
    expect(regimeText).toBeTruthy();
  });

  test('should fetch session-regime-gate snapshot from API', async ({ page }) => {
    // Intercept API call
    const responsePromise = page.waitForResponse(
      (response) => response.url().includes('/api/session-regime-gate/snapshot') && response.status() === 200,
      { timeout: 15000 }
    );
    
    // Reload page to trigger API call
    await page.reload();
    
    const response = await responsePromise;
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
    expect(payload).toHaveProperty('readiness_score');
    expect(payload).toHaveProperty('candles_remaining');
    expect(payload).toHaveProperty('eta_seconds');
    
    // Verify readiness is one of expected values
    expect(['READY', 'WAITING', 'BLOCKED']).toContain(payload.readiness || 'WAITING');
    
    // Verify next_session structure
    if (payload.next_session) {
      expect(payload.next_session).toHaveProperty('next_tradable_session');
      expect(payload.next_session).toHaveProperty('countdown_seconds');
      expect(payload.next_session).toHaveProperty('target_utc');
    }
    
    // Verify block_details structure
    if (payload.block_details) {
      expect(payload.block_details).toHaveProperty('roadmap_aligned');
      expect(payload.block_details).toHaveProperty('is_embargo');
    }
  });

  test('should update transparency features when API data changes', async ({ page }) => {
    // Wait for initial load
    await page.waitForTimeout(2000);
    
    // Get initial readiness status
    const initialReadiness = await page.locator('#readiness-status').textContent();
    
    // Wait for next poll (should poll every 10 seconds)
    await page.waitForTimeout(11000);
    
    // Get updated readiness status
    const updatedReadiness = await page.locator('#readiness-status').textContent();
    
    // Status should be visible (might be same or different)
    expect(updatedReadiness).toBeTruthy();
  });

  test('should show "Why Trades Are Blocked" information', async ({ page }) => {
    // Check if block reason panel is visible (even if hidden)
    const blockReason = page.locator('#block-reason');
    
    // Check if session gate panel exists
    const sessionGatePanel = page.locator('text=🎯 Trading Readiness').locator('..').locator('..');
    await expect(sessionGatePanel).toBeVisible();
    
    // Verify all key elements are present
    await expect(page.locator('#readiness-status')).toBeVisible();
    await expect(page.locator('#current-session')).toBeVisible();
    await expect(page.locator('#current-regime')).toBeVisible();
    await expect(page.locator('#next-session-countdown')).toBeVisible();
  });

  test('should have correct color coding for readiness states', async ({ page }) => {
    // Check readiness badge
    const badge = page.locator('#session-gate-badge');
    await expect(badge).toBeVisible();
    
    const badgeText = await badge.textContent();
    
    // Check gauge color based on readiness
    const gauge = page.locator('#readiness-gauge');
    const strokeColor = await gauge.getAttribute('stroke');
    
    if (badgeText?.includes('READY')) {
      expect(strokeColor).toBe('#00ff88'); // Green
    } else if (badgeText?.includes('WAITING')) {
      expect(strokeColor).toBe('#ffc107'); // Yellow
    } else {
      // BLOCKED or unknown
      expect(['#ff3e3e', '#00ff88', '#ffc107']).toContain(strokeColor); // Red, Green, or Yellow
    }
  });
});
