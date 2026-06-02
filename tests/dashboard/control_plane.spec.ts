import { test, expect } from '@playwright/test';
import type { Page } from '@playwright/test';
import fs from 'fs';
import path from 'path';

const CONTROL_URL = 'http://localhost:5173/control';
const API_URL = 'http://localhost:8000';

test.describe('Alpha Control Plane', () => {
  
  test.beforeEach(async ({ page }) => {
    // Reset config before each test to a known state
    // Adjusted path for being in tests/dashboard/
    const configDir = path.resolve(__dirname, '../../dashboard/control_plane/config');
    const controlStatePath = path.join(configDir, 'control_state.json');
    const routingConfigPath = path.join(configDir, 'routing_config.json');

    const initialControlState = {
      global_trading_enabled: false,
      execution_mode: "DRY_RUN",
      last_updated: new Date().toISOString()
    };

    const initialRoutingConfig = {
      outputs: [
        {
          bridge_account: "FTMO_DEMO_1",
          enabled: true,
          lot_multiplier: 1.0,
          max_daily_loss: 500.0,
          max_trades_per_day: 5
        }
      ]
    };

    // Ensure directory exists
    if (!fs.existsSync(configDir)) {
      fs.mkdirSync(configDir, { recursive: true });
    }

    fs.writeFileSync(controlStatePath, JSON.stringify(initialControlState, null, 2));
    fs.writeFileSync(routingConfigPath, JSON.stringify(initialRoutingConfig, null, 2));

    await page.goto(CONTROL_URL);
  });

  test('should load dashboard and show correct title', async ({ page }) => {
    await expect(page.getByText('Alpha Control Plane')).toBeVisible();
    await expect(page.getByText('Local-First MT5 Bridge Controller')).toBeVisible();
  });

  test('should show API online status', async ({ page }) => {
    await expect(page.getByText('API: ok')).toBeVisible();
  });

  test('should toggle global trading', async ({ page }) => {
    const toggleBtn = page.getByRole('button', { name: 'TRADING STOPPED' });
    await expect(toggleBtn).toBeVisible();
    
    await toggleBtn.click();
    await expect(page.getByRole('button', { name: 'TRADING ON' })).toBeVisible();
    
    // Verify persistence
    await page.reload();
    await expect(page.getByRole('button', { name: 'TRADING ON' })).toBeVisible();
  });

  test('should change execution mode', async ({ page }) => {
    const liveBtn = page.getByRole('button', { name: 'LIVE' });
    await liveBtn.click();
    
    // Check if it got the active style (bg-white shadow text-indigo-600)
    await expect(liveBtn).toHaveClass(/bg-white/);
    
    // Verify persistence
    await page.reload();
    await expect(page.getByRole('button', { name: 'LIVE' })).toHaveClass(/bg-white/);
  });

  test('should add new output route', async ({ page }) => {
    await page.getByRole('button', { name: 'Add Output' }).click();
    
    // Use new placeholders matching the UI
    await page.getByPlaceholder('e.g. FTMO_DEMO_2').fill('TEST_ACC_99');
    await page.getByPlaceholder('1.0').fill('2.5');
    await page.getByPlaceholder('500').fill('1000');
    await page.getByPlaceholder('5', { exact: true }).fill('20');
    
    await page.getByRole('button', { name: 'Save Route' }).click();
    
    await expect(page.getByText('TEST_ACC_99')).toBeVisible();
    
    // Verify persistence
    await page.reload();
    await expect(page.getByText('TEST_ACC_99')).toBeVisible();
  });

  test('should update lot multiplier', async ({ page }) => {
    // Target the first input (FTMO_DEMO_1)
    // The table input for multiplier
    const input = page.locator('table input[type="number"]').first();
    await input.fill('5.5');
    
    // Trigger change (blur)
    await input.blur();
    
    // Reload and check
    await page.reload();
    const reloadedInput = page.locator('table input[type="number"]').first();
    await expect(reloadedInput).toHaveValue('5.5');
  });

  test('should toggle output status', async ({ page }) => {
    const toggleBtn = page.getByRole('button', { name: 'ACTIVE' }).first();
    await toggleBtn.click();
    
    await expect(page.getByRole('button', { name: 'DISABLED' }).first()).toBeVisible();
  });

  test.describe('Bias Observability Panel', () => {
    test('should show empty state when no bias logs exist', async ({ page }) => {
      // Mock API to return empty bias states
      await page.route(`${API_URL}/api/bias/state`, async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ bias_states: [], count: 0, timestamp: new Date().toISOString() })
        });
      });

      await page.reload();
      
      // Check for empty state message
      await expect(page.getByText('No bias state data available')).toBeVisible();
      await expect(page.getByText(/Bias states will appear here after Alpha scan cycles/)).toBeVisible();
    });

    test('should render bias panel when BIAS_STATE logs exist', async ({ page }) => {
      // Mock API to return sample bias states
      const mockBiasStates = [
        {
          instrument: "EUR_USD",
          regime: "TRENDING",
          final_bias: "BULLISH",
          blocking_sources: [],
          sources: {
            price_action: { status: "bullish", strength: 0.65, reason: "Strong uptrend" },
            regime_bias: { status: "bullish", reason: "Trending regime" },
            outlook: { status: "bullish", reason: "Positive outlook" }
          },
          timestamp: new Date().toISOString()
        },
        {
          instrument: "GBP_USD",
          regime: "RANGING",
          final_bias: "NEUTRAL",
          blocking_sources: ["low_confidence"],
          sources: {
            price_action: { status: "neutral", strength: 0.35, reason: "Sideways movement" },
            regime_bias: { status: "neutral", reason: "Ranging regime" },
            outlook: { status: "unavailable", reason: "No outlook data" }
          },
          timestamp: new Date().toISOString()
        }
      ];

      await page.route(`${API_URL}/api/bias/state`, async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ bias_states: mockBiasStates, count: 2, timestamp: new Date().toISOString() })
        });
      });

      await page.reload();
      
      // Check that bias panel title is visible
      await expect(page.getByText('Bias Observability')).toBeVisible();
      
      // Check that instruments are displayed
      await expect(page.getByText('EUR_USD')).toBeVisible();
      await expect(page.getByText('GBP_USD')).toBeVisible();
    });

    test('should render correct final_bias badge', async ({ page }) => {
      const mockBiasStates = [
        {
          instrument: "EUR_USD",
          regime: "TRENDING",
          final_bias: "BULLISH",
          blocking_sources: [],
          sources: {},
          timestamp: new Date().toISOString()
        },
        {
          instrument: "GBP_USD",
          regime: "RANGING",
          final_bias: "BEARISH",
          blocking_sources: [],
          sources: {},
          timestamp: new Date().toISOString()
        },
        {
          instrument: "USD_JPY",
          regime: "TRENDING",
          final_bias: "BLOCKED",
          blocking_sources: ["news_embargo"],
          sources: {},
          timestamp: new Date().toISOString()
        }
      ];

      await page.route(`${API_URL}/api/bias/state`, async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ bias_states: mockBiasStates, count: 3, timestamp: new Date().toISOString() })
        });
      });

      await page.reload();
      
      // Check for bias badges
      await expect(page.getByText('BULLISH')).toBeVisible();
      await expect(page.getByText('BEARISH')).toBeVisible();
      await expect(page.getByText('BLOCKED')).toBeVisible();
    });

    test('should expand and show bias source breakdown', async ({ page }) => {
      const mockBiasStates = [
        {
          instrument: "EUR_USD",
          regime: "TRENDING",
          final_bias: "BULLISH",
          blocking_sources: [],
          sources: {
            price_action: { status: "bullish", strength: 0.65, reason: "Strong uptrend detected" },
            regime_bias: { status: "bullish", reason: "Trending regime aligned" },
            outlook: { status: "bullish", reason: "Positive economic outlook" }
          },
          timestamp: new Date().toISOString()
        }
      ];

      await page.route(`${API_URL}/api/bias/state`, async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ bias_states: mockBiasStates, count: 1, timestamp: new Date().toISOString() })
        });
      });

      await page.reload();
      
      // Find the expand button for EUR_USD (should be a chevron)
      const biasCard = page.locator('text=EUR_USD').locator('..').locator('..');
      const expandButton = biasCard.locator('button').last();
      
      // Initially collapsed, sources should not be visible
      await expect(page.getByText('Bias Sources')).not.toBeVisible();
      
      // Click to expand
      await expandButton.click();
      
      // Now sources should be visible
      await expect(page.getByText('Bias Sources')).toBeVisible();
      await expect(page.getByText('price action', { exact: false })).toBeVisible();
      await expect(page.getByText('regime bias', { exact: false })).toBeVisible();
      await expect(page.getByText('outlook', { exact: true })).toBeVisible();
      
      // Check source details
      await expect(page.getByText(/Strong uptrend detected/)).toBeVisible();
    });

    test('should show blocking sources when present', async ({ page }) => {
      const mockBiasStates = [
        {
          instrument: "EUR_USD",
          regime: "TRENDING",
          final_bias: "BLOCKED",
          blocking_sources: ["news_embargo", "low_confidence"],
          sources: {
            price_action: { status: "bullish", strength: 0.45, reason: "Weak signal" },
            regime_bias: { status: "bullish", reason: "Trending" },
            outlook: { status: "unavailable", reason: "No data" }
          },
          timestamp: new Date().toISOString()
        }
      ];

      await page.route(`${API_URL}/api/bias/state`, async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ bias_states: mockBiasStates, count: 1, timestamp: new Date().toISOString() })
        });
      });

      await page.reload();
      
      // Check for blocking badge
      await expect(page.getByText(/Blocking/)).toBeVisible();
      
      // Expand to see blocking sources
      const biasCard = page.locator('text=EUR_USD').locator('..').locator('..');
      const expandButton = biasCard.locator('button').last();
      await expandButton.click();
      
      // Check for blocking sources section
      await expect(page.getByText('Blocking Sources')).toBeVisible();
      await expect(page.getByText('news_embargo')).toBeVisible();
      await expect(page.getByText('low_confidence')).toBeVisible();
    });
  });

  test.describe('Screenshot suite', () => {
    const SCREENSHOTS_DIR = path.resolve(__dirname, '../screenshots');
    const VIEWPORT = { width: 1440, height: 900 };

    test.beforeAll(() => {
      if (!fs.existsSync(SCREENSHOTS_DIR)) {
        fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });
      }
    });

    async function waitForDashboardReady(page: Page) {
      await expect(page.getByText('Alpha Control Plane')).toBeVisible();
      await expect(page.getByText('API: ok')).toBeVisible({ timeout: 10000 });
      await page.waitForTimeout(500);
    }

    test('dashboard_overview', async ({ page }) => {
      await page.setViewportSize(VIEWPORT);
      await waitForDashboardReady(page);
      await page.screenshot({
        path: path.join(SCREENSHOTS_DIR, 'dashboard_overview.png'),
        fullPage: true,
      });
    });

    test('routing_with_multiple_outputs', async ({ page }) => {
      const configDir = path.resolve(__dirname, '../../dashboard/control_plane/config');
      const routingConfigPath = path.join(configDir, 'routing_config.json');
      const routingConfig = {
        outputs: [
          { bridge_account: 'FTMO_DEMO_1', enabled: true, lot_multiplier: 1.0, max_daily_loss: 500, max_trades_per_day: 5 },
          { bridge_account: 'FTMO_DEMO_2', enabled: true, lot_multiplier: 2.0, max_daily_loss: 800, max_trades_per_day: 10 },
          { bridge_account: 'FTMO_DEMO_3', enabled: false, lot_multiplier: 0.5, max_daily_loss: 300, max_trades_per_day: 3 },
        ],
      };
      fs.writeFileSync(routingConfigPath, JSON.stringify(routingConfig, null, 2));
      await page.setViewportSize(VIEWPORT);
      await page.reload();
      await waitForDashboardReady(page);
      await expect(page.getByText('FTMO_DEMO_2')).toBeVisible();
      await expect(page.getByText('FTMO_DEMO_3')).toBeVisible();
      await page.waitForTimeout(300);
      await page.screenshot({
        path: path.join(SCREENSHOTS_DIR, 'routing_with_multiple_outputs.png'),
        fullPage: true,
      });
    });

    test('bias_observability_expanded', async ({ page }) => {
      const mockBiasStates = [
        {
          instrument: 'EUR_USD',
          regime: 'TRENDING',
          final_bias: 'BULLISH',
          blocking_sources: [],
          sources: {
            price_action: { status: 'bullish', strength: 0.72, reason: 'Strong uptrend detected' },
            regime_bias: { status: 'bullish', reason: 'Trending regime aligned' },
            outlook: { status: 'bullish', reason: 'Positive economic outlook' },
          },
          timestamp: new Date().toISOString(),
        },
        {
          instrument: 'GBP_USD',
          regime: 'RANGING',
          final_bias: 'NEUTRAL',
          blocking_sources: [],
          sources: {
            price_action: { status: 'neutral', strength: 0.4, reason: 'Sideways movement' },
            regime_bias: { status: 'neutral', reason: 'Ranging regime' },
            outlook: { status: 'unavailable', reason: 'No outlook data' },
          },
          timestamp: new Date().toISOString(),
        },
      ];
      await page.route(`${API_URL}/api/bias/state`, async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ bias_states: mockBiasStates, count: 2, timestamp: new Date().toISOString() }),
        });
      });
      await page.setViewportSize(VIEWPORT);
      await page.reload();
      await waitForDashboardReady(page);
      await expect(page.getByText('Bias Observability')).toBeVisible();
      await expect(page.getByText('EUR_USD')).toBeVisible();
      const eurCard = page.locator('text=EUR_USD').locator('..').locator('..');
      await eurCard.locator('button').last().click();
      await expect(page.getByText('Bias Sources')).toBeVisible();
      await page.waitForTimeout(300);
      await page.screenshot({
        path: path.join(SCREENSHOTS_DIR, 'bias_observability_expanded.png'),
        fullPage: true,
      });
    });

    test('dry_run_status', async ({ page }) => {
      await page.setViewportSize(VIEWPORT);
      await waitForDashboardReady(page);
      await expect(page.getByText('DRY-RUN')).toBeVisible();
      await page.waitForTimeout(300);
      await page.screenshot({
        path: path.join(SCREENSHOTS_DIR, 'dry_run_status.png'),
        fullPage: true,
      });
    });
  });
});
