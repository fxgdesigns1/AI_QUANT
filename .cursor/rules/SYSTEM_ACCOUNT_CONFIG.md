# SYSTEM ACCOUNT CONFIGURATION - CRITICAL MEMORY

## ⚠️ CRITICAL: NEVER FORGET THIS

### Total Accounts: **6 ACCOUNTS**

**Account Breakdown:**
1. **Account 001** - Regular trading account (Multi-Strategy)
2. **Account 002** - Regular trading account (Ultra Strict)  
3. **Account 003** - Regular trading account (Momentum)
4. **Account 004** - Regular trading account (Gold Scalping)
5. **Account 005** - Regular trading account (Gold Scalping)
6. **Account 006** - **SESSION TRADER** (SessionExecutionStrategy) - **SPECIAL BEHAVIOR**

### Account 006 - Session Trader (CRITICAL DETAILS)

**IMPORTANT CHARACTERISTICS:**
- **Account 006 is RESERVED exclusively for SessionExecutionStrategy**
- **No other strategy can use account 006** (enforced isolation)
- **Account 006 has DIFFERENT execution behavior** than regular accounts
- **Account 006 may not appear in standard account loading** if not in allowlist
- **SessionExecutionStrategy runs on a different schedule/pattern**

### Account Loading Configuration

**Key Environment Variables:**
- `ACCOUNT_ID_PREFIX=101-004-30719775-` (default)
- `ACCOUNT_SUFFIX_ALLOWLIST` - Must include `006` for session trader to load

**Dynamic Account Manager Logic:**
- Code automatically adds '006' to allowlist (see `src/core/dynamic_account_manager.py` lines 48-51)
- But if allowlist is explicitly set, it must include 006
- Account 006 must be explicitly allowed for session trader to work

### Why Account 006 May Not Show in Runner

**Possible Reasons:**
1. **ACCOUNT_SUFFIX_ALLOWLIST doesn't include '006'** - Explicit allowlist must include it
2. **SessionExecutionStrategy has separate loading logic** - May not use standard account manager
3. **Account 006 only loads when SessionExecutionStrategy is active** - Different initialization
4. **Account isolation enforcement** - Account 006 is isolated, may appear separate in logs

### Verification Commands

**Check if account 006 is in allowlist:**
```bash
grep ACCOUNT_SUFFIX_ALLOWLIST /etc/ai-quant/.env
```

**Check all 6 accounts via API:**
```bash
curl http://127.0.0.1:8787/api/trades/active | grep account_suffix
```

**Check SessionExecutionStrategy status:**
```bash
# Look for session execution strategy in logs
sudo journalctl -u ai-quant-runner.service | grep -i "session\|006"
```

### When Discussing Accounts

**ALWAYS REMEMBER:**
- **6 TOTAL ACCOUNTS** (not 5)
- **5 Regular Trading Accounts** (001-005)
- **1 Session Trader Account** (006) - **SPECIAL**
- Account 006 is **RESERVED** and **ISOLATED**
- Account 006 runs **SessionExecutionStrategy** which has **different behavior**

### Common Mistakes to Avoid

❌ **DON'T:** Say "5 accounts" when there are 6
❌ **DON'T:** Forget that account 006 is a session trader
❌ **DON'T:** Assume account 006 loads the same way as 001-005
❌ **DON'T:** Think account 006 uses the same strategies as others

✅ **DO:** Always say "6 accounts total (5 regular + 1 session trader)"
✅ **DO:** Remember account 006 is isolated and reserved
✅ **DO:** Check SessionExecutionStrategy separately
✅ **DO:** Verify account 006 is in ACCOUNT_SUFFIX_ALLOWLIST if explicitly set

---

**Last Updated:** 2026-01-21
**Why This Exists:** Agent kept forgetting account 006 exists and is special
**Status:** ACTIVE MEMORY - CHECK THIS BEFORE ANY ACCOUNT DISCUSSION

### How to Prevent Forgetting (For AI Agents)

**RULE:** When discussing accounts:
1. **ALWAYS say "6 accounts total"** - Never say "5 accounts"
2. **ALWAYS mention:** "5 regular trading accounts (001-005) + 1 session trader (006)"
3. **ALWAYS remember:** Account 006 uses SessionExecutionStrategy (different behavior)
4. **ALWAYS check:** If runner shows 5 accounts, account 006 may be handled separately

**MEMORY TRIGGERS:**
- When seeing "5 accounts loaded" → Remember there are actually 6, check for account 006 separately
- When discussing strategy assignments → Remember account 006 is reserved for SessionExecutionStrategy
- When checking account counts → Always verify 6 total, not 5
