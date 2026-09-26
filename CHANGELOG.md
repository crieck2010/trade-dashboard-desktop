# Changelog

All notable changes to `trade-dashboard-desktop` are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and versioning follows [Semantic Versioning](https://semver.org/).

## [0.5.0] - 2026-09-26

### Added
- **Terminal-wave phase 2** — five new top-level tabs mirroring the
  `trade-dashboard-web` v0.5.0 terminal wave, each running its canonical
  job through the existing `Job`/`JobRunner` background infrastructure:
  - **Trades** (`ui/tabs/trades_tab.py`) — filter form (date range,
    symbol, side, strategy, agent, outcome), scrollable blotter table,
    and an "Export CSV" button writing `engine.trades_to_csv` bytes via a
    Save-As dialog. DEMO banner when the service reports `demo: True`.
  - **Performance** (`ui/tabs/performance_tab.py`) — sub-tabs Summary
    (win rate, profit factor, expectancy, max drawdown, CAGR), Equity &
    Drawdown, Monthly heatmap, Rolling (63-day Sharpe/vol), and Histogram,
    rendered with new pure-math helpers in `ui/charts.py`. Works on paper
    equity or a backtest-result JSON.
  - **Agents** (`ui/tabs/agents_tab.py`) — leaderboards (researcher /
    risk desk / PM), Brier calibration chart, debate timeline, and the
    pending-approval queue; Elo curves shown as one line chart per
    *selected* agent (simplified parity — tkinter has no in-cell SVG).
  - **Network** (`ui/tabs/network_tab.py`) — STATIC parity render of the
    engine-computed correlation MST: nodes colored by cluster and sized
    by annualized vol, edge width scaling with |correlation|. No
    pan/zoom or hover tooltips on desktop; exploration is menu-driven
    (cluster listbox + node selector → top correlations). The tab and
    docs say so explicitly.
  - **Risk Monitor** (`ui/tabs/risk_monitor_tab.py`) — exposure bars,
    Herfindahl + largest-position readout, trailing-21-day realized-vol
    timeline, kill-switch status pill (`halted`/`active`/`unknown`),
    and the regime-conviction gauge with its hysteresis state.
- Five new engine services — `run_trades_job`, `run_performance_job`,
  `run_agent_activity_job`, `run_network_job`, `run_risk_monitor_job` —
  plus `trades_to_csv`, all registered in `_SERVICE_NAMES` and mirrored
  one-for-one in the stdlib-only `engine/services.py` fallback with the
  exact canonical signatures (a parity test pins each signature string).
  The fallbacks are verified byte-identical to the web canonicals on
  every deterministic demo path (verified by a cross-check test, not just
  by signature). Degraded behavior vs the shared engine is documented in
  `engine/services.py`: none on the demo paths (the web terminal jobs
  are stdlib-only there); on the real network path the fallback uses
  this package's own `run_correlation_job` (needs `trade-eda`) for the
  correlation matrix where the web job uses its research_service.
- `ui/charts.py` gains terminal-wave math + renderers, all pure and
  headless-testable: `underwater_curve`, `bar_layout` (signed bars +
  zero line), `heatmap_layout`/`heatmap_color`, `gauge_layout`,
  `network_positions`/`edge_width`/`cluster_color`, `calibration_layout`,
  and thin canvas renderers `draw_underwater`, `draw_histogram`,
  `draw_bars`, `draw_heatmap`, `draw_gauge`, `draw_network`,
  `draw_calibration`.
- New `docs/PARITY.md`: enumerates exactly which terminal views are full,
  simplified, or static parity on desktop vs the web flagship, and why.

### Notes
- The web dashboard remains the flagship for the terminal wave; the
  desktop is simplified parity per `docs/PARITY.md`. All numbers come
  from the same canonical jobs — only presentation differs.
- Demo data is never presented as real: every terminal tab shows a DEMO
  banner whenever the service reports `demo: True`.

## [0.4.0] - 2026-09-24

### Added
- Two new **Research Lab** sub-tabs (now ten): **Breadth**
  (`trade-breadth`) — regime badge, fragility progress bar, recent thrust
  list, and the breadth indicator panel (A/D line, McClellan, EW/CW ratio)
  over the seeded 60-symbol demo universe; and **Macro** (`trade-macro`) —
  copper/gold regime badge, z-score, ratio vs 200DMA, and transition alert.
  Both run via the existing `Job`/`JobRunner` background infra, inputs
  labeled DEMO.
- New **Live** top-level tab (`ui/tabs/live_tab.py`): polls a local
  `trade-stream` demo session in a background thread (`StreamSession`
  source="demo" → `MessageBus` → thread-safe `LatestPriceCache`); the
  tkinter main thread refreshes the latest-price table via `after(2000ms)`.
  The finite seeded feed restarts on exhaustion ("DEMO STREAM — simulated
  feed"). The threading contract is documented in the module docstring
  (stream thread → cache → `after()` UI updates; tkinter never touched from
  the stream thread). Shows an install hint when `trade-stream` is absent.
- **Paper** tab gains a "Broker reconcile (DEMO)" panel: runs
  `run_reconcile_demo_job` through `JobRunner` and renders matched,
  missing-from-broker/ledger, and quantity-mismatch rows. All existing
  panels are preserved.
- Four new engine services — `run_breadth_job`, `run_macro_job`,
  `run_stream_demo_job`, `run_reconcile_demo_job` — added to
  `_SERVICE_NAMES` and mirrored one-for-one in the stdlib-only
  `engine/services.py` fallback, with identical names and signatures to the
  web dashboard's canonical jobs. Each lazy-imports its engine with a
  pip-install hint; demo inputs stay seeded and deterministic.

### Notes
- `trade-data-equities` v0.2.0 added a Polygon provider; this release needs
  **no code change** — the new provider is data-layer only and flows through
  the existing `trade-data-equities` adapter.
- The Live tab and the reconcile demo are read-only simulations; nothing in
  this release touches live trading or real broker accounts.

## [0.3.0] - 2026-09-24

### Added
- Eighth **Research Lab** sub-tab: **Correlations** (trade-eda) — symbol
  inputs, Pearson/Spearman method and Ledoit-Wolf/sample shrinkage
  selectors, lookback; renders diversification stats, the correlation
  matrix, per-asset summary stats, and data-quality flags.
- `run_correlation_job` fallback in `engine/services.py` (stdlib-only,
  lazy `trade-eda` import) plus `run_correlation_job` in `_SERVICE_NAMES`;
  the signature-parity test covers it, so the bound web implementation
  and the fallback stay signature-identical.

## [0.2.0] - 2026-09-24

### Added
- New **Research Lab** top-level tab (`ui/tabs/research_tab.py`) with an
  inner notebook of seven sub-tabs, one per new quant engine: **Pairs**
  (cointegration screening), **Order book** (LOB simulation), **Optimize**
  (Markowitz + frontier), **Monte Carlo** (correlated-GBM VaR), **Vol
  surface** (SVI fits), **Factors** (Fama-French regressions + GRS test),
  **Sentiment** (sentiment-vs-price verdict). All work runs through the
  existing background `Job`/`JobRunner` infrastructure; tkinter code only
  renders the plain-data results.
- Seven new engine services — `run_pairs_job`, `run_orderbook_job`,
  `run_optimize_job`, `run_montecarlo_job`, `run_vol_surface_job`,
  `run_factor_analysis_job`, `run_sentiment_price_job` — added to
  `_SERVICE_NAMES` and mirrored one-for-one in the stdlib-only
  `engine/services.py` fallback, with identical names and signatures to
  `trade_dashboard_web.engine.research_service` (the single source of
  truth in a meta-install). Each talks to its engine of record directly
  via lazy import with a pip-install hint.
- 9 new tests: service-name exposure, one fallback job test per engine,
  and a missing-engine hint test.

### Notes
- The factors panel fetches up to 750 days of demo bars (the demo cap),
  the minimum for the required 24 monthly return observations.
- Research Lab demo caveats match the web dashboard: synthetic vol
  quotes, synthetic factor dates, synthetic sentiment with a planted
  1-day lead. Real data plugs in through the same engine adapters.

## [0.1.1] - 2026-09-23

### Added
- New **Paper** tab wired to the `trade-paper` engine (lazy optional import):
  paper account/equity/buying power, open positions, strategy-approval queue
  with one-click approve, and a fidelity report comparing backtest slippage
  assumptions to realized paper slippage. Jobs run off the tkinter UI thread.
- New engine services `paper_available`, `paper_status`, `paper_approvals`,
  `paper_approve`, `paper_fidelity` — identical names and signatures in the
  shared web engine and the bundled stdlib fallback.

## [0.1.0] - 2026-09-23

### Added
- Dependency-free tkinter desktop dashboard (stdlib + tkinter only).
- Five tabs: Backtest Lab, Strategies, Agent Desk, Risk Review, Market Data.
- Pure-logic `engine/` package with no tkinter imports: market-data, strategy
  catalog, backtest, agent-desk, and risk-review services.
- Engine interoperability: reuses `trade_dashboard_web.engine` when the web
  dashboard package is installed (single source of truth in a meta-install);
  otherwise uses stdlib-only local equivalents with identical signatures.
- Lazy adapters to `trade-data-equities`, `trade-strategies`, `trade-backtest`,
  `trade-risk`, and `trade-agents`; deterministic synthetic demo data keeps
  every tab usable offline.
- Canvas equity-curve and candlestick charts (no matplotlib dependency).
- Background `JobRunner`: backtests and desk runs execute in daemon threads
  with results marshalled to the tkinter main thread, so the UI never blocks.
- License-key check hook (`engine/licensing.py`); community mode default.
- Update-check hook against GitHub releases (`engine/updates.py`), available
  from the Tools menu and on startup (opt-out with `--skip-update-check`).
- Windows distribution path: `build.py` (PyInstaller single-file),
  `build_exe.bat` (one-command build), `installer.iss` (Inno Setup).
- Entry points: `python -m trade_dashboard_desktop` and the
  `trade-dashboard-desktop` console script.
- MIT license, README, architecture doc, and test suite.
