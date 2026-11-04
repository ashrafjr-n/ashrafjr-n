"""portrait.svg: two braille artworks rendered as dots, animated between each other (SMIL only)."""
import sys
W, H, T = 340, 480, 14.0
BITS = [(0, 0, 0x01), (0, 1, 0x02), (0, 2, 0x04), (1, 0, 0x08), (1, 1, 0x10), (1, 2, 0x20), (0, 3, 0x40), (1, 3, 0x80)]

def dots(path, width):
    rows = [l for l in open(path, encoding='utf-8').read().split('\n') if l]
    cols = len(rows[0]); p = width / (cols * 2)          # dot pitch
    x0, y0 = (W - width) / 2, (H - len(rows) * 4 * p) / 2
    d = []
    for r, line in enumerate(rows):
        for c, ch in enumerate(line):
            v = ord(ch) - 0x2800
            for dx, dy, b in BITS:
                if 0 <= v < 256 and v & b:
                    d.append(f'M{x0 + (c * 2 + dx + .5) * p:.1f} {y0 + (r * 4 + dy + .5) * p:.1f}h0')
    return ''.join(d), p

def anim(attr, keys, typ=None, spline=True):
    v = ';'.join(str(k[1]) for k in keys); kt = ';'.join(f'{k[0] / T:.4f}' for k in keys)
    tag = 'animateTransform' if typ else 'animate'
    t = f' type="{typ}"' if typ else ''
    sp = f' calcMode="spline" keySplines="{";".join(["0.6 0 0.4 1"] * (len(keys) - 1))}"' if spline else ''
    return f'<{tag} attributeName="{attr}"{t} values="{v}" keyTimes="{kt}"{sp} dur="{T}s" repeatCount="indefinite"/>'

def layer(d, p, grad, op, sc, blink=None):
    inner = f'<path d="{d}" stroke="url(#{grad})" stroke-width="{p * 0.78:.2f}" stroke-linecap="round" fill="none"/>'
    if blink:
        inner = f'<g transform="translate(0 {blink})"><g>{anim("transform", [(0, "1 1"), (8.1, "1 1"), (8.22, "1 0.06"), (8.4, "1 1"), (T, "1 1")], "scale")}<g transform="translate(0 {-blink})">{inner}</g></g></g>'
    return (f'<g opacity="0">{anim("opacity", op)}<g transform="translate({W / 2} {H / 2})"><g>{anim("transform", sc, "scale")}'
            f'<g transform="translate({-W / 2} {-H / 2})">{inner}</g></g></g></g>')

a, pa = dots(sys.argv[1], 320)
b, pb = dots(sys.argv[2], 324)
A_op = [(0, 1), (4.6, 1), (5.5, 0), (11.6, 0), (12.6, 1), (T, 1)]
A_sc = [(0, 1), (2.3, 1.035), (4.6, 1), (5.5, 2.6), (11.6, 0.55), (12.6, 1), (T, 1)]
B_op = [(0, 0), (5.0, 0), (6.0, 1), (10.8, 1), (11.7, 0), (T, 0)]
B_sc = [(0, 1.7), (5.0, 1.7), (6.0, 1), (8.0, 1.04), (10.8, 1), (11.7, 0.45), (T, 0.45)]
glow = [(0, .35), (2.3, .6), (4.6, .35), (6.0, .8), (7.2, .5), (9.0, .9), (10.8, .5), (12.6, .35), (T, .35)]
svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<defs>
<clipPath id="card"><rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="8"/></clipPath>
<radialGradient id="ga" gradientUnits="userSpaceOnUse" cx="160" cy="236" r="190">
<stop offset="0" stop-color="#FFD84D"/><stop offset=".16" stop-color="#FF8A00"/><stop offset=".34" stop-color="#E5243B"/><stop offset=".55" stop-color="#FFFFFF"/><stop offset="1" stop-color="#8C8C8C"/></radialGradient>
<radialGradient id="gb" gradientUnits="userSpaceOnUse" cx="148" cy="236" r="180">
<stop offset="0" stop-color="#E5243B"/><stop offset=".22" stop-color="#FF8A00"/><stop offset=".38" stop-color="#FFD84D"/><stop offset=".55" stop-color="#FFFFFF"/><stop offset="1" stop-color="#9E9E9E"/></radialGradient>
<radialGradient id="glow"><stop offset="0" stop-color="#E5243B" stop-opacity=".35"/><stop offset=".5" stop-color="#FF8A00" stop-opacity=".08"/><stop offset="1" stop-color="#000" stop-opacity="0"/></radialGradient>
<linearGradient id="scan" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#fff" stop-opacity=".09"/></linearGradient>
</defs>
<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="8" fill="#0A0A0A"/>
<g clip-path="url(#card)">
<ellipse cx="170" cy="240" rx="190" ry="190" fill="url(#glow)">{anim("opacity", glow)}</ellipse>
{layer(a, pa, "ga", A_op, A_sc)}
{layer(b, pb, "gb", B_op, B_sc, blink=240)}
<rect x="0" y="-80" width="{W}" height="80" fill="url(#scan)">{anim("y", [(0, -80), (5.0, -80), (6.6, H), (T, H)], spline=False)}</rect>
</g>
<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="8" fill="none" stroke="#333333"/>
</svg>'''
open(sys.argv[3], 'w', encoding='utf-8').write(svg)
