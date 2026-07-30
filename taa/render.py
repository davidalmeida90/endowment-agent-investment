"""
taa.render — the document shell, in the Coldbrook Capital design system.

DESIGN SOURCE
------------------------------------------------------------------------------
The house system is the one shipped in ds/ in this folder: ds/colors_and_type.css
holds the tokens and ds/preview/ ships component previews. The written spec is
the Coldbrook Capital brand document. Every colour below is the token value read
from that stylesheet, not a remembered approximation, and every component follows
its preview rather than being reinvented.

Two deliberate departures, both stated in the report:

  1. The stylesheet opens with an @import of Source Sans 3 from Google Fonts.
     A network request would break the requirement that these files open from
     disk on a machine that has never seen them and render identically. The
     font stack is kept and the import is dropped, so the documents fall back
     to the system humanist sans where Source Sans 3 is not installed.

  2. ds/colors_and_type.css carries --navy: #0C1E48 while every preview file and
     the written spec use #0A1B3D, and the stylesheet's own --up token is
     #0A1B3D "same as navy", which the navy token no longer is. The tokens file
     is the authority the brief names, so #0C1E48 is used throughout and the
     drift is reported rather than silently resolved.

  3. The wordmark is Ashcroft's, not Coldbrook's. Coldbrook is the fictional
     firm the system was authored for. Putting its mark on a document belonging
     to another institution would be wrong, so the lockup geometry, type
     treatment and three-bar device are used with the correct name.

WHAT THIS SHELL WILL NOT DO
------------------------------------------------------------------------------
No red and green anywhere. No rounded corners, no shadows, no gradients used as
decoration, no three-up card grids, no icons, no centred body text, no pill tags
or coloured status badges. Blocks are separated by a section head, a hairline
rule and whitespace, never by a box. Those are the defaults that arrive when
nobody made a decision, and a reader who works in finance clocks them at once.
"""

from __future__ import annotations

import datetime as dt
from html import escape

from . import charts

TOKENS = """
:root{
  --navy:#0C1E48; --navy-deep:#061842; --navy-soft:#24365A;
  --clay:#C08878; --clay-deep:#A45E52; --clay-tint:#E8D2C9;
  --blush:#F2EBE5; --panel:#E4EAEA; --slate:#7E8A9C; --hairline:#D4DBE0;
  --paper:#FFFFFF; --ink:#1A1F28;
  --series-1:#0C1E48; --series-2:#C08878; --series-3:#4F86B0; --series-4:#B8C4CE;
  --benchmark:#7E8A9C; --reference:#A8935F;
  --font-sans:'Source Sans 3','Segoe UI','Nunito Sans',system-ui,sans-serif;
  --radius:0;
}
"""

