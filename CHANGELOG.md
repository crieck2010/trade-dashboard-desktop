# Changelog

All notable changes to `trade-dashboard-desktop` are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and versioning follows [Semantic Versioning](https://semver.org/).

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
