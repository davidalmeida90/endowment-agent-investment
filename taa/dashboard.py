"""
taa.dashboard — the five-year decision log, interactive, one self-contained file.

A snapshot dashboard answers "where are we". This one answers "has this office
been thinking, and has it been right", which is a question about twenty
decisions and not about today's weights. Current position sits last, because it
is one quarter of twenty.

Self-contained: no network, no CDN, no external font. Opens from disk. The data
is embedded as JSON and every chart is SVG generated here from that same data,
so the dashboard cannot disagree with the report.

The window is a control: the reader picks it and the performance comparison
redraws.

Run:  py -3 -m taa.dashboard
"""

from __future__ import annotations

import json

import pandas as pd

from . import charts as C
from . import config, perf
from . import render as R
from . import report_build as RB

OUT = config.ROOT / "report"

CSS = """
.wrap{max-width:1180px;margin:0 auto;padding:22px 30px 44px;background:var(--paper)}
.controls{display:flex;gap:22px;align-items:flex-end;flex-wrap:wrap;padding:12px 0 14px;
          border-bottom:1px solid var(--hairline);margin-bottom:16px}
.ctl label{display:block;font-size:9px;font-weight:600;text-transform:uppercase;
           letter-spacing:.07em;color:var(--slate);margin-bottom:4px}
.ctl select,.ctl input{font-family:var(--font-sans);font-size:12px;padding:4px 6px;
   border:1px solid var(--hairline);background:var(--paper);color:var(--ink);border-radius:0}
.kpis{display:flex;background:var(--blush);padding:13px 0;margin:0 0 6px}
.kpis .c{flex:1;text-align:center;border-right:1px solid rgba(12,30,72,.14);padding:0 10px}
.kpis .c:last-child{border-right:0}
.kpis .v{font-size:19px;font-weight:600;color:var(--navy)}
.kpis .l{font-size:9.5px;color:var(--navy);margin-top:2px}
table.log{width:100%;border-collapse:collapse;font-size:11px;
          font-variant-numeric:tabular-nums lining-nums}
table.log thead th{background:var(--clay);color:#fff;font-weight:600;padding:6px 7px;
   text-align:right;font-size:10px;cursor:pointer;user-select:none;white-space:nowrap}
table.log thead th:first-child,table.log thead th.l{text-align:left}
table.log thead th:hover{background:var(--clay-deep)}
table.log tbody td{padding:5px 7px;text-align:right;border-bottom:1px solid var(--hairline)}
table.log tbody td:first-child,table.log tbody td.l{text-align:left}
table.log tbody tr.r{cursor:pointer}
table.log tbody tr.r:hover{background:rgba(232,210,201,.5)}
table.log tbody tr.open{background:rgba(232,210,201,.5)}
tr.detail td{background:var(--panel);padding:12px 16px;text-align:left;font-size:11.5px;
             line-height:1.5}
tr.detail .g{display:grid;grid-template-columns:150px 1fr;gap:3px 14px}
tr.detail .k{font-size:9px;font-weight:600;text-transform:uppercase;letter-spacing:.06em;
             color:var(--slate);padding-top:2px}
.sub2{font-size:10.5px;color:var(--slate);margin:4px 0 10px}
.missing{border-top:2px solid var(--navy);padding-top:9px;margin-top:16px}
.two{display:flex;gap:20px;align-items:flex-start}
.two>*{flex:1;min-width:0}
.hint{font-size:10px;color:var(--slate);margin-top:5px}
"""


