//+------------------------------------------------------------------+
//| FTMO_Bridge_EA.mq5                                                |
//| Canonical execution consumer - reads signals_ftmo_demo2.jsonl     |
//| bridge_account must match InpBridgeAccount. Paper/live per broker.|
//+------------------------------------------------------------------+
#property copyright "FXG Canonical Bridge"
#property version   "1.04"
#property strict

#include <Trade\Trade.mqh>
#include <Trade\SymbolInfo.mqh>

input string InpSignalFilePath = "signals_ftmo_demo2.jsonl";
input string InpBridgeAccount  = "ftmo_demo2";
input string InpBridgeLogFile  = "ftmo_demo2_bridge_log.jsonl";
// Legacy input: unused for signal volume since v1.04 (volume comes from JSON "lots" / "volume"); retained for saved-set compatibility.
input double InpMaxLotSize     = 0.01;
input int    InpPollMs         = 1000;
input bool   InpPaperOnly      = true;

CTrade         g_trade;
ulong          g_lastFilePos = 0;
ulong          g_lastCheckTime = 0;
string         g_seenSignalIds[];

enum JsonNumKind
  {
   JSON_NUM_ABSENT = 0,
   JSON_NUM_NULL   = 1,
   JSON_NUM_VALUE  = 2
};

//+------------------------------------------------------------------+
string EscapeJson(string s)
{
   string out = "";
   for(int i = 0; i < StringLen(s); i++)
     {
      ushort c = StringGetCharacter(s, i);
      if(c == '"')
         out += "\\\"";
      else if(c == '\\')
         out += "\\\\";
      else
         out += CharToString((uchar)c);
     }
   return out;
}

//+------------------------------------------------------------------+
void LogBridge(string type, string msg, string signalId = "")
{
   string line = StringFormat("{\"type\":\"%s\",\"msg\":\"%s\",\"signal_id\":\"%s\",\"ts\":\"%s\"}\n",
                              type, EscapeJson(msg), signalId, TimeToString(TimeCurrent(), TIME_DATE | TIME_SECONDS));
   int h = FileOpen(InpBridgeLogFile, FILE_READ | FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_SHARE_READ);
   if(h != INVALID_HANDLE)
     {
      FileSeek(h, 0, SEEK_END);
      FileWriteString(h, line);
      FileClose(h);
     }
}

//+------------------------------------------------------------------+
void SkipWs(const string &json, int &pos)
{
   while(pos < StringLen(json))
     {
      ushort c = StringGetCharacter(json, pos);
      if(c == ' ' || c == '\t' || c == '\r' || c == '\n')
        {
         pos++;
         continue;
        }
      break;
     }
}

//+------------------------------------------------------------------+
string ExtractJsonString(const string &json, const string &key)
{
   string search = "\"" + key + "\"";
   int pos = StringFind(json, search);
   if(pos < 0)
      return "";
   pos = StringFind(json, ":", pos);
   if(pos < 0)
      return "";
   pos++;
   SkipWs(json, pos);
   int start = StringFind(json, "\"", pos);
   if(start < 0)
      return "";
   start++;
   int end = StringFind(json, "\"", start);
   if(end < 0)
      return "";
   return StringSubstr(json, start, end - start);
}

//+------------------------------------------------------------------+
JsonNumKind ExtractJsonNumberKind(const string &json, const string &key, double &outVal)
{
   outVal = 0;
   string search = "\"" + key + "\"";
   int pos = StringFind(json, search);
   if(pos < 0)
      return JSON_NUM_ABSENT;
   pos = StringFind(json, ":", pos);
   if(pos < 0)
      return JSON_NUM_ABSENT;
   pos++;
   SkipWs(json, pos);
   if(pos < StringLen(json) && StringFind(json, "null", pos) == pos)
      return JSON_NUM_NULL;
   string num = "";
   for(int i = pos; i < StringLen(json); i++)
     {
      ushort c = StringGetCharacter(json, i);
      if(c == '-' || c == '.' || (c >= '0' && c <= '9'))
         num += CharToString((uchar)c);
      else if(StringLen(num) > 0)
         break;
     }
   if(StringLen(num) == 0)
      return JSON_NUM_NULL;
   outVal = StringToDouble(num);
   return JSON_NUM_VALUE;
}

