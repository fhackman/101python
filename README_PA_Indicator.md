# PA Sig 5 Patterns - MT5 Indicator

## Overview

The **PA Sig 5 Indicator** is a MetaTrader 5 custom indicator designed to detect five specific Price Action patterns based on Thai trading methodology. It identifies both BUY and SELL signals with visual alerts and customizable notifications.

![Buy Pattern](file:///C:/Users/HackWarrior/.gemini/antigravity/brain/ae6739ef-4f47-41d4-b37e-41f2a4e8ef56/uploaded_image_1_1764689584403.jpg)

## Features

- **5 Pattern Detection Types**

  - PAT 1: Initial reversal pattern (small candle followed by strong breakout)
  - PAT 2: Confirmation candle (higher highs/lower lows continuation)
  - PAT 3-1: Strong continuation after pullback
  - PAT 3-2: Breakout after consolidation
  - PAT 3-3: Volatility contraction breakout

- **Visual Alerts**

  - Up arrows (lime) for BUY signals
  - Down arrows (red) for SELL signals
  - Pattern labels on chart
  - Customizable colors and sizes

- **Notification System**
  - Popup alerts
  - Email notifications
  - Mobile push notifications
  - Alert on bar close option

## Installation

1. Copy `PA_Sig_5_Indicator.mq5` to your MetaTrader 5 indicators folder:

   ```
   C:\Users\[YourUsername]\AppData\Roaming\MetaQuotes\Terminal\[TerminalID]\MQL5\Indicators\
   ```

2. Restart MetaTrader 5 or right-click on Navigator → Refresh

3. Find "PA Sig 5 Patterns" in the Navigator under Indicators

4. Drag and drop onto your chart

## Parameters

### Pattern Detection Settings

| Parameter                 | Default | Description                        |
| ------------------------- | ------- | ---------------------------------- |
| **InpPAT1_MinBodyRatio**  | 60      | Minimum body ratio for PAT 1 (%)   |
| **InpPAT2_MinBodyRatio**  | 50      | Minimum body ratio for PAT 2 (%)   |
| **InpPAT3_PullbackRatio** | 0.382   | Fibonacci pullback ratio for PAT 3 |
| **InpLookbackBars**       | 10      | Number of bars to analyze          |

### Visual Settings

| Parameter         | Default | Description            |
| ----------------- | ------- | ---------------------- |
| **InpBuyColor**   | Lime    | Color for BUY arrows   |
| **InpSellColor**  | Red     | Color for SELL arrows  |
| **InpArrowSize**  | 2       | Size of signal arrows  |
| **InpShowLabels** | true    | Display pattern labels |
| **InpLabelColor** | White   | Color for pattern text |

### Alert Settings

| Parameter              | Default | Description                |
| ---------------------- | ------- | -------------------------- |
| **InpEnableAlerts**    | true    | Enable popup alerts        |
| **InpEnableEmail**     | false   | Enable email notifications |
| **InpEnablePush**      | false   | Enable push notifications  |
| **InpAlertOnBarClose** | true    | Alert only when bar closes |

## Pattern Descriptions

### BUY Patterns

#### PAT 1 - Initial Reversal

- Previous candle: Small or bearish
- Current candle: Strong bullish with larger body
- Closes above previous high
- **Signal**: Potential trend reversal to upside

#### PAT 2 - Confirmation

- Follows PAT 1 pattern
- Bullish candle with higher high and higher low
- Strong body ratio
- **Signal**: Continuation confirmation

#### PAT 3-1 - Pullback Breakout

- Identifies swing high
- Validates pullback (38.2% - 61.8% Fibonacci)
- Strong bullish breakout above swing high
- **Signal**: Continuation after healthy pullback

#### PAT 3-2 - Consolidation Breakout

- Multiple small consolidation candles
- Strong bullish breakout candle
- Volume expansion (range increase)
- **Signal**: Breakout from consolidation

#### PAT 3-3 - Volatility Contraction

- Decreasing candle ranges (narrowing volatility)
- Strong bullish breakout candle
- Breaks above recent highs
- **Signal**: Explosive move after compression

### SELL Patterns

All SELL patterns are mirror opposites of BUY patterns:

- PAT 1: Strong bearish reversal
- PAT 2: Bearish confirmation with lower lows
- PAT 3-1: Breakdown after pullback
- PAT 3-2: Bearish breakout from consolidation
- PAT 3-3: Bearish explosion after compression

## Usage Tips

1. **Timeframe Selection**

   - Works on all timeframes (M1 to MN1)
   - Best results on H1, H4, and D1 for swing trading
   - M5 and M15 for intraday scalping

2. **Confirmation**

   - Wait for candle close before entering
   - Use with trend analysis for better accuracy
   - Combine with support/resistance levels

3. **Risk Management**

   - Set stop loss below recent swing low (BUY) or above swing high (SELL)
   - Use proper position sizing
   - Consider ATR for stop loss placement

4. **Multiple Patterns**
   - PAT 2 following PAT 1 is stronger signal
   - PAT 3 variations indicate strong momentum
   - Multiple patterns on same bar = high confidence

## Customization

### Changing Arrow Appearance

```mql5
// In indicator properties:
PlotIndexSetInteger(0, PLOT_ARROW, 233);  // Up arrow code
PlotIndexSetInteger(1, PLOT_ARROW, 234);  // Down arrow code
```

Common arrow codes:

- 233: Up arrow
- 234: Down arrow
- 241: Circle
- 242: Square

### Adjusting Sensitivity

**More Signals (Less Strict)**

- Decrease `InpPAT1_MinBodyRatio` to 50
- Decrease `InpPAT2_MinBodyRatio` to 40
- Increase `InpPAT3_PullbackRatio` to 0.5

**Fewer Signals (More Strict)**

- Increase `InpPAT1_MinBodyRatio` to 70
- Increase `InpPAT2_MinBodyRatio` to 60
- Decrease `InpPAT3_PullbackRatio` to 0.3

## Troubleshooting

### No Signals Appearing

- Check if enough historical data is loaded
- Verify `InpLookbackBars` is appropriate for timeframe
- Try reducing body ratio requirements

### Too Many Signals

- Increase minimum body ratios
- Enable `InpAlertOnBarClose` to avoid repainting
- Use stricter pullback ratios

### Alerts Not Working

- Enable alerts in MT5: Tools → Options → Notifications
- For email: Configure SMTP settings in MT5
- For push: Enable notifications in MetaTrader mobile app

## Technical Support

For issues or questions:

- Review pattern detection logic in source code
- Adjust parameters based on market conditions
- Test on demo account first

## Version History

**v1.00** (2025-12-02)

- Initial release
- 5 pattern detection types
- Full alert system
- Customizable visual settings

## License

Copyright 2025, HackWarrior

---

**Disclaimer**: This indicator is for educational purposes. Always practice proper risk management and test thoroughly before live trading.
