# API Configuration Guide

## Overview

Your trading system now has a centralized API configuration management system. All API keys, credentials, and service configurations can be managed from a single dashboard without editing code or environment files manually.

---

## Accessing API Configuration

### From Dashboard

1. Navigate to **Configuration** in the System & Configuration section
2. Click on **API Configuration** panel
3. All APIs are organized by category:
   - **OANDA Trading API** - Trading platform credentials
   - **News & Data APIs** - Market data sources
   - **Telegram** - Notifications bot
   - **Gemini AI** - AI assistant credentials

### Via API

Base URL: `http://localhost:8080/api/config` (or your cloud URL)

---

## Available Services

### 1. OANDA Trading API

**Configuration:**
- API Key: Your OANDA demo/production key
- Environment: `practice` or `live`
- Base URL: Automatically set based on environment

**Testing:**
- Click **Test** button to verify connection
- Will return account ID, balance, and currency if successful

**Limits:**
- 10,000 calls/day (demo account)
- 2,400 calls/hour

---

### 2. News & Data APIs

#### Alpha Vantage
- **Purpose:** Financial market data
- **Limits:** 500 calls/day, 5 calls/minute
- **Best For:** Stock quotes, forex data, indicators

#### Marketaux
- **Purpose:** Financial news aggregation
- **Limits:** 1,000 calls/day, 60 calls/minute
- **Best For:** Real-time news, market sentiment

#### NewsData.io
- **Purpose:** News data specialist
- **Limits:** 200 calls/day, 10 calls/minute
- **Best For:** Breaking news, economic events

---

### 3. Telegram Notifications

**Configuration:**
- Bot Token: From @BotFather on Telegram
- Chat ID: Your personal/group chat ID

**Testing:**
- Validates bot token
- Returns bot name and username
- Confirms chat ID configured

---

### 4. Gemini AI

**Configuration:**
- API Key: From Google AI Studio
- Model: gemini-pro (default)

**Testing:**
- Validates API key
- Tests model access
- Returns success/failure

---

## Common Operations

### Viewing API Keys

All keys are automatically masked for security:
- Shows last 4 characters
- Example: `********************d2a4`

### Updating an API Key

1. Click **Edit** button next to API key field
2. Enter new key in prompt
3. System validates format
4. Click **Test** to verify
5. Changes save automatically

### Testing API Connections

**Single Service:**
```
POST /api/config/test/oanda
POST /api/config/test/alpha_vantage
POST /api/config/test/marketaux
POST /api/config/test/telegram
POST /api/config/test/gemini
```

**Multiple Services:**
```
POST /api/config/test-multiple
Body: {"services": ["oanda", "marketaux", "telegram"]}
```

### Viewing Usage Statistics

**Endpoint:**
```
GET /api/config/usage
```

**Response:**
```json
{
  "oanda": {
    "calls_today": 0,
    "daily_limit": 10000,
    "remaining": 10000,
    "percentage_used": 0.0,
    "status": "green"
  },
  "alpha_vantage": {
    "calls_today": 0,
    "daily_limit": 500,
    "remaining": 500,
    "percentage_used": 0.0,
    "status": "green"
  }
}
```

**Status Colors:**
- 🟢 Green: < 70% used (safe)
- 🟡 Yellow: 70-90% used (caution)
- 🔴 Red: > 90% used (limit approaching)

---

## Backup & Recovery

### Automatic Backups

Before any credential update:
- Previous value is logged
- Timestamp recorded
- Can rollback if needed

### Manual Backup

**Option 1: Dashboard**
- All credentials can be viewed (masked)
- Screenshot for records

**Option 2: Export**
```bash
curl http://localhost:8080/api/config/credentials > api_backup.json
```

### Recovery

If credentials are lost:
1. Check Google Secret Manager (cloud)
2. Check .env files (local)
3. Check app.yaml (cloud config)
4. Contact support with timestamp

---

## Security Best Practices

