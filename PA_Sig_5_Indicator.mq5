//+------------------------------------------------------------------+
//|                                           PA_Sig_5_Indicator.mq5 |
//|                                  Copyright 2025, HackWarrior     |
//|                                                                  |
//+------------------------------------------------------------------+
#property copyright "Copyright 2025, HackWarrior"
#property link      ""
#property version   "1.00"
#property indicator_chart_window
#property indicator_buffers 2
#property indicator_plots   2

//--- Plot Buy signals
#property indicator_label1  "Buy Signal"
#property indicator_type1   DRAW_ARROW
#property indicator_color1  clrLime
#property indicator_style1  STYLE_SOLID
#property indicator_width1  2

//--- Plot Sell signals
#property indicator_label2  "Sell Signal"
#property indicator_type2   DRAW_ARROW
#property indicator_color2  clrRed
#property indicator_style2  STYLE_SOLID
#property indicator_width2  2

//--- Input parameters
input group "=== Pattern Detection Settings ==="
input int    InpPAT1_MinBodyRatio = 60;        // PAT 1: Minimum body ratio (%)
input int    InpPAT2_MinBodyRatio = 50;        // PAT 2: Minimum body ratio (%)
input double InpPAT3_PullbackRatio = 0.382;    // PAT 3: Pullback ratio (Fibonacci)
input int    InpLookbackBars = 10;             // Lookback bars for pattern validation

input group "=== Visual Settings ==="
input color  InpBuyColor = clrLime;            // Buy arrow color
input color  InpSellColor = clrRed;            // Sell arrow color
input int    InpArrowSize = 2;                 // Arrow size
input bool   InpShowLabels = true;             // Show pattern labels
input color  InpLabelColor = clrWhite;         // Label text color

input group "=== Alert Settings ==="
input bool   InpEnableAlerts = true;           // Enable popup alerts
input bool   InpEnableEmail = false;           // Enable email alerts
input bool   InpEnablePush = false;            // Enable push notifications
input bool   InpAlertOnBarClose = true;        // Alert only on bar close

//--- Indicator buffers
double BuyBuffer[];
double SellBuffer[];

//--- Global variables
datetime lastAlertTime = 0;

//+------------------------------------------------------------------+
//| Custom indicator initialization function                         |
//+------------------------------------------------------------------+
int OnInit()
{
   //--- Indicator buffers mapping
   SetIndexBuffer(0, BuyBuffer, INDICATOR_DATA);
   SetIndexBuffer(1, SellBuffer, INDICATOR_DATA);
   
   //--- Set arrow codes
   PlotIndexSetInteger(0, PLOT_ARROW, 233); // Up arrow
   PlotIndexSetInteger(1, PLOT_ARROW, 234); // Down arrow
   
   //--- Set arrow colors
   PlotIndexSetInteger(0, PLOT_LINE_COLOR, InpBuyColor);
   PlotIndexSetInteger(1, PLOT_LINE_COLOR, InpSellColor);
   
   //--- Set empty values
   PlotIndexSetDouble(0, PLOT_EMPTY_VALUE, 0.0);
   PlotIndexSetDouble(1, PLOT_EMPTY_VALUE, 0.0);
   
   //--- Initialize buffers
   ArraySetAsSeries(BuyBuffer, true);
   ArraySetAsSeries(SellBuffer, true);
   
   //--- Set indicator name
   IndicatorSetString(INDICATOR_SHORTNAME, "PA Sig 5 Patterns");
   
   return(INIT_SUCCEEDED);
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
   //--- Set arrays as series
   ArraySetAsSeries(open, true);
   ArraySetAsSeries(high, true);
   ArraySetAsSeries(low, true);
   ArraySetAsSeries(close, true);
   ArraySetAsSeries(time, true);
   
   //--- Check if we have enough bars
   if(rates_total < InpLookbackBars + 5)
      return(0);
   
   //--- Calculate start position
   int limit = rates_total - prev_calculated;
   if(limit > 1)
   {
      limit = rates_total - InpLookbackBars - 5;
      ArrayInitialize(BuyBuffer, 0.0);
      ArrayInitialize(SellBuffer, 0.0);
   }
   
   //--- Main loop
   for(int i = limit; i >= 0; i--)
   {
      BuyBuffer[i] = 0.0;
      SellBuffer[i] = 0.0;
      
      //--- Skip current bar if alert on bar close is enabled
      if(InpAlertOnBarClose && i == 0)
         continue;
      
      //--- Detect Buy signals
      if(DetectBuySignal(i, open, high, low, close))
      {
         BuyBuffer[i] = low[i] - (high[i] - low[i]) * 0.2;
         
         //--- Create label
         if(InpShowLabels && i <= 1)
         {
            string patternType = IdentifyBuyPattern(i, open, high, low, close);
            CreateLabel("Buy_" + TimeToString(time[i]), time[i], BuyBuffer[i], patternType, InpBuyColor);
         }
         
         //--- Send alert
         if(i == 1 && InpEnableAlerts && time[i] != lastAlertTime)
         {
            string patternType = IdentifyBuyPattern(i, open, high, low, close);
            SendAlerts("BUY Signal: " + patternType + " on " + _Symbol + " " + PeriodToString());
            lastAlertTime = time[i];
         }
      }
      
      //--- Detect Sell signals
      if(DetectSellSignal(i, open, high, low, close))
      {
         SellBuffer[i] = high[i] + (high[i] - low[i]) * 0.2;
         
         //--- Create label
         if(InpShowLabels && i <= 1)
         {
            string patternType = IdentifySellPattern(i, open, high, low, close);
            CreateLabel("Sell_" + TimeToString(time[i]), time[i], SellBuffer[i], patternType, InpSellColor);
         }
         
         //--- Send alert
         if(i == 1 && InpEnableAlerts && time[i] != lastAlertTime)
         {
            string patternType = IdentifySellPattern(i, open, high, low, close);
            SendAlerts("SELL Signal: " + patternType + " on " + _Symbol + " " + PeriodToString());
            lastAlertTime = time[i];
         }
      }
   }
   
   return(rates_total);
}

