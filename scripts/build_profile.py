#!/usr/bin/env python3
"""Draws the profile cards in assets/ from profile.json + live GitHub data.

GitHub Actions runs this every day (.github/workflows/update-hero.yml), so new
repos, pushes, contributions and streaks appear on their own.
Standard library only. Without GITHUB_TOKEN it uses sample data for previews:
    python scripts/build_profile.py
"""
import base64
import datetime as dt
import json
import math
import os
import random
import urllib.request
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
FONTS = ASSETS / "fonts"

# navy · cream · coral
CREAM = "#F4EDE3"
CREAM_2 = "#EBE2D4"
RULE = "#DDD2C1"
NAVY = "#1A2B55"
NAVY_2 = "#2A4C88"
INK = "#1A2B55"
MUTED = "#6F7682"
CORAL = "#FF4A2B"
CORAL_DIM = "#A23A2E"
CREAM_DIM = "#4F6394"
HEAT = ["#E6DCCB", "#B9C4DE", "#6D86BC", "#24407E", CORAL]

W = 840
CH = 0.6  # IBM Plex Mono advance = 0.6em

FONT_FILES = {
    "F": "fraunces-latin-400-normal.woff2",
    "FI": "fraunces-latin-400-italic.woff2",
    "M": "ibm-plex-mono-latin-400-normal.woff2",
    "MB": "ibm-plex-mono-latin-600-normal.woff2",
}


def svg(w, h, body, css="", title="", fonts=("F", "FI", "M", "MB")):
    faces = "".join(
        f"@font-face{{font-family:'{f}';src:url(data:font/woff2;base64,"
        f"{base64.b64encode((FONTS / FONT_FILES[f]).read_bytes()).decode()}) format('woff2')}}" for f in fonts)
    base = (".f{font-family:'F',Georgia,serif}.fi{font-family:'FI',Georgia,serif}"
            ".m{font-family:'M',ui-monospace,Menlo,monospace;white-space:pre}"
            ".mb{font-family:'MB',ui-monospace,Menlo,monospace;white-space:pre}")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'role="img" aria-label="{escape(title)}"><title>{escape(title)}</title>'
            f"<style>{faces}{base}{css}</style>{body}</svg>\n")


def card(w, h, fill=CREAM, stroke=RULE):
    return f'<rect x=".5" y=".5" width="{w-1}" height="{h-1}" rx="14" fill="{fill}" stroke="{stroke}"/>'


def t(x, y, s, cls="m", size=11, fill=INK, anchor="start", extra=""):
    return (f'<text x="{x}" y="{y}" class="{cls}" font-size="{size}" fill="{fill}" '
            f'text-anchor="{anchor}" xml:space="preserve" {extra}>{s}</text>')


def kicker(x, y, s, fill=MUTED, anchor="start"):
    return t(x, y, escape(s.upper()), "mb", 9.5, fill, anchor, 'letter-spacing="1.8"')


def ago(iso, now):
    s = (now - dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))).total_seconds()
    for unit, n in ((" yr", 31536000), (" mo", 2592000), ("d", 86400), ("h", 3600), ("m", 60)):
        if s >= n:
            return f"{int(s // n)}{unit} ago"
    return "just now"


# ------------------------------------------------------------------ data
QUERY = """query($login:String!){ user(login:$login){
  followers{totalCount}
  contributionsCollection{ contributionCalendar{ totalContributions
    weeks{ contributionDays{ date contributionCount } } } }
  repositories(first:100, ownerAffiliations:OWNER, privacy:PUBLIC, orderBy:{field:PUSHED_AT,direction:DESC}){
    totalCount nodes{ name description stargazerCount pushedAt isFork primaryLanguage{ name color } } } } }"""


def fetch(login, token):
    req = urllib.request.Request("https://api.github.com/graphql",
                                 data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
                                 headers={"Authorization": f"bearer {token}", "User-Agent": "profile-builder"})
    with urllib.request.urlopen(req, timeout=30) as r:
        payload = json.load(r)
    if "errors" in payload:
        raise SystemExit(f"GitHub API error: {payload['errors']}")
    u = payload["data"]["user"]
    days = [(dt.date.fromisoformat(d["date"]), d["contributionCount"])
            for wk in u["contributionsCollection"]["contributionCalendar"]["weeks"] for d in wk["contributionDays"]]
    return {"days": days, "repos": [r for r in u["repositories"]["nodes"] if not r["isFork"]],
            "followers": u["followers"]["totalCount"]}


