# Architecture

## Layering

```
┌─────────────────────────────────────────────────────────┐
│ ui/            tkinter views — zero business logic       │
│  app.py        main window, menus, status bar            │
│  tabs/*        one build(parent, ctx) -> Frame per tab   │
│  charts.py     pure scaling math + thin canvas renderers │
│  workers.py    JobRunner: threads → after() polling     │
├─────────────────────────────────────────────────────────┤
│ engine/        pure logic — zero tkinter imports         │
│  __init__.py   reuse-or-fallback binding                 │
│  services.py   stdlib-only service implementations      │
│  licensing.py  license-key hook                         │
│  updates.py    GitHub-releases update check             │
├─────────────────────────────────────────────────────────┤
│ siblings (lazy)  trade-data-equities, trade-strategies, │
│                  trade-backtest, trade-risk, trade-agents│
│                  — imported inside functions, never at  │
│                  module top level                       │
└─────────────────────────────────────────────────────────┘
```

The dependency rule is strict: `engine/` may not import `tkinter`, and
`ui/` may not implement business logic — tabs call engine services and
render plain-data results. This keeps the engine importable, testable, and
reusable without a display (e.g. from scripts or the future `trade-suite`
meta-package).

## Engine reuse with trade-dashboard-web

`engine/__init__.py` tries `import trade_dashboard_web.engine` first. When
present, all service names are bound to the web package's
implementations, so both dashboards share one codebase and produce identical
results. When absent, the stdlib-only `engine/services.py` fallback provides
the same names and signatures. `engine.USING_SHARED_ENGINE` records which
binding is active (also shown in the status bar).

The fallback is a deliberate mirror, not a fork: a test asserts the bound
signatures equal the fallback signatures, so the reuse contract is checked
on every test run.

## Data flow per tab

- **Backtest Lab**: `DataService.get_bars` → `run_backtest_job` (strategy
  from `trade-strategies`, execution from `trade-backtest`) → metrics dict,
  equity-curve list, trades list → canvas + treeview.
- **Strategies**: `list_strategies` → registry metadata → listbox/detail pane.
- **Agent Desk**: per-symbol `get_bars` → `run_desk_job`
  (`trade-agents` desk: researchers → portfolio manager → risk manager) →
  `DeskReport.to_dict()` → briefs/ideas/allocations/orders/vetoes views.
- **Risk Review**: `describe_limits` → limit picker → `evaluate_orders_job`
  (`trade-agents` risk agent over `trade-risk` limits, cumulative fills) →
  approved/vetoed views.
- **Paper**: `paper_status` / `paper_approvals` / `paper_fidelity`
  (`trade-paper` engine, lazy import, background jobs) → account line,
  positions/approvals/fidelity treeviews; `paper_approve` on selected row.
  Paper-only: nothing in this tab can reach a live broker — `trade-paper`
  refuses live Alpaca endpoints in code.
- **Trades**: `run_trades_job` → blotter rows → treeview; `trades_to_csv`
  → Save-As dialog bytes.
- **Performance**: `run_performance_job` → summary cards + canvas charts
  (equity, underwater, heatmap, rolling, histogram).
- **Agents**: `run_agent_activity_job` → leaderboard trees, Elo line per
  selected agent, Brier calibration canvas, debate/queue trees.
- **Network**: `run_network_job` → `draw_network` static canvas render +
  cluster listbox + node combobox → top correlations.
- **Risk Monitor**: `run_risk_monitor_job` → exposure bars, Herfindahl
  readout, vol timeline, kill-switch pill, conviction gauge.
- **Market Data**: `get_bars` → `candle_layout` math → canvas.

Bars cross every boundary as plain dicts (`bar_to_dict`), so no engine types
leak into the UI.

## Concurrency

`JobRunner.submit(Job)` runs the job target on a daemon thread and queues a
`JobResult`. The tkinter main loop polls the queue via `after()` (bounded to
8 results per tick) and invokes `on_done`/`on_error` on the main thread —
the only thread that touches widgets. Callbacks are exception-guarded so a
bad callback can never kill the poll loop.

## Offline behavior

`DataService` always offers the `demo` source: deterministic synthetic bars
(`synth_bars`, seeded per symbol) with three regimes. Every tab is fully
usable with no network and no sibling packages installed. The `equities`
source activates when `trade-data-equities` (+ `yfinance`) is importable;
availability is reported by `DataService.sources()` and shown in the source
pickers.

## Packaging

`build.py` drives PyInstaller (`--onefile --windowed`) with `src/` on the
module path; tkinter's data files come from PyInstaller's own hooks, so no
manual `datas` entries are needed. `build_exe.bat` is the one-command Windows
flow; `installer.iss` produces the Inno Setup installer. Native builds must
run on Windows — PyInstaller targets its host OS.

## Research Lab (0.2.0, extended 0.3.0)

One top-level **Research Lab** tab (`ui/tabs/research_tab.py`) holds an
inner `ttk.Notebook` with eight sub-tabs — Pairs, Order book, Optimize,
Monte Carlo, Vol surface, Factors, Sentiment, Correlations — one per quant
engine. The eight service names (`run_pairs_job`, `run_orderbook_job`,
`run_optimize_job`, `run_montecarlo_job`, `run_vol_surface_job`,
`run_factor_analysis_job`, `run_sentiment_price_job`,
`run_correlation_job`) were added to
`_SERVICE_NAMES` and mirrored one-for-one in the stdlib-only fallback
`engine/services.py`, with identical names and signatures to
`trade_dashboard_web.engine.research_service` (the single source of truth
in a meta-install). Each fallback job imports its engine of record
directly with a `pip install` hint when absent.

Panels keep the tab contract: controls collect plain inputs, the engine
does all the work in a background `Job`, and the panel renders the
plain-data result (trees, metric rows, or a verdict text block). The
factors panel fetches up to 750 days of demo bars (the demo cap) to reach
the 24-month floor for Fama-French regressions.

## Terminal wave (0.5.0)

Five top-level tabs — Trades, Performance, Agents, Network, Risk Monitor —
mirror the `trade-dashboard-web` v0.5.0 terminal wave one-for-one. The five
canonical jobs (`run_trades_job`, `run_performance_job`,
`run_agent_activity_job`, `run_network_job`, `run_risk_monitor_job`) plus
`trades_to_csv` are registered in `_SERVICE_NAMES` and mirrored in the
stdlib-only `engine/services.py` fallback with identical signatures; a
cross-check test asserts byte-identical results on every deterministic
demo path. The fallback docstring states the degraded behavior per job
(none on the demo paths; on the real network path the correlation matrix
comes from this package's own `run_correlation_job` — needs `trade-eda` —
where the web job uses its research_service).

`docs/PARITY.md` enumerates the desktop parity split exactly: full,
simplified (Elo sparklines → per-agent line chart), or static (network —
one canvas render of the engine-computed layout, menu-driven exploration).
Charts live in `ui/charts.py` as pure-math helpers + thin renderers
(`underwater_curve`, `bar_layout`, `heatmap_layout`/`heatmap_color`,
`gauge_layout`, `network_positions`/`edge_width`/`cluster_color`,
`calibration_layout` and the matching `draw_*` renderers). No engine math
lives in the tab modules.

## Future scaling seams

- `Job.target` is a plain callable: pointing it at a process pool or a task
  queue (instead of a thread) needs no tab changes.
- `engine` services return plain data, so a headless/CLI or web consumer can
  reuse them directly — the web dashboard already does.
- Charts render from precomputed geometry (`line_points`, `candle_layout`),
  so a different renderer (e.g. a GPU canvas) can slot in behind the same
  math.
