const { chromium } = require('playwright');

async function testAIAssistant() {
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();
  
  try {
    console.log('🌐 Opening dashboard...');
    await page.goto('http://localhost:5001');
    await page.waitForLoadState('domcontentloaded');
    
    console.log('🔍 Looking for AI button...');
    const aiButton = await page.locator('.ai-toggle');
    await aiButton.waitFor({ timeout: 5000 });
    
    console.log('🤖 Clicking AI button...');
    await aiButton.click();
    
    console.log('🔍 Looking for AI panel...');
    const aiPanel = await page.locator('.ai-assistant-panel');
    await aiPanel.waitFor({ timeout: 5000 });
    
    console.log('✅ AI Assistant panel opened successfully!');
    
    console.log('💬 Testing chat input...');
    const chatInput = await page.locator('#chatInput');
    await chatInput.fill('market overview');
    
    console.log('📤 Sending message...');
    const sendButton = await page.locator('.send-button');
    await sendButton.click();
    
    console.log('⏳ Waiting for response...');
    await page.waitForTimeout(2000);
    
    console.log('✅ AI Assistant test completed successfully!');
    
  } catch (error) {
    console.error('❌ Test failed:', error.message);
  } finally {
    await browser.close();
  }
}

testAIAssistant();

