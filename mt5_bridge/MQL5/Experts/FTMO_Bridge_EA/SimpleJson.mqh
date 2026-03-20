//+------------------------------------------------------------------+
//|                                                      SimpleJson.mqh |
//|                                                   Copyright 2026 |
//|                                                Minimal JSON Parser |
//+------------------------------------------------------------------+
#property copyright "Copyright 2026"
#property link      ""
#property strict

// A very basic JSON parser for the specific needs of the Bridge
// capable of parsing a list of objects and extracting string/number fields.
// NOT a full JSON validator.

class CSimpleJson
{
private:
   string m_json;
   int    m_length;
   int    m_pos;

public:
   CSimpleJson() : m_json(""), m_length(0), m_pos(0) {}
   
   void SetJson(string json)
   {
      m_json = json;
      m_length = StringLen(json);
      m_pos = 0;
   }
   
   // Extract values from an object string for a given key
   // Assumes simple structure "key": "value" or "key": number
   static string ExtractString(string json_object, string key)
   {
      string search = "\"" + key + "\"";
      int start = StringFind(json_object, search);
      if (start == -1) return "";
      
      start += StringLen(search);
      // Find colon
      start = StringFind(json_object, ":", start);
      if (start == -1) return "";
      start++; // skip colon
      
      // Skip whitespace
      while(start < StringLen(json_object) && (StringGetCharacter(json_object, start) == ' ' || StringGetCharacter(json_object, start) == '\t')) start++;
      
      // Check if string
      if (StringGetCharacter(json_object, start) == '\"')
      {
         start++; // skip quote
         int end = start;
         bool escaped = false;
         while(end < StringLen(json_object))
         {
            ushort c = StringGetCharacter(json_object, end);
            if (c == '\\' && !escaped) escaped = true;
            else if (c == '\"' && !escaped) break;
            else escaped = false;
            end++;
         }
         return StringSubstr(json_object, start, end - start);
      }
      return "";
   }
   
   static double ExtractDouble(string json_object, string key)
   {
      string val = ExtractPrimitive(json_object, key);
      if (val == "null" || val == "") return 0.0;
      return StringToDouble(val);
   }
   
   static long ExtractInteger(string json_object, string key)
   {
      string val = ExtractPrimitive(json_object, key);
      if (val == "null" || val == "") return 0;
      return StringToInteger(val);
   }
   
   static bool ExtractBool(string json_object, string key)
   {
      string val = ExtractPrimitive(json_object, key);
      return (val == "true");
   }

   // Extract primitive value (number, boolean, null)
   static string ExtractPrimitive(string json_object, string key)
   {
      string search = "\"" + key + "\"";
      int start = StringFind(json_object, search);
      if (start == -1) return "";
      
      start += StringLen(search);
      start = StringFind(json_object, ":", start);
      if (start == -1) return "";
      start++;
      
      while(start < StringLen(json_object) && (StringGetCharacter(json_object, start) == ' ' || StringGetCharacter(json_object, start) == '\t')) start++;
      
      int end = start;
      while(end < StringLen(json_object))
      {
         ushort c = StringGetCharacter(json_object, end);
         if (c == ',' || c == '}' || c == ']') break;
         end++;
      }
      return StringSubstr(json_object, start, end - start);
   }

   // Split a JSON array of objects into string array of objects
   // Assumes format [{"..."}, {"..."}]
   static void SplitArrayObjects(string json_array, string &objects[])
   {
      ArrayResize(objects, 0);
      int depth = 0;
      int start = -1;
      int count = 0;
      
      for(int i=0; i<StringLen(json_array); i++)
      {
         ushort c = StringGetCharacter(json_array, i);
         if(c == '{')
         {
            if(depth == 0) start = i;
            depth++;
         }
         else if(c == '}')
         {
            depth--;
            if(depth == 0 && start != -1)
            {
               count++;
               ArrayResize(objects, count);
               objects[count-1] = StringSubstr(json_array, start, i - start + 1);
               start = -1;
            }
         }
      }
   }
};
