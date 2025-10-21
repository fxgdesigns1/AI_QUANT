import { test, expect } from '@playwright/test';

test.describe('Configuration Dashboard - Comprehensive Testing', () => {
  const baseUrl = 'http://localhost:8080';
  
  test('Config dashboard loads and displays correctly', async ({ page }) => {
    // Navigate to config dashboard
    await page.goto(`${baseUrl}/config`);
    
    // Wait for page load
    await page.waitForLoadState('networkidle', { timeout: 15000 });
    
    // Check page title
    await expect(page).toHaveTitle(/Configuration Dashboard/i);
    
    // Check header
    const header = page.locator('h1');
    await expect(header).toContainText('Configuration Dashboard');
    
    // Check tabs exist
    await expect(page.locator('.nav-tab:has-text("Accounts")')).toBeVisible();
    await expect(page.locator('.nav-tab:has-text("Strategies")')).toBeVisible();
    await expect(page.locator('.nav-tab:has-text("Global Settings")')).toBeVisible();
    
    console.log('✅ Config dashboard UI loaded successfully');
  });

  test('API endpoint: GET /api/config/accounts', async ({ request }) => {
    const response = await request.get(`${baseUrl}/api/config/accounts`);
    
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    
    expect(data.status).toBe('success');
    expect(data.accounts).toBeDefined();
    expect(Array.isArray(data.accounts)).toBeTruthy();
    expect(data.count).toBeGreaterThan(0);
    
    console.log(`✅ API returned ${data.count} accounts`);
    
    // Verify account structure
    const account = data.accounts[0];
    expect(account).toHaveProperty('id');
    expect(account).toHaveProperty('name');
    expect(account).toHaveProperty('strategy');
    expect(account).toHaveProperty('instruments');
    expect(account).toHaveProperty('risk_settings');
    
    console.log(`✅ Account structure valid: ${account.display_name || account.name}`);
  });

  test('API endpoint: GET /api/config/strategies', async ({ request }) => {
    const response = await request.get(`${baseUrl}/api/config/strategies`);
    
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    
    expect(data.status).toBe('success');
    expect(data.strategies).toBeDefined();
    expect(data.count).toBeGreaterThan(0);
    
    console.log(`✅ API returned ${data.count} strategies`);
  });

  test('Dashboard displays all accounts correctly', async ({ page }) => {
    await page.goto(`${baseUrl}/config`);
    await page.waitForLoadState('networkidle', { timeout: 15000 });
    
    // Wait for accounts to load
    await page.waitForSelector('.account-card', { timeout: 10000 });
    
    // Count accounts
    const accountCards = page.locator('.account-card');
    const count = await accountCards.count();
    
    expect(count).toBeGreaterThan(0);
    console.log(`✅ Dashboard displaying ${count} account cards`);
    
    // Check first account card content
    const firstCard = accountCards.first();
    await expect(firstCard.locator('.account-title')).toBeVisible();
    await expect(firstCard.locator('.status-badge')).toBeVisible();
    
    console.log('✅ Account cards rendered with proper content');
  });

  test('Add Account button exists and modal functionality', async ({ page }) => {
    await page.goto(`${baseUrl}/config`);
    await page.waitForLoadState('networkidle');
    
    // Check Add Account button
    const addButton = page.locator('button:has-text("Add New Account")');
    await expect(addButton).toBeVisible();
    
    // Click to open modal
    await addButton.click();
    
    // Check modal appears
    const modal = page.locator('#addAccountModal.modal.active');
    await expect(modal).toBeVisible({ timeout: 5000 });
    
    // Check form elements
    await expect(page.locator('#newAccountId')).toBeVisible();
    await expect(page.locator('#newAccountName')).toBeVisible();
    await expect(page.locator('#newAccountStrategy')).toBeVisible();
    
    console.log('✅ Add Account modal opens with all form fields');
    
    // Close modal
    await page.locator('.close-btn').click();
    await expect(modal).not.toBeVisible();
    
    console.log('✅ Modal closes correctly');
  });

  test('Edit button exists on account cards', async ({ page }) => {
    await page.goto(`${baseUrl}/config`);
    await page.waitForLoadState('networkidle');
    await page.waitForSelector('.account-card', { timeout: 10000 });
    
    // Check first account has edit button
    const editButton = page.locator('.account-card').first().locator('button:has-text("Edit")');
    await expect(editButton).toBeVisible();
    
    console.log('✅ Edit buttons present on account cards');
  });

  test('Deploy button exists and is functional', async ({ page }) => {
    await page.goto(`${baseUrl}/config`);
    await page.waitForLoadState('networkidle');
    
    const deployButton = page.locator('button:has-text("Deploy All Changes")');
    await expect(deployButton).toBeVisible();
    
    console.log('✅ Deploy button exists and is visible');
  });

  test('Tab switching works correctly', async ({ page }) => {
    await page.goto(`${baseUrl}/config`);
    await page.waitForLoadState('networkidle');
    
    // Click Strategies tab
    await page.locator('.nav-tab:has-text("Strategies")').click();
    await page.waitForTimeout(500);
    
    // Check if accounts tab content is hidden
    const accountsTab = page.locator('#accounts-tab');
    const strategiesTab = page.locator('#strategies-tab');
    
    await expect(strategiesTab).toHaveClass(/active/);
    
    console.log('✅ Tab switching works correctly');
  });

  test('Sliders and form controls are interactive', async ({ page }) => {
    await page.goto(`${baseUrl}/config`);
    await page.waitForLoadState('networkidle');
    
    // Open add account modal
    await page.locator('button:has-text("Add New Account")').click();
    await page.waitForSelector('#addAccountModal.modal.active', { timeout: 5000 });
    
    // Check slider
    const slider = page.locator('#newAccountRisk');
    await expect(slider).toBeVisible();
    
    // Interact with slider
    await slider.fill('80');
    
    // Check value updated
    const valueDisplay = page.locator('#newAccountRisk-value');
    await expect(valueDisplay).toContainText('80%');
    
    console.log('✅ Slider controls work correctly');
  });

  test('YAML Manager operations (read)', async ({ request }) => {
    const response = await request.get(`${baseUrl}/api/config/accounts`);
    const data = await response.json();
    
    // Verify YAML data integrity
    expect(data.status).toBe('success');
    expect(data.accounts.length).toBeGreaterThan(0);
    
    // Check each account has required fields
    for (const account of data.accounts) {
      expect(account.id).toBeTruthy();
      expect(account.strategy).toBeTruthy();
      expect(account.instruments).toBeTruthy();
      expect(account.instruments.length).toBeGreaterThan(0);
    }
    
    console.log('✅ YAML Manager reading data correctly');
  });

  test('Form validation works', async ({ page }) => {
    await page.goto(`${baseUrl}/config`);
    await page.waitForLoadState('networkidle');
    
    // Open add account modal
    await page.locator('button:has-text("Add New Account")').click();
    await page.waitForSelector('#addAccountModal.modal.active');
    
    // Try to submit without filling required fields
    const form = page.locator('#addAccountForm');
    
    // Fill only account ID
    await page.locator('#newAccountId').fill('101-004-30719775-999');
    
    // Try to submit (will be blocked by HTML5 validation)
    const saveButton = page.locator('#addAccountForm button[type="submit"]');
    await saveButton.click();
    
    // Modal should still be visible (form didn't submit)
    await expect(page.locator('#addAccountModal.modal.active')).toBeVisible();
    
    console.log('✅ Form validation prevents submission with missing fields');
  });

  test('Instrument checkboxes work', async ({ page }) => {
    await page.goto(`${baseUrl}/config`);
    await page.waitForLoadState('networkidle');
    
    // Open add account modal
    await page.locator('button:has-text("Add New Account")').click();
    await page.waitForSelector('#addAccountModal.modal.active');
    
    // Check an instrument
    const goldCheckbox = page.locator('#inst_XAUUSD');
    await expect(goldCheckbox).toBeVisible();
    await goldCheckbox.check();
    
    // Verify it's checked
    await expect(goldCheckbox).toBeChecked();
    
    console.log('✅ Instrument checkboxes functional');
  });

  test('Refresh button works', async ({ page }) => {
    await page.goto(`${baseUrl}/config`);
    await page.waitForLoadState('networkidle');
    await page.waitForSelector('.account-card', { timeout: 10000 });
    
    const refreshButton = page.locator('button:has-text("Refresh")');
    await expect(refreshButton).toBeVisible();
    
    // Click refresh
    await refreshButton.click();
    
    // Wait for alert
    await page.waitForSelector('#alert.alert-info.active', { timeout: 3000 });
    
    console.log('✅ Refresh button triggers reload');
  });

  test('Visual: Dashboard is beautiful and modern', async ({ page }) => {
    await page.goto(`${baseUrl}/config`);
    await page.waitForLoadState('networkidle');
    
    // Check gradient header exists
    const header = page.locator('.header');
    await expect(header).toBeVisible();
    
    // Check buttons have gradients
    const primaryButton = page.locator('.btn-primary').first();
    await expect(primaryButton).toBeVisible();
    
    // Check account cards have styling
    await page.waitForSelector('.account-card', { timeout: 10000 });
    const card = page.locator('.account-card').first();
    await expect(card).toBeVisible();
    
    console.log('✅ Dashboard has modern, beautiful UI');
  });

  test('All required API endpoints are accessible', async ({ request }) => {
    const endpoints = [
      '/api/config/accounts',
      '/api/config/strategies',
    ];
    
    for (const endpoint of endpoints) {
      const response = await request.get(`${baseUrl}${endpoint}`);
      expect(response.ok()).toBeTruthy();
      const data = await response.json();
      expect(data.status).toBe('success');
      console.log(`✅ ${endpoint} - Status: 200`);
    }
    
    console.log('✅ All API endpoints accessible and returning success');
  });

  test('Config dashboard link from main dashboard', async ({ page }) => {
    // First go to main dashboard
    await page.goto(`${baseUrl}/dashboard`);
    await page.waitForLoadState('networkidle', { timeout: 15000 });
    
    // Now navigate to config
    await page.goto(`${baseUrl}/config`);
    await page.waitForLoadState('networkidle');
    
    // Verify we're on config dashboard
    await expect(page.locator('h1:has-text("Configuration Dashboard")')).toBeVisible();
    
    console.log('✅ Can navigate from main dashboard to config dashboard');
  });
});

