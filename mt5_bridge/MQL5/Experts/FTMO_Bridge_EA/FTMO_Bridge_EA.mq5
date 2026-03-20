//+------------------------------------------------------------------+
//|                                               FTMO_Bridge_EA.mq5 |
//|                                    Copyright 2026, AI Quant Team |
//|                                          https://www.example.com |
//+------------------------------------------------------------------+
#property copyright "Copyright 2026, AI Quant Team"
#property link      "https://www.example.com"
#property version   "1.03"
#property strict

// Enable WebRequest for the specific URL in MT5 Options if using WEB source!
#include "SimpleJson.mqh"
#include <Trade\Trade.mqh>

enum ENUM_SIGNAL_SOURCE
{
   SOURCE_WEB,
   SOURCE_FILE
};

//+------------------------------------------------------------------+
//| Inputs                                                           |
//+------------------------------------------------------------------+
input ENUM_SIGNAL_SOURCE InpSignalSource = SOURCE_FILE;             // Signal Source
input string   InpApiUrl         = "http://127.0.0.1:28787/api/signals"; // ALPHA API URL (if WEB)
input string   InpSignalFilePath = "signals.jsonl";                 // Signal File Path (if FILE, relative to MQL5/Files)
input string   InpLogFilePath    = "ftmo_bridge_log.jsonl";        // Bridge Log File (relative to MQL5/Files)
input string   InpDedupeDir      = "fxg_dedupe";                    // Dedupe Dir for one-trade-per-signal lock files
input string   InpBridgeAccount  = "ftmo_eval_primary";                  // Bridge Account ID (Must match ALPHA)
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
double   gl_start_of_day_equity = 0.0;
datetime gl_last_day_check = 0;
ulong    gl_last_file_position = 0; // To track file reading position (FileTell returns ulong)

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
   
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   EventKillTimer();
   LogEvent("EA_STOP", "Deinitialized", EnumToString((ENUM_INIT_RETCODE)reason));
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
   
   // Visibility instrumentation: one log entry per read cycle
   LogEvent("CYCLE", "", StringFormat("file:%s last_id:%s new_lines:%s", InpSignalFilePath, gl_last_processed_signal_id, IntegerToString(new_lines_processed)));
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
   
   // One-trade-per-signal guard: if lock exists, skip (already processed)
   string lock_path = InpDedupeDir + "/" + signal_id + ".lock";
   if (FileIsExist(lock_path))
      return;
   
   // Deduplication check (in-memory)
   if (signal_id == gl_last_processed_signal_id) return;
   
   // NOTE: With file reading line-by-line, we might not need this if we track file position perfectly.
   // But it's good safety.
   
   string bridge_acc = CSimpleJson::ExtractString(json_signal, "bridge_account");
   string symbol    = CSimpleJson::ExtractString(json_signal, "symbol");
   string side      = CSimpleJson::ExtractString(json_signal, "side");
   string strategy  = CSimpleJson::ExtractString(json_signal, "strategy");
   string news      = CSimpleJson::ExtractString(json_signal, "news_state");
   bool   execution_allowed = CSimpleJson::ExtractBool(json_signal, "execution_allowed");
   double lots_sig = CSimpleJson::ExtractDouble(json_signal, "lots");
   double sl_sig   = CSimpleJson::ExtractDouble(json_signal, "stop_loss");
   double tp_sig   = CSimpleJson::ExtractDouble(json_signal, "take_profit");
   string entry_type = CSimpleJson::ExtractString(json_signal, "entry_type");
   double limit_pr  = CSimpleJson::ExtractDouble(json_signal, "limit_price");
   
   // 0. Account Routing Check
   if (bridge_acc != "" && bridge_acc != InpBridgeAccount)
   {
      // LogEvent("SIGNAL_SKIPPED", signal_id, StringFormat("Bridge Account Mismatch. Signal:%s EA:%s", bridge_acc, InpBridgeAccount));
      return; 
   }
   
   // 1. FTMO Validation (Dry Run)
   string mt5_sym = NormalizeSymbol(symbol);
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
   int lock_handle = FileOpen(lock_path, FILE_WRITE|FILE_TXT|FILE_ANSI);
   if (lock_handle != INVALID_HANDLE)
   {
      FileWriteString(lock_handle, signal_id);
      FileClose(lock_handle);
   }
   
   // 3. Log Decision (to InpLogFilePath)
   LogEvent("SIGNAL", signal_id, StringFormat("Sym:%s Side:%s Dec:%s Reason:%s", symbol, side, decision, reason));
   
   // Update last processed ID
   gl_last_processed_signal_id = signal_id;
   
   // 4. Execution (If Enabled)
   if (decision == "ACCEPTED" && InpEnableExecution)
   {
       ExecuteTrade(signal_id, symbol, side, lots_sig, sl_sig, tp_sig, entry_type, limit_pr);
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

bool ExecuteTrade(string signal_id, string symbol, string side, double lots_in, double sl_in, double tp_in, string entry_type_in, double limit_price_in)
{
   string mt5_symbol = NormalizeSymbol(symbol);
   if(!SymbolSelect(mt5_symbol, true))
   {
      Print("FTMO_Bridge: Symbol not found ", mt5_symbol, " (original ", symbol, ")");
      LogEvent("EXEC_FAIL", signal_id, StringFormat("Symbol not found:%s", mt5_symbol));
      return false;
   }
   
   double lots = (lots_in > 0) ? lots_in : InpLotSize;
   double step = SymbolInfoDouble(mt5_symbol, SYMBOL_VOLUME_STEP);
   if(step > 0) lots = MathRound(lots / step) * step;
   double max_vol = SymbolInfoDouble(mt5_symbol, SYMBOL_VOLUME_MAX);
   if(max_vol > 0 && lots > max_vol) lots = max_vol;
   double sl = (sl_in != 0) ? sl_in : 0;
   double tick_size = SymbolInfoDouble(mt5_symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tick_size > 0) {
      if(limit_price_in > 0) limit_price_in = MathRound(limit_price_in / tick_size) * tick_size;
      if(sl > 0) sl = MathRound(sl / tick_size) * tick_size;
      if(tp > 0) tp = MathRound(tp / tick_size) * tick_size;
   }
   string entry_type = (StringLen(entry_type_in) > 0) ? entry_type_in : "MARKET";
   
   double price = 0;
   if(StringFind(entry_type, "LIMIT") >= 0 && limit_price_in > 0)
      price = limit_price_in;
   else
   {
      if(StringFind(side, "BUY") >= 0)
         price = SymbolInfoDouble(mt5_symbol, SYMBOL_ASK);
      else
         price = SymbolInfoDouble(mt5_symbol, SYMBOL_BID);
   }
   
   if(price <= 0)
   {
      Print("FTMO_Bridge: Invalid price for ", mt5_symbol);
      LogEvent("EXEC_FAIL", signal_id, "Invalid price");
      return false;
   }
   
   bool ok = false;
   string comment = StringSubstr(signal_id, 0, 31);
   
   if(StringFind(side, "BUY") >= 0)
   {
      if(StringFind(entry_type, "LIMIT") >= 0 && limit_price_in > 0)
         ok = gl_trade.BuyLimit(lots, limit_price_in, mt5_symbol, sl, tp, ORDER_TIME_GTC, 0, comment);
      else
         ok = gl_trade.Buy(lots, mt5_symbol, price, sl, tp, comment);
   }
   else
   {
      if(StringFind(entry_type, "LIMIT") >= 0 && limit_price_in > 0)
         ok = gl_trade.SellLimit(lots, limit_price_in, mt5_symbol, sl, tp, ORDER_TIME_GTC, 0, comment);
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
