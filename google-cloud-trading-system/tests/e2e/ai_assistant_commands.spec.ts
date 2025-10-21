import { test, expect } from '@playwright/test';

test.describe('AI Assistant - Command Previews and Confirmations (staging)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('preview close positions without execution until confirm', async ({ page }) => {
    const input = page.locator('.ai-assistant-panel textarea');
    const send = page.locator('.ai-assistant-panel .send-button');
    await expect(input).toBeVisible();

    await input.fill('Close all XAUUSD longs');
    await send.click();

    const preview = page.locator('.ai-assistant-panel .command-preview');
    await expect(preview).toBeVisible();
    await expect(preview).toContainText('XAUUSD');

    // Ensure nothing executed yet
    const result = page.locator('.ai-assistant-panel .command-result');
    await expect(result).toHaveCount(0);
  });

  test('confirm DEMO execution', async ({ page }) => {
    const input = page.locator('.ai-assistant-panel textarea');
    const send = page.locator('.ai-assistant-panel .send-button');
    await input.fill('Close all XAUUSD longs');
    await send.click();

    const confirm = page.locator('.ai-assistant-panel .confirm-button');
    await confirm.click();

    const result = page.locator('.ai-assistant-panel .command-result');
    await expect(result).toBeVisible();
    await expect(result).toContainText('Executed (demo)');
  });

  test('live guard requires explicit token and UI confirm', async ({ page }) => {
    const input = page.locator('.ai-assistant-panel textarea');
    const send = page.locator('.ai-assistant-panel .send-button');
    await input.fill('Place live order EURUSD 10000');
    await send.click();

    const guard = page.locator('.ai-assistant-panel .live-guard');
    await expect(guard).toBeVisible();
    await expect(guard).toContainText('LIVE CONFIRM YES');
  });
});
