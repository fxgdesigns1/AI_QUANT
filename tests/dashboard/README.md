# Dashboard E2E Tests

Playwright tests for dashboard functionality.

## Running Tests

```bash
# Install Playwright browsers (first time only)
npm run pw:install

# Run all tests
npm test

# Run with UI mode (interactive)
npm run test:ui

# Debug single test
npm run test:debug
```

## Test Modes

### Mock API Mode (Default)
```bash
# Start mock API
python scripts/mock_api_server.py

# Run tests
npm test
```

### Live VM Mode
```bash
# Start tunnel
./scripts/dev_tunnel_alpha.sh

# Run tests against live VM
npm run test:live
```

## Writing Tests

See `dashboard.spec.js` for examples.

All tests should:
1. Wait for API responses
2. Verify data structure
3. Test error handling
4. Be independent (can run in any order)

## Test Structure

```
tests/dashboard/
  ├── dashboard.spec.js      # Basic functionality tests
  ├── api.spec.js            # API endpoint tests
  └── ui.spec.js             # UI component tests
```
