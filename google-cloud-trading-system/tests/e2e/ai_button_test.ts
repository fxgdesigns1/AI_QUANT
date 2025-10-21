import { test, expect } from '@playwright/test';

test('AI Button Test', async ({ page }) => {
  // Navigate to the dashboard
  await page.goto('http://localhost:5005');
  
  // Wait for page load
  await page.waitForLoadState('networkidle');
  
  // Log initial page state
  console.log('🔍 Looking for AI button...');
  
  // Check if AI button exists
  const aiButton = await page.locator('button.ai-toggle');
  
  // Log button properties
  const buttonVisible = await aiButton.isVisible();
  console.log('Button visible:', buttonVisible);
  
  if (buttonVisible) {
    // Get button properties
    const buttonHTML = await aiButton.evaluate(el => el.outerHTML);
    console.log('Button HTML:', buttonHTML);
    
    // Try clicking the button
    console.log('🖱️ Clicking AI button...');
    await aiButton.click();
    
    // Check if panel appears
    const aiPanel = await page.locator('.ai-assistant-panel');
    const panelVisible = await aiPanel.isVisible();
    console.log('Panel visible after click:', panelVisible);
    
    // Get panel HTML
    const panelHTML = await aiPanel.evaluate(el => el.outerHTML);
    console.log('Panel HTML:', panelHTML);
  }
});

