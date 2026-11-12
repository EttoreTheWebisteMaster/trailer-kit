"""trailer-kit core: chunked HyperFrames films, one source for every format.

A film is a list of chunks. Each chunk is a standalone HyperFrames project
(rendered and cached on its own), so a fix re-renders only the chunks it touches,
and a new format (9x16, 4x5) re-lays out the same scenes instead of cropping.

The kit holds craft only (geometry, camera, text, cursor, render, mix, checks).
Every look decision lives in the project's LOOK dict, so films don't converge.
"""
import hashlib, json, math, os, shutil, subprocess, sys
from pathlib import Path
from PIL import Image

KIT = Path(__file__).resolve().parent
FPS = 30
FORMATS = {"16x9": (1920, 1080), "9x16": (1080, 1920), "4x5": (1080, 1350)}
MAX_UPSCALE = 2.0  # LESSONS: art past 2x reads muddy


class Fmt:
    def __init__(self, name):
        self.name = name
        self.W, self.H = FORMATS[name]
        self.vert = self.H > self.W
        # title-safe box: 80% centre; vertical also keeps clear of top 15% / bottom 20% UI
        if name == "9x16":
            self.safe = (0.1 * self.W, 0.15 * self.H, 0.9 * self.W, 0.80 * self.H)
        else:
            self.safe = (0.1 * self.W, 0.1 * self.H, 0.9 * self.W, 0.9 * self.H)
        self.cx, self.cy = self.W / 2, self.H / 2
        self.u = min(self.W, self.H) / 1080  # 1 unit = 1px at 1080 short side

    def pick(self, h, v=None, p=None):
        """Per-format value: 16x9 -> h, 9x16 -> v, 4x5 -> p (missing ones fall back to h)."""
        return {"16x9": h, "9x16": h if v is None else v, "4x5": h if p is None else p}[self.name]


class Assets:
    """Registry of stills with their ORIGINAL pixel size, so focus points are written
    in the coordinates you see in the source, while files can be downscaled copies."""

    def __init__(self, root, max_px=2600):
        self.root, self.max_px, self.items = Path(root), max_px, {}

    def add(self, key, src, max_px=None, **focus):
        p = self.root / src
        with Image.open(p) as im:
            ow, oh = im.size
        self.items[key] = dict(src=src, ow=ow, oh=oh, focus=focus, max_px=max_px or self.max_px)

    def video(self, key, src, t0, dur, **focus):
        """A clip cut from a source video (t0..t0+dur in the source), placed like a still."""
        r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=width,height",
                            "-of", "csv=p=0", str(self.root / src)], capture_output=True, text=True, check=True)
        ow, oh = map(int, r.stdout.strip().split(","))
        self.items[key] = dict(src=src, ow=ow, oh=oh, fw=ow, fh=oh, focus=focus, kind="video", t0=t0, dur=dur)

    def frame(self, key, src, t, **focus):
        """A still pulled from a video at source time t (a freeze frame)."""
        dst = self.root / "_frames" / f"{key}.png"
        dst.parent.mkdir(exist_ok=True)
        if not dst.exists():
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", str(self.root / src), "-frames:v", "1", str(dst)], check=True)
        self.add(key, f"_frames/{key}.png", **focus)

    def up(self, key, display_scale):
        """Upscale factor vs the shipped file for a display scale given in ORIGINAL px."""
        it = self.items[key]
        return display_scale * it["ow"] / it["fw"]

    def prepare(self, out_dir):
        """Write web-sized JPEG copies (cached) into the chunk asset folder."""
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        for k, it in self.items.items():
            if it.get("kind") == "video":
                vd = out.parent / "vid"
                vd.mkdir(exist_ok=True)
                dst = vd / f"{k}.mp4"
                if not dst.exists():
                    tmp = vd / f"_tmp_{k}.mp4"
                    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(it["t0"]), "-i", str(self.root / it["src"]), "-t", str(it["dur"]),
                                    "-an", "-c:v", "libx264", "-crf", "14", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-g", "12", str(tmp)], check=True)
                    tmp.rename(dst)
                continue
            dst = out / f"{k}.jpg"
            src = self.root / it["src"]
            want = round(min(1.0, it["max_px"] / max(it["ow"], it["oh"])) * it["ow"])
            if dst.exists() and dst.stat().st_mtime >= src.stat().st_mtime:
                with Image.open(dst) as im:
                    it["fw"], it["fh"] = im.size
                if it["fw"] == want:
                    continue
            with Image.open(src) as im:
                if im.mode in ("RGBA", "LA", "P"):        # LESSONS: transparent PNG -> white, not black
                    im = im.convert("RGBA")
                    bg = Image.new("RGBA", im.size, "white")
                    bg.alpha_composite(im)
                    im = bg
                im = im.convert("RGB")
                s = min(1.0, it["max_px"] / max(im.size))
                if s < 1:
                    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
                im.save(dst, quality=92)
                it["fw"], it["fh"] = im.size

    def f(self, key, name):
        return self.items[key]["focus"][name]


