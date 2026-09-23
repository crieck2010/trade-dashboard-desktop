"""Engine-service tests (no tkinter involved)."""

from __future__ import annotations

import inspect
import sys

import pytest

from trade_dashboard_desktop import engine
from trade_dashboard_desktop.engine import services


def test_demo_bars_shape(demo_bars):
    assert len(demo_bars) == 200
    b = demo_bars[0]
    assert set(b) == {"symbol", "timestamp", "open", "high", "low", "close", "volume"}
    assert b["high"] >= b["low"] >= 0
    assert b["symbol"] == "SPY"


def test_synth_bars_deterministic():
    a = services.synth_bars("SPY", n=50)
    b = services.synth_bars("SPY", n=50)
    assert a == b
    c = services.synth_bars("AAPL", n=50)
    assert a != c


def test_sources_lists_demo(data_service):
    sources = data_service.sources()
    assert sources[0]["id"] == "demo" and sources[0]["available"]


def test_get_bars_validates(data_service):
    with pytest.raises(ValueError):
        data_service.get_bars("", source="demo")
    with pytest.raises(ValueError):
        data_service.get_bars("SPY", source="nope")


def test_bar_to_dict_from_dict():
    d = engine.bar_to_dict({"symbol": "SPY", "timestamp": "2024-01-02T00:00:00+00:00",
                            "open": 1, "high": 2, "low": 0.5, "close": 1.5,
                            "volume": 10})
    assert d["close"] == 1.5 and d["timestamp"].startswith("2024-01-02")


def test_engine_binding_matches_fallback_signatures():
    """Reuse contract: bound names expose the same signatures as the fallback."""
    for name in engine.__all__:
        if name == "USING_SHARED_ENGINE":
            continue
        bound = getattr(engine, name)
        fallback = getattr(services, name, None)
        assert callable(bound)
        if fallback is not None and inspect.isfunction(fallback):
            # eval_str=True so `from __future__ import annotations` in the
            # fallback does not produce a spurious mismatch.
            assert (str(inspect.signature(bound, eval_str=True))
                    == str(inspect.signature(fallback, eval_str=True))), name


def test_using_shared_engine_flag_is_bool():
    assert isinstance(engine.USING_SHARED_ENGINE, bool)


def test_list_strategies():
    pytest.importorskip("trade_strategies")
    strategies = engine.list_strategies()
    assert len(strategies) >= 15
    assert {"name", "family", "description"} <= set(strategies[0])


def test_describe_strategy_unknown():
    pytest.importorskip("trade_strategies")
    with pytest.raises(KeyError):
        engine.describe_strategy("no_such_strategy")


def test_run_backtest_job_demo(demo_bars):
    pytest.importorskip("trade_strategies")
    result = engine.run_backtest_job("donchian_breakout", ["SPY"],
                                     {"entry": 20, "exit": 10}, demo_bars)
    assert result["final_equity"] > 0
    assert len(result["equity_curve"]) == len(demo_bars)
    assert "sharpe_ratio" in result["metrics"]


def test_run_backtest_job_validates(demo_bars):
    pytest.importorskip("trade_strategies")
    with pytest.raises(ValueError):
        engine.run_backtest_job("donchian_breakout", [], {}, demo_bars)


def test_describe_limits():
    pytest.importorskip("trade_risk")
    limits = engine.describe_limits()
    assert len(limits) >= 5
    assert {"name", "description"} <= set(limits[0])


def test_run_desk_job_demo(demo_bars):
    pytest.importorskip("trade_agents")
    report = engine.run_desk_job(["SPY"], {"SPY": demo_bars}, equity=100_000.0)
    assert {"briefs", "allocations", "approved_orders", "vetoes"} <= set(report)
    assert len(report["briefs"]) > 0


def test_evaluate_orders_job():
    pytest.importorskip("trade_agents")
    pytest.importorskip("trade_risk")
    result = engine.evaluate_orders_job(
        [{"symbol": "SPY", "side": "buy", "quantity": 10, "price": 580.0}],
        limits=[["max_position_notional", {"max_pct": 0.01}]],
        equity=100_000.0,
    )
    assert "approved" in result and "vetoed" in result
    # $5,800 notional > 1% of $100k, so the tight limit must veto it.
    assert len(result["vetoed"]) == 1
