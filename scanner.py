import os

print("TOKEN:", os.getenv("TELEGRAM_TOKEN"))
print("CHAT:", os.getenv("CHAT_ID"))

from telegram_alerts import send_telegram_message

send_telegram_message("TEST MESSAGE FROM GITHUB ACTION – ASTIKAR")

import yfinance as yf
import pandas as pd
import argparse
import requests
from datetime import datetime
import os
import threading
import time
import sys

# ===============================
# IMPORT TELEGRAM CONFIG
# ===============================
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

# ===============================
# CONFIGURATION
# ===============================
CSV_PATH = "nifty200.csv"
WEEKS_LOOKBACK = 20
VOLUME_MULTIPLIER = 1.2
ALERT_LOG_FILE = "sent_alerts.csv"
RETRY_YFINANCE = 3
RETRY_TELEGRAM = 3

# ===============================
# LOADING ANIMATION
# ===============================
loading = True

def show_loading():
    dots = 0
    while loading:
        dots = (dots % 3) + 1
        sys.stdout.write("\rProcessing data" + "." * dots + "   ")
        sys.stdout.flush()
        time.sleep(0.5)

# ===============================
# TELEGRAM ALERT FUNCTION
# ===============================
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    print("Sending Telegram message...")
    print("URL:", url)
    print("Payload:", payload)
    try:
        response = requests.post(url, data=payload, timeout=5)
        print("Response:", response.status_code, response.text)
        return response.status_code == 200
    except Exception as e:
        print("Telegram send failed:", e)
        return False

# ===============================
# DUPLICATE ALERT MANAGEMENT
# ===============================
def load_sent_alerts():
    if os.path.exists(ALERT_LOG_FILE):
        return pd.read_csv(ALERT_LOG_FILE)
    return pd.DataFrame(columns=["Symbol", "Year", "Week"])

def save_sent_alert(symbol, year, week):
    new_entry = pd.DataFrame([[symbol, year, week]], columns=["Symbol", "Year", "Week"])
    if os.path.exists(ALERT_LOG_FILE):
        df = pd.read_csv(ALERT_LOG_FILE)
        df = pd.concat([df, new_entry], ignore_index=True)
    else:
        df = new_entry
    df.to_csv(ALERT_LOG_FILE, index=False)

def already_alerted(symbol, year, week):
    df = load_sent_alerts()
    return not df[(df["Symbol"] == symbol) & (df["Year"] == year) & (df["Week"] == week)].empty

def auto_reset_weekly(current_year, current_week):
    if not os.path.exists(ALERT_LOG_FILE):
        return
    df = pd.read_csv(ALERT_LOG_FILE)
    # Keep only current week alerts
    df = df[(df["Year"] == current_year) & (df["Week"] == current_week)]
    df.to_csv(ALERT_LOG_FILE, index=False)

# ===============================
# FETCH WEEKLY DATA
# ===============================
def fetch_weekly_data(symbol):
    for _ in range(RETRY_YFINANCE):
        ticker = yf.Ticker(symbol + ".NS")
        df = ticker.history(period="2y", interval="1wk")
        if not df.empty:
            return df.rename(columns=str.title)
        time.sleep(1)
    print(f"Data fetch failed for {symbol}")
    return None

# ===============================
# WEEKLY BREAKOUT LOGIC
# ===============================
def check_weekly_breakout(df):
    if len(df) < WEEKS_LOOKBACK + 1:
        return False, None, None, None

    previous_high = df["High"].rolling(WEEKS_LOOKBACK).max().shift(1)
    avg_volume = df["Volume"].rolling(WEEKS_LOOKBACK).mean()
    last_row = df.iloc[-1]

    breakout = last_row["Close"] > previous_high.iloc[-1] and last_row["Volume"] > avg_volume.iloc[-1] * VOLUME_MULTIPLIER
    return breakout, previous_high.iloc[-1], last_row["Close"], last_row["Volume"]

# ===============================
# MAIN FUNCTION
# ===============================
def main():
    global loading

    parser = argparse.ArgumentParser(description="SAT Engine - Weekly Confirmed Buy Scanner")
    parser.add_argument("--max-symbols", type=int, help="Limit number of symbols to scan")
    parser.add_argument("--symbol", type=str, help="Scan single symbol only")
    args = parser.parse_args()

    print("\n===================================")
    print(" SAT ENGINE – WEEKLY CONFIRMED BUY")
    print("===================================\n")

    symbols = []

    # Load symbols
    if args.symbol:
        symbols = [args.symbol.strip().upper()]
    else:
        try:
            df_symbols = pd.read_csv(CSV_PATH)
            symbols = [s.strip().upper() for s in df_symbols.iloc[:, 0].dropna()]
        except Exception as e:
            print("Error loading CSV:", e)
            return
        if args.max_symbols:
            symbols = symbols[:args.max_symbols]

    current_date = datetime.now()
    current_year = current_date.year
    current_week = current_date.isocalendar()[1]

    auto_reset_weekly(current_year, current_week)

    # Start loading animation
    loading_thread = threading.Thread(target=show_loading)
    loading_thread.start()

    results = []

    try:
        for symbol in symbols:
            df = fetch_weekly_data(symbol)
            if df is None:
                continue

            breakout, prev_high, close, volume = check_weekly_breakout(df)
            if breakout and not already_alerted(symbol, current_year, current_week):
                results.append(symbol)
                message = (
                    f"🚀 SAT WEEKLY BREAKOUT ALERT\n\n"
                    f"Stock: {symbol}\n"
                    f"Close: {close:.2f}\n"
                    f"20W High: {prev_high:.2f}\n"
                    f"Volume: {volume:.0f}\n"
                    f"Time: {current_date.strftime('%d-%m-%Y %H:%M')}"
                )
                send_telegram_message(message)
                save_sent_alert(symbol, current_year, current_week)
    finally:
        loading = False
        loading_thread.join()

    # Print summary
    print("\n\nScan completed.\n")
    if results:
        print("New BUY signals:")
        for r in results:
            print(f" - {r}")
    else:
        print("No new SAT BUY signals found.\n")

# ===============================
# ENTRY POINT
# ===============================
if __name__ == "__main__":
    main()
