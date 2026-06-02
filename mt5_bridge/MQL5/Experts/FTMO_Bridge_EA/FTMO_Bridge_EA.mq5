//+------------------------------------------------------------------+
//|                                               FTMO_Bridge_EA.mq5 |
//|                                    Copyright 2026, AI Quant Team |
//|                                          https://www.example.com |
//+------------------------------------------------------------------+
#property copyright "Copyright 2026, AI Quant Team"
#property link      "https://www.example.com"
#property version   "1.04"
#property strict

// Enable WebRequest for the specific URL in MT5 Options if using WEB source!
#include "SimpleJson.mqh"
#include <Trade\Trade.mqh>

enum ENUM_SIGNAL_SOURCE
{
   SOURCE_WEB,
   SOURCE_FILE
};

/// Canonical pending/market classification (centralized validation + OrderSend routing).
enum ENUM_FXG_ENTRY_KIND
{
   FXG_ENTRY_MARKET = 0,
   FXG_ENTRY_BUY_LIMIT,
   FXG_ENTRY_SELL_LIMIT,
   FXG_ENTRY_BUY_STOP,
   FXG_ENTRY_SELL_STOP,
   FXG_ENTRY_UNSUPPORTED = 99
};

//+------------------------------------------------------------------+
//| Inputs                                                           |
//+------------------------------------------------------------------+
input ENUM_SIGNAL_SOURCE InpSignalSource = SOURCE_FILE;             // Signal Source
input string   InpApiUrl         = "http://127.0.0.1:28787/api/signals"; // ALPHA API URL (if WEB)
input string   InpSignalFilePath = "signals.jsonl";                 // Signal File Path (if FILE, relative to MQL5/Files)
input string   InpLogFilePath    = "ftmo_bridge_log.jsonl";        // Bridge Log File (relative to MQL5/Files)
input string   InpDedupeDir      = "fxg_dedupe";                    // Dedupe Dir for one-trade-per-signal lock files
input string   InpBridgeAccount  = "ftmo_demo2";                         // Bridge Account ID (Must match ALPHA)
input int      InpPollInterval   = 1;                                    // Poll Interval (seconds)
input bool     InpEnableExecution = false;                               // KILL SWITCH (Must be true to trade)
input double   InpMaxDailyLoss   = 500.0;                                // Max Daily Loss (Account Currency)
input double   InpMaxTotalLoss   = 1000.0;                               // Max Total Loss (Account Currency)
input double   InpRiskPerTrade   = 0.5;                                  // Max Risk % per trade
input double   InpLotSize        = 0.01;                                  // Lot Size (position size for execution)
input int      InpMagicNumber    = 123456;                               // Magic Number (Unique per Instance)

//+------------------------------------------------------------------+
//| Global Variables                                                 |
//+------------------------------------------------------------------+
CTrade   gl_trade;
int      gl_timer_handle;
string   gl_last_processed_signal_id = "";
string   gl_latest_signal_id_seen = "";
string   gl_latest_signal_id_attempted = "";
string   gl_latest_signal_id_executed_ok = "";
string   gl_latest_signal_id_failed = "";
string   gl_last_result_code = "";
double   gl_start_of_day_equity = 0.0;
datetime gl_last_day_check = 0;
ulong    gl_last_file_position = 0; // To track file reading position (FileTell returns ulong)
ulong    gl_metrics_terminal_rejects = 0;
ulong    gl_metrics_lock_dedupe_hits = 0;
ulong    gl_metrics_validation_ok = 0;
int      gl_last_cycle_new_lines = 0;

// Heartbeat (compact, overwrite every write)
#define FXG_HEARTBEAT_FILE "ftmo_consumer_heartbeat.json"
#define FXG_HEARTBEAT_SCHEMA_VERSION 1

//+------------------------------------------------------------------+
string FxgIsoUtcNow()
{
   datetime t = TimeGMT();
   MqlDateTime dt;
   TimeToStruct(t, dt);
   return StringFormat("%04d-%02d-%02dT%02d:%02d:%02dZ", dt.year, dt.mon, dt.day, dt.hour, dt.min, dt.sec);
}

