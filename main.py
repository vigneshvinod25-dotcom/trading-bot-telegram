import os
import time
from datetime import datetime
from threading import Thread
from flask import Flask
import pandas as pd
import pytz
import requests
import yfinance as yf

# Render Port എറർ ഒഴിവാക്കാൻ Flask സർവർ
app = Flask("")


@app.route("/")
def home():
  return "Bot is running live!"


def run_web_server():
  port = int(os.environ.get("PORT", 10000))
  app.run(host="0.0.0.0", port=port)


Thread(target=run_web_server).start()

# ടെലിഗ്രാം വിവരങ്ങൾ
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")


def send_telegram(msg):
  url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
  requests.post(url, data={"chat_id": CHAT_ID, "text": msg})


def get_nifty50_universe():
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


NIFTY_UNIVERSE = get_nifty50_universe()
DYNAMIC_WATCHLIST = []
triggered_stocks = set()
trade_history = []  # ട്രേഡുകൾ സേവ് ചെയ്യാൻ


def run_market_analysis_and_watchlist():
  global DYNAMIC_WATCHLIST
  DYNAMIC_WATCHLIST = []

  send_telegram("📊 Nifty 50 മാർക്കറ്റ് വിശകലനം നടക്കുന്നു...")

  for symbol in NIFTY_UNIVERSE:
    try:
      ticker = yf.Ticker(symbol)
      df = ticker.history(period="1d", interval="5m")
      if len(df) >= 2:
        change = (
            (df["Close"].iloc[-1] - df["Open"].iloc[0]) / df["Open"].iloc[0]
        ) * 100
        if change >= 0.3:
          DYNAMIC_WATCHLIST.append(symbol)
    except Exception:
      pass

  if DYNAMIC_WATCHLIST:
    names = ", ".join([s.replace(".NS", "") for s in DYNAMIC_WATCHLIST])
    send_telegram(
        f"📋 വാച്ച്‌ലിസ്റ്റ് ({len(DYNAMIC_WATCHLIST)} സ്റ്റോക്കുകൾ):\n{names}\n\nഈ"
        " സ്റ്റോക്കുകളിൽ മാത്രം സിഗ്നലുകൾ നോക്കുന്നു."
    )
  else:
    send_telegram("ഇന്ന് വാച്ച്‌ലിസ്റ്റിൽ സ്റ്റോക്കുകൾ ലഭ്യമല്ല.")


def send_trade_signal(stock_name, strategy, price, symbol):
  entry = round(price, 2)
  target = round(entry * 1.01, 2)  # 1% Target
  sl = round(entry * 0.995, 2)  # 0.5% Stop Loss

  # ട്രേഡ് വിവരങ്ങൾ സേവ് ചെയ്യുന്നു
  trade_history.append({
      "symbol": symbol,
      "stock": stock_name,
      "entry": entry,
      "target": target,
      "sl": sl,
      "strategy": strategy,
  })

  msg = (
      f"🚨 HIGH QUALITY SIGNAL: {stock_name}\n"
      f"Strategy: {strategy}\n\n"
      f"Entry: ₹{entry}\n"
      f"Target (1%): ₹{target}\n"
      f"Stop Loss (0.5%): ₹{sl}"
  )
  send_telegram(msg)


def scan_selected_stocks():
  global triggered_stocks
  for symbol in DYNAMIC_WATCHLIST:
    if symbol in triggered_stocks:
      continue

    try:
      ticker = yf.Ticker(symbol)
      df = ticker.history(period="5d", interval="5m")
      if len(df) < 50:
        continue

      stock_name = symbol.replace(".NS", "")
      curr_price = df["Close"].iloc[-1]
      prev_price = df["Close"].iloc[-2]

      # 1. Volume Filter
      curr_vol = df["Volume"].iloc[-1]
      avg_vol = df["Volume"].iloc[-20:].mean()
      volume_ok = curr_vol > (avg_vol * 1.2)

      # 2. 200 EMA Filter
      df["EMA200"] = df["Close"].ewm(span=200, adjust=False).mean()
      ema_ok = curr_price > df["EMA200"].iloc[-1]

      if volume_ok and ema_ok:
        # ORB Strategy
        orb_high = df["High"].iloc[:3].max()
        if prev_price <= orb_high and curr_price > orb_high:
          send_trade_signal(
              stock_name, "15-Min ORB + Vol + 200 EMA", curr_price, symbol
          )
          triggered_stocks.add(symbol)
          continue

        # VWAP Strategy
        typical = (df["High"] + df["Low"] + df["Close"]) / 3
        vwap = (typical * df["Volume"]).cumsum() / df["Volume"].cumsum()
        if prev_price < vwap.iloc[-2] and curr_price > vwap.iloc[-1]:
          send_trade_signal(
              stock_name, "VWAP Crossover + Vol + 200 EMA", curr_price, symbol
          )
          triggered_stocks.add(symbol)
    except Exception as e:
      print(f"Error: {e}")


def send_end_of_day_report():
  if not trade_history:
    send_telegram("📅 END OF DAY REPORT:\nഇന്ന് ട്രേഡുകളൊന്നും ഉണ്ടായിരുന്നില്ല.")
    return

  total_trades = len(trade_history)
  wins = 0
  losses = 0
  pending = 0
  details = ""

  for trade in trade_history:
    try:
      ticker = yf.Ticker(trade["symbol"])
      df = ticker.history(period="1d", interval="5m")
      if not df.empty:
        max_high = df["High"].max()
        min_low = df["Low"].min()

        if max_high >= trade["target"]:
          wins += 1
          status = "✅ TARGET HIT"
        elif min_low <= trade["sl"]:
          losses += 1
          status = "❌ SL HIT"
        else:
          pending += 1
          status = "⏳ OPEN / NO TARGET"

        details += f"• {trade['stock']}: {status} (Entry: ₹{trade['entry']})\n"
    except Exception:
      details += f"• {trade['stock']}: Data Error\n"

  report = (
      f"📊 END OF DAY REPORT 📊\n\n"
      f"Total Trades: {total_trades}\n"
      f"Wins (🎯): {wins}\n"
      f"Losses (❌): {losses}\n"
      f"Open (⏳): {pending}\n\n"
      f"Details:\n{details}"
  )
  send_telegram(report)


# ബോട്ട് സ്റ്റാർട്ടപ്പ് മെസ്സേജ്
try:
  send_telegram("🚀 Bot active. EOD Summary report enabled!")
except Exception as e:
  print(f"Startup Message Error: {e}")

screener_done = False
summary_sent = False

while True:
  tz = pytz.timezone("Asia/Kolkata")
  now = datetime.now(tz)

  if now.weekday() < 5:
    # 9:25 AM: വാച്ച്‌ലിസ്റ്റ്
    if now.hour == 9 and now.minute >= 25 and not screener_done:
      run_market_analysis_and_watchlist()
      screener_done = True

    # 9:30 AM: സ്കാനിംഗ്
    if now.hour >= 9 and now.minute >= 30 and DYNAMIC_WATCHLIST:
      scan_selected_stocks()

    # 3:30 PM: റിസൾട്ട് റിപ്പോർട്ട് അയക്കുന്നു
    if now.hour == 15 and now.minute >= 30 and not summary_sent:
      send_end_of_day_report()
      summary_sent = True

    # 4 PM: റീസെറ്റ്
    if now.hour >= 16:
      screener_done = False
      summary_sent = False
      DYNAMIC_WATCHLIST = []
      triggered_stocks = set()
      trade_history = []

  time.sleep(300)