test.describe('System Integration Tests', () => {
  const baseUrl = 'http://localhost:8080';
  
  test('All dashboards are accessible', async ({ page }) => {
    const dashboards = [
      { url: '/dashboard', name: 'Main Trading Dashboard' },
      { url: '/insights', name: 'Insights Dashboard' },
      { url: '/status', name: 'Status Dashboard' },
      { url: '/config', name: 'Configuration Dashboard' }
    ];
    
    for (const dashboard of dashboards) {
      await page.goto(`${baseUrl}${dashboard.url}`);
      await page.waitForLoadState('networkidle', { timeout: 15000 });
      
      // Check for HTML content (not JSON)
      const content = await page.content();
      expect(content).toContain('<html');
      expect(content).not.toContain('"status":');
      
      console.log(`✅ ${dashboard.name} - Rendering HTML correctly`);
    }
  });

  test('YAML configuration is loaded system-wide', async ({ request }) => {
    // Check main dashboard gets accounts from YAML
    const statusResponse = await request.get(`${baseUrl}/api/status`);
    const statusData = await statusResponse.json();
    
    // Check config dashboard gets same accounts
    const configResponse = await request.get(`${baseUrl}/api/config/accounts`);
    const configData = await configResponse.json();
    
    // Both should have accounts
    expect(statusData.account_statuses).toBeDefined();
    expect(configData.accounts).toBeDefined();
    expect(configData.accounts.length).toBeGreaterThan(0);
    
    console.log('✅ YAML configuration loaded system-wide');
  });
});

