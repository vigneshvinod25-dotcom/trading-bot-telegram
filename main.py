import time
import pandas as pd
import yfinance as yf


def get_nifty50_list():
  return [
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


NIFTY_STOCKS = get_nifty50_list()

total_trades = 0
wins = 0
losses = 0

print("⏳ 2 മാസത്തെ ബാക്ക്ടെസ്റ്റിംഗ് ആരംഭിക്കുന്നു...")

for symbol in NIFTY_STOCKS:
  try:
    # Yahoo API ബ്ലോക്ക് ഒഴിവാക്കാൻ 1 സെക്കൻഡ് ഇടവേള
    time.sleep(1)

    ticker = yf.Ticker(symbol)
    df = ticker.history(period="60d", interval="5m")

    if df.empty or len(df) < 100:
      continue

    # EMA 200 & Volume MA
    df["EMA200"] = df["Close"].ewm(span=200, adjust=False).mean()
    df["Vol_Avg"] = df["Volume"].rolling(20).mean()
    df["Date"] = df.index.date

    for date, day_df in df.groupby("Date"):
      if len(day_df) < 15:
        continue

      # 1. 9:25 AM വാച്ച്‌ലിസ്റ്റ് ഫിൽട്ടർ (0.3% Gain)
      open_price = day_df["Open"].iloc[0]
      price_925 = day_df["Close"].iloc[2]
      gain = ((price_925 - open_price) / open_price) * 100

      if gain < 0.3:
        continue

      # 2. ORB High (ആദ്യ 15 മിനിറ്റ്)
      orb_high = day_df["High"].iloc[:3].max()

      # 3. VWAP
      typical = (day_df["High"] + day_df["Low"] + day_df["Close"]) / 3
      vwap = (typical * day_df["Volume"]).cumsum() / day_df["Volume"].cumsum()

      # 9:30 AM - 3:30 PM സ്കാനിംഗ്
      for i in range(3, len(day_df) - 1):
        curr_close = day_df["Close"].iloc[i]
        prev_close = day_df["Close"].iloc[i - 1]
        curr_vol = day_df["Volume"].iloc[i]
        avg_vol = day_df["Vol_Avg"].iloc[i]
        ema = day_df["EMA200"].iloc[i]

        volume_ok = curr_vol > (avg_vol * 1.2)
        ema_ok = curr_close > ema

        if volume_ok and ema_ok:
          orb_signal = prev_close <= orb_high and curr_close > orb_high
          vwap_signal = (
              prev_close < vwap.iloc[i - 1] and curr_close > vwap.iloc[i]
          )

          if orb_signal or vwap_signal:
            entry = curr_close
            target = entry * 1.01  # 1% Target
            sl = entry * 0.995  # 0.5% SL

            future = day_df.iloc[i + 1 :]
            total_trades += 1

            if future["High"].max() >= target:
              wins += 1
            elif future["Low"].min() <= sl:
              losses += 1

            break  # ഒരു ദിവസം ഒരു ട്രേഡ് മാത്രം
  except Exception as e:
    print(f"Error loading {symbol}: {e}")

print("\n=== 2 MONTHS BACKTEST RESULT ===")
print(f"Total Trades: {total_trades}")
print(f"Wins (🎯 Target Hit): {wins}")
print(f"Losses (❌ SL Hit): {losses}")

if total_trades > 0:
  win_rate = round((wins / total_trades) * 100, 2)
  print(f"Win Rate: {win_rate}%")