string FxgJsonEscape(string s)
{
   // Minimal JSON string escaper (fail-open). Avoids breaking monitoring consumers.
   string out = "";
   for(int i = 0; i < StringLen(s); i++)
   {
      ushort c = StringGetCharacter(s, i);
      if(c == '\\') out += "\\\\";
      else if(c == '"') out += "\\\"";
      else if(c == '\n') out += "\\n";
      else if(c == '\r') out += "\\r";
      else if(c == '\t') out += "\\t";
      else if(c < 32) out += " "; // control chars -> space
      else out += CharToString((uchar)c);
   }
   return out;
}

bool FxgWriteHeartbeat(string event_hint)
{
   string ea_name = MQLInfoString(MQL_PROGRAM_NAME);
   string ea_ver = MQLInfoString(MQL_PROGRAM_VERSION);
   if(StringLen(ea_name) < 1) ea_name = "FTMO_Bridge_EA";
   if(StringLen(ea_ver) < 1) ea_ver = "1.04";

   string mt5_symbol = Symbol();
   string ts = FxgIsoUtcNow();
   long login = (long)AccountInfoInteger(ACCOUNT_LOGIN);
   string server = AccountInfoString(ACCOUNT_SERVER);
   double bal = AccountInfoDouble(ACCOUNT_BALANCE);
   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   bool exec_enabled = InpEnableExecution;
   bool kill_enabled = !InpEnableExecution;

   string json = "{"
      + "\"heartbeat_schema_version\":" + IntegerToString(FXG_HEARTBEAT_SCHEMA_VERSION) + ","
      + "\"ts_utc\":\"" + FxgJsonEscape(ts) + "\","
      + "\"bridge_account\":\"" + FxgJsonEscape(InpBridgeAccount) + "\","
      + "\"ea_name\":\"" + FxgJsonEscape(ea_name) + "\","
      + "\"ea_version\":\"" + FxgJsonEscape(ea_ver) + "\","
      + "\"chart_symbol\":\"" + FxgJsonEscape(mt5_symbol) + "\","
      + "\"signal_file_path\":\"" + FxgJsonEscape(InpSignalFilePath) + "\","
      + "\"bridge_log_path\":\"" + FxgJsonEscape(InpLogFilePath) + "\","
      + "\"poll_interval_seconds\":" + IntegerToString(InpPollInterval) + ","
      + "\"kill_switch_enabled\":" + (kill_enabled ? "true" : "false") + ","
      + "\"execution_enabled\":" + (exec_enabled ? "true" : "false") + ","
      + "\"latest_signal_id_seen\":\"" + FxgJsonEscape(gl_latest_signal_id_seen) + "\","
      + "\"latest_signal_id_attempted\":\"" + FxgJsonEscape(gl_latest_signal_id_attempted) + "\","
      + "\"latest_signal_id_executed_ok\":\"" + FxgJsonEscape(gl_latest_signal_id_executed_ok) + "\","
      + "\"latest_signal_id_failed\":\"" + FxgJsonEscape(gl_latest_signal_id_failed) + "\","
      + "\"last_result_code\":\"" + FxgJsonEscape(gl_last_result_code) + "\","
      + "\"validation_ok_count\":" + IntegerToString((int)gl_metrics_validation_ok) + ","
      + "\"terminal_rejects_count\":" + IntegerToString((int)gl_metrics_terminal_rejects) + ","
      + "\"lock_dedupe_hits_count\":" + IntegerToString((int)gl_metrics_lock_dedupe_hits) + ","
      + "\"last_cycle_new_lines\":" + IntegerToString((int)gl_last_cycle_new_lines) + ","
      + "\"account_login\":\"" + FxgJsonEscape(IntegerToString((int)login)) + "\","
      + "\"account_server\":\"" + FxgJsonEscape(server) + "\","
      + "\"account_balance\":" + DoubleToString(bal, 2) + ","
      + "\"account_equity\":" + DoubleToString(eq, 2) + ","
      + "\"event_hint\":\"" + FxgJsonEscape(event_hint) + "\""
      + "}";

   int h = FileOpen(FXG_HEARTBEAT_FILE, FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_SHARE_READ|FILE_SHARE_WRITE);
   if(h == INVALID_HANDLE)
   {
      int err = (int)GetLastError();
      Print("FXG_HEARTBEAT: write failed path=", FXG_HEARTBEAT_FILE, " err=", err);
      LogEvent("HEARTBEAT_FAIL", "", StringFormat("path=%s err=%d", FXG_HEARTBEAT_FILE, err));
      return false;
   }
   FileWriteString(h, json);
   FileClose(h);
   return true;
}

