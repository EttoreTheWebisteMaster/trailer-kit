# LESSONS — mistakes that already cost a render. Read before building.

## Runtime (HyperFrames)
- Tween transforms only (x, y, scale, opacity, clipPath). `top`/`left`/`width`/`height` tweens are rejected by StaticGuard and the whole timeline silently freezes. The kit runs `validate` before every render and stops on this.
- Never put a CSS `transform` on an element GSAP moves with x/y: set the start with `tl.set` instead (kit cursor does this).
- Centre text on a 0×0 wrapper + `xPercent/yPercent:-50` on the inner, so the wrapper can move and scale freely.
- Chrome: `HYPERFRAMES_BROWSER_PATH=/usr/bin/google-chrome` (bundled download fails). The kit sets it.
- System emoji don't render: use Noto SVGs (`@svgmoji/noto`).

## Images
- Never upscale art past 2× the shipped file (`MAX_UPSCALE`; the kit warns). Raise `max_px` on an asset instead of zooming a small copy.
- Transparent PNGs flatten to black in JPEG: the kit composites them on white.
- Don't over-brighten dark art (> ~1.2): it goes muddy.
- Real logos on clothes/shoes in AI shots (e.g. swooshes): frame above them.

## Timing and sound
- Chunk lengths are cut on the film frame grid (`round(t1*30) - round(t0*30)`), or the film drifts a frame.
- Don't force a silence beat on tracks with no drop to rise into (Roaster / Take Five).
- Drop: RMS-scan at 50 ms around the breakdown; `offset = drop_in_song − reveal_time`; confirm the peak in the render.
- SFX quiet and few; synthesized ones live in `kit/mix.py`.

## Look
- The kit is craft only. Every trailer gets its own LOOK (pace, motion, transitions, type, sound) from the product. Don't reuse another film's LOOK.
