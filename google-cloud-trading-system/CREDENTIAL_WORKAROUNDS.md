# 🔐 AI Quant Trading System - Credential Access Workarounds

## Problem
You need to access Google Cloud credentials stored in Google Drive for your AI quant trading system, but you can't access them directly from mobile devices or when Google Drive files aren't available.

## Solutions

I've created **5 different workarounds** to solve this problem:

---

## 🚀 Solution 1: Quick Setup (Recommended for Immediate Use)

**Fastest way to get started in under 2 minutes:**

```bash
cd google-cloud-trading-system
python quick_credential_setup.py
```

**What it does:**
- Interactive prompts for all credentials
- Creates all necessary files automatically
- Sets up symbolic links
- Tests your configuration
- Creates encrypted backup

**Perfect for:** When you need immediate access and can type credentials manually.

---

## 📱 Solution 2: Mobile Web Interface

**Access from any mobile device with a web browser:**

```bash
cd google-cloud-trading-system
python mobile_credential_uploader.py --start-server
```

Then open your mobile browser and go to: `http://YOUR_IP:8080`

**Features:**
- Mobile-optimized interface
- Manual credential entry
- File upload support
- QR code generation (planned)
- Works on any device with a browser

**Perfect for:** Mobile devices, tablets, or any device where you can't run Python scripts.

---

## ⚙️ Solution 3: Environment Variables

**Set up credentials using environment variables:**

```bash
cd google-cloud-trading-system
python credential_manager.py --method env --setup
```

**What it does:**
- Creates `.env.template` file
- You fill in your actual credentials
- System loads from environment variables
- Works across all platforms

**Perfect for:** Server deployments, Docker containers, or when you prefer environment-based configuration.

---

## ☁️ Solution 4: Google Drive API Integration

**Direct access to Google Drive without manual downloads:**

```bash
# First time setup
python gdrive_credential_sync.py --setup

# Download credentials
python gdrive_credential_sync.py --download

# Upload credentials
python gdrive_credential_sync.py --upload
```

**What it does:**
- Authenticates with Google Drive API
- Downloads credentials directly from your Google Drive folder
- Uploads local changes back to Google Drive
- Maintains sync between local and cloud

**Perfect for:** When you want to keep using Google Drive but need programmatic access.

---

## 🔧 Solution 5: Manual Credential Manager

**Interactive credential management with multiple options:**

```bash
cd google-cloud-trading-system
python credential_manager.py --method manual --create
```

**Features:**
- Step-by-step credential setup
- Multiple access methods
- Encrypted credential creation
- Backup and restore functionality

---

## 📋 Quick Start Guide

### For Immediate Access (Mobile/Remote):

1. **Use the Mobile Web Interface:**
   ```bash
   python mobile_credential_uploader.py --start-server
   ```
   Open `http://localhost:8080` in your mobile browser

2. **Or use Quick Setup:**
   ```bash
   python quick_credential_setup.py
   ```

### For Google Drive Integration:

1. **Set up Google Drive API:**
   ```bash
   python gdrive_credential_sync.py --setup
   ```

2. **Download your credentials:**
   ```bash
   python gdrive_credential_sync.py --download
   ```

### For Environment Variables:

1. **Create environment template:**
   ```bash
   python credential_manager.py --method env --setup
   ```

2. **Edit the `.env` file with your credentials**

---

## 🔒 Security Features

All solutions include security best practices:

- ✅ Credentials stored in separate `credentials/` directory
- ✅ Symbolic links prevent accidental commits
- ✅ Environment variable support
- ✅ Encrypted backup options
- ✅ No credentials in version control
- ✅ Secure file permissions

---

## 📁 File Structure

After setup, your credentials will be organized as:

```
google-cloud-trading-system/
├── credentials/                    # Secure credential storage
│   ├── accounts.yaml              # OANDA account configuration
│   ├── google_cloud_credentials.json  # Google Cloud service account
│   ├── .env                       # Environment variables
│   └── gdrive_token.json          # Google Drive API token
├── accounts.yaml -> credentials/accounts.yaml  # Symbolic link
├── .env -> credentials/.env        # Symbolic link
└── [credential management scripts]
```

---

## 🛠️ Troubleshooting

### "Google APIs not available"
```bash
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

### "Permission denied" errors
```bash
chmod +x *.py
```

### "File not found" errors
Make sure you're in the `google-cloud-trading-system` directory:
```bash
cd google-cloud-trading-system
```

### Mobile interface not accessible
Check your IP address and firewall settings:
```bash
python mobile_credential_uploader.py --host 0.0.0.0 --port 8080
```

---

## 🎯 Recommended Workflow

### For Mobile/Remote Access:
1. Use **Mobile Web Interface** for immediate access
2. Use **Quick Setup** for one-time configuration
3. Use **Google Drive API** for ongoing sync

### For Development:
1. Use **Environment Variables** for local development
2. Use **Google Drive API** for team collaboration
3. Use **Manual Manager** for complex configurations

---

## 📞 Support

If you encounter issues:

1. Check the troubleshooting section above
2. Verify all required packages are installed
3. Ensure you have the necessary API keys
4. Check file permissions and paths

---

## 🚀 Next Steps

After setting up credentials:

1. **Test your configuration:**
   ```bash
   python src/main.py --test
   ```

2. **Start trading:**
   ```bash
   python src/main.py
   ```

3. **View dashboard:**
   ```bash
   python scripts/dashboard.py
   ```

---

**All solutions are now ready to use! Choose the one that best fits your situation.**