//+------------------------------------------------------------------+
string FxgStringUpper(string s)
{
   string out = "";
   for(int i = 0; i < StringLen(s); i++)
   {
      ushort c = StringGetCharacter(s, i);
      if(c >= 'a' && c <= 'z')
         c = (ushort)(c - 32);
      out += CharToString((uchar)c);
   }
   return out;
}

//+------------------------------------------------------------------+
double ExtractLimitPriceFromSignal(string json_signal)
{
   double p = CSimpleJson::ExtractDouble(json_signal, "limit_price");
   if(p > 0)
      return p;
   p = CSimpleJson::ExtractDouble(json_signal, "price");
   if(p > 0)
      return p;
   p = CSimpleJson::ExtractDouble(json_signal, "entry");
   return p;
}

//+------------------------------------------------------------------+
ENUM_FXG_ENTRY_KIND ClassifyEntryOrderKind(string entry_u, string side_u)
{
   bool has_limit = (StringFind(entry_u, "LIMIT") >= 0);
   bool has_stop = (StringFind(entry_u, "STOP") >= 0);
   if(has_limit && has_stop)
      return FXG_ENTRY_UNSUPPORTED;
   if(has_limit)
   {
      if(StringFind(side_u, "BUY") >= 0)
         return FXG_ENTRY_BUY_LIMIT;
      if(StringFind(side_u, "SELL") >= 0)
         return FXG_ENTRY_SELL_LIMIT;
      return FXG_ENTRY_UNSUPPORTED;
   }
   if(has_stop)
   {
      if(StringFind(side_u, "BUY") >= 0)
         return FXG_ENTRY_BUY_STOP;
      if(StringFind(side_u, "SELL") >= 0)
         return FXG_ENTRY_SELL_STOP;
      return FXG_ENTRY_UNSUPPORTED;
   }
   return FXG_ENTRY_MARKET;
}

//+------------------------------------------------------------------+
/// BUY LIMIT: entry < Ask. SELL LIMIT: entry > Bid.
/// BUY STOP: entry > Ask. SELL STOP: entry < Bid.
bool ValidatePendingEntryVsMarket(string mt5_symbol, ENUM_FXG_ENTRY_KIND kind, double pending_price, string &reason_out)
{
   reason_out = "";
   double bid = SymbolInfoDouble(mt5_symbol, SYMBOL_BID);
   double ask = SymbolInfoDouble(mt5_symbol, SYMBOL_ASK);
   if(bid <= 0 || ask <= 0 || pending_price <= 0)
   {
      reason_out = "no_quotes_or_bad_price";
      return false;
   }
   switch(kind)
   {
      case FXG_ENTRY_BUY_LIMIT:
         if(pending_price >= ask)
         {
            reason_out = "invalid_limit_vs_market";
            return false;
         }
         break;
      case FXG_ENTRY_SELL_LIMIT:
         if(pending_price <= bid)
         {
            reason_out = "invalid_limit_vs_market";
            return false;
         }
         break;
      case FXG_ENTRY_BUY_STOP:
         if(pending_price <= ask)
         {
            reason_out = "invalid_stop_vs_market";
            return false;
         }
         break;
      case FXG_ENTRY_SELL_STOP:
         if(pending_price >= bid)
         {
            reason_out = "invalid_stop_vs_market";
            return false;
         }
         break;
      default:
         break;
   }
   return true;
}

//+------------------------------------------------------------------+
void EnsureDedupeDir()
{
   if(StringLen(InpDedupeDir) < 1)
      return;
   if(!FolderCreate(InpDedupeDir))
   {
      int err = (int)GetLastError();
      if(err != 5019)
         Print("FTMO_Bridge: FolderCreate dedupe failed path=", InpDedupeDir, " err=", err);
   }
}

