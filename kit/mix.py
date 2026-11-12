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
    mixw = (m + s).astype(np.float32)
    return master(mixw, out_wav, lufs, tp)


def _integrated(x):
    with tempfile.TemporaryDirectory() as td:
        raw = Path(td) / "x.f32"
        x.astype(np.float32).tofile(raw)
        r = subprocess.run(["ffmpeg", "-v", "info", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", str(raw),
                            "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
    return float(r[r.rfind("Summary:"):].split("I:")[1].split("LUFS")[0])


def limit(x, ceiling_db, look_ms=3.0, release_ms=80.0):
    """Look-ahead brickwall on sample peaks (deterministic, no overshoot in the WAV)."""
    from scipy.ndimage import minimum_filter1d
    c = 10 ** (ceiling_db / 20)
    peak = np.abs(x).max(1) + 1e-12
    need = np.minimum(1.0, c / peak)
    la = max(1, int(SR * look_ms / 1000))
    g = minimum_filter1d(need, size=2 * la + 1, origin=0)        # gain already down when the peak arrives
    rel = np.exp(-1 / (SR * release_ms / 1000))
    out = np.empty_like(g); cur = 1.0
    for i, v in enumerate(g):                                  # instant attack, smooth release
        cur = v if v < cur else v + (cur - v) * rel
        out[i] = cur
    return x * out[:, None].astype(np.float32)


def master(x, out_wav, lufs=-16.0, tp=-1.5):
    """Gain to target LUFS, then limit sample peaks 1.5 dB under the true-peak target:
    AAC adds up to ~1.5 dB on transients (LESSONS), so the MP4 lands <= tp."""
    for _ in range(2):                                         # limiting costs a little loudness: re-trim once
        x = x * 10 ** ((lufs - _integrated(x)) / 20)
        x = limit(x, tp - 1.5)
    with tempfile.TemporaryDirectory() as td:
        raw = Path(td) / "m.f32"
        x.astype(np.float32).tofile(raw)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", str(raw),
                        "-c:a", "pcm_s24le", str(out_wav)], check=True)
    return out_wav


def measure(path):
    r = subprocess.run(["ffmpeg", "-v", "info", "-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    tail = r[r.rfind("Summary:"):]
    I = float(tail.split("I:")[1].split("LUFS")[0])
    P = float(tail.split("Peak:")[1].split("dBFS")[0])
    return I, P
