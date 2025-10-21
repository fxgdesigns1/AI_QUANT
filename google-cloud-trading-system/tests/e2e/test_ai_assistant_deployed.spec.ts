import { test, expect } from '@playwright/test';

test.describe('AI Assistant Integration Tests - Deployed', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to deployed dashboard
    await page.goto('https://ai-quant-trading.uc.r.appspot.com/');
    await page.waitForLoadState('networkidle');
  });

  test('should show AI button and toggle panel', async ({ page }) => {
    // Check if AI button is visible
    const aiButton = page.locator('#aiToggleButton');
    await expect(aiButton).toBeVisible();
    
    // Check if AI panel is initially hidden
    const aiPanel = page.locator('#aiAssistantPanel');
    await expect(aiPanel).not.toBeVisible();
    
    // Click AI button to open panel
    await aiButton.click();
    await expect(aiPanel).toBeVisible();
    
    // Check panel content
    await expect(page.locator('.ai-assistant-title')).toContainText('🤖 AI Assistant');
    await expect(page.locator('.ai-mode-badge')).toContainText('Demo Mode');
    
    // Close panel
    await page.locator('button:has-text("×")').click();
    await expect(aiPanel).not.toBeVisible();
  });

  test('should send and receive AI messages', async ({ page }) => {
    // Open AI panel
    await page.locator('#aiToggleButton').click();
    await page.waitForSelector('#aiAssistantPanel', { state: 'visible' });
    
    // Send a message
    const messageInput = page.locator('#aiMessageInput');
    await messageInput.fill('What is the current market status?');
    await page.locator('.send-button').click();
    
    // Wait for response
    await page.waitForTimeout(2000);
    
    // Check if user message appears
    const userMessage = page.locator('.message.user').last();
    await expect(userMessage).toContainText('What is the current market status?');
    
    // Check if AI response appears
    const aiMessage = page.locator('.message.assistant').last();
    await expect(aiMessage).toBeVisible();
  });

  test('should handle Enter key to send messages', async ({ page }) => {
    // Open AI panel
    await page.locator('#aiToggleButton').click();
    await page.waitForSelector('#aiAssistantPanel', { state: 'visible' });
    
    // Send message using Enter key
    const messageInput = page.locator('#aiMessageInput');
    await messageInput.fill('Show me the portfolio status');
    await messageInput.press('Enter');
    
    // Wait for response
    await page.waitForTimeout(2000);
    
    // Check if message was sent
    const userMessage = page.locator('.message.user').last();
    await expect(userMessage).toContainText('Show me the portfolio status');
  });

  test('should test AI health endpoint', async ({ page }) => {
    // Test AI health endpoint directly
    const response = await page.request.get('https://ai-quant-trading.uc.r.appspot.com/ai/health');
    expect(response.status()).toBe(200);
    
    const data = await response.json();
    expect(data.status).toBe('healthy');
    expect(data.mode).toBe('demo');
  });

  test('should test AI interpret endpoint', async ({ page }) => {
    // Test AI interpret endpoint directly
    const response = await page.request.post('https://ai-quant-trading.uc.r.appspot.com/ai/interpret', {
      data: { message: 'What is the current market status?' }
    });
    
    expect(response.status()).toBe(200);
    
    const data = await response.json();
    expect(data.reply).toBeDefined();
    expect(data.mode).toBe('demo');
  });
});

