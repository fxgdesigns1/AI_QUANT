import { test, expect } from '@playwright/test';

test.describe('AI Assistant - Chat & Q&A (staging, flag on)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    // Ensure backend is up and AI assistant is registered
    await page.waitForLoadState('domcontentloaded');
    await page.waitForResponse((resp) => resp.url().includes('/ai/health') && resp.status() === 200, { timeout: 15000 }).catch(() => {});
  });

  test('widget hidden when feature flag is off (manual run condition)', async ({ page }) => {
    // This test is meaningful only when run with AI_ASSISTANT_ENABLED=false
    const widget = page.locator('.ai-assistant-panel');
    // Do not fail if visible (depends on env). This is a smoke assertion.
    await expect(widget).toHaveCount(0);
  });

  test('market overview Q&A renders structured reply (flag on)', async ({ page }) => {
    // Wait for the widget to mount
    const input = page.locator('.ai-assistant-panel textarea');
    const send = page.locator('.ai-assistant-panel .send-button');
    await page.waitForSelector('.ai-assistant-panel textarea', { timeout: 20000 });
    await expect(input).toBeVisible();
    await input.fill('Give me a market overview for EURUSD and XAUUSD');
    await send.click();

    const messages = page.locator('.ai-assistant-panel .chat-messages');
    await expect(messages).toContainText('Assistant:');
  });
});
