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


# ---------------------------------------------------------------------------
# Paper trading (trade-paper, lazy)
# ---------------------------------------------------------------------------

def paper_available() -> tuple[bool, str]:
    try:
        import trade_paper  # noqa: F401
        return True, ""
    except ImportError:
        return False, ("trade-paper is not installed; "
                       "pip install git+https://github.com/crieck2010/trade-paper.git")


def _paper_require():
    ok, hint = paper_available()
    if not ok:
        raise RuntimeError(hint)
    from trade_paper.brokers import make_broker
    from trade_paper.config import PaperConfig
    from trade_paper.ledger import Ledger
    return make_broker, PaperConfig, Ledger


def _paper_load(config_path: str):
    make_broker, PaperConfig, Ledger = _paper_require()
    cfg = PaperConfig.load(config_path or "paper-config.json")
    return cfg, make_broker(cfg), Ledger(cfg.db_path)


def paper_status(config_path: str = "") -> dict:
    cfg, broker, ledger = _paper_load(config_path)
    try:
        acct = broker.get_account()
        positions = broker.get_positions()
        return {
            "available": True, "broker": broker.name,
            "paper_only": True,
            "equity": round(acct.equity, 2), "cash": round(acct.cash, 2),
            "buying_power": round(acct.buying_power, 2),
            "market_open": broker.is_market_open(),
            "positions": [{"symbol": p.symbol, "qty": p.quantity,
                           "avg_entry": round(p.avg_entry_price, 4),
                           "market": round(p.market_price, 4),
                           "unrealized": round(p.unrealized_pnl, 2),
                           "asset_class": p.asset_class.value}
                          for p in positions],
            "pending_approvals": len(ledger.list_approvals(status="pending")),
            "active_strategies": len(ledger.active_strategies()),
            "recent_orders": [
                {"id": o["client_order_id"], "symbol": o["symbol"],
                 "side": o["side"], "qty": o["quantity"],
                 "strategy": o["strategy"], "state": o["state"]}
                for o in ledger.list_orders(limit=25)
            ],
        }
    finally:
        ledger.close()


def paper_approvals(config_path: str = "", status: str = "pending") -> dict:
    _, _, ledger = _paper_load(config_path)
    try:
        rows = ledger.list_approvals(status=status or None)
        return {"available": True, "approvals": [
            {"id": r["id"], "strategy": r["strategy"], "symbols": r["symbols"],
             "status": r["status"], "decided_by": r["decided_by"],
             "reason": r["reason"], "created_at": r["created_at"],
             "score": (r["metrics"].get("score")),
             "metrics": r["metrics"].get("metrics", {})}
            for r in rows]}
    finally:
        ledger.close()


def paper_approve(config_path: str, approval_id: int, reason: str = "") -> dict:
    _, _, ledger = _paper_load(config_path)
    try:
        ledger.decide_approval(approval_id, True, decided_by="user", reason=reason)
        return {"available": True, "approved": approval_id}
    finally:
        ledger.close()


def paper_fidelity(config_path: str = "") -> dict:
    _paper_require()
    from trade_paper import fidelity as fmod
    from trade_paper.config import PaperConfig
    from trade_paper.ledger import Ledger
    cfg = PaperConfig.load(config_path or "paper-config.json")
    ledger = Ledger(cfg.db_path)
    try:
        out = fmod.report(ledger, cfg.assumed_slippage_bps)
        out["available"] = True
        return out
    finally:
        ledger.close()


# ---------------------------------------------------------------------------
# Research lab (mirrors trade_dashboard_web.engine.research_service one-for-one)
# ---------------------------------------------------------------------------

def _research_require(dist: str, package: str):
    try:
        return __import__(package, fromlist=["*"])
    except ImportError as exc:
        raise RuntimeError(
            f"{dist} is not installed; install it with "
            f"`pip install git+https://github.com/crieck2010/{dist}.git`"
        ) from exc


def _clean_research_symbols(symbols: list[str]) -> list[str]:
    out = [s.strip().upper() for s in symbols if s and s.strip()]
    if not out:
        raise ValueError("at least one symbol is required")
    return out


def _closes_by_symbol(bars_by_symbol: dict[str, list]) -> dict[str, list[float]]:
    closes = {}
    for s, bs in bars_by_symbol.items():
        key = (s or "").strip().upper()
        if not key:
            continue
        closes[key] = [float(b["close"]) for b in bs]
    if not closes:
        raise ValueError("at least one symbol with bars is required")
    m = min(len(c) for c in closes.values())
    return {s: c[-m:] for s, c in closes.items()}


