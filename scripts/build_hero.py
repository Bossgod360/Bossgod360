#!/usr/bin/env python3
"""Builds hero.svg: an animated terminal + rotating ASCII DNA helix.
The terminal pulls your newest public repos from the GitHub API, so the
banner updates itself whenever the workflow runs. Edit profile.json to
change the text. Run locally:  python scripts/build_hero.py
"""
import datetime as dt, json, math, os, random, sys, urllib.request
from xml.sax.saxutils import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = json.load(open(os.path.join(ROOT, "profile.json"), encoding="utf-8"))
USER = CFG["github_user"]
OUT = os.environ.get("HERO_OUT", os.path.join(ROOT, "hero.svg"))
STATIC_T = float(os.environ["HERO_STATIC"]) if os.environ.get("HERO_STATIC") else None  # preview only

W = 960
BG = "#0c1018"
CW = 7.8          # char width at 13px mono
STEP = 21         # terminal row height
T = float(CFG.get("helix_seconds", 8))   # seconds per full rotation


# ---------- data from GitHub ----------
def api(path):
    req = urllib.request.Request(
        "https://api.github.com" + path,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "hero-builder"},
    )
    tok = os.environ.get("GITHUB_TOKEN")
    if tok:
        req.add_header("Authorization", "Bearer " + tok)
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.load(r)


def short(l): return {'Jupyter Notebook': 'Jupyter', 'JavaScript': 'JS', 'TypeScript': 'TS'}.get(l, l or '-')


def ago(iso):
    d = (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))).days
    if d < 1: return "today"
    if d < 14: return f"{d}d"
    if d < 60: return f"{d // 7}w"
    return f"{d // 30}mo"


if os.environ.get("HERO_SAMPLE"):  # dev only: lets you preview without calling the API
    _now = dt.datetime.now(dt.timezone.utc)
    def _s(name, lang, days, stars=0):
        return {"name": name, "language": lang, "fork": False, "stargazers_count": stars,
                "pushed_at": (_now - dt.timedelta(days=days)).isoformat()}
    repos = [_s("Mouse-Pose-Estimation", "Python", 2, 3), _s("Identifying-Blood-Cells-CNN", "Jupyter Notebook", 9),
             _s("Aura", "HTML", 20), _s("Ascendance-Kingdom", "Java", 70), _s("Choose-Your-Own-Adventure-Game", "Java", 120),
             _s("Eudaimonia", "Swift", 200)]
else:
    repos = api(f"/users/{USER}/repos?per_page=100&sort=pushed&type=owner")
repos = [r for r in repos if not r["fork"] and r["name"].lower() != USER.lower()]
repos.sort(key=lambda r: r["pushed_at"], reverse=True)
n_recent = int(CFG.get("recent_count", 4))
recent = repos[:n_recent]
stars = sum(r["stargazers_count"] for r in repos)
lang_count = {}
for r in repos:
    if r["language"]:
        lang_count[short(r["language"])] = lang_count.get(short(r["language"]), 0) + 1
top_langs = [l for l, _ in sorted(lang_count.items(), key=lambda kv: -kv[1])[:3]]


# ---------- terminal content ----------
lines = []
def cmd(t): lines.append(("cmd", [("$ ", "p"), (t, "c")]))
def out(*segs): lines.append(("out", list(segs)))
def clip(s, n): return s if len(s) <= n else s[: n - 1] + "…"

cmd("whoami")
out((clip(CFG["headline"], 46), "b"))
cmd("cat now.txt")
for item in CFG["now"]:
    out(("  > ", "a"), (clip(item, 42), "o"))
cmd(f"ls -t ~/projects | head -{n_recent}")
for r in recent:
    out(("  > ", "a"), (f"{clip(r['name'], 24):<25}", "c"),
        (f"{clip(short(r['language']), 9):<10}", "m"), (f"{ago(r['pushed_at']):>5}", "m"))
cmd("./stats.sh")
out((clip(f"{len(repos)} repos · {stars} stars · {' '.join(top_langs) or 'hello world'}", 46), "o"))
cmd("echo $PRINCIPLE")
out((clip(CFG["principle"], 46), "o"))
cmd("")

x0, y0 = 40, 84
y_last = y0 + (len(lines) - 1) * STEP
H = max(440, y_last + 56)

