"""Feeling v2 — 20 s. Usage: python3 projects/feeling/film.py [16x9|9x16|4x5] [build|snap|render]"""
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))
from kit.kit import Film, Assets, FPS
from kit import mix as M

# ---------------------------------------------------------------- LOOK (Feeling only)
# The NEON ad's world: moonlit blue -> red fog -> black. No white ground of our own;
# the store is the only light, and it gets switched off. Cuts on the beat, dead stops,
# slow menacing pushes, handheld jitter, 2-frame red flashes. Black Han Sans white on black.
RED = "#EB2021"          # sampled from the NEON imagery
LOOK = dict(
    ground="#000",
    fonts={"BHS": "BlackHanSans-Regular.woff2", "Afacad": "Afacad-Regular.woff2"},
    css=f"""
.bhs{{font-family:BHS;text-transform:uppercase;letter-spacing:-0.01em;line-height:1}}
.afa{{font-family:Afacad}}
.white{{color:#fff}} .ink{{color:#000}}
""",
)

MUSIC = HERE / "audio/osaka.mp3"
DROP_SONG, DROP_FILM = 121.43, 4.70       # riser peak in OSAKA lands on the wordmark
OFFSET = DROP_SONG - DROP_FILM
BEATS = [round(b - OFFSET, 3) for b in json.load(open(HERE / "audio/osaka_beats.json"))["beatTimes"]
         if 0 <= b - OFFSET <= 21]
HB = 0.345                                 # half-beat at 87 BPM


def assets():
    A = Assets(HERE / "assets/img")
    A.add("hands", "hands_f_full.png", hand=(1391, 520), arm=(1304, 1159), low=(942, 1956), F=(1377, 1377))
    A.add("hoodback", "hoodie_back.png", print=(2046, 1304), up=(2046, 1100))
    A.add("hoodwalk", "hoodie_walk.png", max_px=4096, face=(1993, 720), chest=(2205, 1160))
    A.add("teefront", "tee_front.png", F=(1648, 1089))
    A.add("alleyback", "tee_alley_back.png", print=(1993, 1696), up=(2048, 1500))
    A.add("alleyfront", "tee_alley_front.png", max_px=5440, face=(1551, 1351), F=(1752, 2048))
    # the NEON ad (Ettore's own AI film): clips cut from it, coordinates in its 1920x1080 frame
    ad = "../video/ad.mp4"
    A.video("v_hand", ad, 13.85, 0.8, hand=(950, 470))
    A.video("v_rise", ad, 19.35, 0.6, face=(940, 380))
    A.video("v_grab", ad, 20.25, 0.6, hand=(470, 470))
    A.video("v_fog", ad, 26.2, 0.6, crawl=(840, 560))
    A.video("v_walk", ad, 32.9, 0.6, crowd=(1020, 300))
    A.video("v_face", ad, 43.2, 0.6, face=(840, 330))
    A.video("v_eyes", ad, 47.3, 0.6, eyes=(960, 330))
    A.video("v_hdr", ad, 35.3, 4.0, mid=(960, 540))
    A.video("v_cell1", ad, 47.0, 2.4, mid=(960, 400))
    A.video("v_cell2", ad, 51.6, 2.4, F=(990, 300))
    A.video("v_crowd", ad, 39.1, 3.0, lead=(1040, 440))
    A.video("v_end", ad, 62.2, 3.0, z=(1220, 380))
    A.video("v_neon", ad, 50.55, 2.3, F=(990, 300))
    return A


# ---------------------------------------------------------------- store page (real copy)
PAGE_W = 1010            # css px of the rebuilt storefront; shown at P = W / PAGE_W (1.9x at 1080p)
CARD = dict(x1=16, x2=513, y=820, s=481)