### DO ✅

- ✅ Test new keys immediately after setting
- ✅ Use strong, unique keys per service
- ✅ Monitor usage statistics regularly
- ✅ Rotate keys periodically
- ✅ Keep backups in secure location

### DON'T ❌

- ❌ Share API keys in chat/email
- ❌ Commit keys to version control
- ❌ Use production keys in development
- ❌ Disable validation checks
- ❌ Ignore usage warnings

---

## Troubleshooting

### Issue: "Credential update failed"

**Solutions:**
1. Check you have write permissions
2. Verify format matches service requirements
3. Try with `force_overwrite: true`
4. Check logs for specific error

### Issue: "Test connection failed"

**Solutions:**
1. Verify API key is correct
2. Check rate limits haven't been hit
3. Confirm network connectivity
4. Verify account is active
5. Check service status page

### Issue: "Secret not found"

**Solutions:**
1. Check Google Cloud project permissions
2. Verify Secret Manager is enabled
3. Fall back to .env files
4. Check environment variables

---

## Advanced Configuration

### Environment-Specific Settings

**Local Development:**
- Uses `.env` files
- Credentials in `oanda_config.env`, `news_api_config.env`
- Easy to update and test

**Google Cloud Production:**
- Uses Secret Manager
- Credentials in `app.yaml` env_variables
- Auto-synced with deployments

### Custom Validation

Add custom validation by editing `config_api_manager.py`:

```python
def validate_api_key(key: str, value: str) -> Dict[str, Any]:
    # Add your custom validation logic
    pass
```

---

## API Reference

### Complete Endpoint List

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/config/credentials` | List all credentials (masked) |
| GET | `/api/config/credentials/{key}` | Get specific credential |
| PUT | `/api/config/credentials/{key}` | Update credential |
| POST | `/api/config/test/{service}` | Test API connection |
| POST | `/api/config/test-multiple` | Test multiple services |
| POST | `/api/config/validate` | Validate credential format |
| GET | `/api/config/usage` | Get usage statistics |

### Request/Response Examples

**Update Credential:**
```bash
PUT /api/config/credentials/OANDA_API_KEY
Content-Type: application/json

{
  "value": "your_new_key",
  "validate": true,
  "force_overwrite": false
}
```

**Response:**
```json
{
  "success": true,
  "message": "Credential OANDA_API_KEY updated successfully",
  "timestamp": "2024-12-XX..."
}
```

---

## Migration Notes

### From Hardcoded to Centralized

If you have existing hardcoded credentials:

1. **Export current credentials:**
   ```bash
   grep -r "API_KEY" .env files > current_creds.txt
   ```

2. **Import to new system:**
   - Use dashboard Edit button
   - Or use PUT API endpoints

3. **Verify:**
   ```bash
   curl http://localhost:8080/api/config/credentials | jq
   ```

4. **Test all connections:**
   ```bash
   curl -X POST http://localhost:8080/api/config/test-multiple \
     -H "Content-Type: application/json" \
     -d '{"services": ["oanda", "alpha_vantage", "marketaux", "telegram"]}'
   ```

---

## Support

**Need Help?**
1. Check logs: `tail -f logs/*.log`
2. Review error messages in dashboard
3. Test individual components
4. Check API documentation
5. Contact development team

**Common Questions:**

**Q: Why are my credentials masked?**  
A: Security feature to prevent accidental exposure in screenshots/logs.

**Q: Can I see full keys?**  
A: Only via test endpoint responses or export. Masking is permanent in UI.

**Q: How often should I rotate keys?**  
A: Production keys: Every 90 days. Demo keys: As needed.

**Q: What happens if I hit rate limits?**  
A: System shows warning. Some services have fallback or retry logic.

**Q: Can I add custom API services?**  
A: Yes. Edit `config_api_manager.py` to add new service handlers.

---

**Last Updated:** December 2024  
**Version:** 1.0  
**Status:** Production Ready

