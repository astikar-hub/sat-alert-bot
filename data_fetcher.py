from dataclasses import dataclass
import pandas as pd
import yfinance as yf


class DataFetchError(Exception):
    pass


@dataclass(frozen=True)
class FetchConfig:
    period: str = "1y"
    interval: str = "1wk"
    auto_adjust: bool = True
    timeout_s: int = 15


class YahooFinanceClient:
    def __init__(self, config: FetchConfig | None = None):
        self.config = config or FetchConfig()

    def ensure_ns_suffix(self, symbol: str) -> str:
        symbol = symbol.strip().upper()
        if not symbol.endswith(".NS"):
            symbol = symbol + ".NS"
        return symbol

    def fetch_ohlcv(self, symbol: str) -> pd.DataFrame:
        ns_symbol = self.ensure_ns_suffix(symbol)

        try:
            frame = yf.download(
                ns_symbol,
                period=self.config.period,
                interval=self.config.interval,
                auto_adjust=self.config.auto_adjust,
                progress=False,
                timeout=self.config.timeout_s,
            )
        except Exception as e:
            raise DataFetchError(f"Download failed for {ns_symbol}: {e}")

        if frame.empty:
            raise DataFetchError(f"No data returned for {ns_symbol}")

        # Fix MultiIndex columns (new yfinance behavior)
        if isinstance(frame.columns, pd.MultiIndex):
            frame.columns = frame.columns.get_level_values(0)

        # Normalize column names
        frame.columns = [col.capitalize() for col in frame.columns]

        required = ["Open", "High", "Low", "Close", "Volume"]

        for col in required:
            if col not in frame.columns:
                raise DataFetchError(
                    f"Missing required column '{col}' for {ns_symbol}"
                )

        return frame[required]
