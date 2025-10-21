import { test, expect } from '@playwright/test';

test('Basic AI Assistant Test', async ({ page }) => {
  // Go to the page
  await page.goto('http://localhost:5005');
  
  // Verify AI button exists and is visible
  const aiButton = await page.locator('.ai-button');
  await expect(aiButton).toBeVisible();
  
  // Verify AI panel exists and is visible
  const aiPanel = await page.locator('.ai-panel');
  await expect(aiPanel).toBeVisible();
  
  // Type and send a message
  await page.locator('#messageInput').fill('market overview');
  await page.locator('button:text("Send")').click();
  
  // Wait for response
  await page.waitForSelector('.message.ai');
  
  // Verify response
  const messages = await page.locator('.message').all();
  expect(messages.length).toBeGreaterThan(1);
});

