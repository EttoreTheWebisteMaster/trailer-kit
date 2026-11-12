"""Feeling v1 — 20 s. Usage: python3 projects/feeling/film.py [16x9|9x16|4x5] [build|snap|render]"""
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))
from kit.kit import Film, Assets, FPS
from kit import mix as M

# ---------------------------------------------------------------- LOOK (Feeling only)
# Night, neon, hard. Cuts on the beat, dead stops, slow menacing pushes, handheld jitter in
# the dark world; square, flat, black-on-white in the store. No springs, no soft fades.
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
    A.add("handscut", "hands_f_cut.png", F=(1782, 1782))
    A.add("field", "field_f.png", F=(1445, 720), core=(1372, 760), crowd=(1139, 980))
    A.add("grave", "graveyard_f.png", F=(705, 230), mid=(680, 470), left=(205, 330))
    A.add("hoodback", "hoodie_back.png", print=(2046, 1304), up=(2046, 1100))
    A.add("hoodwalk", "hoodie_walk.png", max_px=4096, face=(1993, 720), chest=(2205, 1160))
    A.add("teeback", "tee_back.png", print=(1297, 1290))
    A.add("teefront", "tee_front.png", F=(1648, 1089))
    A.add("alleyback", "tee_alley_back.png", print=(1993, 1696), up=(2048, 1500))
    A.add("alleyfront", "tee_alley_front.png", max_px=5440, face=(1551, 1351), F=(1752, 2048))
    return A


# ---------------------------------------------------------------- store page (real copy)
PAGE_W = 1010            # css px of the rebuilt storefront; shown at P = W / PAGE_W (1.9x at 1080p)
CARD = dict(x1=16, x2=513, y=820, s=481)


