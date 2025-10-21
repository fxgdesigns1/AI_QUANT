/**
 * AI Insights Section - Verification Test
 * Tests that the AI Insights section now loads properly
 */

import { test, expect } from '@playwright/test';

test.describe('AI Insights Section Fix Verification', () => {
  
  test('Verify AI Insights section is NOT stuck on "System initializing"', async ({ page }) => {
    console.log('\n🔍 Testing AI Insights Section...');
    
    await page.goto('https://ai-quant-trading.uc.r.appspot.com/dashboard', {
      waitUntil: 'domcontentloaded',
      timeout: 90000
    });
    
    // Wait for WebSocket connection and data load
    console.log('⏳ Waiting for data to load (15 seconds)...');
    await page.waitForTimeout(15000);
    
    // Check Trade Phase
    const tradePhase = await page.locator('#tradePhase').textContent();
    console.log(`\n📊 Trade Phase: ${tradePhase}`);
    
    // Should NOT be "Analyzing market conditions..." (the default loading text)
    expect(tradePhase).not.toBe('Analyzing market conditions...');
    
    // Should contain actual data
    const hasRealData = tradePhase?.includes('BULLISH') || 
                        tradePhase?.includes('BEARISH') || 
                        tradePhase?.includes('NEUTRAL') ||
                        tradePhase?.includes('Monitoring');
    
    console.log(`   ${hasRealData ? '✅' : '❌'} Contains real trading phase`);
    expect(hasRealData).toBe(true);
    
    // Check Upcoming News section
    const upcomingNews = await page.locator('#upcomingNews').textContent();
    console.log(`\n📰 Upcoming News section: ${upcomingNews?.substring(0, 100)}...`);
    
    // Should NOT be "System initializing"
    expect(upcomingNews).not.toContain('System initializing');
    expect(upcomingNews).not.toContain('Loading AI analysis...');
    
    // Should have real data
    const hasNewsData = upcomingNews?.includes('Fed Funds') || 
                        upcomingNews?.includes('CPI') ||
                        upcomingNews?.includes('monitoring') ||
                        upcomingNews?.includes('AI');
    
    console.log(`   ${hasNewsData ? '✅' : '❌'} Contains real news/economic data`);
    expect(hasNewsData).toBe(true);
    
    // Take screenshot
    await page.screenshot({ path: 'ai_insights_fixed.png', fullPage: true });
    console.log('\n📸 Screenshot saved: ai_insights_fixed.png');
    
    console.log('\n✅ AI Insights section is NOW WORKING!');
  });
  
  test('Verify API provides trade_phase and upcoming_news', async ({ page }) => {
    console.log('\n🔍 Testing API Data...');
    
    const response = await page.request.get('https://ai-quant-trading.uc.r.appspot.com/api/status');
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    
    // Check for required fields
    console.log('\n📊 API Fields Check:');
    console.log(`   ${data.trade_phase ? '✅' : '❌'} trade_phase: ${data.trade_phase}`);
    console.log(`   ${data.upcoming_news ? '✅' : '❌'} upcoming_news: ${data.upcoming_news?.length} items`);
    console.log(`   ${data.ai_recommendation ? '✅' : '❌'} ai_recommendation: ${data.ai_recommendation}`);
    
    expect(data).toHaveProperty('trade_phase');
    expect(data).toHaveProperty('upcoming_news');
    expect(data).toHaveProperty('ai_recommendation');
    
    // Trade phase should not be empty or default
    expect(data.trade_phase).toBeTruthy();
    expect(data.trade_phase).not.toBe('Analyzing market conditions...');
    
    // Upcoming news should be an array
    expect(Array.isArray(data.upcoming_news)).toBe(true);
    
    console.log('\n✅ API is providing all required AI insights data!');
  });

});

