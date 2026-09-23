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
present, all eight service names are bound to the web package's
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

## Future scaling seams

- `Job.target` is a plain callable: pointing it at a process pool or a task
  queue (instead of a thread) needs no tab changes.
- `engine` services return plain data, so a headless/CLI or web consumer can
  reuse them directly — the web dashboard already does.
- Charts render from precomputed geometry (`line_points`, `candle_layout`),
  so a different renderer (e.g. a GPU canvas) can slot in behind the same
  math.
