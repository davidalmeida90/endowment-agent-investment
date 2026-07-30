"""
taa.charts — inline SVG, drawn from the data, in the Coldbrook Capital system.

Every chart in the report and the dashboard is generated here as an SVG string
and written into the HTML. No chart library, no CDN, no network, no image of a
chart. The report opens from disk on a machine that has never seen it and looks
exactly the same.

Design rules, taken from ds/colors_and_type.css and the component previews in
ds/preview/ rather than from memory:

  Charts sit inside a flat light-grey panel with the title INSIDE the panel,
  centred, all caps navy, and the unit note directly under it in slate.
  Horizontal gridlines only, very light. No chart border, no shadow, no
  rounded corners, no gradient used as decoration.

  Series order is fixed: navy first, clay second. The benchmark is slate and
  always dashed. The only third hue in the system is a muted gold used for a
  dashed reference line, which is where a mandate limit is drawn.

  THERE IS NO RED AND GREEN. Direction is carried by navy against clay, by
  parentheses on negatives, and by position relative to a zero axis. In a
  diverging bar chart navy adds and clay detracts. Roughly one man in twelve
  cannot separate red from green and a trustee document is the wrong place to
  find that out.

  Numerals are tabular lining everywhere, so columns of figures line up.
"""

from __future__ import annotations

import math
from html import escape

# Tokens, transcribed from ds/colors_and_type.css. The stylesheet is the
# authority; these mirror it because SVG attributes cannot read CSS variables
# when the file is opened directly from disk in every browser.
NAVY = "#0C1E48"
NAVY_SOFT = "#24365A"
CLAY = "#C08878"
CLAY_DEEP = "#A45E52"
CLAY_TINT = "#E8D2C9"
BLUSH = "#F2EBE5"
PANEL = "#E4EAEA"
SLATE = "#7E8A9C"
HAIRLINE = "#D4DBE0"
PAPER = "#FFFFFF"
INK = "#1A1F28"
SERIES_3 = "#4F86B0"
SERIES_4 = "#B8C4CE"
BENCHMARK = "#7E8A9C"
REFERENCE = "#A8935F"

FONT = "'Source Sans 3','Segoe UI',system-ui,sans-serif"

SERIES = [NAVY, CLAY, SERIES_3, SERIES_4]


def _e(s) -> str:
    return escape(str(s), quote=True)


def _n(x: float, dp: int = 2) -> str:
    """House number format: negatives in parentheses, tabular, never coloured."""
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return "—"
    s = f"{abs(x):,.{dp}f}"
    return f"({s})" if x < 0 else s


def _nice(lo: float, hi: float, ticks: int = 4) -> tuple[float, float, float]:
    """A readable axis domain and step."""
    if hi <= lo:
        hi = lo + 1.0
    raw = (hi - lo) / max(1, ticks)
    mag = 10 ** math.floor(math.log10(raw)) if raw > 0 else 1.0
    for m in (1, 2, 2.5, 5, 10):
        if raw / mag <= m:
            step = m * mag
            break
    else:
        step = 10 * mag
    return math.floor(lo / step) * step, math.ceil(hi / step) * step, step