def sample(today):
    rnd = random.Random(3)
    start = today - dt.timedelta(days=364 + (today.weekday() + 1) % 7)
    days, d = [], start
    while d <= today:
        age = (today - d).days
        p = 0.05 if age > 120 else 0.3 if age > 30 else 0.75
        days.append((d, rnd.choice([1, 2, 3, 5, 8]) if rnd.random() < p else 0))
        d += dt.timedelta(days=1)
    mk = lambda n, desc, lang, col, st, dago: {
        "name": n, "description": desc, "stargazerCount": st,
        "pushedAt": (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=dago)).isoformat(),
        "primaryLanguage": {"name": lang, "color": col} if lang else None}
    repos = [mk("Bossgod360", "", "Python", "#3572A5", 0, 0),
             mk("Mouse-Pose-Estimation", "Mouse pose estimation using SLEAP for behavioural analysis", "Python", "#3572A5", 3, 2),
             mk("Identifying-Blood-Cells-CNN", "", "Jupyter Notebook", "#DA5B0B", 0, 9),
             mk("Eudaimonia", "", "Swift", "#F05138", 0, 24),
             mk("Aura", "", "HTML", "#E34C26", 0, 40),
             mk("Ascendance-Kingdom", "", "Java", "#B07219", 0, 70),
             mk("Choose-Your-Own-Adventure-Game", "", "Java", "#B07219", 0, 90)]
    return {"days": days, "repos": repos, "followers": 4}


def streaks(days, today):
    counts = dict(days)
    cur, d = 0, today if counts.get(today) else today - dt.timedelta(days=1)
    while counts.get(d):
        cur += 1
        d -= dt.timedelta(days=1)
    longest = run = 0
    for _, c in sorted(days):
        run = run + 1 if c else 0
        longest = max(longest, run)
    return cur, longest


# ------------------------------------------------------------------ ASCII DNA
def dna_frames(n_frames=40, rows=30, amp=12, twist=0.30):
    """Rotating double helix, shaded by depth like the classic spinning donut."""
    ramp = ".,:;+=*#%@"          # far -> near
    cols = amp * 2 + 5
    frames = []
    for f in range(n_frames):
        phi = 2 * math.pi * f / n_frames
        grid = [[(" ", None, -9.0) for _ in range(cols)] for _ in range(rows)]

        def put(r, c, ch, cls, z):
            if 0 <= r < rows and 0 <= c < cols and z > grid[r][c][2]:
                grid[r][c] = (ch, cls, z)

        def shade(z):
            return ramp[max(0, min(len(ramp) - 1, int((z + 1) / 2 * len(ramp))))]

        # strands: sample finely so fast-moving parts stay continuous, 2 chars thick
        steps = rows * 8
        for i in range(steps + 1):
            rf = i / 8
            r = round(rf)
            th = rf * twist + phi
            for k, (hot, cold) in enumerate((("bA", "dA"), ("bB", "dB"))):
                a = th + k * math.pi
                x, z = math.cos(a), math.sin(a)
                cx = cols / 2 - .5 + x * amp
                cls = hot if z > -0.25 else cold
                put(r, round(cx), shade(z), cls, z + 0.02)
                put(r, round(cx + (1 if x < 0 else -1) * 0.9), shade(z - 0.35), cls, z - 0.01)
        # base pairs every row: blue half meets red half at the middle
        for r in range(rows):
            th = r * twist + phi
            ca, za = cols / 2 - .5 + math.cos(th) * amp, math.sin(th)
            cb, zb = cols / 2 - .5 - math.cos(th) * amp, -math.sin(th)
            a_, b_ = round(ca), round(cb)
            step = 1 if b_ > a_ else -1
            for c in range(a_ + step, b_, step):
                t = (c - a_) / (b_ - a_)
                z = za + (zb - za) * t
                if r % 2 == 0:
                    cls = ("rA" if t < .5 else "rB") if z > -0.3 else ("dA" if t < .5 else "dB")
                    put(r, c, "-" if abs(z) < .5 else ("=" if z > 0 else "."), cls, z - 0.2)
        frames.append(grid)
    return frames, cols


def dna_group(x0, y0, size=10.5, lh=11.4, n_frames=40, period=5.0, rows=27):
    frames, cols = dna_frames(n_frames, rows=rows, amp=12)
    color = {"bA": CORAL, "dA": CORAL_DIM, "bB": CREAM, "dB": CREAM_DIM, "rA": "#FF9580", "rB": "#C3D0E8"}
    out = []
    for i, grid in enumerate(frames):
        lines = []
        for r, row in enumerate(grid):
            spans, cur, buf = [], None, ""
            for ch, cls, _ in row + [("", "END", 0)]:
                if cls != cur and buf:
                    fill = f' fill="{color[cur]}"' if cur else ""
                    spans.append(f"<tspan{fill}>{escape(buf)}</tspan>")
                    buf = ""
                cur = cls
                buf += ch
            lines.append(f'<text x="{x0:.1f}" y="{y0 + r*lh:.1f}" class="m" font-size="{size}" xml:space="preserve">{"".join(spans)}</text>')
        delay = -period * (n_frames - i) / n_frames
        out.append(f'<g class="fr" style="animation-delay:{delay:.3f}s">{"".join(lines)}</g>')
    css = (f".fr{{opacity:0;animation:fr {period}s steps(1,end) infinite}}"
           f"@keyframes fr{{0%{{opacity:1}}{100/n_frames:.3f}%{{opacity:0}}100%{{opacity:0}}}}")
    return "".join(out), css, cols * size * CH


