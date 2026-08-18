#!/usr/bin/env python3
"""Build README SVGs from real GitHub contribution data. Monochrome palette."""

import os
import sys
import json
import datetime
import urllib.request

LOGIN = os.environ.get("GH_LOGIN", "ashrafjr-n")
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")

RIGHT_OUT = "right_column.svg"
ACTIVITY_OUT = "activity.svg"

# ---- palette: black / white / dark silver only -----------------------------
BG      = "#0A0A0A"
HEADBG  = "#171717"
BORDER  = "#333333"
TITLE   = "#808080"
WHITE   = "#FFFFFF"
SILVER  = "#B5B5B5"
MUTED   = "#5E5E5E"
GRID    = "#242424"
FAINT   = "#1A1A1A"
# the only permitted colour accents:
BTN     = ("#FF5F56", "#FFBD2E", "#27C93F")
LIVE    = "#27C93F"

MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,'Liberation Mono',monospace"

API = "https://api.github.com/graphql"

Q_CREATED = "query($login:String!){user(login:$login){createdAt}}"
Q_CAL = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


def gql(query, variables):
    body = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request(
        API, data=body,
        headers={"Authorization": f"bearer {TOKEN}",
                 "Content-Type": "application/json",
                 "User-Agent": "readme-stats"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        payload = json.loads(r.read().decode())
    if "errors" in payload:
        raise RuntimeError(payload["errors"])
    return payload["data"]


def fetch_days():
    created = gql(Q_CREATED, {"login": LOGIN})["user"]["createdAt"]
    start = datetime.datetime.strptime(created, "%Y-%m-%dT%H:%M:%SZ").date()
    today = datetime.date.today()
    days, total = {}, 0
    cursor = start
    while cursor <= today:
        end = min(cursor + datetime.timedelta(days=364), today)
        cal = gql(Q_CAL, {"login": LOGIN,
                          "from": f"{cursor.isoformat()}T00:00:00Z",
                          "to": f"{end.isoformat()}T23:59:59Z"}
                  )["user"]["contributionsCollection"]["contributionCalendar"]
        total += cal["totalContributions"]
        for wk in cal["weeks"]:
            for d in wk["contributionDays"]:
                days[d["date"]] = d["contributionCount"]
        cursor = end + datetime.timedelta(days=1)
    return days, total


def streaks(days):
    today = datetime.date.today()
    longest = run = 0
    prev = None
    for ds in sorted(days):
        d = datetime.date.fromisoformat(ds)
        if days[ds] > 0:
            run = run + 1 if (prev and (d - prev).days == 1) else 1
            longest = max(longest, run)
            prev = d
        else:
            run, prev = 0, None

    cur, day = 0, today
    if days.get(day.isoformat(), 0) == 0:
        day -= datetime.timedelta(days=1)
    while days.get(day.isoformat(), 0) > 0:
        cur += 1
        day -= datetime.timedelta(days=1)
    return cur, longest


def weekly_totals(days, weeks=12):
    today = datetime.date.today()
    monday = today - datetime.timedelta(days=today.weekday())
    out = []
    for i in range(weeks - 1, -1, -1):
        s = monday - datetime.timedelta(weeks=i)
        out.append(sum(days.get((s + datetime.timedelta(days=j)).isoformat(), 0)
                       for j in range(7) if s + datetime.timedelta(days=j) <= today))
    return out


def monthly_totals(days, months=12):
    today = datetime.date.today()
    slots = []
    for i in range(months - 1, -1, -1):
        mm, yy = today.month - i, today.year
        while mm <= 0:
            mm += 12
            yy -= 1
        slots.append((yy, mm))
    tot = {s: 0 for s in slots}
    for ds, c in days.items():
        d = datetime.date.fromisoformat(ds)
        if (d.year, d.month) in tot:
            tot[(d.year, d.month)] += c
    return ([datetime.date(y, m, 1).strftime("%b") for y, m in slots],
            [tot[s] for s in slots])


def chrome(w, h, y0, title):
    """Rounded terminal box with header bar and three buttons."""
    return (
        f'<rect x="0.5" y="{y0+0.5}" width="{w-1}" height="{h-1}" rx="8" fill="{BG}" stroke="{BORDER}"/>'
        f'<path d="M0,{y0+8} A8,8 0 0 1 8,{y0} L{w-8},{y0} A8,8 0 0 1 {w},{y0+8} '
        f'L{w},{y0+32} L0,{y0+32} Z" fill="{HEADBG}"/>'
        f'<path d="M0,{y0+31.5} L{w},{y0+31.5}" stroke="{BORDER}"/>'
        f'<circle cx="18" cy="{y0+16}" r="5.5" fill="{BTN[0]}"/>'
        f'<circle cx="36" cy="{y0+16}" r="5.5" fill="{BTN[1]}"/>'
        f'<circle cx="54" cy="{y0+16}" r="5.5" fill="{BTN[2]}"/>'
        f'<text x="{w//2+10}" y="{y0+21}" text-anchor="middle" fill="{TITLE}" '
        f'font-size="12">{title}</text>'
    )


def build_right_column(current, total, longest):
    W, H = 440, 480
    WH_H = 208                 # whoami terminal height
    ST_Y, ST_H = 220, 260      # stats terminal offset + height
    updated = datetime.date.today().strftime("%b %d, %Y")

    kt = "0;0.125;0.29;0.333;0.458;0.625;0.667;0.792;0.958;1"
    phrases = [("AI Engineer", 132), ("Full Stack Developer", 240), ("Building AI Products", 240)]
    widths = [
        "0;132;132;0;0;0;0;0;0;0",
        "0;0;0;0;240;240;0;0;0;0",
        "0;0;0;0;0;0;0;240;240;0",
    ]
    clips, texts = [], []
    for i, ((txt, tl), vals) in enumerate(zip(phrases, widths)):
        clips.append(
            f'<clipPath id="cp{i}"><rect x="46" y="106" width="0" height="30">'
            f'<animate attributeName="width" values="{vals}" keyTimes="{kt}" '
            f'dur="12s" repeatCount="indefinite"/></rect></clipPath>'
        )
        texts.append(
            f'<g clip-path="url(#cp{i})"><text x="46" y="128" fill="{WHITE}" textLength="{tl}" '
            f'lengthAdjust="spacingAndGlyphs" font-size="20">{txt}</text></g>'
        )

    cx, cy, r = 112, ST_Y + 138, 46
    circ = 2 * 3.14159265 * r

    flame = (
        f'<g transform="translate({cx},{ST_Y+90})">'
        f'<circle r="19" fill="{BG}"/>'
        f'<path d="M0.5,-15 C2,-8.5 6.2,-6.8 7.8,-2.4 C10,3.6 6.2,11.5 0,11.5 '
        f'C-6.2,11.5 -10,3.6 -7.8,-2.4 C-6.7,-5.4 -4.2,-6.2 -3.2,-9.2 '
        f'C-2.3,-12 -0.6,-13.8 0.5,-15 Z" fill="{WHITE}"/>'
        f'<path d="M0.8,-2.2 C2.2,0.8 3.8,2.4 3.8,4.9 C3.8,7.9 2,9.6 0,9.6 '
        f'C-2,9.6 -3.8,7.9 -3.8,4.9 C-3.8,2.8 -1.4,0.6 0.8,-2.2 Z" fill="{BG}"/>'
        f'</g>'
    )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{MONO}">
<defs>
  <linearGradient id="ring" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0%" stop-color="{WHITE}"/><stop offset="100%" stop-color="{MUTED}"/>
  </linearGradient>
  {"".join(clips)}
</defs>

{chrome(W, WH_H, 0, "ashraf@github: ~$ ./whoami.sh")}
<text x="24" y="62" font-size="14"><tspan fill="{SILVER}">$</tspan><tspan fill="{TITLE}" dx="8">whoami --role</tspan></text>
<text x="24" y="128" fill="{SILVER}" font-size="20">&#8250;</text>
{"".join(texts)}
<rect y="110" width="10" height="22" fill="{WHITE}" x="46">
  <animate attributeName="x" values="46;178;178;46;286;286;46;286;286;46" keyTimes="{kt}" dur="12s" repeatCount="indefinite"/>
  <animate attributeName="opacity" values="1;1;0;0;1" keyTimes="0;0.45;0.5;0.95;1" dur="1.1s" repeatCount="indefinite"/>
</rect>
<path d="M24,158 L416,158" stroke="{GRID}"/>
<text x="24" y="184" font-size="13"><tspan fill="{MUTED}">status:</tspan><tspan fill="{SILVER}" dx="8">building</tspan></text>
<circle cx="404" cy="179" r="5" fill="{LIVE}"><animate attributeName="opacity" values="1;0.25;1" dur="2s" repeatCount="indefinite"/></circle>
<circle cx="404" cy="179" r="5" fill="none" stroke="{LIVE}" stroke-width="1.5">
  <animate attributeName="r" values="5;13;13" dur="2s" repeatCount="indefinite"/>
  <animate attributeName="opacity" values="0.7;0;0" dur="2s" repeatCount="indefinite"/>
</circle>

{chrome(W, ST_H, ST_Y, "ashraf@github: ~$ ./stats.sh")}
<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{FAINT}" stroke-width="7"/>
<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="url(#ring)" stroke-width="7"
        stroke-linecap="round" transform="rotate(-90 {cx} {cy})"
        stroke-dasharray="{circ:.1f}" stroke-dashoffset="{circ:.1f}">
  <animate attributeName="stroke-dashoffset" from="{circ:.1f}" to="0" dur="1.6s" begin="0.2s"
           fill="freeze" calcMode="spline" keyTimes="0;1" keySplines="0.3 0 0.2 1"/>
</circle>
<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{SILVER}" stroke-width="1.5" opacity="0">
  <animate attributeName="r" values="{r};{r+14};{r+14}" dur="2.8s" begin="1.6s" repeatCount="indefinite"/>
  <animate attributeName="opacity" values="0.45;0;0" dur="2.8s" begin="1.6s" repeatCount="indefinite"/>
</circle>
{flame}
<text x="{cx}" y="{cy+13}" text-anchor="middle" fill="{WHITE}" font-size="34" font-weight="bold" opacity="0">{current}
  <animate attributeName="opacity" values="0;1" dur="0.5s" begin="0.9s" fill="freeze"/></text>
<text x="{cx}" y="{ST_Y+212}" text-anchor="middle" fill="{SILVER}" font-size="11" letter-spacing="1.4">CURRENT STREAK</text>
<text x="{cx}" y="{ST_Y+230}" text-anchor="middle" fill="{MUTED}" font-size="10">days in a row</text>

<path d="M228,{ST_Y+62} L228,{ST_Y+222}" stroke="{GRID}"/>

<text x="334" y="{ST_Y+108}" text-anchor="middle" fill="{WHITE}" font-size="26" font-weight="bold">{total:,}</text>
<text x="334" y="{ST_Y+127}" text-anchor="middle" fill="{MUTED}" font-size="9.5" letter-spacing="0.8">CONTRIBUTIONS</text>
<path d="M256,{ST_Y+150} L412,{ST_Y+150}" stroke="{GRID}"/>
<text x="334" y="{ST_Y+186}" text-anchor="middle" fill="{WHITE}" font-size="26" font-weight="bold">{longest}</text>
<text x="334" y="{ST_Y+205}" text-anchor="middle" fill="{MUTED}" font-size="9.5" letter-spacing="0.8">LONGEST STREAK</text>

<text x="{W-14}" y="{H-10}" text-anchor="end" fill="#2E2E2E" font-size="8.5">updated {updated}</text>
</svg>'''


def build_activity(weekly, mlabels, mvalues):
    W, H = 780, 268
    updated = datetime.date.today().strftime("%b %d, %Y")

    lx0, lx1, ly0, ly1 = 8, 356, 46, 216
    n = len(weekly)
    mx = max(weekly) or 1
    step = (lx1 - lx0) / (n - 1) if n > 1 else 0
    pts = [(lx0 + i * step, ly1 - (v / mx) * (ly1 - ly0)) for i, v in enumerate(weekly)]
    line_d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area_d = line_d + f" L{pts[-1][0]:.1f},{ly1} L{pts[0][0]:.1f},{ly1} Z"

    grid = "".join(
        f'<path d="M{lx0},{y} L{lx1},{y}" stroke="{GRID}"/>'
        for y in range(ly0 + 8, ly1 + 1, 40)
    )
    dots = "".join(
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.2" fill="{BG}" stroke="{WHITE}" stroke-width="2" opacity="0">'
        f'<animate attributeName="opacity" values="0;1" dur="0.4s" begin="{1.0+i*0.05:.2f}s" fill="freeze"/></circle>'
        for i, (x, y) in enumerate(pts)
    )

    bx0, bx1, base, top = 424, 772, 216, 46
    m = len(mvalues)
    gap = 13
    bw = (bx1 - bx0 - gap * (m - 1)) / m
    mmax = max(mvalues) or 1
    bars, labels = [], []
    for i, (lab, v) in enumerate(zip(mlabels, mvalues)):
        x = bx0 + i * (bw + gap)
        h = max((v / mmax) * (base - top), 2)
        bars.append(
            f'<rect x="{x:.1f}" y="{base}" width="{bw:.1f}" height="0" rx="2" fill="url(#bar)">'
            f'<animate attributeName="y" from="{base}" to="{base-h:.1f}" dur="0.6s" begin="{0.25+i*0.06:.2f}s" '
            f'fill="freeze" calcMode="spline" keySplines="0.3 0 0.2 1"/>'
            f'<animate attributeName="height" from="0" to="{h:.1f}" dur="0.6s" begin="{0.25+i*0.06:.2f}s" '
            f'fill="freeze" calcMode="spline" keySplines="0.3 0 0.2 1"/></rect>'
        )
        labels.append(
            f'<text x="{x+bw/2:.1f}" y="{base+16}" text-anchor="middle" fill="{MUTED}" font-size="9">{lab}</text>'
        )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{MONO}">
<defs>
  <linearGradient id="area" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="{WHITE}" stop-opacity="0.22"/>
    <stop offset="100%" stop-color="{WHITE}" stop-opacity="0"/>
  </linearGradient>
  <linearGradient id="bar" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="{SILVER}"/><stop offset="100%" stop-color="#4A4A4A"/>
  </linearGradient>
  <clipPath id="lp"><rect x="{lx0}" y="{ly0-8}" width="{lx1-lx0}" height="{ly1-ly0+8}"/></clipPath>
</defs>

<text x="{lx0}" y="26" fill="{SILVER}" font-size="12">contributions / week</text>
<text x="{lx1}" y="26" text-anchor="end" fill="{MUTED}" font-size="10">last 12w</text>
{grid}
<g clip-path="url(#lp)"><path d="{area_d}" fill="url(#area)"/></g>
<path d="{line_d}" fill="none" stroke="{WHITE}" stroke-width="2.4" stroke-linecap="round"
      stroke-linejoin="round" stroke-dasharray="1400" stroke-dashoffset="1400">
  <animate attributeName="stroke-dashoffset" from="1400" to="0" dur="1s" begin="0.15s" fill="freeze"
           calcMode="spline" keySplines="0.3 0 0.2 1"/></path>
{dots}
<path d="M{lx0},{ly1+0.5} L{lx1},{ly1+0.5}" stroke="{BORDER}"/>

<text x="{bx0}" y="26" fill="{SILVER}" font-size="12">contributions / month</text>
<text x="{bx1}" y="26" text-anchor="end" fill="{MUTED}" font-size="10">last 12mo</text>
<path d="M{bx0},{base+0.5} L{bx1},{base+0.5}" stroke="{BORDER}"/>
{"".join(bars)}
{"".join(labels)}

<text x="{W-8}" y="{H-8}" text-anchor="end" fill="#2E2E2E" font-size="8.5">updated {updated}</text>
</svg>'''


def main():
    if not TOKEN:
        print("No token; leaving SVGs untouched.", file=sys.stderr)
        return 1
    try:
        days, total = fetch_days()
        current, longest = streaks(days)
        weekly = weekly_totals(days)
        mlabels, mvalues = monthly_totals(days)
    except Exception as exc:  # noqa: BLE001
        print(f"Fetch failed: {exc}; leaving SVGs untouched.", file=sys.stderr)
        return 1

    with open(RIGHT_OUT, "w", encoding="utf-8") as fh:
        fh.write(build_right_column(current, total, longest))
    with open(ACTIVITY_OUT, "w", encoding="utf-8") as fh:
        fh.write(build_activity(weekly, mlabels, mvalues))

    print(f"current={current} total={total} longest={longest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
