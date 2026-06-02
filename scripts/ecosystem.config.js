/**
 * PM2 Ecosystem Configuration for FXG Watchdog
 * Usage: pm2 start ecosystem.config.js
 */

module.exports = {
  apps: [
    {
      name: 'fxg-watchdog',
      script: './fxg-watchdog.js',
      cwd: '/opt/ai-quant/scripts',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '500M',
      env: {
        NODE_ENV: 'production',
        MT5_SIDECAR_BASE_URL: process.env.MT5_SIDECAR_BASE_URL || 'http://192.168.1.100:8080'
      },
      error_file: '/opt/ai-quant/logs/fxg-watchdog-error.log',
      out_file: '/opt/ai-quant/logs/fxg-watchdog-out.log',
      log_file: '/opt/ai-quant/logs/fxg-watchdog.log',
      time: true,
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      merge_logs: true,

      // Restart policy
      min_uptime: '30s',
      max_restarts: 10,
      restart_delay: 5000,

      // Health monitoring
      health_check_grace_period: 3000,
      kill_timeout: 5000,

      // Cron restart (daily at 3 AM to ensure fresh state)
      cron_restart: '0 3 * * *',

      exec_mode: 'fork'
    }
  ]
};