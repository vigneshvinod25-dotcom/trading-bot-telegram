import os
import time
from datetime import datetime
from threading import Thread
from flask import Flask
import pandas as pd
import pytz
import requests
import yfinance as yf

# Render Port എറർ പരിഹരിക്കാൻ Flask സർവർ നൽകുന്നു
app = Flask("")


@app.route("/")
def home():
  return "Bot is running live!"


def run_web_server():
  port = int(os.environ.get("PORT", 10000))
  app.run(host="0.0.0.0", port=port)


# വെബ് സർവർ ബാക്ക്ഗ്രൗണ്ടിൽ സ്റ്റാർട്ട് ചെയ്യുന്നു
Thread(target=run_web_server).start()

# ടെലിഗ്രാം വിവരങ്ങൾ
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")


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


def send_telegram(msg):
  url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
  requests.post(url, data={"chat_id": CHAT_ID, "text": msg})


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


def send_trade_signal(stock_name, strategy, price):
  entry = round(price, 2)
  target = round(entry * 1.02, 2)
  sl = round(entry * 0.99, 2)

  msg = (
      f"🚨 TRADE SIGNAL: {stock_name}\n"
      f"Strategy: {strategy}\n\n"
      f"Entry: ₹{entry}\n"
      f"Target (2%): ₹{target}\n"
      f"Stop Loss (1%): ₹{sl}"
  )
  send_telegram(msg)


def scan_selected_stocks():
  global triggered_stocks
  for symbol in DYNAMIC_WATCHLIST:
    if symbol in triggered_stocks:
      continue

    try:
      ticker = yf.Ticker(symbol)
      df = ticker.history(period="1d", interval="5m")
      if len(df) < 5:
        continue

      stock_name = symbol.replace(".NS", "")
      curr_price = df["Close"].iloc[-1]
      prev_price = df["Close"].iloc[-2]

      # ORB Strategy
      orb_high = df["High"].iloc[:3].max()
      if prev_price <= orb_high and curr_price > orb_high:
        send_trade_signal(stock_name, "15-Min ORB Breakout", curr_price)
        triggered_stocks.add(symbol)
        continue

      # VWAP Strategy
      typical = (df["High"] + df["Low"] + df["Close"]) / 3
      vwap = (typical * df["Volume"]).cumsum() / df["Volume"].cumsum()
      if prev_price < vwap.iloc[-2] and curr_price > vwap.iloc[-1]:
        send_trade_signal(stock_name, "VWAP Crossover", curr_price)
        triggered_stocks.add(symbol)
    except Exception as e:
      print(f"Error: {e}")


screener_done = False
while True:
  tz = pytz.timezone("Asia/Kolkata")
  now = datetime.now(tz)

  if now.weekday() < 5:
    # 9:25 AM: വാച്ച്‌ലിസ്റ്റ് ഉണ്ടാക്കുന്നു
    if now.hour == 9 and now.minute >= 25 and not screener_done:
      run_market_analysis_and_watchlist()
      screener_done = True

    # 9:30 AM മുതൽ: വാച്ച്‌ലിസ്റ്റ് സ്റ്റോക്കുകൾ സ്കാൻ ചെയ്യുന്നു
    if now.hour >= 9 and now.minute >= 30 and DYNAMIC_WATCHLIST:
      scan_selected_stocks()

    # വൈകുന്നേരം 4 മണിക്ക് റീസെറ്റ് ചെയ്യുന്നു
    if now.hour >= 16:
      screener_done = False
      DYNAMIC_WATCHLIST = []
      triggered_stocks = set()

  time.sleep(300)