def page_html(c, P, hide_nav_mark=False, hdr=None):
    """Home page of the Feeling store, rebuilt from the real copy, at scale P.
    The real header plays the NEON ad: hdr = (film_start, film_end)."""
    hs = PAGE_W / 1920
    hdr_img = (f'<video class="clip" src="assets/vid/v_hdr.mp4" muted playsinline preload="auto" data-start="{max(0,c.t(hdr[0]))}" '
               f'data-duration="{round(hdr[1]-hdr[0],4)}" data-media-start="0" style="position:absolute;left:0;top:{(560-1080*hs)/2:.1f}px;'
               f'width:{PAGE_W}px;height:{1080*hs:.1f}px"></video>')
    card = lambda key, cx, cy, ch: c.crop(key, cx, cy, ch, CARD["s"], CARD["s"])[0]
    def card_html(x, title, img):
        return (f'<div style="position:absolute;left:{x}px;top:{CARD["y"]}px;width:{CARD["s"]}px;height:{CARD["s"]}px;overflow:hidden">{img}'
                f'<div id="ct_{title}" class="bhs white" style="position:absolute;left:24px;bottom:78px;font-size:60px;text-shadow:0 4px 6px rgba(0,0,0,.35)">{title}</div>'
                f'<div id="cb_{title}" style="position:absolute;left:24px;bottom:26px;padding:4px 24px;border:1px solid #fff;color:#fff;font:600 14px Afacad;'
                f'letter-spacing:.04em;background:rgba(255,255,255,.12);backdrop-filter:blur(16px)">ORDER NOW</div></div>')
    mark = "" if hide_nav_mark else "FEELING"
    return f'''<div style="position:absolute;left:0;top:0;width:{PAGE_W}px;height:1400px;background:#fff;transform-origin:0 0;transform:scale({P})">
 <div style="position:absolute;left:0;top:0;width:{PAGE_W}px;height:60px;display:flex;align-items:center;justify-content:center">
  <div style="position:absolute;left:20px;top:21px;width:22px">{"".join('<div style="height:2px;background:#000;margin-bottom:5px"></div>' for _ in range(3))}</div>
  <div class="bhs ink" style="font-size:32px">{mark}</div></div>
 <div style="position:absolute;left:0;top:60px;width:{PAGE_W}px;height:560px;overflow:hidden">{hdr_img}
  <div id="hn" class="bhs white" style="position:absolute;left:28px;top:24px;font-size:96px;text-shadow:0 4px 6px rgba(0,0,0,.35)">NEON</div>
  <div id="hc" class="bhs white" style="position:absolute;right:28px;bottom:24px;font-size:96px;text-shadow:0 4px 6px rgba(0,0,0,.35)">COLLECTION</div></div>
 <div style="position:absolute;left:0;top:640px;width:{PAGE_W}px;text-align:center">
  <div class="bhs ink" style="font-size:40px">BACK FROM THE DEAD, READY TO SLAY</div>
  <div class="afa" style="font-size:17px;color:#333;margin:14px auto 0;width:640px;line-height:1.35">Step into the glow of a streetwear collection like no other. AI-crafted and inspired by the allure of neon lights and the mystery of the undead.</div></div>
 {card_html(CARD["x1"], "TEE", card("alleyfront", 1640, 1900, 2350))}
 {card_html(CARD["x2"], "HOODIE", card("hoodback", 2046, 1350, 2300))}
</div>'''