//+------------------------------------------------------------------+
//| Detect PAT 1 (Buy) - Initial reversal pattern                    |
//+------------------------------------------------------------------+
bool DetectPAT1_Buy(int shift, const double &open[], const double &high[], 
                    const double &low[], const double &close[])
{
   if(shift + 2 >= ArraySize(close))
      return false;
   
   //--- Previous candle should be bearish or small
   double prevBody = MathAbs(close[shift+1] - open[shift+1]);
   double prevRange = high[shift+1] - low[shift+1];
   
   //--- Current candle should be bullish with larger body
   double currBody = close[shift] - open[shift];
   double currRange = high[shift] - low[shift];
   
   //--- Check conditions
   bool isBullish = close[shift] > open[shift];
   bool hasLargerBody = currBody > prevBody * 1.5;
   bool goodBodyRatio = (currBody / currRange * 100) >= InpPAT1_MinBodyRatio;
   bool closedAbovePrevHigh = close[shift] > high[shift+1];
   
   return (isBullish && hasLargerBody && goodBodyRatio && closedAbovePrevHigh);
}

//+------------------------------------------------------------------+
//| Detect PAT 1 (Sell) - Initial reversal pattern                   |
//+------------------------------------------------------------------+
bool DetectPAT1_Sell(int shift, const double &open[], const double &high[], 
                     const double &low[], const double &close[])
{
   if(shift + 2 >= ArraySize(close))
      return false;
   
   //--- Previous candle should be bullish or small
   double prevBody = MathAbs(close[shift+1] - open[shift+1]);
   double prevRange = high[shift+1] - low[shift+1];
   
   //--- Current candle should be bearish with larger body
   double currBody = open[shift] - close[shift];
   double currRange = high[shift] - low[shift];
   
   //--- Check conditions
   bool isBearish = close[shift] < open[shift];
   bool hasLargerBody = currBody > prevBody * 1.5;
   bool goodBodyRatio = (currBody / currRange * 100) >= InpPAT1_MinBodyRatio;
   bool closedBelowPrevLow = close[shift] < low[shift+1];
   
   return (isBearish && hasLargerBody && goodBodyRatio && closedBelowPrevLow);
}

//+------------------------------------------------------------------+
//| Detect PAT 2 (Buy) - Confirmation candle                         |
//+------------------------------------------------------------------+
bool DetectPAT2_Buy(int shift, const double &open[], const double &high[], 
                    const double &low[], const double &close[])
{
   if(shift + 3 >= ArraySize(close))
      return false;
   
   //--- Should follow a bullish candle (PAT 1)
   if(!DetectPAT1_Buy(shift+1, open, high, low, close))
      return false;
   
   //--- Current candle should be bullish
   double currBody = close[shift] - open[shift];
   double currRange = high[shift] - low[shift];
   
   //--- Check higher high and higher low
   bool isBullish = close[shift] > open[shift];
   bool higherHigh = high[shift] > high[shift+1];
   bool higherLow = low[shift] > low[shift+1];
   bool goodBodyRatio = (currBody / currRange * 100) >= InpPAT2_MinBodyRatio;
   
   return (isBullish && higherHigh && higherLow && goodBodyRatio);
}

