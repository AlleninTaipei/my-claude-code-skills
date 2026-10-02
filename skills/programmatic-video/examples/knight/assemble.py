"""把 AI 生成的三段鏡頭組成 13 秒預告: 剪接, 調色, 遮幅, 標題, 原創配樂.

素材在 gen/ (由 PixelForge 生成): shot_a.mp4, shot_b.mp4, shot_c.mp4
用法:
    python assemble.py           輸出 knight.mp4
    python assemble.py check     只輸出關鍵影格 PNG 到 check/
"""
import math
import os
import sys

import av
import cv2
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "got"))
import audio as A            # noqa: E402  重用 got 的合成函式
from fx import text_mask     # noqa: E402

W, H = 1920, 1080
BAR_H = 138
FPS = 24
SR = A.SR

# (素材, 素材起點秒, 時間軸起點, 時間軸終點)
CUTS = (("shot_a.mp4", 0.6, 0.0, 3.5),
        ("shot_b.mp4", 0.35, 3.5, 6.75),
        ("shot_c.mp4", 0.8, 6.75, 10.0))
DUR = 13.0
N = int(DUR * FPS)
TITLE_T = 10.0
GRAIN = np.random.default_rng(5)


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def load(name):
    c = av.open(os.path.join(HERE, "gen", name))
    frames = [f.to_ndarray(format="rgb24") for f in c.decode(video=0)]
    c.close()
    return frames


def fit(frame):
    """等比放大填滿 1920x1080 後置中裁切."""
    h, w = frame.shape[:2]
    s = max(W / w, H / h)
    big = cv2.resize(frame, (int(math.ceil(w * s)), int(math.ceil(h * s))), interpolation=cv2.INTER_LANCZOS4)
    y0 = (big.shape[0] - H) // 2
    x0 = (big.shape[1] - W) // 2
    return big[y0:y0 + H, x0:x0 + W].astype(np.float32) / 255


def grade(img):
    """輕微的青橘調色與 S 曲線."""
    lum = img.mean(axis=2, keepdims=True)
    shadow = np.clip(1 - lum * 2.2, 0, 1)
    high = np.clip(lum * 1.6 - 0.6, 0, 1)
    img = img + shadow * np.array([-0.012, 0.004, 0.018], np.float32) + high * np.array([0.03, 0.012, -0.02], np.float32)
    img = np.clip(img, 0, 1)
    return img * img * (3 - 2 * img) * 0.35 + img * 0.65