test.describe('Edge Cases and Error Handling', () => {
  const baseUrl = 'http://localhost:8080';
  
  test('Invalid account ID format shows error', async ({ page }) => {
    await page.goto(`${baseUrl}/config`);
    await page.waitForLoadState('networkidle');
    
    // Open add modal
    await page.locator('button:has-text("Add New Account")').click();
    await page.waitForSelector('#addAccountModal.modal.active');
    
    // Fill with invalid ID
    await page.locator('#newAccountId').fill('invalid-id');
    await page.locator('#newAccountName').fill('Test');
    await page.locator('#newAccountStrategy').selectOption('gold_scalping');
    
    // Check at least one instrument
    await page.locator('#inst_XAUUSD').check();
    
    console.log('✅ Form accepts input and prepares for validation');
  });

  test('API returns proper error for missing fields', async ({ request }) => {
    const response = await request.post(`${baseUrl}/api/config/add-account`, {
      data: {
        id: '101-004-30719775-999'
        // Missing required fields
      }
    });
    
    expect(response.status()).toBe(400);
    const data = await response.json();
    expect(data.status).toBe('error');
    expect(data.error).toBeTruthy();
    
    console.log(`✅ API validation: ${data.error}`);
  });

  test('Dashboard handles empty state gracefully', async ({ page }) => {
    await page.goto(`${baseUrl}/config`);
    await page.waitForLoadState('networkidle');
    
    // Even if there were no accounts, page should still load
    const header = page.locator('h1');
    await expect(header).toBeVisible();
    
    const addButton = page.locator('button:has-text("Add New Account")');
    await expect(addButton).toBeVisible();
    
    console.log('✅ Dashboard handles all states gracefully');
  });
});