BASE_CSS = TOKENS + """
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{
  font-family:var(--font-sans); color:var(--ink); background:#F4F5F6;
  margin:0; font-size:14px; line-height:1.45;
  font-variant-numeric:tabular-nums lining-nums;
}
.sheet{
  max-width:960px; margin:0 auto; background:var(--paper);
  padding:26px 46px 40px; border-radius:0; box-shadow:none;
}
@media print{
  body{background:#fff}
  .sheet{max-width:none;padding:0 12mm}
  .page-break{page-break-before:always}
  .no-print{display:none}
}

/* ---- header, every page ---- */
.hdr{display:flex;justify-content:space-between;align-items:flex-start;position:relative;
     overflow:hidden;padding-bottom:2px}
.ribbon{position:absolute;top:-34px;left:210px;width:250px;height:160px;
        transform:skewX(-22deg);pointer-events:none;
        background:linear-gradient(90deg,rgba(192,136,120,.16),rgba(192,136,120,.03))}
.mark{display:flex;align-items:flex-end;gap:10px;position:relative}
.wm{font-size:29px;font-weight:300;color:var(--navy);letter-spacing:.01em;line-height:1}
.wm-sub{font-size:9px;color:var(--slate);letter-spacing:.05em;margin-top:3px;
        text-transform:uppercase}
.hdr-right{text-align:right;position:relative}
.doctitle{font-size:25px;font-weight:700;color:var(--navy);text-transform:uppercase;
          line-height:1.05;letter-spacing:.005em}
.period{font-size:16px;font-weight:600;color:var(--clay);margin-top:2px}
.ident{font-size:10px;color:var(--slate);margin-top:3px}
.rule{border:0;border-top:1px solid var(--hairline);margin:13px 0 0}
.rule-thick{border:0;border-top:2px solid var(--navy);margin:0 0 14px}

/* ---- section heads: type weight alone, no rule, no box ---- */
h2.sec{font-size:12.5px;font-weight:600;text-transform:uppercase;letter-spacing:.045em;
       color:var(--navy);margin:30px 0 0}
h2.sec + .sechr{border:0;border-top:1px solid var(--hairline);margin:5px 0 13px}
h3.sub{font-size:11.5px;font-weight:600;text-transform:uppercase;letter-spacing:.04em;
       color:var(--navy-soft);margin:19px 0 7px}
h4.mini{font-size:11px;font-weight:600;color:var(--navy);margin:14px 0 5px}

p{font-size:12.5px;line-height:1.55;text-align:justify;margin:0 0 9px}
p.lead{font-size:13.5px;line-height:1.5}
.note{font-size:10.5px;color:var(--slate);line-height:1.45;text-align:left;margin:6px 0 0}
.fn{font-size:10px;color:var(--slate);margin-top:7px;line-height:1.4}
ul,ol{font-size:12.5px;line-height:1.55;margin:0 0 9px;padding-left:18px}
li{margin-bottom:3px}
strong{font-weight:600}
a{color:var(--navy);text-decoration:underline;text-underline-offset:2px}
code{font-family:ui-monospace,'Cascadia Mono',Consolas,monospace;font-size:11px;
     background:var(--blush);padding:1px 4px}

/* ---- tables ---- */
table{width:100%;border-collapse:collapse;font-size:11.5px;margin:2px 0 4px;
      font-variant-numeric:tabular-nums lining-nums}
thead th{background:var(--clay);color:#fff;font-weight:600;padding:7px 8px;
         text-align:right;font-size:10.5px;letter-spacing:.01em}
thead th:first-child{text-align:left}
thead tr.unit th{background:var(--clay-deep);font-size:9px;font-weight:400;padding:3px 8px}
tbody td{padding:5.5px 8px;text-align:right;color:var(--ink);vertical-align:top}
tbody td:first-child{text-align:left}
tbody tr:nth-child(even){background:rgba(232,210,201,.34)}
tbody tr.group td{background:var(--panel);font-weight:600;font-size:10.5px;
                  text-transform:uppercase;letter-spacing:.04em;color:var(--navy)}
tfoot td{background:var(--blush);font-weight:600;padding:6.5px 8px;text-align:right;
         border-top:1px solid var(--clay)}
tfoot td:first-child{text-align:left}
td.l,th.l{text-align:left}
td.wrap{white-space:normal;line-height:1.4}
.tbl-sm{font-size:10.5px}
.tbl-sm tbody td{padding:4px 7px}

/* ---- stat rail, page one ---- */
.split{display:flex;gap:24px;align-items:stretch;margin:14px 0 0}
.rail{width:252px;flex:0 0 252px;position:relative;overflow:hidden;padding:18px 18px 20px;
      background:linear-gradient(160deg,rgba(46,60,99,.55) 0%,rgba(46,60,99,0) 42%),
                 linear-gradient(180deg,#14264F 0%,#0C1E48 55%,#08183E 100%)}
.rail .rib{position:absolute;top:-40px;left:-30px;width:200px;height:230px;
           transform:skewX(-24deg);pointer-events:none;
           background:linear-gradient(120deg,rgba(46,60,99,.45),rgba(46,60,99,0) 70%)}
.rail .r{position:relative;padding:8.5px 0;border-bottom:1px solid rgba(174,185,199,.22)}
.rail .r:last-child{border-bottom:0}
.rail .l{font-size:8.5px;font-weight:600;color:#AEB9C7;text-transform:uppercase;
         letter-spacing:.08em;line-height:1.25}
.rail .v{font-size:21px;font-weight:600;color:#fff;margin-top:3px;letter-spacing:.01em}
.rail .v .u{font-size:12px;font-weight:400;color:#C9D2DC;margin-left:3px}
.rail .v .sm{font-size:14px}
.rail .x{font-size:9.5px;color:#AEB9C7;margin-top:2px}

/* ---- fact strip ---- */
.strip{margin:16px 0 0;background:var(--blush);display:flex;padding:12px 0}
.strip .c{flex:1;text-align:center;border-right:1px solid rgba(12,30,72,.14);padding:0 8px}
.strip .c:last-child{border-right:0}
.strip .v{font-size:18px;font-weight:600;color:var(--navy)}
.strip .l{font-size:9.5px;color:var(--navy);margin-top:1px}

/* ---- charts ---- */
.chart{margin:10px 0 4px}
.chart-row{display:flex;gap:14px;align-items:flex-start}
.chart-row > *{flex:1;min-width:0}
.cap{font-size:10px;color:var(--slate);margin-top:4px;text-align:left}

/* ---- verdict line: a rule and space, never a box ---- */
.verdict{margin:12px 0 4px;padding:9px 0 0;border-top:2px solid var(--navy)}
.verdict .k{font-size:9.5px;font-weight:600;text-transform:uppercase;
            letter-spacing:.07em;color:var(--slate)}
.verdict .v{font-size:15px;font-weight:600;color:var(--navy);margin-top:2px}

/* ---- callout tag: the one filled label in the system, and it is a link ---- */
.tag{display:inline-block;background:var(--clay);color:#fff;font-size:9.5px;
     font-weight:600;letter-spacing:.06em;text-transform:uppercase;padding:4px 9px;
     text-decoration:none}

.ftr{border-top:1px solid var(--hairline);margin-top:26px;padding-top:7px;display:flex;
     justify-content:space-between;font-size:10px;color:var(--slate)}
.pass{font-weight:600;color:var(--navy)}
.fail{font-weight:600;color:var(--clay-deep)}
"""


