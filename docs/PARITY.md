# Desktop parity — web flagship vs trade-dashboard-desktop (v0.5.0)

The web dashboard is the **flagship** for the terminal wave; this desktop
app receives **simplified parity**. The contract is the same either way:
the desktop calls the canonical `run_*_job` functions from
`trade_dashboard_web.engine.terminal_service` whenever the web package is
installed (`engine.USING_SHARED_ENGINE` is `True`, shown in the status
bar). No reimplementation of the math — the numbers are identical; only
presentation differs. When the web package is absent, the stdlib-only
fallback in `engine/services.py` runs the same algorithms with identical
signatures (byte-identical results on every deterministic demo path, as
the cross-check tests assert).

## View-by-view split

| Terminal view | Desktop parity | Notes |
|---|---|---|
| Trades blotter + CSV | **Full**: filter table; CSV export via Save-As dialog | Same job; tkinter Treeview |
| Performance: summary cards, equity, underwater, monthly heatmap, histogram | **Full**: canvas renders, tabbed sub-views | Canvas instead of matplotlib; same numbers |
| Performance: rolling Sharpe/vol | **Full**: same lines on canvas | |
| Agents: leaderboards, Brier chart, debate timeline, approval queue | **Full**: tables + static canvas chart | |
| Agents: Elo sparklines | **Simplified**: numeric rating per agent + one canvas line per *selected* agent | No in-cell SVG in tkinter |
| Network: SVG graph, pan/zoom, hover tooltips, click-a-node detail | **Static subset**: one canvas rendering (edge width by \|ρ\|, node color by cluster, node size by vol, node labels); clusters as a listbox; top-correlations for the selected node via a combobox | tkinter can't do the interactive SVG; the topology data (nodes/edges/clusters) is identical, only exploration is menu-driven |
| Risk: exposure bars, Herfindahl, vol-regime timeline, kill-switch pill, conviction gauge | **Full**: canvas bars/line/gauge + headline labels | |

## What's intentionally static on desktop

- **Network pan/zoom and hover tooltips**: no equivalent widget in
  tkinter; replaced by a cluster listbox + node selector combobox. The
  layout itself is still the engine's seeded, deterministic
  Fruchterman-Reingold result — what is static is the *exploration*, not
  the data.
- **Elo in-cell sparklines**: replaced by per-agent rating numbers plus a
  per-agent line chart.

## What's never duplicated

The jobs themselves: `run_trades_job` / `run_performance_job` /
`run_agent_activity_job` / `run_network_job` / `run_risk_monitor_job`
(and the `trades_to_csv` export helper). Any future change in the math
lands in both dashboards by upgrading the shared package (or by
mirroring it into `engine/services.py` for the standalone fallback).

## DEMO banners

Whenever a job reports `demo: True` (no paper ledger / no track record /
no hedge state found), the tab shows a gold DEMO banner: the rows are
deterministic synthetic plumbing data, never presented as real.