class Panel:
    """A chart panel: flat grey fill, title inside, unit note under the title."""

    def __init__(self, width: int, height: int, title: str, unit: str = "",
                 pad_l: int = 52, pad_r: int = 18, pad_t: int = 46, pad_b: int = 34,
                 panelled: bool = True):
        self.w, self.h = width, height
        self.title, self.unit = title, unit
        self.pl, self.pr, self.pt, self.pb = pad_l, pad_r, pad_t, pad_b
        self.panelled = panelled
        self.parts: list[str] = []
        if unit:
            self.pt += 10

    @property
    def px0(self) -> float: return self.pl

    @property
    def px1(self) -> float: return self.w - self.pr

    @property
    def py0(self) -> float: return self.pt

    @property
    def py1(self) -> float: return self.h - self.pb

    def add(self, s: str) -> None:
        self.parts.append(s)

    def render(self) -> str:
        head = []
        if self.panelled:
            head.append(f'<rect x="0" y="0" width="{self.w}" height="{self.h}" fill="{PANEL}"/>')
        head.append(
            f'<text x="{self.w/2:.1f}" y="22" text-anchor="middle" font-size="12.5" '
            f'font-weight="600" fill="{NAVY}" letter-spacing="0.04em" '
            f'style="text-transform:uppercase">{_e(self.title)}</text>')
        if self.unit:
            head.append(
                f'<text x="{self.w/2:.1f}" y="37" text-anchor="middle" font-size="10" '
                f'fill="{SLATE}">{_e(self.unit)}</text>')
        return (f'<svg viewBox="0 0 {self.w} {self.h}" width="100%" '
                f'preserveAspectRatio="xMidYMid meet" role="img" '
                f'aria-label="{_e(self.title)}" '
                f'style="display:block;font-family:{FONT};'
                f'font-variant-numeric:tabular-nums lining-nums">'
                + "".join(head) + "".join(self.parts) + "</svg>")


class YAxis:
    def __init__(self, p: Panel, lo: float, hi: float, ticks: int = 4,
                 fmt=lambda v: _n(v, 0), gridlines: bool = True, zero_rule: bool = True):
        self.p = p
        self.lo, self.hi, self.step = _nice(lo, hi, ticks)
        self.fmt = fmt
        if gridlines:
            v = self.lo
            while v <= self.hi + 1e-9:
                y = self.y(v)
                is_zero = abs(v) < 1e-12
                p.add(f'<line x1="{p.px0}" y1="{y:.1f}" x2="{p.px1}" y2="{y:.1f}" '
                      f'stroke="{NAVY if (is_zero and zero_rule) else HAIRLINE}" '
                      f'stroke-width="{1 if is_zero and zero_rule else 1}"/>')
                p.add(f'<text x="{p.px0-7:.1f}" y="{y+3.5:.1f}" text-anchor="end" '
                      f'font-size="9.5" fill="{SLATE}">{_e(self.fmt(v))}</text>')
                v += self.step

    def y(self, v: float) -> float:
        if self.hi == self.lo:
            return (self.p.py0 + self.p.py1) / 2
        t = (v - self.lo) / (self.hi - self.lo)
        return self.p.py1 - t * (self.p.py1 - self.p.py0)


def _xs(p: Panel, n: int, inset: float = 0.0) -> list[float]:
    if n <= 1:
        return [(p.px0 + p.px1) / 2]
    a, b = p.px0 + inset, p.px1 - inset
    return [a + i * (b - a) / (n - 1) for i in range(n)]


def _xlabels(p: Panel, xs: list[float], labels: list[str], every: int = 1,
             y: float | None = None) -> None:
    y = y if y is not None else p.py1 + 15
    for i, (x, lb) in enumerate(zip(xs, labels)):
        if lb and i % every == 0:
            p.add(f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="middle" '
                  f'font-size="9.5" fill="{SLATE}">{_e(lb)}</text>')


def legend(items: list[tuple[str, str, str]], width: int) -> str:
    """items: (label, colour, style) where style is 'line', 'dash' or 'block'."""
    if not items:
        return ""
    cells = []
    for label, colour, style in items:
        if style == "dash":
            sw = (f'<span style="display:inline-block;width:16px;'
                  f'border-top:2px dashed {colour};vertical-align:middle;margin-right:6px"></span>')
        elif style == "block":
            sw = (f'<span style="display:inline-block;width:13px;height:9px;'
                  f'background:{colour};vertical-align:middle;margin-right:5px"></span>')
        else:
            sw = (f'<span style="display:inline-block;width:16px;height:2px;'
                  f'background:{colour};vertical-align:middle;margin-right:6px"></span>')
        cells.append(f'<span style="white-space:nowrap">{sw}{_e(label)}</span>')
    return (f'<div style="display:flex;gap:18px;justify-content:center;flex-wrap:wrap;'
            f'font-size:10px;color:{INK};margin:6px 0 0">' + "".join(cells) + "</div>")


