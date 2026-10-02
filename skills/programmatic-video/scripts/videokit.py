"""程序化影片的共用工具: 緩動, 無縫雜訊, 文字, 後製, 音訊合成, PyAV 編碼.

在專案的 render.py 裡:
    import sys; sys.path.insert(0, r"<skill>/scripts")
    from videokit import *

只依賴 numpy, opencv-python, pillow, av (PyAV). 不需要 ffmpeg 執行檔.
"""
import math
import os
from multiprocessing import Pool

import av
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONT_DIR = "C:/Windows/Fonts" if os.name == "nt" else "/usr/share/fonts"


# ---------- 緩動 ----------

def clamp01(x):
    return min(max(x, 0.0), 1.0)


def ease(x):
    x = clamp01(x)
    return x * x * (3 - 2 * x)


def ease_out(x):
    x = clamp01(x)
    return 1 - (1 - x) ** 3


def ease_in(x):
    x = clamp01(x)
    return x ** 3


def ease_io(x):
    x = clamp01(x)
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def lerp(a, b, u):
    return a + (b - a) * u


def col(*c):
    return np.array(c, np.float32)


# ---------- 雜訊 ----------

def fbm(h, w, base_cells, octaves, seed):
    """無縫 (可上下左右環繞) 的分形雜訊, 值域 0-1.

    先把小格點 tile 成 3x3 再放大, 取中間一塊, 邊界自然接續.
    非無縫雜訊在捲動時會出現明顯的直線接縫.
    """
    rng = np.random.default_rng(seed)
    out = np.zeros((h, w), np.float32)
    amp, total = 1.0, 0.0
    for o in range(octaves):
        cells = base_cells * 2 ** o
        small = rng.random((max(int(cells * h / w), 2), cells)).astype(np.float32)
        big = cv2.resize(np.tile(small, (3, 3)), (w * 3, h * 3), interpolation=cv2.INTER_CUBIC)
        out += big[h:2 * h, w:2 * w] * amp
        total += amp
        amp *= 0.5
    out /= total
    return (out - out.min()) / (out.max() - out.min())


def scroll(tex, ox, oy, h, w):
    """從雜訊貼圖以環繞方式取出 (h, w) 視窗, 用來做捲動的雲, 煙, 火."""
    th, tw = tex.shape[:2]
    ys = (np.arange(h) + int(oy)) % th
    xs = (np.arange(w) + int(ox)) % tw
    return tex[np.ix_(ys, xs)]


# ---------- 文字 ----------

def font(name, size, variation=None):
    f = ImageFont.truetype(os.path.join(FONT_DIR, name), int(size))
    if variation:
        f.set_variation_by_name(variation)
    return f


def text_mask(text, name, size, tracking=0.0, variation=None):
    """回傳文字的 float 遮罩 (0-1). tracking 為字距 px, 可做動畫."""
    f = font(name, size, variation)
    widths = [f.getlength(c) for c in text]
    tw = int(sum(widths) + tracking * (len(text) - 1)) + 20
    th = int(size * 1.6)
    im = Image.new("L", (tw, th), 0)
    d = ImageDraw.Draw(im)
    x = 10
    for c, w in zip(text, widths):
        d.text((x, th * 0.5), c, font=f, fill=255, anchor="lm")
        x += w + tracking
    return np.asarray(im, np.float32) / 255


def place(img, m, cx, cy, color, alpha=1.0):
    """把遮罩以 color 合成到 img, 中心在 (cx, cy). 超出畫面的部分自動裁掉.

    color 可以是 RGB 向量, 或與 m 同尺寸的 (h, w, 3) 陣列 (漸層, 金屬質感).
    """
    H, W = img.shape[:2]
    th, tw = m.shape
    x0, y0 = int(cx - tw / 2), int(cy - th / 2)
    xa, ya, xb, yb = max(x0, 0), max(y0, 0), min(x0 + tw, W), min(y0 + th, H)
    if xb <= xa or yb <= ya or alpha <= 0.002:
        return
    mm = m[ya - y0:yb - y0, xa - x0:xb - x0][..., None] * alpha
    c = color if np.ndim(color) == 1 else color[ya - y0:yb - y0, xa - x0:xb - x0]
    reg = img[ya:yb, xa:xb]
    reg *= 1 - mm
    reg += np.asarray(c, np.float32) * mm


