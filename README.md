# AI-Powered Quantitative Trading System

A sophisticated automated trading system for forex and commodities (gold) with AI-driven signal generation, multi-strategy execution, and comprehensive monitoring dashboards.

## 🌟 Features

- **Multi-Strategy Trading**: Adaptive Momentum, Champion, Gold DNA, and more
- **Real-time Dashboard**: Advanced web-based monitoring with live data
- **AI-Driven Signals**: Machine learning-powered trade signal generation
- **Risk Management**: Sophisticated position sizing and exposure controls
- **News Integration**: Real-time market news and sentiment analysis
- **Telegram Alerts**: Instant notifications for trades and market events
- **Paper Trading**: Safe testing environment before live deployment
- **Cloud Deployment**: Google Cloud Platform integration

## 🏗️ Architecture

```
quant_system_clean/
├── google-cloud-trading-system/    # Main trading system
│   ├── src/
│   │   ├── strategies/             # Trading strategies
│   │   ├── templates/              # Dashboard UI
│   │   ├── main.py                 # Core trading engine
│   │   └── ...
│   ├── config/
│   │   ├── accounts.yaml           # Account configurations
│   │   └── strategies.yaml         # Strategy parameters
│   └── ...
├── dashboard/                      # Alternative dashboard
├── requirements.txt                # Python dependencies
└── README.md                       # This file
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- OANDA API account (demo or live)
- Google Cloud account (optional, for deployment)
- Telegram bot (optional, for alerts)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/fxgdesigns1/AI_QUANT.git
   cd AI_QUANT
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure accounts** (Create your own config file)
   ```bash
   cp google-cloud-trading-system/config/accounts.yaml.template google-cloud-trading-system/config/accounts.yaml
   # Edit accounts.yaml with your OANDA credentials
   ```

4. **Configure strategies**
   ```bash
   cp google-cloud-trading-system/config/strategies.yaml.template google-cloud-trading-system/config/strategies.yaml
   # Adjust strategy parameters as needed
   ```

5. **Run the system**
   ```bash
   cd google-cloud-trading-system
   python src/main.py
   ```

6. **Access the dashboard**
   Open your browser to `http://localhost:8080` (or your deployed URL)

## 📊 Available Strategies

- **Adaptive Momentum**: EMA-based momentum trading with dynamic position sizing
- **Champion Strategy**: High win-rate strategy optimized for stable returns
- **Gold DNA**: Specialized strategy for gold trading
- **Hybrid Manual**: Semi-automated trading with manual oversight

## ⚙️ Configuration

### Account Setup

Edit `google-cloud-trading-system/config/accounts.yaml`:
```yaml
accounts:
  - name: "demo_account_1"
    oanda_account_id: "YOUR_ACCOUNT_ID"
    oanda_api_key: "YOUR_API_KEY"
    environment: "practice"
    initial_balance: 10000
```

### Strategy Configuration

Edit `google-cloud-trading-system/config/strategies.yaml`:
```yaml
strategies:
  - name: "adaptive_momentum_1"
    type: "adaptive_momentum"
    account: "demo_account_1"
    instruments: ["EUR_USD", "GBP_USD", "XAU_USD"]
    risk_per_trade: 0.02
    max_positions: 5
```

## 🔒 Security Notes

**NEVER commit sensitive data to GitHub:**
- API keys and credentials are excluded via `.gitignore`
- Always use environment variables or separate config files
- Use demo accounts for testing and development
- Review all commits before pushing

## 📈 Trading Hours

System is optimized for London time (GMT/BST):
- **Prime Trading**: 1pm-5pm (London/NY overlap)
- **London Session**: 8am-5pm
- **Avoid**: 10pm-8am (Asian session)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📱 Telegram Integration

Daily updates configured:
- Morning briefing at 6:00 AM London time
- End-of-day summary at 9:30 PM London time
- Real-time trade alerts

## ☁️ Cloud Deployment

The system can be deployed to Google Cloud Platform:
1. Set up GCP credentials
2. Configure Cloud Run or Compute Engine
3. Deploy using provided scripts
4. Access dashboard via public URL

## 📝 Documentation

- `HOW_TO_ADD_ACCOUNTS_AND_STRATEGIES.md` - Adding new accounts/strategies
- `HYBRID_MANUAL_TRADING_GUIDE.md` - Manual trading guide
- `QUICK_START_GUIDE.md` - Quick reference
- `DEPLOYMENT_WORKFLOW.md` - Deployment instructions

## ⚠️ Disclaimer

This trading system is for educational and research purposes. Trading involves substantial risk of loss. Always:
- Start with paper trading
- Never risk more than you can afford to lose
- Thoroughly backtest strategies before live trading
- Monitor your positions regularly

## 📊 Performance

Each strategy maintains isolated statistics for proper evaluation:
- Individual account performance tracking
- No aggregated metrics (by design)
- Transparent win rates and P&L
- Real-time position monitoring

## 🛠️ Technology Stack

- **Backend**: Python 3.8+, Flask
- **Trading API**: OANDA v20 API
- **Cloud**: Google Cloud Platform
- **Monitoring**: Custom dashboard with Chart.js
- **Alerts**: Telegram Bot API
- **Data**: Real-time price feeds and news APIs

## 📞 Support

For issues and questions:
1. Check existing documentation
2. Review logs in `logs/` directory
3. Open an issue on GitHub
4. Ensure you're using demo accounts for testing

## 📄 License

[Specify your license here]

---

**Built with precision for quantitative trading. Trade smart, trade safe.**

