"""Paper tab: monitor the ``trade-paper`` engine (paper trading only)."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .. import helpers as H
from ..context import AppContext
from ..workers import Job


def _money(value) -> str:
    return f"${float(value):,.2f}"


def build(parent: tk.Widget, ctx: AppContext) -> ttk.Frame:
    frame = ttk.Frame(parent, padding=8)
    eng = ctx.engine

    # -- top controls -----------------------------------------------------
    top = ttk.Frame(frame)
    top.pack(fill="x", pady=(0, 6))
    cfg_var = H.entry_row(top, "Config", default="paper-config.json", width=40)
    refresh_btn = ttk.Button(top, text="Refresh")
    refresh_btn.pack(side="left", padx=6)
    status_var = tk.StringVar(value="press Refresh to load paper state")
    ttk.Label(top, textvariable=status_var, foreground="gray").pack(side="left", padx=8)

    # -- account ----------------------------------------------------------
    acct_box = ttk.LabelFrame(frame, text="Account (paper only)", padding=6)
    acct_box.pack(fill="x", pady=(0, 6))
    acct_var = tk.StringVar(value="—")
    ttk.Label(acct_box, textvariable=acct_var).pack(anchor="w")

    body = ttk.PanedWindow(frame, orient="horizontal")
    body.pack(fill="both", expand=True)

    # -- positions --------------------------------------------------------
    left = ttk.LabelFrame(body, text="Positions", padding=6)
    pos_tree = H.make_tree(left, [("symbol", 70), ("qty", 70),
                                  ("entry", 80), ("mark", 80), ("uPnL", 80)])
    pos_tree.pack(fill="both", expand=True)
    body.add(left, weight=1)

    # -- approvals --------------------------------------------------------
    mid = ttk.LabelFrame(body, text="Approvals (you decide)", padding=6)
    appr_tree = H.make_tree(mid, [("id", 40), ("strategy", 130),
                                  ("symbols", 90), ("score", 60)])
    appr_tree.pack(fill="both", expand=True)
    appr_btn = ttk.Button(mid, text="Approve selected")
    appr_btn.pack(anchor="e", pady=4)
    body.add(mid, weight=1)

    # -- fidelity ---------------------------------------------------------
    right = ttk.LabelFrame(body, text="Fidelity (backtest vs paper)", padding=6)
    fid_tree = H.make_tree(right, [("strategy", 130), ("fills", 50),
                                   ("avg bps", 70), ("gap bps", 70)])
    fid_tree.pack(fill="both", expand=True)
    fid_var = tk.StringVar(value="—")
    ttk.Label(right, textvariable=fid_var, foreground="gray").pack(anchor="w")
    body.add(right, weight=1)

    approval_ids: list[int] = []

    # -- jobs -------------------------------------------------------------
    def on_error(exc: Exception) -> None:
        status_var.set(f"Paper error: {exc}")
        ctx.status(f"Paper refresh failed: {exc}")
        refresh_btn.config(state="normal")

    def on_done(result: dict) -> None:
        s, appr, fid = result["status"], result["approvals"], result["fidelity"]
        acct_var.set(
            f"equity {_money(s['equity'])} · cash {_money(s['cash'])} · "
            f"buying power {_money(s['buying_power'])} · broker {s['broker']} · "
            f"{'market OPEN' if s['market_open'] else 'market closed'} · "
            f"{s['active_strategies']} active strategies · "
            f"{s['pending_approvals']} awaiting approval")
        H.set_tree_rows(pos_tree, [
            (p["symbol"], f"{p['qty']:.4f}", f"{p['avg_entry']:.2f}",
             f"{p['market']:.2f}", f"{p['unrealized']:.2f}")
            for p in s["positions"]])
        approval_ids.clear()
        rows = []
        for r in appr["approvals"]:
            approval_ids.append(r["id"])
            rows.append((r["id"], r["strategy"], r["symbols"],
                         f"{(r['score'] or 0):.2f}"))
        H.set_tree_rows(appr_tree, rows)
        H.set_tree_rows(fid_tree, [
            (name, d["fills"],
             "n/a" if d["avg_realized_slippage_bps"] is None else f"{d['avg_realized_slippage_bps']:.1f}",
             "n/a" if d["slippage_gap_bps"] is None else f"{d['slippage_gap_bps']:.1f}")
            for name, d in fid["strategies"].items()])
        fid_var.set(f"backtest assumption: {fid['assumed_slippage_bps']} bps · "
                    f"{fid['total_fills']} fills")
        status_var.set("loaded")
        ctx.status("Paper state loaded")
        refresh_btn.config(state="normal")

    def refresh() -> None:
        cfg = cfg_var.get().strip()
        refresh_btn.config(state="disabled")
        status_var.set("Loading paper state…")

        def target():
            return {"status": eng.paper_status(cfg),
                    "approvals": eng.paper_approvals(cfg, status="pending"),
                    "fidelity": eng.paper_fidelity(cfg)}

        ctx.submit(Job("paper-refresh", target, on_done=on_done, on_error=on_error))

    refresh_btn.config(command=refresh)

    def approve_selected() -> None:
        sel = appr_tree.selection()
        if not sel:
            status_var.set("select an approval row first")
            return
        aid = approval_ids[appr_tree.index(sel[0])]
        appr_btn.config(state="disabled")

        def target():
            return eng.paper_approve(cfg_var.get().strip(), aid,
                                     reason="approved from desktop dashboard")

        def done(_result):
            appr_btn.config(state="normal")
            status_var.set(f"approved #{aid}")
            refresh()

        def err(exc: Exception):
            appr_btn.config(state="normal")
            on_error(exc)

        ctx.submit(Job("paper-approve", target, on_done=done, on_error=err))

    appr_btn.config(command=approve_selected)
    return frame