# ==========================================================================
# Charts
# ==========================================================================
def line_chart(series: list[dict], labels: list[str], title: str, unit: str = "",
               width: int = 860, height: int = 250, ticks: int = 4,
               fmt=lambda v: _n(v, 0), label_every: int = 6,
               reference: tuple[float, str] | None = None,
               end_labels: bool = True) -> str:
    """
    series: [{"name":..., "values":[...], "colour":..., "dash":bool, "width":float}]
    reference: (value, label) drawn as the dashed gold reference line.
    """
    p = Panel(width, height, title, unit)
    vals = [v for s in series for v in s["values"] if v is not None and not math.isnan(v)]
    if reference:
        vals.append(reference[0])
    if not vals:
        return p.render()
    ax = YAxis(p, min(vals), max(vals), ticks, fmt)
    n = max(len(s["values"]) for s in series)
    xs = _xs(p, n)
    _end_label_ys: list[float] = []

    if reference:
        rv, rl = reference
        y = ax.y(rv)
        p.add(f'<line x1="{p.px0}" y1="{y:.1f}" x2="{p.px1}" y2="{y:.1f}" '
              f'stroke="{REFERENCE}" stroke-width="2" stroke-dasharray="10 6"/>')
        p.add(f'<text x="{p.px1-3:.1f}" y="{y-6:.1f}" text-anchor="end" font-size="10.5" '
              f'font-weight="600" fill="{REFERENCE}">{_e(rl)}</text>')

    for i, s in enumerate(series):
        colour = s.get("colour", SERIES[i % len(SERIES)])
        dash = ' stroke-dasharray="6 4"' if s.get("dash") else ""
        pts, run = [], []
        for x, v in zip(xs, s["values"]):
            if v is None or (isinstance(v, float) and math.isnan(v)):
                if run:
                    pts.append(run)
                    run = []
                continue
            run.append(f"{x:.1f},{ax.y(v):.1f}")
        if run:
            pts.append(run)
        for seg in pts:
            if len(seg) > 1:
                p.add(f'<polyline fill="none" stroke="{colour}" '
                      f'stroke-width="{s.get("width", 2.2)}"{dash} '
                      f'points="{" ".join(seg)}"/>')
            elif seg:
                x, y = seg[0].split(",")
                p.add(f'<circle cx="{x}" cy="{y}" r="2.2" fill="{colour}"/>')
        if end_labels and s["values"]:
            last = next((v for v in reversed(s["values"])
                         if v is not None and not math.isnan(v)), None)
            if last is not None:
                # Two series ending at similar values collide here and print one
                # number on top of another, which in a report of figures is worse
                # than no label. Push them apart vertically instead.
                y = ax.y(last) - 7
                for prev in _end_label_ys:
                    if abs(y - prev) < 13:
                        y = prev + 13 if y >= prev else prev - 13
                _end_label_ys.append(y)
                p.add(f'<text x="{p.px1-2:.1f}" y="{y:.1f}" text-anchor="end" '
                      f'font-size="11" font-weight="600" fill="{colour}">'
                      f'{_e(fmt(last))}</text>')

    _xlabels(p, xs, labels, label_every)
    return p.render()


