# trade-dashboard-desktop

A dependency-free **tkinter desktop dashboard** for the [trade-suite](https://github.com/crieck2010/trade-suite)
algorithmic/agentic trading system. Backtest strategies, browse the strategy
catalog, run the hedge-fund research desk, review orders against risk limits,
and inspect market data — from a native desktop window with no browser, no
build step, and no third-party GUI toolkit.

Part of the trade-suite: one pure-Python repo per module
(`trade-data-*`, `trade-backtest`, `trade-strategies`, `trade-risk`,
`trade-agents`, `trade-dashboard-web`, `trade-dashboard-desktop`,
`trade-suite`).

> **Research tooling only.** This is backtesting / research / paper-trading
> software. It does not trade live and it is not investment advice.

---

## Features

| Tab | What it does |
|---|---|
| **Backtest Lab** | Pick a strategy, symbols, data source, and params; runs in the background and renders an equity curve, metrics (return, Sharpe, max drawdown), and the round-trip trade list. |
| **Strategies** | Browse the `trade-strategies` registry: family, description, parameters, warmup bars. |
| **Agent Desk** | Run the `trade-agents` research desk (niche scouts → portfolio manager → risk manager) and inspect ideas, allocations, approved orders, vetoes, and advisor notes. |
| **Risk Review** | Assemble a `trade-risk` limit stack from the registry, paste orders as JSON, and evaluate approvals/vetoes with cumulative fill tracking. |
| **Paper** | Monitor `trade-paper`: paper account/equity, open positions, pending strategy approvals with one-click approve, backtest-vs-paper fidelity, plus a Broker reconcile (DEMO) panel comparing the paper ledger to the Robinhood MCP mock. Paper only — can never trade live. |
| **Market Data** | Fetch bars (synthetic demo or delayed equities) and render a candlestick chart plus OHLC stats. |
| **Research Lab** | Ten quant-engine panels in sub-tabs: pairs screening, order-book simulation, portfolio optimization, Monte Carlo VaR, vol-surface fitting, factor analysis, sentiment-vs-price, correlation/EDA, market-breadth regime, copper/gold macro regime. All run in the background; panels render plain-data tables/metrics. |
| **Live** | Polls a local `trade-stream` demo session (StreamSession source="demo"); background thread pumps ticks to a thread-safe LatestPriceCache, the UI refreshes latest prices via `after(2000ms)` on the tkinter main thread. DEMO STREAM — simulated feed. |

- **Zero required dependencies** beyond Python's stdlib + tkinter (ships with
  standard CPython on Windows/macOS; on Linux install `python3-tk`).
- **Engine/UI split**: all logic lives in `engine/` (no tkinter imports);
  `ui/` is a thin view layer. The engine is importable and testable without
  a display.
- **Shared engine with the web dashboard**: when `trade-dashboard-web` is
  installed, this package reuses its `engine` (single source of truth);
  otherwise it uses a stdlib-only local equivalent with identical signatures,
  so the desktop works fully standalone.
- **Lazy sibling adapters**: `trade-data-equities`, `trade-strategies`,
  `trade-backtest`, `trade-risk`, `trade-agents` are imported only when a tab
  needs them. Without them, every tab still works on deterministic synthetic
  demo data — fully offline.
- **Responsive UI**: backtests and desk runs execute in background daemon
  threads; results are marshalled to the tkinter main thread, so the window
  never freezes.
- **Live tab threading**: the stream thread (`trade_stream.StreamSession`,
  source="demo") is the only writer to a thread-safe `LatestPriceCache` on
  the message bus; the tkinter main thread polls the cache with
  `after(2000ms)` and updates widgets. Tkinter widgets are never touched
  from the stream thread.
- **Monetization-ready**: license-key check hook and GitHub-releases
  update-check hook are built in (Tools menu).
- **Windows distribution**: one-command PyInstaller single-file `.exe` build
  plus an Inno Setup installer script.

---

## Installation

Requires Python 3.10+.