def page_html(c, P, hide_nav_mark=False):
    """Home page of the Feeling store, rebuilt from the real copy. Rendered at scale P."""
    hdr_img, _, _ = c.crop("field", 1445, 760, 1300, PAGE_W, 560)
    card = lambda key, cx, cy, ch: c.crop(key, cx, cy, ch, CARD["s"], CARD["s"])[0]
    def card_html(x, title, img):
        return (f'<div style="position:absolute;left:{x}px;top:{CARD["y"]}px;width:{CARD["s"]}px;height:{CARD["s"]}px;overflow:hidden">{img}'
                f'<div class="bhs white" style="position:absolute;left:24px;bottom:78px;font-size:60px;text-shadow:0 4px 6px rgba(0,0,0,.35)">{title}</div>'
                f'<div style="position:absolute;left:24px;bottom:26px;padding:4px 24px;border:1px solid #fff;color:#fff;font:600 14px Afacad;'
                f'letter-spacing:.04em;background:rgba(255,255,255,.12);backdrop-filter:blur(16px)">ORDER NOW</div></div>')
    mark = "" if hide_nav_mark else "FEELING"
    return f'''<div style="position:absolute;left:0;top:0;width:{PAGE_W}px;height:1400px;background:#fff;transform-origin:0 0;transform:scale({P})">
 <div style="position:absolute;left:0;top:0;width:{PAGE_W}px;height:60px;display:flex;align-items:center;justify-content:center">
  <div style="position:absolute;left:20px;top:21px;width:22px">{"".join('<div style="height:2px;background:#000;margin-bottom:5px"></div>' for _ in range(3))}</div>
  <div class="bhs ink" style="font-size:32px">{mark}</div></div>
 <div style="position:absolute;left:0;top:60px;width:{PAGE_W}px;height:560px;overflow:hidden">{hdr_img}
  <div class="bhs white" style="position:absolute;left:28px;top:24px;font-size:96px;text-shadow:0 4px 6px rgba(0,0,0,.35)">NEON</div>
  <div class="bhs white" style="position:absolute;right:28px;bottom:24px;font-size:96px;text-shadow:0 4px 6px rgba(0,0,0,.35)">COLLECTION</div></div>
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
    b = BEATS

    # ============ C1 0–2.605  problem montage: the dead brand, no text, handheld, cuts on half-beats
    t_freeze = 2.605
    c = F.chunk("montage", 0, t_freeze)
    cuts = [0, 0.535, 0.88, 1.225, 1.57, 1.915, 2.26, t_freeze]
    shots = [("hands", "hand", 1.55, 1.10), ("grave", "mid", 1.0, 1.06), ("alleyfront", "face", 2.9, 1.08),
             ("hands", "low", 2.0, 1.10), ("field", "crowd", 1.25, 1.07), ("hoodwalk", "face", 2.7, 1.08),
             ("hoodback", "print", 2.2, 1.08)]
    for (key, foc, z, push), s0, s1 in zip(shots, cuts, cuts[1:]):
        c.photo(key, foc, zoom=z, push=push, start=s0, end=s1, ease="power1.out",
                dof=(9, 0.22, 0.6), vign=0.6, shake=6 * u, filt="filter:contrast(1.08) saturate(1.05)")
    for t in (1.225, 1.915):                         # 2-frame red flash on the downbeats
        c.flat(RED, t, t + 2 / FPS, z=30)
    sfx += [("heart", 0.0, 0.9), ("heart", 1.225, 0.8), ("heart", 1.915, 0.9)]

    # ============ C2 2.605–4.70  hard stop: still graveyard field, music cut, slow push, hook line; zoom through the F
    c = F.chunk("stop", t_freeze, DROP_FILM)
    t_zoom = 4.40
    pid = c.photo("field", "F", zoom=1.0, push=1.05, start=t_freeze, end=DROP_FILM, ease="sine.inOut",
                  vign=0.7, filt="filter:brightness(.62) saturate(.9)", id="fld")
    # zoom through the F's white-hot core (motion blur hides the upscale; it ends on 2 white frames)
    lt = c.t(t_zoom)
    c.tl(f'tl.to("#fldc",{{scale:9,duration:{DROP_FILM-t_zoom},ease:"power3.in"}},{lt});')
    c.tl(f'tl.to("#fldc img",{{filter:"brightness(3.2) saturate(.3)",duration:{DROP_FILM-t_zoom},ease:"power1.in"}},{lt});')
    c.flat("#fff", DROP_FILM - 2 / FPS, DROP_FILM, z=45)
    fs = round(L.pick(118, 112) * u)
    c.words(["BACK", "FROM", "THE", "DEAD."], [2.75, 3.0, 3.305, 3.65], t_zoom + 0.05,
            W / 2, L.pick(0.84 * H, 0.72 * H), "bhs white", enter="slam", z=40,
            id="hook")
    c.style(f"#hook .bhs{{font-size:{fs}px}}")
    sfx += [("thud", t_freeze, 1.0), ("whoosh", t_zoom - 0.05, 0.8)]

    # ============ C3 4.70–6.40  drop: FEELING slams on white, then carries into the store nav
    P = W / PAGE_W if not L.vert else W / PAGE_W
    c = F.chunk("reveal", DROP_FILM, 6.40)
    c.box(page_html(c, P, hide_nav_mark=True), DROP_FILM, 6.40, z=1, id="pg",
          style="background:#fff")
    big = round(L.pick(300, 230) * u)
    nav_fs = 32 * P
    c.box(f'<div id="wmo" style="position:absolute;left:{W/2}px;top:{H/2}px;width:0;height:0">'
          f'<div id="wm" class="bhs ink" style="position:absolute;left:0;top:0;font-size:{big}px;white-space:nowrap">FEELING</div></div>',
          DROP_FILM, 6.40, z=10, id="wmL")
    c.tl('tl.set("#wm",{xPercent:-50,yPercent:-50},0);')
    # page hidden under a white sheet until the carry, then the sheet lifts away (page rises in)
    c.box("", DROP_FILM, 6.40, z=5, id="sheet", style="background:#fff")
    t_carry = 5.365
    lc = c.t(t_carry)
    c.tl(f'tl.fromTo("#wmo",{{scale:1.10}},{{scale:1,duration:{3/FPS},ease:"power2.out"}},0);')
    c.tl(f'tl.to("#wmo",{{y:{30*P - H/2:.1f},scale:{nav_fs/big:.4f},duration:0.75,ease:"power3.inOut"}},{lc});')
    c.tl(f'tl.fromTo("#sheet",{{y:0}},{{y:{-H},duration:0.75,ease:"power3.inOut"}},{lc+0.06});')
    c.tl(f'tl.fromTo("#pg > div",{{y:{0.25*H}}},{{y:0,duration:0.8,ease:"power3.out"}},{lc+0.06});')
    sfx += [("whoosh", t_carry, 0.35)]

    # ============ C4 6.40–9.70  store home: header, scroll to the cards, click ORDER NOW on TEE; the tee becomes the world
    c = F.chunk("store", 6.40, 9.70)
    t_scroll, t_click, t_end = 7.10, b[11] - 0.0 if len(b) > 11 else 8.815, 9.70
    t_click = 8.815
    S1 = 800                                           # css scroll for the cards
    c.box(f'<div id="pgw">{page_html(c, P)}</div>', 6.40, t_end, z=1, id="pg", style="background:#fff")
    c.tl(f'tl.to("#pgw",{{y:{-S1*P},duration:0.75,ease:"power3.inOut"}},{c.t(t_scroll)});')
    # slow push on the header image while held
    c.tl(f'tl.fromTo("#pgw img",{{scale:1}},{{scale:1.04,duration:0.7,ease:"none",transformOrigin:"50% 50%"}},0);')
    # card -> world: a copy of the TEE card image grows to full frame, centred on the chest F
    cx, cy, cs = CARD["x1"] * P, (CARD["y"] - S1) * P, CARD["s"] * P
    btn = (cx + 24 * P + 75 * P, cy + (CARD["s"] - 26 - 18) * P)
    c.cursor([(7.75, W * 0.78, H * 0.92), (8.62, btn[0], btn[1]), (9.0, btn[0] + 6, btn[1] + 4)],
             clicks=[t_click], start=7.75, end=t_click + 0.18)
    A_ = A.items["alleyfront"]
    s0 = cs / 2350                                       # card crop scale (orig px)
    l0 = min(0, max(cs - A_["ow"] * s0, cs / 2 - 1640 * s0)); t0 = min(0, max(cs - A_["oh"] * s0, cs / 2 - 1900 * s0))
    sF = MATCH_F_H * u / 148                             # final: chest F MATCH_F_H tall at frame centre
    l1, t1 = W / 2 - 1752 * sF, H / 2 - 2048 * sF
    def inset(x, y, w, h):
        return f"inset({y:.1f}px {W-x-w:.1f}px {H-y-h:.1f}px {x:.1f}px)"
    c.box(f'<div id="xw" style="position:absolute;inset:0;overflow:hidden">'
          f'<img id="xi" src="assets/img/alleyfront.jpg" style="position:absolute;left:0;top:0;width:{A_["ow"]*s0:.1f}px;'
          f'height:{A_["oh"]*s0:.1f}px;transform-origin:0 0"></div>', t_click + 0.03, t_end, z=20, id="xL")
    lx, dur = c.t(t_click + 0.03), t_end - t_click - 0.03
    c.tl(f'tl.set("#xw",{{clipPath:"{inset(cx, cy, cs, cs)}"}},0);tl.set("#xi",{{x:{cx+l0:.1f},y:{cy+t0:.1f},scale:1}},0);')
    c.tl(f'tl.to("#xw",{{clipPath:"{inset(0, 0, W, H)}",duration:{dur},ease:"power3.inOut"}},{lx});')
    c.tl(f'tl.to("#xi",{{x:{l1:.1f},y:{t1:.1f},scale:{sF/s0:.4f},duration:{dur},ease:"power3.inOut"}},{lx});')
    if A.up("alleyfront", sF) > 2.0:
        c.warn.append(f"alleyfront final {A.up('alleyfront', sF):.2f}x")
    sfx += [("whoosh", t_scroll, 0.3), ("click", t_click, 0.9), ("whoosh", t_click + 0.1, 0.45)]

    # ============ C5 9.70–12.605  product page: match cut F->F, pull back, pick M, Checkout; AI-CRAFTED.
    c = F.chunk("product", 9.70, 12.605)
    TF = A.items["teefront"]
    pw = L.pick(0.52 * W, W)                              # image panel
    ph = L.pick(H, 0.50 * H)
    si = min(pw / TF["ow"], ph / TF["oh"]) * 1.08          # product photo scale in the panel
    ix, iy = pw / 2 - TF["ow"] * si / 2, ph / 2 - TF["oh"] * si / 2 + L.pick(0, 0.04 * H)
    Fx, Fy = ix + 1648 * si, iy + 1089 * si               # F position in page coords
    zs = (MATCH_F_H * u / 300) / si                       # camera scale so F matches C4's last frame
    ux, uy = L.pick(0.60 * W, 0.08 * W), L.pick(0.20 * H, 0.55 * H)  # info column origin
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
  {info}</div>''', 9.70, 12.605, z=1, id="ppL", style="background:#fff")
    c.tl(f'tl.fromTo("#pp",{{x:{W/2 - Fx*zs:.1f},y:{H/2 - Fy*zs:.1f},scale:{zs:.4f}}},{{x:0,y:0,scale:1,duration:0.95,ease:"power3.inOut"}},0);')
    # info column positions in frame (after pull-back)
    mx = ux + sz + round(14 * u) + sz / 2; my = uy + round(70*u) + round(14*u) + round(40*u)*1.25 + round(40*u) + sz / 2
    ckx = ux + 310 * u; cky = my + sz / 2 + round(30*u) + round(34*u)*1.3 + round(30*u) + 44 * u
    t_m, t_ck, t_ai = 10.535, 11.225, 11.26
    c.cursor([(10.0, W * 0.92, H * 0.95), (10.48, mx, my), (10.70, mx, my), (11.17, ckx, cky), (11.4, ckx + 4, cky + 3)],
             clicks=[t_m, t_ck], start=10.0, end=t_ai + 0.05)
    c.tl(f'tl.set("#szM",{{background:"#000",color:"#fff"}},{c.t(t_m)});')
    c.tl(f'tl.set("#ck",{{background:"#222"}},{c.t(t_ck)});tl.set("#ck",{{background:"#000"}},{c.t(t_ck)+0.1});')
    # blur swap: the page drops back, the line slams in
    c.tl(f'tl.to("#pp",{{filter:"blur(18px)",opacity:0.35,duration:0.18,ease:"power2.out"}},{c.t(t_ai)});')
    c.tl(f'tl.to("#pp",{{scale:1.03,duration:{12.605-t_ai},ease:"none",transformOrigin:"50% 50%"}},{c.t(t_ai)});')
    c.words(["AI-CRAFTED."], [t_ai + 1 / FPS], 12.605, W / 2, H / 2, "bhs ink", enter="slam", id="ai")
    c.style(f"#ai .bhs{{font-size:{round(L.pick(210, 150)*u)}px}}")
    sfx += [("click", t_m, 0.8), ("click", t_ck, 0.9), ("hit", t_ai, 0.55)]

    # ============ C6 12.605–14.675  slot roll of the AI models; EVERY MODEL. EVERY AD.
    c = F.chunk("models", 12.605, 14.675)
    c.box("", 12.605, 14.675, z=0, style="background:#fff")
    ww, wh = L.pick(0.37 * W, 0.62 * W), L.pick(0.80 * H, 0.42 * H)
    wx, wy = L.pick(0.57 * W, (W - 0.62 * W) / 2), L.pick(0.10 * H, 0.16 * H)
    reel = [("alleyback", 2048, 1700, 2400), ("hoodback", 2046, 1300, 2300), ("teeback", 1297, 1290, 1500),
            ("alleyfront", 1600, 1700, 2500), ("grave", 680, 400, 700), ("hoodwalk", 2050, 1150, 2200)]
    cells = "".join(f'<div style="position:absolute;left:0;top:{i*wh}px;width:{ww}px;height:{wh}px;overflow:hidden">'
                    f'{c.crop(k, x, y, h, ww, wh)[0]}</div>' for i, (k, x, y, h) in enumerate(reel))
    c.box(f'<div style="position:absolute;left:{wx}px;top:{wy}px;width:{ww}px;height:{wh}px;overflow:hidden;background:#000">'
          f'<div id="strip" style="position:absolute;left:0;top:0;width:{ww}px;height:{len(reel)*wh}px">{cells}</div></div>',
          12.605, 14.675, z=2, id="slot")
    land = 13.985
    c.tl(f'tl.fromTo("#strip",{{y:0}},{{y:{-(len(reel)-1)*wh},duration:{land-12.605},ease:"power3.out"}},0);')
    c.tl(f'tl.fromTo("#slot",{{scale:1}},{{scale:1.035,duration:{14.675-12.605},ease:"none"}},0);')
    tx, ty1, ty2 = L.pick(0.08 * W, W / 2), L.pick(0.40 * H, 0.66 * H), L.pick(0.58 * H, 0.75 * H)
    al = L.pick("left", "center")
    fs6 = round(L.pick(112, 110) * u)
    c.words(["EVERY", "MODEL."], [12.75, 12.75], 14.675, tx, ty1, "bhs ink", align=al, id="m1")
    c.words(["EVERY", "AD."], [13.295, 13.295], 14.675, tx, ty2, "bhs ink", align=al, id="m2")
    c.style(f"#m1 .bhs,#m2 .bhs{{font-size:{fs6}px}}")
    for k in range(1, len(reel)):                       # ticks as cells pass (power3.out)
        frac = 1 - (1 - k / (len(reel) - 1)) ** (1 / 3)
        sfx.append(("tick", 12.605 + frac * (land - 12.605), 0.5 if k < len(reel) - 1 else 0.9))

    # ============ C7 14.675–17.425  payoff on black: READY TO SLAY. hard-cut per word, the hands breathing behind
    c = F.chunk("payoff", 14.675, 17.425)
    c.photo("hands", "F", zoom=L.pick(1.0, 1.0), push=1.06, start=14.675, end=17.425,
            filt="filter:brightness(.38) saturate(1.1)", vign=0.8, id="hb")
    c.tl(f'tl.fromTo("#hb",{{opacity:0.45}},{{opacity:0.45}},0);tl.set("#hb",{{opacity:1}},{c.t(15.365)});')
    fs7 = round(L.pick(190, 200) * u)
    if L.vert:
        for i, (wd, t) in enumerate((("READY", 14.675), ("TO", 15.02), ("SLAY.", 15.365))):
            c.words([wd], [t], 17.425, W / 2, H * (0.36 + 0.14 * i), "bhs white", enter="cut", id=f"p{i}")
        c.style(f"#p0 .bhs,#p1 .bhs,#p2 .bhs{{font-size:{fs7}px}}")
    else:
        c.words(["READY", "TO", "SLAY."], [14.675, 15.02, 15.365], 17.425, W / 2, H / 2, "bhs white", enter="cut", id="pay")
        c.style(f"#pay .bhs{{font-size:{fs7}px}}")
    sfx += [("hit", 14.675, 0.5), ("hit", 15.02, 0.45), ("hit", 15.365, 0.75)]

    # ============ C8 17.425–20.0  end card on white
    c = F.chunk("end", 17.425, 20.0)
    c.box("", 17.425, 20.0, z=0, style="background:#fff")
    isz = round(L.pick(380, 520) * u)
    ic, _, _ = c.crop("handscut", 1782, 1782, 3400, isz, isz)
    gy = L.pick(0.36 * H, 0.38 * H)
    c.box(f'<div id="eg" style="position:absolute;inset:0">'
          f'<div id="ic" style="position:absolute;left:{W/2-isz/2}px;top:{gy-isz/2}px;width:{isz}px;height:{isz}px;overflow:hidden">{ic}</div>'
          f'<div id="ew" class="bhs ink" style="position:absolute;left:{W/2}px;top:{gy+isz*0.62}px;transform:translate(-50%,0);font-size:{round(150*u)}px">FEELING</div>'
          f'<div id="el" class="afa ink" style="position:absolute;left:{W/2}px;top:{gy+isz*0.62+170*u}px;transform:translate(-50%,0);font-size:{round(44*u)}px;white-space:nowrap">An AI-driven streetwear brand.</div>'
          f'<div id="es" class="afa" style="position:absolute;left:{W/2}px;top:{L.pick(0.90,0.80)*H}px;transform:translate(-50%,0);font-size:{round(28*u)}px;color:#64748B">Made by Ettore</div>'
          f'</div>', 17.425, 20.0, z=2, id="endL")
    c.tl('tl.fromTo("#ic",{scale:1.08},{scale:1,duration:0.12,ease:"power2.out"},0);')
    for sel, t in (("#ew", 17.60), ("#el", 17.82), ("#es", 18.05)):
        c.tl(f'tl.fromTo("{sel}",{{opacity:0}},{{opacity:1,duration:0.01}},{c.t(t)});')
    c.tl(f'tl.fromTo("#eg",{{scale:1}},{{scale:1.02,duration:{20-17.425},ease:"none",transformOrigin:"50% 45%"}},0);')
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
        final = HERE / "out" / f"feeling_{fmt}_20s_v1.mp4"
        final.parent.mkdir(exist_ok=True)
        audio(F, sfx, final)
        print(final)
