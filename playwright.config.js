// Playwright configuration for dashboard testing
// Supports both mock API and live VM testing via Cloudflare Tunnel

const { defineConfig, devices } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './tests/dashboard',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [
    ['html'],
    ['json', { outputFile: 'test-results/results.json' }],
    ['list']
  ],
  use: {
    // Default to tunnel URL if not specified
    baseURL: process.env.DASHBOARD_URL || 'https://alpha-dashboard.fxg.internal',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    // Disable storage state to ensure auth-free access
    storageState: undefined,
  },
  
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
  ],

  // Web server for serving mock API (if needed)
  webServer: process.env.USE_MOCK_API ? {
    command: 'python scripts/mock_api_server.py',
    port: 8787,
    reuseExistingServer: !process.env.CI,
    timeout: 120 * 1000,
  } : undefined,
});