def underwater(values: list[float], labels: list[str], title: str, unit: str = "",
               limit: float | None = None, limit_label: str = "",
               width: int = 860, height: int = 230, fmt=lambda v: _n(v, 1),
               label_every: int = 6) -> str:
    """Drawdown. Only ever negative, so the zero rule sits at the top."""
    p = Panel(width, height, title, unit)
    lo = min([v for v in values if v is not None] + ([limit] if limit else [0]))
    ax = YAxis(p, lo * 1.08, 0.0, 4, fmt)
    xs = _xs(p, len(values))

    pts = [f"{x:.1f},{ax.y(v):.1f}" for x, v in zip(xs, values) if v is not None]
    if pts:
        area = f"{xs[0]:.1f},{ax.y(0):.1f} " + " ".join(pts) + f" {xs[-1]:.1f},{ax.y(0):.1f}"
        p.add(f'<polygon points="{area}" fill="rgba(192,136,120,.35)"/>')
        p.add(f'<polyline fill="none" stroke="{CLAY}" stroke-width="2" '
              f'points="{" ".join(pts)}"/>')

    if limit is not None:
        y = ax.y(limit)
        p.add(f'<line x1="{p.px0}" y1="{y:.1f}" x2="{p.px1}" y2="{y:.1f}" '
              f'stroke="{REFERENCE}" stroke-width="2" stroke-dasharray="10 6"/>')
        p.add(f'<text x="{p.px1-3:.1f}" y="{y+13:.1f}" text-anchor="end" font-size="10.5" '
              f'font-weight="600" fill="{REFERENCE}">{_e(limit_label)}</text>')

    valid = [(i, v) for i, v in enumerate(values) if v is not None]
    if valid:
        i, v = min(valid, key=lambda t: t[1])
        p.add(f'<circle cx="{xs[i]:.1f}" cy="{ax.y(v):.1f}" r="3.5" fill="{NAVY}"/>')
        anchor = "start" if xs[i] < (p.px0 + p.px1) / 2 else "end"
        dx = 8 if anchor == "start" else -8
        p.add(f'<text x="{xs[i]+dx:.1f}" y="{ax.y(v)+4:.1f}" text-anchor="{anchor}" '
              f'font-size="10.5" font-weight="600" fill="{NAVY}">'
              f'{_e(fmt(v))}  {_e(labels[i] if i < len(labels) else "")}</text>')

    _xlabels(p, xs, labels, label_every)
    return p.render()


def diverging_bars(items: list[tuple[str, float]], title: str, unit: str = "",
                   width: int = 420, height: int | None = None,
                   fmt=lambda v: _n(v, 0), name_w: int = 118, val_w: int = 52,
                   pos_label: str = "Added", neg_label: str = "Detracted") -> str:
    """
    Horizontal bars across a centred zero. Navy adds, clay detracts. No hue
    carries direction beyond those two, and the value is printed either way.
    """
    row_h = 19
    height = height or (46 + 14 + row_h * len(items))
    p = Panel(width, height, title, unit, pad_l=name_w + 6, pad_r=val_w + 6, pad_b=12)
    if not items:
        return p.render()
    m = max(abs(v) for _, v in items) or 1.0
    x0, x1 = p.px0, p.px1
    mid = (x0 + x1) / 2
    top = p.py0 + 4

    p.add(f'<line x1="{mid:.1f}" y1="{top-3:.1f}" x2="{mid:.1f}" '
          f'y2="{top + row_h*len(items):.1f}" stroke="{NAVY}" stroke-width="1"/>')
    for i, (name, v) in enumerate(items):
        y = top + i * row_h
        cy = y + row_h / 2
        w = abs(v) / m * (x1 - x0) / 2 * 0.94
        colour = NAVY if v >= 0 else CLAY
        bx = mid if v >= 0 else mid - w
        p.add(f'<rect x="{bx:.1f}" y="{cy-5.5:.1f}" width="{w:.1f}" height="11" fill="{colour}"/>')
        p.add(f'<text x="{x0-9:.1f}" y="{cy+3.5:.1f}" text-anchor="end" font-size="11" '
              f'fill="{INK}">{_e(name)}</text>')
        p.add(f'<text x="{x1+9:.1f}" y="{cy+3.5:.1f}" text-anchor="start" font-size="11" '
              f'fill="{INK}">{_e(fmt(v))}</text>')
    return p.render()


