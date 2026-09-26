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
                 "run_stream_demo_job", "run_reconcile_demo_job",
                 "run_trades_job", "run_performance_job",
                 "run_agent_activity_job", "run_network_job",
                 "run_risk_monitor_job", "trades_to_csv"):
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


# -- terminal wave (fallback services; stdlib-only, demo paths need no engines)

_MISSING = "/definitely/not/here"

_TERMINAL_SIGNATURES = {
    "run_trades_job":
        "(ledger_path=None, date_from=None, date_to=None, symbol=None, "
        "side=None, strategy=None, agent=None, outcome=None, limit=500) -> dict",
    "run_performance_job":
        "(source='paper', ledger_path=None, backtest=None, "
        "backtest_path=None, risk_free=0.0) -> dict",
    "run_agent_activity_job":
        "(track_record_path=None, approvals_ledger_path=None, limit=50) -> dict",
    "run_network_job":
        "(symbols=None, source='yfinance', days=252, method='pearson', "
        "seed=7, breadth=None, macro=None, regime=None) -> dict",
    "run_risk_monitor_job":
        "(ledger_path=None, hedge_state_path=None, regime=None, vol_days=63) -> dict",
}


def test_terminal_signatures_match_canonical():
    """Fallbacks carry the exact canonical signatures (eval_str normalized)."""
    for name, expected in _TERMINAL_SIGNATURES.items():
        got = str(inspect.signature(getattr(services, name), eval_str=True))
        assert got == expected, (name, got)


def test_terminal_signatures_match_web_engine():
    """Fallback signatures equal the web canonicals when the web package is present."""
    web = pytest.importorskip("trade_dashboard_web.engine.terminal_service")
    for name, expected in _TERMINAL_SIGNATURES.items():
        got = str(inspect.signature(getattr(web, name), eval_str=True))
        assert got == expected, (name, got)


def test_trades_demo():
    r = services.run_trades_job(ledger_path=_MISSING, limit=3)
    assert r["demo"] is True and r["count"] == 12
    assert len(r["trades"]) == 3
    assert all(t["demo"] is True for t in r["trades"])
    assert r["ledger_path"] is None
    # filters apply to the demo rows too
    w = services.run_trades_job(ledger_path=_MISSING, symbol="SPY",
                                outcome="win", limit=50)
    assert w["count"] < 12 and all(
        t["symbol"] == "SPY" and t["outcome"] == "win"
        for t in w["trades"])
    import json

    json.dumps(r)  # JSON-serializable


def test_trades_csv_roundtrip():
    r = services.run_trades_job(ledger_path=_MISSING, limit=2)
    text = services.trades_to_csv(r)
    lines = text.splitlines()
    assert lines[0].split(",") == [
        "id", "symbol", "side", "qty", "filled_qty", "avg_fill_price",
        "commission", "strategy", "state", "created_at", "filled_at",
        "realized_pnl", "outcome", "demo"]
    assert len(lines) == 3  # header + 2 rows


def test_performance_demo():
    r = services.run_performance_job(ledger_path=_MISSING)
    assert r["demo"] is True and r["equity_source"] == "demo"
    assert len(r["equity"]) == 252
    assert len(r["drawdown"]) == 252
    assert all(d <= 0 for d in r["drawdown"])
    assert r["summary"]["max_drawdown"] >= 0
    assert r["years"] == [2025]
    assert len(r["monthly"]) == 1 and len(r["monthly"][0]) == 12
    assert r["histogram"]["counts"] and sum(r["histogram"]["counts"]) == 251
    import json

    json.dumps(r)
    with pytest.raises(ValueError):
        services.run_performance_job(source="live")


def test_performance_backtest_dict():
    backtest = {
        "equity": [
            {"timestamp": "2025-01-02T00:00:00+00:00", "equity": 100.0},
            {"timestamp": "2025-01-03T00:00:00+00:00", "equity": 110.0}],
        "trades": [{"pnl": 10.0}],
    }
    r = services.run_performance_job(source="backtest", backtest=backtest)
    assert r["demo"] is False and r["equity_source"] == "backtest"
    assert r["summary"]["n_trades"] == 1
    with pytest.raises(ValueError):
        services.run_performance_job(source="backtest")  # no data at all


def test_agent_activity_empty_graceful():
    r = services.run_agent_activity_job(track_record_path=_MISSING,
                                        approvals_ledger_path=_MISSING)
    assert r["leaderboards"] == {"researcher": [], "risk_desk": [], "pm": []}
    assert r["elo_curves"] == {}
    assert r["brier"] == {"bins": [], "observed": [], "n": []}
    assert r["debates"] == [] and r["approval_queue"] == []
    assert "no track-record JSONL found" in r["message"]
    import json

    json.dumps(r)


