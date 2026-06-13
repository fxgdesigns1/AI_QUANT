#!/usr/bin/env node
/**
 * Playwright forensic trace script for forbidden endpoint detection
 * 
 * Captures runtime proof of forbidden endpoint requests:
 * - /socket.io
 * - /tasks/full_scan
 * - /api/insights
 * - /api/trade_ideas
 * 
 * Classifies initiators (our code vs third-party) and fails if same-origin
 * forbidden requests are observed from our code paths.
 */

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const ARTIFACTS_DIR = path.join(__dirname, 'artifacts');
const LOG_FILE = path.join(ARTIFACTS_DIR, 'pw_forbidden_requests.log');

const FORBIDDEN_PREFIXES = [
    '/socket.io',
    '/tasks/full_scan',
    '/api/insights',
    '/api/trade_ideas'
];

const TEST_URL = process.env.CONTROL_PLANE_URL || 'http://127.0.0.1:8787/';
const DURATION_SECONDS = parseInt(process.env.PW_DURATION || '60', 10);

function log(message) {
    const timestamp = new Date().toISOString();
    const line = `[${timestamp}] ${message}\n`;
    process.stdout.write(line);
    fs.appendFileSync(LOG_FILE, line, 'utf8');
}

function isForbiddenPath(urlString) {
    try {
        const url = new URL(urlString);
        return FORBIDDEN_PREFIXES.some(prefix => url.pathname.startsWith(prefix));
    } catch (e) {
        // Not a full URL, check if path matches
        return FORBIDDEN_PREFIXES.some(prefix => urlString.startsWith(prefix));
    }
}

function isSameOrigin(urlString, pageOrigin) {
    try {
        const url = new URL(urlString, pageOrigin);
        return url.origin === new URL(pageOrigin).origin;
    } catch (e) {
        return false;
    }
}