def column_pairs(groups: list[str], a: list[float], b: list[float],
                 a_name: str, b_name: str, title: str, unit: str = "",
                 width: int = 860, height: int = 250, fmt=lambda v: _n(v, 1),
                 value_labels: bool = True) -> str:
    """Paired columns, navy against clay, crossing a centred zero where needed."""
    p = Panel(width, height, title, unit, pad_b=40)
    vals = [v for v in a + b if v is not None and not math.isnan(v)]
    if not vals:
        return p.render()
    ax = YAxis(p, min(vals + [0.0]), max(vals + [0.0]), 4, fmt)
    n = len(groups)
    slot = (p.px1 - p.px0) / max(1, n)
    bw = min(30.0, slot * 0.32)
    zero = ax.y(0.0)
    for i, g in enumerate(groups):
        cx = p.px0 + slot * (i + 0.5)
        for j, (vals_, colour) in enumerate(((a, NAVY), (b, CLAY))):
            v = vals_[i] if i < len(vals_) else None
            if v is None or math.isnan(v):
                continue
            x = cx - bw - 1 + j * (bw + 2)
            y = min(ax.y(v), zero)
            h = abs(ax.y(v) - zero)
            p.add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" '
                  f'height="{max(h,0.6):.1f}" fill="{colour}"/>')
            if value_labels:
                ly = (y - 4) if v >= 0 else (y + h + 10)
                p.add(f'<text x="{x+bw/2:.1f}" y="{ly:.1f}" text-anchor="middle" '
                      f'font-size="9.5" font-weight="600" fill="{colour}">{_e(fmt(v))}</text>')
        p.add(f'<text x="{cx:.1f}" y="{p.py1+16:.1f}" text-anchor="middle" '
              f'font-size="10" fill="{SLATE}">{_e(g)}</text>')
    return p.render()


def bar_series(values: list[float], labels: list[str], title: str, unit: str = "",
               width: int = 860, height: int = 200, fmt=lambda v: _n(v, 1),
               label_every: int = 6, threshold: float | None = None,
               threshold_label: str = "") -> str:
    """A long run of columns crossing zero. Navy above, clay below."""
    p = Panel(width, height, title, unit, pad_b=32)
    vals = [v for v in values if v is not None and not math.isnan(v)]
    if not vals:
        return p.render()
    hi = max(vals + [0.0])
    lo = min(vals + [0.0])
    if threshold is not None:
        hi, lo = max(hi, threshold), min(lo, threshold)
    ax = YAxis(p, lo, hi, 4, fmt)
    n = len(values)
    slot = (p.px1 - p.px0) / max(1, n)
    bw = max(1.6, slot * 0.66)
    zero = ax.y(0.0)
    for i, v in enumerate(values):
        if v is None or math.isnan(v):
            continue
        cx = p.px0 + slot * (i + 0.5)
        y = min(ax.y(v), zero)
        h = abs(ax.y(v) - zero)
        p.add(f'<rect x="{cx-bw/2:.1f}" y="{y:.1f}" width="{bw:.1f}" '
              f'height="{max(h,0.5):.1f}" fill="{NAVY if v >= 0 else CLAY}"/>')
    if threshold is not None:
        y = ax.y(threshold)
        p.add(f'<line x1="{p.px0}" y1="{y:.1f}" x2="{p.px1}" y2="{y:.1f}" '
              f'stroke="{REFERENCE}" stroke-width="2" stroke-dasharray="10 6"/>')
        p.add(f'<text x="{p.px1-3:.1f}" y="{y-6:.1f}" text-anchor="end" font-size="10.5" '
              f'font-weight="600" fill="{REFERENCE}">{_e(threshold_label)}</text>')
    xs = [p.px0 + slot * (i + 0.5) for i in range(n)]
    _xlabels(p, xs, labels, label_every)
    return p.render()


