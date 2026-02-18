"""Alert interfaces; ready to extend with Telegram MCP sender."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class BreakoutAlert:
    symbol: str
    week_ending: str
    close: float
    resistance: float
    volume_ratio: float


class AlertSink(Protocol):
    def send(self, alert: BreakoutAlert) -> None:
        """Send a single alert to any downstream transport."""


class ConsoleAlertSink:
    """Default sink for CLI workflows."""

    def send(self, alert: BreakoutAlert) -> None:
        print(
            f"[BREAKOUT] {alert.symbol} | Week: {alert.week_ending} | "
            f"Close: {alert.close:.2f} > Resistance: {alert.resistance:.2f} | "
            f"Volume x{alert.volume_ratio:.2f}"
        )