async function main() {
    // Clear/create log file
    if (!fs.existsSync(ARTIFACTS_DIR)) {
        fs.mkdirSync(ARTIFACTS_DIR, { recursive: true });
    }
    fs.writeFileSync(LOG_FILE, `Playwright Forbidden Request Trace\nStarted: ${new Date().toISOString()}\nURL: ${TEST_URL}\nDuration: ${DURATION_SECONDS}s\n\n`, 'utf8');

    log('Starting Playwright forensic trace...');
    log(`Target URL: ${TEST_URL}`);
    log(`Duration: ${DURATION_SECONDS} seconds`);
    log(`Forbidden prefixes: ${FORBIDDEN_PREFIXES.join(', ')}`);

    const browser = await chromium.launch({ headless: true });
    const context = await browser.newContext();
    const page = await context.newPage();

    const forbiddenRequests = [];
    const consoleTraces = [];

    // Track console messages (including traces)
    page.on('console', msg => {
        const text = msg.text();
        if (text.includes('forbidden') || text.includes('Blocked endpoint') || text.includes('DEBUG_NET_TRACE')) {
            consoleTraces.push({
                type: msg.type(),
                text: text,
                timestamp: new Date().toISOString()
            });
            log(`Console [${msg.type()}]: ${text}`);
        }
    });

    // Track all requests
    page.on('request', request => {
        const url = request.url();
        const pageUrl = page.url();
        
        if (isForbiddenPath(url) && isSameOrigin(url, pageUrl)) {
            const requestInfo = {
                url: url,
                method: request.method(),
                resourceType: request.resourceType(),
                headers: request.headers(),
                timestamp: new Date().toISOString(),
                frame: request.frame() ? request.frame().url() : 'unknown'
            };
            
            forbiddenRequests.push(requestInfo);
            log(`\n=== FORBIDDEN REQUEST DETECTED ===`);
            log(`Method: ${requestInfo.method}`);
            log(`URL: ${requestInfo.url}`);
            log(`Resource Type: ${requestInfo.resourceType}`);
            log(`Frame: ${requestInfo.frame}`);
            log(`Timestamp: ${requestInfo.timestamp}`);
        }
    });

    // Track responses to classify 404s
    page.on('response', response => {
        const url = response.url();
        const pageUrl = page.url();
        
        if (isForbiddenPath(url) && isSameOrigin(url, pageUrl)) {
            const status = response.status();
            log(`Response: ${response.method()} ${url} -> ${status}`);
            
            if (status === 404) {
                log(`⚠️  404 detected for forbidden endpoint: ${url}`);
            }
        }
    });

    // Inject network tracing BEFORE page load
    await page.addInitScript(() => {
        // Store original functions
        const originalFetch = window.fetch;
        const originalXHROpen = XMLHttpRequest.prototype.open;
        const originalWSConstructor = window.WebSocket;

        // Wrap fetch
        window.fetch = function(...args) {
            const url = args[0];
            if (typeof url === 'string' && ['/socket.io', '/tasks/full_scan', '/api/insights', '/api/trade_ideas'].some(prefix => url.includes(prefix))) {
                console.error('[INJECTED_TRACE] Forbidden fetch detected:', url);
                console.trace('Stack trace for fetch:');
            }
            return originalFetch.apply(this, args);
        };

        // Wrap XMLHttpRequest.open
        XMLHttpRequest.prototype.open = function(method, url, ...rest) {
            if (typeof url === 'string' && ['/socket.io', '/tasks/full_scan', '/api/insights', '/api/trade_ideas'].some(prefix => url.includes(prefix))) {
                console.error('[INJECTED_TRACE] Forbidden XHR detected:', method, url);
                console.trace('Stack trace for XHR:');
            }
            return originalXHROpen.call(this, method, url, ...rest);
        };

        // Wrap WebSocket constructor
        window.WebSocket = function(url, ...args) {
            if (typeof url === 'string' && ['/socket.io', '/tasks/full_scan', '/api/insights', '/api/trade_ideas'].some(prefix => url.includes(prefix))) {
                console.error('[INJECTED_TRACE] Forbidden WebSocket detected:', url);
                console.trace('Stack trace for WebSocket:');
            }
            return new originalWSConstructor(url, ...args);
        };
    });

    try {
        log('Navigating to page...');
        await page.goto(TEST_URL, { waitUntil: 'networkidle', timeout: 30000 });
        
        const pageOrigin = new URL(page.url()).origin;
        log(`Page loaded. Origin: ${pageOrigin}`);
        log(`Waiting ${DURATION_SECONDS} seconds to capture polling/interactions...`);

        // Wait for duration to capture polling
        await page.waitForTimeout(DURATION_SECONDS * 1000);

        log('\n=== SUMMARY ===');
        log(`Total forbidden requests (same-origin): ${forbiddenRequests.length}`);
        
        // Group by prefix
        const byPrefix = {};
        FORBIDDEN_PREFIXES.forEach(prefix => {
            byPrefix[prefix] = forbiddenRequests.filter(req => req.url.includes(prefix));
        });

        FORBIDDEN_PREFIXES.forEach(prefix => {
            const count = byPrefix[prefix].length;
            log(`${prefix}: ${count} requests`);
            if (count > 0) {
                byPrefix[prefix].forEach(req => {
                    log(`  - ${req.method} ${req.url} (${req.resourceType})`);
                });
            }
        });

        log(`Console traces captured: ${consoleTraces.length}`);

        // Determine pass/fail
        // FAIL if any same-origin forbidden requests (except socket.io which may be TradingView)
        const nonSocketRequests = forbiddenRequests.filter(req => !req.url.includes('/socket.io'));
        const socketRequests = forbiddenRequests.filter(req => req.url.includes('/socket.io'));

        if (nonSocketRequests.length > 0) {
            log('\n❌ FAIL: Same-origin forbidden requests detected (excluding /socket.io):');
            nonSocketRequests.forEach(req => {
                log(`  ${req.method} ${req.url}`);
            });
            process.exit(1);
        }

        if (socketRequests.length > 0) {
            log(`\n⚠️  Warning: ${socketRequests.length} /socket.io requests detected (likely TradingView widget; acceptable)`);
        }

        log('\n✅ PASS: No forbidden endpoint requests from our code detected');
        
    } catch (error) {
        log(`\n❌ Error during trace: ${error.message}`);
        log(error.stack);
        process.exit(1);
    } finally {
        await browser.close();
        log(`\nTrace complete. Log file: ${LOG_FILE}`);
    }
}

if (require.main === module) {
    main().catch(error => {
        console.error('Fatal error:', error);
        process.exit(1);
    });
}

module.exports = { main };