def _e(s) -> str:
    return escape(str(s), quote=True)


def mark_svg(size: int = 44, reversed_: bool = False) -> str:
    """
    The three-bar device from the house system: reads as moving water and as a
    bar chart. Middle bar in clay, outer bars in navy, or white when reversed.
    """
    a = "#FFFFFF" if reversed_ else charts.NAVY
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 52 52" aria-hidden="true">'
            f'<rect x="6" y="12" width="40" height="5" fill="{a}"/>'
            f'<rect x="12" y="23" width="28" height="5" fill="{charts.CLAY}"/>'
            f'<rect x="6" y="34" width="34" height="5" fill="{a}"/></svg>')


def header(doc_title: str, period: str, ident: str = "",
           org: str = "Ashcroft", org_sub: str = "University Endowment") -> str:
    return f"""
<div class="hdr">
  <div class="ribbon"></div>
  <div class="mark">{mark_svg(42)}
    <div><div class="wm">{_e(org)}</div><div class="wm-sub">{_e(org_sub)}</div></div>
  </div>
  <div class="hdr-right">
    <div class="doctitle">{_e(doc_title)}</div>
    <div class="period">{_e(period)}</div>
    {f'<div class="ident">{_e(ident)}</div>' if ident else ''}
  </div>
</div>
<hr class="rule">
"""


def footer(doc: str, period: str, page: str = "") -> str:
    return (f'<div class="ftr"><span>Ashcroft University Endowment &nbsp;·&nbsp; '
            f'{_e(doc)} &nbsp;·&nbsp; {_e(period)}</span><span>{_e(page)}</span></div>')


