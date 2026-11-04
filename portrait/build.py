"""portrait.svg: two braille artworks rendered as dots. Each scene dives into its pupil, a stream of\ndots pours out, and the next scene rises from far away (SMIL only, loops)."""
import sys
W, H, T = 340, 480, 16.0
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

IN, OUT, EASE = '0.55 0 0.95 0.5', '0.05 0.5 0.45 1', '0.6 0 0.4 1'

def anim(attr, keys, typ=None, spline=True):
    """keys: (t, value[, spline]) — the spline eases the segment that ends at this key."""
    v = ';'.join(str(k[1]) for k in keys); kt = ';'.join(f'{k[0] / T:.4f}' for k in keys)
    tag = 'animateTransform' if typ else 'animate'
    t = f' type="{typ}"' if typ else ''
    sp = f' calcMode="spline" keySplines="{";".join(k[2] if len(k) > 2 else EASE for k in keys[1:])}"' if spline else ''
    return f'<{tag} attributeName="{attr}"{t} values="{v}" keyTimes="{kt}"{sp} dur="{T}s" repeatCount="indefinite"/>'

def about(pt, sc, inner):
    """scale `inner` about point pt."""
    x, y = pt
    return (f'<g transform="translate({x} {y})"><g>{anim("transform", sc, "scale")}'
            f'<g transform="translate({-x} {-y})">{inner}</g></g></g>')

def art(d, p, grad):
    return f'<path d="{d}" stroke="url(#{grad})" stroke-width="{p * 0.78:.2f}" stroke-linecap="round" fill="none"/>'

def warp(pt, seed, t0):
    """braille-dot particles streaming out of the pupil: the 'code' tunnel between scenes."""
    import math, random
    r = random.Random(seed); x0, y0 = pt; d = []
    for _ in range(420):
        a = r.uniform(0, 6.2832); rad = 6 + 90 * r.random() ** 0.6
        for k in range(r.choice((1, 2, 3))):          # short braille-like streaks along the ray
            rr = rad + k * 2.2
            d.append(f'M{x0 + rr * math.cos(a):.1f} {y0 + rr * math.sin(a):.1f}h0')
    d = ''.join(d)
    path = f'<path d="{d}" stroke="url(#gw)" stroke-width="1.5" stroke-linecap="round" fill="none"/>'
    op = [(0, 0), (t0, 0), (t0 + 0.35, 0.95), (t0 + 1.1, 0.9), (t0 + 1.6, 0), (T, 0)]
    sc = [(0, 0.05), (t0, 0.05), (t0 + 1.6, 4.2, IN), (T, 4.2)]
    return f'<g opacity="0">{anim("opacity", op)}{about(pt, sc, path)}</g>'

a, pa = dots(sys.argv[1], 320)
b, pb = dots(sys.argv[2], 324)
PA, PB = (170, 191), (153, 233)          # pupil centres of the two artworks
T = 16.0
# A: hold -> dive into its pupil -> (B scene) -> emerge from far away -> hold
A_op = [(0, 1), (6.3, 1), (6.7, 0), (13.9, 0), (14.4, 1), (T, 1)]
A_sc = [(0, 1), (2.5, 1.03), (4.9, 1), (6.7, 16, IN), (13.9, 0.06), (15.2, 1, OUT), (T, 1)]
# B: emerge from far -> hold + blink -> dive into its pupil
B_op = [(0, 0), (6.6, 0), (7.1, 1), (13.4, 1), (13.8, 0), (T, 0)]
B_sc = [(0, 0.06), (6.6, 0.06), (8.0, 1, OUT), (10.3, 1.03), (12.0, 1), (13.8, 16, IN), (T, 16)]
blink = [(0, '1 1'), (10.2, '1 1'), (10.32, '1 0.06'), (10.5, '1 1'), (T, '1 1')]
glow = [(0, .35), (2.5, .6), (4.9, .35), (6.7, .9), (8.0, .45), (10.3, .7), (12.0, .45), (13.8, .9), (15.2, .35), (T, .35)]
B_art = (f'<g transform="translate(0 {PB[1]})"><g>{anim("transform", blink, "scale")}'
         f'<g transform="translate(0 {-PB[1]})">{art(b, pb, "gb")}</g></g></g>')
svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<defs>
<clipPath id="card"><rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="8"/></clipPath>
<radialGradient id="ga" gradientUnits="userSpaceOnUse" cx="160" cy="236" r="190">
<stop offset="0" stop-color="#FFD84D"/><stop offset=".16" stop-color="#FF8A00"/><stop offset=".34" stop-color="#E5243B"/><stop offset=".55" stop-color="#FFFFFF"/><stop offset="1" stop-color="#8C8C8C"/></radialGradient>
<radialGradient id="gb" gradientUnits="userSpaceOnUse" cx="148" cy="236" r="180">
<stop offset="0" stop-color="#E5243B"/><stop offset=".22" stop-color="#FF8A00"/><stop offset=".38" stop-color="#FFD84D"/><stop offset=".55" stop-color="#FFFFFF"/><stop offset="1" stop-color="#9E9E9E"/></radialGradient>
<radialGradient id="gw" gradientUnits="objectBoundingBox"><stop offset="0" stop-color="#FFFFFF"/><stop offset=".35" stop-color="#FFD84D"/><stop offset=".7" stop-color="#FF8A00"/><stop offset="1" stop-color="#E5243B"/></radialGradient>
<radialGradient id="glow"><stop offset="0" stop-color="#E5243B" stop-opacity=".35"/><stop offset=".5" stop-color="#FF8A00" stop-opacity=".08"/><stop offset="1" stop-color="#000" stop-opacity="0"/></radialGradient>
</defs>
<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="8" fill="#0A0A0A"/>
<g clip-path="url(#card)">
<ellipse cx="170" cy="240" rx="190" ry="190" fill="url(#glow)">{anim("opacity", glow)}</ellipse>
<g>{anim("opacity", A_op)}{about(PA, A_sc, art(a, pa, "ga"))}</g>
<g opacity="0">{anim("opacity", B_op)}{about(PB, B_sc, B_art)}</g>
{warp(PA, 1, 5.9)}
{warp(PB, 2, 13.0)}
</g>
<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="8" fill="none" stroke="#333333"/>
</svg>'''
open(sys.argv[3], 'w', encoding='utf-8').write(svg)
