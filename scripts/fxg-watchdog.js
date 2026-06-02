#!/usr/bin/env node
/**
 * FXG Watchdog Service
 * Monitors FXG system components every 60 seconds
 * Sends Telegram alerts with exact fix commands for any failures
 * Designed to run with PM2: pm2 start fxg-watchdog.js
 */

const { exec } = require('child_process');
const fs = require('fs');
const path = require('path');
const util = require('util');

const execAsync = util.promisify(exec);

// Configuration
const CONFIG = {
    checkIntervalMs: 60 * 1000, // 60 seconds
    logFile: '/opt/ai-quant/logs/fxg-watchdog.log',
    services: ['ai-quant-control-plane', 'ai-quant-runner'],
    signalFile: '/home/aiquant/gcloud-system/logs/signals_ftmo_demo2.jsonl',
    preflightUrl: 'http://127.0.0.1:8787/api/mt5/preflight',
    sidearUrl: process.env.MT5_SIDECAR_BASE_URL || 'http://192.168.1.100:8080',
    windowsPullLog: 'C:\\FXG\\logs\\pull_signals.log',
    heartbeatThreshold: 120, // seconds
    signalSizeThreshold: 1000, // bytes
    telegramScript: '/opt/ai-quant/scripts/send_telegram_alert.sh'
};

// Ensure logs directory exists
const logDir = path.dirname(CONFIG.logFile);
if (!fs.existsSync(logDir)) {
    try {
        fs.mkdirSync(logDir, { recursive: true });
    } catch (err) {
        console.error('Failed to create log directory:', err.message);
        // Fallback to local directory
        CONFIG.logFile = './logs/fxg-watchdog.log';
        fs.mkdirSync('./logs', { recursive: true });
    }
}

/**
 * Enhanced logging with console and file output
 */
function log(level, message, data = null) {
    const timestamp = new Date().toISOString();
    const logEntry = `[${timestamp}] [${level}] ${message}`;

    console.log(logEntry);

    if (data) {
        console.log(JSON.stringify(data, null, 2));
    }

    try {
        fs.appendFileSync(CONFIG.logFile, logEntry + (data ? '\n' + JSON.stringify(data) : '') + '\n');
    } catch (err) {
        console.error('Failed to write to log file:', err.message);
    }
}

/**
 * Send Telegram alert with fix command
 */
async function sendTelegramAlert(level, title, message, fixCommand = null) {
    const emoji = {
        'CRITICAL': '🚨',
        'WARNING': '⚠️',
        'INFO': 'ℹ️',
        'SUCCESS': '✅'
    }[level] || 'ℹ️';

    let fullMessage = `${emoji} **${title}**\n\n${message}`;

    if (fixCommand) {
        fullMessage += `\n\n**Fix command:**\n\`\`\`\n${fixCommand}\n\`\`\``;
    }

    try {
        // Try to use existing telegram script
        if (fs.existsSync(CONFIG.telegramScript)) {
            await execAsync(`echo "${fullMessage}" | ${CONFIG.telegramScript} "${level}"`);
        } else {
            // Fallback to Python telegram notifier
            const pythonCode = `
import sys
sys.path.append('/opt/ai-quant/src')
try:
    from control_plane.telegram_notifier import TelegramNotifier
    notifier = TelegramNotifier()
    notifier.send_message('${fullMessage.replace(/'/g, "\\'")}')
    print('Telegram alert sent')
except Exception as e:
    print(f'Failed to send telegram: {e}')
`;
            await execAsync(`python3 -c "${pythonCode}"`);
        }

        log('INFO', `Telegram alert sent: ${title}`);
    } catch (err) {
        log('WARNING', `Failed to send Telegram alert: ${err.message}`);
    }
}

/**
 * Check service status
 */
async function checkService(serviceName) {
    try {
        const { stdout, stderr } = await execAsync(`systemctl is-active ${serviceName} --quiet`);
        log('INFO', `✅ Service ${serviceName} is running`);
        return true;
    } catch (err) {
        log('ERROR', `❌ Service ${serviceName} is NOT running`);

        const fixCommand = `sudo systemctl restart ${serviceName} && sudo systemctl status ${serviceName}`;
        await sendTelegramAlert(
            'CRITICAL',
            `Service Down: ${serviceName}`,
            `Service ${serviceName} is down and needs immediate attention.`,
            fixCommand
        );

        return false;
    }
}

/**
 * Check EA heartbeat
 */
