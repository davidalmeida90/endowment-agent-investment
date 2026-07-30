# Coldbrook Capital design system

Design language modelled on the Kinea Creditas FII monthly report. Colours sampled from
the source PDF, not described from memory. Coldbrook is a fictional US active equity
manager, created as a design exercise.

Full written spec sits one level up in `coldbrook-brand.md`.

## What defines this system

Two colours in tension. Deep navy carries authority: headings, the stat rail, the first
data series, the logo. Muted clay carries emphasis: the period, table header bands, the
second data series, buttons, and the one big number on a page. Every other colour exists
to hold those two apart.

Nothing floats. No shadows, no elevation, no gradients, no rounded corners except small
status tags. Panels are flat fills of light grey or pale blush sitting directly on white.

Charts sit inside light grey panels with the title inside the panel rather than above it,
and data labels print directly on the marks so a chart reads without an axis.

Body copy is justified. That one choice does more than any other to make a page read as
institutional.

Section heads are all caps navy with no rule and no box. Type weight alone separates them.

## Files

`colors_and_type.css` holds every token. Preview files each carry a `@dsCard` marker on
line two, which is what puts them in the Design System pane.

| Group | File |
|---|---|
| Brand | `preview/brand-logo.html` |
| Colors | `preview/colors-core.html` |
| Type | `preview/type-scale.html` |
| Page furniture | `preview/components-page-header.html` |
| Components | `preview/components-stat-rail.html`, `components-table.html`, `components-description-table.html`, `components-fund-card.html` |
| Charts | `preview/charts-panel-set.html`, `charts-return-grid.html`, `charts-diverging.html`, `charts-bars.html`, `charts-lines.html` |

## No red and green

Direction is carried by navy against clay, by the parenthesis convention on negatives, and
by position relative to a zero axis. Never by hue. The source report does the same thing
and it is why its charts stay legible in greyscale and for colour blind readers. The only
third hue anywhere is a muted gold used for a dashed reference line.

## Still to add

Growth of $10,000, holdings card grid, activity timeline entry, glossary block, disclaimer
block, the process diagram from page 15 of the source, and the web nav and footer.