class Chunk:
    def __init__(self, film, name, t0, t1):
        self.film, self.name, self.t0, self.t1 = film, name, t0, t1
        self.dur = round(t1 - t0, 4)
        self.L = film.L
        self.els, self.js, self.css, self.warn = [], [], [], []
        self.n = 0

    # ---- time helpers (film time in, chunk-local time out)
    def t(self, film_t):
        return round(film_t - self.t0, 4)

    def uid(self, p="e"):
        self.n += 1
        return f"{p}{self.n}"

    def add(self, html):
        self.els.append(html)

    def tl(self, code):
        self.js.append(code)

    def style(self, css):
        self.css.append(css)

    # ---- building blocks -------------------------------------------------
    def box(self, html="", start=None, end=None, z=1, style="", cls="", id=None):
        """A full-frame layer visible from film time start to end (hard on/off)."""
        id = id or self.uid("b")
        s = self.t(start if start is not None else self.t0)
        e = self.t(end if end is not None else self.t1)
        if "<video" in html:
            # LESSONS: a timed <video> must not sit inside a timed wrapper (frames come out wrong).
            # Wrapper visibility goes through GSAP instead; the video keeps its own data-start.
            self.add(f'<div id="{id}" class="layer {cls}" style="z-index:{z};opacity:0;{style}">{html}</div>')
            self.tl(f'tl.set("#{id}",{{opacity:1}},{max(0,s)});')
            if e < self.dur - 1e-6:
                self.tl(f'tl.set("#{id}",{{opacity:0}},{e});')
            return id
        self.add(f'<div id="{id}" class="clip layer {cls}" data-start="{max(0,s)}" '
                 f'data-duration="{round(e-max(0,s),4)}" style="z-index:{z};{style}">{html}</div>')
        return id

    def photo(self, key, focus, at=None, zoom=1.0, push=None, start=None, end=None, z=1,
              frame=None, filt="", id=None, ease="none", dof=None, vign=None, shake=0, offset=0):
        """Full-cover still. `focus` = point in source px (or a named focus) placed at
        `at` (frame px, default centre). `push` = end zoom multiplier (camera move about
        the focus point). `frame` = (x,y,w,h) window instead of full frame."""
        L, A = self.L, self.film.assets.items[key]
        if isinstance(focus, str):
            focus = self.film.assets.f(key, focus)
        fx, fy = focus
        X, Y, W, H = frame or (0, 0, L.W, L.H)
        ax, ay = at or (W / 2, H / 2)
        s = max(W / A["ow"], H / A["oh"]) * zoom
        left = min(0, max(W - A["ow"] * s, ax - fx * s))
        top = min(0, max(H - A["oh"] * s, ay - fy * s))
        # focus may shift after clamping: compute where it actually sits (camera origin)
        ox, oy = left + fx * s, top + fy * s
        pmax = max(max(push) if isinstance(push, tuple) else (push or 1), 1)
        up = s * pmax * A["ow"] / A["fw"]
        if up > MAX_UPSCALE + 1e-6:
            self.warn.append(f"{key}: upscale {up:.2f}x > {MAX_UPSCALE}x")
        id = id or self.uid("p")
        geo = f'position:absolute;left:{left:.1f}px;top:{top:.1f}px;width:{A["ow"]*s:.1f}px;height:{A["oh"]*s:.1f}px;{filt}'
        if A.get("kind") == "video":
            vs = self.t(start if start is not None else self.t0)
            ve = self.t(end if end is not None else self.t1)
            media = (f'<video id="{id or "v"}_v{self.n}" class="clip" src="assets/vid/{key}.mp4" muted playsinline preload="auto" '
                     f'data-start="{max(0,vs)}" data-duration="{round(ve-max(0,vs),4)}" data-media-start="{offset}" style="{geo}"></video>')
        else:
            media = f'<img src="assets/img/{key}.jpg" style="{geo}">'
        img = (f'<div class="cam" id="{id}c" style="position:absolute;left:0;top:0;width:{W}px;height:{H}px;'
               f'transform-origin:{ox:.1f}px {oy:.1f}px">{media}</div>')
        extra = ""
        if dof:
            extra += self.dof_html(*dof, W=W, H=H, at=(ox, oy))
        if vign:
            extra += self.vign_html(vign)
        wrap = (f'position:absolute;left:{X}px;top:{Y}px;width:{W}px;height:{H}px;overflow:hidden;'
                if frame else "")
        lid = self.box(img + extra, start, end, z, style=wrap, id=id)
        s0, e0 = self.t(start if start is not None else self.t0), self.t(end if end is not None else self.t1)
        if isinstance(push, tuple):   # (from, to) camera scale
            self.tl(f'tl.fromTo("#{id}c",{{scale:{push[0]}}},{{scale:{push[1]},duration:{e0-max(0,s0)},ease:"{ease}"}},{max(0,s0)});')
        elif push and push != 1:
            self.tl(f'tl.fromTo("#{id}c",{{scale:1}},{{scale:{push},duration:{e0-max(0,s0)},ease:"{ease}"}},{max(0,s0)});')
        if shake:
            self.tl(f'shake("#{id}c",{max(0,s0)},{e0},{shake});')
        return id

    def crop(self, key, cx, cy, ch, W, H, id="", extra=""):
        """<img> showing a region of `key` centred on (cx,cy) (original px), `ch` original px
        tall, inside a W x H box. Returns (html, scale, (left, top))."""
        A = self.film.assets.items[key]
        s = H / ch
        if A["ow"] * s < W:
            s = W / A["ow"]
        left = min(0, max(W - A["ow"] * s, W / 2 - cx * s))
        top = min(0, max(H - A["oh"] * s, H / 2 - cy * s))
        if self.film.assets.up(key, s) > MAX_UPSCALE + 1e-6:
            self.warn.append(f"{key}: crop upscale {self.film.assets.up(key, s):.2f}x")
        idattr = f' id="{id}"' if id else ""
        return (f'<img{idattr} src="assets/img/{key}.jpg" style="position:absolute;left:{left:.1f}px;top:{top:.1f}px;'
                f'width:{A["ow"]*s:.1f}px;height:{A["oh"]*s:.1f}px;{extra}">', s, (left, top))

    def dof_html(self, blur=10, r0=0.28, r1=0.62, W=None, H=None, at=None):
        L = self.L
        W, H = W or L.W, H or L.H
        x, y = at or (W / 2, H / 2)
        m = f"radial-gradient(circle at {x:.0f}px {y:.0f}px, transparent {r0*max(W,H):.0f}px, black {r1*max(W,H):.0f}px)"
        return (f'<div style="position:absolute;inset:0;backdrop-filter:blur({blur}px);'
                f'-webkit-backdrop-filter:blur({blur}px);mask-image:{m};-webkit-mask-image:{m}"></div>')

    def vign_html(self, a=0.55):
        return (f'<div style="position:absolute;inset:0;background:radial-gradient(ellipse at 50% 50%,'
                f'rgba(0,0,0,0) 45%, rgba(0,0,0,{a}) 100%)"></div>')

    def flat(self, color, start, end, z=50):
        """Flat full-frame colour (LESSONS: max 3 frames)."""
        if end - start > 3 / FPS + 1e-6:
            self.warn.append(f"flat {color} lasts {(end-start)*FPS:.0f} frames (>3)")
        return self.box("", start, end, z, style=f"background:{color}")

    def words(self, words, times, end, x, y, cls, align="center", z=40, gap="0.22em",
              enter="cut", color=None, id=None, accent="#E01010"):
        """One line of words, each appearing at its own film time (on the beat).
        enter: cut (hard) | slam (scale 1.12->1 in 3 frames) | blur | grey |
        flicker (letters strike on like a failing tube, deterministic) |
        impact (hard slam 1.3->1 with an `accent` offset shadow snapping home, no blur)."""
        id = id or self.uid("w")
        tr = {"center": "translate(-50%,-50%)", "left": "translate(0,-50%)", "right": "translate(-100%,-50%)"}[align]
        def inner(i, w):
            if enter != "flicker":
                return w
            return "".join(f'<span id="{id}_{i}_{j}" style="opacity:0">{ch}</span>' for j, ch in enumerate(w))
        spans = "".join(f'<span class="wd" id="{id}_{i}" style="display:inline-block;margin-right:{gap if i<len(words)-1 else 0};'
                        f'opacity:0">{inner(i, w)}</span>' for i, w in enumerate(words))
        col = f"color:{color};" if color else ""
        self.box(f'<div class="{cls}" style="position:absolute;left:{x}px;top:{y}px;transform:{tr};'
                 f'white-space:nowrap;text-align:{align};{col}">{spans}</div>', times[0], end, z, id=id)
        for i, t in enumerate(times):
            lt = self.t(t)
            sel = f"#{id}_{i}"
            if enter == "cut":
                self.tl(f'tl.set("{sel}",{{opacity:1}},{lt});')
            elif enter == "slam":
                self.tl(f'tl.set("{sel}",{{opacity:1,scale:1.12}},{lt});tl.to("{sel}",{{scale:1,duration:{3/FPS},ease:"power2.out"}},{lt});')
            elif enter == "blur":
                self.tl(f'tl.fromTo("{sel}",{{opacity:0,filter:"blur(14px)",y:8}},{{opacity:1,filter:"blur(0px)",y:0,duration:0.35,ease:"power3.out"}},{lt});')
            elif enter == "flicker":
                self.tl(f'tl.set("{sel}",{{opacity:1}},{lt});')
                for j in range(len(words[i])):
                    f0 = (j * 7 + i * 3) % 5                      # frames: on, off, on (stays)
                    for k, (df, op) in enumerate(((f0, 1), (f0 + 1, 0.15), (f0 + 3, 1))):
                        self.tl(f'tl.set("#{id}_{i}_{j}",{{opacity:{op}}},{lt + df / FPS:.4f});')
            elif enter == "impact":
                self.tl(f'tl.set("{sel}",{{opacity:1,scale:1.3,textShadow:"22px -10px 0 {accent}"}},{lt});'
                        f'tl.to("{sel}",{{scale:1,duration:{3/FPS},ease:"power3.out"}},{lt});'
                        f'tl.to("{sel}",{{textShadow:"0px 0px 0 {accent}",duration:{5/FPS},ease:"power2.out"}},{lt});')
            elif enter == "grey":
                self.tl(f'tl.set("{sel}",{{opacity:1,color:"#B5B5B5"}},{lt});tl.to("{sel}",{{color:"inherit",duration:0.25}},{lt+0.12});')
        # LESSONS: hold >= 0.5 s + 0.3 s/word (min 1.2)
        need = max(1.2, 0.5 + 0.3 * len(words))
        if end - times[0] + 1e-6 < need:
            self.warn.append(f'"{" ".join(words)}" held {end-times[0]:.2f}s < {need:.2f}s')
        return id

    def cursor(self, path, clicks=(), start=None, end=None, z=60, size=None):
        """path: [(film_t, x, y), ...]; clicks: film times. Size ~5% of frame height."""
        L = self.L
        size = size or round(0.055 * min(L.W, L.H) * (1.25 if L.vert else 1))
        id = self.uid("cur")
        svg = (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24"><path d="M3 2l17 9.5-7.2 1.6 4.3 7.7-3.1 1.7'
               f'-4.3-7.7L4.6 19z" fill="#000" stroke="#fff" stroke-width="1.4" stroke-linejoin="round"/></svg>')
        t0, x0, y0 = path[0]
        self.box(f'<div id="{id}m" style="position:absolute;left:0;top:0">'
                 f'<div id="{id}s" style="transform-origin:4px 3px">{svg}</div></div>',
                 start if start is not None else t0, end, z, id=id)
        self.tl(f'tl.set("#{id}m",{{x:{x0},y:{y0}}},0);')   # LESSONS: never mix CSS transform with GSAP x/y
        for (ta, xa, ya), (tb, xb, yb) in zip(path, path[1:]):
            self.tl(f'tl.to("#{id}m",{{x:{xb},y:{yb},duration:{round(tb-ta,4)},ease:"power2.inOut"}},{self.t(ta)});')
        for c in clicks:
            self.tl(f'tl.to("#{id}s",{{scale:0.82,duration:0.07,ease:"power2.in"}},{self.t(c)-0.07});'
                    f'tl.to("#{id}s",{{scale:1,duration:0.16,ease:"power2.out"}},{self.t(c)});')
        return id

    # ---- output ----------------------------------------------------------
    def html(self):
        L, look = self.L, self.film.look
        fonts = "".join(f'@font-face{{font-family:"{n}";src:url("assets/fonts/{f}") format("woff2");font-display:block}}'
                        for n, f in look["fonts"].items())
        js = "\n".join(self.js)
        return f"""<!doctype html><html><head><meta charset="utf-8">
<style>{fonts}
html,body{{margin:0;background:{look['ground']};}}
#{self.name}{{position:relative;width:{L.W}px;height:{L.H}px;overflow:hidden;background:{look['ground']}}}
.layer{{position:absolute;inset:0;overflow:hidden}}
.layer img{{display:block}}
{look.get('css','')}
{''.join(self.css)}
</style></head><body>
<div id="{self.name}" data-composition-id="{self.name}" data-width="{L.W}" data-height="{L.H}" data-fps="{FPS}" data-duration="{self.dur}" data-motion-blur="on">
{chr(10).join(self.els)}
</div>
<script src="kit/gsap.min.js"></script>
<script>
const tl = gsap.timeline({{paused:true}});
function shake(sel,t0,t1,a){{ // deterministic handheld: summed sines, no randomness
  const n=Math.max(2,Math.round((t1-t0)*12));
  for(let i=0;i<n;i++){{const t=t0+(t1-t0)*i/n,k=i*1.7;
    tl.to(sel,{{x:a*Math.sin(k*1.3)+a*0.5*Math.sin(k*3.1),y:a*Math.cos(k*1.1)*0.7,duration:(t1-t0)/n,ease:"sine.inOut"}},t);}}
}}
{js}
tl.set({{}},{{}},{self.dur});
window.__timelines = window.__timelines || {{}};
window.__timelines["{self.name}"] = tl;
</script></body></html>"""


