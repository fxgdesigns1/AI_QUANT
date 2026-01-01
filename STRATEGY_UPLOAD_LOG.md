# Strategy Upload Log - Google Cloud Trading System

**Last Updated:** November 16, 2025 18:03 (London Time)

---

## 🆕 NEW STRATEGIES (Uploaded Today - Nov 16, 2025)

| Strategy Key | Display Name | Upload Date | Status | Account Number | Lane/Account |
|-------------|--------------|-------------|--------|----------------|--------------|
| ~~`optimized_multi_pair_live`~~ | ~~Optimized Multi-Pair Live~~ | **Nov 16, 2025 18:03** | ❌ **REMOVED** | N/A | **Marked for removal when loading new strategies** |
| `gold_scalping_winrate` | Gold Scalper (Winrate) | **Nov 16, 2025 16:08** | ✅ Active | **⚠️ NEEDS ASSIGNMENT** | `lane_gold_winrate_demo` (DEMO) |
| `gold_scalping_strict1` | Gold Scalper (Strict1) | **Nov 16, 2025 16:08** | ✅ Active | **⚠️ NEEDS ASSIGNMENT** | `lane_gold_strict1_demo` (DEMO) |
| `gold_scalping_topdown` | Gold Scalper (Topdown) | **Nov 16, 2025 16:08** | ✅ Active | **⚠️ NEEDS ASSIGNMENT** | `lane_gold_topdown_demo` (DEMO) |
| `trade_with_pat_orb_dual` | Trade With Pat ORB (Dual Session) | **Nov 16, 2025 15:12** | ✅ Registered | `101-004-30719775-010` | Not yet in live config |

**Note:** The three Gold Scalper profiles are ready for deployment. `optimized_multi_pair_live` has been **REMOVED** from deployment and marked for removal. Run `deploy_strategy.sh` to activate the Gold Scalper strategies on GCloud.

---

## 📅 RECENTLY UPLOADED (Nov 14, 2025)

| Strategy Key | Display Name | Upload Date | Status | Account Number | Lane/Account |
|-------------|--------------|-------------|--------|----------------|--------------|
| `dynamic_multi_pair_unified` | Dynamic Multi-Pair Unified | **Nov 14, 2025 14:25** | ✅ Active | `101-004-30719775-011` | `unified_multi_pair_account` |
| `ultra_strict_forex` | Ultra Strict Forex | **Nov 14, 2025 14:25** | ✅ Registered | `101-004-30719775-003` (inactive) | Not in live config |
| `momentum_trading` | Momentum Trading | **Nov 14, 2025 14:25** | ✅ Active | `101-004-30719775-008` | Primary Trading Account |
| `gold_scalping` | Gold Scalping (Base) | **Nov 14, 2025 14:25** | ✅ Active | `101-004-30719775-007` | Gold Scalping Account |
| `pattern_discovery_v11` | Pattern Discovery V11 | **Nov 14, 2025 14:25** | ✅ Registered | Not assigned | Not in live config |

---

## 📋 OLDER STRATEGIES (Nov 12, 2025)

| Strategy Key | Display Name | Upload Date | Status | Account Number | Lane/Account |
|-------------|--------------|-------------|--------|----------------|--------------|
| `all_weather_70wr` | All-Weather 70% WR | **Nov 12, 2025 03:09** | ✅ Active | `101-004-30719775-005` | All Weather 70WR Account |
| `gbp_rank_1` | GBP/USD Rank #1 | **Nov 12, 2025 03:09** | ✅ Active | `101-004-30719775-006` | Strategy Alpha Account |
| `gbp_rank_2` | GBP/USD Rank #2 | **Nov 12, 2025 03:09** | ✅ Active | `101-004-30719775-009` | GBP Rank #2 |
| `gbp_rank_3` | GBP/USD Rank #3 | **Nov 12, 2025 03:09** | ⚠️ Note | `101-004-30719775-010` | Currently mapped to `trade_with_pat_orb_dual` in accounts.yaml |