//+------------------------------------------------------------------+
bool WriteSignalLockFile(string signal_id)
{
   EnsureDedupeDir();
   string lock_path = InpDedupeDir + "/" + signal_id + ".lock";
   int lock_handle = FileOpen(lock_path, FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(lock_handle != INVALID_HANDLE)
   {
      FileWriteString(lock_handle, signal_id);
      FileClose(lock_handle);
      return true;
   }
   return false;
}

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   Print("Initializing FTMO Bridge EA...");
   Print("Signal Source: ", EnumToString(InpSignalSource));
   if (InpSignalSource == SOURCE_WEB) Print("API URL: ", InpApiUrl);
   else Print("File Path: ", InpSignalFilePath);
   
   Print("Bridge Account: ", InpBridgeAccount);
   Print("Log File: ", InpLogFilePath);
   Print("Dedupe Dir: ", InpDedupeDir);
   Print("Execution Enabled: ", InpEnableExecution);
   EnsureDedupeDir();

   // Timer for polling
   EventSetTimer(InpPollInterval);
   
   // Initialize trade object
   gl_trade.SetExpertMagicNumber(InpMagicNumber);
   gl_trade.SetDeviationInPoints(10);
   gl_trade.SetTypeFilling(ORDER_FILLING_IOC);
   
   // Initialize daily equity
   gl_start_of_day_equity = AccountInfoDouble(ACCOUNT_EQUITY);
   gl_last_day_check = TimeCurrent();
   
   // Log Start (use InpLogFilePath)
   LogEvent("EA_START", "Initialized", StringFormat("Account:%s Exec:%s", InpBridgeAccount, InpEnableExecution ? "true" : "false"));
   gl_last_result_code = "init_ok";
   FxgWriteHeartbeat("init");
   
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   EventKillTimer();
   LogEvent("EA_STOP", "Deinitialized", EnumToString((ENUM_INIT_RETCODE)reason));
   gl_last_result_code = "deinit";
   FxgWriteHeartbeat("deinit");
}

//+------------------------------------------------------------------+
//| Expert timer function                                            |
//+------------------------------------------------------------------+
void OnTimer()
{
   CheckNewDay();
   
   if (InpSignalSource == SOURCE_WEB)
      FetchAndProcessSignalsWeb();
   else
      FetchAndProcessSignalsFile();

   // Always write heartbeat at end of cycle (fail-open).
   if(StringLen(gl_last_result_code) < 1)
      gl_last_result_code = "cycle_ok";
   FxgWriteHeartbeat("cycle");
}

//+------------------------------------------------------------------+
//| Logic                                                            |
//+------------------------------------------------------------------+

void CheckNewDay()
{
   datetime current_time = TimeCurrent();
   MqlDateTime dt, last_dt;
   TimeToStruct(current_time, dt);
   TimeToStruct(gl_last_day_check, last_dt);
   
   if(dt.day != last_dt.day)
   {
      Print("New day detected. Resetting daily stats.");
      gl_start_of_day_equity = AccountInfoDouble(ACCOUNT_EQUITY);
      gl_last_day_check = current_time;
   }
}

// --- FILE READING ---

void FetchAndProcessSignalsFile()
{
   // Open file for reading. We use FILE_SHARE_READ and FILE_SHARE_WRITE to coexist with Python.
   // MQL5 FileOpen with FILE_COMMON looks in global Common path, without it looks in MQL5/Files.
   // We assume MQL5/Files for now as per standard sandbox.
   
   int handle = FileOpen(InpSignalFilePath, FILE_READ|FILE_TXT|FILE_ANSI|FILE_SHARE_READ|FILE_SHARE_WRITE);
   
   if(handle == INVALID_HANDLE)
   {
      // Silent fail if file doesn't exist yet (Python hasn't started)
      // Print("Waiting for signal file...");
      return;
   }

   // If the signal file was replaced/synced to a smaller size, reset seek (prevents re-reading whole file wrongly).
   long fsize = FileSize(handle);
   if(fsize >= 0 && (ulong)fsize < gl_last_file_position)
      gl_last_file_position = 0;
   
   // Seek to last known position (FileSeek takes long; safe cast from ulong)
   if (gl_last_file_position > 0)
   {
      long seek_pos = (gl_last_file_position <= (ulong)2147483647) ? (long)gl_last_file_position : 2147483647;
      FileSeek(handle, seek_pos, SEEK_SET);
   }
   
   int new_lines_processed = 0;
      
   // Read new lines
   while(!FileIsEnding(handle))
   {
      string line = FileReadString(handle);
      
      // Update position
      // Note: FileTell might not be accurate after reading line if buffering involved, but usually ok.
      
      if (StringLen(line) > 0)
      {
         // Process the line
         // We expect one JSON object per line.
         ProcessResponse(line);
         new_lines_processed++;
      }
   }
   
   gl_last_file_position = FileTell(handle);
   FileClose(handle);
   gl_last_cycle_new_lines = new_lines_processed;
   
   // Visibility instrumentation: one log entry per read cycle
   LogEvent("CYCLE", "", StringFormat("file:%s last_id:%s new_lines:%s FXG_METRICS terminal_rejects:%s lock_dedupe_hits:%s validation_ok:%s",
              InpSignalFilePath, gl_last_processed_signal_id, IntegerToString(new_lines_processed),
              IntegerToString(gl_metrics_terminal_rejects), IntegerToString(gl_metrics_lock_dedupe_hits), IntegerToString(gl_metrics_validation_ok)));
}