def scrim(img, yc, side, amount, width=1150, sigma=200):
    """字卡後方的暗色漸層. side: 'l', 'r' 或 'c'. 複雜背景上的字一定要墊."""
    if amount <= 0:
        return
    H, W = img.shape[:2]
    y0, y1 = int(max(yc - 2 * sigma, 0)), int(min(yc + 2 * sigma, H))
    xs = np.arange(W, dtype=np.float32)
    d = xs if side == "l" else (W - xs) if side == "r" else np.abs(xs - W / 2) * 1.6
    hm = np.clip(1 - d / width, 0, 1) ** 1.2
    vm = np.exp(-((np.arange(y0, y1, dtype=np.float32) - yc) / sigma) ** 4)
    img[y0:y1] *= (1 - amount * vm[:, None] * hm[None, :])[..., None]


# ---------- 剪影 ----------

def rim(mask, dx, dy, blur=1.5):
    """遮罩往光源方向位移後的差, 當作剪影的邊緣光."""
    M = np.float32([[1, 0, -dx], [0, 1, -dy]])
    shifted = cv2.warpAffine(mask, M, (mask.shape[1], mask.shape[0]))
    return cv2.GaussianBlur(np.clip(mask - shifted, 0, 1), (0, 0), blur)


def silhouette(img, mask, body=(0.01, 0.01, 0.012), rim_col=None, rim_dir=(5, -3), rim_k=1.0):
    m = mask[..., None]
    img *= 1 - m
    img += m * col(*body)
    if rim_col is not None:
        img += rim(mask, *rim_dir)[..., None] * col(*rim_col) * rim_k


# ---------- 後製 ----------

def aces(x):
    x = np.maximum(x, 0)
    return (x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14)