def run_pairs_job(
    symbols: list[str],
    bars_by_symbol: dict[str, list],
    lookback: int = 252,
    max_pairs: int = 10,
) -> dict:
    tp = _research_require("trade-pairs", "trade_pairs")
    closes = _closes_by_symbol(bars_by_symbol)
    syms = _clean_research_symbols(symbols)
    missing = [s for s in syms if s not in closes]
    if missing:
        raise ValueError(f"no bars for {', '.join(missing)}")
    prices = {s: closes[s] for s in syms}
    lb = min(lookback, min(len(c) for c in prices.values()))
    if lb < 30:
        raise ValueError(f"need >= 30 bars per symbol, have {lb}")
    cands = tp.find_pairs(prices, lookback=lb, max_pairs=max_pairs)
    return {
        "source": "trade-pairs",
        "symbols": syms,
        "lookback": lb,
        "n_cointegrated": sum(1 for c in cands if c.cointegrated),
        "pairs": [c.to_dict() for c in cands],
    }


def run_orderbook_job(
    symbol: str = "DEMO",
    side: str = "buy",
    quantity: float = 100.0,
    order_type: str = "market",
    n_levels: int = 5,
    level_qty: float = 50.0,
) -> dict:
    if side not in ("buy", "sell"):
        raise ValueError("side must be 'buy' or 'sell'")
    if order_type not in ("market", "limit"):
        raise ValueError("order_type must be 'market' or 'limit'")
    tob = _research_require("trade-orderbook", "trade_orderbook")
    book = tob.OrderBook()
    mid, tick = 100.0, 0.01
    oid = 0
    for lvl in range(1, n_levels + 1):
        for s, px in (("bid", mid - lvl * tick), ("ask", mid + lvl * tick)):
            oid += 1
            book.add(tob.Order(order_id=f"seed-{oid}", side=s,
                               quantity=level_qty, price=round(px, 4)))
    probe = tob.Order(
        order_id="probe", side="bid" if side == "buy" else "ask",
        quantity=quantity, price=None if order_type == "market" else mid,
        order_type=order_type)
    fills = tob.fills_for_paper_order(book, probe)
    filled = sum(f["quantity"] for f in fills)
    avg = (sum(f["quantity"] * f["price"] for f in fills) / filled
           if filled else 0.0)
    signed = 1.0 if side == "buy" else -1.0
    return {
        "source": "trade-orderbook",
        "symbol": (symbol or "DEMO").strip().upper(),
        "side": side,
        "quantity": quantity,
        "order_type": order_type,
        "midprice": mid,
        "filled_qty": filled,
        "fill_ratio": filled / quantity if quantity else 0.0,
        "avg_fill_price": round(avg, 4),
        "slippage_bps": round((avg / mid - 1.0) * 10_000 * signed, 2),
        "n_fills": len(fills),
        "book_features": tob.to_agent_features(
            book, levels=n_levels, symbol=(symbol or "DEMO").strip().upper()),
    }


def run_optimize_job(
    symbols: list[str],
    bars_by_symbol: dict[str, list],
    method: str = "max_sharpe",
    max_weight: float = 1.0,
) -> dict:
    import math

    topt = _research_require("trade-optimize", "trade_optimize")
    syms = _clean_research_symbols(symbols)
    closes = _closes_by_symbol({s: bars_by_symbol[s] for s in syms
                                if s in bars_by_symbol})
    if set(closes) != set(syms):
        raise ValueError("no bars for "
                         + ", ".join(s for s in syms if s not in closes))
    syms = sorted(closes)
    flat = [{"symbol": s, "close": c} for s in syms for c in closes[s]]
    names, R = topt.returns_from_dict_bars(flat, syms)
    mu = topt.estimates.shrink_mean(R)
    sigma = topt.estimates.shrink_covariance(R)
    if method == "max_sharpe":
        w = topt.max_sharpe(sigma, mu, max_weight=max_weight)
    elif method == "min_variance":
        w = topt.min_variance(sigma, max_weight=max_weight)
    elif method == "risk_parity":
        w = topt.risk_parity(sigma, max_weight=max_weight)
    elif method == "equal_weight":
        w = topt.equal_weight(len(names))
    else:
        raise ValueError(f"unknown method {method!r}")

    def stats(w_: list[float]) -> dict:
        er = sum(x * m for x, m in zip(w_, mu))
        var = sum(x * sum(s * y for s, y in zip(row, w_))
                  for x, row in zip(w_, sigma))
        vol = math.sqrt(max(var, 0.0))
        return {"expected_return": er, "volatility": vol,
                "sharpe": er / vol if vol > 0 else 0.0}

    port = stats(w)
    frontier = [{"expected_return": p["expected_return"],
                 "volatility": p["volatility"], "sharpe": p["sharpe"]}
                for p in topt.efficient_frontier(sigma, mu,
                                                 max_weight=max_weight,
                                                 n_points=20)]
    return {
        "source": "trade-optimize",
        "symbols": names,
        "method": method,
        "weights": {s: round(x, 4) for s, x in zip(names, w)},
        **{k: round(v, 6) for k, v in port.items()},
        "frontier": frontier,
    }


