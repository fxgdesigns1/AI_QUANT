# Google Cloud Trading System

🚀 **Production-Ready Live OANDA Trading System for Google Cloud Platform**

A comprehensive, clean, and production-ready trading system that connects to OANDA for live paper trading with advanced risk management and real-time monitoring.

## 🌟 Features

- **Live OANDA Integration**: Real-time market data and trade execution
- **Advanced Risk Management**: 2% per trade, 10% portfolio max, 5 positions max
- **Ultra Strict Forex Strategy**: EMA crossover with momentum confirmation
- **Real-time Dashboard**: Live monitoring with WebSocket updates
- **Google Cloud Deployment**: Production-ready App Engine deployment
- **Comprehensive Logging**: Structured logging and monitoring
- **Security**: Non-root containers, environment-based configuration

## 📁 Project Structure

```
google-cloud-trading-system/
├── src/                          # Source code
│   ├── core/                     # Core trading components
│   │   ├── oanda_client.py       # OANDA API client
│   │   ├── data_feed.py          # Live data streaming
│   │   └── order_manager.py      # Order management
│   ├── strategies/               # Trading strategies
│   │   └── ultra_strict_forex.py # Ultra Strict Forex strategy
│   ├── dashboard/                # Web dashboard
│   │   └── advanced_dashboard.py # Main dashboard application
│   └── utils/                    # Utility functions
├── config/                       # Configuration files
│   └── app.yaml                  # App Engine configuration
├── scripts/                      # Deployment scripts
│   └── deploy.sh                 # Automated deployment
├── docs/                         # Documentation
├── requirements.txt              # Python dependencies
├── Dockerfile                    # Container configuration
└── README.md                     # This file
```

## 🚀 Quick Start

### Prerequisites

1. **Google Cloud Account**: [Sign up here](https://cloud.google.com/)
2. **OANDA Demo Account**: [Sign up here](https://www.oanda.com/)
3. **Google Cloud SDK**: [Install here](https://cloud.google.com/sdk/docs/install)

### 1. Setup OANDA Account

1. Create OANDA demo account
2. Get API key and Account ID
3. Note your credentials for deployment

### 2. Deploy to Google Cloud

```bash
# Clone and navigate to project
cd google-cloud-trading-system

# Set your project ID
export GOOGLE_CLOUD_PROJECT="your-project-id"

# Authenticate with Google Cloud
gcloud auth login

# Deploy the system
./scripts/deploy.sh
```

### 3. Configure OANDA Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to App Engine > Settings > Environment Variables
3. Add your OANDA credentials:
   - `OANDA_API_KEY`: Your OANDA API key
   - `OANDA_ACCOUNT_ID`: Your OANDA account ID

### 4. Start Trading

Visit your deployed URL to access the live trading dashboard!

## 📊 Trading Strategy

### Ultra Strict Forex Strategy

- **Instruments**: EUR/USD, GBP/USD, USD/JPY, AUD/USD
- **Signals**: EMA crossover (3, 8, 21 periods) + momentum confirmation
- **Risk Management**: 0.2% stop-loss, 0.3% take-profit
- **Limits**: 50 trades/day, 5 max positions, 2% per trade

### Risk Management

- **Per Trade Risk**: Maximum 2% of account balance
- **Portfolio Risk**: Maximum 10% total exposure
- **Position Limits**: Maximum 5 concurrent positions
- **Daily Limits**: Maximum 50 trades per day

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OANDA_API_KEY` | OANDA API key | Required |
| `OANDA_ACCOUNT_ID` | OANDA account ID | Required |
| `OANDA_ENVIRONMENT` | OANDA environment | `practice` |
| `MAX_RISK_PER_TRADE` | Risk per trade | `0.02` (2%) |
| `MAX_PORTFOLIO_RISK` | Portfolio risk limit | `0.10` (10%) |
| `MAX_POSITIONS` | Maximum positions | `5` |
| `DAILY_TRADE_LIMIT` | Daily trade limit | `50` |

### Risk Management Settings

Edit `config/app.yaml` to adjust risk parameters:

```yaml
env_variables:
  MAX_RISK_PER_TRADE: "0.02"      # 2% per trade
  MAX_PORTFOLIO_RISK: "0.10"      # 10% total portfolio
  MAX_POSITIONS: "5"              # Maximum positions
  DAILY_TRADE_LIMIT: "50"         # Daily trade limit
```

## 📈 Monitoring

### Dashboard Features

- **Real-time Prices**: Live OANDA market data
- **Account Information**: Balance, P&L, margin
- **Position Tracking**: Open positions and P&L
- **Risk Monitoring**: Portfolio risk and exposure
- **Trade History**: Recent trades and performance

### Logging

- **Application Logs**: View in Google Cloud Console
- **Trading Logs**: All trade executions logged
- **Error Logs**: Comprehensive error tracking
- **Performance Logs**: System performance metrics

## 🛡️ Security

### Production Security Features

- **Non-root Containers**: Secure container execution
- **Environment Variables**: Secure credential storage
- **HTTPS Only**: All traffic encrypted
- **Rate Limiting**: API rate limiting protection
- **Input Validation**: All inputs validated

### Best Practices

- Use OANDA demo accounts only
- Regularly rotate API keys
- Monitor account activity
- Set up alerts for risk breaches
- Keep system updated

## 🔄 Deployment

### Automated Deployment

```bash
# Deploy to Google Cloud
./scripts/deploy.sh
```

### Manual Deployment

```bash
# Set project
gcloud config set project YOUR_PROJECT_ID

# Deploy
gcloud app deploy config/app.yaml
```

### Docker Deployment

```bash
# Build image
docker build -t trading-system .

# Run locally
docker run -p 8080:8080 trading-system
```

## 📞 Support

### Troubleshooting

1. **Check Logs**: View in Google Cloud Console
2. **Verify Credentials**: Ensure OANDA credentials are correct
3. **Check Quotas**: Verify Google Cloud quotas
4. **Monitor Resources**: Check CPU and memory usage

### Common Issues

- **OANDA Connection Failed**: Check API credentials
- **Deployment Failed**: Verify Google Cloud setup
- **No Trades**: Check risk limits and market conditions
- **High Latency**: Check instance configuration

## 📄 License

This project is for educational and research purposes. Please ensure compliance with your local trading regulations.

## ⚠️ Disclaimer

- This system is for educational purposes only
- Always use demo accounts for testing
- Trading involves risk of loss
- Never risk more than you can afford to lose
- Follow local trading regulations

---

**🎯 Ready for Production Trading on Google Cloud!**

Your clean, production-ready trading system is now deployed and ready for live OANDA paper trading.