```bash
# core (stdlib + tkinter only)
pip install trade-dashboard-desktop

# with the trade-suite engines (install each from GitHub)
pip install git+https://github.com/crieck2010/trade-data-equities.git
pip install git+https://github.com/crieck2010/trade-strategies.git
pip install git+https://github.com/crieck2010/trade-backtest.git
pip install git+https://github.com/crieck2010/trade-risk.git
pip install git+https://github.com/crieck2010/trade-agents.git
# optional: share one engine implementation with the web dashboard
pip install git+https://github.com/crieck2010/trade-dashboard-web.git
```

For real (delayed) equity data you also need `yfinance`:
`pip install yfinance`.

## Quickstart

```bash
trade-dashboard-desktop
# or
python -m trade_dashboard_desktop
# skip the startup update check
python -m trade_dashboard_desktop --skip-update-check
```

On first launch every tab works out of the box on synthetic demo data.
Pick the **Equities (delayed)** source in the Backtest Lab or Market Data tab
once `trade-data-equities` + `yfinance` are installed.

---

## Project structure

```
trade-dashboard-desktop/
├── src/trade_dashboard_desktop/
│   ├── __init__.py / __main__.py   # version, CLI entry point
│   ├── engine/                     # pure logic, NO tkinter imports
│   │   ├── __init__.py             # binds trade_dashboard_web.engine
│   │   │                           # when installed, else local fallback
│   │   ├── services.py             # stdlib-only service equivalents
│   │   ├── licensing.py            # license-key check hook
│   │   └── updates.py              # GitHub-releases update-check hook
│   └── ui/                         # thin tkinter view layer
│       ├── app.py                  # main window, menus, status bar
│       ├── charts.py               # pure chart math + canvas renderers
│       ├── workers.py              # background JobRunner (threads + after)
│       ├── context.py / helpers.py # shared tab context + widget helpers
│       └── tabs/                   # backtest / strategies / desk /
│                                   # risk / data — each exposes build()
├── tests/                          # 40 tests, headless-safe
├── docs/ARCHITECTURE.md
├── build.py / build_exe.bat        # PyInstaller single-file .exe build
├── installer.iss                   # Inno Setup installer definition
├── CHANGELOG.md / LICENSE (MIT)
└── pyproject.toml
```

### Engine services

`trade_dashboard_desktop.engine` exposes:

- `DataService` / `bar_to_dict` — demo + delayed-equity bars, normalized to plain dicts
- `list_strategies` / `describe_strategy` — strategy catalog
- `run_backtest_job(strategy, symbols, params, bars, initial_cash)` — backtest → metrics, equity curve, trades
- `run_desk_job(symbols, bars_by_symbol, equity)` — agent desk → plain-data report
- `describe_limits` / `evaluate_orders_job(orders, limits, equity)` — risk review
- `paper_available` / `paper_status` / `paper_approvals` / `paper_approve` /
  `paper_fidelity` — paper-trading monitor (needs `trade-paper` installed)
- `run_pairs_job` / `run_orderbook_job` / `run_optimize_job` /
  `run_montecarlo_job` / `run_vol_surface_job` / `run_factor_analysis_job` /
  `run_sentiment_price_job` / `run_correlation_job` / `run_breadth_job` /
  `run_macro_job` — Research Lab jobs, one per quant engine
  (needs the corresponding engine installed; demo-friendly defaults)
- `run_stream_demo_job` — end-to-end trade-stream demo (feed -> bus -> cache),
  JSON-serializable summary
- `run_reconcile_demo_job` — paper-ledger vs Robinhood-MCP-mock reconcile
  demo (read-only, deliberate drift; needs `trade-paper`)

`engine.USING_SHARED_ENGINE` is `True` when the implementation is reused from
`trade-dashboard-web`, `False` when the bundled fallback is active (shown in
the status bar).

---

## Interoperability & scaling notes

- **One engine, two dashboards.** The desktop and web dashboards share the
  same service functions and signatures, so a backtest or desk run produces
  identical results in either UI. The binding is lazy: install order doesn't
  matter, and neither package hard-depends on the other.
- **Sibling engines are optional at import time.** Every integration point is
  a lazy import with a clear error message naming the missing package; the
  test suite covers both the connected and standalone paths.
- **UI never blocks on compute.** `JobRunner` bounds main-thread work per
  poll tick; CPU-heavy jobs stay on worker threads. For heavier fleets later,
  the same `Job` seam can be pointed at a process pool or task queue without
  touching the tabs.
