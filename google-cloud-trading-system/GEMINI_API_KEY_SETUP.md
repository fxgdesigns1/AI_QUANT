# 🔑 Gemini API Key Setup Guide

## 📋 CURRENT STATUS

**Status:** ❌ **NOT CONFIGURED**  
**Found:** Placeholder value `your_gemini_api_key` in `news_api_config.env`  
**Action Required:** Get a real Gemini API key and configure it

---

## 🎯 STEP 1: Get Your Gemini API Key

### Option A: Google AI Studio (Recommended - Free)
1. Go to: **https://makersuite.google.com/app/apikey**
2. Sign in with your Google account
3. Click **"Create API Key"**
4. Copy the generated API key (starts with `AIza...`)

### Option B: Google Cloud Console
1. Go to: **https://console.cloud.google.com/apis/credentials**
2. Select your project: `ai-quant-trading`
3. Click **"Create Credentials"** → **"API Key"**
4. Enable **Generative Language API** if prompted
5. Copy the API key

---

## 🔧 STEP 2: Configure the Key

You have **3 options** to configure the Gemini API key:

### **Option 1: Google Cloud Secret Manager (Recommended for Production)**

This is the most secure method for production:

```bash
# Set your API key
export GEMINI_API_KEY="AIzaSyC-your-actual-key-here"

# Upload to Secret Manager
echo -n "$GEMINI_API_KEY" | gcloud secrets create gemini-api-key \
  --data-file=- \
  --project=ai-quant-trading \
  --replication-policy="automatic"

# Or if secret already exists, update it:
echo -n "$GEMINI_API_KEY" | gcloud secrets versions add gemini-api-key \
  --data-file=- \
  --project=ai-quant-trading
```

**Verify:**
```bash
gcloud secrets versions access latest --secret="gemini-api-key" --project=ai-quant-trading
```

---

### **Option 2: app.yaml Environment Variable (Quick Setup)**

Edit `google-cloud-trading-system/app.yaml`:

```yaml
env_variables:
  # AI Assistant Configuration - F1 OPTIMIZED
  AI_ASSISTANT_ENABLED: "true"
  AI_MODEL_PROVIDER: "gemini"  # Change from "demo" to "gemini"
  GEMINI_API_KEY: "AIzaSyC-your-actual-key-here"  # Add this line
  AI_RATE_LIMIT_PER_MINUTE: "5"
  AI_REQUIRE_LIVE_CONFIRMATION: "true"
```

**Then deploy:**
```bash
cd google-cloud-trading-system
gcloud app deploy app.yaml
```

---

### **Option 3: Local .env File (For Local Development)**

Edit `google-cloud-trading-system/news_api_config.env`:

```bash
# Gemini AI Configuration
GEMINI_API_KEY=AIzaSyC-your-actual-key-here
GEMINI_MODEL=gemini-pro
GEMINI_MAX_TOKENS=1000
GEMINI_TEMPERATURE=0.7
```

---

## ✅ STEP 3: Verify Configuration

### Test Locally:
```bash
cd google-cloud-trading-system
python3 -c "
import os
os.environ['GEMINI_API_KEY'] = 'your-key-here'
import google.generativeai as genai
genai.configure(api_key=os.environ['GEMINI_API_KEY'])
model = genai.GenerativeModel('gemini-pro')
response = model.generate_content('Hello')
print('✅ Gemini API working!')
print(response.text)
"
```

### Check Cloud Configuration:
After deploying, check logs:
```bash
gcloud app logs tail -s default | grep -i "gemini\|ai assistant"
```

Look for:
- ✅ "Gemini API initialized successfully"
- ✅ "AI Assistant initialized - Provider: gemini"

---

## 🔍 STEP 4: Update Code to Use Key

The code already checks for the key in these locations (in order):
1. ✅ `GEMINI_API_KEY` environment variable
2. ✅ Google Cloud Secret Manager (`gemini-api-key` secret)
3. ✅ Fallback to demo mode if not found

**Files that use Gemini:**
- `src/dashboard/ai_assistant_api.py` - Main AI assistant
- `src/dashboard/enhanced_ai_assistant.py` - Enhanced assistant with Gemini

---

## 🚀 QUICK START (Recommended)

**For Production (Google Cloud):**

1. Get your key from: https://makersuite.google.com/app/apikey
2. Upload to Secret Manager:
   ```bash
   echo -n "YOUR_KEY_HERE" | gcloud secrets create gemini-api-key \
     --data-file=- \
     --project=ai-quant-trading
   ```
3. Update `app.yaml`:
   ```yaml
   AI_MODEL_PROVIDER: "gemini"  # Change from "demo"
   ```
4. Deploy:
   ```bash
   gcloud app deploy app.yaml
   ```

**For Local Development:**
1. Get your key
2. Add to `news_api_config.env`:
   ```
   GEMINI_API_KEY=your-key-here
   ```
3. Restart your local server

---

## 📊 AFTER CONFIGURATION

Once configured, your AI Assistant will:
- ✅ Use Gemini AI for intelligent responses
- ✅ Provide better market analysis
- ✅ Generate sophisticated trading insights
- ✅ Answer complex questions about your trading system

**Current Status:** Demo mode (rule-based responses)  
**After Setup:** Full AI-powered assistance

---

## 🔒 SECURITY NOTES

- ⚠️ **Never commit API keys to git**
- ✅ Use Secret Manager for production
- ✅ Use .env files for local development (add to .gitignore)
- ✅ Rotate keys periodically

---

## ❓ TROUBLESHOOTING

### "Gemini API key not found"
- Check Secret Manager: `gcloud secrets list --project=ai-quant-trading`
- Check app.yaml has `GEMINI_API_KEY` set
- Check environment variables are loaded

### "API key invalid"
- Verify key starts with `AIza...`
- Check key hasn't expired
- Ensure Generative Language API is enabled

### "Rate limit exceeded"
- Free tier: 15 requests/minute
- Upgrade to paid tier for higher limits
- Check `AI_RATE_LIMIT_PER_MINUTE` setting

---

## 📞 SUPPORT

- Gemini API Docs: https://ai.google.dev/docs
- Google AI Studio: https://makersuite.google.com
- Secret Manager Docs: https://cloud.google.com/secret-manager/docs

---

**🎯 Next Step:** Get your API key and follow Option 2 (app.yaml) for quickest setup!