def finish(img):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    vr = ((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2
    img = img * (1 - 0.25 * vr)[..., None]
    img = img + GRAIN.normal(0, 0.012, (H, W, 1)).astype(np.float32)
    img = np.clip(img, 0, 1)
    img[:BAR_H] = 0
    img[H - BAR_H:] = 0
    return img


def place(img, m, cx, cy, color, alpha):
    th, tw = m.shape
    x0, y0 = int(cx - tw / 2), int(cy - th / 2)
    mm = m[..., None] * alpha
    reg = img[y0:y0 + th, x0:x0 + tw]
    reg *= 1 - mm
    reg += np.asarray(color, np.float32) * mm


def title(img, lt):
    a = ease(lt / 1.2)
    tr = 44 - 18 * ease(lt / 1.8)
    m = text_mask("GAME OF THRONES", "constanb.ttf", 120, tr)
    m = cv2.GaussianBlur(m, (0, 0), 0.1 + 10 * (1 - a))
    if m.shape[1] > W - 40:                         # 保險: 超出畫面時置中裁切
        c0 = (m.shape[1] - (W - 40)) // 2
        m = m[:, c0:c0 + W - 40]
    th, tw = m.shape
    gx = np.arange(tw, dtype=np.float32)[None, :]
    gy = np.linspace(0, 1, th, dtype=np.float32)[:, None]
    metal = 0.6 + 0.4 * np.exp(-((gy - 0.42) / 0.12) ** 2) - 0.2 * gy
    sweep = np.exp(-((gx + gy * 120 - (-300 + (tw + 600) * ease((lt - 0.6) / 1.6))) / 90) ** 2) * 0.9
    col = np.clip((metal + sweep)[..., None] * np.array([0.93, 0.89, 0.81], np.float32), 0, 1)
    th2, tw2 = m.shape
    x0, y0 = int(W / 2 - tw2 / 2), int(H * 0.47 - th2 / 2)
    mm = m[..., None] * a
    reg = img[y0:y0 + th2, x0:x0 + tw2]
    reg *= 1 - mm
    reg += col * mm
    a2 = ease((lt - 1.2) / 0.8)
    place(img, text_mask("WINTER IS COMING", "constan.ttf", 34, 16), W / 2, H * 0.59, (0.85, 0.85, 0.86), a2)


def build_frames():
    clips = {name: load(name) for name, *_ in CUTS}
    last = None
    for f in range(N):
        t = f / FPS
        img = None
        for name, src0, a, b in CUTS:
            if a <= t < b:
                fr = clips[name]
                idx = min(int(round((src0 + t - a) * FPS)), len(fr) - 1)
                img = grade(fit(fr[idx]))
                if t - a < 0.12 and a > 0:                    # 剪接點的閃光
                    img = img + 0.25 * math.exp(-(t - a) / 0.05)
                if b - t < 0.1 and b < TITLE_T:
                    img = img * (1 - 0.6 * ease((t - (b - 0.1)) / 0.1))
                last = (name, idx)
        if img is None:
            # 標題: 最後一格放慢推近, 模糊壓暗
            name, idx = last
            base = grade(fit(clips[name][idx]))
            lt = t - TITLE_T
            s = 1 + 0.04 * lt
            M = np.float32([[s, 0, W / 2 - s * W / 2], [0, s, H / 2 - s * H / 2]])
            base = cv2.warpAffine(base, M, (W, H), borderMode=cv2.BORDER_REFLECT)
            k = ease(lt / 0.8)
            base = cv2.GaussianBlur(base, (0, 0), 0.1 + 9 * k) * (1 - 0.7 * k)
            img = base + 0.6 * math.exp(-lt / 0.08)
            title(img, lt)
            img *= 1 - ease((lt - 2.3) / 0.7)
        if t < 0.6:
            img = img * ease(t / 0.6)
        yield (finish(np.clip(img, 0, 1.5)) * 255 + 0.5).astype(np.uint8)


def build_audio():
    n = int(SR * DUR)
    t = np.arange(n) / SR
    rng = np.random.default_rng(8)
    noise = rng.standard_normal(n)
    L = np.zeros(n)
    R = np.zeros(n)
    wet = np.zeros(n)

    def add(sig, pan=0.0, rv=0.0):
        nonlocal L, R, wet
        L += sig * (1 - max(pan, 0))
        R += sig * (1 + min(pan, 0))
        wet += sig * rv

    def gate(a, b, fade=0.01):
        return np.clip((t - a) / fade, 0, 1) * np.clip((b - t) / fade, 0, 1)

    def braam(t0, amp=1.0):
        notes = (A.D2 / 2, A.D2, A.A2, A.D3)
        sig = sum(A.saw(t, f) + A.saw(t, f * 1.007) for f in notes)
        open_ = A.env(t, t0, 0.08, 0.7)
        out = A.fft_filter(sig, hi=250) * (1 - open_) + A.fft_filter(sig, hi=1200) * open_
        add(out * A.env(t, t0, 0.04, 1.6) * 0.12 * amp, 0, 0.35)
        add(A.sweep_sine(t, t0, 120, 30, 0.08) * A.env(t, t0, 0.003, 1.0) * 0.7 * amp, 0, 0.1)
        add(A.fft_filter(noise, hi=1500) * A.env(t, t0, 0.001, 0.3) * 0.35 * amp, 0, 0.5)

    def taiko(t0, amp=1.0):
        add(A.sweep_sine(t, t0, 140, 55, 0.04) * A.env(t, t0, 0.002, 0.35) * 0.7 * amp, 0, 0.4)
        add(A.fft_filter(noise, lo=80, hi=900) * A.env(t, t0, 0.001, 0.06) * 0.35 * amp, 0, 0.5)

    def riser(a, b, amp=0.5):
        u = np.clip((t - a) / (b - a), 0, 1)
        add(A.fft_filter(noise, lo=300, hi=6000) * u ** 2.5 * gate(a, b, 0.008) * amp, 0, 0.3)

    # 風與持續音
    wind = A.fft_filter(noise, lo=300, hi=1400)
    add(wind * (0.6 + 0.4 * np.sin(t * 0.8) ** 2) * gate(0, 3.6, 0.8) * 0.25, 0.2, 0.2)
    drone = np.sin(2 * np.pi * A.D2 / 2 * t) + 0.5 * A.fft_filter(A.saw(t, A.D2), hi=220)
    add(drone * np.clip(t / 2, 0, 1) * gate(0, 10.0, 0.05) * 0.22, 0, 0.2)

    # 大提琴固定音型, 3.5s 起
    pattern = (A.D3, A.A2, A.F3, A.A2, A.D3, A.A2, A.E3, A.A2)
    cello = np.zeros(n)
    step = A.BEAT / 2
    t0 = 3.5
    k = 0
    while t0 < 9.95:
        vib = 1 + 0.004 * np.sin(2 * np.pi * 5.5 * t)
        cello += A.saw(t * vib, pattern[k % len(pattern)]) * A.env(t, t0, 0.035, 0.22) * gate(t0, t0 + step * 0.95)
        t0 += step
        k += 1
    add(A.fft_filter(cello, hi=1400) * 0.13, -0.25, 0.4)

    for i in range(int((10.0 - 3.5) / A.BEAT)):
        tb = 3.5 + i * A.BEAT
        taiko(tb, 0.8 if i % 4 == 0 else 0.45)

    # 鏡頭 B 舉劍的金屬聲
    clang = sum(np.sin(2 * np.pi * f * t) * a for f, a in ((1460, 1.0), (2370, 0.6), (3520, 0.4)))
    add(clang * A.env(t, 4.6, 0.02, 0.9) * 0.08, 0.3, 0.8)

    braam(3.5, 0.9)
    braam(6.75, 1.0)
    riser(8.8, 9.98, 0.6)
    braam(TITLE_T, 1.4)
    add(A.sweep_sine(t, TITLE_T, 90, 26, 0.3) * A.env(t, TITLE_T, 0.003, 2.2) * 0.6)
    bell = sum(np.sin(2 * np.pi * 587.33 * p * t) * a for p, a in ((1, 1.0), (2.0, 0.5), (3.01, 0.25)))
    add(bell * A.env(t, 11.2, 0.003, 1.0) * 0.06, 0, 0.8)

    wl = A.reverb(wet, seed=1)
    wr = A.reverb(wet, seed=2)
    mix = np.stack([A.fft_filter(L + 0.5 * wl, lo=22, order=1), A.fft_filter(R + 0.5 * wr, lo=22, order=1)])
    mix = np.tanh(mix / np.abs(mix).max() * 1.8)
    mix *= np.clip((DUR - t) / 0.6, 0, 1)
    mix /= np.abs(mix).max() / 0.89
    return mix.astype(np.float32)


def encode(path):
    audio = build_audio()
    out = av.open(path, "w")
    vs = out.add_stream("libx264", rate=FPS)
    vs.width, vs.height, vs.pix_fmt = W, H, "yuv420p"
    vs.options = {"crf": "17", "preset": "medium"}
    ast = out.add_stream("aac", rate=SR, layout="stereo")
    ast.bit_rate = 256000
    chunk, a_pos = 1024, 0
    for f, frame in enumerate(build_frames()):
        for p in vs.encode(av.VideoFrame.from_ndarray(frame, format="rgb24")):
            out.mux(p)
        target = int((f + 1) / FPS * SR)
        while a_pos < target:
            seg = audio[:, a_pos:a_pos + chunk]
            if seg.shape[1] < chunk:
                seg = np.pad(seg, ((0, 0), (0, chunk - seg.shape[1])))
            af = av.AudioFrame.from_ndarray(np.ascontiguousarray(seg), format="fltp", layout="stereo")
            af.sample_rate = SR
            af.pts = a_pos
            for p in ast.encode(af):
                out.mux(p)
            a_pos += chunk
    for p in vs.encode():
        out.mux(p)
    for p in ast.encode():
        out.mux(p)
    out.close()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        os.makedirs(os.path.join(HERE, "check"), exist_ok=True)
        want = {12, 60, 84, 110, 150, 170, 200, 235, 250, 280}
        for f, fr in enumerate(build_frames()):
            if f in want:
                Image.fromarray(fr).save(os.path.join(HERE, "check", f"f{f:03d}.png"))
        print("saved", sorted(want))
    else:
        encode(os.path.join(HERE, "knight.mp4"))