//+------------------------------------------------------------------+
bool ExtractJsonBool(const string &json, const string &key)
{
   string search = "\"" + key + "\"";
   int pos = StringFind(json, search);
   if(pos < 0)
      return false;
   pos = StringFind(json, ":", pos);
   if(pos < 0)
      return false;
   return (StringFind(json, "true", pos) >= 0);
}

//+------------------------------------------------------------------+
string NormalizeSymbol(string sym)
{
   StringReplace(sym, "_", "");
   return sym;
}

//+------------------------------------------------------------------+
bool IsAlreadySeenSignalId(const string id)
{
   if(StringLen(id) == 0)
      return false;
   int n = ArraySize(g_seenSignalIds);
   for(int i = 0; i < n; i++)
     {
      if(g_seenSignalIds[i] == id)
         return true;
     }
   return false;
}

//+------------------------------------------------------------------+
void RememberSignalId(const string id)
{
   if(StringLen(id) == 0)
      return;
   int n = ArraySize(g_seenSignalIds);
   ArrayResize(g_seenSignalIds, n + 1);
   g_seenSignalIds[n] = id;
}

//+------------------------------------------------------------------+
bool ValidateStopsForMarket(const string symbol, const string side, const double bid, const double ask,
                            const bool useSl, const double sl, const bool useTp, const double tp,
                            string &failReason)
{
   failReason = "";
   double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
   if(point <= 0)
     {
      failReason = "SYMBOL_POINT_invalid";
      return false;
     }
   int stopsLevel = (int)SymbolInfoInteger(symbol, SYMBOL_TRADE_STOPS_LEVEL);
   double minDist = stopsLevel * point;

   if(useSl && sl <= 0)
     {
      failReason = "EA_PARSE_FAIL: stop_loss must be > 0 when provided";
      return false;
     }
   if(useTp && tp <= 0)
     {
      failReason = "EA_PARSE_FAIL: take_profit must be > 0 when provided";
      return false;
     }

   if(side == "BUY")
     {
      if(useSl)
        {
         if(sl >= bid)
           {
            failReason = "EA_PARSE_FAIL: BUY stop_loss must be below bid";
            return false;
           }
         if(stopsLevel > 0 && (bid - sl) < minDist - 1e-10)
           {
            failReason = StringFormat("EA_PARSE_FAIL: BUY SL too close (min %d points)", stopsLevel);
            return false;
           }
        }
      if(useTp)
        {
         if(tp <= ask)
           {
            failReason = "EA_PARSE_FAIL: BUY take_profit must be above ask";
            return false;
           }
         if(stopsLevel > 0 && (tp - ask) < minDist - 1e-10)
           {
            failReason = StringFormat("EA_PARSE_FAIL: BUY TP too close (min %d points)", stopsLevel);
            return false;
           }
        }
     }
   else
     {
      if(useSl)
        {
         if(sl <= ask)
           {
            failReason = "EA_PARSE_FAIL: SELL stop_loss must be above ask";
            return false;
           }
         if(stopsLevel > 0 && (sl - ask) < minDist - 1e-10)
           {
            failReason = StringFormat("EA_PARSE_FAIL: SELL SL too close (min %d points)", stopsLevel);
            return false;
           }
        }
      if(useTp)
        {
         if(tp >= bid)
           {
            failReason = "EA_PARSE_FAIL: SELL take_profit must be below bid";
            return false;
           }
         if(stopsLevel > 0 && (bid - tp) < minDist - 1e-10)
           {
            failReason = StringFormat("EA_PARSE_FAIL: SELL TP too close (min %d points)", stopsLevel);
            return false;
           }
        }
     }
   return true;
}

