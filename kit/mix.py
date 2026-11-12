"""trailer-kit audio: music bed with offset + silence beat, synthesized SFX, loudness to spec.

LESSONS: SFX few and quiet, each with a cause on screen, one frame after the picture.
Master -16 LUFS, true peak <= -1.5 dBTP. Music bed ~ -18 LUFS before SFX.
"""
import json, subprocess, tempfile
from pathlib import Path
import numpy as np

SR = 48000
FRAME = 1 / 30


def load(path, start, dur):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(start), "-t", str(dur), "-i", str(path),
                          "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    a = np.frombuffer(raw, dtype=np.float32).reshape(-1, 2).copy()
    n = int(round(dur * SR))
    if len(a) < n:
        a = np.vstack([a, np.zeros((n - len(a), 2), np.float32)])
    return a[:n]


def env_ramp(n, a, b):
    return np.linspace(a, b, max(n, 1), dtype=np.float32)


# ---- synthesized SFX (deterministic) ---------------------------------------
def _noise(n, seed):
    return np.random.default_rng(seed).standard_normal(n).astype(np.float32)


def sfx(kind, seed=1):
    t = lambda d: np.arange(int(d * SR)) / SR
    if kind == "thud":       # deep body hit: pitched-down sine + soft click
        x = t(0.9); f = 70 * np.exp(-x * 6) + 38
        y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x * 5.5)
        y[:240] += _noise(240, seed)[:240] * np.linspace(0.4, 0, 240)
        return y
    if kind == "heart":      # muffled double beat
        x = t(0.55); y = np.zeros_like(x)
        for off, g in ((0, 1.0), (0.17, 0.7)):
            m = x >= off; xx = x[m] - off
            y[m] += g * np.sin(2 * np.pi * (55 + 30 * np.exp(-xx * 30)) * xx) * np.exp(-xx * 16)
        return y
    if kind == "click":
        # soft-attack click: hard broadband transients overshoot ~3 dB after AAC (LESSONS)
        x = t(0.05); nz = np.convolve(_noise(len(x), seed), np.ones(6) / 6, "same")
        y = nz * np.exp(-x * 220) * 0.5 + np.sin(2 * np.pi * 2400 * x) * np.exp(-x * 300) * 0.4
        y[:48] *= np.linspace(0, 1, 48)
        return y
    if kind == "tick":
        x = t(0.03); return np.sin(2 * np.pi * 2100 * x) * np.exp(-x * 400)
    if kind == "whoosh":     # band-swept noise, rises then falls
        x = t(0.5); nz = _noise(len(x), seed)
        k = np.exp(-((x - 0.3) / 0.13) ** 2)
        y = np.convolve(nz, np.ones(9) / 9, "same") * k
        return y * 0.9
    if kind == "hit":        # short impact: sub + noise burst
        x = t(0.6)
        return np.sin(2 * np.pi * 48 * x) * np.exp(-x * 7) + _noise(len(x), seed) * np.exp(-x * 40) * 0.35
    raise ValueError(kind)


def mix(music, offset, length, out_wav, mutes=(), fade_out=None, events=(), music_gain=1.0,
        sfx_gain=0.5, lufs=-16.0, tp=-1.5):
    """mutes: [(t0, t1)] hard silence windows (2 ms edges); fade_out: (t0, t1);
    events: [(kind, film_t, gain)] placed one frame after film_t."""
    m = load(music, offset, length) * music_gain
    for a, b in mutes:
        i0, i1, e = int(a * SR), int(b * SR), int(0.002 * SR)
        m[i0:i1] = 0
        m[max(0, i0 - e):i0] *= env_ramp(min(e, i0), 1, 0)[:, None]
        m[i1:i1 + e] *= env_ramp(e, 0, 1)[:, None]
    if fade_out:
        i0, i1 = int(fade_out[0] * SR), int(fade_out[1] * SR)
        m[i0:i1] *= env_ramp(i1 - i0, 1, 0)[:, None]
        m[i1:] = 0
    s = np.zeros_like(m)
    for k, (kind, ft, g) in enumerate(events):
        y = sfx(kind, seed=k + 1) * g * sfx_gain
        i = int((ft + FRAME) * SR)
        j = min(len(s), i + len(y))
        s[i:j] += y[: j - i, None]
    mixw = m + s
    with tempfile.TemporaryDirectory() as td:
        raw = Path(td) / "mix.f32"
        mixw.astype(np.float32).tofile(raw)
        base = ["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", str(raw)]
        # pass 1: measure
        r = subprocess.run([x if x != "error" else "info" for x in base] + ["-af", f"loudnorm=I={lufs}:TP={tp}:LRA=11:print_format=json", "-f", "null", "-"],
                           capture_output=True, text=True)
        js = json.loads(r.stderr[r.stderr.rfind("{"):])
        af = (f"loudnorm=I={lufs}:TP={tp}:LRA=11:measured_I={js['input_i']}:measured_TP={js['input_tp']}:"
              f"measured_LRA={js['input_lra']}:measured_thresh={js['input_thresh']}:offset={js['target_offset']}:linear=true,"
              f"alimiter=limit={10**((tp-1.6)/20):.4f}:level=disabled,aresample={SR}")
        subprocess.run(base + ["-af", af, "-c:a", "pcm_s16le", str(out_wav)], check=True)
    return out_wav


def measure(path):
    r = subprocess.run(["ffmpeg", "-v", "info", "-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    tail = r[r.rfind("Summary:"):]
    I = float(tail.split("I:")[1].split("LUFS")[0])
    P = float(tail.split("Peak:")[1].split("dBFS")[0])
    return I, P
