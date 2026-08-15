#!/usr/bin/env python3
"""Generate stats_terminal.svg from real GitHub contribution data."""

import os
import sys
import json
import datetime
import urllib.request

LOGIN = os.environ.get("GH_LOGIN", "ashrafjr-n")
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
OUT = "stats_terminal.svg"
MONITOR_OUT = "monitor_terminal.svg"

API = "https://api.github.com/graphql"

Q_CREATED = """
query($login: String!) {
  user(login: $login) { createdAt }
}
"""

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
        API,
        data=body,
        headers={
            "Authorization": f"bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "readme-stats-generator",
        },
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

    days = {}
    total = 0
    year_start = start
    while year_start <= today:
        year_end = min(year_start + datetime.timedelta(days=364), today)
        data = gql(
            Q_CAL,
            {
                "login": LOGIN,
                "from": f"{year_start.isoformat()}T00:00:00Z",
                "to": f"{year_end.isoformat()}T23:59:59Z",
            },
        )
        cal = data["user"]["contributionsCollection"]["contributionCalendar"]
        total += cal["totalContributions"]
        for week in cal["weeks"]:
            for d in week["contributionDays"]:
                days[d["date"]] = d["contributionCount"]
        year_start = year_end + datetime.timedelta(days=1)

    return days, total


def streaks(days):
    today = datetime.date.today()
    dates = sorted(days.keys())
    if not dates:
        return 0, 0

    # longest streak across all history
    longest = 0
    run = 0
    prev = None
    for ds in dates:
        d = datetime.date.fromisoformat(ds)
        if days[ds] > 0:
            if prev is not None and (d - prev).days == 1:
                run += 1
            else:
                run = 1
            longest = max(longest, run)
            prev = d
        else:
            run = 0
            prev = None

    # current streak: walk backwards from today (today not yet counted is ok)
    cur = 0
    day = today
    if days.get(day.isoformat(), 0) == 0:
        day -= datetime.timedelta(days=1)
    while days.get(day.isoformat(), 0) > 0:
        cur += 1
        day -= datetime.timedelta(days=1)

    return cur, longest


def human(n):
    return f"{n:,}"


def weekly_totals(days, weeks=12):
    """Return the last `weeks` weekly contribution totals (Mon-Sun), oldest first."""
    today = datetime.date.today()
    this_monday = today - datetime.timedelta(days=today.weekday())
    buckets = []
    for i in range(weeks - 1, -1, -1):
        wk_start = this_monday - datetime.timedelta(weeks=i)
        total = 0
        for j in range(7):
            d = wk_start + datetime.timedelta(days=j)
            if d > today:
                break
            total += days.get(d.isoformat(), 0)
        buckets.append(total)
    return buckets


def monthly_totals(days, months=12):
    """Return the last `months` months' contribution totals and labels, oldest first."""
    today = datetime.date.today()
    y, m = today.year, today.month
    slots = []
    for i in range(months - 1, -1, -1):
        mm = m - i
        yy = y
        while mm <= 0:
            mm += 12
            yy -= 1
        slots.append((yy, mm))

    totals = {ym: 0 for ym in slots}
    for ds, count in days.items():
        d = datetime.date.fromisoformat(ds)
        ym = (d.year, d.month)
        if ym in totals:
            totals[ym] += count

    labels = [datetime.date(yy, mm, 1).strftime("%b") for yy, mm in slots]
    values = [totals[ym] for ym in slots]
    return labels, values


