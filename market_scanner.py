import sys
import os
import yfinance as yf
from textblob import TextBlob
import pandas as pd
import time
import datetime
import requests

# --- CONFIGURATION ---
# Read from GitHub Secrets (Environment Variables)
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

WATCHLIST = ['AAPL', 'TSLA', 'NVDA', 'SPY', 'QQQ']
VOLUME_THRESHOLD_MULTIPLIER = 2.0
SENTIMENT_THRESHOLD = 0.2

def send_telegram_message(message):
    """Sends a text to your phone via Telegram"""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Error: Telegram tokens not found in Environment Variables.")
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
                print(f"No data for {ticker}")
                continue

            # Flatten columns if needed
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)

            # Ensure we have enough data
            if len(data) < 20: 
                continue

            last_candle = data.iloc[-2] # Last completed candle
            current_volume = float(last_candle['Volume'])

            open_price = float(last_candle['Open'])
            close_price = float(last_candle['Close'])

            is_green_candle = close_price > open_price
            volume_type = "BUY" if is_green_candle else "SELL"

            # Calculate Average Volume (last 20 minutes excluding current)
            avg_volume = data['Volume'].iloc[-22:-2].mean()

            # 2. Check for Volume Anomaly
            vol_alert = False
            if avg_volume > 0 and current_volume > (avg_volume * VOLUME_THRESHOLD_MULTIPLIER):
                vol_alert = True
                print(f"Volume Alert found for {ticker}")

            # 3. Check for Sentiment
            sentiment_score = get_news_sentiment(ticker)
            news_alert = False
            if sentiment_score > SENTIMENT_THRESHOLD:
                news_alert = True

            # 4. TRIGGER LOGIC
            if vol_alert:
                icon = "🚀" if volume_type == "BUY" else "🔻"
                msg = (f"{icon} [{volume_type} ALERT] {ticker}\n"
                       f"Vol: {int(current_volume)} (Avg: {int(avg_volume)})\n"
                       f"Price: ${close_price:.2f}")
                print(msg)
                send_telegram_message(msg)

            if news_alert:
                msg = (f"ℹ️ [NEWS INFO] {ticker}\n"
                       f"Positive Sentiment Detected.\n"
                       f"Score: {sentiment_score:.2f}")
                print(msg)
                send_telegram_message(msg)

        except Exception as e:
            print(f"Error scanning {ticker}: {e}")

# Run ONCE and exit. The GitHub YAML handles the loop.
if __name__ == "__main__":
    check_market_conditions()