class Film:
    def __init__(self, project_dir, fmt, look, assets):
        self.dir = Path(project_dir)
        self.L = Fmt(fmt)
        self.look, self.assets = look, assets
        self.chunks = []

    def chunk(self, name, t0, t1):
        c = Chunk(self, name, t0, t1)
        self.chunks.append(c)
        return c

    # ---- build -----------------------------------------------------------
    def build(self):
        out = self.dir / "build" / self.L.name
        shared = self.dir / "build" / "_assets"
        self.assets.prepare(shared / "img")
        (shared / "fonts").mkdir(parents=True, exist_ok=True)
        for f in (self.dir / "assets" / "fonts").glob("*"):
            shutil.copy2(f, shared / "fonts" / f.name)
        warn = []
        for i, c in enumerate(self.chunks):
            d = out / f"{i:02d}_{c.name}"
            d.mkdir(parents=True, exist_ok=True)
            (d / "index.html").write_text(c.html())
            for link, target in (("assets", shared), ("kit", KIT / "vendor")):
                p = d / link
                if p.is_symlink() or p.exists():
                    p.unlink() if p.is_symlink() else shutil.rmtree(p)
                p.symlink_to(target)
            warn += [f"[{c.name}] {w}" for w in c.warn]
        # check chunk continuity
        for a, b in zip(self.chunks, self.chunks[1:]):
            if abs(a.t1 - b.t0) > 1e-6:
                warn.append(f"gap/overlap between {a.name} ({a.t1}) and {b.name} ({b.t0})")
        return out, warn

    def chunk_hash(self, d):
        h = hashlib.sha1((d / "index.html").read_bytes())
        for img in sorted(list((d / "assets" / "img").glob("*.jpg")) + list((d / "assets" / "vid").glob("*.mp4"))):
            if img.stem in (d / "index.html").read_text():
                h.update(img.read_bytes()[:4096] + str(img.stat().st_size).encode())
        return h.hexdigest()[:16]

    def render(self, out, quality="delivery", only=None):
        """Render each chunk (cached by content hash), then concat with -c copy."""
        cache = self.dir / "build" / "_cache"
        cache.mkdir(parents=True, exist_ok=True)
        env = dict(os.environ, HYPERFRAMES_BROWSER_PATH="/usr/bin/google-chrome")
        parts = []
        for i, c in enumerate(self.chunks):
            d = out / f"{i:02d}_{c.name}"
            key = f"{self.L.name}_{c.name}_{self.chunk_hash(d)}_{quality}.mp4"
            dst = cache / key
            n = round(c.t1 * FPS) - round(c.t0 * FPS)      # frame-exact on the film grid (no drift)
            key = key.replace(".mp4", f"_{n}f.mp4")
            dst = cache / key
            raw = cache / f"raw_{self.L.name}_{c.name}_{self.chunk_hash(d)}_{quality}.mp4"
            if not dst.exists() and not raw.exists() and (only is None or c.name in only):
                tmp = cache / f"_tmp_{key}"
                # gate: refuse to spend a render on a chunk the runtime will reject
                g = subprocess.run(["npx", "hyperframes", "validate", str(d)], env=env, capture_output=True, text=True)
                if "Invalid HyperFrame contract" in g.stdout + g.stderr or " error(s)" in g.stdout and " 0 error(s)" not in g.stdout:
                    sys.exit(f"{c.name} fails validation:\n{(g.stdout + g.stderr)[-1500:]}")
                print(f"render {c.name} ({c.dur:.2f}s)", flush=True)
                r = subprocess.run(["npx", "hyperframes", "render", str(d), "-o", str(tmp), "-q", quality,
                                    "-f", str(FPS), "-w", "4"], env=env, capture_output=True, text=True)
                if r.returncode != 0 or not tmp.exists():
                    sys.exit(f"render failed for {c.name}:\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}")
                tmp.rename(raw)                                 # keep the raw render: re-trims never re-render
            if not dst.exists() and raw.exists():
                tmp = raw
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(tmp), "-an", "-vf", f"fps={FPS},tpad=stop=-1:stop_mode=clone",
                                "-frames:v", str(n), "-c:v", "libx264", "-crf", "16", "-preset", "veryfast",
                                "-pix_fmt", "yuv420p", "-g", str(FPS), str(cache / f"_n_{key}")], check=True)
                (cache / f"_n_{key}").rename(dst)
            elif not dst.exists():
                sys.exit(f"{c.name} not rendered (filtered by only=)")
            else:
                print(f"cached {c.name}", flush=True)
            parts.append(dst)
        lst = out / "concat.txt"
        lst.write_text("".join(f"file '{p}'\n" for p in parts))
        video = out / "video.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
                        "-c", "copy", str(video)], check=True)
        return video

    def snap(self, out, times, sheet, cols=6, thumb=320):
        """Low-res contact sheet at film times (cheap to review)."""
        from PIL import ImageDraw
        env = dict(os.environ, HYPERFRAMES_BROWSER_PATH="/usr/bin/google-chrome")
        shots = []
        by = {}
        for t in times:
            c = next(c for c in self.chunks if c.t0 <= t < c.t1 or (t == c.t1 and c is self.chunks[-1]))
            by.setdefault(c, []).append(t)
        tmpd = out / "_snaps"
        for c, ts in by.items():
            d = out / f"{self.chunks.index(c):02d}_{c.name}"
            od = tmpd / c.name
            shutil.rmtree(od, ignore_errors=True)
            at = ",".join(f"{max(0,min(c.dur-0.001, t-c.t0)):.3f}" for t in ts)
            subprocess.run(["npx", "hyperframes", "snapshot", str(d), "--at", at, "--no-end", "--keep", "-o", str(od)],
                           env=env, capture_output=True, text=True)
            for t in ts:
                lt = max(0, min(c.dur - 0.001, t - c.t0))
                cand = sorted(od.glob("at-*.png"), key=lambda p: abs(float(p.stem[3:-1]) - lt))
                if cand:
                    shots.append((t, cand[0]))
        if not shots:
            return None
        L = self.L
        tw, th = thumb, round(thumb * L.H / L.W)
        rows = math.ceil(len(shots) / cols)
        im = Image.new("RGB", (cols * tw, rows * (th + 18)), "#222")
        dr = ImageDraw.Draw(im)
        for i, (t, p) in enumerate(sorted(shots)):
            x, y = (i % cols) * tw, (i // cols) * (th + 18)
            im.paste(Image.open(p).convert("RGB").resize((tw, th)), (x, y + 18))
            dr.text((x + 4, y + 3), f"{t:.2f}", fill="#fff")
        im.save(sheet, quality=80)
        return sheet