---

## 🔄 BACKTESTING LANE

| Strategy Key | Display Name | Upload Date | Status | Account Number | Lane/Account |
|-------------|--------------|-------------|--------|----------------|--------------|
| `lane_backtest_parity` | Backtesting Parity Lane | **Nov 16, 2025 16:08** | ⏸️ Inactive | Not assigned | `lane_backtest_parity` (Backtesting only) |

**Purpose:** Dedicated lane for backtesting to ensure config/logic parity with live trading.

---

## 📊 SUMMARY

### Total Strategies Registered: **13** (1 removed)
- **New (Today):** 4 strategies (1 removed: `optimized_multi_pair_live`)
- **Recent (Nov 14):** 5 strategies  
- **Older (Nov 12):** 4 strategies

### Active in Live Config: **5 lanes**
1. `dynamic_multi_pair_unified` → Account `101-004-30719775-011`
2. `gold_scalping_winrate` → **⚠️ NEEDS ACCOUNT ASSIGNMENT**
3. `gold_scalping_strict1` → **⚠️ NEEDS ACCOUNT ASSIGNMENT**
4. `gold_scalping_topdown` → **⚠️ NEEDS ACCOUNT ASSIGNMENT**
5. `lane_backtest_parity` → Inactive (backtesting only)

### Active in Accounts (from blotter): **7 accounts**
- Account `101-004-30719775-007`: `gold_scalping` (base) - Gold Scalping Account
- Account `101-004-30719775-011`: `dynamic_multi_pair_unified` - Dynamic Multi-Pair Unified Account
- Account `101-004-30719775-005`: `all_weather_70wr` - All Weather 70WR Account
- Account `101-004-30719775-006`: `gbp_rank_1` - Strategy Alpha Account
- Account `101-004-30719775-009`: `gbp_rank_2` - GBP Rank #2
- Account `101-004-30719775-010`: `gbp_rank_3` (Note: Also mapped to `trade_with_pat_orb_dual` in accounts.yaml)
- Account `101-004-30719775-008`: `momentum_trading` - Primary Trading Account

### Available Accounts (Not Currently Active):
- Account `101-004-30719775-004`: Reserve Account (inactive)
- Account `101-004-30719775-003`: Legacy Ultra Strict (inactive)
- Account `101-004-30719775-001`: Strategy Zeta Account (inactive)

---

## 🎯 MONITORING PLAN (Next Week)

### New Strategies to Monitor (Uploaded Nov 16):
1. ✅ **Gold Scalper (Winrate)** - `lane_gold_winrate_demo` - **⚠️ NEEDS ACCOUNT ASSIGNMENT**
2. ✅ **Gold Scalper (Strict1)** - `lane_gold_strict1_demo` - **⚠️ NEEDS ACCOUNT ASSIGNMENT**
3. ✅ **Gold Scalper (Topdown)** - `lane_gold_topdown_demo` - **⚠️ NEEDS ACCOUNT ASSIGNMENT**

**Removed from Deployment:**
- ❌ **Optimized Multi-Pair Live** - Marked for removal when loading new strategies (removed from deployment script and registry)

**Action Required:** 
1. Assign demo account numbers to the 3 Gold Scalper lanes in `accounts.yaml`
2. Deploy to GCloud using `deploy_strategy.sh` to activate them

---

## 📝 NOTES

- All new Gold Scalper profiles use **demo accounts only** (per system policy)
- File modification dates are in London time (GMT/BST)
- Strategies marked "Registered" are in the registry but not yet active in live config
- The backtesting lane is intentionally inactive for production services
- **⚠️ IMPORTANT:** The three new Gold Scalper lanes need account numbers assigned in `accounts.yaml` before deployment
- Account `101-004-30719775-010` appears to be mapped to both `gbp_rank_3` (in blotter) and `trade_with_pat_orb_dual` (in accounts.yaml) - verify which strategy is actually running

---

**Generated:** November 16, 2025 16:08 London Time