def test_network_demo_deterministic():
    kw = {"source": "demo", "days": 60, "seed": 7}
    a = services.run_network_job(**kw)
    b = services.run_network_job(**kw)
    assert a == b  # deterministic given the seed
    assert len(a["nodes"]) == 12 and len(a["edges"]) == 11  # n-1 MST edges
    assert a["params"]["demo"] is True
    assert a["params"]["correlation_source"] == "stdlib"
    assert sum(len(c["members"]) for c in a["clusters"]) == 12
    assert all(-100 <= n["x"] <= 100 and -100 <= n["y"] <= 100
               for n in a["nodes"])
    c = services.run_network_job(**{**kw, "method": "spearman"})
    assert len(c["nodes"]) == 12  # different metric, still a valid network
    assert c["params"]["correlation_source"] == "stdlib"
    import json

    json.dumps(a)
    with pytest.raises(ValueError):
        services.run_network_job(source="demo", days=10)
    with pytest.raises(ValueError):
        services.run_network_job(symbols=["SPY", "QQQ"], source="demo")


def test_network_overlays():
    regime = {"schema_version": 1, "conviction": 72.5, "composite_raw": 0.7,
              "exposure_scale": 0.8,
              "hysteresis": {"state": "held", "reason": "within band",
                             "prior_conviction": 70.0}}
    r = services.run_network_job(source="demo", days=60, regime=regime)
    assert r["regime"]["conviction"] == 72.5
    assert r["regime"]["hysteresis_state"] == "held"
    assert r["breadth"] is None and r["macro"] is None


def test_risk_monitor_demo():
    r = services.run_risk_monitor_job(ledger_path=_MISSING,
                                      hedge_state_path=_MISSING)
    assert r["demo"] is True
    exp = r["exposures"]
    assert exp["n_positions"] == 5
    assert 0.0 < exp["herfindahl"] <= 1.0
    assert exp["largest_position"]["symbol"] is not None
    assert r["kill_switch"]["status"] == "unknown"
    assert r["regime"] is None
    assert r["vol_regime"]["note"] == "demo mode — no ledger, no vol timeline"
    import json

    json.dumps(r)


def test_risk_monitor_kill_switch_states(tmp_path):
    import json as _json

    halted = tmp_path / "halted.json"
    halted.write_text(_json.dumps({"consecutive_halts": 2, "cycles_run": 9}))
    r = services.run_risk_monitor_job(ledger_path=_MISSING,
                                      hedge_state_path=str(halted))
    assert r["kill_switch"]["status"] == "halted"
    active = tmp_path / "active.json"
    active.write_text(_json.dumps({"consecutive_halts": 0}))
    r = services.run_risk_monitor_job(ledger_path=_MISSING,
                                      hedge_state_path=str(active))
    assert r["kill_switch"]["status"] == "active"


def test_terminal_crosscheck_fallback_matches_web():
    """Fallback and bound (web) jobs agree exactly on identical inputs."""
    web = pytest.importorskip("trade_dashboard_web.engine.terminal_service")
    a = services.run_trades_job(ledger_path=_MISSING, symbol="SPY",
                                outcome="win", limit=50)
    b = web.run_trades_job(ledger_path=_MISSING, symbol="SPY",
                           outcome="win", limit=50)
    assert a == b
    a = services.trades_to_csv(services.run_trades_job(ledger_path=_MISSING))
    b = web.trades_to_csv(web.run_trades_job(ledger_path=_MISSING))
    assert a == b
    a = services.run_performance_job(ledger_path=_MISSING)
    b = web.run_performance_job(ledger_path=_MISSING)
    assert a == b
    bt = {"equity": [
        {"timestamp": "2025-01-02T00:00:00+00:00", "equity": 100.0},
        {"timestamp": "2025-01-03T00:00:00+00:00", "equity": 105.0}],
        "trades": [{"realized_pnl": 5.0}]}
    assert (services.run_performance_job(source="backtest", backtest=bt)
            == web.run_performance_job(source="backtest", backtest=bt))
    a = services.run_agent_activity_job(track_record_path=_MISSING,
                                        approvals_ledger_path=_MISSING)
    b = web.run_agent_activity_job(track_record_path=_MISSING,
                                   approvals_ledger_path=_MISSING)
    assert a == b
    for kw in ({"source": "demo", "days": 60},
               {"source": "demo", "days": 60, "method": "spearman",
                "seed": 42}):
        assert services.run_network_job(**kw) == web.run_network_job(**kw)
    a = services.run_risk_monitor_job(ledger_path=_MISSING,
                                      hedge_state_path=_MISSING)
    b = web.run_risk_monitor_job(ledger_path=_MISSING,
                                 hedge_state_path=_MISSING)
    assert a == b
