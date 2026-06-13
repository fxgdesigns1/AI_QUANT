# DASHBOARD API WIRING - COMPLETE SPECIFICATION

**Last Updated:** 2026-01-20  
**Purpose:** Complete mapping of all dashboard elements to API endpoints, response fields, and JavaScript implementation code.

---

## TABLE OF CONTENTS

1. [System Status Wiring](#1-system-status-wiring)
2. [Session & Regime Readiness Wiring (NEW)](#2-session--regime-readiness-wiring-new)
3. [Market Data Wiring](#3-market-data-wiring)
4. [News & AI Insights Wiring](#4-news--ai-insights-wiring)
5. [Performance & Journal Wiring](#5-performance--journal-wiring)
6. [Active Trades Wiring](#6-active-trades-wiring)
7. [Strategy Management Wiring](#7-strategy-management-wiring)
8. [Complete JavaScript Implementation](#8-complete-javascript-implementation)

---

## 1. SYSTEM STATUS WIRING

### API Endpoint
```
GET /api/status
```

### Response Structure
```json
{
  "data": {
    "mode": "paper" | "live",
    "execution_enabled": boolean,
    "accounts_loaded": number,
    "accounts_execution_capable": number,
    "active_strategy_key": string,
    "active_strategy_assignments_count": number,
    "assigned_accounts_count": number,
    "last_scan_at": "ISO8601",
    "last_status_write_at": "ISO8601",
    "last_signals_generated": number,
    "last_executed_count": number,
    "weekend_indicator": boolean,
    "config_mtime": number,
    "execution_guard": {
      "allowed": boolean,
      "reason_code": string,
      "mode": "paper" | "live"
    },
    "system_label": "ALPHA" | "BETA" | "UNKNOWN",
    "accounts_with_strategy": number,
    "accounts_execution_enabled": number,
    "daily_limit_current": { "account_id": limit },
    "daily_trades_today": { "account_id": count },
    "price_sanity_blocks_per_account": { "account_id": count },
    "tp_omitted_per_account": { "account_id": count },
    "throttle_skips_per_account": { "account_id": count },
    "oanda_cancel_reasons_per_account": { "account_id": { "reason": count } },
    "execution_suspended_accounts": { "account_id": { "reason": string, "since": ISO8601 } }
  },
  "truth": {
    "source": "status_snapshot",
    "freshness_ms": number,
    "last_verified_at": "ISO8601"
  }
}
```

### Dashboard Element Mappings

| Dashboard Element | API Field Path | Display Format |
|-------------------|----------------|-----------------|
| Execution Status Badge | `data.execution_enabled` | Green if `true`, Red if `false` |
| Mode Indicator | `data.mode` | "PAPER" or "LIVE" badge |
| Accounts Loaded | `data.accounts_loaded` | Number display |
| Accounts Execution Capable | `data.accounts_execution_capable` | Number display |
| Active Strategy | `data.active_strategy_key` | Strategy name badge |
| Last Scan Time | `data.last_scan_at` | Relative time (e.g., "2m ago") |
| Signals Generated | `data.last_signals_generated` | Number display |
| Trades Executed | `data.last_executed_count` | Number display |
| System Label | `data.system_label` | "ALPHA" / "BETA" badge |
| Execution Guard Status | `data.execution_guard.allowed` | Status indicator |
| Execution Guard Reason | `data.execution_guard.reason_code` | Tooltip/explanation |

### JavaScript Implementation
```javascript
async function pollStatus() {
    try {
        const response = await fetch('/api/status');
        const envelope = await response.json();
        const data = envelope.data;
        
        // Update execution status
        const execBadge = document.getElementById('execution-status');
        if (execBadge) {
            execBadge.textContent = data.execution_enabled ? 'ENABLED' : 'DISABLED';
            execBadge.className = data.execution_enabled ? 'chip chip-success' : 'chip chip-danger';
        }
        
        // Update mode
        setText('mode-indicator', data.mode.toUpperCase());
        
        // Update accounts
        setText('accounts-loaded', String(data.accounts_loaded));
        setText('accounts-execution-capable', String(data.accounts_execution_capable));
        
        // Update strategy
        setText('active-strategy', data.active_strategy_key || 'NONE');
        
        // Update last scan (relative time)
        if (data.last_scan_at) {
            const scanTime = new Date(data.last_scan_at);
            const now = new Date();
            const diffMs = now - scanTime;
            const diffMins = Math.floor(diffMs / 60000);
            setText('last-scan', diffMins < 1 ? 'Just now' : `${diffMins}m ago`);
        }
        
        // Update signals/trades
        setText('signals-generated', String(data.last_signals_generated));
        setText('trades-executed', String(data.last_executed_count));
        
        // Update system label
        setText('system-label', data.system_label);
        
        // Update execution guard
        const guardEl = document.getElementById('execution-guard');
        if (guardEl) {
            guardEl.textContent = data.execution_guard.allowed ? 'ALLOWED' : 'BLOCKED';
            guardEl.className = data.execution_guard.allowed ? 'chip chip-success' : 'chip chip-danger';
            guardEl.title = `Reason: ${data.execution_guard.reason_code}`;
        }
        
        return data;
    } catch (e) {
        console.error('Poll status error:', e);
        return null;
    }
}
```

---

## 2. SESSION & REGIME READINESS WIRING (NEW)

### API Endpoint
```
GET /api/session-regime-gate/snapshot
```

### Response Structure
```json
{
  "data": {
    "ok": true,
    "current_session": "asia" | "london" | "london_ny_overlap" | "new_york" | "transition",
    "current_time_utc": "ISO8601",
    "last_known_regime": "TRENDING" | "RANGING" | "CHOPPY" | "UNKNOWN",
    "last_policy_key": "session|regime|news_state|bias_alignment",
    "trade_block_reason": string | null,
    "block_details": {
      "roadmap_aligned": boolean,
      "is_embargo": boolean,
      "daily_bias": "BULLISH" | "BEARISH" | "NEUTRAL",
      "weekly_bias": "BULLISH" | "BEARISH" | "NEUTRAL",
      "news_state": "normal" | "elevated" | "embargo",
      "session": string,
      "regime": string
    },
    "readiness": "READY" | "WAITING" | "BLOCKED",
    "readiness_score": 0-100,
    "candles_remaining": number,
    "eta_seconds": number,
    "next_session": {
      "next_tradable_session": string,
      "countdown_seconds": number,
      "target_utc": "ISO8601"
    },
    "ts_utc": number
  },
  "truth": {
    "source": "session_regime_gate_panel",
    "complete": true
  }
}
```

### Additional Endpoint (Regime Readiness from Status)
```
GET /api/truth/status
```

### Response Structure (includes regime_readiness)
```json
{
  "data": {
    "system_truth_state": "FULL" | "PARTIAL" | "NONE",
    "checks": {
      "status_snapshot": boolean,
      "audit_log": boolean,
      "outlook_daily": boolean,
      "structural_scanner": boolean,
      "trade_ledger": boolean
    },
    "ts_utc": number,
    "regime_readiness": {
      "score": 0-100,
      "candles_remaining": number,
      "eta_seconds": number,
      "regime": "TRENDING" | "RANGING" | "CHOPPY" | "UNKNOWN",
      "last_updated": "ISO8601"
    }
  }
}
```

### Dashboard Element Mappings

| Dashboard Element | API Field Path | Display Format |
|-------------------|----------------|-----------------|
| **Readiness Score Gauge** | `data.readiness_score` | Circular gauge 0-100, color-coded |
| **Regime ETA Countdown** | `data.eta_seconds` | "HH:MM:SS" countdown timer |
| **Candles Remaining** | `data.candles_remaining` | Number with label "candles" |
| **Trade Imminent Banner** | Check audit log for `TRADE_IMMINENT` event | Conditional banner (only when score >= 80) |
| **Current Session** | `data.current_session` | Session badge (London/NY/etc) |
| **Regime Status** | `data.last_known_regime` | Regime badge |
| **Readiness Status** | `data.readiness` | "READY" / "WAITING" / "BLOCKED" |
| **Block Reason** | `data.trade_block_reason` | Tooltip/explanation |
| **Next Session Countdown** | `data.next_session.countdown_seconds` | "Next: London in 2h 15m" |

### HTML Structure Required

```html
<!-- Add to Live Terminal Tab or create new "Readiness" section -->
<div class="glass-card p-6 rounded-2xl mb-4">
    <h3 class="text-lg font-bold mb-4 flex items-center gap-2">
        <span>🎯</span> Trading Readiness
    </h3>
    
    <!-- Readiness Score Gauge -->
    <div class="flex items-center justify-center mb-4">
        <div class="relative w-32 h-32">
            <svg class="transform -rotate-90 w-32 h-32">
                <circle cx="64" cy="64" r="56" stroke="#1f2937" stroke-width="8" fill="none"/>
                <circle 
                    id="readiness-gauge" 
                    cx="64" cy="64" r="56" 
                    stroke="#00ff88" 
                    stroke-width="8" 
                    fill="none"
                    stroke-dasharray="351.86"
                    stroke-dashoffset="351.86"
                    stroke-linecap="round"/>
            </svg>
            <div class="absolute inset-0 flex items-center justify-center">
                <div class="text-center">
                    <div id="readiness-score-value" class="text-3xl font-black text-[#00ff88]">0</div>
                    <div class="text-xs text-gray-400 uppercase">Readiness</div>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Regime ETA Countdown -->
    <div class="bg-black/30 p-4 rounded-lg mb-3">
        <div class="text-xs text-gray-500 uppercase mb-1">Regime Resolution ETA</div>
        <div id="regime-eta" class="text-2xl font-mono font-bold text-white">--:--:--</div>
        <div class="text-xs text-gray-400 mt-1">
            <span id="candles-remaining">0</span> candles remaining
        </div>
    </div>
    
    <!-- Trade Imminent Banner (Conditional) -->
    <div id="trade-imminent-banner" class="hidden bg-gradient-to-r from-[#00ff88]/20 to-[#00cc6a]/10 border-2 border-[#00ff88] p-4 rounded-lg mb-3">
        <div class="flex items-center gap-2">
            <span class="w-3 h-3 rounded-full bg-[#00ff88] animate-pulse"></span>
            <span class="font-black text-[#00ff88] uppercase text-sm">TRADE IMMINENT</span>
        </div>
        <p class="text-xs text-gray-300 mt-2">All conditions met. System ready for execution.</p>
    </div>
    
    <!-- Current Status Grid -->
    <div class="grid grid-cols-2 gap-3 mt-4">
        <div>
            <div class="text-xs text-gray-500 uppercase">Session</div>
            <div id="current-session" class="font-bold text-white">--</div>
        </div>
        <div>
            <div class="text-xs text-gray-500 uppercase">Regime</div>
            <div id="current-regime" class="font-bold text-white">--</div>
        </div>
        <div>
            <div class="text-xs text-gray-500 uppercase">Status</div>
            <div id="readiness-status" class="font-bold text-white">--</div>
        </div>
        <div>
            <div class="text-xs text-gray-500 uppercase">Next Session</div>
            <div id="next-session-countdown" class="font-bold text-white">--</div>
        </div>
    </div>
    
    <!-- Block Reason (if blocked) -->
    <div id="block-reason" class="mt-3 text-xs text-red-400 hidden"></div>
</div>
```

### JavaScript Implementation

```javascript
// Poll session regime gate snapshot
async function pollSessionRegimeGate() {
    try {
        const response = await fetch('/api/session-regime-gate/snapshot');
        const envelope = await response.json();
        const data = envelope.data;
        
        if (!data || !data.ok) {
            console.warn('Session regime gate snapshot unavailable');
            return;
        }
        
        // Update Readiness Score Gauge
        const score = data.readiness_score || 0;
        const gauge = document.getElementById('readiness-gauge');
        const scoreValue = document.getElementById('readiness-score-value');
        
        if (gauge && scoreValue) {
            // Calculate stroke-dashoffset (351.86 is circumference for r=56)
            const circumference = 2 * Math.PI * 56; // ~351.86
            const offset = circumference - (score / 100) * circumference;
            gauge.style.strokeDashoffset = offset;
            
            // Color coding
            if (score >= 80) {
                gauge.setAttribute('stroke', '#00ff88'); // Green
            } else if (score >= 50) {
                gauge.setAttribute('stroke', '#ffc107'); // Yellow
            } else {
                gauge.setAttribute('stroke', '#ff3e3e'); // Red
            }
            
            scoreValue.textContent = score;
        }
        
        // Update Regime ETA Countdown
        const etaSeconds = data.eta_seconds || 0;
        const etaEl = document.getElementById('regime-eta');
        const candlesEl = document.getElementById('candles-remaining');
        
        if (etaEl) {
            if (etaSeconds > 0) {
                const hours = Math.floor(etaSeconds / 3600);
                const minutes = Math.floor((etaSeconds % 3600) / 60);
                const seconds = etaSeconds % 60;
                etaEl.textContent = `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
            } else {
                etaEl.textContent = 'READY';
            }
        }
        
        if (candlesEl) {
            candlesEl.textContent = String(data.candles_remaining || 0);
        }
        
        // Update Trade Imminent Banner
        const banner = document.getElementById('trade-imminent-banner');
        if (banner) {
            if (score >= 80 && data.readiness === 'READY') {
                banner.classList.remove('hidden');
            } else {
                banner.classList.add('hidden');
            }
        }
        
        // Update Current Status
        setText('current-session', data.current_session?.toUpperCase() || '--');
        setText('current-regime', data.last_known_regime || '--');
        setText('readiness-status', data.readiness || '--');
        
        // Update Next Session Countdown
        if (data.next_session) {
            const nextCountdown = data.next_session.countdown_seconds || 0;
            const hours = Math.floor(nextCountdown / 3600);
            const minutes = Math.floor((nextCountdown % 3600) / 60);
            setText('next-session-countdown', `${hours}h ${minutes}m`);
        }
        
        // Update Block Reason
        const blockReasonEl = document.getElementById('block-reason');
        if (blockReasonEl) {
            if (data.trade_block_reason) {
                blockReasonEl.textContent = `Blocked: ${data.trade_block_reason}`;
                blockReasonEl.classList.remove('hidden');
            } else {
                blockReasonEl.classList.add('hidden');
            }
        }
        
        return data;
    } catch (e) {
        console.error('Poll session regime gate error:', e);
        return null;
    }
}

// Check for TRADE_IMMINENT events in audit log
async function checkTradeImminent() {
    try {
        const response = await fetch('/api/session-regime-gate/decisions?limit=10');
        const envelope = await response.json();
        const decisions = envelope.data?.decisions || [];
        
        // Find most recent TRADE_IMMINENT event
        const imminentEvent = decisions.find(d => d.event === 'TRADE_IMMINENT');
        
        const banner = document.getElementById('trade-imminent-banner');
        if (banner) {
            if (imminentEvent) {
                // Check if event is recent (within last 5 minutes)
                const eventTime = new Date(imminentEvent.timestamp);
                const now = new Date();
                const ageMs = now - eventTime;
                const ageMins = ageMs / 60000;
                
                if (ageMins < 5) {
                    banner.classList.remove('hidden');
                } else {
                    banner.classList.add('hidden');
                }
            } else {
                banner.classList.add('hidden');
            }
        }
    } catch (e) {
        console.error('Check trade imminent error:', e);
    }
}

// Start countdown timer for ETA
function startCountdownTimer() {
    setInterval(() => {
        const etaEl = document.getElementById('regime-eta');
        if (!etaEl) return;
        
        const currentText = etaEl.textContent;
        if (currentText === 'READY' || currentText === '--:--:--') return;
        
        // Parse current time and decrement
        const parts = currentText.split(':');
        let totalSeconds = parseInt(parts[0]) * 3600 + parseInt(parts[1]) * 60 + parseInt(parts[2]);
        
        if (totalSeconds > 0) {
            totalSeconds--;
            const hours = Math.floor(totalSeconds / 3600);
            const minutes = Math.floor((totalSeconds % 3600) / 60);
            const seconds = totalSeconds % 60;
            etaEl.textContent = `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
        } else {
            etaEl.textContent = 'READY';
        }
    }, 1000);
}
```

---

## 3. MARKET DATA WIRING

### API Endpoint
```
GET /api/market/overview
```

### Response Structure
```json
{
  "data": {
    "system_label": "ALPHA" | "BETA",
    "ts_utc": "ISO8601",
    "instruments": [
      {
        "instrument": "XAU_USD",
        "bid": number,
        "ask": number,
        "mid": number,
        "time": "ISO8601",
        "status": "ok" | "error",
        "regime": {
          "regime": "TRENDING" | "RANGING" | "CHOPPY" | "UNKNOWN",
          "desc": string,
          "adx": number
        }
      }
    ],
    "metadata": {
      "last_scan_at": "ISO8601",
      "last_signals_generated": number,
      "last_executed_count": number
    }
  }
}
```

### Dashboard Element Mappings

| Dashboard Element | API Field Path | Display Format |
|-------------------|----------------|-----------------|
| Instrument Prices | `data.instruments[].bid/ask/mid` | Price display with spread |
| Instrument Regime | `data.instruments[].regime.regime` | Regime badge |
| Instrument ADX | `data.instruments[].regime.adx` | ADX value |
| Last Scan | `data.metadata.last_scan_at` | Relative time |

### JavaScript Implementation
```javascript
async function pollMarketOverview() {
    try {
        const response = await fetch('/api/market/overview');
        const envelope = await response.json();
        const data = envelope.data;
        
        if (!data || !data.instruments) return;
        
        // Update price displays for each instrument
        data.instruments.forEach(inst => {
            const priceEl = document.getElementById(`price-${inst.instrument}`);
            if (priceEl) {
                priceEl.textContent = inst.mid?.toFixed(5) || '--';
            }
            
            const regimeEl = document.getElementById(`regime-${inst.instrument}`);
            if (regimeEl) {
                regimeEl.textContent = inst.regime?.regime || 'UNKNOWN';
            }
        });
        
        return data;
    } catch (e) {
        console.error('Poll market overview error:', e);
        return null;
    }
}
```

---

## 4. NEWS & AI INSIGHTS WIRING

### API Endpoints
```
GET /api/news
GET /api/news/assess
GET /api/economic_calendar
```

### Response Structures

**/api/news:**
```json
{
  "data": {
    "ok": true,
    "news": [
      {
        "id": string,
        "ts_utc": number,
        "source": string,
        "title": string,
        "url": string,
        "summary": string,
        "symbols": [string],
        "impact": "high" | "medium" | "low"
      }
    ],
    "provider_status": {},
    "source_mode": "snapshot" | "provider_registry",
    "ts_utc": number
  }
}
```

**/api/news/assess:**
```json
{
  "data": {
    "ok": true,
    "news_count": number,
    "summary": string,
    "sentiment": "positive" | "negative" | "neutral",
    "impact_score": 1-9,
    "provider": "AI_QUANT_INTERNAL",
    "timestamp": number
  }
}
```

### Dashboard Element Mappings

| Dashboard Element | API Field Path | Display Format |
|-------------------|----------------|-----------------|
| News Count | `data.news_count` | Number badge |
| Sentiment | `data.sentiment` | Color-coded badge |
| Impact Score | `data.impact_score` | 1-9 scale display |
| News Summary | `data.summary` | Text block |
| News Feed | `data.news[]` | List of news items |
| Economic Calendar | `/api/economic_calendar` | Upcoming events list |

### JavaScript Implementation
```javascript
async function pollNews() {
    try {
        const [newsResponse, assessResponse] = await Promise.all([
            fetch('/api/news'),
            fetch('/api/news/assess')
        ]);
        
        const newsEnvelope = await newsResponse.json();
        const assessEnvelope = await assessResponse.json();
        
        const newsData = newsEnvelope.data;
        const assessData = assessEnvelope.data;
        
        // Update news count
        setText('news-count', String(assessData.news_count || 0));
        
        // Update sentiment
        const sentimentEl = document.getElementById('news-sentiment');
        if (sentimentEl) {
            sentimentEl.textContent = assessData.sentiment?.toUpperCase() || 'NEUTRAL';
            sentimentEl.className = assessData.sentiment === 'positive' ? 'chip chip-success' : 
                                   assessData.sentiment === 'negative' ? 'chip chip-danger' : 
                                   'chip chip-warning';
        }
        
        // Update impact score
        setText('news-impact-score', String(assessData.impact_score || 0));
        
        // Update summary
        setText('news-sentiment-summary', assessData.summary || 'No news analysis available');
        
        // Render news feed
        const feedEl = document.getElementById('news-feed');
        if (feedEl && newsData.news) {
            feedEl.innerHTML = newsData.news.slice(0, 10).map(item => `
                <div class="glass-card p-3 rounded-lg mb-2">
                    <div class="flex justify-between items-start mb-1">
                        <h4 class="font-bold text-sm text-white">${item.title || 'No title'}</h4>
                        <span class="chip ${item.impact === 'high' ? 'chip-danger' : item.impact === 'medium' ? 'chip-warning' : 'chip-success'} text-[8px]">
                            ${item.impact?.toUpperCase() || 'LOW'}
                        </span>
                    </div>
                    <p class="text-xs text-gray-400">${item.summary || ''}</p>
                    <div class="text-[10px] text-gray-500 mt-2">
                        ${new Date(item.ts_utc * 1000).toLocaleString()}
                    </div>
                </div>
            `).join('');
        }
        
        return { news: newsData, assess: assessData };
    } catch (e) {
        console.error('Poll news error:', e);
        return null;
    }
}

async function pollEconomicCalendar() {
    try {
        const response = await fetch('/api/economic_calendar');
        const envelope = await response.json();
        const data = envelope.data;
        
        if (!data || !data.events) return;
        
        const calendarEl = document.getElementById('economic-calendar');
        if (calendarEl) {
            calendarEl.innerHTML = data.events.slice(0, 5).map(event => {
                const countdown = Math.floor(event.countdown_seconds / 60);
                return `
                    <div class="glass-card p-3 rounded-lg mb-2">
                        <div class="flex justify-between items-start">
                            <div>
                                <h4 class="font-bold text-sm text-white">${event.title}</h4>
                                <p class="text-xs text-gray-400">${event.country} - ${event.currency}</p>
                            </div>
                            <div class="text-right">
                                <div class="chip ${event.impact === 'high' ? 'chip-danger' : 'chip-warning'} text-[8px]">
                                    ${event.impact?.toUpperCase() || 'MEDIUM'}
                                </div>
                                <div class="text-xs text-gray-400 mt-1">${countdown}m</div>
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
        }
        
        return data;
    } catch (e) {
        console.error('Poll economic calendar error:', e);
        return null;
    }
}
```

---

## 5. PERFORMANCE & JOURNAL WIRING

### API Endpoints
```
GET /api/performance/summary?days=30
GET /api/performance/strategies?days=30
GET /api/performance/accounts?days=30
GET /api/performance/ai-evaluation?days=30
GET /api/journal/trades?limit=50&offset=0
```

### Response Structures

**/api/performance/summary:**
```json
{
  "data": {
    "ok": true,
    "status": "OK" | "NO_DATA",
    "total_trades": number,
    "win_rate": number,
    "total_pnl": number,
    "ts_utc": number
  }
}
```

**/api/journal/trades:**
```json
{
  "data": {
    "ok": true,
    "trades": [
      {
        "id": string,
        "instrument": string,
        "side": "BUY" | "SELL",
        "entry_price": number,
        "exit_price": number,
        "pnl": number,
        "status": "open" | "closed",
        "open_time": "ISO8601",
        "close_time": "ISO8601",
        "strategy_key": string,
        "account_id_redacted": string
      }
    ],
    "total": number,
    "limit": number,
    "offset": number,
    "ts_utc": number
  }
}
```

### JavaScript Implementation
```javascript
async function pollPerformance() {
    try {
        const [summary, strategies, accounts, aiEval] = await Promise.all([
            fetch('/api/performance/summary?days=30'),
            fetch('/api/performance/strategies?days=30'),
            fetch('/api/performance/accounts?days=30'),
            fetch('/api/performance/ai-evaluation?days=30')
        ]);
        
        const summaryData = (await summary.json()).data;
        const strategiesData = (await strategies.json()).data;
        const accountsData = (await accounts.json()).data;
        const aiEvalData = (await aiEval.json()).data;
        
        // Update performance cards
        const cardsEl = document.getElementById('performance-cards');
        if (cardsEl) {
            cardsEl.innerHTML = `
                <div class="glass-card p-6 rounded-2xl">
                    <h3 class="font-bold mb-4">Overall Performance</h3>
                    <div class="space-y-3">
                        <div class="flex justify-between">
                            <span class="text-gray-400">Total Trades</span>
                            <span class="font-bold text-white">${summaryData.total_trades || 0}</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-gray-400">Win Rate</span>
                            <span class="font-bold text-[#00ff88]">${((summaryData.win_rate || 0) * 100).toFixed(1)}%</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-gray-400">Total P&L</span>
                            <span class="font-bold ${summaryData.total_pnl >= 0 ? 'text-[#00ff88]' : 'text-red-400'}">
                                ${summaryData.total_pnl?.toFixed(2) || '0.00'}
                            </span>
                        </div>
                    </div>
                </div>
            `;
        }
        
        return { summary: summaryData, strategies: strategiesData, accounts: accountsData, aiEval: aiEvalData };
    } catch (e) {
        console.error('Poll performance error:', e);
        return null;
    }
}

async function pollJournal() {
    try {
        const response = await fetch('/api/journal/trades?limit=50&offset=0');
        const envelope = await response.json();
        const data = envelope.data;
        
        if (!data || !data.trades) return;
        
        // Render closed trades
        const journalEl = document.getElementById('journal-list');
        if (journalEl) {
            const closedTrades = data.trades.filter(t => t.status === 'closed');
            journalEl.innerHTML = closedTrades.map(trade => `
                <div class="glass-card p-4 rounded-lg mb-3">
                    <div class="flex justify-between items-start mb-2">
                        <div>
                            <h4 class="font-bold text-white">${trade.instrument} ${trade.side}</h4>
                            <p class="text-xs text-gray-400">${trade.strategy_key || 'Unknown'}</p>
                        </div>
                        <div class="text-right">
                            <div class="font-bold ${trade.pnl >= 0 ? 'text-[#00ff88]' : 'text-red-400'}">
                                ${trade.pnl >= 0 ? '+' : ''}${trade.pnl?.toFixed(2) || '0.00'}
                            </div>
                            <div class="text-xs text-gray-400">${new Date(trade.close_time).toLocaleDateString()}</div>
                        </div>
                    </div>
                </div>
            `).join('');
        }
        
        return data;
    } catch (e) {
        console.error('Poll journal error:', e);
        return null;
    }
}
```

---

## 6. ACTIVE TRADES WIRING

### API Endpoint
```
GET /api/trades/active
```

### Response Structure
```json
{
  "data": {
    "ok": boolean,
    "system_label": "ALPHA" | "BETA",
    "refreshed_at": "ISO8601",
    "accounts": [
      {
        "account_suffix": "006",
        "account_id_masked": "101***006",
        "open_trades_count": number,
        "open_positions_count": number,
        "lastTransactionID": number,
        "trades": [
          {
            "id": string,
            "instrument": string,
            "price": number,
            "units": string,
            "unrealizedPL": string,
            "openTime": "ISO8601",
            "state": "OPEN",
            "initialUnits": string,
            "realizedPL": string
          }
        ],
        "balance": number,
        "equity": number,
        "margin_used": number,
        "margin_available": number,
        "currency": "USD",
        "error": string | null
      }
    ]
  }
}
```

### JavaScript Implementation
```javascript
async function pollActiveTrades() {
    try {
        const response = await fetch('/api/trades/active');
        const envelope = await response.json();
        const data = envelope.data;
        
        if (!data || !data.accounts) return;
        
        // Render open trades
        const openTradesEl = document.getElementById('open-trades-list');
        if (openTradesEl) {
            const allTrades = data.accounts.flatMap(acc => 
                (acc.trades || []).map(t => ({ ...t, account: acc.account_suffix }))
            );
            
            if (allTrades.length === 0) {
                openTradesEl.innerHTML = '<div class="text-sm text-gray-400 italic">No open trades</div>';
            } else {
                openTradesEl.innerHTML = allTrades.map(trade => `
                    <div class="glass-card p-4 rounded-lg mb-3">
                        <div class="flex justify-between items-start">
                            <div>
                                <h4 class="font-bold text-white">${trade.instrument} ${parseFloat(trade.units) > 0 ? 'BUY' : 'SELL'}</h4>
                                <p class="text-xs text-gray-400">Account: ${trade.account}</p>
                                <p class="text-xs text-gray-400">Entry: ${trade.price}</p>
                            </div>
                            <div class="text-right">
                                <div class="font-bold ${parseFloat(trade.unrealizedPL) >= 0 ? 'text-[#00ff88]' : 'text-red-400'}">
                                    ${parseFloat(trade.unrealizedPL) >= 0 ? '+' : ''}${trade.unrealizedPL}
                                </div>
                                <div class="text-xs text-gray-400">Unrealized P&L</div>
                            </div>
                        </div>
                    </div>
                `).join('');
            }
        }
        
        // Update positions count
        const totalPositions = data.accounts.reduce((sum, acc) => sum + (acc.open_positions_count || 0), 0);
        setText('positions', String(totalPositions).padStart(2, '0'));
        
        return data;
    } catch (e) {
        console.error('Poll active trades error:', e);
        return null;
    }
}
```

---

## 7. STRATEGY MANAGEMENT WIRING

### API Endpoints
```
GET /api/strategies
POST /api/config (requires auth token)
POST /api/strategy/activate (requires auth token)
```

### JavaScript Implementation
```javascript
async function loadStrategies() {
    try {
        const response = await fetch('/api/strategies');
        const envelope = await response.json();
        const data = envelope.data;
        
        if (!data || !data.allowed) return;
        
        // Render strategy buttons
        const buttonsEl = document.getElementById('strategy-buttons');
        if (buttonsEl) {
            buttonsEl.innerHTML = data.allowed.map(key => {
                const info = data.strategies?.find(s => s.key === key) || {};
                const isActive = key === data.default;
                return `
                    <button 
                        id="strategy-${key}"
                        class="strategy-btn ${isActive ? 'active' : ''} px-4 py-2 rounded-lg text-sm font-bold"
                        onclick="switchStrategy('${key}')">
                        ${info.name || key}
                    </button>
                `;
            }).join('');
        }
        
        return data;
    } catch (e) {
        console.error('Load strategies error:', e);
        return null;
    }
}

async function switchStrategy(strategyKey) {
    const token = localStorage.getItem('control_plane_token');
    if (!token) {
        alert('Please set CONTROL_PLANE_TOKEN in Settings');
        return;
    }
    
    try {
        const response = await fetch('/api/config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ active_strategy_key: strategyKey })
        });
        
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const envelope = await response.json();
        if (envelope.data?.status === 'ok') {
            alert(`Strategy switched to ${strategyKey}`);
            await loadStrategies();
            await pollStatus();
        }
    } catch (e) {
        console.error('Switch strategy error:', e);
        alert(`Failed to switch strategy: ${e.message}`);
    }
}
```

---

## 8. COMPLETE JAVASCRIPT IMPLEMENTATION

### Main Polling Loop

```javascript
// Initialize all polling functions
let pollingIntervals = {};

function startPolling() {
    // Status polling (every 5 seconds)
    pollingIntervals.status = setInterval(pollStatus, 5000);
    
    // Session regime gate polling (every 10 seconds)
    pollingIntervals.regime = setInterval(pollSessionRegimeGate, 10000);
    
    // Trade imminent check (every 30 seconds)
    pollingIntervals.imminent = setInterval(checkTradeImminent, 30000);
    
    // Market overview (every 15 seconds)
    pollingIntervals.market = setInterval(pollMarketOverview, 15000);
    
    // News (every 60 seconds)
    pollingIntervals.news = setInterval(pollNews, 60000);
    
    // Economic calendar (every 300 seconds)
    pollingIntervals.calendar = setInterval(pollEconomicCalendar, 300000);
    
    // Performance (every 120 seconds)
    pollingIntervals.performance = setInterval(pollPerformance, 120000);
    
    // Journal (every 30 seconds)
    pollingIntervals.journal = setInterval(pollJournal, 30000);
    
    // Active trades (every 10 seconds)
    pollingIntervals.activeTrades = setInterval(pollActiveTrades, 10000);
    
    // Strategies (once on load, then every 300 seconds)
    loadStrategies();
    pollingIntervals.strategies = setInterval(loadStrategies, 300000);
    
    // Start countdown timer for ETA
    startCountdownTimer();
    
    // Initial load
    Promise.all([
        pollStatus(),
        pollSessionRegimeGate(),
        pollMarketOverview(),
        pollNews(),
        pollEconomicCalendar(),
        pollPerformance(),
        pollJournal(),
        pollActiveTrades(),
        checkTradeImminent()
    ]).catch(console.error);
}

function stopPolling() {
    Object.values(pollingIntervals).forEach(interval => clearInterval(interval));
    pollingIntervals = {};
}

// Start polling when page loads
document.addEventListener('DOMContentLoaded', () => {
    startPolling();
});

// Stop polling when page unloads
window.addEventListener('beforeunload', () => {
    stopPolling();
});
```

### Helper Functions

```javascript
// Safe text setter
function setText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text || '';
}

// Safe HTML setter
function setHTML(id, html) {
    const el = document.getElementById(id);
    if (el) el.innerHTML = html || '';
}

// Format relative time
function formatRelativeTime(isoString) {
    if (!isoString) return '--';
    const time = new Date(isoString);
    const now = new Date();
    const diffMs = now - time;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    return `${diffDays}d ago`;
}

// Format currency
function formatCurrency(value, currency = 'USD') {
    if (value === null || value === undefined) return '--';
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: currency,
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(value);
}

// Format percentage
function formatPercent(value) {
    if (value === null || value === undefined) return '--';
    return `${(value * 100).toFixed(1)}%`;
}
```

---

## DEPLOYMENT CHECKLIST

- [ ] Add HTML structure for Readiness Gauge section to `templates/forensic_command.html`
- [ ] Add JavaScript functions to `templates/forensic_command.html` `<script>` section
- [ ] Initialize polling on page load
- [ ] Test all API endpoints return expected data
- [ ] Verify readiness score updates correctly
- [ ] Verify countdown timer decrements
- [ ] Verify TRADE_IMMINENT banner appears/disappears correctly
- [ ] Verify all dashboard tabs display data correctly
- [ ] Test error handling (API failures, missing data)
- [ ] Verify no console errors in browser

---

## NOTES

1. **Truth Envelope**: All API responses are wrapped in a `truth` envelope. Always access data via `envelope.data`.

2. **Error Handling**: All polling functions should catch errors and log them without breaking the UI.

3. **Rate Limiting**: Polling intervals are conservative to avoid overwhelming the API. Adjust as needed.

4. **Authentication**: POST endpoints require `CONTROL_PLANE_TOKEN` in `Authorization: Bearer <token>` header.

5. **CORS**: API is same-origin only by default. No CORS headers needed for localhost.

6. **Cache Control**: Dashboard HTML should have `Cache-Control: no-store` headers (already set in API).

---

**END OF SPECIFICATION**