//+------------------------------------------------------------------+
bool ValidateStopsForPending(const string symbol, const string side, const double orderPrice,
                            const double bid, const double ask,
                            const bool useSl, const double sl, const bool useTp, const double tp,
                            string &failReason)
{
   failReason = "";
   double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
   if(point <= 0)
     {
      failReason = "SYMBOL_POINT_invalid";
      return false;
     }
   int stopsLevel = (int)SymbolInfoInteger(symbol, SYMBOL_TRADE_STOPS_LEVEL);
   double minDist = stopsLevel * point;

   if(useSl && sl <= 0)
     {
      failReason = "EA_PARSE_FAIL: stop_loss must be > 0 when provided";
      return false;
     }
   if(useTp && tp <= 0)
     {
      failReason = "EA_PARSE_FAIL: take_profit must be > 0 when provided";
      return false;
     }

   if(side == "BUY")
     {
      if(orderPrice >= ask)
        {
         failReason = "EA_PARSE_FAIL: BUY LIMIT entry_price must be strictly below Ask";
         return false;
        }
      if(useSl)
        {
         if(sl >= orderPrice)
           {
            failReason = "EA_PARSE_FAIL: BUY LIMIT stop_loss must be below entry_price";
            return false;
           }
         if(stopsLevel > 0 && (orderPrice - sl) < minDist - 1e-10)
           {
            failReason = StringFormat("EA_PARSE_FAIL: BUY LIMIT SL too close to entry (min %d points)", stopsLevel);
            return false;
           }
        }
      if(useTp)
        {
         if(tp <= orderPrice)
           {
            failReason = "EA_PARSE_FAIL: BUY LIMIT take_profit must be above entry_price";
            return false;
           }
         if(stopsLevel > 0 && (tp - orderPrice) < minDist - 1e-10)
           {
            failReason = StringFormat("EA_PARSE_FAIL: BUY LIMIT TP too close to entry (min %d points)", stopsLevel);
            return false;
           }
        }
     }
   else
     {
      if(orderPrice <= ask)
        {
         failReason = "EA_PARSE_FAIL: SELL LIMIT entry_price must be strictly above Ask";
         return false;
        }
      if(useSl)
        {
         if(sl <= orderPrice)
           {
            failReason = "EA_PARSE_FAIL: SELL LIMIT stop_loss must be above entry_price";
            return false;
           }
         if(stopsLevel > 0 && (sl - orderPrice) < minDist - 1e-10)
           {
            failReason = StringFormat("EA_PARSE_FAIL: SELL LIMIT SL too close to entry (min %d points)", stopsLevel);
            return false;
           }
        }
      if(useTp)
        {
         if(tp >= orderPrice)
           {
            failReason = "EA_PARSE_FAIL: SELL LIMIT take_profit must be below entry_price";
            return false;
           }
         if(stopsLevel > 0 && (orderPrice - tp) < minDist - 1e-10)
           {
            failReason = StringFormat("EA_PARSE_FAIL: SELL LIMIT TP too close to entry (min %d points)", stopsLevel);
            return false;
           }
        }
     }
   return true;
}

//+------------------------------------------------------------------+
//+------------------------------------------------------------------+
//| Round signal lots to broker volume step; enforce min/max.         |
//+------------------------------------------------------------------+
bool NormalizeVolumeForSymbol(const string symbol, const double rawLots, double &outVol, string &failReason)
{
   failReason = "";
   double vmin = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
   double vmax = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MAX);
   double vstep = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);
   if(vmin <= 0.0 || vmax <= 0.0 || vstep <= 0.0)
     {
      failReason = "broker_volume_meta_invalid";
      return false;
     }
   if(rawLots < vmin - 1e-12)
     {
      failReason = StringFormat("lots_below_broker_min min=%.10g want=%.10g", vmin, rawLots);
      return false;
     }
   if(rawLots > vmax + 1e-12)
     {
      failReason = StringFormat("lots_above_broker_max max=%.10g want=%.10g", vmax, rawLots);
      return false;
     }
   double n = MathRound(rawLots / vstep);
   outVol = NormalizeDouble(n * vstep, 8);
   if(outVol < vmin - 1e-12)
     {
      failReason = StringFormat("rounded_volume_below_min min=%.10g rounded=%.10g", vmin, outVol);
      return false;
     }
   if(outVol > vmax + 1e-12)
     {
      failReason = StringFormat("rounded_volume_above_max max=%.10g rounded=%.10g", vmax, outVol);
      return false;
     }
   return true;
}

//+------------------------------------------------------------------+
void ApplySymbolFillingMode(const string symbol)
{
   uint fm = (uint)SymbolInfoInteger(symbol, SYMBOL_FILLING_MODE);
   if((fm & SYMBOL_FILLING_IOC) != 0)
      g_trade.SetTypeFilling(ORDER_FILLING_IOC);
   else if((fm & SYMBOL_FILLING_FOK) != 0)
      g_trade.SetTypeFilling(ORDER_FILLING_FOK);
   else
      g_trade.SetTypeFilling(ORDER_FILLING_RETURN);
}

