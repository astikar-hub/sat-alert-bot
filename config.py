"""
Configuration and symbol universe utilities for Nifty 200 scanning.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List

import pandas as pd

# ==============================
# TELEGRAM CONFIGURATION (FROM ENV VARIABLES)
# ==============================

# These will be read from Render Environment Variables
# Do NOT hardcode token or chat ID here

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    raise ValueError("Telegram credentials are missing. Check environment variables.")

# ==============================
# NIFTY 200 CONFIGURATION
# ==============================

NIFTY200_CSV_URL = "https://www.niftyindices.com/IndexConstituent/ind_nifty200list.csv"

# Fallback basket if online constituent fetch is unavailable.
FALLBACK_SYMBOLS = [
    "RELIANCE",
    "TCS",
    "HDFCBANK",
    "INFY",
    "ICICIBANK",
    "KOTAKBANK",
    "LT",
    "SBIN",
    "BHARTIARTL",
    "HINDUNILVR",
]


@dataclass(frozen=True)
class ScannerSettings:
    lookback_weeks: int = 20
    min_volume_ratio: float = 1.2
    max_symbols: int | None = None


def load_nifty200_symbols() -> List[str]:
    """Load Nifty 200 constituent symbols from NSE index CSV, with safe fallback."""
    try:
        table = pd.read_csv(NIFTY200_CSV_URL)

        symbol_col = next(
            (c for c in table.columns if c.strip().lower() == "symbol"),
            None
        )

        if not symbol_col:
            raise ValueError("symbol column not found")

        symbols = (
            table[symbol_col]
            .dropna()
            .astype(str)
            .str.strip()
            .str.upper()
            .unique()
            .tolist()
        )

        return symbols or FALLBACK_SYMBOLS

    except Exception:
        return FALLBACK_SYMBOLS