def _research_corr_matrix(returns: list[list[float]]) -> list[list[float]]:
    import math

    t = len(returns)
    cols = [list(c) for c in zip(*returns)]
    means = [sum(c) / t for c in cols]
    stds = []
    for i, c in enumerate(cols):
        var = sum((x - means[i]) ** 2 for x in c) / (t - 1)
        stds.append(math.sqrt(max(var, 0.0)))
    n = len(cols)
    out = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if stds[i] > 0 and stds[j] > 0:
                cov = sum((returns[k][i] - means[i]) * (returns[k][j] - means[j])
                          for k in range(t)) / (t - 1)
                out[i][j] = max(-1.0, min(1.0, cov / (stds[i] * stds[j])))
            out[i][i] = 1.0
    return out


def run_montecarlo_job(
    symbols: list[str],
    bars_by_symbol: dict[str, list],
    weights: list[float] | None = None,
    equity: float = 100_000.0,
    n_paths: int = 5_000,
    n_steps: int = 252,
    seed: int = 7,
    alpha: float = 0.95,
) -> dict:
    import math

    tmc = _research_require("trade-montecarlo", "trade_montecarlo")
    syms = _clean_research_symbols(symbols)
    closes = _closes_by_symbol({s: bars_by_symbol[s] for s in syms
                                if s in bars_by_symbol})
    syms = sorted(closes)
    R = [[closes[s][i] / closes[s][i - 1] - 1.0 for s in syms]
         for i in range(1, len(closes[syms[0]]))]
    t = len(R)
    mu = [sum(R[k][i] for k in range(t)) / t for i in range(len(syms))]
    sigma = [math.sqrt(sum((R[k][i] - mu[i]) ** 2 for k in range(t)) / (t - 1))
             for i in range(len(syms))]
    corr = _research_corr_matrix(R)
    s0 = [closes[s][-1] for s in syms]
    w = list(weights) if weights else [1.0 / len(syms)] * len(syms)
    if len(w) != len(syms):
        raise ValueError("weights length must match symbols")
    result = tmc.portfolio_var(w, s0, mu, sigma, corr, capital=equity,
                               n_paths=n_paths, n_steps=n_steps, T=1.0,
                               seed=seed, alpha=alpha)
    return {
        "source": "trade-montecarlo",
        "symbols": syms,
        "n_paths": n_paths,
        "n_steps": n_steps,
        "seed": seed,
        "equity": equity,
        **result,
    }


def run_vol_surface_job(
    symbol: str = "SPY",
    spot: float | None = None,
    risk_free: float = 0.03,
) -> dict:
    import math

    tvs = _research_require("trade-volsurface", "trade_volsurface")
    try:
        from trade_volsurface.cli import demo_quotes
    except ImportError as exc:
        raise RuntimeError(
            "trade-volsurface is installed but its demo quotes are not "
            "importable"
        ) from exc
    quotes = demo_quotes()
    s0 = spot if spot is not None else 100.0
    rows = [{"T": q["T"], "K": s0 * math.exp(risk_free * q["T"] + q["k"]),
             "iv": q["iv"]} for q in quotes]
    surface = tvs.from_option_chain(rows, s0=s0, r=risk_free)
    fits = tvs.fit_svi_surface(surface)
    return {
        "source": "trade-volsurface",
        "symbol": (symbol or "SPY").strip().upper(),
        "spot": s0,
        "risk_free": risk_free,
        "n_quotes": len(quotes),
        "expiries": sorted({q["T"] for q in quotes}),
        "svi_fits": {str(k): {p: round(v, 6) for p, v in f.to_dict().items()}
                     for k, f in fits.items()},
        "agent_surface": tvs.to_agent_surface(surface),
    }