# ------------------------------------------------------------------ hero
def hero(p):
    H = 380
    px, py, pw, ph = 548, 20, 272, 340  # navy panel
    helix, hcss, hw = dna_group(px + (pw - 29 * 10.5 * CH) / 2, py + 34)
    whoami_w = len("$ whoami") * 12 * CH
    tag = "".join(t(40, 282 + i * 24, escape(s), "f", 17, INK) for i, s in enumerate(p["tagline"]))
    body = f"""
{card(W, H)}
<clipPath id="type"><rect x="40" y="40" width="0" height="24">
  <animate attributeName="width" from="0" to="{whoami_w + 2:.1f}" begin=".3s" dur=".6s" fill="freeze"/></rect></clipPath>
<g clip-path="url(#type)">{t(40, 58, '<tspan fill="' + CORAL + '">$</tspan> whoami', "m", 12, MUTED)}</g>
<rect x="{40 + whoami_w + 6:.1f}" y="47" width="7.2" height="14" fill="{CORAL}" class="cur"/>
<g class="rise" style="animation-delay:1s">{t(34, 156, escape(p["first_name"]), "f", 96, NAVY, extra='letter-spacing="-2.5"')}</g>
<g class="rise" style="animation-delay:1.2s">{t(34, 244, escape(p["last_name"]), "fi", 96, CORAL, extra='letter-spacing="-2.5"')}</g>
<g class="fade" style="animation-delay:1.6s">{tag}{t(40, 344, escape(p["meta"]), "m", 11, MUTED, extra='letter-spacing=".4"')}</g>

<rect x="{px}" y="{py}" width="{pw}" height="{ph}" rx="10" fill="{NAVY}"/>
<clipPath id="panel"><rect x="{px}" y="{py}" width="{pw}" height="{ph}" rx="10"/></clipPath>
<g clip-path="url(#panel)">{helix}</g>
{t(px + 16, py + 22, "~/dna --spin", "m", 9.5, "#8EA2CF")}
<circle cx="{px + pw - 20}" cy="{py + 18}" r="3.5" fill="{CORAL}" class="pulse"/>
"""
    css = hcss + """
.cur{animation:blink 1.1s steps(1) infinite}@keyframes blink{50%{opacity:0}}
.rise{opacity:0;animation:rise .9s cubic-bezier(.2,.7,.2,1) forwards}
@keyframes rise{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:none}}
.fade{opacity:0;animation:fade 1s ease forwards}@keyframes fade{to{opacity:1}}
.pulse{animation:pulse 2s ease-in-out infinite}@keyframes pulse{50%{opacity:.25}}
"""
    return svg(W, H, body, css, title=f"{p['first_name']} {p['last_name']}")


# ------------------------------------------------------------------ track record
def track_record(p):
    rows = p["track_record"]
    top, rh = 88, 58
    H = top + rh * len(rows) + 14
    out = []
    for i, r in enumerate(rows):
        y = top + i * rh
        out.append(t(40, y + 26, escape(r["when"]), "m", 10.5, MUTED)
                   + t(132, y + 25, escape(r["title"]), "f", 18, INK)
                   + t(132, y + 45, escape(r["sub"]), "f", 13.5, MUTED)
                   + t(W - 40, y + 26, escape(r["tag"].upper()), "mb", 9, CORAL, "end", 'letter-spacing="1.6"'))
        if i < len(rows) - 1:
            out.append(f'<line x1="40" x2="{W-40}" y1="{y+rh}" y2="{y+rh}" stroke="{RULE}"/>')
    body = f"""
{card(W, H)}
<text x="40" y="56" class="f" font-size="28" fill="{INK}">Track record, <tspan class="fi" fill="{CORAL}">so far</tspan></text>
{kicker(W-40, 52, "research · build · lead", anchor="end")}
<line x1="40" x2="{W-40}" y1="{top}" y2="{top}" stroke="{INK}" stroke-width="1.2"/>
{''.join(out)}
"""
    return svg(W, H, body, title="Track record")


