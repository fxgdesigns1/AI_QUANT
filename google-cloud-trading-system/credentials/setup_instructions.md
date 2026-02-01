# AI Quant Trading System - Credential Setup Instructions
========================================================

## Your Google Drive Folder
Target: https://drive.google.com/drive/folders/1fhKX5LOUrrvyUNuX0UUr_PfBh_0QogCT

## Setup Steps

### Step 1: Copy Template Files
```bash
cd /workspace/google-cloud-trading-system
cp credentials/accounts.yaml.template credentials/accounts.yaml
cp credentials/google_cloud_credentials.json.template credentials/google_cloud_credentials.json
cp credentials/.env.template credentials/.env
```

### Step 2: Edit Your Credentials

#### Edit accounts.yaml:
- Replace 'YOUR-OANDA-ACCOUNT-ID' with your actual OANDA account ID
- Replace 'YOUR-OANDA-API-KEY' with your actual OANDA API key
- Adjust trading instruments and risk settings as needed

#### Edit google_cloud_credentials.json:
- Replace all placeholder values with your actual Google Cloud service account credentials
- Get these from: https://console.cloud.google.com/iam-admin/serviceaccounts

#### Edit .env:
- Fill in all your API keys and configuration values

### Step 3: Create Symbolic Links
```bash
python3 simple_credential_setup.py --create-links
```

### Step 4: Test Your Setup
```bash
python3 simple_credential_setup.py --test
```

## Alternative: Use Mobile Web Interface

If you prefer a web interface:

1. Start the mobile interface:
   ```bash
   python3 mobile_credential_uploader.py --host 0.0.0.0 --port 8080
   ```

2. Open your browser and go to: http://YOUR_IP:8080

3. Upload your credential files or enter them manually

## Files Created

- credentials/accounts.yaml.template - OANDA account configuration
- credentials/google_cloud_credentials.json.template - Google Cloud credentials
- credentials/.env.template - Environment variables
- credentials/setup_instructions.md - This file

## Next Steps

After setting up credentials:

1. Test your configuration:
   ```bash
   python3 src/main.py --test
   ```

2. Start trading:
   ```bash
   python3 src/main.py
   ```

3. View dashboard:
   ```bash
   python3 scripts/dashboard.py
   ```

## Support

If you need help:
1. Check the template files for examples
2. Verify all placeholder values are replaced
3. Test your configuration before trading
4. Check logs for any errors

Generated on: 2025-10-21 20:47:40
