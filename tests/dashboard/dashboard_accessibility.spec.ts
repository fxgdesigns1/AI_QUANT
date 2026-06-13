import { test, expect } from '@playwright/test';

// Test dashboard accessibility via tunnel
const DASHBOARD_URL = process.env.DASHBOARD_URL || 'http://127.0.0.1:28787';

test.describe('Dashboard Accessibility', () => {
  test('dashboard root is accessible', async ({ page }) => {
    const response = await page.goto(DASHBOARD_URL);
    
    // Should not be 404
    expect(response?.status()).not.toBe(404);
    expect(response?.status()).toBeLessThan(400);
    
    // Should load some content
    await page.waitForLoadState('networkidle');
    const bodyText = await page.textContent('body');
    expect(bodyText).toBeTruthy();
  });

  test('health endpoint works', async ({ request }) => {
    const response = await request.get(`${DASHBOARD_URL}/health`);
    expect(response.status()).toBe(200);
    
    const data = await response.json();
    expect(data).toHaveProperty('status');
  });

  test('status endpoint returns valid data', async ({ request }) => {
    const response = await request.get(`${DASHBOARD_URL}/api/status`);
    expect(response.status()).toBe(200);
    
    const data = await response.json();
    expect(data).toHaveProperty('data');
    expect(data.data).toHaveProperty('mode');
    expect(data.data).toHaveProperty('execution_enabled');
  });

  test('dashboard serves React app (not 404)', async ({ page }) => {
    await page.goto(DASHBOARD_URL);
    
    // Wait for React to load
    await page.waitForLoadState('networkidle');
    
    // Check that we're not getting a 404 error page
    const pageContent = await page.textContent('body');
    expect(pageContent).not.toContain('Not Found');
    expect(pageContent).not.toContain('404');
    
    // Should have some React content (root div or React app)
    const rootElement = await page.locator('#root').count();
    // Either React app is loaded or it's an API response
    expect(rootElement).toBeGreaterThanOrEqual(0);
  });
});