def range_bars(rows: list[dict], title: str, unit: str = "",
               width: int = 860, height: int | None = None) -> str:
    """
    Each line's permitted range as a track, policy as a tick, current position
    as a mark. This is the corridor chart: it shows at a glance which lines are
    near a bound, which is the fact a range constraint exists to surface.
    rows: {"name","lo","hi","policy","current"}
    """
    row_h = 24
    height = height or (52 + 18 + row_h * len(rows))
    p = Panel(width, height, title, unit, pad_l=142, pad_r=104, pad_b=16)
    if not rows:
        return p.render()
    lo = min(r["lo"] for r in rows)
    hi = max(r["hi"] for r in rows)
    span = (hi - lo) or 1.0

    def X(v):
        return p.px0 + (v - lo) / span * (p.px1 - p.px0)

    top = p.py0
    for i, r in enumerate(rows):
        y = top + i * row_h
        cy = y + row_h / 2
        p.add(f'<rect x="{X(r["lo"]):.1f}" y="{cy-6:.1f}" '
              f'width="{max(X(r["hi"])-X(r["lo"]),1):.1f}" height="12" fill="{CLAY_TINT}"/>')
        px = X(r["policy"])
        p.add(f'<line x1="{px:.1f}" y1="{cy-9:.1f}" x2="{px:.1f}" y2="{cy+9:.1f}" '
              f'stroke="{SLATE}" stroke-width="1.5" stroke-dasharray="3 2"/>')
        cx = X(r["current"])
        p.add(f'<rect x="{min(px,cx):.1f}" y="{cy-3:.1f}" '
              f'width="{abs(cx-px):.1f}" height="6" fill="{NAVY}" opacity="0.85"/>')
        p.add(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="4.2" fill="{NAVY}"/>')
        p.add(f'<text x="{p.px0-10:.1f}" y="{cy+3.5:.1f}" text-anchor="end" '
              f'font-size="11" fill="{INK}">{_e(r["name"])}</text>')
        p.add(f'<text x="{p.px1+10:.1f}" y="{cy+3.5:.1f}" text-anchor="start" '
              f'font-size="10.5" fill="{INK}">{_n(r["current"]*100,1)} '
              f'<tspan fill="{SLATE}">/ {_n(r["policy"]*100,1)}</tspan></text>')
    return p.render()


def heat_grid(rows: list[str], cols: list[str], values: list[list[float]],
              title: str, unit: str = "", width: int = 860,
              fmt=lambda v: _n(v, 1), cell_h: int = 22, name_w: int = 92) -> str:
    """
    A month-by-year return grid. Magnitude is carried by tint depth in a single
    hue per direction, navy for positive and clay for negative, so it reads in
    greyscale and for a colour blind reader.
    """
    height = 52 + 16 + cell_h * len(rows) + 16
    p = Panel(width, height, title, unit, pad_l=name_w, pad_r=14, pad_b=16)
    flat = [abs(v) for row in values for v in row if v is not None and not math.isnan(v)]
    m = max(flat) if flat else 1.0
    cw = (p.px1 - p.px0) / max(1, len(cols))
    top = p.py0 + 12
    for j, c in enumerate(cols):
        p.add(f'<text x="{p.px0 + cw*(j+0.5):.1f}" y="{top-4:.1f}" text-anchor="middle" '
              f'font-size="9.5" fill="{SLATE}">{_e(c)}</text>')
    for i, rname in enumerate(rows):
        y = top + i * cell_h
        p.add(f'<text x="{p.px0-8:.1f}" y="{y+cell_h/2+3.5:.1f}" text-anchor="end" '
              f'font-size="10.5" fill="{INK}">{_e(rname)}</text>')
        for j in range(len(cols)):
            v = values[i][j] if j < len(values[i]) else None
            x = p.px0 + cw * j
            if v is None or math.isnan(v):
                p.add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{cw-1.5:.1f}" '
                      f'height="{cell_h-2}" fill="{PAPER}" opacity="0.45"/>')
                p.add(f'<text x="{x+cw/2:.1f}" y="{y+cell_h/2+3.5:.1f}" '
                      f'text-anchor="middle" font-size="9.5" fill="{SLATE}">·</text>')
                continue
            op = 0.10 + 0.72 * (abs(v) / m if m else 0)
            colour = NAVY if v >= 0 else CLAY
            p.add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{cw-1.5:.1f}" height="{cell_h-2}" '
                  f'fill="{colour}" opacity="{op:.3f}"/>')
            p.add(f'<text x="{x+cw/2:.1f}" y="{y+cell_h/2+3.5:.1f}" text-anchor="middle" '
                  f'font-size="9.5" fill="{PAPER if op > 0.5 else INK}">{_e(fmt(v))}</text>')
    return p.render()


