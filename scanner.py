import yfinance as yf
import pandas as pd
import argparse
import requests
from pathlib import Path
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
# CONFIG
# ===============================

CSV_PATH = "nifty200.csv"
WEEKS_LOOKBACK = 20
VOLUME_MULTIPLIER = 1.2
ALERT_LOG_FILE = "sent_alerts.csv"

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

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }

    try:
        response = requests.post(url, data=payload)

        if response.status_code != 200:
            print("\nTelegram error:", response.text)

    except Exception as e:
        print("\nTelegram sending failed:", e)

# ===============================
# DUPLICATE ALERT CONTROL
# ===============================

def load_sent_alerts():
    if os.path.exists(ALERT_LOG_FILE):
        return pd.read_csv(ALERT_LOG_FILE)
    else:
        return pd.DataFrame(columns=["Symbol", "Year", "Week"])


def auto_reset_weekly(current_year, current_week):
    alerts_df = load_sent_alerts()

    if alerts_df.empty:
        return alerts_df

    filtered = alerts_df[
        (alerts_df["Year"] == current_year) &
        (alerts_df["Week"] == current_week)
    ]

    filtered.to_csv(ALERT_LOG_FILE, index=False)
    return filtered


def save_sent_alert(symbol, year, week):
    new_entry = pd.DataFrame([[symbol, year, week]], columns=["Symbol", "Year", "Week"])

    if os.path.exists(ALERT_LOG_FILE):
        existing = pd.read_csv(ALERT_LOG_FILE)
        updated = pd.concat([existing, new_entry], ignore_index=True)
    else:
        updated = new_entry

    updated.to_csv(ALERT_LOG_FILE, index=False)


def already_alerted(symbol, year, week):
    alerts_df = load_sent_alerts()
    match = alerts_df[
        (alerts_df["Symbol"] == symbol) &
        (alerts_df["Year"] == year) &
        (alerts_df["Week"] == week)
    ]
    return not match.empty

# ===============================
# DATA FETCH
# ===============================

def fetch_weekly_data(symbol):
    ticker = yf.Ticker(symbol + ".NS")
    df = ticker.history(period="2y", interval="1wk")

    if df.empty:
        return None

    df = df.rename(columns=str.title)
    return df

# ===============================
# BREAKOUT LOGIC
# ===============================

def check_weekly_breakout(df):
    if len(df) < WEEKS_LOOKBACK + 1:
        return False, None, None, None

    previous_high = df["High"].rolling(WEEKS_LOOKBACK).max().shift(1)
    avg_volume = df["Volume"].rolling(WEEKS_LOOKBACK).mean()

    last_row = df.iloc[-1]

    breakout = (
        last_row["Close"] > previous_high.iloc[-1]
        and last_row["Volume"] > avg_volume.iloc[-1] * VOLUME_MULTIPLIER
    )

    return breakout, previous_high.iloc[-1], last_row["Close"], last_row["Volume"]

# ===============================
# MAIN
# ===============================

def main():
    global loading

    parser = argparse.ArgumentParser()
    parser.add_argument("--max-symbols", type=int, help="Limit number of symbols")
    parser.add_argument("--symbol", type=str, help="Check single symbol")
    args = parser.parse_args()

    print("\n===================================")
    print(" SAT ENGINE – WEEKLY CONFIRMED BUY")
    print("===================================\n")

    symbols = []

    if args.symbol:
        symbols = [args.symbol.upper()]
    else:
        try:
            df_symbols = pd.read_csv(CSV_PATH)
            symbols = df_symbols.iloc[:, 0].dropna().tolist()
        except Exception as e:
            print("Error loading CSV:", e)
            return

        if args.max_symbols:
            symbols = symbols[:args.max_symbols]

    current_date = datetime.now()
    current_year = current_date.year
    current_week = current_date.isocalendar()[1]

    auto_reset_weekly(current_year, current_week)

    # 🔥 Start loading animation thread
    loading_thread = threading.Thread(target=show_loading)
    loading_thread.start()

    results = []

    for symbol in symbols:
        df = fetch_weekly_data(symbol)
        if df is None:
            continue

        breakout, prev_high, close, volume = check_weekly_breakout(df)

        if breakout:
            if already_alerted(symbol, current_year, current_week):
                continue

            results.append(symbol)

            timestamp = current_date.strftime("%d-%m-%Y %H:%M")

            message = (
                f"🚀 SAT WEEKLY BREAKOUT ALERT\n\n"
                f"Stock: {symbol}\n"
                f"Close: {close:.2f}\n"
                f"20W High: {prev_high:.2f}\n"
                f"Volume: {volume:.0f}\n"
                f"Time: {timestamp}"
            )

            send_telegram_message(message)
            save_sent_alert(symbol, current_year, current_week)

    # 🔥 Stop loading animation
    loading = False
    loading_thread.join()

    print("\n\nScan completed.\n")

    if results:
        print("New BUY signals:")
        for r in results:
            print(f" - {r}")
    else:
        print("No new SAT BUY signals found.\n")


if __name__ == "__main__":
    main()