svg = []
a = svg.append
a(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="t d">')
a(f'<title id="t">{escape(USER)} terminal intro</title>')
a('<desc id="d">An animated terminal lists who the author is and their newest projects, beside a rotating ASCII DNA double helix.</desc>')

HCX = W - 215
a(f"""<style>
text{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;white-space:pre}}
.t{{font-size:13px}}
.p{{fill:#ff9e64}}.c{{fill:#e6edf3}}.o{{fill:#c9d1d9}}.b{{fill:#fff;font-weight:700}}.m{{fill:#7d8590}}.a{{fill:#f2cc60}}
.hx{{font-size:10px;text-anchor:middle}}
.s1{{fill:#f2cc60;font-weight:700}}.s2{{fill:#79c0ff;font-weight:700}}.rg{{fill:#5b6b86}}
.cA{{fill:#ff9e64;font-weight:700}}.cT{{fill:#bb9af7;font-weight:700}}.cG{{fill:#7ee787;font-weight:700}}.cC{{fill:#56d4dd;font-weight:700}}
.rn{{font-size:11px;fill:#79c0ff;opacity:.13}}
.gx{{animation:sx {T}s infinite linear}}
.dp{{animation:dp {T}s infinite linear}}
@keyframes sx{{
0%{{transform:translateX(0);animation-timing-function:cubic-bezier(.61,1,.88,1)}}
25%{{transform:translateX(var(--a));animation-timing-function:cubic-bezier(.12,0,.39,0)}}
50%{{transform:translateX(0);animation-timing-function:cubic-bezier(.61,1,.88,1)}}
75%{{transform:translateX(calc(var(--a) * -1));animation-timing-function:cubic-bezier(.12,0,.39,0)}}
100%{{transform:translateX(0)}}}}
@keyframes dp{{
0%{{opacity:.55;transform:scale(1);animation-timing-function:cubic-bezier(.61,1,.88,1)}}
25%{{opacity:calc(.55 + .45 * var(--k));transform:scale(calc(1 + .3 * var(--k)));animation-timing-function:cubic-bezier(.12,0,.39,0)}}
50%{{opacity:.55;transform:scale(1);animation-timing-function:cubic-bezier(.61,1,.88,1)}}
75%{{opacity:calc(.55 - .45 * var(--k));transform:scale(calc(1 - .3 * var(--k)));animation-timing-function:cubic-bezier(.12,0,.39,0)}}
100%{{opacity:.55;transform:scale(1)}}}}
.rain{{animation:rain linear infinite}}
@keyframes rain{{to{{transform:translateY(var(--h))}}}}
.glow{{animation:glow 6s ease-in-out infinite alternate}}
@keyframes glow{{from{{opacity:.55}}to{{opacity:1}}}}
@keyframes slide{{to{{transform:translateX(var(--w))}}}}
.cursor{{opacity:0;animation:blink 1.1s steps(1) infinite}}
@keyframes blink{{0%,49%{{opacity:1}}50%,100%{{opacity:0}}}}
@media (prefers-reduced-motion:reduce){{.cover{{display:none}}.gx,.dp,.rain,.glow{{animation-play-state:paused}}.cursor{{animation:none;opacity:1}}}}
</style>""")
a(f"""<defs>
<radialGradient id="g" cx="50%" cy="50%" r="50%"><stop offset="0" stop-color="#1f6feb" stop-opacity=".30"/><stop offset="1" stop-color="#1f6feb" stop-opacity="0"/></radialGradient>
<clipPath id="hc"><rect x="590" y="46" width="{W - 20 - 590}" height="{H - 46 - 56}"/></clipPath>
</defs>""")
a(f'<rect x="10" y="10" width="{W - 20}" height="{H - 20}" rx="12" fill="{BG}" stroke="#2d333b"/>')
a('<circle cx="34" cy="32" r="6" fill="#ff5f56"/><circle cx="54" cy="32" r="6" fill="#ffbd2e"/><circle cx="74" cy="32" r="6" fill="#27c93f"/>')
a(f'<text x="{W // 2}" y="37" text-anchor="middle" class="m" style="font-size:12px">~/{escape(USER.lower())}</text>')

# ---- glow + ATGC rain (background layer)
a(f'<ellipse class="glow" cx="{HCX}" cy="{H // 2}" rx="190" ry="{H // 2 - 30}" fill="url(#g)"/>')
rng = random.Random(7)
rows_rain = (H - 100) // 11 + 2
a('<g clip-path="url(#hc)">')
for i, cx in enumerate(range(612, W - 40, 36)):
    seq = "".join(rng.choice("ATGC") for _ in range(rows_rain))
    hgt = rows_rain * 11
    dur = 11 + (i * 3) % 9
    def col(offset):
        ts = "".join(f'<tspan x="{cx}" dy="11">{ch}</tspan>' for ch in seq)
        return f'<text class="rn" x="{cx}" y="{offset}">{ts}</text>'
    if STATIC_T is None:
        a(f'<g class="rain" style="--h:{hgt}px;animation-duration:{dur}s;animation-delay:-{i * 2.3:.1f}s">{col(40)}{col(40 - hgt)}</g>')
    else:
        a(col(40 + (i * 53) % hgt))
a('</g>')

# ---- the helix
sp = 9
R = (H - 126) // sp
HY0 = 76
rungs = 0
fid = 0
def put(x, y, ch, cls, amp, k, d, off=0.0):
    """One character that swings sideways by amp*sin(phase) and fades/scales with depth k*cos(phase)."""
    X = x + off
    if STATIC_T is None:
        dly = -(d % T)
        dly2 = -((d + T / 4) % T)
        return (f'<g transform="translate({X:.1f},{y:.1f})"><g class="gx" style="--a:{amp:.1f}px;animation-delay:{dly:.2f}s">'
                f'<text class="hx dp {cls}" style="--k:{k:.2f};animation-delay:{dly2:.2f}s">{ch}</text></g></g>')
    s = math.sin(2 * math.pi * (STATIC_T + d) / T)
    z = math.cos(2 * math.pi * (STATIC_T + d) / T)
    return (f'<text class="hx {cls}" transform="translate({X + amp * s:.1f},{y:.1f}) scale({1 + .3 * k * z:.2f})" '
            f'opacity="{.55 + .45 * k * z:.2f}">{ch}</text>')

pairs = {"A": "T", "T": "A", "G": "C", "C": "G"}
hel = []
SPAN = R * sp          # vertical extent of the helix in px
PITCH = 170            # px per full twist
def taper_at(y):
    u = (y - HY0) / SPAN
    return 0.40 + 0.60 * (math.sin(math.pi * min(max(u, 0), 1))) ** 0.5
def phase_d(y):        # time offset (s) so the whole column of characters twists
    return (y - HY0) / PITCH * T

# strands: sampled densely along the curve so they read as continuous tubes
n_samp = int(SPAN / 1.8)
for i in range(n_samp + 1):
    y = HY0 + i * SPAN / n_samp
    A = 100 * taper_at(y)
    ch = "@" if i % 2 == 0 else "o"
    hel.append(put(HCX, y, ch, "s1", A, 1.0, phase_d(y)))
    hel.append(put(HCX, y, ch, "s2", -A, -1.0, phase_d(y)))

# base-pair rungs: letters sit at the strands, dotted bridge between them
for r in range(0, R, 2):
    rungs += 1
    y = HY0 + r * sp
    A = 100 * taper_at(y)
    d = phase_d(y)
    base = rng.choice("ATGC")
    for i, k in enumerate([i / 6 * 0.86 for i in range(-6, 7)]):
        hel.append(put(HCX, y, "-" if i % 2 == 0 else ".", "rg", A * k, k, d))
    hel.append(put(HCX, y, base, "c" + base, A * 0.93, 0.93, d))
    hel.append(put(HCX, y, pairs[base], "c" + pairs[base], -A * 0.93, -0.93, d))
a("".join(hel))
a(f'<text class="m" x="{HCX}" y="{H - 28}" text-anchor="middle" style="font-size:11px">helix.exe · {rungs} base pairs · looping</text>')

# ---- terminal text, typed out
t = 0.6
for i, (kind, segs) in enumerate(lines):
    y = y0 + i * STEP
    n = sum(len(s) for s, _ in segs)
    sp_ = 0.045 if kind == "cmd" else 0.014
    dur = max(n * sp_, 0.2)
    inner = "".join(f'<tspan class="{c}">{escape(s)}</tspan>' for s, c in segs)
    a(f'<text class="t" x="{x0}" y="{y}" textLength="{n * CW:.1f}" lengthAdjust="spacing" xml:space="preserve">{inner}</text>')
    if STATIC_T is None:
        w = n * CW + 12
        a(f'<rect class="cover" x="{x0 - 2}" y="{y - 15}" width="{w:.1f}" height="21" fill="{BG}" '
          f'style="--w:{w:.1f}px;animation:slide {dur:.2f}s steps({max(n, 1)}) {t:.2f}s forwards"/>')
    t += dur + (0.4 if kind == "cmd" else 0.18)
a(f'<rect class="cursor" x="{x0 + 2 * CW}" y="{y_last - 12}" width="8" height="16" fill="#f2cc60" '
  f'style="animation-delay:{t:.2f}s{";opacity:1;animation:none" if STATIC_T is not None else ""}"/>')
a("</svg>")

open(OUT, "w", encoding="utf-8").write("\n".join(svg))
print(f"wrote {OUT} ({os.path.getsize(OUT) // 1024} KB) · {len(repos)} repos · recent: {[r['name'] for r in recent]}")