//+------------------------------------------------------------------+
//| Detect PAT 2 (Sell) - Confirmation candle                        |
//+------------------------------------------------------------------+
bool DetectPAT2_Sell(int shift, const double &open[], const double &high[], 
                     const double &low[], const double &close[])
{
   if(shift + 3 >= ArraySize(close))
      return false;
   
   //--- Should follow a bearish candle (PAT 1)
   if(!DetectPAT1_Sell(shift+1, open, high, low, close))
      return false;
   
   //--- Current candle should be bearish
   double currBody = open[shift] - close[shift];
   double currRange = high[shift] - low[shift];
   
   //--- Check lower high and lower low
   bool isBearish = close[shift] < open[shift];
   bool lowerHigh = high[shift] < high[shift+1];
   bool lowerLow = low[shift] < low[shift+1];
   bool goodBodyRatio = (currBody / currRange * 100) >= InpPAT2_MinBodyRatio;
   
   return (isBearish && lowerHigh && lowerLow && goodBodyRatio);
}

//+------------------------------------------------------------------+
//| Detect PAT 3 Type 1 (Buy) - Strong continuation after pullback   |
//+------------------------------------------------------------------+
bool DetectPAT3_Type1_Buy(int shift, const double &open[], const double &high[], 
                          const double &low[], const double &close[])
{
   if(shift + 4 >= ArraySize(close))
      return false;
   
   //--- Find recent swing high
   double swingHigh = high[shift+1];
   for(int i = shift+1; i <= shift+3; i++)
      if(high[i] > swingHigh) swingHigh = high[i];
   
   //--- Find recent swing low (pullback)
   double swingLow = low[shift+1];
   for(int i = shift+1; i <= shift+3; i++)
      if(low[i] < swingLow) swingLow = low[i];
   
   //--- Calculate pullback ratio
   double swingRange = swingHigh - swingLow;
   double pullback = swingHigh - swingLow;
   double pullbackRatio = pullback / swingRange;
   
   //--- Current candle should be strong bullish breaking above
   bool isBullish = close[shift] > open[shift];
   bool breakoutAbove = close[shift] > swingHigh;
   bool validPullback = pullbackRatio >= InpPAT3_PullbackRatio && pullbackRatio <= 0.618;
   
   return (isBullish && breakoutAbove && validPullback);
}

//+------------------------------------------------------------------+
//| Detect PAT 3 Type 1 (Sell) - Strong continuation after pullback  |
//+------------------------------------------------------------------+
bool DetectPAT3_Type1_Sell(int shift, const double &open[], const double &high[], 
                           const double &low[], const double &close[])
{
   if(shift + 4 >= ArraySize(close))
      return false;
   
   //--- Find recent swing low
   double swingLow = low[shift+1];
   for(int i = shift+1; i <= shift+3; i++)
      if(low[i] < swingLow) swingLow = low[i];
   
   //--- Find recent swing high (pullback)
   double swingHigh = high[shift+1];
   for(int i = shift+1; i <= shift+3; i++)
      if(high[i] > swingHigh) swingHigh = high[i];
   
   //--- Calculate pullback ratio
   double swingRange = swingHigh - swingLow;
   double pullback = swingHigh - swingLow;
   double pullbackRatio = pullback / swingRange;
   
   //--- Current candle should be strong bearish breaking below
   bool isBearish = close[shift] < open[shift];
   bool breakoutBelow = close[shift] < swingLow;
   bool validPullback = pullbackRatio >= InpPAT3_PullbackRatio && pullbackRatio <= 0.618;
   
   return (isBearish && breakoutBelow && validPullback);
}

