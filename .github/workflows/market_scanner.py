import os
import datetime
import requests
import pandas as pd
import yfinance as yf
from textblob import TextBlob


# --- CONFIG ---
WATCHLIST = ['AAPL', 'TSLA', 'NVDA', 'SPY', 'QQQ']
VOLUME_THRESHOLD_MULTIPLIER = 2.0
SENTIMENT_THRESHOLD = 0.2


# --- TELEGRAM FROM GITHUB SECRETS ---
TELEGRAM_TOKEN = os.getenv("7756398872:AAHanVqt-vCA_rToXNJIHYle4CGo3JKhj34")
TELEGRAM_CHAT_ID = os.getenv("5410110707")


def send_telegram_message(message: str):
    """Send alert to Telegram bot."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram credentials missing.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}

    try:
        requests.post(url, data=payload, timeout=5)
    except Exception as e:
        print(f"Telegram error: {e}")


def get_news_sentiment(ticker: str) -> float:
    """Fetch latest news titles & compute sentiment."""
    try:
        news = yf.Ticker(ticker).news
        if not news:
            return 0

        scores = [
            TextBlob(article.get("title", "")).sentiment.polarity
            for article in news[:5]
        ]

        return sum(scores) / len(scores) if scores else 0

    except Exception:
        return 0


def check_market_conditions():
    print(f"--- Running Scan @ {datetime.datetime.now()} ---")

    for ticker in WATCHLIST:
        try:
            data = yf.download(ticker, period="1d", interval="1m", progress=False)

            if data.empty:
                continue

            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)

            last = data.iloc[-2]
            curr_vol = float(last["Volume"])
            open_p = float(last["Open"])
            close_p = float(last["Close"])

            is_green = close_p > open_p
            vol_type = "BUY" if is_green else "SELL"

            avg_vol = data["Volume"].tail(20).mean()

            vol_alert = curr_vol > (avg_vol * VOLUME_THRESHOLD_MULTIPLIER)

            sentiment = get_news_sentiment(ticker)
            news_alert = sentiment > SENTIMENT_THRESHOLD

            if vol_alert:
                icon = "🚀" if is_green else "🔻"
                msg = (
                    f"{icon} [{vol_type} ALERT] {ticker}\n"
                    f"Vol: {int(curr_vol)} (Avg: {int(avg_vol)})\n"
                    f"Price: ${close_p:.2f}"
                )
                print(msg)
                send_telegram_message(msg)

            if news_alert:
                msg = (
                    f"ℹ️ [NEWS] {ticker}\n"
                    f"Positive sentiment detected.\n"
                    f"Score: {sentiment:.2f}"
                )
                print(msg)
                send_telegram_message(msg)

        except Exception as e:
            print(f"Error scanning {ticker}: {e}")


if __name__ == "__main__":
    send_telegram_message("Scanner Online: Cloud job started.")
    check_market_conditions()