// --- WEB READING ---

void FetchAndProcessSignalsWeb()
{
   char post_data[];
   ArrayResize(post_data, 0);  // empty for GET
   char result[];
   string result_headers;
   string url = InpApiUrl + "?limit=5"; // Fetch last 5 signals
   
   int timeout = 3000; // 3 seconds
   
   ResetLastError();
   // Use 7-param overload: method, url, headers, timeout, data[], result[], result_headers
   int res = WebRequest("GET", url, "", timeout, post_data, result, result_headers);
   
   if(res == 200)
   {
      // CharArrayToString expects uchar[]; WebRequest returns char[] - convert
      uchar uresult[];
      ArrayResize(uresult, ArraySize(result));
      for(int j = 0; j < ArraySize(result); j++)
         uresult[j] = (uchar)result[j];
      string json_response = CharArrayToString(uresult);
      
      // The WEB API usually returns an ARRAY of objects: [ {...}, {...} ]
      // The File usually contains one object per line: {...}
      // We need to handle both formats in ProcessResponse or separate them.
      
      // SimpleJson split is for array.
      string objects[];
      CSimpleJson::SplitArrayObjects(json_response, objects);
      
      for(int i=0; i<ArraySize(objects); i++)
      {
         ProcessSignal(objects[i]);
      }
      gl_last_cycle_new_lines = (int)ArraySize(objects);
   }
}

// --- PROCESSING ---

void ProcessResponse(string json_chunk)
{
   // Check if it's a single object or array
   // Basic check: starts with [ is array, { is object
   
   string trimmed = StringTrimLeft(json_chunk);
   
   if (StringFind(trimmed, "[") == 0)
   {
      // Array handling (mostly for WEB)
      string objects[];
      CSimpleJson::SplitArrayObjects(json_chunk, objects);
      for(int i=0; i<ArraySize(objects); i++)
         ProcessSignal(objects[i]);
   }
   else
   {
      // Single object handling (mostly for FILE line-by-line)
      ProcessSignal(json_chunk);
   }
}