def build(fmt):
    A = assets()
    F = Film(HERE, fmt, LOOK, A)
    L = F.L
    W, H, u = L.W, L.H, L.u
    A.prepare(HERE / "build/_assets/img")
    sfx = []
    MONT = dict(dof=(8, 0.24, 0.62), vign=0.65, shake=5 * u, ease="power1.out", filt="filter:contrast(1.12)")

    # ============ C1 0–2.605  the ad's resurrection, cut on half-beats: blue soil -> red fog -> eyes
    t_freeze = 2.605
    c = F.chunk("montage", 0, t_freeze)
    cuts = [0, 0.535, 0.88, 1.225, 1.57, 1.915, 2.26, t_freeze]
    shots = [("v_hand", "hand", 1.15, 1.10), ("v_rise", "face", 1.45, 1.08), ("v_grab", "hand", 1.55, 1.08),
             ("v_fog", "crawl", 1.25, 1.08), ("v_walk", "crowd", 1.3, 1.08), ("v_face", "face", 1.4, 1.08),
             ("v_eyes", "eyes", 1.6, 1.10)]
    for (key, foc, z, push), s0, s1 in zip(shots, cuts, cuts[1:]):
        c.photo(key, foc, zoom=z, push=push, start=s0, end=s1, **MONT)
    for t in (1.225, 1.915):                         # 2-frame red flash where blue turns red, and on the faces
        c.flat(RED, t, t + 2 / FPS, z=30)
    sfx += [("heart", 0.0, 0.9), ("heart", 1.225, 0.8), ("heart", 1.915, 0.9)]

    # ============ C2 2.605–4.70  hard stop: the ad's own cut, eyes -> the neon F over the crowd (live, slow push).
    # Music cut. Type stacked low: BACK FROM THE strikes on like a failing tube, DEAD. hits hard on the beat
    # with a red offset snapping home and a camera jolt. Then the world rushes through the F behind the type.
    c = F.chunk("stop", t_freeze, DROP_FILM)
    t_zoom, t_dead = 4.36, 3.305
    c.photo("v_neon", "F", zoom=1.0, push=1.06, start=t_freeze, end=DROP_FILM, ease="sine.inOut",
            vign=0.8, filt="filter:brightness(.62) contrast(1.1)", id="fld")
    lt = c.t(t_zoom)
    c.tl(f'tl.to("#fldc",{{scale:9,duration:{DROP_FILM-t_zoom},ease:"power3.in"}},{lt});')
    ld = c.t(t_dead)                                    # impact jolt on DEAD.
    for k, (dx, dy) in enumerate(((14, -9), (-10, 7), (6, -4), (0, 0))):
        c.tl(f'tl.set("#fld",{{x:{dx*u:.1f},y:{dy*u:.1f}}},{ld + k / FPS:.4f});')
    fsA, fsB = round(L.pick(72, 66) * u), round(L.pick(330, 250) * u)
    yA = L.pick(0.60 * H, 0.58 * H)
    yB = yA + fsA * 0.55 + fsB * 0.5
    c.words(["BACK", "FROM", "THE"], [2.75, 2.92, 3.09], t_zoom + 0.22, W / 2, yA, "bhs white", enter="flicker",
            gap="0.5em", id="hkA")
    c.words(["DEAD."], [t_dead], t_zoom + 0.22, W / 2, yB, "bhs white", enter="impact", accent=RED, id="hkB")
    c.style(f"#hkA .bhs{{font-size:{fsA}px;letter-spacing:.32em}} #hkB .bhs{{font-size:{fsB}px;letter-spacing:-.01em}}")
    # the type is pulled into the F with the world in the last frames (parallax: it trails the background)
    c.tl(f'tl.to("#hkA,#hkB",{{scale:1.8,opacity:0,transformOrigin:"50% 28%",duration:0.22,ease:"power3.in"}},{lt + 0.06});')
    c.flat(RED, DROP_FILM - 2 / FPS, DROP_FILM, z=45)
    sfx += [("thud", t_freeze, 0.9), ("tick", 2.75, 0.5), ("tick", 2.92, 0.5), ("tick", 3.09, 0.5),
            ("hit", t_dead, 1.0), ("whoosh", t_zoom - 0.05, 0.8)]

    # ============ C3 4.70–6.055  drop: the ad's own lockup, white on black, red fog breathing behind
    t_store = 6.055
    c = F.chunk("reveal", DROP_FILM, t_store)
    c.photo("v_end", "z", zoom=1.0, push=1.05, start=DROP_FILM, end=t_store, filt="filter:brightness(.32)", vign=0.85, id="fog")
    big = round(L.pick(280, 220) * u)
    c.words(["FEELING"], [DROP_FILM], t_store, W / 2, H / 2 - 0.06 * H, "bhs white", enter="slam", id="wm")
    c.words(["NEON", "COLLECTION"], [5.365, 5.365], t_store, W / 2, H / 2 + big * 0.55, "bhs", enter="cut", id="nc",
            color="#BFBFBF")
    c.style(f"#wm .bhs{{font-size:{big}px}} #nc .bhs{{font-size:{round(big*0.32)}px;letter-spacing:.06em}}")
    c.warn = [w for w in c.warn if "NEON COLLECTION" not in w]   # second line of the lockup, read with FEELING
    sfx += [("hit", 5.365, 0.4)]

    # ============ C4 6.055–9.445  the store: we're inside its header (the ad plays there), pull back, scroll, ORDER NOW
    P = W / PAGE_W
    c = F.chunk("store", t_store, 9.445)
    t_scroll, t_click, t_end = 7.0, 8.815, 9.445
    S1 = 800
    hy = (60 + 280) * P                                # header centre in frame
    c.box(f'<div id="pgw" style="position:absolute;inset:0">{page_html(c, P, hdr=(t_store, t_end))}</div>',
          t_store, t_end, z=1, id="pg", style="background:#000")
    c.tl(f'tl.fromTo("#pgw",{{scale:1.5,transformOrigin:"{W/2}px {hy:.0f}px"}},{{scale:1,duration:0.8,ease:"power3.inOut"}},0.05);')
    c.tl(f'tl.to("#pgw",{{y:{-S1*P},duration:0.75,ease:"power3.inOut"}},{c.t(t_scroll)});')
    # header labels cut in on the beat once the camera is out (never cropped mid-word)
    c.tl(f'tl.set("#hn,#hc",{{opacity:0}},0);tl.set("#hn",{{opacity:1}},{c.t(6.745)});tl.set("#hc",{{opacity:1}},{c.t(6.745)+HB/2});')
    cx, cy, cs = CARD["x1"] * P, (CARD["y"] - S1) * P, CARD["s"] * P
    btn = (cx + 24 * P + 75 * P, cy + (CARD["s"] - 26 - 18) * P)
    c.cursor([(7.75, W * 0.78, H * 0.92), (8.62, btn[0], btn[1]), (9.0, btn[0] + 6, btn[1] + 4)],
             clicks=[t_click], start=7.75, end=t_click + 0.18)
    # card -> world: ONE camera move. The page flies into the TEE card until its chest F sits centred at
    # MATCH_F_H, the size and place the product shot opens on (C5). Labels on the card get out of the way first.
    sc = CARD["s"] / 2350                                   # card crop scale (css px per original px)
    A_ = A.items["alleyfront"]
    l0c = min(0, max(CARD["s"] - A_["ow"] * sc, CARD["s"] / 2 - 1640 * sc))
    t0c = min(0, max(CARD["s"] - A_["oh"] * sc, CARD["s"] / 2 - 1900 * sc))
    FxP, FyP = (CARD["x1"] + l0c + 1752 * sc) * P, (CARD["y"] + t0c + 2048 * sc) * P   # F in page coords (pgw space)
    k = MATCH_F_H * u / (148 * sc * P)
    if A.up("alleyfront", sc * P * k) > 2.0:
        c.warn.append(f"alleyfront at match {A.up('alleyfront', sc*P*k):.2f}x")
    lz = c.t(t_click + 0.05)
    c.tl(f'tl.to("#ct_TEE,#cb_TEE,#ct_HOODIE,#cb_HOODIE",{{opacity:0,duration:0.12,ease:"power2.out"}},{lz});')
    c.tl(f'tl.set("#pgw",{{transformOrigin:"0px 0px"}},{lz});')
    c.tl(f'tl.to("#pgw",{{x:{W/2 - FxP*k:.1f},y:{H/2 - FyP*k:.1f},scale:{k:.4f},duration:{t_end - t_click - 0.05:.3f},ease:"power3.inOut"}},{lz});')
    sfx += [("whoosh", t_store + 0.05, 0.35), ("whoosh", t_scroll, 0.3), ("click", t_click, 0.9), ("whoosh", t_click + 0.1, 0.45)]

    # ============ C5 9.445–12.605  product page: match cut F->F, pick M, Checkout; the page dies to black: AI-CRAFTED.
    c = F.chunk("product", 9.445, 12.605)
    TF = A.items["teefront"]
    pw = L.pick(0.52 * W, W); ph = L.pick(H, 0.50 * H)
    si = min(pw / TF["ow"], ph / TF["oh"]) * 1.08
    ix, iy = pw / 2 - TF["ow"] * si / 2, ph / 2 - TF["oh"] * si / 2 + L.pick(0, 0.04 * H)
    Fx, Fy = ix + 1648 * si, iy + 1089 * si
    zs = (MATCH_F_H * u / 300) / si
    ux, uy = L.pick(0.60 * W, 0.08 * W), L.pick(0.20 * H, 0.55 * H)
    sz = round(84 * u)
    sizes = "".join(f'<div id="sz{s}" style="width:{sz}px;height:{sz}px;border:2px solid #000;display:flex;align-items:center;justify-content:center;'
                    f'font:400 {round(30*u)}px Afacad;margin-right:{round(14*u)}px">{s}</div>' for s in ("S", "M", "L", "XL"))
    info = f'''<div style="position:absolute;left:{ux}px;top:{uy}px;color:#000">
  <div class="afa" style="font-size:{round(70*u)}px;line-height:1">Neon Tee</div>
  <div class="afa" style="font-size:{round(40*u)}px;margin-top:{round(14*u)}px">29,99 €</div>
  <div style="display:flex;margin-top:{round(40*u)}px">{sizes}</div>
  <div class="afa" style="display:flex;gap:{round(34*u)}px;font-size:{round(34*u)}px;margin-top:{round(30*u)}px"><span>−</span><span>1</span><span>+</span></div>
  <div id="ck" style="width:{round(620*u)}px;height:{round(88*u)}px;background:#000;color:#fff;display:flex;align-items:center;justify-content:center;font:400 {round(32*u)}px Afacad;margin-top:{round(30*u)}px">Checkout</div>
  <div class="afa" style="font-size:{round(26*u)}px;color:#64748B;margin-top:{round(18*u)}px;text-decoration:underline">Contact support</div></div>'''
    c.box(f'''<div id="pp" style="position:absolute;left:0;top:0;width:{W}px;height:{H}px;background:#fff;transform-origin:0 0">
  <img src="assets/img/teefront.jpg" style="position:absolute;left:{ix:.1f}px;top:{iy:.1f}px;width:{TF["ow"]*si:.1f}px;height:{TF["oh"]*si:.1f}px">
  {info}</div>''', 9.445, 12.605, z=1, id="ppL", style="background:#000")
    c.tl(f'tl.fromTo("#pp",{{x:{W/2 - Fx*zs:.1f},y:{H/2 - Fy*zs:.1f},scale:{zs:.4f}}},{{x:0,y:0,scale:1,duration:0.9,ease:"power3.inOut"}},0.07);')
    # the worn tee (last frame of C4, identical framing) dissolves into the product shot over 4 frames
    sF = MATCH_F_H * u / 148
    AF = A.items["alleyfront"]
    c.box(f'<img src="assets/img/alleyfront.jpg" style="position:absolute;left:{W/2-1752*sF:.1f}px;top:{H/2-2048*sF:.1f}px;'
          f'width:{AF["ow"]*sF:.1f}px;height:{AF["oh"]*sF:.1f}px">', 9.445, 9.445 + 5 / FPS, z=30, id="worn")
    c.tl(f'tl.fromTo("#worn",{{opacity:1}},{{opacity:0,duration:{4/FPS:.4f},ease:"none"}},0);')
    mx = ux + sz + round(14 * u) + sz / 2; my = uy + round(70*u) + round(14*u) + round(40*u)*1.25 + round(40*u) + sz / 2
    ckx = ux + 310 * u; cky = my + sz / 2 + round(30*u) + round(34*u)*1.3 + round(30*u) + 44 * u
    t_m, t_ck, t_ai = 10.535, 11.225, 11.26
    c.cursor([(9.9, W * 0.92, H * 0.95), (10.48, mx, my), (10.70, mx, my), (11.17, ckx, cky), (11.4, ckx + 4, cky + 3)],
             clicks=[t_m, t_ck], start=9.9, end=t_ai + 0.05)
    c.tl(f'tl.set("#szM",{{background:"#000",color:"#fff"}},{c.t(t_m)});')
    c.tl(f'tl.set("#ck",{{background:"#333"}},{c.t(t_ck)});tl.set("#ck",{{background:"#000"}},{c.t(t_ck)+0.1});')
    # lights out: the page drops to near-black (the ad's world takes it back)
    c.tl(f'tl.to("#pp",{{opacity:0.10,filter:"blur(14px)",duration:0.14,ease:"power2.out"}},{c.t(t_ai)});')
    c.tl(f'tl.to("#pp",{{scale:1.03,duration:{12.605-t_ai},ease:"none",transformOrigin:"50% 50%"}},{c.t(t_ai)});')
    c.words(["AI-CRAFTED."], [t_ai + 1 / FPS], 12.605, W / 2, H / 2, "bhs white", enter="slam", id="ai")
    c.style(f"#ai .bhs{{font-size:{round(L.pick(210, 150)*u)}px}}")
    sfx += [("click", t_m, 0.8), ("click", t_ck, 0.9), ("thud", t_ai, 0.8)]

    # ============ C6 12.605–14.675  slot reel on black: models and ad frames, lands on the skull hoodie
    c = F.chunk("models", 12.605, 14.675)
    ww, wh = L.pick(0.37 * W, 0.62 * W), L.pick(0.80 * H, 0.42 * H)
    wx, wy = L.pick(0.57 * W, (W - 0.62 * W) / 2), L.pick(0.10 * H, 0.16 * H)
    reel = [("alleyback", 2048, 1700, 2400), ("v_cell1", 960, 420, 760), ("hoodback", 2046, 1300, 2300),
            ("v_cell2", 990, 520, 900), ("alleyfront", 1600, 1700, 2500), ("hoodwalk", 2050, 1150, 2200)]
    cells = ""
    for i, (k, x, y, h) in enumerate(reel):
        if A.items[k].get("kind") == "video":
            V = A.items[k]; sv = max(wh / h, ww / V["ow"])
            lv = min(0, max(ww - V["ow"] * sv, ww / 2 - x * sv)); tv = min(0, max(wh - V["oh"] * sv, wh / 2 - y * sv))
            html = (f'<video class="clip" src="assets/vid/{k}.mp4" muted playsinline preload="auto" data-start="0" '
                    f'data-duration="{c.dur}" data-media-start="0" style="position:absolute;left:{lv:.1f}px;top:{tv:.1f}px;'
                    f'width:{V["ow"]*sv:.1f}px;height:{V["oh"]*sv:.1f}px"></video>')
        else:
            html = c.crop(k, x, y, h, ww, wh)[0]
        cells += f'<div style="position:absolute;left:0;top:{i*wh}px;width:{ww}px;height:{wh}px;overflow:hidden">{html}</div>'
    c.box(f'<div style="position:absolute;left:{wx}px;top:{wy}px;width:{ww}px;height:{wh}px;overflow:hidden;background:#000">'
          f'<div id="strip" style="position:absolute;left:0;top:0;width:{ww}px;height:{len(reel)*wh}px">{cells}</div></div>',
          12.605, 14.675, z=2, id="slot")
    land = 13.985
    c.tl(f'tl.fromTo("#strip",{{y:0}},{{y:{-(len(reel)-1)*wh},duration:{land-12.605},ease:"power3.out"}},0);')
    c.tl(f'tl.fromTo("#slot",{{scale:1}},{{scale:1.035,duration:{14.675-12.605},ease:"none"}},0);')
    tx, ty1, ty2 = L.pick(0.08 * W, W / 2), L.pick(0.40 * H, 0.66 * H), L.pick(0.58 * H, 0.75 * H)
    al = L.pick("left", "center")
    fs6 = round(L.pick(112, 110) * u)
    c.words(["EVERY", "MODEL."], [12.75, 12.75], 14.675, tx, ty1, "bhs white", align=al, id="m1")
    c.words(["EVERY", "AD."], [13.295, 13.295], 14.675, tx, ty2, "bhs white", align=al, id="m2")
    c.style(f"#m1 .bhs,#m2 .bhs{{font-size:{fs6}px}}")
    for k in range(1, len(reel)):
        frac = 1 - (1 - k / (len(reel) - 1)) ** (1 / 3)
        sfx.append(("tick", 12.605 + frac * (land - 12.605), 0.5 if k < len(reel) - 1 else 0.9))

    # ============ C7 14.675–17.425  payoff: the ad's crowd walks at us; READY TO SLAY. hard-cut per word
    c = F.chunk("payoff", 14.675, 17.425)
    c.photo("v_crowd", "lead", zoom=1.0, push=1.06, start=14.675, end=17.425,
            filt="filter:brightness(.42)", vign=0.8, id="cr")
    c.tl(f'tl.to("#crc video",{{filter:"brightness(.75)",duration:0.08}},{c.t(15.365)});')
    fs7 = round(L.pick(190, 200) * u)
    if L.vert:
        for i, (wd, t) in enumerate((("READY", 14.675), ("TO", 15.02), ("SLAY.", 15.365))):
            c.words([wd], [t], 17.425, W / 2, H * (0.36 + 0.14 * i), "bhs white", enter="cut", id=f"p{i}")
        c.style(f"#p0 .bhs,#p1 .bhs,#p2 .bhs{{font-size:{fs7}px}}")
    else:
        c.words(["READY", "TO", "SLAY."], [14.675, 15.02, 15.365], 17.425, W / 2, H / 2, "bhs white", enter="cut", id="pay")
        c.style(f"#pay .bhs{{font-size:{fs7}px}}")
    sfx += [("hit", 14.675, 0.5), ("hit", 15.02, 0.45), ("hit", 15.365, 0.75)]

    # ============ C8 17.425–20.0  end card on black, like the ad's: wordmark, one line, signature
    c = F.chunk("end", 17.425, 20.0)
    c.photo("v_end", "z", zoom=1.0, push=1.04, start=17.425, end=20.0, filt="filter:brightness(.22)", vign=0.9, id="ef")
    ey = L.pick(0.44 * H, 0.42 * H)
    c.words(["FEELING"], [17.425], 20.0, W / 2, ey, "bhs white", enter="slam", id="ew")
    c.words(["An", "AI-driven", "streetwear", "brand."], [17.82] * 4, 20.0, W / 2, ey + 150 * u, "afa", gap="0.25em",
            color="#BFBFBF", id="el")
    c.words(["Made", "by", "Ettore"], [18.05] * 3, 20.0, W / 2, L.pick(0.90, 0.80) * H, "afa", gap="0.25em",
            color="#8A8A8A", id="es")
    c.style(f"#ew .bhs{{font-size:{round(190*u)}px}} #el .afa{{font-size:{round(44*u)}px}} #es .afa{{font-size:{round(28*u)}px}}")
    sfx += [("thud", 17.425, 0.6)]

    return F, sfx


