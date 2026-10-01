#!/usr/bin/env python3
"""
gen_cards.py - terminal-style GitHub profile cards. Pure stdlib, no deps.

  python3 scripts/gen_cards.py            # live data (needs GH_TOKEN / GITHUB_TOKEN)
  python3 scripts/gen_cards.py --sample   # offline demo data

Env: GH_USER (default DarkHeart01), GH_TOKEN, OUT_DIR (default ./profile)
"""
import datetime as dt
import json
import math
import os
import re
import sys
import textwrap
import urllib.request
from xml.sax.saxutils import escape as esc

USER = os.environ.get("GH_USER", "DarkHeart01")
OUT = os.environ.get("OUT_DIR", "profile")
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")

# ---------------------------------------------------------------- theme
PANEL, EDGE = "#0a110a", "#1d3b22"
G, GB, MID, DIM = "#00c853", "#39ff88", "#7fbf8f", "#3f6b4b"
AMBER, OFF = "#ffb000", "#0f2113"
FONT = "ui-monospace,SFMono-Regular,Menlo,Consolas,'Liberation Mono','DejaVu Sans Mono',monospace"
FULL, HALF = 720, 358


# ---------------------------------------------------------------- svg helpers
def T(x, y, s, size=12, fill=MID, anchor="start", weight="normal", glow=False):
    f = ' filter="url(#glow)"' if glow else ""
    return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" text-anchor="{anchor}" '
            f'font-weight="{weight}" xml:space="preserve"{f}>{esc(str(s))}</text>')


def TT(x, y, parts, size=12):
    """One text element, several coloured runs: parts = [(text, fill, weight)]"""
    spans = "".join(
        f'<tspan fill="{c}" font-weight="{w}">{esc(str(t))}</tspan>' for t, c, w in parts)
    return f'<text x="{x}" y="{y}" font-size="{size}" xml:space="preserve">{spans}</text>'


def cursor(x, y, size=11):
    return (f'<rect x="{x:.1f}" y="{y - size + 1}" width="{size * 0.6:.1f}" height="{size}" fill="{GB}">'
            f'<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.5;1" '
            f'dur="1.1s" repeatCount="indefinite"/></rect>')


def prompt(cmd, y=42):
    s = f"$ {cmd}"
    return T(14, y, s, 11, DIM) + cursor(14 + len(s) * 6.6 + 4, y)


def leds(x, y, on, total, w=6.6, gap=2, h=10, col=G):
    out = []
    for i in range(total):
        c = col if i < on else OFF
        out.append(f'<rect x="{x + i * (w + gap):.1f}" y="{y}" width="{w}" height="{h}" fill="{c}"/>')
    return "".join(out)


