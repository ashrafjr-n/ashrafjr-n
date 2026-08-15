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


def main():
    if not TOKEN:
        print("No token found; leaving existing SVG untouched.", file=sys.stderr)
        return 1
    try:
        days, total = fetch_days()
        current, longest = streaks(days)
    except Exception as exc:  # noqa: BLE001
        print(f"Fetch failed: {exc}; leaving existing SVG untouched.", file=sys.stderr)
        return 1

    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(build_svg(current, total, longest))
    print(f"current={current} total={total} longest={longest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