async function checkHeartbeat() {
    try {
        const { stdout } = await execAsync(`curl -s --connect-timeout 5 "${CONFIG.sidearUrl}/api/heartbeat"`);
        const data = JSON.parse(stdout);

        if (data.timestamp) {
            const currentTime = Math.floor(Date.now() / 1000);
            const heartbeatAge = currentTime - data.timestamp;

            if (heartbeatAge > CONFIG.heartbeatThreshold) {
                log('ERROR', `❌ EA heartbeat stale: ${heartbeatAge}s old`);

                const fixCommand = `gcloud compute scp --tunnel-through-iap --zone us-central1-a fxg-windows-vm-instance:/FXG/telemetry/latest.json /tmp/ea_heartbeat_sync.json --project fxg-ai-trading`;
                await sendTelegramAlert(
                    'CRITICAL',
                    'EA Heartbeat Stale',
                    `EA heartbeat is ${heartbeatAge}s old (threshold: ${CONFIG.heartbeatThreshold}s). Trading may be impacted.`,
                    fixCommand
                );

                return false;
            } else {
                log('INFO', `✅ EA heartbeat fresh: ${heartbeatAge}s old`);
                return true;
            }
        } else {
            throw new Error('No timestamp in heartbeat response');
        }
    } catch (err) {
        log('ERROR', `❌ Cannot reach sidecar heartbeat: ${err.message}`);

        await sendTelegramAlert(
            'CRITICAL',
            'Sidecar Unreachable',
            'Cannot connect to Windows sidecar for heartbeat check. EA may be down.',
            'Check Windows VM and sidecar service status'
        );

        return false;
    }
}

/**
 * Check preflight status
 */
async function checkPreflight() {
    try {
        const { stdout } = await execAsync(`curl -s --connect-timeout 5 "${CONFIG.preflightUrl}"`);
        const data = JSON.parse(stdout);

        if (data.status === 'PASS') {
            log('INFO', '✅ Preflight status: PASS');
            return true;
        } else {
            log('ERROR', `❌ Preflight status: ${data.status}`);

            const reason = data.blocking_reason || 'Unknown';
            const fixCommand = `curl -s ${CONFIG.preflightUrl} | python3 -m json.tool && sudo systemctl restart ai-quant-control-plane ai-quant-runner`;

            await sendTelegramAlert(
                'CRITICAL',
                'Preflight BLOCKED',
                `Preflight is blocked: ${reason}. Trading is halted.`,
                fixCommand
            );

            return false;
        }
    } catch (err) {
        log('ERROR', `❌ Cannot reach preflight API: ${err.message}`);

        await sendTelegramAlert(
            'CRITICAL',
            'Preflight API Unreachable',
            'Cannot connect to preflight API. Control plane may be down.',
            'sudo systemctl restart ai-quant-control-plane && sudo systemctl status ai-quant-control-plane'
        );

        return false;
    }
}

/**
 * Check signal file
 */
async function checkSignalFile() {
    try {
        if (fs.existsSync(CONFIG.signalFile)) {
            const stats = fs.statSync(CONFIG.signalFile);

            if (stats.size < CONFIG.signalSizeThreshold) {
                log('WARNING', `⚠️ Signal file small: ${stats.size} bytes`);

                await sendTelegramAlert(
                    'WARNING',
                    'Signal File Small',
                    `Signal file is only ${stats.size} bytes (threshold: ${CONFIG.signalSizeThreshold}). May indicate signal generation issues.`,
                    'Check signal generation and file permissions'
                );

                return false;
            } else {
                log('INFO', `✅ Signal file OK: ${stats.size} bytes`);
                return true;
            }
        } else {
            log('ERROR', `❌ Signal file missing: ${CONFIG.signalFile}`);

            await sendTelegramAlert(
                'CRITICAL',
                'Signal File Missing',
                `Signal file not found at ${CONFIG.signalFile}. Signal generation may be broken.`,
                'Check signal generation process and file permissions'
            );

            return false;
        }
    } catch (err) {
        log('ERROR', `❌ Cannot check signal file: ${err.message}`);
        return false;
    }
}

/**
 * Check Windows pull loop
 */
