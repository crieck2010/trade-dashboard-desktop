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


# -- research lab (fallback services) -----------------------------------------

def _rbars(symbols=("SPY", "QQQ"), days=300):
    from trade_dashboard_desktop.engine import services as svc
    ds = svc.DataService()
    return {s: ds.get_bars(s, source="demo", days=days) for s in symbols}


def test_research_service_names_exposed():
    for name in ("run_pairs_job", "run_orderbook_job", "run_optimize_job",
                 "run_montecarlo_job", "run_vol_surface_job",
                 "run_factor_analysis_job", "run_sentiment_price_job",
                 "run_correlation_job", "run_breadth_job", "run_macro_job",
                 "run_stream_demo_job", "run_reconcile_demo_job"):
        assert name in engine._SERVICE_NAMES
        assert callable(getattr(engine, name))


def test_research_pairs_fallback():
    pytest.importorskip("trade_pairs")
    r = services.run_pairs_job(["SPY", "QQQ", "IWM"], _rbars(("SPY", "QQQ", "IWM")),
                               lookback=100, max_pairs=3)
    assert r["source"] == "trade-pairs"
    assert all("hedge_ratio" in p for p in r["pairs"])


def test_research_orderbook_fallback():
    pytest.importorskip("trade_orderbook")
    r = services.run_orderbook_job(side="sell", quantity=50.0)
    assert r["source"] == "trade-orderbook"
    assert 0.0 <= r["fill_ratio"] <= 1.0


def test_research_optimize_fallback():
    pytest.importorskip("trade_optimize")
    r = services.run_optimize_job(["SPY", "QQQ"], _rbars(days=250),
                                  method="equal_weight")
    assert r["source"] == "trade-optimize"
    assert abs(sum(r["weights"].values()) - 1.0) < 1e-9


def test_research_montecarlo_fallback():
    pytest.importorskip("trade_montecarlo")
    r = services.run_montecarlo_job(["SPY", "QQQ"], _rbars(days=250),
                                    n_paths=200, n_steps=60, seed=7)
    assert r["source"] == "trade-montecarlo"
    assert r["var"] >= 0


def test_research_volsurface_fallback():
    pytest.importorskip("trade_volsurface")
    r = services.run_vol_surface_job()
    assert r["source"] == "trade-volsurface"
    assert r["n_quotes"] > 0


def test_research_factors_fallback():
    pytest.importorskip("trade_factors")
    r = services.run_factor_analysis_job(["SPY", "QQQ"],
                                         _rbars(("SPY", "QQQ"), days=750),
                                         model="ff3", n_months=24)
    assert r["source"] == "trade-factors"
    assert r["grs"]["pvalue"] is not None


def test_research_sentiment_fallback():
    pytest.importorskip("trade_sentiment_vs_price")
    r = services.run_sentiment_price_job("SPY", days=180)
    assert r["source"] == "trade-sentiment-vs-price"
    assert r["lead_lag"]["best_lag"] == 1


def test_research_correlation_fallback():
    pytest.importorskip("trade_eda")
    bars = _rbars(("SPY", "QQQ", "IWM"), days=300)
    r = services.run_correlation_job(["SPY", "QQQ", "IWM"], bars,
                                     method="spearman", lookback=200)
    assert r["source"] == "trade-eda"
    assert r["correlation"]["method"] == "spearman"
    assert r["n_obs"] == 199
    assert len(r["correlation"]["matrix"]) == 3
    with pytest.raises(ValueError):
        services.run_correlation_job(["SPY"], bars)


def test_research_breadth_fallback():
    pytest.importorskip("trade_breadth")
    r = services.run_breadth_job(preset="standard", seed=7, n_days=600)
    assert r["source"] == "trade-breadth"
    assert r["preset"] == "standard"
    assert r["seed"] == 7 and r["n_days"] == 600
    assert r["n_symbols"] == 60
    snap = r["snapshot"]
    assert snap["regime"] in ("BROADENING", "NARROWING", "NEUTRAL")
    assert 0.0 <= snap["fragility"] <= 1.0
    assert isinstance(snap["thrusts_recent"], list)
    assert "indicators" in snap
    import json

    json.dumps(r)  # must be JSON-serializable
    with pytest.raises(ValueError):
        services.run_breadth_job(preset="nope")
    with pytest.raises(ValueError):
        services.run_breadth_job(n_days=0)