//+------------------------------------------------------------------+
//| Detect PAT 3 Type 2 (Buy) - Multiple small candles then breakout |
//+------------------------------------------------------------------+
bool DetectPAT3_Type2_Buy(int shift, const double &open[], const double &high[], 
                          const double &low[], const double &close[])
{
   if(shift + 5 >= ArraySize(close))
      return false;
   
   //--- Count small consolidation candles
   int smallCandleCount = 0;
   double avgRange = 0;
   
   for(int i = shift+1; i <= shift+3; i++)
   {
      double range = high[i] - low[i];
      avgRange += range;
      double body = MathAbs(close[i] - open[i]);
      if(body < range * 0.5) // Small body
         smallCandleCount++;
   }
   avgRange /= 3;
   
   //--- Current candle should be strong bullish breakout
   double currBody = close[shift] - open[shift];
   double currRange = high[shift] - low[shift];
   
   bool hasConsolidation = smallCandleCount >= 2;
   bool isBullish = close[shift] > open[shift];
   bool isBreakout = currRange > avgRange * 1.5;
   bool strongBody = currBody > currRange * 0.6;
   
   return (hasConsolidation && isBullish && isBreakout && strongBody);
}

//+------------------------------------------------------------------+
//| Detect PAT 3 Type 2 (Sell) - Multiple small candles then breakout|
//+------------------------------------------------------------------+
bool DetectPAT3_Type2_Sell(int shift, const double &open[], const double &high[], 
                           const double &low[], const double &close[])
{
   if(shift + 5 >= ArraySize(close))
      return false;
   
   //--- Count small consolidation candles
   int smallCandleCount = 0;
   double avgRange = 0;
   
   for(int i = shift+1; i <= shift+3; i++)
   {
      double range = high[i] - low[i];
      avgRange += range;
      double body = MathAbs(close[i] - open[i]);
      if(body < range * 0.5) // Small body
         smallCandleCount++;
   }
   avgRange /= 3;
   
   //--- Current candle should be strong bearish breakout
   double currBody = open[shift] - close[shift];
   double currRange = high[shift] - low[shift];
   
   bool hasConsolidation = smallCandleCount >= 2;
   bool isBearish = close[shift] < open[shift];
   bool isBreakout = currRange > avgRange * 1.5;
   bool strongBody = currBody > currRange * 0.6;
   
   return (hasConsolidation && isBearish && isBreakout && strongBody);
}

//+------------------------------------------------------------------+
//| Detect PAT 3 Type 3 (Buy) - Consolidation with decreasing volatility|
//+------------------------------------------------------------------+
bool DetectPAT3_Type3_Buy(int shift, const double &open[], const double &high[], 
                          const double &low[], const double &close[])
{
   if(shift + 5 >= ArraySize(close))
      return false;
   
   //--- Check for decreasing volatility (narrowing range)
   double range1 = high[shift+3] - low[shift+3];
   double range2 = high[shift+2] - low[shift+2];
   double range3 = high[shift+1] - low[shift+1];
   
   bool decreasingVolatility = (range2 < range1) && (range3 < range2);
   
   //--- Current candle should be strong bullish breakout
   double currBody = close[shift] - open[shift];
   double currRange = high[shift] - low[shift];
   double avgPrevRange = (range1 + range2 + range3) / 3;
   
   bool isBullish = close[shift] > open[shift];
   bool isBreakout = currRange > avgPrevRange * 1.8;
   bool strongBody = currBody > currRange * 0.65;
   bool breaksHigh = close[shift] > MathMax(MathMax(high[shift+1], high[shift+2]), high[shift+3]);
   
   return (decreasingVolatility && isBullish && isBreakout && strongBody && breaksHigh);
}

//+------------------------------------------------------------------+
//| Detect PAT 3 Type 3 (Sell) - Consolidation with decreasing volatility|
//+------------------------------------------------------------------+
bool DetectPAT3_Type3_Sell(int shift, const double &open[], const double &high[], 
                           const double &low[], const double &close[])
{
   if(shift + 5 >= ArraySize(close))
      return false;
   
   //--- Check for decreasing volatility (narrowing range)
   double range1 = high[shift+3] - low[shift+3];
   double range2 = high[shift+2] - low[shift+2];
   double range3 = high[shift+1] - low[shift+1];
   
   bool decreasingVolatility = (range2 < range1) && (range3 < range2);
   
   //--- Current candle should be strong bearish breakout
   double currBody = open[shift] - close[shift];
   double currRange = high[shift] - low[shift];
   double avgPrevRange = (range1 + range2 + range3) / 3;
   
   bool isBearish = close[shift] < open[shift];
   bool isBreakout = currRange > avgPrevRange * 1.8;
   bool strongBody = currBody > currRange * 0.65;
   bool breaksLow = close[shift] < MathMin(MathMin(low[shift+1], low[shift+2]), low[shift+3]);
   
   return (decreasingVolatility && isBearish && isBreakout && strongBody && breaksLow);
}