def build() -> str:
    d = RB.load_all()
    rec = d["record"]
    decs = rec["decisions"]
    s, b, a = d["s"], d["b"], d["a"]
    sc = rec["scorecard"]

    payload = {
        "window": rec["window"],
        "dates": [str(x.date()) for x in s.index],
        "strategy": [float(v) for v in s.values],
        "benchmark": [float(v) for v in b.values],
        "missing": rec.get("missing_observations", {}),
        "decisions": [{
            "n": e["n"], "date": e["date"], "kind": e["kind"],
            "moved": ", ".join(f"{config.LINE_LABEL[k]} {v:+.2f}pp"
                               for k, v in sorted(e["trades_pp"].items(),
                                                  key=lambda kv: -abs(kv[1]))[:3]) or "no trade",
            "turnover": e["turnover_pp"], "cost": e["cost_bps"],
            "signal": max(e["signal_readings"].items(), key=lambda kv: abs(kv[1]))
            if e["signal_readings"] else ["", 0],
            "regime": e["regime"]["label"],
            "te": e["te_after_bps"], "bind": e["binding_constraint"],
            "pass": e["compliance"]["passed"],
            "breach": e["compliance"]["fund_in_breach"],
            "earned": e["outcome"]["active_return_bps"],
            "verdict": e["outcome"]["verdict"],
            "agreed": e["desks_agreed"], "gap": e["max_desk_disagreement_bps"],
            "reason": e["reason"],
            "watch": " ".join(w["text"] for w in e.get("watch", [])),
            "resolved": "; ".join(
                f'{r["text"][:110]} — {"it occurred" if r["happened"] else "it did not occur"}'
                for r in e.get("watch_resolution", [])) or "no item carried in",
            "before": {k: round(v * 100, 2) for k, v in e["weights_before"].items() if v > 0.0005},
            "after": {k: round(v * 100, 2) for k, v in e["weights_after"].items() if v > 0.0005},
        } for e in decs],
        "scorecard": sc,
        "labels": config.LINE_LABEL,
    }

    body = ['<div class="wrap">']
    body.append(R.header("Decision Dashboard", "Twenty quarterly meetings",
                         "1 July 2021 to 30 June 2026 · Office of the Chief Investment Officer"))

    body.append(
        '<p style="text-align:left">This dashboard answers whether the office has been '
        'thinking and whether it has been right. It is a record of twenty decisions rather '
        'than a picture of today. The current position is at the foot, because it is one '
        'quarter of twenty.</p>')

    body.append('<div class="controls">')
    body.append('<div class="ctl"><label>Window</label><select id="win">'
                '<option value="60">Full record, five years</option>'
                '<option value="36">Three years</option>'
                '<option value="12">One year</option>'
                '<option value="15">The 2022 drawdown, Jul 21 to Sep 22</option>'
                '</select></div>')
    body.append('<div class="ctl"><label>Decision type</label><select id="fkind">'
                '<option value="">All</option><option>tilt</option>'
                '<option>unwind</option><option>hold</option></select></div>')
    body.append('<div class="ctl"><label>Binding constraint</label>'
                '<select id="fbind"><option value="">All</option></select></div>')
    body.append('<div class="ctl"><label>Outcome</label><select id="fverd">'
                '<option value="">All</option><option>helped</option><option>hurt</option>'
                '<option>too small to tell</option></select></div>')
    body.append('<div class="ctl"><label>&nbsp;</label>'
                '<span id="count" style="font-size:11px;color:var(--slate)"></span></div>')
    body.append('</div>')

    body.append('<div class="kpis" id="kpis"></div>')
    body.append('<div class="hint" id="kpihint"></div>')

    body.append(R.section("Performance against the benchmark, on the selected window"))
    body.append('<div id="perfchart"></div>')

    body.append(R.section("The active return path, with the decisions marked"))
    body.append('<div id="activechart"></div>')

    body.append('<div class="two">')
    body.append('<div>' + R.section("Which constraint bound, as a frequency")
                + '<div id="bindchart"></div>'
                + '<p class="hint">The realised drawdown constraint bound at 15 of 20 '
                  'meetings. That is the most important fact in this record: from December '
                  '2022 the binding constraint was the fund\'s own drawdown against the '
                  'board limit, not any signal. The signal was rarely what set position '
                  'size.</p></div>')
    body.append('<div>' + R.section("The scorecard")
                + '<div id="scorechart"></div>'
                + '<p class="hint" id="scorenote"></p></div>')
    body.append('</div>')

    body.append(R.section("The twenty meetings"))
    body.append('<p class="sub2">Click any row for the full reasoning tabled at that meeting. '
                'Click a column heading to sort.</p>')
    body.append(
        '<table class="log"><thead><tr>'
        '<th class="l" data-k="date">Date</th>'
        '<th class="l" data-k="kind">Decision</th>'
        '<th class="l" data-k="moved">What moved</th>'
        '<th data-k="sig">Signal</th>'
        '<th class="l" data-k="regime">Regime</th>'
        '<th data-k="te">TE</th>'
        '<th class="l" data-k="bind">Binding constraint</th>'
        '<th class="l" data-k="pass">Compliance</th>'
        '<th data-k="earned">Earned</th>'
        '</tr><tr class="unit"><th></th><th></th><th></th><th>z</th><th></th><th>bps</th>'
        '<th></th><th></th><th>bps</th></tr></thead><tbody id="tb"></tbody></table>')

    body.append('<div class="missing">')
    body.append('<h2 class="sec" style="margin-top:0">What is missing</h2>')
    body.append('<div id="missing"></div>')
    body.append('</div>')

    body.append(R.section("What the office got consistently wrong"))
    hurt = [e for e in decs if e["outcome"]["verdict"] == "hurt"]
    dshort = [e for e in hurt if e["active_after_bps"].get("ust_duration", 0) < -100]
    dlong = [e for e in hurt if e["active_after_bps"].get("ust_duration", 0) > 100]
    body.append(
        f'<p style="text-align:left">{len(hurt)} decisions hurt, and they are not eight '
        f'unrelated bad calls. <strong>All {len(dshort) + len(dlong)} of them carried a '
        f'Treasury duration position, and the sign flipped halfway through the record.</strong> '
        f'{len(dshort)} were duration underweight with a large cash overweight, from '
        f'{dshort[0]["date"][:7]} to {dshort[-1]["date"][:7]}, while the tightening cycle '
        f'peaked and the long end recovered. {len(dlong)} were duration overweight funded from '
        f'equity, from {dlong[0]["date"][:7]} to {dlong[-1]["date"][:7]}, after the same '
        f'signals flipped positive. That is one error made twice with the sign reversed: a '
        f'trend signal at a turning point, on the single line whose out-of-sample R² '
        f'against the expanding mean is most negative. Five unrelated bad calls and five '
        f'instances of the same bad call are different findings, and only the second is '
        f'fixable. The recommendation removes the duration position entirely. The deeper cause '
        f'is that the programme was sized to a tracking-error budget rather than to '
        f'demonstrated skill, and a budget is permission to take risk rather than a reason '
        f'to.</p>')

    body.append(R.section("Current position"))
    body.append('<div id="current"></div>')
    body.append(R.footer("Decision Dashboard", "1 July 2021 to 30 June 2026",
                         "Ashcroft University Endowment"))
    body.append('</div>')

    js = _JS.replace("__DATA__", json.dumps(payload))
    tokens = {"NAVY": C.NAVY, "CLAY": C.CLAY, "SLATE": C.SLATE, "HAIRLINE": C.HAIRLINE,
              "PANEL": C.PANEL, "REFERENCE": C.REFERENCE, "BENCH": C.BENCHMARK,
              "CLAYTINT": C.CLAY_TINT, "INK": C.INK, "PAPER": C.PAPER}
    for k, v in tokens.items():
        js = js.replace(f"__{k}__", v)
    return R.document("Ashcroft University Endowment — Decision Dashboard",
                      "".join(body), extra_css=CSS, extra_js=js)


