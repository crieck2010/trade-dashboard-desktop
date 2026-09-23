"""Local stdlib-only service implementations.

These mirror :mod:`trade_dashboard_web.engine` one-for-one (same function
names and signatures) so the desktop behaves identically whether or not the
web dashboard package is installed.  When ``trade_dashboard_web`` *is*
installed, :mod:`trade_dashboard_desktop.engine` binds these names to the
web engine instead, keeping a single source of truth in a meta-install.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone


# ---------------------------------------------------------------------------
# Market data
# ---------------------------------------------------------------------------

def bar_to_dict(bar) -> dict:
    """Normalize a dict-like or engine ``Bar`` to a plain dict."""
    if isinstance(bar, dict):
        ts = bar.get("timestamp")
        return {
            "symbol": bar.get("symbol", ""),
            "timestamp": ts.isoformat() if hasattr(ts, "isoformat") else str(ts),
            "open": float(bar.get("open", 0.0)),
            "high": float(bar.get("high", 0.0)),
            "low": float(bar.get("low", 0.0)),
            "close": float(bar.get("close", 0.0)),
            "volume": float(bar.get("volume", 0.0)),
        }
    ts = getattr(bar, "timestamp", None)
    return {
        "symbol": getattr(bar, "symbol", "") or "",
        "timestamp": ts.isoformat() if hasattr(ts, "isoformat") else str(ts),
        "open": float(bar.open),
        "high": float(bar.high),
        "low": float(bar.low),
        "close": float(bar.close),
        "volume": float(getattr(bar, "volume", 0.0) or 0.0),
    }


def synth_bars(symbol: str, n: int = 250, start: float = 100.0, seed: int = 7) -> list[dict]:
    """Deterministic demo bars with three regimes (up / chop / down)."""
    rng = random.Random(seed + abs(hash(symbol)) % 997)
    bars, price = [], start
    t = datetime(2024, 1, 2, tzinfo=timezone.utc)
    for i in range(n):
        drift = 0.003 if i < n * 0.4 else (-0.001 if i < n * 0.7 else -0.003)
        o = price
        c = o * (1 + drift + rng.uniform(-0.02, 0.02))
        bars.append(
            {
                "symbol": symbol,
                "timestamp": t.isoformat(),
                "open": o,
                "high": max(o, c) * 1.005,
                "low": min(o, c) * 0.995,
                "close": c,
                "volume": 2_000_000.0,
            }
        )
        price, t = c, t + timedelta(days=1)
    return bars


class DataService:
    """Fetch bars from the configured sources (``demo`` always works)."""

    SOURCES = ("demo", "equities")

    def sources(self) -> list[dict]:
        out = [{"id": "demo", "label": "Demo (synthetic, offline)", "available": True}]
        try:
            import trade_data_equities  # noqa: F401

            available, note = True, "Delayed data via trade-data-equities (yfinance)"
        except ImportError:
            available, note = False, "Install trade-data-equities for real data"
        out.append(
            {"id": "equities", "label": "Equities (delayed)",
             "available": available, "note": note}
        )
        return out

    def get_bars(self, symbol: str, source: str = "demo", days: int = 365) -> list[dict]:
        symbol = (symbol or "").strip().upper()
        if not symbol:
            raise ValueError("symbol is required")
        if source == "demo":
            return synth_bars(symbol, n=max(60, min(days, 750)))
        if source == "equities":
            return self._equities_bars(symbol, days)
        raise ValueError(f"unknown source {source!r}; choose from demo, equities")

    def _equities_bars(self, symbol: str, days: int) -> list[dict]:
        try:
            from trade_data_equities import EquitiesDataClient, Timeframe
            from trade_data_equities.providers.yfinance import YFinanceProvider
        except ImportError as exc:
            raise RuntimeError(
                "the equities source needs the trade-data-equities package "
                "(and yfinance) installed"
            ) from exc
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=max(30, days))
        client = EquitiesDataClient(YFinanceProvider())
        bars = client.get_bars(symbol, Timeframe.DAILY, start, end, use_cache=True)
        out = [bar_to_dict(b) for b in bars]
        for b in out:
            b["symbol"] = symbol
        if not out:
            raise RuntimeError(f"no bars returned for {symbol}")
        return out


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

def list_strategies() -> list[dict]:
    try:
        from trade_strategies.registry import describe_strategies
    except ImportError as exc:
        raise RuntimeError(
            "the strategy catalog needs the trade-strategies package installed"
        ) from exc
    return describe_strategies()


def describe_strategy(name: str) -> dict:
    for desc in list_strategies():
        if desc["name"] == name:
            return desc
    raise KeyError(f"unknown strategy {name!r}")


# ---------------------------------------------------------------------------
# Backtesting
# ---------------------------------------------------------------------------

def run_backtest_job(
    strategy_name: str,
    symbols: list[str],
    params: dict | None,
    bars: list,
    initial_cash: float = 100_000.0,
) -> dict:
    """Backtest ``strategy_name`` over ``bars``; return plain-data results."""
    try:
        from trade_strategies import get_strategy
        from trade_strategies.adapters import run_backtest
    except ImportError as exc:
        raise RuntimeError(
            "backtests need the trade-strategies and trade-backtest packages installed"
        ) from exc

    if not symbols:
        raise ValueError("at least one symbol is required")
    strategy = get_strategy(strategy_name)(list(symbols), **(params or {}))
    result = run_backtest(strategy, bars, initial_cash=initial_cash)

    curve = [
        {"timestamp": _iso(p.timestamp), "equity": p.equity, "cash": p.cash}
        for p in result.equity_curve
    ]
    trades = [
        {
            "symbol": t.symbol,
            "entry_time": _iso(t.entry_time),
            "exit_time": _iso(t.exit_time),
            "quantity": t.quantity,
            "entry_price": t.entry_price,
            "exit_price": t.exit_price,
            "pnl": t.pnl,
            "return_pct": t.return_pct,
        }
        for t in result.trades
    ]
    return {
        "strategy": strategy_name,
        "symbols": list(symbols),
        "params": params or {},
        "initial_cash": initial_cash,
        "final_equity": result.final_equity,
        "metrics": {k: float(v) for k, v in result.metrics.items()},
        "equity_curve": curve,
        "trades": trades,
    }


def _iso(value) -> str:
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


# ---------------------------------------------------------------------------
# Agent desk
# ---------------------------------------------------------------------------

def run_desk_job(
    symbols: list[str], bars_by_symbol: dict[str, list], equity: float = 100_000.0
) -> dict:
    """Run ``trade_agents.default_desk`` over the given bars; plain-data report."""
    try:
        from trade_agents import DictBarsProvider, default_desk
    except ImportError as exc:
        raise RuntimeError(
            "the desk needs the trade-agents package (and its siblings) installed"
        ) from exc

    symbols = [s.strip().upper() for s in symbols if s and s.strip()]
    if not symbols:
        raise ValueError("at least one symbol is required")
    provider = DictBarsProvider({s: bars_by_symbol.get(s, []) for s in symbols})
    desk = default_desk()
    for scout in desk.researchers:
        universe = getattr(scout, "universe", None)
        if universe:
            overlap = [s for s in universe if s in provider.symbols()]
            scout.universe = tuple(overlap) if overlap else tuple(symbols)
    report = desk.run(provider, equity=equity)
    return report.to_dict()


# ---------------------------------------------------------------------------
# Risk
# ---------------------------------------------------------------------------

def describe_limits() -> list[dict]:
    try:
        from trade_risk.registry import describe_limits
    except ImportError as exc:
        raise RuntimeError("risk tools need the trade-risk package installed") from exc
    return describe_limits()


def evaluate_orders_job(
    orders: list[dict],
    limits: list[list] | None = None,
    equity: float = 100_000.0,
) -> dict:
    """Evaluate ``orders`` against a ``[[name, params], ...]`` limit stack."""
    try:
        from trade_agents.risk_agent import RiskManagerAgent
    except ImportError as exc:
        raise RuntimeError(
            "risk evaluation needs the trade-agents and trade-risk packages installed"
        ) from exc

    limits_cfg = [(name, params or {}) for name, params in limits] if limits else None
    agent = RiskManagerAgent(limits=limits_cfg)
    approved, vetoes = agent.review(orders, equity=equity)
    return {
        "approved": [{k: v for k, v in o.items() if k != "idea"} for o in approved],
        "vetoed": [v.to_dict() for v in vetoes],
    }