async function checkWindowsPullLoop() {
    try {
        const command = `gcloud compute ssh --tunnel-through-iap --zone us-central1-a fxg-windows-vm-instance --command="powershell -Command 'Get-Content ${CONFIG.windowsPullLog} -Tail 5'" --project fxg-ai-trading`;

        const { stdout } = await execAsync(command);

        if (stdout.toLowerCase().includes('error')) {
            log('ERROR', '❌ Windows pull loop has errors');

            const fixCommand = `gcloud compute ssh --tunnel-through-iap --zone us-central1-a fxg-windows-vm-instance --project fxg-ai-trading\n# Then run: powershell -Command 'Restart-Service FXGPullSignals; Get-Service FXGPullSignals'`;

            await sendTelegramAlert(
                'CRITICAL',
                'Windows Pull Loop Error',
                'Windows pull_signals.log contains errors. Signal pulling may be broken.',
                fixCommand
            );

            return false;
        } else {
            log('INFO', '✅ Windows pull loop OK');
            return true;
        }
    } catch (err) {
        log('WARNING', `⚠️ Cannot check Windows pull loop: ${err.message}`);

        await sendTelegramAlert(
            'WARNING',
            'Windows Pull Loop Unreachable',
            'Cannot access Windows pull_signals.log. Connection or VM may be down.',
            'Check Windows VM status and connectivity'
        );

        return false;
    }
}

/**
 * Run comprehensive health check
 */
async function runHealthCheck() {
    log('INFO', '=== Starting FXG Watchdog Health Check ===');

    const results = {
        timestamp: new Date().toISOString(),
        services: {},
        heartbeat: false,
        preflight: false,
        signalFile: false,
        windowsPullLoop: false,
        overallHealthy: true
    };

    // Check services
    for (const service of CONFIG.services) {
        const isHealthy = await checkService(service);
        results.services[service] = isHealthy;
        if (!isHealthy) results.overallHealthy = false;
    }

    // Check other components
    results.heartbeat = await checkHeartbeat();
    if (!results.heartbeat) results.overallHealthy = false;

    results.preflight = await checkPreflight();
    if (!results.preflight) results.overallHealthy = false;

    results.signalFile = await checkSignalFile();
    if (!results.signalFile) results.overallHealthy = false;

    results.windowsPullLoop = await checkWindowsPullLoop();
    if (!results.windowsPullLoop) results.overallHealthy = false;

    // Log summary
    if (results.overallHealthy) {
        log('INFO', '✅ All systems healthy');
    } else {
        log('WARNING', '⚠️ Some systems have issues');
        log('INFO', 'Health check results:', results);
    }

    log('INFO', '=== FXG Watchdog Health Check Complete ===');

    return results;
}

/**
 * Main watchdog loop
 */
async function startWatchdog() {
    log('INFO', '🐕 FXG Watchdog Service Starting...');
    log('INFO', `Check interval: ${CONFIG.checkIntervalMs / 1000}s`);
    log('INFO', `Log file: ${CONFIG.logFile}`);

    // Send startup notification
    await sendTelegramAlert(
        'INFO',
        'FXG Watchdog Started',
        `Watchdog service is now monitoring FXG system components every ${CONFIG.checkIntervalMs / 1000} seconds.`
    );

    // Main monitoring loop
    while (true) {
        try {
            await runHealthCheck();
        } catch (err) {
            log('ERROR', `Health check failed: ${err.message}`);
            await sendTelegramAlert(
                'CRITICAL',
                'Watchdog Error',
                `Watchdog health check failed: ${err.message}`,
                'Check watchdog service logs and system status'
            );
        }

        // Wait for next check
        await new Promise(resolve => setTimeout(resolve, CONFIG.checkIntervalMs));
    }
}

/**
 * Handle graceful shutdown
 */
process.on('SIGINT', async () => {
    log('INFO', '🛑 FXG Watchdog Service Stopping...');
    await sendTelegramAlert(
        'INFO',
        'FXG Watchdog Stopped',
        'Watchdog service has been stopped. System monitoring is disabled.'
    );
    process.exit(0);
});

process.on('SIGTERM', async () => {
    log('INFO', '🛑 FXG Watchdog Service Terminating...');
    await sendTelegramAlert(
        'WARNING',
        'FXG Watchdog Terminated',
        'Watchdog service was terminated. System monitoring is disabled.'
    );
    process.exit(0);
});

// Handle unhandled rejections
process.on('unhandledRejection', (reason, promise) => {
    log('ERROR', 'Unhandled Rejection:', reason);
});

process.on('uncaughtException', (error) => {
    log('ERROR', 'Uncaught Exception:', error);
    process.exit(1);
});

// Start the watchdog service
if (require.main === module) {
    startWatchdog().catch((err) => {
        log('CRITICAL', `Watchdog startup failed: ${err.message}`);
        process.exit(1);
    });
}

module.exports = {
    startWatchdog,
    runHealthCheck,
    CONFIG
};