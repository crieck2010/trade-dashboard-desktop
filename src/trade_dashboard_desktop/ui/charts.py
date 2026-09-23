"""Canvas charts: pure scaling math (testable, no tkinter) + thin renderers."""

from __future__ import annotations


def line_points(values: list[float], width: int, height: int, pad: int = 8) -> list[tuple[float, float]]:
    """Map ``values`` to canvas (x, y) points.  Empty input -> []."""
    if not values or width <= 2 * pad or height <= 2 * pad:
        return []
    lo, hi = min(values), max(values)
    span = (hi - lo) or 1.0
    n = len(values)
    return [
        (
            pad + i * (width - 2 * pad) / max(n - 1, 1),
            height - pad - (v - lo) / span * (height - 2 * pad),
        )
        for i, v in enumerate(values)
    ]


def candle_layout(
    bars: list[dict], width: int, height: int, pad: int = 8
) -> list[dict]:
    """Compute candle geometry for ``bars`` (dicts with o/h/l/c keys).

    Returns one dict per bar: ``x``, ``body`` (x0, y0, x1, y1), ``wick``
    (x, y_high, y_low) and ``up`` bool.  Empty input -> [].
    """
    if not bars or width <= 2 * pad or height <= 2 * pad:
        return []
    lo = min(b["low"] for b in bars)
    hi = max(b["high"] for b in bars)
    span = (hi - lo) or 1.0

    def y(price: float) -> float:
        return height - pad - (price - lo) / span * (height - 2 * pad)

    slot = (width - 2 * pad) / len(bars)
    body_w = max(1.0, slot * 0.6)
    out = []
    for i, b in enumerate(bars):
        cx = pad + slot * (i + 0.5)
        up = b["close"] >= b["open"]
        out.append(
            {
                "x": cx,
                "body": (cx - body_w / 2, y(max(b["open"], b["close"])),
                         cx + body_w / 2, y(min(b["open"], b["close"]))),
                "wick": (cx, y(b["high"]), y(b["low"])),
                "up": up,
            }
        )
    return out


# --- canvas renderers (duck-typed canvas; only used with a real tk.Canvas) ---

UP_COLOR = "#2e7d32"
DOWN_COLOR = "#c62828"
LINE_COLOR = "#1565c0"
GRID_COLOR = "#e0e0e0"


def draw_equity_curve(canvas, curve: list[dict], width: int, height: int) -> None:
    """Render ``curve`` (list of {equity}) as a line chart on ``canvas``."""
    canvas.delete("all")
    values = [float(p["equity"]) for p in curve]
    pts = line_points(values, width, height)
    if len(pts) < 2:
        canvas.create_text(width // 2, height // 2, text="not enough data",
                           fill="gray")
        return
    flat = [c for p in pts for c in p]
    canvas.create_line(*flat, fill=LINE_COLOR, width=2)
    first, last = values[0], values[-1]
    canvas.create_text(10, 12, anchor="w", fill="gray",
                       text=f"${first:,.0f} → ${last:,.0f}")


def draw_candles(canvas, bars: list[dict], width: int, height: int) -> None:
    """Render OHLC ``bars`` as candlesticks on ``canvas``."""
    canvas.delete("all")
    layout = candle_layout(bars, width, height)
    if not layout:
        canvas.create_text(width // 2, height // 2, text="no bars", fill="gray")
        return
    for c in layout:
        color = UP_COLOR if c["up"] else DOWN_COLOR
        x0, y0, x1, y1 = c["body"]
        wx, wy_hi, wy_lo = c["wick"]
        canvas.create_line(wx, wy_hi, wx, wy_lo, fill=color)
        canvas.create_rectangle(x0, y0, x1, max(y1, y0 + 1), fill=color,
                                outline=color)
    lo = min(b["low"] for b in bars)
    hi = max(b["high"] for b in bars)
    canvas.create_text(10, 12, anchor="w", fill="gray",
                       text=f"low ${lo:,.2f}  high ${hi:,.2f}  n={len(bars)}")
