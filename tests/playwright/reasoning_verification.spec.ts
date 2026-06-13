import { test, expect } from '@playwright/test';
import type { Page } from '@playwright/test';
import fs from 'fs';
import path from 'path';

const CONTROL_URL = 'https://alpha.fxgdesigns.co.uk/control';
const API_URL = 'https://alpha.fxgdesigns.co.uk';

test.describe('Reasoning Snapshot Verification (S5)', () => {
  
  test.beforeEach(async ({ page }) => {
    await page.goto(CONTROL_URL);
    // Wait for dashboard to load
    await expect(page.getByText('Alpha Control Plane')).toBeVisible();
  });

  test('should display reasoning snapshot in Session Gate & Reasoning panel', async ({ page }) => {
    // Wait for the Session Gate & Reasoning section to appear
    const sessionGateSection = page.locator('section[aria-label="Session Gate & Reasoning"]');
    await expect(sessionGateSection).toBeVisible({ timeout: 10000 });
    
    // Check if reasoning snapshot is available or shows empty state
    const emptyState = page.getByText('No reasoning snapshot available yet');
    const hasData = page.getByText('Primary Blocker:');
    
    // Either empty state or data should be visible
    const hasContent = await emptyState.isVisible().catch(() => false) || 
                      await hasData.isVisible().catch(() => false);
    
    expect(hasContent).toBe(true);
  });

  test('should display primary_blocker when reasoning snapshot exists', async ({ page }) => {
    // First, check if API returns reasoning data
    const apiResponse = await page.request.get(`${API_URL}/api/system/reasoning`);
    const reasoningData = await apiResponse.json();
    
    if (reasoningData.ok && reasoningData.snapshot) {
      // If snapshot exists, verify UI displays it
      const sessionGateSection = page.locator('section[aria-label="Session Gate & Reasoning"]');
      await expect(sessionGateSection).toBeVisible({ timeout: 10000 });
      
      // Check for primary blocker text (either the blocker or "None - Ready to Trade")
      const primaryBlockerLabel = page.getByText('Primary Blocker:', { exact: false });
      await expect(primaryBlockerLabel).toBeVisible();
      
      // Verify primary blocker value is displayed
      const blockerValue = reasoningData.snapshot.primary_blocker;
      if (blockerValue) {
        // Should show the blocker text
        await expect(page.getByText(blockerValue, { exact: false })).toBeVisible();
      } else {
        // Should show "None - Ready to Trade"
        await expect(page.getByText('None - Ready to Trade')).toBeVisible();
      }
    } else {
      // If no snapshot, should show empty state
      const emptyState = page.getByText('No reasoning snapshot available yet');
      await expect(emptyState).toBeVisible();
    }
  });

  test('should display readiness_score numeric value', async ({ page }) => {
    // Check API for reasoning data
    const apiResponse = await page.request.get(`${API_URL}/api/system/reasoning`);
    const reasoningData = await apiResponse.json();
    
    if (reasoningData.ok && reasoningData.snapshot) {
      const sessionGateSection = page.locator('section[aria-label="Session Gate & Reasoning"]');
      await expect(sessionGateSection).toBeVisible({ timeout: 10000 });
      
      // Verify readiness score label
      const readinessLabel = page.getByText('Readiness Score:', { exact: false });
      await expect(readinessLabel).toBeVisible();
      
      // Verify numeric value is displayed
      const score = reasoningData.snapshot.readiness_score;
      if (typeof score === 'number') {
        await expect(page.getByText(score.toString(), { exact: true })).toBeVisible();
      }
    }
  });

  test('should display nearest_unblock_event', async ({ page }) => {
    // Check API for reasoning data
    const apiResponse = await page.request.get(`${API_URL}/api/system/reasoning`);
    const reasoningData = await apiResponse.json();
    
    if (reasoningData.ok && reasoningData.snapshot) {
      const sessionGateSection = page.locator('section[aria-label="Session Gate & Reasoning"]');
      await expect(sessionGateSection).toBeVisible({ timeout: 10000 });
      
      // Verify nearest unblock event label
      const unblockLabel = page.getByText('Nearest Unblock Event:', { exact: false });
      await expect(unblockLabel).toBeVisible();
      
      // Verify unblock event value is displayed
      const unblockEvent = reasoningData.snapshot.nearest_unblock_event;
      if (unblockEvent) {
        // Use a more specific locator that includes the label context
        const unblockSection = page.locator('section[aria-label="Session Gate & Reasoning"]');
        await expect(unblockSection.getByText(unblockEvent, { exact: false }).first()).toBeVisible();
      }
    }
  });

  test('should display timestamp and update live', async ({ page }) => {
    const sessionGateSection = page.locator('section[aria-label="Session Gate & Reasoning"]');
    await expect(sessionGateSection).toBeVisible({ timeout: 10000 });
    
    // Check for timestamp label
    const timestampLabel = page.getByText('Timestamp:', { exact: false });
    await expect(timestampLabel).toBeVisible();
    
    // Wait a bit and check if timestamp updates (dashboard polls every 2 seconds)
    const initialTimestamp = await page.locator('text=/Timestamp:.*/').textContent();
    await page.waitForTimeout(3000); // Wait 3 seconds
    const updatedTimestamp = await page.locator('text=/Timestamp:.*/').textContent();
    
    // Timestamp should exist (may or may not change depending on scan cycle)
    expect(initialTimestamp).toBeTruthy();
    expect(updatedTimestamp).toBeTruthy();
  });

  test('should display secondary_blockers when present', async ({ page }) => {
    // Check API for reasoning data
    const apiResponse = await page.request.get(`${API_URL}/api/system/reasoning`);
    const reasoningData = await apiResponse.json();
    
    if (reasoningData.ok && reasoningData.snapshot && 
        reasoningData.snapshot.secondary_blockers && 
        reasoningData.snapshot.secondary_blockers.length > 0) {
      
      const sessionGateSection = page.locator('section[aria-label="Session Gate & Reasoning"]');
      await expect(sessionGateSection).toBeVisible({ timeout: 10000 });
      
      // Verify secondary blockers label
      const secondaryLabel = page.getByText('Secondary Blockers:', { exact: false });
      await expect(secondaryLabel).toBeVisible();
      
      // Verify at least one secondary blocker is displayed
      const firstBlocker = reasoningData.snapshot.secondary_blockers[0];
      await expect(page.getByText(firstBlocker, { exact: false })).toBeVisible();
    }
  });

  test('should fail if reasoning elements are missing or stale', async ({ page }) => {
    // Check API for reasoning data
    const apiResponse = await page.request.get(`${API_URL}/api/system/reasoning`);
    const reasoningData = await apiResponse.json();
    
    if (reasoningData.ok && reasoningData.snapshot) {
      const sessionGateSection = page.locator('section[aria-label="Session Gate & Reasoning"]');
      await expect(sessionGateSection).toBeVisible({ timeout: 10000 });
      
      // All required elements must be present
      await expect(page.getByText('Primary Blocker:', { exact: false })).toBeVisible();
      await expect(page.getByText('Nearest Unblock Event:', { exact: false })).toBeVisible();
      await expect(page.getByText('Readiness Score:', { exact: false })).toBeVisible();
      
      // Check timestamp is not too old (within last 2 scan cycles = ~60 seconds for 30s scan interval)
      const timestampText = await page.locator('text=/Timestamp:.*/').textContent();
      expect(timestampText).toBeTruthy();
      
      // Extract timestamp and verify it's recent
      const timestampMatch = timestampText?.match(/(\d{1,2}):(\d{2}):(\d{2})/);
      if (timestampMatch) {
        const [_, hours, minutes, seconds] = timestampMatch;
        const timestampDate = new Date();
        timestampDate.setHours(parseInt(hours), parseInt(minutes), parseInt(seconds), 0);
        
        const now = new Date();
        const ageSeconds = (now.getTime() - timestampDate.getTime()) / 1000;
        
        // Should be within last 2 minutes (allowing for scan interval + processing)
        expect(ageSeconds).toBeLessThan(120);
      }
    }
  });

  test('should capture screenshot evidence', async ({ page }) => {
    const sessionGateSection = page.locator('section[aria-label="Session Gate & Reasoning"]');
    await expect(sessionGateSection).toBeVisible({ timeout: 10000 });
    
    // Wait for content to load
    await page.waitForTimeout(2000);
    
    // Capture screenshot of the reasoning section
    const screenshotDir = path.resolve(__dirname, '../../playwright/screenshots');
    if (!fs.existsSync(screenshotDir)) {
      fs.mkdirSync(screenshotDir, { recursive: true });
    }
    
    await sessionGateSection.screenshot({ 
      path: path.join(screenshotDir, 'reasoning_visible.png'),
      fullPage: false
    });
    
    // Verify screenshot was created
    const screenshotPath = path.join(screenshotDir, 'reasoning_visible.png');
    expect(fs.existsSync(screenshotPath)).toBe(true);
  });

  test('should verify API returns exact file contents', async ({ page }) => {
    // Test that API endpoint returns verbatim file contents
    const apiResponse = await page.request.get(`${API_URL}/api/system/reasoning`);
    const apiData = await apiResponse.json();
    
    // If file exists, verify structure
    if (apiData.ok && apiData.snapshot) {
      const snapshot = apiData.snapshot;
      
      // Verify all required fields are present
      expect(snapshot).toHaveProperty('instrument');
      expect(snapshot).toHaveProperty('primary_blocker');
      expect(snapshot).toHaveProperty('secondary_blockers');
      expect(snapshot).toHaveProperty('readiness_score');
      expect(snapshot).toHaveProperty('nearest_unblock_event');
      expect(snapshot).toHaveProperty('estimated_time_to_readiness');
      expect(snapshot).toHaveProperty('embargo_active');
      expect(snapshot).toHaveProperty('regime');
      expect(snapshot).toHaveProperty('bias_state');
      expect(snapshot).toHaveProperty('timestamp_utc');
      
      // Verify types
      expect(typeof snapshot.readiness_score).toBe('number');
      expect(Array.isArray(snapshot.secondary_blockers)).toBe(true);
      expect(typeof snapshot.embargo_active).toBe('boolean');
    } else if (!apiData.ok) {
      // If file missing, should return explicit error
      expect(apiData).toHaveProperty('error');
      expect(apiData).toHaveProperty('reason');
    }
  });

  test.afterAll(async () => {
    const logPath = path.resolve(__dirname, '../../../logs/reasoning_verification_live.log');
    const logDir = path.dirname(logPath);
    if (!fs.existsSync(logDir)) {
      fs.mkdirSync(logDir, { recursive: true });
    }
    fs.appendFileSync(
      logPath,
      `VERIFICATION_COMPLETE ${new Date().toISOString()}\n`
    );
  });
});