//+------------------------------------------------------------------+
//| Pending expiration policy: GTC+0 when allowed; else explicit     |
//| ORDER_TIME_SPECIFIED (30d or session EOD when DAY-only symbol).   |
//+------------------------------------------------------------------+
void ResolveLimitOrderTimePolicy(const string symbol, ENUM_ORDER_TYPE_TIME &typeTime, datetime &expiration)
{
   typeTime = ORDER_TIME_GTC;
   expiration = 0;
   long mode = 0;
   if(!SymbolInfoInteger(symbol, SYMBOL_EXPIRATION_MODE, mode))
      mode = 0;
   datetime srv = TimeTradeServer();
   if((mode & SYMBOL_EXPIRATION_GTC) != 0)
     {
      typeTime = ORDER_TIME_GTC;
      expiration = 0;
      return;
     }
   if((mode & SYMBOL_EXPIRATION_SPECIFIED) != 0)
     {
      typeTime = ORDER_TIME_SPECIFIED;
      expiration = srv + (datetime)(86400 * 30);
      return;
     }
   if((mode & SYMBOL_EXPIRATION_DAY) != 0)
     {
      typeTime = ORDER_TIME_SPECIFIED;
      MqlDateTime z;
      TimeToStruct(srv, z);
      z.hour = 23;
      z.min = 55;
      z.sec = 0;
      expiration = StructToTime(z);
      if(expiration <= srv + 60)
         expiration = srv + (datetime)(86400 * 30);
      return;
     }
   typeTime = ORDER_TIME_SPECIFIED;
   expiration = srv + (datetime)(86400 * 30);
}

//+------------------------------------------------------------------+
//| Zeroed pending LIMIT/stop request — avoids CTrade arg/order bugs. |
//+------------------------------------------------------------------+
string FormatTradeResultLine(const MqlTradeResult &r)
{
   if(StringLen(r.comment) > 0)
      return r.comment;
   return StringFormat("retcode=%u", (uint)r.retcode);
}

bool SendPendingLimitRaw(const string symbol, const ENUM_ORDER_TYPE orderType, const double volume,
                         const double price, const double sl, const double tp,
                         const ENUM_ORDER_TYPE_TIME typeTime, const datetime expiration,
                         MqlTradeResult &result)
{
   MqlTradeRequest req;
   ZeroMemory(req);
   ZeroMemory(result);

   req.action       = TRADE_ACTION_PENDING;
   req.symbol       = symbol;
   req.magic        = (ulong)(1512827972 % 10000);
   req.volume       = volume;
   req.type         = orderType;
   req.price        = price;
   req.sl           = sl;
   req.tp           = tp;
   req.deviation    = 0;
   req.type_time    = typeTime;
   req.expiration   = expiration;
   req.type_filling = ORDER_FILLING_RETURN;

   return OrderSend(req, result);
}

//+------------------------------------------------------------------+
void SeedFilePositionToEnd()
{
   int h = FileOpen(InpSignalFilePath, FILE_READ | FILE_TXT | FILE_ANSI | FILE_SHARE_READ);
   if(h == INVALID_HANDLE)
     {
      LogBridge("FILE_READ", StringFormat("signal file not readable yet: %s", InpSignalFilePath), "");
      return;
     }
   FileSeek(h, 0, SEEK_END);
   g_lastFilePos = FileTell(h);
   FileClose(h);
   LogBridge("FILE_READ", "tail mode: file_pos=" + IntegerToString((long)g_lastFilePos), "");
}

//+------------------------------------------------------------------+
int OnInit()
{
   g_trade.SetExpertMagicNumber(1512827972 % 10000);
   g_trade.SetDeviationInPoints(10);
   g_trade.SetTypeFilling(ORDER_FILLING_IOC);
   ArrayResize(g_seenSignalIds, 0);
   SeedFilePositionToEnd();
   LogBridge("EA_START", "FTMO_Bridge_EA v1.04 signal volume from JSON lots+volume_alias; no silent 0.01 cap; watch=MQL5/Files/" + InpSignalFilePath + " log=" + InpBridgeLogFile, "");
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   LogBridge("EA_STOP", "FTMO_Bridge_EA stopped", "");
}

