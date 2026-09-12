import pandas as pd
import yfinance as yf


# Nifty 50 സ്റ്റോക്കുകൾ കണ്ടെത്തുന്ന ഫംഗ്ഷൻ
def get_nifty50_list():
  try:
    url = "https://en.wikipedia.org/wiki/NIFTY_50"
    tables = pd.read_html(url)
    for df in tables:
      if "Symbol" in df.columns:
        return [f"{symbol}.NS" for symbol in df["Symbol"].dropna()]
  except Exception:
    pass

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

print(f"⏳ {len(NIFTY_STOCKS)} Nifty 50 സ്റ്റോക്കുകൾ സ്കാൻ ചെയ്യുന്നു...")

for symbol in NIFTY_STOCKS:
  try:
    # 60 ദിവസം (2 മാസം) 5 മിനിറ്റ് ഡാറ്റ
    df = yf.download(symbol, period="60d", interval="5m", progress=False)

    if df.empty or len(df) < 100:
      continue

    # EMA 200 & Volume MA
    df["EMA200"] = df["Close"].ewm(span=200, adjust=False).mean()
    df["Vol_Avg"] = df["Volume"].rolling(20).mean()
    df["Date"] = df.index.date

    # ഓരോ ദിവസത്തെയും ഡാറ്റ പരിശോധിക്കുന്നു
    for date, day_df in df.groupby("Date"):
      if len(day_df) < 15:
        continue

      # 1. 9:25 AM വാച്ച്‌ലിസ്റ്റ് ഫിൽട്ടർ (0.3% Gain)
      open_price = day_df["Open"].iloc[0]
      price_925 = day_df["Close"].iloc[2]
      gain = ((price_925 - open_price) / open_price) * 100

      if gain < 0.3:
        continue  # 0.3% ഗെയിൻ ഇല്ലെങ്കിൽ ഒഴിവാക്കുന്നു

      # 2. ORB High (ആദ്യ 15 മിനിറ്റ്)
      orb_high = day_df["High"].iloc[:3].max()

      # 3. VWAP
      typical = (day_df["High"] + day_df["Low"] + day_df["Close"]) / 3
      vwap = (typical * day_df["Volume"]).cumsum() / day_df["Volume"].cumsum()

      # 9:30 AM - 3:30 PM ട്രേഡ് സ്കാനിംഗ്
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
            sl = entry * 0.995  # 0.5% Stop Loss

            future = day_df.iloc[i + 1 :]
            total_trades += 1

            if future["High"].max() >= target:
              wins += 1
            elif future["Low"].min() <= sl:
              losses += 1

            break  # ഒരു ദിവസം ഒരു സ്റ്റോക്കിൽ ഒരു ട്രേഡ് മാത്രം
  except Exception:
    pass

print("\n=== 2 MONTH FULL NIFTY 50 BACKTEST RESULT ===")
print(f"Total Trades: {total_trades}")
print(f"Wins (🎯 Target Hit): {wins}")
print(f"Losses (❌ SL Hit): {losses}")

if total_trades > 0:
  win_rate = round((wins / total_trades) * 100, 2)
  print(f"Win Rate: {win_rate}%")