//+------------------------------------------------------------------+
//| Detect Buy Signal - Combines all patterns                        |
//+------------------------------------------------------------------+
bool DetectBuySignal(int shift, const double &open[], const double &high[], 
                     const double &low[], const double &close[])
{
   return (DetectPAT1_Buy(shift, open, high, low, close) ||
           DetectPAT2_Buy(shift, open, high, low, close) ||
           DetectPAT3_Type1_Buy(shift, open, high, low, close) ||
           DetectPAT3_Type2_Buy(shift, open, high, low, close) ||
           DetectPAT3_Type3_Buy(shift, open, high, low, close));
}

//+------------------------------------------------------------------+
//| Detect Sell Signal - Combines all patterns                       |
//+------------------------------------------------------------------+
bool DetectSellSignal(int shift, const double &open[], const double &high[], 
                      const double &low[], const double &close[])
{
   return (DetectPAT1_Sell(shift, open, high, low, close) ||
           DetectPAT2_Sell(shift, open, high, low, close) ||
           DetectPAT3_Type1_Sell(shift, open, high, low, close) ||
           DetectPAT3_Type2_Sell(shift, open, high, low, close) ||
           DetectPAT3_Type3_Sell(shift, open, high, low, close));
}

//+------------------------------------------------------------------+
//| Identify specific Buy pattern type                               |
//+------------------------------------------------------------------+
string IdentifyBuyPattern(int shift, const double &open[], const double &high[], 
                          const double &low[], const double &close[])
{
   if(DetectPAT1_Buy(shift, open, high, low, close))
      return "PAT 1";
   if(DetectPAT2_Buy(shift, open, high, low, close))
      return "PAT 2";
   if(DetectPAT3_Type1_Buy(shift, open, high, low, close))
      return "PAT 3-1";
   if(DetectPAT3_Type2_Buy(shift, open, high, low, close))
      return "PAT 3-2";
   if(DetectPAT3_Type3_Buy(shift, open, high, low, close))
      return "PAT 3-3";
   
   return "Unknown";
}

//+------------------------------------------------------------------+
//| Identify specific Sell pattern type                              |
//+------------------------------------------------------------------+
string IdentifySellPattern(int shift, const double &open[], const double &high[], 
                           const double &low[], const double &close[])
{
   if(DetectPAT1_Sell(shift, open, high, low, close))
      return "PAT 1";
   if(DetectPAT2_Sell(shift, open, high, low, close))
      return "PAT 2";
   if(DetectPAT3_Type1_Sell(shift, open, high, low, close))
      return "PAT 3-1";
   if(DetectPAT3_Type2_Sell(shift, open, high, low, close))
      return "PAT 3-2";
   if(DetectPAT3_Type3_Sell(shift, open, high, low, close))
      return "PAT 3-3";
   
   return "Unknown";
}

//+------------------------------------------------------------------+
//| Create text label on chart                                       |
//+------------------------------------------------------------------+
void CreateLabel(string name, datetime time, double price, string text, color clr)
{
   if(ObjectFind(0, name) >= 0)
      ObjectDelete(0, name);
   
   ObjectCreate(0, name, OBJ_TEXT, 0, time, price);
   ObjectSetString(0, name, OBJPROP_TEXT, text);
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE, 8);
   ObjectSetString(0, name, OBJPROP_FONT, "Arial Bold");
   ObjectSetInteger(0, name, OBJPROP_BACK, false);
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
}

//+------------------------------------------------------------------+
//| Send alerts via all enabled methods                              |
//+------------------------------------------------------------------+
void SendAlerts(string message)
{
   if(InpEnableAlerts)
      Alert(message);
   
   if(InpEnableEmail)
      SendMail("PA Sig 5 Indicator Alert", message);
   
   if(InpEnablePush)
      SendNotification(message);
}

//+------------------------------------------------------------------+
//| Convert period to string                                         |
//+------------------------------------------------------------------+
string PeriodToString()
{
   switch(_Period)
   {
      case PERIOD_M1:  return "M1";
      case PERIOD_M5:  return "M5";
      case PERIOD_M15: return "M15";
      case PERIOD_M30: return "M30";
      case PERIOD_H1:  return "H1";
      case PERIOD_H4:  return "H4";
      case PERIOD_D1:  return "D1";
      case PERIOD_W1:  return "W1";
      case PERIOD_MN1: return "MN1";
      default:         return "Unknown";
   }
}
//+------------------------------------------------------------------+
