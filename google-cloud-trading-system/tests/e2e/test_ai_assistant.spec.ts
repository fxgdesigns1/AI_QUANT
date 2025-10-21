import { test, expect } from '@playwright/test';

test.describe('AI Assistant Integration Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to dashboard
    await page.goto('http://localhost:5005');
    await page.waitForLoadState('networkidle');
  });

  test('should show AI button and toggle panel', async ({ page }) => {
    // Check AI button exists and is visible
    const aiButton = page.locator('#aiToggleButton');
    await expect(aiButton).toBeVisible();
    
    // Click AI button
    await aiButton.click();
    
    // Verify panel appears
    const aiPanel = page.locator('#aiAssistantPanel');
    await expect(aiPanel).toBeVisible();
    
    // Verify panel has expected components
    const chatInput = page.locator('#chatInput');
    const sendButton = page.locator('.send-button');
    await expect(chatInput).toBeVisible();
    await expect(sendButton).toBeVisible();
    
    // Click button again to hide
    await aiButton.click();
    await expect(aiPanel).toBeHidden();
  });

  test('should send and receive AI messages', async ({ page }) => {
    // Open AI panel
    await page.locator('#aiToggleButton').click();
    
    // Type and send a message
    await page.locator('#chatInput').fill('market overview');
    await page.locator('.send-button').click();
    
    // Wait for response
    await page.waitForTimeout(1000);
    
    // Verify message appears in chat
    const messages = page.locator('.message');
    await expect(messages).toHaveCount(2); // User message + AI response
    
    // Verify message content
    const userMessage = page.locator('.message.user').first();
    const aiResponse = page.locator('.message.assistant').first();
    await expect(userMessage).toContainText('market overview');
    await expect(aiResponse).toBeVisible();
  });

  test('should handle Enter key to send messages', async ({ page }) => {
    // Open AI panel
    await page.locator('#aiToggleButton').click();
    
    // Type message and press Enter
    await page.locator('#chatInput').fill('system status');
    await page.locator('#chatInput').press('Enter');
    
    // Wait for response
    await page.waitForTimeout(1000);
    
    // Verify message exchange
    const messages = page.locator('.message');
    await expect(messages).toHaveCount(2);
  });

  test('should persist chat visibility state', async ({ page }) => {
    // Open panel
    await page.locator('#aiToggleButton').click();
    
    // Verify panel is visible
    const aiPanel = page.locator('#aiAssistantPanel');
    await expect(aiPanel).toBeVisible();
    
    // Refresh page
    await page.reload();
    await page.waitForLoadState('networkidle');
    
    // Panel should maintain state
    await expect(aiPanel).toBeVisible();
  });

  test('should handle API errors gracefully', async ({ page }) => {
    // Open panel
    await page.locator('#aiToggleButton').click();
    
    // Send a message that might trigger an error
    await page.locator('#chatInput').fill('trigger_error');
    await page.locator('.send-button').click();
    
    // Wait for error response
    await page.waitForTimeout(1000);
    
    // Verify error message appears
    const errorMessage = page.locator('.message.assistant:has-text("error")');
    await expect(errorMessage).toBeVisible();
  });
});