def stacked_area(series: list[dict], labels: list[str], title: str, unit: str = "",
                 width: int = 860, height: int = 240, label_every: int = 6,
                 fmt=lambda v: _n(v, 0)) -> str:
    """Composition through time. Used for the weight path across the record."""
    p = Panel(width, height, title, unit)
    n = max(len(s["values"]) for s in series) if series else 0
    if not n:
        return p.render()
    ax = YAxis(p, 0.0, 100.0, 4, fmt)
    xs = _xs(p, n)
    base = [0.0] * n
    for i, s in enumerate(series):
        colour = s.get("colour", SERIES[i % len(SERIES)])
        top = [base[k] + (s["values"][k] or 0.0) for k in range(n)]
        pts_top = " ".join(f"{x:.1f},{ax.y(v):.1f}" for x, v in zip(xs, top))
        pts_bot = " ".join(f"{x:.1f},{ax.y(v):.1f}" for x, v in zip(reversed(xs), reversed(base)))
        p.add(f'<polygon points="{pts_top} {pts_bot}" fill="{colour}" opacity="0.9"/>')
        base = top
    _xlabels(p, xs, labels, label_every)
    return p.render()


def marked_line(values: list[float], labels: list[str], marks: list[dict],
                title: str, unit: str = "", width: int = 860, height: int = 260,
                fmt=lambda v: _n(v, 0), label_every: int = 6) -> str:
    """
    A line with the committee decisions marked on it, so a reader can see which
    meeting preceded which move. marks: {"i": index, "kind": "tilt|hold|unwind"}.
    Kind is carried by mark shape, not by hue.
    """
    p = Panel(width, height, title, unit, pad_b=44)
    vals = [v for v in values if v is not None and not math.isnan(v)]
    if not vals:
        return p.render()
    ax = YAxis(p, min(vals + [0.0]), max(vals + [0.0]), 4, fmt)
    xs = _xs(p, len(values))
    pts = " ".join(f"{x:.1f},{ax.y(v):.1f}" for x, v in zip(xs, values)
                   if v is not None and not math.isnan(v))
    p.add(f'<polyline fill="none" stroke="{NAVY}" stroke-width="2.2" points="{pts}"/>')
    ymark = p.py1 + 12
    for mk in marks:
        i = mk["i"]
        if i >= len(xs):
            continue
        x = xs[i]
        p.add(f'<line x1="{x:.1f}" y1="{p.py0}" x2="{x:.1f}" y2="{p.py1:.1f}" '
              f'stroke="{SLATE}" stroke-width="0.6" stroke-dasharray="2 3" opacity="0.7"/>')
        k = mk.get("kind", "hold")
        if k == "hold":
            p.add(f'<circle cx="{x:.1f}" cy="{ymark:.1f}" r="3" fill="none" '
                  f'stroke="{SLATE}" stroke-width="1.3"/>')
        elif k == "unwind":
            p.add(f'<rect x="{x-3:.1f}" y="{ymark-3:.1f}" width="6" height="6" fill="{CLAY}"/>')
        else:
            p.add(f'<polygon points="{x:.1f},{ymark-4:.1f} {x+3.6:.1f},{ymark+2.6:.1f} '
                  f'{x-3.6:.1f},{ymark+2.6:.1f}" fill="{NAVY}"/>')
    _xlabels(p, xs, labels, label_every, y=p.py1 + 32)
    return p.render()