def build_svg(current, total, longest):
    W, H = 340, 300
    cx, cy, r = 170, 118, 40
    circ = 2 * 3.141592653589793 * r
    mono = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"
    updated = datetime.date.today().strftime("%b %d, %Y")

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <defs>
    <linearGradient id="ringGrad" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#8B8FFF"/>
      <stop offset="100%" stop-color="#27C93F"/>
    </linearGradient>
  </defs>

  <rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="8" fill="#0D1117" stroke="#30363D"/>
  <path d="M0,8 A8,8 0 0 1 8,0 L{W-8},0 A8,8 0 0 1 {W},8 L{W},36 L0,36 Z" fill="#161B22"/>
  <path d="M0,35.5 L{W},35.5" stroke="#30363D" stroke-width="1"/>
  <circle cx="20" cy="18" r="6" fill="#FF5F56"/>
  <circle cx="40" cy="18" r="6" fill="#FFBD2E"/>
  <circle cx="60" cy="18" r="6" fill="#27C93F"/>
  <text x="{W//2+8}" y="23" text-anchor="middle" fill="#8B949E"
        font-family="{mono}" font-size="12">ashraf@github: ~$ ./stats.sh</text>

  <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#21262D" stroke-width="6"/>
  <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="url(#ringGrad)" stroke-width="6"
          stroke-linecap="round" transform="rotate(-90 {cx} {cy})"
          stroke-dasharray="{circ:.1f}" stroke-dashoffset="{circ:.1f}">
    <animate attributeName="stroke-dashoffset" from="{circ:.1f}" to="0"
             dur="1.6s" begin="0.2s" fill="freeze" calcMode="spline"
             keyTimes="0;1" keySplines="0.3 0 0.2 1"/>
  </circle>
  <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#8B8FFF" stroke-width="1.5" opacity="0">
    <animate attributeName="r" values="{r};{r+14};{r+14}" dur="2.6s" begin="1.4s" repeatCount="indefinite"/>
    <animate attributeName="opacity" values="0.55;0;0" dur="2.6s" begin="1.4s" repeatCount="indefinite"/>
  </circle>

  <text x="{cx}" y="{cy+11}" text-anchor="middle" fill="#FFFFFF"
        font-family="{mono}" font-size="32" font-weight="bold" opacity="0">{current}
    <animate attributeName="opacity" values="0;1" dur="0.5s" begin="0.9s" fill="freeze"/>
  </text>

  <text x="{cx}" y="{cy+66}" text-anchor="middle" fill="#8B8FFF"
        font-family="{mono}" font-size="11" letter-spacing="1.5">CURRENT STREAK</text>
  <text x="{cx}" y="{cy+84}" text-anchor="middle" fill="#484F58"
        font-family="{mono}" font-size="10">days in a row</text>

  <path d="M28,{cy+104} L{W-28},{cy+104}" stroke="#21262D" stroke-width="1"/>

  <text x="92" y="{cy+136}" text-anchor="middle" fill="#FFFFFF"
        font-family="{mono}" font-size="20" font-weight="bold">{human(total)}</text>
  <text x="92" y="{cy+153}" text-anchor="middle" fill="#484F58"
        font-family="{mono}" font-size="9.5" letter-spacing="0.8">CONTRIBUTIONS</text>

  <path d="M170,{cy+118} L170,{cy+158}" stroke="#21262D" stroke-width="1"/>

  <text x="248" y="{cy+136}" text-anchor="middle" fill="#FFFFFF"
        font-family="{mono}" font-size="20" font-weight="bold">{longest}</text>
  <text x="248" y="{cy+153}" text-anchor="middle" fill="#484F58"
        font-family="{mono}" font-size="9.5" letter-spacing="0.8">LONGEST STREAK</text>

  <text x="{W-14}" y="{H-9}" text-anchor="end" fill="#30363D"
        font-family="{mono}" font-size="8.5">updated {updated}</text>