def frame(w, h, title, body):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" font-family="{FONT}">
<defs>
<filter id="glow" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="1.5" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
<linearGradient id="tb" x1="0" x2="1" y1="0" y2="0"><stop offset="0" stop-color="#1c6b32"/><stop offset="1" stop-color="#0b150c"/></linearGradient>
<pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="1" y="3" fill="#000" fill-opacity="0.30"/></pattern>
</defs>
<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" fill="{PANEL}" stroke="{EDGE}"/>
<rect x="1" y="1" width="{w - 2}" height="22" fill="url(#tb)"/>
<text x="10" y="16" font-size="11" fill="#d8ffe4" font-weight="bold">{esc(title)}</text>
<text x="{w - 10}" y="16" font-size="11" fill="{MID}" text-anchor="end" xml:space="preserve">[_] [#] [x]</text>
{chr(10).join(body)}
<rect x="1" y="23" width="{w - 2}" height="{h - 24}" fill="url(#scan)"/>
</svg>
'''


def fmt(d, year=False):
    return f"{d:%b} {d.day}" + (f", {d.year}" if year else "")


# ---------------------------------------------------------------- cards
def pin_card(r):
    W, H = HALF, 140
    name = r["name"]
    shown = name if len(name) <= 34 else name[:33] + "…"
    desc = (r.get("description") or "no description provided").strip()
    lines = textwrap.wrap(desc, 40)
    if len(lines) > 2:
        lines = [lines[0], lines[1][:37].rstrip() + "…"]
    b = [prompt("cat README.md"), T(14, 64, "> " + shown, 15, GB, weight="bold", glow=True)]
    for i, ln in enumerate(lines):
        b.append(T(14, 86 + i * 16, ("# " if i == 0 else "  ") + ln, 12, MID))
    b.append(f'<line x1="14" y1="108" x2="{W - 14}" y2="108" stroke="{EDGE}" stroke-dasharray="3 3"/>')
    if r.get("lang"):
        b.append(f'<rect x="14" y="119" width="9" height="9" fill="{r.get("color") or "#888888"}"/>')
        b.append(T(29, 128, r["lang"], 11, MID))
    else:
        b.append(T(14, 128, "n/a", 11, DIM))
    b.append(T(W - 14, 128, f'stars:{r.get("stars", 0)}  forks:{r.get("forks", 0)}', 11, DIM, "end"))
    return frame(W, H, f"~/projects/{shown}", b)


def stats_card(d):
    W, H = HALF, 196
    fol = "--" if d["followers"] is None else d["followers"]
    rows = [("stars", d["stars"]), (f"commits_{d['year']}", d["commits"]),
            ("pull_requests", d["prs"]), ("issues", d["issues"]),
            ("contributed_to", d["contrib_to"]), ("followers", fol)]
    b = [prompt(f"./stats --user {d['login']}")]
    for i, (k, v) in enumerate(rows):
        b.append(TT(14, 68 + i * 21, [((k + " ").ljust(19, "."), MID, "normal"), (f" {v}", GB, "bold")], 12.5))
    xp = (d["commits"] + 5 * d["prs"] + 3 * d["issues"] + 5 * d["stars"]
          + 3 * d["contrib_to"] + 2 * (d["followers"] or 0))
    lvl = int(math.sqrt(xp / 25))
    lo, hi = 25 * lvl * lvl, 25 * (lvl + 1) ** 2
    frac = (xp - lo) / (hi - lo)
    px = 214
    b += [f'<rect x="{px}" y="54" width="130" height="126" fill="none" stroke="{EDGE}"/>',
          T(px + 65, 74, "CLEARANCE", 10, DIM, "middle"),
          T(px + 65, 126, f"{lvl:02d}", 50, GB, "middle", "bold", True),
          T(px + 65, 144, "LVL", 11, MID, "middle"),
          leds(px + 11, 150, round(frac * 10), 10, w=9, gap=2, h=8),
          T(px + 65, 174, f"xp {xp}/{hi}", 10, DIM, "middle")]
    return frame(W, H, f"stats.sh --user {d['login']}", b)


def lang_card(d):
    W = HALF
    rows = d["langs"][:6]
    H = 66 + 24 * (len(rows) - 1) + 20
    b = [prompt("langs --top 6")]
    mx = rows[0]["pct"] if rows else 1
    for i, r in enumerate(rows):
        y = 66 + i * 24
        b.append(f'<rect x="12" y="{y - 9}" width="10" height="10" fill="{r["color"]}"/>')
        b.append(T(28, y, r["name"], 12, MID))
        b.append(leds(150, y - 9, max(1, round(r["pct"] / mx * 18)), 18, w=6.6, gap=2, h=10))
        b.append(T(W - 14, y, f'{r["pct"]:.1f}%', 12, GB, "end", "bold"))
    return frame(W, H, "langs.sh", b)


def streak_card(d):
    W, H = FULL, 146
    cur, lng = d["cur"], d["lng"]
    rng = lambda t: "—" if not t[0] else f"{fmt(t[1])} - {fmt(t[2])}"
    cols = [("CURRENT STREAK (days)", cur[0], rng(cur), AMBER),
            ("LONGEST STREAK (days)", lng[0], rng(lng), GB),
            ("TOTAL CONTRIBUTIONS", d["total"], f"since {fmt(d['since'], True)}", GB)]
    b = [prompt("uptime")]
    for (lab, val, sub, col), cx in zip(cols, (120, 360, 600)):
        b += [T(cx, 70, lab, 10, DIM, "middle"),
              T(cx, 112, val, 40, col, "middle", "bold", True),
              T(cx, 132, sub, 11, MID, "middle")]
    for x in (240, 480):
        b.append(f'<line x1="{x}" y1="56" x2="{x}" y2="134" stroke="{EDGE}" stroke-dasharray="3 3"/>')
    return frame(W, H, "uptime", b)


def activity_card(d):
    W = FULL
    days = d["last30"]
    mx = max(c for _, c in days) or 1
    ROWS, BH, GAP = 16, 7, 2
    P = BH + GAP
    unit = math.ceil(mx / ROWS)
    top = 60
    base = top + ROWS * P
    x0, bw = 44, 14
    slot = (W - 20 - x0) / len(days)
    H = base + 44
    b = [prompt("scope --channel contributions --last 30d")]
    for k in (4, 8, 12, 16):
        y = base - k * P
        b.append(f'<line x1="{x0}" y1="{y}" x2="{W - 20}" y2="{y}" stroke="{EDGE}" stroke-dasharray="2 4"/>')
        b.append(T(x0 - 6, y + 3, k * unit, 9, DIM, "end"))
    b.append(f'<line x1="{x0}" y1="{base + 1}" x2="{W - 20}" y2="{base + 1}" stroke="{DIM}"/>')
    blocks = []
    peak_day = None
    for i, (day, c) in enumerate(days):
        x = x0 + i * slot + (slot - bw) / 2
        cx = x + bw / 2
        n = math.ceil(c / unit) if c else 0
        hot = c == mx and mx > 0
        if hot and peak_day is None:
            peak_day = day
        col = AMBER if hot else G
        if n == 0:
            blocks.append(f'<rect x="{x:.1f}" y="{base - 1}" width="{bw}" height="1" fill="{DIM}"/>')
        for j in range(n):
            blocks.append(f'<rect x="{x:.1f}" y="{base - (j + 1) * P + GAP}" width="{bw}" height="{BH}" fill="{col}"/>')
        b.append(T(f"{cx:.1f}", base + 15, day.day, 9, MID, "middle"))
        if i == 0 or day.day == 1:
            b.append(T(f"{cx:.1f}", base + 26, f"{day:%b}".lower(), 9, DIM, "middle"))
    b.append(f'<g filter="url(#glow)">{"".join(blocks)}</g>')
    b.append(T(14, H - 8,
               f"1 block = {unit} contribution{'s' if unit > 1 else ''}   "
               f"peak: {mx} on {fmt(peak_day) if peak_day else '-'}   "
               f"30d total: {sum(c for _, c in days)}", 10, DIM))
    return frame(W, H, "scope.exe  -  contributions / last 30 days", b)


def ach_card(d):
    W, H = FULL, 172
    items = [
        ("ARCTIC_CODE_VAULT", True, "contributor"),
        (f"100_COMMITS_{d['year']}", d["commits"] >= 100, f"{min(d['commits'], 100)}/100"),
        ("500_CONTRIBUTIONS", d["total"] >= 500, f"{min(d['total'], 500)}/500"),
        ("1000_CONTRIBUTIONS", d["total"] >= 1000, f"{min(d['total'], 1000)}/1000"),
        ("7_DAY_STREAK", d["lng"][0] >= 7, f"{min(d['lng'][0], 7)}/7"),
        ("30_DAY_STREAK", d["lng"][0] >= 30, f"{min(d['lng'][0], 30)}/30"),
        ("POLYGLOT_5", len(d["langs"]) >= 5, f"{min(len(d['langs']), 5)}/5"),
        ("10_PULL_REQUESTS", d["prs"] >= 10, f"{min(d['prs'], 10)}/10"),
    ]
    b = [prompt("ls ~/.achievements")]
    for i, (name, ok, det) in enumerate(items):
        x0 = 16 if i % 2 == 0 else 372
        x1 = 346 if i % 2 == 0 else 704
        y = 68 + (i // 2) * 26
        if ok:
            b.append(TT(x0, y, [("[x] ", GB, "bold"), (name, GB, "bold")], 12))
            b.append(T(x1, y, det, 11, MID, "end"))
        else:
            b.append(TT(x0, y, [("[ ] ", DIM, "normal"), (name, DIM, "normal")], 12))
            b.append(T(x1, y, det, 11, DIM, "end"))
    done = sum(1 for _, ok, _ in items if ok)
    b.append(T(14, H - 10, f"{done}/{len(items)} unlocked", 10, DIM))
    return frame(W, H, "~/.achievements", b)


# ---------------------------------------------------------------- data
Q_PROFILE = """
query($login:String!){ user(login:$login){
  createdAt
  followers{ totalCount }
  repositoriesContributedTo(first:1, contributionTypes:[COMMIT,PULL_REQUEST,ISSUE,REPOSITORY]){ totalCount }
  repositories(first:100, ownerAffiliations:OWNER, isFork:false){ nodes{
    stargazerCount
    languages(first:10, orderBy:{field:SIZE, direction:DESC}){ edges{ size node{ name color } } } } }
  pinnedItems(first:6, types:REPOSITORY){ nodes{ ... on Repository{
    name description stargazerCount forkCount owner{ login } primaryLanguage{ name color } } } }
}}"""

Q_YEAR = """
query($login:String!, $from:DateTime!, $to:DateTime!){ user(login:$login){
  contributionsCollection(from:$from, to:$to){
    totalCommitContributions totalPullRequestContributions totalIssueContributions
    contributionCalendar{ weeks{ contributionDays{ date contributionCount } } } } } }"""


def gql(query, variables):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json",
                 "User-Agent": "profile-cards"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if "errors" in data:
        raise RuntimeError(data["errors"])
    return data["data"]


def streaks(days, today):
    n, d = 0, today if days.get(today, 0) > 0 else today - dt.timedelta(1)
    end = d
    while days.get(d, 0) > 0:
        n += 1
        d -= dt.timedelta(1)
    cur = (n, d + dt.timedelta(1), end) if n else (0, None, None)
    best, run, start = (0, None, None), 0, None
    if days:
        day = min(days)
        while day <= today:
            if days.get(day, 0) > 0:
                if run == 0:
                    start = day
                run += 1
                if run > best[0]:
                    best = (run, start, day)
            else:
                run = 0
            day += dt.timedelta(1)
    return cur, best


def build(days, today, since, **kw):
    cur, lng = streaks(days, today)
    last30 = [(today - dt.timedelta(29 - i), days.get(today - dt.timedelta(29 - i), 0)) for i in range(30)]
    return dict(login=USER, year=today.year, total=sum(days.values()), since=since,
                cur=cur, lng=lng, last30=last30, **kw)


def fetch_live():
    p = gql(Q_PROFILE, {"login": USER})["user"]
    now = dt.datetime.now(dt.timezone.utc)
    today = now.date()
    since = dt.date.fromisoformat(p["createdAt"][:10])
    days, commits, prs, issues = {}, 0, 0, 0
    for y in range(since.year, today.year + 1):
        end = now.strftime("%Y-%m-%dT%H:%M:%SZ") if y == today.year else f"{y}-12-31T23:59:59Z"
        c = gql(Q_YEAR, {"login": USER, "from": f"{y}-01-01T00:00:00Z", "to": end})["user"]["contributionsCollection"]
        for w in c["contributionCalendar"]["weeks"]:
            for dd in w["contributionDays"]:
                days[dt.date.fromisoformat(dd["date"])] = dd["contributionCount"]
        if y == today.year:
            commits, prs, issues = (c["totalCommitContributions"], c["totalPullRequestContributions"],
                                    c["totalIssueContributions"])
    stars, sizes, colors = 0, {}, {}
    for r in p["repositories"]["nodes"]:
        stars += r["stargazerCount"]
        for e in r["languages"]["edges"]:
            n = e["node"]["name"]
            sizes[n] = sizes.get(n, 0) + e["size"]
            colors[n] = e["node"]["color"] or "#888888"
    tot = sum(sizes.values()) or 1
    langs = [dict(name=n, pct=s * 100 / tot, color=colors[n])
             for n, s in sorted(sizes.items(), key=lambda kv: -kv[1])]
    pins = []
    for n in p["pinnedItems"]["nodes"]:
        if not n:
            continue
        pl = n["primaryLanguage"] or {}
        pins.append(dict(name=n["name"], owner=n["owner"]["login"], description=n["description"],
                         lang=pl.get("name"), color=pl.get("color"),
                         stars=n["stargazerCount"], forks=n["forkCount"]))
    return build(days, today, since, stars=stars, commits=commits, prs=prs, issues=issues,
                 contrib_to=p["repositoriesContributedTo"]["totalCount"],
                 followers=p["followers"]["totalCount"], langs=langs), pins


def fetch_sample():
    today = dt.date(2026, 10, 1)
    days = {dt.date(2026, 9, k): v for k, v in
            {4: 4, 17: 2, 19: 4, 20: 9, 22: 3, 23: 1, 24: 10, 25: 1, 26: 14,
             27: 10, 28: 9, 29: 6, 30: 13}.items()}
    days[dt.date(2019, 11, 25)] = 1
    d = build(days, today, dt.date(2019, 11, 25), stars=0, commits=329, prs=5, issues=0,
              contrib_to=19, followers=None,
              langs=[dict(name="TypeScript", pct=39.02, color="#3178c6"),
                     dict(name="Python", pct=27.05, color="#3572A5"),
                     dict(name="Go", pct=18.15, color="#00ADD8"),
                     dict(name="C++", pct=5.98, color="#f34b7d"),
                     dict(name="JavaScript", pct=5.79, color="#f1e05a"),
                     dict(name="Jupyter Notebook", pct=4.01, color="#DA5B0B")])
    d["total"], d["cur"], d["lng"] = 526, (9, dt.date(2026, 9, 22), dt.date(2026, 9, 30)), (9, dt.date(2026, 9, 22), dt.date(2026, 9, 30))
    pins = [dict(name="erp-masterdata-integration", lang="Go", color="#00ADD8"),
            dict(name="General-Swarm", lang="Python", color="#3572A5"),
            dict(name="Auditor", description="The Main Module for the Auditor", lang="Python", color="#3572A5"),
            dict(name="TTS", lang="Python", color="#3572A5"),
            dict(name="Realstate_allan", lang="Go", color="#00ADD8", forks=1),
            dict(name="Serapeum")]
    return d, pins


# ---------------------------------------------------------------- main
def write(name, svg):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
        f.write(svg)
    print("wrote", os.path.join(OUT, name))


def main():
    d, pins = fetch_sample() if "--sample" in sys.argv else fetch_live()
    write("stats.svg", stats_card(d))
    write("top-langs.svg", lang_card(d))
    write("streak.svg", streak_card(d))
    write("activity-graph.svg", activity_card(d))
    write("achievements.svg", ach_card(d))
    for r in pins:
        write(f"pin-{re.sub(r'[^a-z0-9]+', '-', r['name'].lower()).strip('-')}.svg", pin_card(r))


if __name__ == "__main__":
    main()