# ------------------------------------------------------------------ activity
def activity(days, today):
    H = 214
    cell, gap = 11, 3
    pitch = cell + gap
    weeks = []
    for d, c in sorted(days):
        if not weeks or d.weekday() == 6:
            weeks.append([])
        weeks[-1].append((d, c))
    weeks = weeks[-53:]
    peak = max((c for _, c in days), default=0) or 1
    x0, y0 = (W - len(weeks) * pitch + gap) // 2, 84
    rects, months, last = [], [], None
    for wi, wk in enumerate(weeks):
        x = x0 + wi * pitch
        for d, c in wk:
            lvl = 0 if not c else min(4, 1 + int(3 * c / peak + .25))
            rects.append(f'<rect x="{x}" y="{y0 + ((d.weekday()+1) % 7)*pitch}" width="{cell}" height="{cell}" rx="2.5" fill="{HEAT[lvl]}"/>')
        if wk[0][0].month != last and x < W - 190:
            months.append(t(x, 198, wk[0][0].strftime("%b"), "m", 9, MUTED))
            last = wk[0][0].month
    legend = t(W - 152, 198, "less", "m", 9, MUTED, "end")
    legend += "".join(f'<rect x="{W-146+i*14}" y="189" width="10" height="10" rx="2" fill="{c}"/>' for i, c in enumerate(HEAT))
    legend += t(W - 74, 198, "more", "m", 9, MUTED)
    total = sum(c for _, c in days)
    cur, longest = streaks(days, today)
    right = f"{total} contributions · " + (f"{cur}-day streak" if cur else f"best streak {longest}d")
    scan = (f'<rect y="{y0-3}" width="{pitch}" height="{7*pitch+3}" rx="3" fill="{CORAL}" opacity=".18">'
            f'<animate attributeName="x" from="{x0-2}" to="{x0 + len(weeks)*pitch - 2}" dur="8s" repeatCount="indefinite"/></rect>')
    body = f"""
{card(W, H)}
<text x="40" y="56" class="f" font-size="28" fill="{INK}">Every day, <tspan class="fi" fill="{CORAL}">a little further</tspan></text>
{t(W-40, 52, escape(right), "m", 10.5, MUTED, "end")}
{''.join(rects)}{scan}{''.join(months)}{legend}
"""
    return svg(W, H, body, title=f"{total} contributions in the last year")


# ------------------------------------------------------------------ repos (self-updating)
def repos_card(p, repos):
    now = dt.datetime.now(dt.timezone.utc)
    hide = set(p.get("hide_repos", []))
    repos = [r for r in repos if r["name"] not in hide][:6]
    top, rh = 88, 40
    H = top + rh * len(repos) + 14
    out = []
    for i, r in enumerate(repos):
        y = top + i * rh
        lang = r.get("primaryLanguage") or {"name": "", "color": RULE}
        name = r["name"] if len(r["name"]) <= 30 else r["name"][:29] + "…"
        desc = (r.get("description") or "").strip()
        desc = desc if len(desc) <= 40 else desc[:39].rstrip() + "…"
        out.append(f'<g class="row" style="animation-delay:{.1 + i*.08:.2f}s">'
                   + t(40, y + 26, escape(name), "mb", 12.5, NAVY)
                   + t(300, y + 26, escape(desc), "fi", 14, MUTED)
                   + f'<circle cx="632" cy="{y+22}" r="4" fill="{lang["color"] or RULE}"/>'
                   + t(642, y + 26, escape(lang["name"][:11]), "m", 10.5, INK)
                   + t(W - 40, y + 26, ago(r["pushedAt"], now), "m", 10.5, MUTED, "end") + "</g>")
        if i < len(repos) - 1:
            out.append(f'<line x1="40" x2="{W-40}" y1="{y+rh}" y2="{y+rh}" stroke="{RULE}"/>')
    body = f"""
{card(W, H)}
<text x="40" y="56" class="f" font-size="28" fill="{INK}">Recently <tspan class="fi" fill="{CORAL}">shipped</tspan></text>
{kicker(W-40, 52, "auto-updated daily", anchor="end")}
<line x1="40" x2="{W-40}" y1="{top}" y2="{top}" stroke="{INK}" stroke-width="1.2"/>
{''.join(out)}
"""
    css = ".row{opacity:0;animation:in .5s ease forwards}@keyframes in{from{opacity:0;transform:translateX(-6px)}to{opacity:1;transform:none}}"
    return svg(W, H, body, css, title="My most recently updated repositories")


def main():
    p = json.loads((ROOT / "profile.json").read_text())
    today = dt.date.today()
    token = os.environ.get("GITHUB_TOKEN")
    data = fetch(p["github_user"], token) if token else sample(today)
    if not token:
        print("No GITHUB_TOKEN: using sample data (preview only).")
    out = {"hero.svg": hero(p), "track-record.svg": track_record(p),
           "activity.svg": activity(data["days"], today), "repos.svg": repos_card(p, data["repos"])}
    ASSETS.mkdir(exist_ok=True)
    for name, content in out.items():
        (ASSETS / name).write_text(content, encoding="utf-8")
        print(f"wrote assets/{name} ({len(content)//1024} KB)")


if __name__ == "__main__":
    main()