MATCH_F_H = 230   # px (at 1080) height of the chest F at the C4->C5 match cut


def audio(F, sfx, out):
    wav = F.dir / "build" / F.L.name / "mix.wav"
    M.mix(MUSIC, OFFSET, 20.0, wav, mutes=[(2.605, 4.30)], fade_out=(18.6, 20.0), events=sfx,
          music_gain=1.0, sfx_gain=0.32)
    subprocess_mux(F.dir / "build" / F.L.name / "video.mp4", wav, out)
    return wav


def subprocess_mux(video, wav, out):
    import subprocess
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-i", str(wav), "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart", str(out)], check=True)


if __name__ == "__main__":
    fmt = sys.argv[1] if len(sys.argv) > 1 else "16x9"
    act = sys.argv[2] if len(sys.argv) > 2 else "build"
    F, sfx = build(fmt)
    out, warn = F.build()
    print("\n".join(warn) or "no warnings")
    if act == "snap":
        ts = [float(x) for x in sys.argv[3].split(",")]
        print(F.snap(out, ts, out / f"sheet_{sys.argv[4] if len(sys.argv)>4 else 'x'}.jpg"))
    elif act == "render":
        F.render(out)
        final = HERE / "out" / f"feeling_{fmt}_20s_v2.mp4"
        final.parent.mkdir(exist_ok=True)
        audio(F, sfx, final)
        print(final)