void ProcessSignal(string json_signal)
{
   string signal_id = CSimpleJson::ExtractString(json_signal, "signal_id");
   if (signal_id == "") return; // Invalid line

   gl_latest_signal_id_seen = signal_id;
   
   // One-trade-per-signal guard: if lock exists, skip (already processed or terminal reject)
   string lock_path = InpDedupeDir + "/" + signal_id + ".lock";
   if (FileIsExist(lock_path))
   {
      gl_metrics_lock_dedupe_hits++;
      return;
   }
   
   // Deduplication check (in-memory)
   if (signal_id == gl_last_processed_signal_id) return;
   
   string bridge_acc = CSimpleJson::ExtractString(json_signal, "bridge_account");
   string symbol    = CSimpleJson::ExtractString(json_signal, "symbol");
   string side      = CSimpleJson::ExtractString(json_signal, "side");
   string strategy  = CSimpleJson::ExtractString(json_signal, "strategy");
   string news      = CSimpleJson::ExtractString(json_signal, "news_state");
   bool   execution_allowed = CSimpleJson::ExtractBool(json_signal, "execution_allowed");
   double lots_sig = CSimpleJson::ExtractDouble(json_signal, "lots");
   double sl_sig   = CSimpleJson::ExtractDouble(json_signal, "stop_loss");
   double tp_sig   = CSimpleJson::ExtractDouble(json_signal, "take_profit");
   string comment_payload = CSimpleJson::ExtractString(json_signal, "comment");
   string entry_type = CSimpleJson::ExtractString(json_signal, "entry_type");
   double limit_pr  = ExtractLimitPriceFromSignal(json_signal);
   string entry_u = FxgStringUpper(entry_type);
   string side_u = FxgStringUpper(side);
   ENUM_FXG_ENTRY_KIND entry_kind = ClassifyEntryOrderKind(entry_u, side_u);
   
   // 0. Account Routing Check
   if (bridge_acc != "" && bridge_acc != InpBridgeAccount)
   {
      // LogEvent("SIGNAL_SKIPPED", signal_id, StringFormat("Bridge Account Mismatch. Signal:%s EA:%s", bridge_acc, InpBridgeAccount));
      return; 
   }
   
   // 0b. Deterministic pending validation (before FTMO / locks for accept path) — terminal reject once
   string mt5_sym = NormalizeSymbol(symbol);
   if(entry_kind == FXG_ENTRY_UNSUPPORTED)
   {
      WriteSignalLockFile(signal_id);
      gl_last_processed_signal_id = signal_id;
      gl_metrics_terminal_rejects++;
      gl_last_result_code = "reject_unsupported_entry_kind";
      string msg = StringFormat("FXG_BRIDGE reject reason=unsupported_entry_kind entry_type=%s side=%s", entry_type, side);
      LogEvent("BRIDGE_REJECT", signal_id, msg);
      Print("FXG_BRIDGE reject ", signal_id, " ", msg);
      return;
   }
   
   bool needs_pending_price = (entry_kind != FXG_ENTRY_MARKET);
   if(needs_pending_price)
   {
      if(limit_pr <= 0)
      {
         WriteSignalLockFile(signal_id);
         gl_last_processed_signal_id = signal_id;
         gl_metrics_terminal_rejects++;
         gl_last_result_code = "reject_missing_limit_price";
         string msg = "FXG_BRIDGE reject reason=missing_limit_price (need limit_price|price|entry)";
         LogEvent("BRIDGE_REJECT", signal_id, msg);
         Print("FXG_BRIDGE reject ", signal_id, " ", msg);
         return;
      }
      if(!SymbolSelect(mt5_sym, true))
      {
         WriteSignalLockFile(signal_id);
         gl_last_processed_signal_id = signal_id;
         gl_metrics_terminal_rejects++;
         gl_last_result_code = "reject_symbol_not_found";
         string msg = StringFormat("FXG_BRIDGE reject reason=symbol_not_found sym=%s", mt5_sym);
         LogEvent("BRIDGE_REJECT", signal_id, msg);
         Print("FXG_BRIDGE reject ", signal_id, " ", msg);
         return;
      }
      double tick_sz = SymbolInfoDouble(mt5_sym, SYMBOL_TRADE_TICK_SIZE);
      if(tick_sz > 0 && limit_pr > 0)
         limit_pr = MathRound(limit_pr / tick_sz) * tick_sz;
      string vreason = "";
      if(!ValidatePendingEntryVsMarket(mt5_sym, entry_kind, limit_pr, vreason))
      {
         WriteSignalLockFile(signal_id);
         gl_last_processed_signal_id = signal_id;
         gl_metrics_terminal_rejects++;
         gl_last_result_code = "reject_invalid_pending_vs_market";
         double bid = SymbolInfoDouble(mt5_sym, SYMBOL_BID);
         double ask = SymbolInfoDouble(mt5_sym, SYMBOL_ASK);
         string msg = StringFormat("FXG_BRIDGE reject reason=%s kind=%d entry=%.5f bid=%.5f ask=%.5f", vreason, (int)entry_kind, limit_pr, bid, ask);
         LogEvent("BRIDGE_REJECT", signal_id, msg);
         Print("FXG_BRIDGE reject ", signal_id, " ", msg);
         return;
      }
      gl_metrics_validation_ok++;
   }
   
   // 1. FTMO Validation (Dry Run)
   bool ftmo_pass = ValidateFTMORules(mt5_sym);
   
   string decision = "REJECTED";
   string reason = "";
   
   if (!ftmo_pass)
   {
      reason = "FTMO Rules Violation";
   }
   else if (news == "embargo")
   {
      reason = "News Embargo";
   }
   else if (!execution_allowed)
   {
      reason = "Source Blocked Execution";
   }
   else
   {
      decision = "ACCEPTED";
      if(!InpEnableExecution)
      {
         decision = "ACCEPTED_DRY_RUN";
         reason = "Execution Disabled in EA";
      }
   }
   
   // 2. Create lock file (claim this signal_id; path relative to MQL5/Files)
   WriteSignalLockFile(signal_id);
   
   // 3. Log Decision (to InpLogFilePath)
   LogEvent("SIGNAL", signal_id, StringFormat("Sym:%s Side:%s Dec:%s Reason:%s", symbol, side, decision, reason));
   
   // Update last processed ID
   gl_last_processed_signal_id = signal_id;
   
   // 4. Execution (If Enabled)
   if (decision == "ACCEPTED" && InpEnableExecution)
   {
       gl_latest_signal_id_attempted = signal_id;
       bool ok = ExecuteTrade(signal_id, symbol, side, lots_sig, sl_sig, tp_sig, entry_type, limit_pr, comment_payload, entry_kind);
       if(ok)
       {
          gl_latest_signal_id_executed_ok = signal_id;
          gl_last_result_code = "exec_ok";
       }
       else
       {
          gl_latest_signal_id_failed = signal_id;
          if(StringLen(gl_last_result_code) < 1)
             gl_last_result_code = "exec_fail";
       }
   }
}