</svg>
"""


def build_monitor_svg(weekly, month_labels, month_values):
    W, H = 440, 500
    mono = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"
    plot_x0, plot_x1 = 28, 412
    plot_top, plot_bottom = 80, 300

    # ---- line/dots: last 12 weeks ----
    n = len(weekly)
    max_w = max(weekly) if max(weekly, default=0) > 0 else 1
    step = (plot_x1 - plot_x0) / (n - 1) if n > 1 else 0
    pts = []
    for i, v in enumerate(weekly):
        x = plot_x0 + i * step
        y = plot_bottom - (v / max_w) * (plot_bottom - plot_top - 10)
        pts.append((x, y))

    line_d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area_d = line_d + f" L{pts[-1][0]:.1f},{plot_bottom} L{pts[0][0]:.1f},{plot_bottom} Z"

    grid = []
    for gy in range(plot_top + 20, plot_bottom + 1, 44):
        grid.append(f'<path d="M{plot_x0},{gy} L{plot_x1},{gy}" stroke="#21262D" stroke-width="1"/>')
    for gx in range(plot_x0, plot_x1 + 1, 48):
        grid.append(f'<path d="M{gx},{plot_top} L{gx},{plot_bottom}" stroke="#161B22" stroke-width="1"/>')

    dots = []
    for i, (x, y) in enumerate(pts):
        dots.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="#0D1117" stroke="#8B8FFF" stroke-width="2" opacity="0">'
            f'<animate attributeName="opacity" values="0;1" dur="0.4s" begin="{1.1 + i*0.05:.2f}s" fill="freeze"/>'
            f'</circle>'
        )

    # ---- bars: last 12 months ----
    bx0, bx1 = 28, 412
    base_y, top_y = 452, 352
    m = len(month_values)
    gap = 14
    bw = (bx1 - bx0 - gap * (m - 1)) / m
    max_m = max(month_values) if max(month_values, default=0) > 0 else 1

    bars = []
    labels = []
    for i, (lab, v) in enumerate(zip(month_labels, month_values)):
        x = bx0 + i * (bw + gap)
        h = (v / max_m) * (base_y - top_y) if max_m else 0
        h = max(h, 2)
        y = base_y - h
        bars.append(
            f'<rect x="{x:.1f}" y="{base_y}" width="{bw:.1f}" height="0" rx="2" fill="url(#barGrad)">'
            f'<animate attributeName="y" from="{base_y}" to="{y:.1f}" dur="0.6s" '
            f'begin="{0.3 + i*0.06:.2f}s" fill="freeze" calcMode="spline" keySplines="0.3 0 0.2 1"/>'
            f'<animate attributeName="height" from="0" to="{h:.1f}" dur="0.6s" '
            f'begin="{0.3 + i*0.06:.2f}s" fill="freeze" calcMode="spline" keySplines="0.3 0 0.2 1"/>'
            f'</rect>'
        )
        labels.append(
            f'<text x="{x + bw/2:.1f}" y="{base_y + 16}" text-anchor="middle" fill="#484F58" '
            f'font-family="{mono}" font-size="9">{lab}</text>'
        )

    updated = datetime.date.today().strftime("%b %d, %Y")

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <defs>
    <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#8B8FFF" stop-opacity="0.35"/>
      <stop offset="100%" stop-color="#8B8FFF" stop-opacity="0"/>
    </linearGradient>
    <linearGradient id="barGrad" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#8B8FFF"/>
      <stop offset="100%" stop-color="#3D4499"/>
    </linearGradient>
    <clipPath id="plotClip"><rect x="{plot_x0}" y="{plot_top}" width="{plot_x1-plot_x0}" height="{plot_bottom-plot_top}"/></clipPath>
  </defs>

  <rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="8" fill="#0D1117" stroke="#30363D"/>
  <path d="M0,8 A8,8 0 0 1 8,0 L{W-8},0 A8,8 0 0 1 {W},8 L{W},36 L0,36 Z" fill="#161B22"/>
  <path d="M0,35.5 L{W},35.5" stroke="#30363D" stroke-width="1"/>
  <circle cx="20" cy="18" r="6" fill="#FF5F56"/>
  <circle cx="40" cy="18" r="6" fill="#FFBD2E"/>
  <circle cx="60" cy="18" r="6" fill="#27C93F"/>
  <text x="{W//2+5}" y="23" text-anchor="middle" fill="#8B949E"
        font-family="{mono}" font-size="12.5">ashraf@github: ~$ ./activity.sh</text>

  <text x="24" y="60" font-family="{mono}" font-size="12" fill="#484F58">contributions / week (last 12w)</text>

  {chr(10).join("  " + g for g in grid)}

  <g clip-path="url(#plotClip)">
    <path d="{area_d}" fill="url(#areaGrad)"/>
  </g>
  <path d="{line_d}" fill="none" stroke="#8B8FFF" stroke-width="2.5"
        stroke-linecap="round" stroke-linejoin="round"
        stroke-dasharray="1400" stroke-dashoffset="1400">
    <animate attributeName="stroke-dashoffset" from="1400" to="0" dur="1s" begin="0.15s" fill="freeze"
             calcMode="spline" keySplines="0.3 0 0.2 1"/>
  </path>
  {chr(10).join("  " + d for d in dots)}

  <path d="M24,330 L416,330" stroke="#21262D" stroke-width="1"/>
  <text x="24" y="350" font-family="{mono}" font-size="12" fill="#484F58">contributions / month (last 12mo)</text>

  <path d="M{bx0},{base_y+0.5} L{bx1},{base_y+0.5}" stroke="#30363D" stroke-width="1"/>
  {chr(10).join("  " + b for b in bars)}
  {chr(10).join("  " + l for l in labels)}

  <text x="{W-14}" y="{H-14}" text-anchor="end" fill="#30363D"
        font-family="{mono}" font-size="8.5">updated {updated}</text>
</svg>
'''


def main():
    if not TOKEN:
        print("No token found; leaving existing SVG untouched.", file=sys.stderr)
        return 1
    try:
        days, total = fetch_days()
        current, longest = streaks(days)
        weekly = weekly_totals(days, weeks=12)
        month_labels, month_values = monthly_totals(days, months=12)
    except Exception as exc:  # noqa: BLE001
        print(f"Fetch failed: {exc}; leaving existing SVGs untouched.", file=sys.stderr)
        return 1

    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(build_svg(current, total, longest))
    with open(MONITOR_OUT, "w", encoding="utf-8") as fh:
        fh.write(build_monitor_svg(weekly, month_labels, month_values))

    print(f"current={current} total={total} longest={longest}")
    print(f"weekly={weekly}")
    print(f"months={list(zip(month_labels, month_values))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