def post(img, *, focus=None, bloom=0.8, streak=0.0, grade=(1, 1, 1), vignette=0.3, grain=0.012,
         letterbox=0, rng=None):
    """場景以線性 HDR 值繪製, 最後一次做: 景深, bloom, 橫向光條, 調色, ACES, 暗角, 顆粒, 遮幅.

    focus: (fx, fy, r0, r1) 以焦點為中心, r0 內清楚, r1 外全糊.
    letterbox: 上下黑邊高度 px (2.39:1 在 1080p 約 138).
    """
    H, W = img.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    if focus is not None:
        fx, fy, r0, r1 = focus
        blur = cv2.GaussianBlur(img, (0, 0), 6)
        m = np.clip((np.hypot(xx - fx, yy - fy) - r0) / (r1 - r0), 0, 1)[..., None]
        img = img * (1 - m) + blur * m
    q = 4
    small = cv2.resize(np.maximum(img - bloom, 0), (W // q, H // q), interpolation=cv2.INTER_AREA)
    add = cv2.GaussianBlur(small, (0, 0), 3) * 0.6 + cv2.GaussianBlur(small, (0, 0), 14) * 0.5
    if streak > 0:
        add = add + cv2.blur(small.mean(axis=2), (151, 1))[..., None] * col(0.45, 0.6, 1.0) * streak
    img = img + cv2.resize(add, (W, H))
    img = aces(img * col(*grade))
    vr = ((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2
    img *= (1 - vignette * vr)[..., None]
    rng = rng or np.random.default_rng()
    img += rng.normal(0, grain, (H, W, 1)).astype(np.float32)
    img = np.clip(img, 0, 1)
    if letterbox:
        img[:letterbox] = 0
        img[H - letterbox:] = 0
    return img


def to_u8(img):
    return (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)


def shake(img, amount, t):
    if amount <= 0.01:
        return img
    H, W = img.shape[:2]
    dx = amount * 14 * math.sin(t * 91.0) * math.cos(t * 37.0)
    dy = amount * 10 * math.sin(t * 73.0 + 1.0)
    M = np.float32([[1.02, 0, dx - W * 0.01], [0, 1.02, dy - H * 0.01]])
    return cv2.warpAffine(img, M, (W, H), borderMode=cv2.BORDER_REFLECT)


def whip(img, amount, vertical=False):
    """甩鏡轉場的方向性動態模糊, amount 0-1."""
    k = int(amount * 140)
    if k < 3:
        return img
    ker = np.ones((1, k), np.float32) / k
    return cv2.filter2D(img, -1, ker.T if vertical else ker, borderType=cv2.BORDER_REFLECT)


# ---------- 音訊 ----------

SR = 48000


def fft_filter(x, lo=None, hi=None, order=2):
    """零相位的頻域濾波. 固定截止頻率時比逐樣本迴圈快上百倍."""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    g = np.ones_like(f)
    if hi is not None:
        g /= np.sqrt(1 + (f / hi) ** (2 * order))
    if lo is not None:
        g /= np.sqrt(1 + (lo / np.maximum(f, 1e-3)) ** (2 * order))
    return np.fft.irfft(X * g, len(x))


def env(t, t0, attack, decay):
    x = t - t0
    with np.errstate(over="ignore"):
        return np.where(x < 0, 0.0, np.where(x < attack, x / max(attack, 1e-4),
                                              np.exp(-np.maximum(x - attack, 0) / decay)))


def saw(t, f):
    return 2 * ((t * f) % 1.0) - 1


def sweep_sine(t, t0, f_hi, f_lo, k):
    """音高由 f_hi 指數下滑到 f_lo: kick, boom, 太鼓."""
    x = np.clip(t - t0, 0, None)
    return np.sin(2 * np.pi * np.cumsum(f_lo + (f_hi - f_lo) * np.exp(-x / k)) / SR)


def reverb(x, seconds=2.4, decay=0.6, seed=0):
    n = int(SR * seconds)
    rng = np.random.default_rng(seed)
    ir = rng.standard_normal(n) * np.exp(-np.arange(n) / (SR * decay))
    ir = fft_filter(ir, hi=6000)
    ir /= np.sqrt((ir ** 2).sum())
    size = 1 << int(np.ceil(np.log2(len(x) + n)))
    return np.fft.irfft(np.fft.rfft(x, size) * np.fft.rfft(ir, size), size)[:len(x)]


class Mixer:
    """立體聲混音匯流排, 附殘響送出.

        mx = Mixer(dur)
        mx.add(sig, pan=-0.3, rv=0.4)
        audio = mx.master()      # (2, n) float32, 峰值 -1 dBFS
    """

    def __init__(self, dur, seed=0):
        self.dur = dur
        self.n = int(SR * dur)
        self.t = np.arange(self.n) / SR
        self.noise = np.random.default_rng(seed).standard_normal(self.n)
        self.L = np.zeros(self.n)
        self.R = np.zeros(self.n)
        self.wet = np.zeros(self.n)

    def add(self, sig, pan=0.0, rv=0.0):
        self.L += sig * (1 - max(pan, 0))
        self.R += sig * (1 + min(pan, 0))
        self.wet += sig * rv

    def gate(self, a, b, fade=0.01):
        t = self.t
        return np.clip((t - a) / fade, 0, 1) * np.clip((b - t) / fade, 0, 1)

    # 常用音色
    def kick(self, t0, amp=1.0):
        self.add(sweep_sine(self.t, t0, 160, 46, 0.03) * env(self.t, t0, 0.002, 0.28) * 0.95 * amp)

    def boom(self, t0, amp=1.0, low=30):
        self.add(sweep_sine(self.t, t0, 180, low, 0.06) * env(self.t, t0, 0.002, 1.1) * amp, 0, 0.15)
        self.add(fft_filter(self.noise, hi=1800) * env(self.t, t0, 0.001, 0.35) * 0.6 * amp, 0, 0.6)

    def taiko(self, t0, amp=1.0):
        self.add(sweep_sine(self.t, t0, 140, 55, 0.04) * env(self.t, t0, 0.002, 0.35) * 0.7 * amp, 0, 0.4)
        self.add(fft_filter(self.noise, lo=80, hi=900) * env(self.t, t0, 0.001, 0.06) * 0.35 * amp, 0, 0.5)

    def riser(self, a, b, amp=0.5):
        u = np.clip((self.t - a) / (b - a), 0, 1)
        self.add(fft_filter(self.noise, lo=300, hi=6000) * u ** 2.5 * self.gate(a, b, 0.008) * amp, 0, 0.3)

    def braam(self, t0, notes=(36.71, 73.42, 110.0, 146.83), amp=1.0):
        t = self.t
        sig = sum(saw(t, f) + saw(t, f * 1.007) for f in notes)
        o = env(t, t0, 0.08, 0.7)
        out = fft_filter(sig, hi=250) * (1 - o) + fft_filter(sig, hi=1200) * o
        self.add(out * env(t, t0, 0.04, 1.6) * 0.12 * amp, 0, 0.35)
        self.boom(t0, 0.7 * amp)

    def master(self, drive=1.8, rv_mix=0.5, fade_out=0.5):
        wl = reverb(self.wet, seed=1)
        wr = reverb(self.wet, seed=2)
        mix = np.stack([fft_filter(self.L + rv_mix * wl, lo=22, order=1),
                        fft_filter(self.R + rv_mix * wr, lo=22, order=1)])
        mix = np.tanh(mix / (np.abs(mix).max() + 1e-9) * drive)
        mix *= np.clip((self.dur - self.t) / fade_out, 0, 1)
        mix /= np.abs(mix).max() / 0.89
        return mix.astype(np.float32)


def loudness_report(audio, step=2.0):
    """每段 RMS dB, 用來確認音量曲線有起伏, 也沒有整段靜音."""
    n = audio.shape[1]
    lines = []
    for s in np.arange(0, n / SR, step):
        seg = audio[:, int(s * SR):int((s + step) * SR)]
        lines.append(f"{s:5.1f}s  {20 * np.log10(np.sqrt((seg ** 2).mean()) + 1e-9):6.1f} dB")
    return "\n".join(lines)


# ---------- 編碼 ----------

def encode(path, render, n_frames, fps, audio, size=(1920, 1080), workers=1, crf=18):
    """平行渲染並以 PyAV 輸出 H.264 + AAC MP4. 不需要 ffmpeg 執行檔.

    render: 頂層函式 f -> uint8 (H, W, 3) RGB. workers > 1 時用 multiprocessing,
    在 Windows 上呼叫端必須放在 `if __name__ == "__main__":` 之下.
    影音逐格交錯寫入, 避免播放器同步問題.
    """
    W, H = size
    out = av.open(path, "w")
    vs = out.add_stream("libx264", rate=fps)
    vs.width, vs.height, vs.pix_fmt = W, H, "yuv420p"
    vs.options = {"crf": str(crf), "preset": "medium"}
    ast = out.add_stream("aac", rate=SR, layout="stereo")
    ast.bit_rate = 256000
    chunk, a_pos = 1024, 0

    def frames():
        if workers > 1:
            with Pool(workers) as pool:
                yield from pool.imap(render, range(n_frames), chunksize=2)
        else:
            for f in range(n_frames):
                yield render(f)

    for f, frame in enumerate(frames()):
        for p in vs.encode(av.VideoFrame.from_ndarray(frame, format="rgb24")):
            out.mux(p)
        target = int((f + 1) / fps * SR)
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
        if f % fps == fps - 1:
            print(f"frame {f + 1}/{n_frames}", flush=True)
    for p in vs.encode():
        out.mux(p)
    for p in ast.encode():
        out.mux(p)
    out.close()
