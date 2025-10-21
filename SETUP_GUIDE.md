# Setup Guide - AI Trading System

This guide will help you set up the trading system on your local machine or collaborate with others via GitHub.

## Prerequisites

### 1. Install Xcode Command Line Tools (macOS only)

If you're on macOS, you need Xcode command line tools for Git to work:

```bash
xcode-select --install
```

A dialog will appear - click **Install** and wait for it to complete (5-10 minutes).

### 2. Install Python 3.8+

Check your Python version:
```bash
python3 --version
```

If you need to install Python, download from [python.org](https://www.python.org/downloads/)

### 3. Get OANDA API Credentials

1. Sign up for a free OANDA demo account at [oanda.com](https://www.oanda.com/)
2. Go to "Manage API Access" in your account settings
3. Generate an API token
4. Note your account ID (format: `XXX-XXX-XXXXXXXX-XXX`)

## Installation Steps

### Step 1: Clone the Repository

```bash
git clone https://github.com/YOUR-USERNAME/quant_system_clean.git
cd quant_system_clean
```

### Step 2: Install Dependencies

```bash
pip3 install -r requirements.txt
```

Or if you prefer using a virtual environment (recommended):

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Step 3: Configure Your Accounts

1. **Copy the template file:**
   ```bash
   cp google-cloud-trading-system/accounts.yaml.template google-cloud-trading-system/accounts.yaml
   ```

2. **Edit `accounts.yaml` with your credentials:**
   ```bash
   nano google-cloud-trading-system/accounts.yaml  # or use any text editor
   ```

3. **Replace placeholders:**
   - `YOUR-OANDA-ACCOUNT-ID-1` → Your OANDA account ID
   - `YOUR-OANDA-API-KEY-HERE` → Your OANDA API token
   - Adjust instruments and risk settings as needed

### Step 4: Configure Environment Variables (Optional)

If you want to use environment variables for sensitive data:

```bash
# Create .env file
cat > google-cloud-trading-system/.env << EOF
OANDA_API_KEY=your-api-key-here
OANDA_ACCOUNT_ID=your-account-id-here
TELEGRAM_BOT_TOKEN=your-telegram-token  # optional
TELEGRAM_CHAT_ID=your-chat-id          # optional
EOF
```

### Step 5: Test the Installation

```bash
cd google-cloud-trading-system
python3 src/main.py --test
```

If everything is configured correctly, you should see:
- ✓ OANDA connection successful
- ✓ Accounts loaded
- ✓ Strategies initialized

### Step 6: Run the System

```bash
python3 src/main.py
```

Then open your browser to: `http://localhost:8080`

## GitHub Collaboration Workflow

### Initial Setup (First Time)

1. **Fork the repository** on GitHub (click the "Fork" button)

2. **Clone your fork:**
   ```bash
   git clone https://github.com/YOUR-USERNAME/quant_system_clean.git
   cd quant_system_clean
   ```

3. **Add upstream remote:**
   ```bash
   git remote add upstream https://github.com/ORIGINAL-OWNER/quant_system_clean.git
   ```

### Making Changes

1. **Create a new branch:**
   ```bash
   git checkout -b feature/my-new-feature
   ```

2. **Make your changes** in your favorite editor

3. **Test your changes:**
   ```bash
   python3 -m pytest tests/  # if tests exist
   python3 src/main.py --test
   ```

4. **Commit your changes:**
   ```bash
   git add .
   git commit -m "Add: brief description of changes"
   ```

5. **Push to your fork:**
   ```bash
   git push origin feature/my-new-feature
   ```

6. **Create a Pull Request** on GitHub

### Keeping Your Fork Updated

```bash
# Fetch latest changes from upstream
git fetch upstream

# Merge them into your main branch
git checkout main
git merge upstream/main

# Push updates to your fork
git push origin main
```

## Common Git Commands

```bash
# Check status
git status

# See what changed
git diff

# View commit history
git log --oneline

# Discard local changes
git checkout -- filename

# Create and switch to new branch
git checkout -b branch-name

# Switch branches
git checkout branch-name

# List all branches
git branch -a
```

## Security Best Practices

⚠️ **NEVER commit sensitive data:**

- The `.gitignore` file is configured to exclude:
  - `accounts.yaml` (use `accounts.yaml.template` instead)
  - API keys and credentials
  - Log files
  - Backup directories

- **Before committing, always check:**
  ```bash
  git status  # What will be committed?
  git diff    # What changed in the files?
  ```

- **If you accidentally commit sensitive data:**
  ```bash
  # Remove from staging
  git reset HEAD accounts.yaml
  
  # Or amend the last commit
  git commit --amend
  ```

## Troubleshooting

### "xcode-select: command not found"
You're not on macOS, skip the Xcode step.

### "Permission denied (publickey)"
Set up SSH keys for GitHub:
```bash
ssh-keygen -t ed25519 -C "your-email@example.com"
# Follow prompts, then add to GitHub in Settings → SSH Keys
```

### "OANDA API connection failed"
- Check your API key and account ID
- Ensure you're using the practice account
- Verify your internet connection
- Check OANDA service status

### "Module not found" errors
Reinstall dependencies:
```bash
pip install -r requirements.txt --upgrade
```

### Dashboard won't load
- Check if port 8080 is already in use
- Try a different port: `python3 src/main.py --port 8081`
- Check firewall settings

## Project Structure

```
quant_system_clean/
├── google-cloud-trading-system/     # Main system
│   ├── src/
│   │   ├── main.py                  # Entry point
│   │   ├── strategies/              # Trading strategies
│   │   ├── templates/               # Web dashboard
│   │   └── ...
│   ├── accounts.yaml                # Your credentials (not in git)
│   ├── accounts.yaml.template       # Template for setup
│   └── ...
├── requirements.txt                 # Python dependencies
├── README.md                        # Project overview
├── SETUP_GUIDE.md                   # This file
└── .gitignore                       # Files to exclude from git
```

## Getting Help

1. **Check the documentation:**
   - `README.md` - Project overview
   - `HOW_TO_ADD_ACCOUNTS_AND_STRATEGIES.md` - Account management
   - `QUICK_START_GUIDE.md` - Quick reference

2. **Review the logs:**
   ```bash
   tail -f google-cloud-trading-system/logs/trading.log
   ```

3. **Ask for help:**
   - Open an issue on GitHub
   - Check existing issues for solutions
   - Include error messages and logs

## Next Steps

Once you have the system running:

1. **Familiarize yourself with the dashboard** - Explore all sections
2. **Run in paper trading mode** - Test with demo accounts first
3. **Review strategy documentation** - Understand each strategy
4. **Monitor performance** - Check daily reports
5. **Adjust risk settings** - Tune to your preferences

## Contributing

We welcome contributions! See `CONTRIBUTING.md` for guidelines.

**Happy Trading!** 🚀📈