//+------------------------------------------------------------------+
void OnTick()
{
   if(GetTickCount64() - g_lastCheckTime < (ulong)InpPollMs)
      return;
   g_lastCheckTime = GetTickCount64();

   int h = FileOpen(InpSignalFilePath, FILE_READ | FILE_TXT | FILE_ANSI | FILE_SHARE_READ);
   if(h == INVALID_HANDLE)
      return;

   FileSeek(h, (long)g_lastFilePos, SEEK_SET);
   while(!FileIsEnding(h))
     {
      string line = FileReadString(h);
      if(StringLen(line) < 10)
         continue;

      string signalIdEarly = ExtractJsonString(line, "signal_id");

      string bridgeAccount = ExtractJsonString(line, "bridge_account");
      if(bridgeAccount != InpBridgeAccount)
        {
         LogBridge("SIGNAL_SKIP", StringFormat("bridge_account mismatch got=%s want=%s", bridgeAccount, InpBridgeAccount), signalIdEarly);
         continue;
        }

      bool execAllowed = ExtractJsonBool(line, "execution_allowed");
      if(!execAllowed)
        {
         LogBridge("SIGNAL_SKIP", "execution_allowed is false", signalIdEarly);
         continue;
        }

      string entryType = ExtractJsonString(line, "entry_type");
      if(entryType != "MARKET" && entryType != "LIMIT")
        {
         LogBridge("SIGNAL_SKIP", StringFormat("entry_type not MARKET or LIMIT: %s", entryType), signalIdEarly);
         continue;
        }

      string signalId = signalIdEarly;
      if(StringLen(signalId) == 0)
         signalId = IntegerToString((long)GetTickCount64());

      if(IsAlreadySeenSignalId(signalId))
        {
         LogBridge("DUPLICATE_SKIP", "same signal_id already processed this session", signalId);
         continue;
        }

      string symbolRaw = ExtractJsonString(line, "symbol");
      string symbol = NormalizeSymbol(symbolRaw);
      string side = ExtractJsonString(line, "side");

      double unitsD = 0;
      JsonNumKind uk = ExtractJsonNumberKind(line, "units", unitsD);
      int units = (int)unitsD;
      if(uk != JSON_NUM_VALUE || units == 0)
        {
         LogBridge("EA_PARSE_FAIL", "units missing, null, or zero", signalId);
         continue;
        }

      double slRaw = 0;
      double tpRaw = 0;
      JsonNumKind slKind = ExtractJsonNumberKind(line, "stop_loss", slRaw);
      JsonNumKind tpKind = ExtractJsonNumberKind(line, "take_profit", tpRaw);

      bool useSl = (slKind == JSON_NUM_VALUE && slRaw > 0);
      bool useTp = ( tpKind == JSON_NUM_VALUE && tpRaw > 0);

      if(StringLen(symbol) == 0 || (side != "BUY" && side != "SELL") || units == 0)
        {
         LogBridge("EA_PARSE_FAIL", "missing symbol/side/units", signalId);
         continue;
        }

      if(!SymbolSelect(symbol, true))
        {
         LogBridge("EA_PARSE_FAIL", StringFormat("SymbolSelect failed for %s", symbol), signalId);
         continue;
        }

      double lotsRaw = 0.0;
      JsonNumKind lk = ExtractJsonNumberKind(line, "lots", lotsRaw);
      string lotsFieldUsed = "lots";
      if(lk != JSON_NUM_VALUE)
        {
         lk = ExtractJsonNumberKind(line, "volume", lotsRaw);
         lotsFieldUsed = "volume";
        }
      if(lk == JSON_NUM_ABSENT)
        {
         LogBridge("LOT_PARSE_REJECT", "lots_field_absent (no numeric lots or volume)", signalId);
         continue;
        }
      if(lk == JSON_NUM_NULL)
        {
         LogBridge("LOT_PARSE_REJECT", StringFormat("%s_is_null", lotsFieldUsed), signalId);
         continue;
        }
      if(lotsRaw != lotsRaw || lotsRaw <= 0.0)
        {
         LogBridge("LOT_PARSE_REJECT", StringFormat("%s_invalid_or_non_positive raw=%.10g", lotsFieldUsed, lotsRaw), signalId);
         continue;
        }

      double lots = 0.0;
      string normMsg = "";
      if(!NormalizeVolumeForSymbol(symbol, lotsRaw, lots, normMsg))
        {
         LogBridge("LOT_PARSE_REJECT", StringFormat("%s after_json raw=%.10g %s", lotsFieldUsed, lotsRaw, normMsg), signalId);
         continue;
        }

      LogBridge("LOT_RESOLVE", StringFormat("field=%s signal_lots=%.10g parsed_lots=%.10g fallback_used=false final_vol=%.10g watch=%s",
                                             lotsFieldUsed, lotsRaw, lotsRaw, lots, InpSignalFilePath), signalId);

      double bid = SymbolInfoDouble(symbol, SYMBOL_BID);
      double ask = SymbolInfoDouble(symbol, SYMBOL_ASK);

      double slSend = 0;
      double tpSend = 0;
      if(useSl)
         slSend = slRaw;
      if(useTp)
         tpSend = tpRaw;

      string failReason = "";
      double entryPriceLimit = 0;
      if(entryType == "MARKET")
        {
         if(!ValidateStopsForMarket(symbol, side, bid, ask, useSl, slRaw, useTp, tpRaw, failReason))
           {
            LogBridge("EA_PARSE_FAIL", failReason, signalId);
            continue;
           }
        }
      else
        {
         JsonNumKind epk = ExtractJsonNumberKind(line, "entry_price", entryPriceLimit);
         if(epk != JSON_NUM_VALUE || entryPriceLimit <= 0)
            epk = ExtractJsonNumberKind(line, "limit_price", entryPriceLimit);
         if(epk != JSON_NUM_VALUE || entryPriceLimit <= 0)
           {
            LogBridge("EA_PARSE_FAIL", "LIMIT requires positive entry_price or limit_price", signalId);
            continue;
           }
         if(!ValidateStopsForPending(symbol, side, entryPriceLimit, bid, ask, useSl, slRaw, useTp, tpRaw, failReason))
           {
            LogBridge("EA_PARSE_FAIL", failReason, signalId);
            continue;
           }
        }

      LogBridge("SIGNAL_ACCEPT", StringFormat("%s %s units=%d symbol_norm=%s entry=%s", side, symbolRaw, units, symbol, entryType), signalId);

      ApplySymbolFillingMode(symbol);
      bool ok = false;
      if(entryType == "MARKET")
        {
         string reqMsg = StringFormat(
                          "symbol=%s side=%s vol=%.4f price_mode=MARKET sl_set=%s tp_set=%s sl=%.10g tp=%.10g bid=%.10g ask=%.10g",
                          symbol, side, lots, (useSl ? "true" : "false"), (useTp ? "true" : "false"),
                          slSend, tpSend, bid, ask);
         LogBridge("REQUEST_SUMMARY", reqMsg, signalId);
         if(side == "BUY")
            ok = g_trade.Buy(lots, symbol, 0, slSend, tpSend);
         else
            ok = g_trade.Sell(lots, symbol, 0, slSend, tpSend);
         if(ok)
            LogBridge("EXECUTED", StringFormat("MARKET %s %s %.4f", symbol, side, lots), signalId);
         else
            LogBridge("BROKER_REJECT", g_trade.ResultRetcodeDescription(), signalId);
         RememberSignalId(signalId);
        }
      else
        {
         ENUM_ORDER_TYPE_TIME limTime;
         datetime limExp;
         ResolveLimitOrderTimePolicy(symbol, limTime, limExp);

         string expStr = (limExp == 0 ? "0" : TimeToString(limExp, TIME_DATE | TIME_SECONDS));
         string reqMsg = StringFormat(
                          "symbol=%s side=%s vol=%.4f price_mode=LIMIT entry=%.10g sl_set=%s tp_set=%s sl=%.10g tp=%.10g bid=%.10g ask=%.10g type_time=%s expiration=%s",
                          symbol, side, lots, entryPriceLimit, (useSl ? "true" : "false"), (useTp ? "true" : "false"),
                          slSend, tpSend, bid, ask, EnumToString(limTime), expStr);
         LogBridge("REQUEST_SUMMARY", reqMsg, signalId);

         MqlTradeResult limRes;
         ZeroMemory(limRes);
         if(side == "BUY")
            ok = SendPendingLimitRaw(symbol, ORDER_TYPE_BUY_LIMIT, lots, entryPriceLimit, slSend, tpSend, limTime, limExp, limRes);
         else
            ok = SendPendingLimitRaw(symbol, ORDER_TYPE_SELL_LIMIT, lots, entryPriceLimit, slSend, tpSend, limTime, limExp, limRes);

         if(ok)
            LogBridge("EXECUTED", StringFormat("LIMIT %s %s %.4f @%.10g", symbol, side, lots, entryPriceLimit), signalId);
         else
            LogBridge("BROKER_REJECT", FormatTradeResultLine(limRes), signalId);
         RememberSignalId(signalId);
        }
     }
   g_lastFilePos = FileTell(h);
   FileClose(h);
}