- **Charts are dependency-free canvas drawings** (no matplotlib), so the
  packaged `.exe` stays lean.

---

## Windows packaging

Native `.exe` builds must run **on Windows** (PyInstaller targets its host OS).

```bat
build_exe.bat
```

This installs PyInstaller and produces `dist\TradeDashboardDesktop.exe`.
Then open `installer.iss` in [Inno Setup](https://jrsoftware.org/isinfo.php)
and compile to get a versioned installer in `installer-output/`.

---

## Monetization hooks

- **License keys** (`engine/licensing.py`): v0.1.0 runs in community mode —
  no key required. Keys look like `TD-XXXX-XXXX-XXXX` and are stored in
  `~/.trade_dashboard_desktop/license.key`. Validate against a merchant of
  record (Gumroad / Lemon Squeezy) before gating premium features.
- **Update checks** (`engine/updates.py`): compares the running version
  against the latest GitHub release; runs once at startup (background) and on
  demand from Tools → Check for updates.
- Payments, when added, go through a merchant of record — never custom
  billing code.

---

## Testing

```bash
# standalone (bundled engine fallback)
PYTHONPATH=src python -m pytest tests/ -q

# fully connected (shared engine + all siblings)
PYTHONPATH=src:../trade-dashboard-web/src:../trade-strategies/src:../trade-backtest/src:../trade-risk/src:../trade-agents/src:../trade-data-equities/src \
  python -m pytest tests/ -q
```

40 tests, 1 skipped (the live-widget test needs a display; it runs on dev
machines and in the packaged Windows app smoke test).

---

## Changelog / License

See [CHANGELOG.md](CHANGELOG.md). MIT — see [LICENSE](LICENSE).

## The maths

**What you learn.** Like its web sibling, this dashboard is a thin view over a pure-Python engine: the Backtest Lab reports backtest metrics, the Research Lab renders ten quant-engine results, and the Market Data tab draws candlesticks — all from plain-data computations in `engine/` (or the shared web engine) plus pure chart-scaling math in `ui/charts.py`.

**Why it matters.** The engine/UI split is a correctness guarantee: `engine/services.py` carries the same function signatures as the web dashboard's `engine/research_service.py` (a parity test enforces this), and `engine.USING_SHARED_ENGINE` tells you which implementation is live. A backtest or research run gives identical numbers on desktop and web, and identical numbers to the `trade-suite` CLI, because there is one computation per job regardless of the UI in front of it. Heavy jobs run on background threads via `JobRunner`, but the maths is unchanged — threading only moves *where* it runs.

**The maths.** Backtests delegate to `trade-backtest` (return, Sharpe, max drawdown, win rate, round-trip trades). The Optimize panel maximizes Sharpe `(wᵀμ)/√(wᵀΣw)` or minimizes variance `wᵀΣw` over sample moments of daily simple returns, subject to a max-weight cap. The Monte Carlo panel fits per-asset `μ`, `σ`, and the correlation matrix from sample moments, simulates correlated GBM paths, and reports VaR/CVaR at the chosen level. The Correlation panel offers sample or Ledoit-Wolf-shrunk covariance (`Σ* = δF + (1−δ)S`, shrinking the sample covariance toward a structured target for stability in small samples). The remaining panels (pairs ADF cointegration, order-book impact, vol-surface fitting, Fama-French regressions with GRS, sentiment lead-lag) delegate to their engines of record. Charting is pure affine scaling: `line_points` maps values to canvas coordinates via `x = pad + i·(W−2·pad)/(n−1)`, `y = H−pad − (v−lo)/span·(H−2·pad)`; `candle_layout` places each bar in its time slot with body `max(1, 0.6·slot)` wide and wicks spanning high–low — all testable without a display.

**Honest limitations.** The dashboard adds no statistics of its own; it inherits the engines' assumptions (GBM VaR, Gaussian-ish Sharpe, sample-moment frontiers). Ledoit-Wolf shrinkage is a bias-variance tradeoff, not free accuracy. Demo data is synthetic; each Research Lab panel carries the same demo caveats as the web dashboard. The bundled fallback engine mirrors the web engine's signatures, not a second independent implementation — new web-engine parameters must be mirrored here by hand.
