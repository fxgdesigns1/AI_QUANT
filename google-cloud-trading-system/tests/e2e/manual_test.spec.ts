import { test, expect } from '@playwright/test';

test.describe('Manual Function Test', () => {
  test('should manually call API functions', async ({ page }) => {
    await page.goto('https://ai-quant-trading.uc.r.appspot.com/');
    await page.waitForLoadState('networkidle');
    
    // Wait a bit for page to load
    await page.waitForTimeout(5000);
    
    // Manually call the API endpoints and update the DOM
    const result = await page.evaluate(async () => {
      try {
        // Test accounts API
        const accountsResponse = await fetch('/api/accounts');
        const accountsData = await accountsResponse.json();
        console.log('Accounts API Response:', accountsData);
        
        // Update account status manually
        const accountContainer = document.getElementById('account-status');
        if (accountContainer && accountsData.accounts) {
          accountContainer.innerHTML = '';
          Object.entries(accountsData.accounts).forEach(([name, account]: [string, any]) => {
            const plClass = account.total_pl >= 0 ? 'pl-positive' : 'pl-negative';
            const plSign = account.total_pl >= 0 ? '+' : '';
            
            accountContainer.innerHTML += `
              <div class="account-card">
                <div class="account-header">
                  <span class="account-name">${name}</span>
                  <span class="account-balance">$${account.balance.toLocaleString()}</span>
                </div>
                <div class="account-pl ${plClass}">${plSign}$${account.total_pl.toFixed(2)} (${plSign}${account.pl_percentage.toFixed(2)}%)</div>
                <div>Positions: ${account.open_positions} | Margin: ${account.margin_used.toFixed(1)}%</div>
              </div>
            `;
          });
        }
        
        // Test prices API
        const pricesResponse = await fetch('/api/prices');
        const pricesData = await pricesResponse.json();
        console.log('Prices API Response:', pricesData);
        
        // Update prices manually
        const pricesContainer = document.getElementById('live-prices');
        if (pricesContainer && pricesData.prices) {
          pricesContainer.innerHTML = '';
          Object.entries(pricesData.prices).forEach(([instrument, price]: [string, any]) => {
            const spread = (price.ask - price.bid).toFixed(5);
            const timestamp = new Date(price.timestamp).toLocaleTimeString();
            
            pricesContainer.innerHTML += `
              <div class="signal-item" style="margin-bottom: 10px;">
                <strong>${instrument}</strong><br>
                <div style="font-size: 14px; margin: 5px 0;">
                  Bid: <span style="color: #4CAF50;">${price.bid.toFixed(5)}</span> | 
                  Ask: <span style="color: #f44336;">${price.ask.toFixed(5)}</span>
                </div>
                <div style="font-size: 11px; color: #9ca3af;">
                  Spread: ${spread} | Live: ${timestamp}
                </div>
              </div>
            `;
          });
        }
        
        return { success: true, accountsCount: Object.keys(accountsData.accounts || {}).length, pricesCount: Object.keys(pricesData.prices || {}).length };
      } catch (error) {
        return { success: false, error: error.message };
      }
    });
    
    console.log('Manual API Test Result:', result);
    
    // Check if data was loaded
    const accountStatus = await page.locator('#account-status').textContent();
    const livePrices = await page.locator('#live-prices').textContent();
    
    console.log('Account Status After Manual Update:', accountStatus);
    console.log('Live Prices After Manual Update:', livePrices);
    
    // Should not contain loading messages
    expect(accountStatus).not.toContain('Loading live account data');
    expect(livePrices).not.toContain('Loading live market prices');
    
    // Should contain actual data
    expect(accountStatus).toContain('101-004-30719775');
    expect(livePrices).toContain('EUR_USD');
  });
});