def test_research_macro_fallback():
    pytest.importorskip("trade_macro")
    r = services.run_macro_job(preset="standard", seed=42, days=600)
    assert r["source"] == "trade-macro"
    assert r["preset"] == "standard"
    assert r["seed"] == 42 and r["days"] == 600
    assert r["snapshot"]["source"] == "synthetic"
    snap = r["snapshot"]
    assert snap["regime"] in ("EXPANSION", "CONTRACTION", "NEUTRAL")
    assert isinstance(snap["z_score"], float)
    assert "ratio_vs_200dma" in snap
    assert isinstance(snap["transition_alert"], bool)
    import json

    json.dumps(r)  # must be JSON-serializable
    with pytest.raises(ValueError):
        services.run_macro_job(preset="nope")
    with pytest.raises(ValueError):
        services.run_macro_job(days=-1)


def test_research_stream_demo_fallback():
    pytest.importorskip("trade_stream")
    r = services.run_stream_demo_job(symbols=("AAA", "BBB"), seed=7, n_ticks=50)
    assert r["source"] == "trade-stream"
    assert r["demo"] is True
    assert r["symbols"] == ["AAA", "BBB"]
    assert r["n_ticks"] == 50
    assert set(r["latest"]) == {"AAA", "BBB"}
    import json

    json.dumps(r)  # explicitly guaranteed by the service
    with pytest.raises(ValueError):
        services.run_stream_demo_job(symbols=())
    with pytest.raises(ValueError):
        services.run_stream_demo_job(n_ticks=0)


def test_research_reconcile_demo_fallback():
    pytest.importorskip("trade_paper")
    r = services.run_reconcile_demo_job()
    assert r["source"] == "trade-paper"
    assert r["demo"] is True
    assert r["account_id"] == "AGENTIC-001"
    assert r["paper_positions"] == {"AAPL": 10.0, "TSLA": 4.5, "NVDA": 2.0}
    assert r["broker_positions"] == {"AAPL": 10.0, "TSLA": 5.0}
    rec = r["reconcile"]
    assert rec["clean"] is False  # deliberate drift
    assert rec["matched"] == ["AAPL"]
    assert rec["missing_from_broker"] == [{"symbol": "NVDA", "paper": 2.0}]
    assert rec["quantity_mismatches"] == [
        {"symbol": "TSLA", "paper": 4.5, "broker": 5.0, "diff": 0.5}]
    import json

    json.dumps(r)  # must be JSON-serializable


def test_crosscheck_fallback_matches_web_engine():
    """Fallback and bound (web) jobs agree exactly on identical inputs."""
    web = pytest.importorskip("trade_dashboard_web.engine")
    pytest.importorskip("trade_breadth")
    pytest.importorskip("trade_macro")
    assert engine.USING_SHARED_ENGINE is True
    a = services.run_breadth_job(preset="standard", seed=7, n_days=600)
    b = web.run_breadth_job(preset="standard", seed=7, n_days=600)
    assert a == b
    a = services.run_macro_job(preset="standard", seed=42, days=600)
    b = web.run_macro_job(preset="standard", seed=42, days=600)
    assert a == b


def test_research_missing_breadth_engine_hint():
    import sys
    blocked = "trade_breadth"
    real_import = __import__

    def fake_import(name, *a, **k):
        if name == blocked or name.startswith(blocked + "."):
            raise ImportError(f"No module named {name!r}")
        return real_import(name, *a, **k)

    import builtins
    old = builtins.__import__
    builtins.__import__ = fake_import
    try:
        for mod in list(sys.modules):
            if mod == blocked or mod.startswith(blocked + "."):
                del sys.modules[mod]
        with pytest.raises(RuntimeError, match="trade-breadth"):
            services.run_breadth_job(seed=7, n_days=60)
    finally:
        builtins.__import__ = old


def test_research_missing_pairs_engine_hint():
    import sys
    blocked = "trade_pairs"
    real_import = __import__

    def fake_import(name, *a, **k):
        if name == blocked or name.startswith(blocked + "."):
            raise ImportError(f"No module named {name!r}")
        return real_import(name, *a, **k)

    import builtins
    old = builtins.__import__
    builtins.__import__ = fake_import
    try:
        for mod in list(sys.modules):
            if mod == blocked or mod.startswith(blocked + "."):
                del sys.modules[mod]
        with pytest.raises(RuntimeError, match="trade-pairs"):
            services.run_pairs_job(["SPY", "QQQ"], _rbars(days=100),
                                   lookback=100)
    finally:
        builtins.__import__ = old
    real_import = __import__

    def fake_import(name, *a, **k):
        if name == blocked or name.startswith(blocked + "."):
            raise ImportError(f"No module named {name!r}")
        return real_import(name, *a, **k)

    import builtins
    old = builtins.__import__
    builtins.__import__ = fake_import
    try:
        for mod in list(sys.modules):
            if mod == blocked or mod.startswith(blocked + "."):
                del sys.modules[mod]
        with pytest.raises(RuntimeError, match="trade-pairs"):
            services.run_pairs_job(["SPY", "QQQ"], _rbars(days=100),
                                   lookback=100)
    finally:
        builtins.__import__ = old
