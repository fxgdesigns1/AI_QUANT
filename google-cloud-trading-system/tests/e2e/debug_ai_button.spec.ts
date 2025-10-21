import { test, expect } from '@playwright/test';

test('Debug AI Button', async ({ page }) => {
  await page.goto('https://ai-quant-trading.uc.r.appspot.com/');
  await page.waitForLoadState('networkidle');
  
  // Check console logs
  const logs = [];
  page.on('console', msg => logs.push(msg.text()));
  
  // Check for JavaScript errors
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  
  // Wait for page to fully load
  await page.waitForTimeout(5000);
  
  console.log('Console logs:', logs);
  console.log('Page errors:', errors);
  
  // Check if AI button exists
  const aiButton = page.locator('#aiToggleButton');
  const buttonExists = await aiButton.count() > 0;
  console.log('AI button exists:', buttonExists);
  
  if (buttonExists) {
    const isVisible = await aiButton.isVisible();
    console.log('AI button visible:', isVisible);
    
    if (isVisible) {
      // Try to click the button
      await aiButton.click();
      await page.waitForTimeout(1000);
      
      // Check if panel exists
      const aiPanel = page.locator('#aiAssistantPanel');
      const panelExists = await aiPanel.count() > 0;
      console.log('AI panel exists:', panelExists);
      
      if (panelExists) {
        const panelVisible = await aiPanel.isVisible();
        console.log('AI panel visible after click:', panelVisible);
        
        // Check panel style
        const panelStyle = await aiPanel.evaluate(el => el.style.display);
        console.log('AI panel display style:', panelStyle);
      }
    }
  }
  
  // Check if functions exist
  const functionsExist = await page.evaluate(() => {
    return {
      toggleAIAssistant: typeof window.toggleAIAssistant,
      initAIAssistant: typeof window.initAIAssistant,
      sendAIMessage: typeof window.sendAIMessage
    };
  });
  
  console.log('Functions exist:', functionsExist);
  
  // Take screenshot
  await page.screenshot({ path: 'debug_ai_button.png' });
});

