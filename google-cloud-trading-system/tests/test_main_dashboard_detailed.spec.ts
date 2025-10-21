/**
 * Comprehensive Main Trading Dashboard Test
 * Verify all elements are displaying correctly
 */

import { test, expect } from '@playwright/test';

const DASHBOARD_URL = 'https://ai-quant-trading.uc.r.appspot.com/dashboard';

test.describe('Main Trading Dashboard Detailed Tests', () => {
  
  test('Main dashboard - comprehensive element check', async ({ page }) => {
    console.log('🔍 Testing main trading dashboard comprehensively...');
    
    // Navigate with extended timeout
    await page.goto(DASHBOARD_URL, { 
      waitUntil: 'domcontentloaded',
      timeout: 90000 
    });
    
    // Wait for initial content
    await page.waitForTimeout(10000);
    
    // Take screenshot
    await page.screenshot({ 
      path: 'main_dashboard_full.png', 
      fullPage: true 
    });
    console.log('📸 Full screenshot saved: main_dashboard_full.png');
    
    // Check page basics
    const title = await page.title();
    console.log(`\n📋 Page Title: ${title}`);
    
    const h1Text = await page.locator('h1').first().textContent().catch(() => 'No H1');
    console.log(`📋 Main Heading: ${h1Text}`);
    
    // Check for account sections
    console.log('\n🔍 Checking for account elements:');
    const accountElements = await page.locator('text=/PRIMARY|GOLD_SCALP|STRATEGY_ALPHA/i').count();
    console.log(`  • Account names found: ${accountElements}`);
    
    // Check for balance displays
    const balanceElements = await page.locator('text=/Balance|\\$/').count();
    console.log(`  • Balance elements found: ${balanceElements}`);
    
    // Check for market data
    const priceElements = await page.locator('text=/EUR_USD|GBP_USD|USD_JPY|XAU_USD/').count();
    console.log(`  • Price elements found: ${priceElements}`);
    
    // Check for news section
    const newsElements = await page.locator('text=/News|Sentiment|Market/i').count();
    console.log(`  • News elements found: ${newsElements}`);
    
    // Check for AI assistant
    const aiElements = await page.locator('text=/AI|Assistant|Chat/i').count();
    console.log(`  • AI elements found: ${aiElements}`);
    
    // Get all visible text
    const bodyText = await page.textContent('body');
    
    console.log('\n📊 Content Analysis:');
    console.log(`  • Page contains "account": ${bodyText?.toLowerCase().includes('account')}`);
    console.log(`  • Page contains "balance": ${bodyText?.toLowerCase().includes('balance')}`);
    console.log(`  • Page contains "trading": ${bodyText?.toLowerCase().includes('trading')}`);
    console.log(`  • Page contains prices: ${bodyText?.includes('USD')}`);
    console.log(`  • Total page length: ${bodyText?.length} characters`);
    
    // Check specific sections by ID
    const sections = [
      'accounts-section',
      'market-data-section', 
      'news-section',
      'ai-assistant-section',
      'positions-section'
    ];
    
    console.log('\n🔍 Checking dashboard sections:');
    for (const sectionId of sections) {
      const exists = await page.locator(`#${sectionId}`).count() > 0;
      console.log(`  • ${sectionId}: ${exists ? '✅' : '❌'}`);
    }
    
    // Log all h1, h2, h3 headings
    const headings = await page.locator('h1, h2, h3').allTextContents();
    console.log('\n📋 All headings found:');
    headings.forEach((h, i) => console.log(`  ${i + 1}. ${h}`));
    
    // Check for any error messages
    const hasError = bodyText?.toLowerCase().includes('error') || 
                     bodyText?.toLowerCase().includes('failed') ||
                     bodyText?.toLowerCase().includes('unavailable');
    console.log(`\n⚠️  Contains error messages: ${hasError}`);
    
    if (hasError) {
      console.log('  Error text found - checking details...');
      const errorText = await page.locator('text=/error|failed|unavailable/i').allTextContents();
      errorText.slice(0, 3).forEach(err => console.log(`    • ${err}`));
    }
  });

  test('Check if WebSocket is connecting', async ({ page }) => {
    console.log('🔍 Testing WebSocket connection...');
    
    await page.goto(DASHBOARD_URL, { waitUntil: 'domcontentloaded', timeout: 90000 });
    
    // Listen for console logs
    const consoleLogs: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'log' || msg.type() === 'error') {
        consoleLogs.push(`${msg.type()}: ${msg.text()}`);
      }
    });
    
    await page.waitForTimeout(8000);
    
    console.log('\n📝 Browser console logs:');
    consoleLogs.slice(0, 10).forEach(log => console.log(`  ${log}`));
    
    // Check if WebSocket connected
    const wsConnected = consoleLogs.some(log => 
      log.includes('WebSocket') || 
      log.includes('socket') || 
      log.includes('Connected')
    );
    
    console.log(`\n🔌 WebSocket connection detected: ${wsConnected}`);
  });

  test('Check what data is actually loaded', async ({ page }) => {
    console.log('🔍 Checking loaded data...');
    
    await page.goto(DASHBOARD_URL, { waitUntil: 'domcontentloaded', timeout: 90000 });
    await page.waitForTimeout(8000);
    
    // Try to find specific data elements
    const dataChecks = {
      'Has dollar amounts': await page.locator('text=/\\$[0-9,]+/').count() > 0,
      'Has percentages': await page.locator('text=/[0-9]+%/').count() > 0,
      'Has account names': await page.locator('text=/PRIMARY|GOLD|ALPHA/i').count() > 0,
      'Has instruments': await page.locator('text=/EUR|GBP|USD|XAU/').count() > 0,
      'Has "Loading"': await page.locator('text=Loading').count() > 0
    };
    
    console.log('\n📊 Data presence check:');
    for (const [check, result] of Object.entries(dataChecks)) {
      console.log(`  ${result ? '✅' : '❌'} ${check}`);
    }
  });

});

