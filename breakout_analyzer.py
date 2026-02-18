"""Breakout detection logic for weekly timeframe."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class BreakoutRule:
    lookback_weeks: int = 20
    min_volume_ratio: float = 1.2


class BreakoutAnalyzer:
    def __init__(self, data):
        """
        Initialize the BreakoutAnalyzer with price and volume data.
        :param data: A pandas DataFrame containing price and volume information
        """
        self.data = data

    def calculate_support_resistance(self):
        """
        Calculate support and resistance levels based on historical data.
        """
        high = self.data['High'].max()
        low = self.data['Low'].min()
        # Example calculations for resistance and support levels
        self.resistance = high * 1.01  # Resistance is set slightly above the highest price
        self.support = low * 0.99        # Support is set slightly below the lowest price

    def detect_breakout(self):
        """
        Detect breakouts using calculated support and resistance levels along with volume confirmation.
        """
        latest_close = self.data['Close'].iloc[-1]
        latest_volume = self.data['Volume'].iloc[-1]
        if latest_close > self.resistance and latest_volume > self.data['Volume'].mean():
            return True  # Breakout detected
        return False  # No breakout detected

    def get_breakout_signal(self):
        """
        Returns a signal if a breakout is detected.
        """
        self.calculate_support_resistance()
        if self.detect_breakout():
            return 'Breakout Detected!'
        return 'No Breakout.'
    """Analyzes daily OHLCV and generates weekly breakout signals."""

    def __init__(self, rule: BreakoutRule | None = None):
        self.rule = rule or BreakoutRule()

    @staticmethod
    def _to_weekly(data: pd.DataFrame) -> pd.DataFrame:
        weekly = data.resample("W-FRI").agg(
            {
                "Open": "first",
                "High": "max",
                "Low": "min",
                "Close": "last",
                "Volume": "sum",
            }
        )
        return weekly.dropna()

    def evaluate(self, data: pd.DataFrame) -> dict:
        weekly = self._to_weekly(data)
        min_rows = self.rule.lookback_weeks + 2
        if len(weekly) < min_rows:
            return {
                "is_breakout": False,
                "reason": f"insufficient_data ({len(weekly)} weekly bars, need {min_rows})",
            }

        recent = weekly.iloc[-1]
        prior_window = weekly.iloc[-(self.rule.lookback_weeks + 1) : -1]

        resistance = prior_window["High"].max()
        avg_volume = prior_window["Volume"].mean()
        volume_ratio = (recent["Volume"] / avg_volume) if avg_volume else 0.0

        is_breakout = bool(
            recent["Close"] > resistance and volume_ratio >= self.rule.min_volume_ratio
        )

        return {
            "is_breakout": is_breakout,
            "close": float(recent["Close"]),
            "resistance": float(resistance),
            "volume_ratio": float(volume_ratio),
            "week_ending": str(weekly.index[-1].date()),
            "reason": "breakout" if is_breakout else "no_breakout",
        }