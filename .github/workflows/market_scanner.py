import sys
import yfinance as yf
from textblob import TextBlob
import pandas as pd
import schedule
import time
import datetime
import requests

# --- CONFIGURATION (FILL THESE IN) ---
TELEGRAM_TOKEN = "7756398872:AAHanVqt-vCA_rToXNJIHYle4CGo3JKhj34"
TELEGRAM_CHAT_ID = "5410110707"

WATCHLIST = ['AAPL', 'TSLA', 'NVDA', 'SPY', 'QQQ']
VOLUME_THRESHOLD_MULTIPLIER = 2.0
SENTIMENT_THRESHOLD = 0.2

def send_telegram_message(message):
    """Sends a text to your phone via Telegram"""
    if TELEGRAM_TOKEN == "PASTE_YOUR_TOKEN_HERE":
        # Silent fail if not configured, just to keep the loop running
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print(f"Error sending text: {e}")

def get_news_sentiment(ticker):
    try:
        stock = yf.Ticker(ticker)
        news = stock.news
        if not news: return 0

        sentiment_scores = []
        for article in news[:5]:
            blob = TextBlob(article.get('title', ''))
            sentiment_scores.append(blob.sentiment.polarity)

        if sentiment_scores:
            return sum(sentiment_scores) / len(sentiment_scores)
    except Exception:
        pass
    return 0

def check_market_conditions():
    print(f"--- Scanning Market: {datetime.datetime.now().strftime('%H:%M:%S')} ---")

    for ticker in WATCHLIST:
        try:
            # 1. Get Intraday Data
            data = yf.download(ticker, period='1d', interval='1m', progress=False, auto_adjust=True)

            if data.empty:
                continue

            # Flatten columns if needed (The Fix)
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)

            # Get the last completed minute candle
            # Use -2 to get the last *completed* candle, as the last one might be partial
            if len(data) < 2: # Ensure there are at least 2 candles to avoid IndexError
                continue

            last_candle = data.iloc[-2]
            current_volume = float(last_candle['Volume'])

            # Get Price Action
            open_price = float(last_candle['Open'])
            close_price = float(last_candle['Close'])

            # DETERMINING BUY VS SELL VOLUME
            is_green_candle = close_price > open_price
            volume_type = "BUY" if is_green_candle else "SELL"

            # Calculate Average Volume (last 20 minutes)
            # Ensure there are enough data points for average volume
            avg_volume_data = data['Volume'].tail(20)
            if len(avg_volume_data) < 20: # If less than 20 min data, use all available
                avg_volume = avg_volume_data.mean()
            else:
                avg_volume = avg_volume_data.iloc[:-1].mean() # Exclude current minute from average


            # 2. Check for Volume Anomaly
            vol_alert = False
            if avg_volume > 0 and current_volume > (avg_volume * VOLUME_THRESHOLD_MULTIPLIER):
                vol_alert = True

            # 3. Check for Sentiment
            sentiment_score = get_news_sentiment(ticker)
            news_alert = False
            if sentiment_score > SENTIMENT_THRESHOLD:
                news_alert = True

            # 4. TRIGGER LOGIC WITH BUY/SELL CONTEXT & TELEGRAM ALERTS
            if vol_alert:
                # Determine direction icon
                icon = "🚀" if volume_type == "BUY" else "🔻"

                # Create message
                msg = (f"{icon} [{volume_type} ALERT] {ticker}\n"
                       f"Vol: {int(current_volume)} (Avg: {int(avg_volume)})\n"
                       f"Price: ${close_price:.2f}")

                # Print to console
                print(msg)
                # Send to Phone
                send_telegram_message(msg)

            if news_alert:
                msg = (f"ℹ️ [NEWS INFO] {ticker}\n"
                       f"Positive Sentiment Detected.\n"
                       f"Score: {sentiment_score:.2f}")

                print(msg)
                send_telegram_message(msg)

        except Exception as e:
            print(f"Error scanning {ticker}: {e}")

# Send a test message on startup
send_telegram_message("System Online: Market Scanner is running.")

# Schedule the scanner to run every 1 minute
schedule.every(1).minutes.do(check_market_conditions)

print("System Initialized. Searching for early signals...")

# Run loop
while True:
    schedule.run_pending()
    time.sleep(1)
