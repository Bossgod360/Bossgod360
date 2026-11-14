#!/usr/bin/env python3
"""Draws the profile SVGs in assets/ from profile.json + live GitHub data.

GitHub Actions runs this every day (.github/workflows/update-hero.yml), so new
repos, pushes, contributions and streaks show up on their own.
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

BG = "#0A0D14"
PANEL = "#0F131C"
LINE = "#1E2633"
TEXT = "#E6EAF2"
MUTED = "#7A8496"
DIM = "#3A4352"
BLUE = "#4C8DFF"
BLUE_DIM = "#1F3E78"
RED = "#FF4B4B"
RED_DIM = "#7A2328"

W = 840
CH = 0.6  # IBM Plex Mono advance = 0.6em


def font_css():
    out = ""
    for fam, f in (("M", "ibm-plex-mono-latin-400-normal.woff2"), ("MB", "ibm-plex-mono-latin-600-normal.woff2")):
        b64 = base64.b64encode((FONTS / f).read_bytes()).decode()
        out += f"@font-face{{font-family:'{fam}';src:url(data:font/woff2;base64,{b64}) format('woff2')}}"
    return out + (".m{font-family:'M',ui-monospace,Menlo,Consolas,monospace;white-space:pre}"
                  ".b{font-family:'MB',ui-monospace,Menlo,Consolas,monospace;white-space:pre}")


def svg(w, h, body, css="", title=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'role="img" aria-label="{escape(title)}"><title>{escape(title)}</title>'
            f"<style>{font_css()}{css}</style>{body}</svg>\n")


def window(w, h, title):
    return (f'<rect x=".5" y=".5" width="{w-1}" height="{h-1}" rx="12" fill="{BG}" stroke="{LINE}"/>'
            f'<path d="M1,36 H{w-1}" stroke="{LINE}"/>'
            f'<circle cx="22" cy="18" r="5.5" fill="{RED}"/><circle cx="40" cy="18" r="5.5" fill="{BLUE}"/>'
            f'<circle cx="58" cy="18" r="5.5" fill="{DIM}"/>'
            f'<text x="{w/2}" y="22" class="m" font-size="11" fill="{MUTED}" text-anchor="middle">{escape(title)}</text>')


def txt(x, y, s, size=13, fill=TEXT, cls="m", extra=""):
    return f'<text x="{x}" y="{y}" class="{cls}" font-size="{size}" fill="{fill}" xml:space="preserve" {extra}>{s}</text>'


def ago(iso, now):
    d = now - dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))
    s = d.total_seconds()
    for unit, n in (("y", 31536000), ("mo", 2592000), ("d", 86400), ("h", 3600), ("m", 60)):
        if s >= n:
            return f"{int(s // n)}{unit}"
    return "now"


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


def dna_svg_group(x0, y0, size=11, lh=12.2, n_frames=40, period=4.8):
    frames, cols = dna_frames(n_frames)
    color = {"bA": BLUE, "dA": BLUE_DIM, "bB": RED, "dB": RED_DIM, "rA": "#9DB8E8", "rB": "#E89D9D"}
    out = []
    for i, grid in enumerate(frames):
        rows = []
        for r, row in enumerate(grid):
            spans, cur, buf = [], None, ""
            for ch, cls, _ in row + [("", "END", 0)]:
                if cls != cur and buf:
                    fill = f' fill="{color[cur]}"' if cur else ""
                    spans.append(f"<tspan{fill}>{escape(buf)}</tspan>")
                    buf = ""
                cur = cls
                buf += ch
            rows.append(f'<text x="{x0}" y="{y0 + r*lh:.1f}" class="m" font-size="{size}" xml:space="preserve">{"".join(spans)}</text>')
        delay = -period * (n_frames - i) / n_frames
        out.append(f'<g class="fr" style="animation-delay:{delay:.3f}s">{"".join(rows)}</g>')
    css = (f".fr{{opacity:0;animation:fr {period}s steps(1,end) infinite}}"
           f"@keyframes fr{{0%{{opacity:1}}{100/n_frames:.3f}%{{opacity:0}}100%{{opacity:0}}}}")
    return "".join(out), css, cols * size * CH


# ------------------------------------------------------------------ hero (terminal)
def hero(p, data, today):
    H = 452
    now = dt.datetime.now(dt.timezone.utc)
    hide = set(p.get("hide_repos", []))
    repos = [r for r in data["repos"] if r["name"] not in hide]
    total = sum(c for _, c in data["days"])
    cur, longest = streaks(data["days"], today)
    principle = p["principles"][today.toordinal() % len(p["principles"])]

    size, lh, x0, y = 13, 21, 28, 66
    lines = []  # (kind, content)
    def cmd(s): lines.append(("cmd", s))
    def out(s): lines.append(("out", s))

    cmd("whoami")
    out(f'<tspan class="b" fill="{TEXT}">{escape(p["name"])}</tspan><tspan fill="{MUTED}">  // {escape(p["role"])}</tspan>')
    cmd("cat focus.txt")
    for f in p["focus"]:
        out(f'<tspan fill="{RED}">&gt; </tspan>{escape(f)}')
    cmd("ls ~/repos --sort=recent | head -4")
    for r in repos[:4]:
        name = r["name"] if len(r["name"]) <= 30 else r["name"][:29] + "~"
        lang = (r.get("primaryLanguage") or {}).get("name", "-")
        lang = lang if len(lang) <= 10 else lang[:9] + "~"
        out(f'<tspan fill="{BLUE}">{escape(name.ljust(31))}</tspan><tspan fill="{MUTED}">{escape(lang.ljust(11))}{ago(r["pushedAt"], now).rjust(4)}</tspan>')
    cmd("./stats.sh")
    streak = f"{cur}-day streak" if cur else f"best streak {longest}d"
    out(f'<tspan fill="{TEXT}">{len(repos)}</tspan><tspan fill="{MUTED}"> repos . </tspan>'
        f'<tspan fill="{TEXT}">{total}</tspan><tspan fill="{MUTED}"> contributions this year . </tspan>'
        f'<tspan fill="{RED}">{streak}</tspan>')
    cmd("echo $PRINCIPLE")
    out(f'<tspan class="b" fill="{TEXT}">{escape(principle)}</tspan>')

    body, t = [], 0.4
    for kind, content in lines:
        if kind == "cmd":
            n = len(content)
            wpx = (n + 2) * size * CH + 2
            cid = f"c{len(body)}"
            body.append(f'<clipPath id="{cid}"><rect x="{x0}" y="{y-15}" width="{size*CH*2}" height="20">'
                        f'<animate attributeName="width" from="{size*CH*2}" to="{wpx:.1f}" begin="{t:.2f}s" dur="{n*0.045:.2f}s" fill="freeze"/></rect></clipPath>'
                        f'<g opacity="0"><set attributeName="opacity" to="1" begin="{t-0.15:.2f}s" fill="freeze"/>'
                        f'<g clip-path="url(#{cid})">{txt(x0, y, f"<tspan fill=\"{RED}\">$</tspan> {escape(content)}", size)}</g></g>')
            t += n * 0.045 + 0.25
        else:
            body.append(f'<g opacity="0"><set attributeName="opacity" to="1" begin="{t:.2f}s" fill="freeze"/>'
                        f'{txt(x0, y, content, size, TEXT)}</g>')
            t += 0.12
        y += lh
    # prompt with blinking cursor
    body.append(f'<g opacity="0"><set attributeName="opacity" to="1" begin="{t:.2f}s" fill="freeze"/>'
                f'{txt(x0, y, f"<tspan fill=\"{RED}\">$</tspan>", size)}'
                f'<rect x="{x0 + 2*size*CH}" y="{y-12}" width="{size*CH:.1f}" height="15" fill="{BLUE}" class="cur"/></g>')

    dx, dy = 598, 66
    helix, hcss, hw = dna_svg_group(dx, dy)
    deco = (txt(dx + hw / 2, 438, "~/dna --spin", 10, DIM, extra='text-anchor="middle"')
            + f'<path d="M574,52 V420" stroke="{LINE}"/>')
    css = hcss + ".cur{animation:blink 1.1s steps(1) infinite}@keyframes blink{50%{opacity:0}}"
    return svg(W, H, window(W, H, f"{p['name'].split()[0]}@{p['github_user'].lower()}: ~") + "".join(body) + helix + deco,
               css, title=f"{p['name']} - {p['role']}")


# ------------------------------------------------------------------ activity (ASCII heatmap)
def activity(days, today):
    ramp = ".:+*#"
    weeks = []
    for d, c in sorted(days):
        if not weeks or d.weekday() == 6:
            weeks.append([])
        weeks[-1].append((d, c))
    weeks = weeks[-52:]
    peak = max((c for _, c in days), default=1) or 1
    pitch, x0, y0 = 14.6, 34, 78
    H = 230
    cells = []
    for wi, wk in enumerate(weeks):
        for d, c in wk:
            r = (d.weekday() + 1) % 7
            if c == 0:
                ch, fill = ".", DIM
            else:
                lvl = min(4, 1 + int(3 * c / peak + .25))
                ch, fill = ramp[lvl], [BLUE_DIM, BLUE, BLUE, "#8DB6FF", RED][lvl]
            cells.append(f'<tspan x="{x0 + wi*pitch:.1f}" y="{y0 + r*16}" fill="{fill}">{escape(ch)}</tspan>')
    months, last = [], None
    for wi, wk in enumerate(weeks):
        m = wk[0][0].month
        if m != last and x0 + wi * pitch < W - 120:
            months.append(txt(x0 + wi * pitch, y0 + 7 * 16 + 8, wk[0][0].strftime("%b").lower(), 10, MUTED))
            last = m
    total = sum(c for _, c in days)
    head = (txt(28, 60, f'<tspan fill="{RED}">$</tspan> git log --since="1 year" | heatmap', 13)
            + txt(W - 28, 60, f"{total} contributions", 11, MUTED, extra='text-anchor="end"'))
    legend = txt(W - 28, H - 12, f'less <tspan fill="{DIM}">.</tspan> <tspan fill="{BLUE_DIM}">:</tspan> '
                 f'<tspan fill="{BLUE}">+ *</tspan> <tspan fill="#8DB6FF">#</tspan> <tspan fill="{RED}">#</tspan> more',
                 10, MUTED, extra='text-anchor="end"')
    scan = (f'<rect x="{x0-6}" y="{y0-14}" width="12" height="{7*16+2}" fill="{BLUE}" opacity=".10">'
            f'<animate attributeName="x" from="{x0-6}" to="{x0 + len(weeks)*pitch - 6:.0f}" dur="7s" repeatCount="indefinite"/></rect>')
    body = (window(W, H, "activity") + head + scan
            + f'<text class="m" font-size="13" xml:space="preserve">{"".join(cells)}</text>' + "".join(months) + legend)
    return svg(W, H, body, title=f"{total} contributions in the last year")


# ------------------------------------------------------------------ repos (ls -la, self-updating)
def repos_card(p, data):
    now = dt.datetime.now(dt.timezone.utc)
    hide = set(p.get("hide_repos", []))
    repos = [r for r in data["repos"] if r["name"] not in hide][:8]
    rh, top = 26, 84
    H = top + rh * len(repos) + 8
    rows = []
    for i, r in enumerate(repos):
        y = top + i * rh
        lang = r.get("primaryLanguage") or {"name": "-", "color": DIM}
        name = r["name"] if len(r["name"]) <= 30 else r["name"][:29] + "~"
        desc = (r.get("description") or "").strip() or "-"
        desc = desc if len(desc) <= 36 else desc[:35] + "~"
        rows.append(
            f'<g class="row" style="animation-delay:{0.15 + i*0.09:.2f}s">'
            + txt(28, y, f'<tspan fill="{BLUE}">{escape(name)}</tspan>', 13)
            + txt(292, y, escape(desc), 12, MUTED)
            + f'<circle cx="{604}" cy="{y-4.5}" r="4" fill="{lang["color"] or DIM}"/>'
            + txt(614, y, escape(lang["name"][:12]), 12, MUTED)
            + txt(736, y, f'*{r["stargazerCount"]}', 12, RED if r["stargazerCount"] else DIM)
            + txt(W - 28, y, ago(r["pushedAt"], now), 12, MUTED, extra='text-anchor="end"')
            + "</g>")
    head = (txt(28, 60, f'<tspan fill="{RED}">$</tspan> ls -la ~/repos', 13)
            + txt(W - 28, 60, f"{len(repos)} shown . auto-updated daily", 11, MUTED, extra='text-anchor="end"'))
    css = ".row{opacity:0;animation:in .5s ease forwards}@keyframes in{from{opacity:0;transform:translateX(-6px)}to{opacity:1;transform:none}}"
    return svg(W, H, window(W, H, "~/repos") + head + f'<path d="M28,{top-17} H{W-28}" stroke="{LINE}"/>' + "".join(rows),
               css, title="My repositories, most recently updated first")


def main():
    p = json.loads((ROOT / "profile.json").read_text())
    today = dt.date.today()
    token = os.environ.get("GITHUB_TOKEN")
    data = fetch(p["github_user"], token) if token else sample(today)
    if not token:
        print("No GITHUB_TOKEN: using sample data (preview only).")
    out = {"hero.svg": hero(p, data, today), "activity.svg": activity(data["days"], today),
           "repos.svg": repos_card(p, data)}
    ASSETS.mkdir(exist_ok=True)
    for name, content in out.items():
        (ASSETS / name).write_text(content, encoding="utf-8")
        print(f"wrote assets/{name} ({len(content)//1024} KB)")


if __name__ == "__main__":
    main()