// Normalize symbol: EUR_USD -> EURUSD, XAU_USD -> XAUUSD
string NormalizeSymbol(string sym)
{
   string out = "";
   for(int i = 0; i < StringLen(sym); i++)
   {
      ushort c = StringGetCharacter(sym, i);
      if(c != '_') out += CharToString((uchar)c);
   }
   return (out != "") ? out : sym;
}

bool ExecuteTrade(string signal_id, string symbol, string side, double lots_in, double sl_in, double tp_in, string entry_type_in, double limit_price_in, string comment_from_payload, ENUM_FXG_ENTRY_KIND entry_kind)
{
   string side_u = FxgStringUpper(side);
   string mt5_symbol = NormalizeSymbol(symbol);
   if(!SymbolSelect(mt5_symbol, true))
   {
      Print("FTMO_Bridge: Symbol not found ", mt5_symbol, " (original ", symbol, ")");
      LogEvent("EXEC_FAIL", signal_id, StringFormat("Symbol not found:%s", mt5_symbol));
      gl_last_result_code = "exec_fail_symbol_not_found";
      return false;
   }
   
   double lots = (lots_in > 0) ? lots_in : InpLotSize;
   double step = SymbolInfoDouble(mt5_symbol, SYMBOL_VOLUME_STEP);
   if(step > 0) lots = MathRound(lots / step) * step;
   double max_vol = SymbolInfoDouble(mt5_symbol, SYMBOL_VOLUME_MAX);
   if(max_vol > 0 && lots > max_vol) lots = max_vol;
   double sl = (sl_in != 0) ? sl_in : 0;
   double tp = (tp_in != 0) ? tp_in : 0;
   double tick_size = SymbolInfoDouble(mt5_symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tick_size > 0) {
      if(limit_price_in > 0) limit_price_in = MathRound(limit_price_in / tick_size) * tick_size;
      if(sl > 0) sl = MathRound(sl / tick_size) * tick_size;
      if(tp > 0) tp = MathRound(tp / tick_size) * tick_size;
   }
   
   double price = 0;
   if(entry_kind != FXG_ENTRY_MARKET && limit_price_in > 0)
      price = limit_price_in;
   else
   {
      if(StringFind(side_u, "BUY") >= 0)
         price = SymbolInfoDouble(mt5_symbol, SYMBOL_ASK);
      else
         price = SymbolInfoDouble(mt5_symbol, SYMBOL_BID);
   }
   
   if(price <= 0)
   {
      Print("FTMO_Bridge: Invalid price for ", mt5_symbol);
      LogEvent("EXEC_FAIL", signal_id, "Invalid price");
      gl_last_result_code = "exec_fail_invalid_price";
      return false;
   }
   
   bool ok = false;
   string comment = comment_from_payload;
   if(StringLen(comment) < 1)
      comment = StringSubstr(signal_id, 0, 31);
   else
      comment = StringSubstr(comment, 0, 31);
   LogEvent("MT5_COMMENT", signal_id, StringFormat("comment_prefix:%s payload_nonempty:%s", comment, (StringLen(comment_from_payload) > 0 ? "true" : "false")));
   
   if(StringFind(side_u, "BUY") >= 0)
   {
      if(entry_kind == FXG_ENTRY_BUY_LIMIT && limit_price_in > 0)
         ok = gl_trade.BuyLimit(lots, limit_price_in, mt5_symbol, sl, tp, ORDER_TIME_GTC, 0, comment);
      else if(entry_kind == FXG_ENTRY_BUY_STOP && limit_price_in > 0)
         ok = gl_trade.BuyStop(lots, limit_price_in, mt5_symbol, sl, tp, ORDER_TIME_GTC, 0, comment);
      else
         ok = gl_trade.Buy(lots, mt5_symbol, price, sl, tp, comment);
   }
   else
   {
      if(entry_kind == FXG_ENTRY_SELL_LIMIT && limit_price_in > 0)
         ok = gl_trade.SellLimit(lots, limit_price_in, mt5_symbol, sl, tp, ORDER_TIME_GTC, 0, comment);
      else if(entry_kind == FXG_ENTRY_SELL_STOP && limit_price_in > 0)
         ok = gl_trade.SellStop(lots, limit_price_in, mt5_symbol, sl, tp, ORDER_TIME_GTC, 0, comment);
      else
         ok = gl_trade.Sell(lots, mt5_symbol, price, sl, tp, comment);
   }
   
   if(ok)
   {
      LogEvent("EXEC_OK", signal_id, StringFormat("Sym:%s Side:%s Lots:%.2f", mt5_symbol, side, lots));
      Print("FTMO_Bridge: Order placed ", signal_id, " ", mt5_symbol, " ", side);
   }
   else
   {
      uint err = GetLastError();
      LogEvent("EXEC_FAIL", signal_id, StringFormat("OrderSend err:%u", err));
      Print("FTMO_Bridge: Order failed ", signal_id, " err=", err);
      gl_last_result_code = StringFormat("exec_fail_err_%u", err);
   }
   return ok;
}

