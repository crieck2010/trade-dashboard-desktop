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


# -- terminal-wave math helpers ------------------------------------------------

def test_underwater_curve():
    dd = charts.underwater_curve([100.0, 110.0, 99.0, 121.0])
    assert dd == [0.0, 0.0, -(110.0 - 99.0) / 110.0, 0.0]
    assert charts.underwater_curve([]) == []
    assert all(d <= 0 for d in charts.underwater_curve([3.0, 2.0, 1.0]))


def test_bar_layout_signed_and_zero_line():
    rects = charts.bar_layout([2.0, -1.0, 0.0], 300, 200)
    assert len(rects) == 3
    zy = charts.zero_line_y([2.0, -1.0, 0.0], 200)
    # positive bar sits above the zero line, negative below it
    assert rects[0][3] <= zy + 1e-9 and rects[0][1] <= rects[0][3]
    assert rects[1][1] >= zy - 1e-9
    assert charts.bar_layout([], 300, 200) == []


def test_heatmap_layout_shape():
    cells = charts.heatmap_layout(2, 12, 400, 200)
    assert len(cells) == 24
    assert cells[0]["row"] == 0 and cells[0]["col"] == 0
    assert cells[13]["row"] == 1 and cells[13]["col"] == 1
    assert cells[0]["x0"] < cells[0]["x1"] and cells[0]["y0"] < cells[0]["y1"]
    assert charts.heatmap_layout(0, 12, 400, 200) == []


def test_heatmap_color_diverging():
    assert charts.heatmap_color(None, -0.1, 0.1) == "#e8e8e8"
    pos = charts.heatmap_color(0.1, -0.1, 0.1)
    neg = charts.heatmap_color(-0.1, -0.1, 0.1)
    zero = charts.heatmap_color(0.0, -0.1, 0.1)
    assert pos != neg and zero == "#ffffff"
    assert pos.startswith("#") and len(pos) == 7


def test_gauge_layout_bounds():
    g = charts.gauge_layout(0.0, 400, 200)
    assert g["frac"] == 0.0
    nx, _ = g["needle"]
    assert abs(nx - (g["cx"] - g["r"])) < 1e-6  # pointing left at 0%
    g = charts.gauge_layout(1.5, 400, 200)  # clamped
    assert g["frac"] == 1.0
    g = charts.gauge_layout(0.5, 400, 200)
    assert g["needle"][1] < g["cy"]  # pointing up at 50%


def test_network_positions_scaling():
    nodes = [{"symbol": "A", "x": -100.0, "y": 100.0, "vol": 0.4,
              "cluster": 0},
             {"symbol": "B", "x": 100.0, "y": -100.0, "vol": 0.1,
              "cluster": 1}]
    pts = charts.network_positions(nodes, 400, 300, pad=20)
    assert len(pts) == 2
    assert pts[0]["x"] < pts[1]["x"] and pts[0]["y"] > pts[1]["y"]
    assert pts[0]["r"] > pts[1]["r"]  # higher vol -> larger node
    assert 5.0 <= pts[1]["r"] <= 16.0
    assert charts.network_positions([], 400, 300) == []
    assert charts.cluster_color(0) == charts.cluster_color(8)  # cycles
    assert charts.cluster_color(0) != charts.cluster_color(1)
    assert charts.edge_width(0.0) < charts.edge_width(-0.9) <= 6.0


def test_calibration_layout_skips_empty_bins():
    brier = {"bins": [0.05, 0.15], "observed": [0.0, None], "n": [4, 0]}
    lay = charts.calibration_layout(brier, 400, 300)
    assert len(lay["diag"]) == 2
    assert len(lay["points"]) == 1
    assert lay["points"][0]["p"] == 0.05
    assert lay["points"][0]["r"] >= 3.0


def _fake_canvas():
    class FakeCanvas:
        def __init__(self):
            self.calls = []

        def delete(self, *args):
            self.calls.append(("delete", args, {}))

        def create_line(self, *args, **kwargs):
            self.calls.append(("line", args, kwargs))

        def create_rectangle(self, *args, **kwargs):
            self.calls.append(("rect", args, kwargs))

        def create_text(self, *args, **kwargs):
            self.calls.append(("text", args, kwargs))

        def create_oval(self, *args, **kwargs):
            self.calls.append(("oval", args, kwargs))

        def create_polygon(self, *args, **kwargs):
            self.calls.append(("polygon", args, kwargs))

        def create_arc(self, *args, **kwargs):
            self.calls.append(("arc", args, kwargs))

    return FakeCanvas()


def test_draw_underwater_fill_and_line():
    c = _fake_canvas()
    charts.draw_underwater(c, [100.0, 90.0, 95.0, 80.0], 400, 300)
    kinds = [k for k, _, _ in c.calls]
    assert "line" in kinds and "polygon" in kinds
    assert any("max drawdown" in kw.get("text", "")
               for k, _, kw in c.calls if k == "text")


def test_draw_histogram_and_bars():
    c = _fake_canvas()
    charts.draw_histogram(c, {"bins": [0, 1, 2], "counts": [3, 5]}, 400, 300)
    assert len([1 for k, _, _ in c.calls if k == "rect"]) == 2
    c = _fake_canvas()
    charts.draw_bars(c, [("SPY", 10.0), ("QQQ", -5.0)], 400, 300)
    assert len([1 for k, _, _ in c.calls if k == "rect"]) == 2
    assert "line" in [k for k, _, _ in c.calls]  # zero line


def test_draw_heatmap_cells():
    c = _fake_canvas()
    charts.draw_heatmap(c, [2025], [[0.01, None] + [0.0] * 10], 400, 200)
    rects = [a for k, a, _ in c.calls if k == "rect"]
    assert len(rects) == 12
    c = _fake_canvas()
    charts.draw_heatmap(c, [], [], 400, 200)
    assert "text" in [k for k, _, _ in c.calls]


def test_draw_gauge_and_calibration():
    c = _fake_canvas()
    charts.draw_gauge(c, 0.725, "conviction 72.5%", 400, 200)
    kinds = [k for k, _, _ in c.calls]
    assert "arc" in kinds and "line" in kinds and "oval" in kinds
    c = _fake_canvas()
    charts.draw_calibration(c, {"bins": [0.05], "observed": [0.1],
                                "n": [10]}, 400, 300)
    assert "line" in [k for k, _, _ in c.calls]  # diagonal
    assert "oval" in [k for k, _, _ in c.calls]  # point
    c = _fake_canvas()
    charts.draw_calibration(c, {"bins": [], "observed": [], "n": []},
                            400, 300)
    assert "oval" not in [k for k, _, _ in c.calls]


def test_draw_network_static():
    c = _fake_canvas()
    result = {
        "nodes": [
            {"symbol": "A", "x": -50.0, "y": 0.0, "vol": 0.2, "cluster": 0},
            {"symbol": "B", "x": 50.0, "y": 0.0, "vol": 0.4, "cluster": 1},
        ],
        "edges": [{"a": 0, "b": 1, "weight": 0.8, "distance": 0.63}],
        "clusters": [{"id": 0, "members": ["A"]},
                     {"id": 1, "members": ["B"]}],
        "params": {"seed": 7},
    }
    charts.draw_network(c, result, 400, 300)
    kinds = [k for k, _, _ in c.calls]
    assert "line" in kinds and kinds.count("oval") == 2
    assert kinds.count("text") >= 2  # symbol labels
    c = _fake_canvas()
    charts.draw_network(c, {"nodes": []}, 400, 300)
    assert "text" in [k for k, _, _ in c.calls]
