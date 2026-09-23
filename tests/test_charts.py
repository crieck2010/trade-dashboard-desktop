"""Chart math tests (pure functions; canvas renderers via a fake canvas)."""

from __future__ import annotations

from trade_dashboard_desktop.ui import charts
from trade_dashboard_desktop.ui.charts import candle_layout, line_points


def test_line_points_empty():
    assert line_points([], 400, 300) == []
    assert line_points([1.0], 10, 10) == []  # too small to draw


def test_line_points_maps_min_to_bottom_max_to_top():
    pts = line_points([0.0, 5.0, 10.0], 100, 100, pad=10)
    assert len(pts) == 3
    xs = [p[0] for p in pts]
    assert xs == sorted(xs)
    # max value -> top (small y), min value -> bottom (large y)
    assert pts[2][1] < pts[1][1] < pts[0][1]
    assert pts[2][1] == 10  # top pad
    assert pts[0][1] == 90  # bottom pad


def test_line_points_degenerate_flat_series():
    pts = line_points([5.0, 5.0, 5.0], 100, 100)
    assert len(pts) == 3
    assert all(isinstance(p[0], float) and isinstance(p[1], float) for p in pts)


def test_candle_layout_empty():
    assert candle_layout([], 400, 300) == []


def test_candle_layout_up_down():
    bars = [
        {"open": 100.0, "high": 105.0, "low": 99.0, "close": 104.0},
        {"open": 104.0, "high": 104.5, "low": 98.0, "close": 99.0},
    ]
    layout = candle_layout(bars, 200, 200)
    assert len(layout) == 2
    assert layout[0]["up"] is True
    assert layout[1]["up"] is False
    for c in layout:
        x0, y0, x1, y1 = c["body"]
        assert x0 < x1 and y0 <= y1
        wx, wy_hi, wy_lo = c["wick"]
        assert wy_hi <= wy_lo


class FakeCanvas:
    def __init__(self):
        self.calls = []

    def delete(self, *args):
        self.calls.append(("delete", args))

    def create_line(self, *args, **kwargs):
        self.calls.append(("line", args))

    def create_rectangle(self, *args, **kwargs):
        self.calls.append(("rect", args))

    def create_text(self, *args, **kwargs):
        self.calls.append(("text", args))


def test_draw_equity_curve_calls_line():
    canvas = FakeCanvas()
    curve = [{"equity": 100000 + i * 100} for i in range(50)]
    charts.draw_equity_curve(canvas, curve, 400, 300)
    kinds = [k for k, _ in canvas.calls]
    assert "line" in kinds


def test_draw_equity_curve_not_enough_data():
    canvas = FakeCanvas()
    charts.draw_equity_curve(canvas, [], 400, 300)
    kinds = [k for k, _ in canvas.calls]
    assert "text" in kinds and "line" not in kinds


def test_draw_candles_creates_rectangles():
    canvas = FakeCanvas()
    bars = [
        {"open": 100.0, "high": 105.0, "low": 99.0, "close": 104.0 + (i % 3 - 1)}
        for i in range(10)
    ]
    charts.draw_candles(canvas, bars, 400, 300)
    rects = [c for k, c in canvas.calls if k == "rect"]
    assert len(rects) == 10
