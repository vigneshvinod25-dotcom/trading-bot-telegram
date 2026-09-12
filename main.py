import pandas as pd
import yfinance as yf

NIFTY_STOCKS = [
    "ADANIENT.NS",
    "ADANIPORTS.NS",
    "APOLLOHOSP.NS",
    "ASIANPAINT.NS",
    "AXISBANK.NS",
    "BAJAJ-AUTO.NS",
    "BAJFINANCE.NS",
    "BAJAJFINSV.NS",
    "BEL.NS",
    "BPCL.NS",
    "BHARTIARTL.NS",
    "BRITANNIA.NS",
    "CIPLA.NS",
    "COALINDIA.NS",
    "DRREDDY.NS",
    "EICHERMOT.NS",
    "GRASIM.NS",
    "HCLTECH.NS",
    "HDFCBANK.NS",
    "HDFCLIFE.NS",
    "HEROMOTOCO.NS",
    "HINDALCO.NS",
    "HINDUNILVR.NS",
    "ICICIBANK.NS",
    "INDUSINDBK.NS",
    "INFY.NS",
    "ITC.NS",
    "JSWSTEEL.NS",
    "KOTAKBANK.NS",
    "LT.NS",
    "LTIM.NS",
    "M&M.NS",
    "MARUTI.NS",
    "NTPC.NS",
    "NESTLEIND.NS",
    "ONGC.NS",
    "POWERGRID.NS",
    "RELIANCE.NS",
    "SBILIFE.NS",
    "SHRIRAMFIN.NS",
    "SBIN.NS",
    "SUNPHARMA.NS",
    "TCS.NS",
    "TATACONSUM.NS",
    "TATAMOTORS.NS",
    "TATASTEEL.NS",
    "TECHM.NS",
    "TITAN.NS",
    "ULTRACEMCO.NS",
    "WIPRO.NS",
]

total_trades = 0
wins = 0
losses = 0

print("⏳ കഴിഞ്ഞ 2 മാസത്തെ ഡാറ്റ ഡൗൺലോഡ് ചെയ്യുന്നു...")

# ഒരൊറ്റ റിക്വസ്റ്റിൽ ബാച്ച് ഡൗൺലോഡ് ചെയ്യുന്നു
data = yf.download(
    NIFTY_STOCKS, period="60d", interval="5m", group_by="ticker", threads=True
)

all_dates = sorted(list(set(data.index.date)))

print("\n=== ദിവസേനയുള്ള വാച്ച്‌ലിസ്റ്റും ബാക്ക്ടെസ്റ്റും ===\n")

for date in all_dates:
  daily_watchlist = []

  # 1. 9:25 AM-ലെ വാച്ച്‌ലിസ്റ്റ് കണ്ടെത്തൽ
  for symbol in NIFTY_STOCKS:
    try:
      if symbol not in data.columns.levels[0]:
        continue
      df_stock = data[symbol].dropna()
      day_df = df_stock[df_stock.index.date == date]

      if len(day_df) < 15:
        continue

      open_price = day_df["Open"].iloc[0]
      price_925 = day_df["Close"].iloc[2]  # 9:25 AM Candle
      gain = ((price_925 - open_price) / open_price) * 100

      if gain >= 0.3:
        daily_watchlist.append(symbol)
    except Exception:
      pass

  # വാച്ച്‌ലിസ്റ്റ് ഉള്ള ദിവസങ്ങൾ മാത്രം ഡിസ്‌പ്ലേ ചെയ്യുന്നു
  if not daily_watchlist:
    continue

  clean_names = [s.replace(".NS", "") for s in daily_watchlist]
  print(
      f"📅 {date} | വാച്ച്‌ലിസ്റ്റ് ({len(clean_names)}): {', '.join(clean_names)}"
  )

  # 2. വാച്ച്‌ലിസ്റ്റിലെ സ്റ്റോക്കുകളിൽ മാത്രം സ്ട്രാറ്റജി സ്കാൻ ചെയ്യുന്നു
  for symbol in daily_watchlist:
    try:
      df_stock = data[symbol].dropna()
      df_stock["EMA200"] = (
          df_stock["Close"].ewm(span=200, adjust=False).mean()
      )
      df_stock["Vol_Avg"] = df_stock["Volume"].rolling(20).mean()

      day_df = df_stock[df_stock.index.date == date]
      if len(day_df) < 15:
        continue

      orb_high = day_df["High"].iloc[:3].max()
      typical = (day_df["High"] + day_df["Low"] + day_df["Close"]) / 3
      vwap = (typical * day_df["Volume"]).cumsum() / day_df["Volume"].cumsum()

      for i in range(3, len(day_df) - 1):
        curr_close = day_df["Close"].iloc[i]
        prev_close = day_df["Close"].iloc[i - 1]
        curr_vol = day_df["Volume"].iloc[i]
        avg_vol = day_df["Vol_Avg"].iloc[i]
        ema = day_df["EMA200"].iloc[i]

        volume_ok = curr_vol > (avg_vol * 1.2)
        ema_ok = curr_close > ema

        if volume_ok and ema_ok:
          orb_signal = (prev_close <= orb_high) and (curr_close > orb_high)
          vwap_signal = (prev_close < vwap.iloc[i - 1]) and (
              curr_close > vwap.iloc[i]
          )

          if orb_signal or vwap_signal:
            entry = curr_close
            target = entry * 1.01
            sl = entry * 0.995

            future = day_df.iloc[i + 1 :]
            total_trades += 1
            stk_name = symbol.replace(".NS", "")

            if future["High"].max() >= target:
              wins += 1
              print(f"   └─ ✅ {stk_name}: Target Hit (Entry: ₹{entry})")
            elif future["Low"].min() <= sl:
              losses += 1
              print(f"   └─ ❌ {stk_name}: SL Hit (Entry: ₹{entry})")
            else:
              print(f"   └─ ⏳ {stk_name}: Open Trade (Entry: ₹{entry})")

            break  # ഒരു ദിവസം ഒരു ട്രേഡ് മാത്രം
    except Exception:
      pass

print("\n=== 2 MONTH BACKTEST SUMMARY ===")
print(f"Total Trades: {total_trades}")
print(f"Wins: {wins}")
print(f"Losses: {losses}")

if total_trades > 0:
  win_rate = round((wins / total_trades) * 100, 2)
  print(f"Win Rate: {win_rate}%")
