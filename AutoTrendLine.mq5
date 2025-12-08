//+------------------------------------------------------------------+
//|                                                AutoTrendLine.mq5 |
//|                                  Copyright 2025, Google Deepmind |
//|                                             https://www.mql5.com |
//+------------------------------------------------------------------+
#property copyright "Copyright 2025, Google Deepmind"
#property link      "https://www.mql5.com"
#property version   "1.00"
#property indicator_chart_window
#property indicator_buffers 0
#property indicator_plots   0

//--- input parameters
input int      InpPeriod         = 10;          // Fractal Period
input color    InpColorSupport   = clrBlue;     // Support Line Color
input color    InpColorResistance= clrRed;      // Resistance Line Color
input color    InpTextColor      = clrWhite;    // Text Label Color
input int      InpTextSize       = 8;          // Text Font Size

//--- global variables
string prefix = "ATL_";

//+------------------------------------------------------------------+
//| Custom indicator initialization function                         |
//+------------------------------------------------------------------+
int OnInit()
  {
   return(INIT_SUCCEEDED);
  }
//+------------------------------------------------------------------+
//| Custom indicator deinitialization function                       |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   ObjectsDeleteAll(0, prefix);
  }
//+------------------------------------------------------------------+
//| Custom indicator iteration function                              |
//+------------------------------------------------------------------+
int OnCalculate(const int rates_total,
                const int prev_calculated,
                const datetime &time[],
                const double &open[],
                const double &high[],
                const double &low[],
                const double &close[],
                const long &tick_volume[],
                const long &volume[],
                const int &spread[])
  {
   if(rates_total < InpPeriod * 2 + 1)
      return(0);

   ArraySetAsSeries(time, true);
   ArraySetAsSeries(high, true);
   ArraySetAsSeries(low, true);

   // Scan range: Re-scan enough bars to update labels and lines
   // We scan the last 500 bars (Index 500 down to 0)
   int start_idx = 500;
   if(start_idx > rates_total - InpPeriod - 1) start_idx = rates_total - InpPeriod - 1;
   
   // Clean up all objects to redraw them fresh
   ObjectsDeleteAll(0, prefix);

   int last_high_idx = -1;
   double last_high_val = 0;
   int prev_high_idx = -1;
   
   int last_low_idx = -1;
   double last_low_val = 0;
   int prev_low_idx = -1;

   // Iterate from OLDEST (High Index) to NEWEST (Low Index)
   for(int i = start_idx; i >= InpPeriod; i--)
     {
      // --- Check Swing High ---
      bool is_high = true;
      for(int k = 1; k <= InpPeriod; k++)
        {
         if(high[i] <= high[i-k] || high[i] <= high[i+k])
           {
            is_high = false;
            break;
           }
        }

      if(is_high)
        {
         string name = prefix + "TxtH_" + TimeToString(time[i]);
         string text = "H";
         
         if(last_high_idx != -1)
           {
            if(high[i] > last_high_val) text = "HH";
            else if(high[i] < last_high_val) text = "LH";
            else text = "EH"; // Equal High
           }
         
         // Create Label
         if(ObjectCreate(0, name, OBJ_TEXT, 0, time[i], high[i]))
           {
            ObjectSetString(0, name, OBJPROP_TEXT, text);
            ObjectSetInteger(0, name, OBJPROP_COLOR, InpTextColor);
            ObjectSetInteger(0, name, OBJPROP_FONTSIZE, InpTextSize);
            ObjectSetInteger(0, name, OBJPROP_ANCHOR, ANCHOR_BOTTOM);
           }
           
         prev_high_idx = last_high_idx;
         last_high_idx = i;
         last_high_val = high[i];
        }

      // --- Check Swing Low ---
      bool is_low = true;
      for(int k = 1; k <= InpPeriod; k++)
        {
         if(low[i] >= low[i-k] || low[i] >= low[i+k])
           {
            is_low = false;
            break;
           }
        }

      if(is_low)
        {
         string name = prefix + "TxtL_" + TimeToString(time[i]);
         string text = "L";
         
         if(last_low_idx != -1)
           {
            if(low[i] > last_low_val) text = "HL";
            else if(low[i] < last_low_val) text = "LL";
            else text = "EL"; // Equal Low
           }

         // Create Label
         if(ObjectCreate(0, name, OBJ_TEXT, 0, time[i], low[i]))
           {
            ObjectSetString(0, name, OBJPROP_TEXT, text);
            ObjectSetInteger(0, name, OBJPROP_COLOR, InpTextColor);
            ObjectSetInteger(0, name, OBJPROP_FONTSIZE, InpTextSize);
            ObjectSetInteger(0, name, OBJPROP_ANCHOR, ANCHOR_TOP);
           }
           
         prev_low_idx = last_low_idx;
         last_low_idx = i;
         last_low_val = low[i];
        }
     }

   // --- Draw Trend Lines connecting the last two swing points ---
   
   // Resistance Line
   if(last_high_idx != -1 && prev_high_idx != -1)
     {
      string name = prefix + "ResLine";
      if(ObjectCreate(0, name, OBJ_TREND, 0, time[prev_high_idx], high[prev_high_idx], time[last_high_idx], high[last_high_idx]))
        {
         ObjectSetInteger(0, name, OBJPROP_COLOR, InpColorResistance);
         ObjectSetInteger(0, name, OBJPROP_WIDTH, 2);
         ObjectSetInteger(0, name, OBJPROP_RAY_RIGHT, true);
        }
     }

   // Support Line
   if(last_low_idx != -1 && prev_low_idx != -1)
     {
      string name = prefix + "SupLine";
      if(ObjectCreate(0, name, OBJ_TREND, 0, time[prev_low_idx], low[prev_low_idx], time[last_low_idx], low[last_low_idx]))
        {
         ObjectSetInteger(0, name, OBJPROP_COLOR, InpColorSupport);
         ObjectSetInteger(0, name, OBJPROP_WIDTH, 2);
         ObjectSetInteger(0, name, OBJPROP_RAY_RIGHT, true);
        }
     }

   return(rates_total);
  }