def hbar_frequency(items: list[tuple[str, float]], title: str, unit: str = "",
                   width: int = 420, height: int | None = None,
                   fmt=lambda v: _n(v, 0), name_w: int = 156) -> str:
    """Plain horizontal bars from a zero baseline at the left. One hue, navy."""
    row_h = 22
    height = height or (52 + 14 + row_h * len(items))
    p = Panel(width, height, title, unit, pad_l=name_w, pad_r=46, pad_b=12)
    if not items:
        return p.render()
    m = max(v for _, v in items) or 1.0
    top = p.py0 + 2
    for i, (name, v) in enumerate(items):
        y = top + i * row_h
        cy = y + row_h / 2
        w = v / m * (p.px1 - p.px0)
        p.add(f'<rect x="{p.px0:.1f}" y="{cy-6:.1f}" width="{max(w,0.8):.1f}" '
              f'height="12" fill="{NAVY}"/>')
        p.add(f'<text x="{p.px0-9:.1f}" y="{cy+3.5:.1f}" text-anchor="end" '
              f'font-size="10.5" fill="{INK}">{_e(name)}</text>')
        p.add(f'<text x="{p.px0+w+7:.1f}" y="{cy+3.5:.1f}" text-anchor="start" '
              f'font-size="10.5" font-weight="600" fill="{NAVY}">{_e(fmt(v))}</text>')
    return p.render()


def scatter(points: list[tuple[float, float, str]], title: str, unit: str = "",
            xlab: str = "", ylab: str = "", width: int = 420, height: int = 300,
            xfmt=lambda v: _n(v, 1), yfmt=lambda v: _n(v, 1)) -> str:
    p = Panel(width, height, title, unit, pad_b=42)
    if not points:
        return p.render()
    xsv = [q[0] for q in points]
    ysv = [q[1] for q in points]
    ax = YAxis(p, min(ysv + [0.0]), max(ysv + [0.0]), 4, yfmt)
    xlo, xhi, xstep = _nice(min(xsv + [0.0]), max(xsv + [0.0]), 4)

    def X(v):
        return p.px0 + (v - xlo) / ((xhi - xlo) or 1) * (p.px1 - p.px0)

    v = xlo
    while v <= xhi + 1e-9:
        p.add(f'<text x="{X(v):.1f}" y="{p.py1+15:.1f}" text-anchor="middle" '
              f'font-size="9.5" fill="{SLATE}">{_e(xfmt(v))}</text>')
        v += xstep
    if xlo < 0 < xhi:
        p.add(f'<line x1="{X(0):.1f}" y1="{p.py0}" x2="{X(0):.1f}" y2="{p.py1:.1f}" '
              f'stroke="{NAVY}" stroke-width="1"/>')
    for x, y, lab in points:
        p.add(f'<circle cx="{X(x):.1f}" cy="{ax.y(y):.1f}" r="4" fill="{NAVY}" opacity="0.85"/>')
        if lab:
            p.add(f'<text x="{X(x)+7:.1f}" y="{ax.y(y)+3.5:.1f}" font-size="9.5" '
                  f'fill="{INK}">{_e(lab)}</text>')
    if xlab:
        p.add(f'<text x="{(p.px0+p.px1)/2:.1f}" y="{p.py1+32:.1f}" text-anchor="middle" '
              f'font-size="9.5" fill="{SLATE}">{_e(xlab)}</text>')
    return p.render()