def _month_end_closes(bars: list) -> list[tuple[str, float]]:
    out: dict[str, float] = {}
    for b in bars:
        out[str(b["timestamp"])[:7].replace("-", "")] = float(b["close"])
    return sorted(out.items())


def run_factor_analysis_job(
    symbols: list[str],
    bars_by_symbol: dict[str, list],
    model: str = "ff5",
    n_months: int = 60,
) -> dict:
    tf = _research_require("trade-factors", "trade_factors")
    syms = _clean_research_symbols(symbols)
    factors = tf.demo_factors(n=120, seed=7)
    monthly: dict[str, list[float]] = {}
    for s in syms:
        if s not in bars_by_symbol:
            raise ValueError(f"no bars for {s}")
        me = _month_end_closes(bars_by_symbol[s])
        rets = [me[i][1] / me[i - 1][1] - 1.0 for i in range(1, len(me))]
        if len(rets) < 24:
            raise ValueError(f"need >= 24 monthly returns for {s}, "
                             f"have {len(rets)} (fetch more bars)")
        monthly[s] = rets
    k = min(n_months, min(len(r) for r in monthly.values()),
            len(factors.dates))
    fdata = tf.FactorData(
        factors.dates[-k:],
        {name: col[-k:] for name, col in factors.factors.items()})
    assets = {s: fdata.excess(monthly[s][-k:]) for s in syms}
    results = tf.panel_regressions(assets, fdata, model=model)
    grs = tf.grs_test(results, fdata, model=model)
    report = tf.to_agent_factor_report(results, grs)
    return {"source": "trade-factors", "model": model, "n_months": k,
            **report}


def run_sentiment_price_job(
    symbol: str,
    bars: list | None = None,
    sentiment_rows: list[dict] | None = None,
    days: int = 180,
    seed: int = 7,
) -> dict:
    tsvp = _research_require("trade-sentiment-vs-price",
                             "trade_sentiment_vs_price")
    symbol = (symbol or "").strip().upper()
    if not symbol:
        raise ValueError("a symbol is required")
    if sentiment_rows is not None:
        if not bars:
            raise ValueError("sentiment_rows need matching price bars")
        sent = tsvp.from_sentiment_scan(sentiment_rows)
        prices = tsvp.prices_from_dict_bars(
            [{"date": str(b["timestamp"])[:10], "close": b["close"]}
             for b in bars])
    else:
        sent, prices = tsvp.demo_data(n_days=days, symbol=symbol, seed=seed)
    return tsvp.to_agent_report(symbol, sent, prices)


def run_correlation_job(
    symbols: list[str],
    bars_by_symbol: dict[str, list],
    method: str = "pearson",
    shrinkage: str = "ledoit_wolf",
    lookback: int = 252,
) -> dict:
    """Correlation/EDA report over a symbol universe (trade-eda).

    Mirrors the web dashboard's canonical job one-for-one: same
    signature, same plain-data result.  Full bar dicts are passed through
    (volume/timestamp feed the data-quality section); series are truncated
    to the common length, oldest-first.
    """
    if method not in ("pearson", "spearman"):
        raise ValueError("method must be 'pearson' or 'spearman'")
    te = _research_require("trade-eda", "trade_eda")
    norm: dict[str, list] = {}
    for s, bs in bars_by_symbol.items():
        key = (s or "").strip().upper()
        if key:
            norm[key] = list(bs)
    syms = _clean_research_symbols(symbols)
    missing = [s for s in syms if s not in norm]
    if missing:
        raise ValueError("no bars for " + ", ".join(missing))
    if len(syms) < 2:
        raise ValueError("need at least two symbols")
    m = min(len(norm[s]) for s in syms)
    lb = min(lookback, m)
    if lb < 30:
        raise ValueError(f"need >= 30 bars per symbol, have {lb}")
    bars = {s: norm[s][-lb:] for s in syms}
    return te.analyze(bars, method=method, shrinkage=shrinkage)