bool ValidateFTMORules(string symbol)
{
   double current_equity = AccountInfoDouble(ACCOUNT_EQUITY);
   
   // 1. Daily Drawdown
   double daily_loss = gl_start_of_day_equity - current_equity;
   if(daily_loss > InpMaxDailyLoss)
   {
      Print("FTMO Fail: Daily Loss Limit Exceeded");
      return false;
   }
   
   // 2. Max Total Loss
   if((AccountInfoDouble(ACCOUNT_BALANCE) - current_equity) > InpMaxTotalLoss)
   {
       Print("FTMO Fail: Max Total Loss Exceeded");
       return false;
   }
   
   // 3. Symbol Market Hours (skip if symbol empty e.g. test signal)
   if(StringLen(symbol) > 0 && SymbolInfoInteger(symbol, SYMBOL_TRADE_MODE) != SYMBOL_TRADE_MODE_FULL)
   {
       Print("FTMO Fail: Symbol not tradeable");
       return false;
   }
   
   return true;
}

//+------------------------------------------------------------------+
//| Logging                                                          |
//+------------------------------------------------------------------+
void LogEvent(string type, string id, string message)
{
   string time_str = TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS);
   string log_line = StringFormat("{\"ts\": \"%s\", \"type\": \"%s\", \"id\": \"%s\", \"signal_id\": \"%s\", \"msg\": \"%s\"}", 
                                  time_str, type, id, id, message);
   
   int file_handle = FileOpen(InpLogFilePath, FILE_READ|FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_SHARE_READ|FILE_SHARE_WRITE);
   if(file_handle == INVALID_HANDLE)
   {
      // Try create if file doesn't exist (e.g. symlink target missing)
      file_handle = FileOpen(InpLogFilePath, FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_SHARE_READ|FILE_SHARE_WRITE);
      if(file_handle != INVALID_HANDLE)
      {
         FileClose(file_handle);
         file_handle = FileOpen(InpLogFilePath, FILE_READ|FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_SHARE_READ|FILE_SHARE_WRITE);
      }
   }
   if(file_handle != INVALID_HANDLE)
   {
      FileSeek(file_handle, 0, SEEK_END);
      FileWriteString(file_handle, log_line + "\n");
      FileClose(file_handle);
   }
   else
   {
      Print("FTMO_Bridge: LogEvent FAILED path=", InpLogFilePath, " err=", GetLastError());
   }
   
   Print(type, ": ", id, " - ", message);
}