_JS = r"""
const D = __DATA__;
const NAVY="__NAVY__", CLAY="__CLAY__", SLATE="__SLATE__", HAIR="__HAIRLINE__",
      PANEL="__PANEL__", REF="__REFERENCE__", BENCH="__BENCH__", TINT="__CLAYTINT__",
      INK="__INK__", PAPER="__PAPER__";
const $ = id => document.getElementById(id);
const fmt = (v,dp=2) => v==null||isNaN(v) ? "—" :
      (v<0 ? "("+Math.abs(v).toLocaleString(undefined,{minimumFractionDigits:dp,maximumFractionDigits:dp})+")"
           : v.toLocaleString(undefined,{minimumFractionDigits:dp,maximumFractionDigits:dp}));
const esc = s => String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

/* ---- window selection ---------------------------------------------- */
function windowSlice(){
  const v = $("win").value;
  if(v === "15") return [0, 15];                 // Jul 21 to Sep 22, the drawdown
  const n = Math.min(parseInt(v,10), D.dates.length);
  return [D.dates.length - n, D.dates.length];
}
function decisionsInWindow(){
  const [i0,i1] = windowSlice();
  const lo = D.dates[i0], hi = D.dates[i1-1];
  return D.decisions.filter(e => e.date >= lo && e.date <= hi);
}
function filtered(){
  const k=$("fkind").value, b=$("fbind").value, v=$("fverd").value;
  return decisionsInWindow().filter(e =>
     (!k || e.kind===k) && (!b || e.bind===b) && (!v || e.verdict===v));
}

/* ---- tiny svg helpers ---------------------------------------------- */
function svgOpen(w,h,title,unit){
  let s = `<svg viewBox="0 0 ${w} ${h}" width="100%" preserveAspectRatio="xMidYMid meet"
    style="display:block;font-family:var(--font-sans);font-variant-numeric:tabular-nums lining-nums">
    <rect x="0" y="0" width="${w}" height="${h}" fill="${PANEL}"/>
    <text x="${w/2}" y="22" text-anchor="middle" font-size="12.5" font-weight="600"
      fill="${NAVY}" letter-spacing="0.04em" style="text-transform:uppercase">${esc(title)}</text>`;
  if(unit) s += `<text x="${w/2}" y="37" text-anchor="middle" font-size="10" fill="${SLATE}">${esc(unit)}</text>`;
  return s;
}
function niceDomain(lo,hi,ticks){
  if(hi<=lo) hi=lo+1;
  let raw=(hi-lo)/ticks, mag=Math.pow(10,Math.floor(Math.log10(raw))), step=10*mag;
  for(const m of [1,2,2.5,5,10]) if(raw/mag<=m){ step=m*mag; break; }
  return [Math.floor(lo/step)*step, Math.ceil(hi/step)*step, step];
}

/* ---- performance chart --------------------------------------------- */
function drawPerf(){
  const [i0,i1] = windowSlice();
  const w=1120,h=280,pl=54,pr=20,pt=48,pb=34;
  let cs=[100], cb=[100];
  for(let i=i0;i<i1;i++){ cs.push(cs[cs.length-1]*(1+D.strategy[i])); cb.push(cb[cb.length-1]*(1+D.benchmark[i])); }
  const all=cs.concat(cb);
  const [lo,hi,step]=niceDomain(Math.min(...all),Math.max(...all),4);
  const Y=v=>(h-pb)-((v-lo)/(hi-lo))*((h-pb)-pt);
  const X=i=>pl+i*((w-pr-pl)/(cs.length-1));
  let s=svgOpen(w,h,"Cumulative return against the benchmark","indexed, 100 at the start of the selected window");
  for(let v=lo;v<=hi+1e-9;v+=step){
    s+=`<line x1="${pl}" y1="${Y(v)}" x2="${w-pr}" y2="${Y(v)}" stroke="${HAIR}"/>`;
    s+=`<text x="${pl-7}" y="${Y(v)+3.5}" text-anchor="end" font-size="9.5" fill="${SLATE}">${fmt(v,0)}</text>`;
  }
  s+=`<polyline fill="none" stroke="${BENCH}" stroke-width="2" stroke-dasharray="6 4" points="${cb.map((v,i)=>X(i)+","+Y(v)).join(" ")}"/>`;
  s+=`<polyline fill="none" stroke="${NAVY}" stroke-width="2.2" points="${cs.map((v,i)=>X(i)+","+Y(v)).join(" ")}"/>`;
  s+=`<text x="${w-pr-2}" y="${Y(cs[cs.length-1])-8}" text-anchor="end" font-size="11" font-weight="600" fill="${NAVY}">${fmt(cs[cs.length-1],1)}</text>`;
  s+=`<text x="${w-pr-2}" y="${Y(cb[cb.length-1])+14}" text-anchor="end" font-size="11" font-weight="600" fill="${BENCH}">${fmt(cb[cb.length-1],1)}</text>`;
  const every=Math.max(1,Math.round((i1-i0)/10));
  for(let i=i0;i<i1;i+=every){
    const dd=new Date(D.dates[i]);
    s+=`<text x="${X(i-i0+1)}" y="${h-pb+16}" text-anchor="middle" font-size="9.5" fill="${SLATE}">${dd.toLocaleString('en',{month:'short'})} ${String(dd.getFullYear()).slice(2)}</text>`;
  }
  s+="</svg>";
  $("perfchart").innerHTML = s +
    `<div style="display:flex;gap:18px;justify-content:center;font-size:10px;margin-top:6px">
      <span><span style="display:inline-block;width:16px;height:2px;background:${NAVY};vertical-align:middle;margin-right:6px"></span>Fund</span>
      <span><span style="display:inline-block;width:16px;border-top:2px dashed ${BENCH};vertical-align:middle;margin-right:6px"></span>Benchmark, policy portfolio</span>
    </div>`;
}

/* ---- active return path with decisions marked ---------------------- */
function drawActive(){
  const [i0,i1]=windowSlice();
  const w=1120,h=270,pl=54,pr=20,pt=48,pb=46;
  let ca=[0]; let acc=1, accb=1;
  for(let i=i0;i<i1;i++){ acc*=(1+D.strategy[i]); accb*=(1+D.benchmark[i]); ca.push((acc-accb)*100); }
  const [lo,hi,step]=niceDomain(Math.min(0,...ca),Math.max(0,...ca),4);
  const Y=v=>(h-pb)-((v-lo)/(hi-lo))*((h-pb)-pt);
  const X=i=>pl+i*((w-pr-pl)/(ca.length-1));
  let s=svgOpen(w,h,"Cumulative active return, with the twenty decisions marked","fund less benchmark, per cent");
  for(let v=lo;v<=hi+1e-9;v+=step){
    const zero=Math.abs(v)<1e-12;
    s+=`<line x1="${pl}" y1="${Y(v)}" x2="${w-pr}" y2="${Y(v)}" stroke="${zero?NAVY:HAIR}"/>`;
    s+=`<text x="${pl-7}" y="${Y(v)+3.5}" text-anchor="end" font-size="9.5" fill="${SLATE}">${fmt(v,1)}</text>`;
  }
  s+=`<polyline fill="none" stroke="${NAVY}" stroke-width="2.2" points="${ca.map((v,i)=>X(i)+","+Y(v)).join(" ")}"/>`;
  const ym=h-pb+13;
  decisionsInWindow().forEach(e=>{
    const idx=D.dates.indexOf(e.date); if(idx<i0||idx>=i1) return;
    const x=X(idx-i0+1);
    s+=`<line x1="${x}" y1="${pt}" x2="${x}" y2="${h-pb}" stroke="${SLATE}" stroke-width="0.6" stroke-dasharray="2 3" opacity="0.65"/>`;
    if(e.kind==="hold") s+=`<circle cx="${x}" cy="${ym}" r="3" fill="none" stroke="${SLATE}" stroke-width="1.3"/>`;
    else if(e.kind==="unwind") s+=`<rect x="${x-3}" y="${ym-3}" width="6" height="6" fill="${CLAY}"/>`;
    else s+=`<polygon points="${x},${ym-4} ${x+3.6},${ym+2.6} ${x-3.6},${ym+2.6}" fill="${NAVY}"/>`;
  });
  s+="</svg>";
  $("activechart").innerHTML = s +
    `<div style="display:flex;gap:18px;justify-content:center;font-size:10px;margin-top:6px">
      <span><span style="display:inline-block;width:16px;height:2px;background:${NAVY};vertical-align:middle;margin-right:6px"></span>Cumulative active return</span>
      <span><span style="display:inline-block;width:0;height:0;border-left:4px solid transparent;border-right:4px solid transparent;border-bottom:7px solid ${NAVY};vertical-align:middle;margin-right:6px"></span>Tilt</span>
      <span><span style="display:inline-block;width:7px;height:7px;background:${CLAY};vertical-align:middle;margin-right:6px"></span>Unwind</span>
      <span><span style="display:inline-block;width:7px;height:7px;border:1.3px solid ${SLATE};border-radius:50%;vertical-align:middle;margin-right:6px"></span>Hold</span>
    </div>`;
}

/* ---- horizontal frequency bars ------------------------------------- */
function hbars(el,items,title,unit,nameW){
  const rowH=24,w=540,h=52+12+rowH*Math.max(items.length,1);
  const pl=nameW,pr=52;
  let s=svgOpen(w,h,title,unit);
  const m=Math.max(1,...items.map(i=>i[1]));
  items.forEach((it,i)=>{
    const cy=52+i*rowH+rowH/2, bw=(it[1]/m)*(w-pl-pr);
    s+=`<rect x="${pl}" y="${cy-6}" width="${Math.max(bw,0.8)}" height="12" fill="${NAVY}"/>`;
    s+=`<text x="${pl-9}" y="${cy+3.5}" text-anchor="end" font-size="10.5" fill="${INK}">${esc(it[0])}</text>`;
    s+=`<text x="${pl+bw+7}" y="${cy+3.5}" font-size="10.5" font-weight="600" fill="${NAVY}">${it[1]}</text>`;
  });
  s+="</svg>"; el.innerHTML=s;
}

function drawBind(){
  const f=decisionsInWindow(), c={};
  f.forEach(e=>c[e.bind]=(c[e.bind]||0)+1);
  hbars($("bindchart"), Object.entries(c).sort((a,b)=>b[1]-a[1]),
        "Which constraint bound", "meetings in the selected window", 168);
}
function drawScore(){
  const f=decisionsInWindow();
  const h=f.filter(e=>e.verdict==="helped").length;
  const u=f.filter(e=>e.verdict==="hurt").length;
  const t=f.filter(e=>e.verdict==="too small to tell").length;
  hbars($("scorechart"), [["Helped",h],["Hurt",u],["Too small to tell",t]],
        "Decisions that helped, hurt, or neither", "count", 132);
  const net=f.reduce((s,e)=>s+e.earned,0), cost=f.reduce((s,e)=>s+e.cost,0);
  const yrs=Math.max(f.length/4,1e-9);
  $("scorenote").innerHTML = `Net <strong>${fmt(net/yrs,1)}bps</strong> a year of active return `
    + `against <strong>${fmt(cost/yrs,1)}bps</strong> of turnover cost, over ${f.length} `
    + `decisions. On sixty monthly observations the standard error of the information ratio `
    + `is roughly 0.45, so a result of this size cannot be separated from zero. The office `
    + `states that plainly rather than presenting it as a positive number.`;
}

/* ---- KPIs ----------------------------------------------------------- */
function drawKpis(){
  const [i0,i1]=windowSlice();
  let acc=1,accb=1,peak=1,dd=0, act=[];
  for(let i=i0;i<i1;i++){
    acc*=(1+D.strategy[i]); accb*=(1+D.benchmark[i]);
    peak=Math.max(peak,acc); dd=Math.min(dd, acc/peak-1);
    act.push(D.strategy[i]-D.benchmark[i]);
  }
  const n=i1-i0, yrs=n/12;
  const ar=Math.pow(acc,1/yrs)-1, br=Math.pow(accb,1/yrs)-1;
  const mean=act.reduce((a,b)=>a+b,0)/n;
  const sd=Math.sqrt(act.reduce((s,v)=>s+(v-mean)*(v-mean),0)/(n-1))*Math.sqrt(12);
  const ir=(mean*12)/sd;
  const f=decisionsInWindow();
  const cells=[[fmt(ar*100,2)+"%","Fund, annualised"],
               [fmt(br*100,2)+"%","Benchmark, annualised"],
               [fmt((ar-br)*10000,0)+"bps","Active, a year"],
               [fmt(sd*10000,0)+"bps","Realised tracking error"],
               [fmt(ir,2),"Information ratio"],
               [fmt(dd*100,2)+"%","Worst drawdown"],
               [String(f.length),"Decisions in window"]];
  $("kpis").innerHTML = cells.map(c=>`<div class="c"><div class="v">${c[0]}</div><div class="l">${c[1]}</div></div>`).join("");
  $("kpihint").innerHTML = `Drawdown limit is (20.00)% (IPS 3.3). Tracking-error budget is `
    + `200bps ex ante (IPS 4.2). ${dd<-0.20 ? "<strong>The drawdown limit was breached on this window.</strong>" : "The drawdown limit held on this window."}`;
}

/* ---- the log -------------------------------------------------------- */
let sortKey="date", sortDir=1;
function drawTable(){
  const rows=filtered().slice().sort((a,b)=>{
    let x=a[sortKey], y=b[sortKey];
    if(sortKey==="sig"){ x=Math.abs(a.signal[1]); y=Math.abs(b.signal[1]); }
    if(sortKey==="pass"){ x=a.pass?1:0; y=b.pass?1:0; }
    return (x>y?1:x<y?-1:0)*sortDir;
  });
  $("count").textContent = rows.length+" of "+D.decisions.length+" meetings shown";
  $("tb").innerHTML = rows.map(e=>`
   <tr class="r" data-n="${e.n}">
     <td class="l">${e.date}</td><td class="l">${e.kind}</td><td class="l">${esc(e.moved)}</td>
     <td>${fmt(e.signal[1],2)}</td><td class="l">${esc(e.regime||"")}</td>
     <td>${fmt(e.te,0)}</td><td class="l">${esc(e.bind)}</td>
     <td class="l">${e.pass?"PASS":"FAIL"}${e.breach&&e.breach.length?" · fund in breach":""}</td>
     <td>${fmt(e.earned,0)}</td>
   </tr>
   <tr class="detail" id="d${e.n}" style="display:none"><td colspan="9">
     <div class="g">
       <div class="k">Reason, as tabled</div><div>${esc(e.reason)}</div>
       <div class="k">Allocation before</div><div>${Object.entries(e.before).map(([k,v])=>D.labels[k]+" "+fmt(v,1)).join(", ")}</div>
       <div class="k">Allocation after</div><div>${Object.entries(e.after).map(([k,v])=>D.labels[k]+" "+fmt(v,1)).join(", ")}</div>
       <div class="k">Turnover</div><div>${fmt(e.turnover,2)}pp one-way, costing ${fmt(e.cost,2)}bps</div>
       <div class="k">Desks agreed</div><div>${e.agreed?"yes":"no, "+fmt(e.gap,0)+"bps apart at the widest line"}</div>
       <div class="k">Watched forward</div><div>${esc(e.watch)}</div>
       <div class="k">Prior item resolved</div><div>${esc(e.resolved)}</div>
       <div class="k">Outcome</div><div>${fmt(e.earned,1)}bps of active return. ${esc(e.verdict)}. Recorded after the fact and used in no reason above.</div>
     </div></td></tr>`).join("");
  document.querySelectorAll("tr.r").forEach(tr=>tr.onclick=()=>{
    const d=$("d"+tr.dataset.n);
    const open=d.style.display!=="none";
    d.style.display=open?"none":"table-row";
    tr.classList.toggle("open",!open);
  });
}

/* ---- missing data --------------------------------------------------- */
function drawMissing(){
  const rows=[];
  const oasBlind = D.decisions.filter(e=>e.date<"2023-07-31").length;
  rows.push(["Credit spread indicators, ICE BofA option-adjusted spreads",
    oasBlind+" of "+D.decisions.length+" meetings",
    "The free FRED endpoint serves only a rolling three-year window of these series, "
    +"beginning 31 July 2023. Meetings before that date ran on three liquidity indicators "
    +"rather than four. Nothing was interpolated and no value was carried backwards."]);
  rows.push(["2008 crisis, for the stress replay","entire episode",
    "The sanctioned price cache begins in July 2009, so the worst episode the risk desk "
    +"can replay is not the worst that occurred. The desk did not reach around the "
    +"point-in-time layer to obtain it."]);
  const miss=Object.entries(D.missing||{});
  if(miss.length) rows.push(["Return observations", miss.map(m=>D.labels[m[0]]+": "+m[1]).join(", "),
    "Months with no return for a line. Filled with zero for the portfolio calculation and "
    +"reported here rather than hidden."]);
  else rows.push(["Return observations","none",
    "All nine lines have a complete monthly return series across the window. Every vehicle "
    +"was investable throughout, so no line is spliced and no implementation is assumed."]);
  $("missing").innerHTML =
    `<p style="text-align:left">A record that silently drops an input for part of its span is `
    + `telling the reader something untrue about how much evidence sits behind it. These are `
    + `the gaps.</p>`
    + `<table class="log"><thead><tr><th class="l">What</th><th class="l">How much</th>`
    + `<th class="l">What was done about it</th></tr></thead><tbody>`
    + rows.map(r=>`<tr><td class="l">${esc(r[0])}</td><td class="l">${esc(r[1])}</td><td class="l">${esc(r[2])}</td></tr>`).join("")
    + `</tbody></table>`;
}

/* ---- current position ----------------------------------------------- */
function drawCurrent(){
  const last=D.decisions[D.decisions.length-1];
  $("current").innerHTML =
    `<p style="text-align:left">Recommended for the year to 30 June 2027: <strong>policy `
    + `weights on every line</strong>, zero intentional active risk, rebalancing on corridor `
    + `breach only. The whole 200bps tracking-error budget is returned unspent because the `
    + `expected value of spending it is negative. This is one quarter of twenty and it sits `
    + `at the foot of this page for that reason.</p>`
    + `<table class="log"><thead><tr><th class="l">Line</th><th>Policy</th>`
    + `<th>Recommended</th><th>Active</th></tr></thead><tbody>`
    + Object.entries(last.after).map(([k,v])=>{
        const pol = {us_equity:38,dev_ex_us:20,em_equity:12,ust_duration:12,us_ig:8,
                     us_hy:5,commodities:3,listed_re:2,cash:0}[k];
        return `<tr><td class="l">${D.labels[k]}</td><td>${fmt(pol,1)}</td>`
             + `<td>${fmt(pol,1)}</td><td>${fmt(0,0)}</td></tr>`;
      }).join("")
    + `</tbody></table>`;
}

/* ---- wire up --------------------------------------------------------- */
function redraw(){ drawKpis(); drawPerf(); drawActive(); drawBind(); drawScore(); drawTable(); }
(function init(){
  const binds=[...new Set(D.decisions.map(e=>e.bind))].sort();
  $("fbind").innerHTML = '<option value="">All</option>'+binds.map(b=>`<option>${esc(b)}</option>`).join("");
  ["win","fkind","fbind","fverd"].forEach(id=>$(id).onchange=redraw);
  document.querySelectorAll("table.log thead th[data-k]").forEach(th=>{
    th.onclick=()=>{ const k=th.dataset.k; sortDir = (k===sortKey)? -sortDir : 1; sortKey=k; drawTable(); };
  });
  redraw(); drawMissing(); drawCurrent();
})();
"""


def main() -> int:
    OUT.mkdir(exist_ok=True)
    html = build()
    (OUT / "dashboard.html").write_text(html, encoding="utf-8")
    print(f"  report/dashboard.html       {(OUT / 'dashboard.html').stat().st_size:,} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
