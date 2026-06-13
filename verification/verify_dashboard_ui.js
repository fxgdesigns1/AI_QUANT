#!/usr/bin/env node
/**
 * Quick dashboard UI verification script
 * Uses Puppeteer to capture screenshots and verify transparency features
 */

const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

const DASHBOARD_URL = process.env.DASHBOARD_URL || 'http://127.0.0.1:8787';

async function verifyDashboard() {
  console.log(`\n🔍 Verifying Dashboard UI at ${DASHBOARD_URL}\n`);
  
  const browser = await puppeteer.launch({ headless: false });
  const page = await browser.newPage();
  
  try {
    // Navigate to dashboard
    console.log('📡 Loading dashboard...');
    await page.goto(DASHBOARD_URL, { waitUntil: 'networkidle2', timeout: 30000 });
    
    // Wait for page to load
    await page.waitForTimeout(3000);
    
    // Take screenshot
    const screenshotDir = path.join(__dirname, '..', 'ARTIFACTS');
    if (!fs.existsSync(screenshotDir)) {
      fs.mkdirSync(screenshotDir, { recursive: true });
    }
    
    const screenshotPath = path.join(screenshotDir, 'dashboard_verification.png');
    await page.screenshot({ path: screenshotPath, fullPage: true });
    console.log(`✅ Screenshot saved: ${screenshotPath}`);
    
    // Check for transparency features
    console.log('\n🔍 Checking transparency features...\n');
    
    // 1. Check block reason element
    const blockReason = await page.$('#block-reason');
    if (blockReason) {
      const isVisible = await page.evaluate((el) => {
        return el.offsetParent !== null && !el.classList.contains('hidden');
      }, blockReason);
      const text = await page.evaluate((el) => el.textContent, blockReason);
      console.log(`📋 Block Reason Element: ${isVisible ? 'VISIBLE' : 'HIDDEN'}`);
      if (text) console.log(`   Text: "${text}"`);
    } else {
      console.log('❌ Block Reason Element: NOT FOUND');
    }
    
    // 2. Check readiness status
    const readinessStatus = await page.$('#readiness-status');
    if (readinessStatus) {
      const text = await page.evaluate((el) => el.textContent, readinessStatus);
      console.log(`📊 Readiness Status: "${text}"`);
    } else {
      console.log('❌ Readiness Status: NOT FOUND');
    }
    
    // 3. Check next session countdown
    const nextSessionCountdown = await page.$('#next-session-countdown');
    if (nextSessionCountdown) {
      const text = await page.evaluate((el) => el.textContent, nextSessionCountdown);
      console.log(`⏰ Next Session Countdown: "${text}"`);
    } else {
      console.log('❌ Next Session Countdown: NOT FOUND');
    }
    
    // 4. Check readiness score
    const readinessScore = await page.$('#readiness-score-value');
    if (readinessScore) {
      const text = await page.evaluate((el) => el.textContent, readinessScore);
      console.log(`🎯 Readiness Score: "${text}"`);
    } else {
      console.log('❌ Readiness Score: NOT FOUND');
    }
    
    // 5. Check current session
    const currentSession = await page.$('#current-session');
    if (currentSession) {
      const text = await page.evaluate((el) => el.textContent, currentSession);
      console.log(`🌍 Current Session: "${text}"`);
    } else {
      console.log('❌ Current Session: NOT FOUND');
    }
    
    // 6. Check API response
    console.log('\n📡 Checking API endpoint...');
    try {
      const response = await page.goto(`${DASHBOARD_URL}/api/session-regime-gate/snapshot`);
      if (response.status() === 200) {
        const data = await response.json();
        console.log('✅ API endpoint responding');
        console.log(`   Readiness: ${data.data?.readiness || 'N/A'}`);
        console.log(`   Block Reason: ${data.data?.trade_block_reason || 'N/A'}`);
        console.log(`   Next Session: ${data.data?.next_session?.next_tradable_session || 'N/A'}`);
      } else {
        console.log(`❌ API endpoint returned ${response.status()}`);
      }
    } catch (e) {
      console.log(`❌ API endpoint error: ${e.message}`);
      console.log('   ⚠️  Server may need restart to load new transparency code');
    }
    
    // 7. Check console for errors
    const consoleErrors = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });
    
    await page.waitForTimeout(2000);
    
    if (consoleErrors.length > 0) {
      console.log('\n⚠️  Console errors found:');
      consoleErrors.forEach(err => console.log(`   - ${err}`));
    }
    
    console.log('\n✅ Verification complete\n');
    
  } catch (error) {
    console.error('\n❌ Verification failed:', error.message);
    process.exit(1);
  } finally {
    await browser.close();
  }
}

verifyDashboard().catch(console.error);
