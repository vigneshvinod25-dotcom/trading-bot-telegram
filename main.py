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

print("⏳ എല്ലാ ഡാറ്റയും ഒന്നിച്ച് ഡൗൺലോഡ് ചെയ്യുന്നു...")

# ഒരൊറ്റ റിക്വസ്റ്റിൽ ബാച്ച് ഡൗൺലോഡ് ചെയ്യുന്നു
data = yf.download(
    NIFTY_STOCKS, period="60d", interval="5m", group_by="ticker", threads=True
)

print("📊 ബാക്ക്ടെസ്റ്റിംഗ് ആരംഭിക്കുന്നു...")

for symbol in NIFTY_STOCKS:
  try:
    if symbol not in data.columns.levels[0]:
      continue

    df = data[symbol].dropna()
    if df.empty or len(df) < 100:
      continue

    df["EMA200"] = df["Close"].ewm(span=200, adjust=False).mean()
    df["Vol_Avg"] = df["Volume"].rolling(20).mean()
    df["Date"] = df.index.date

    for date, day_df in df.groupby("Date"):
      if len(day_df) < 15:
        continue

      open_price = day_df["Open"].iloc[0]
      price_925 = day_df["Close"].iloc[2]
      gain = ((price_925 - open_price) / open_price) * 100

      if gain < 0.3:
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

            if future["High"].max() >= target:
              wins += 1
            elif future["Low"].min() <= sl:
              losses += 1

            break
  except Exception:
    pass

print("\n=== 2 MONTHS BACKTEST RESULT ===")
print(f"Total Trades: {total_trades}")
print(f"Wins: {wins}")
print(f"Losses: {losses}")

if total_trades > 0:
  win_rate = round((wins / total_trades) * 100, 2)
  print(f"Win Rate: {win_rate}%")