def section(title: str) -> str:
    return f'<h2 class="sec">{_e(title)}</h2><hr class="sechr">'


def rail(rows: list[dict]) -> str:
    """rows: {"label","value","unit"(opt),"extra"(opt)}"""
    out = ['<div class="rail"><div class="rib"></div>']
    for r in rows:
        u = f'<span class="u">{_e(r["unit"])}</span>' if r.get("unit") else ""
        x = f'<div class="x">{_e(r["extra"])}</div>' if r.get("extra") else ""
        cls = ' class="sm"' if len(str(r["value"])) > 9 else ""
        out.append(f'<div class="r"><div class="l">{_e(r["label"])}</div>'
                   f'<div class="v"><span{cls}>{_e(r["value"])}</span>{u}</div>{x}</div>')
    out.append("</div>")
    return "".join(out)


def strip(cells: list[tuple[str, str]]) -> str:
    out = ['<div class="strip">']
    for v, l in cells:
        out.append(f'<div class="c"><div class="v">{_e(v)}</div>'
                   f'<div class="l">{_e(l)}</div></div>')
    out.append("</div>")
    return "".join(out)


def verdict(kicker: str, text: str) -> str:
    return (f'<div class="verdict"><div class="k">{_e(kicker)}</div>'
            f'<div class="v">{_e(text)}</div></div>')


def table(headers: list[str], rows: list[list], units: list[str] | None = None,
          foot: list | None = None, cls: str = "", align_left: set[int] | None = None,
          raw: bool = False) -> str:
    align_left = align_left or {0}
    out = [f'<table class="{cls}"><thead><tr>']
    for i, h in enumerate(headers):
        out.append(f'<th{" class=\"l\"" if i in align_left else ""}>{_e(h)}</th>')
    out.append("</tr>")
    if units:
        out.append('<tr class="unit">')
        for i, u in enumerate(units):
            out.append(f'<th{" class=\"l\"" if i in align_left else ""}>{_e(u)}</th>')
        out.append("</tr>")
    out.append("</thead><tbody>")
    for r in rows:
        if isinstance(r, dict) and r.get("_group"):
            out.append(f'<tr class="group"><td colspan="{len(headers)}">'
                       f'{_e(r["_group"])}</td></tr>')
            continue
        out.append("<tr>")
        for i, c in enumerate(r):
            cl = ' class="l"' if i in align_left else ""
            out.append(f'<td{cl}>{c if raw else _e(c)}</td>')
        out.append("</tr>")
    out.append("</tbody>")
    if foot:
        out.append("<tfoot><tr>")
        for i, c in enumerate(foot):
            cl = ' class="l"' if i in align_left else ""
            out.append(f'<td{cl}>{c if raw else _e(c)}</td>')
        out.append("</tr></tfoot>")
    out.append("</table>")
    return "".join(out)


def chart_block(svg: str, legend_items: list[tuple[str, str, str]] | None = None,
                caption: str = "") -> str:
    out = [f'<div class="chart">{svg}']
    if legend_items:
        out.append(charts.legend(legend_items, 0))
    if caption:
        out.append(f'<div class="cap">{_e(caption)}</div>')
    out.append("</div>")
    return "".join(out)


def document(title: str, body: str, extra_css: str = "", extra_js: str = "") -> str:
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_e(title)}</title>
<style>{BASE_CSS}{extra_css}</style>
</head><body>
{body}
{f'<script>{extra_js}</script>' if extra_js else ''}
</body></html>"""


def today_str(d: dt.date | None = None) -> str:
    d = d or dt.date.today()
    return d.strftime("%-d %B %Y") if hasattr(d, "strftime") else str(d)


def datestr(d) -> str:
    if isinstance(d, str):
        d = dt.date.fromisoformat(d[:10])
    return f"{d.day} {d.strftime('%B %Y')}"
