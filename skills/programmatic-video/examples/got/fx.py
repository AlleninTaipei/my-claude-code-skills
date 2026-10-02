"""共用特效: 雜訊, 粒子, 火焰, 文字, 後製."""
import math

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H = 1920, 1080
BAR_H = 138                     # 2.39:1 遮幅
FONT_DIR = "C:/Windows/Fonts"
YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)


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
    rng = np.random.default_rng(seed)
    out = np.zeros((h, w), np.float32)
    amp, total = 1.0, 0.0
    for o in range(octaves):
        cells = base_cells * 2 ** o
        small = rng.random((max(int(cells * h / w), 2), cells)).astype(np.float32)
        big = cv2.resize(np.tile(small, (3, 3)), (w * 3, h * 3), interpolation=cv2.INTER_CUBIC)
        out += big[h:2 * h, w:2 * w] * amp      # 取中間一塊, 上下左右可無縫接續
        total += amp
        amp *= 0.5
    out /= total
    return (out - out.min()) / (out.max() - out.min())


NOISE = {}


def noise(name):
    if name not in NOISE:
        spec = {"cloud": (1400, 2600, 4, 6, 1), "fire": (900, 900, 6, 5, 2), "ice": (1200, 2400, 3, 7, 3),
                "smoke": (900, 1800, 3, 5, 4)}[name]
        h, w, c, o, s = spec
        NOISE[name] = fbm(h, w, c, o, s)
    return NOISE[name]


def scroll(name, ox, oy, h, w):
    """從雜訊貼圖中以環繞方式取出 (h, w) 視窗."""
    n = noise(name)
    nh, nw = n.shape
    ys = (np.arange(h) + int(oy)) % nh
    xs = (np.arange(w) + int(ox)) % nw
    return n[np.ix_(ys, xs)]


# ---------- 火焰與煙 ----------

def fire_field(t, h, w, height=0.6, speed=220.0, seed_x=0.0):
    """回傳 HDR 火焰顏色, 下方最強."""
    a = scroll("fire", seed_x, t * speed, h, w)
    b = scroll("fire", seed_x + 300, t * speed * 1.7 + 200, h, w)
    n = a * 0.6 + b * 0.4
    yy = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    shape = np.clip((yy - (1 - height)) / height, 0, 1) ** 1.2
    f = np.clip(n * shape * 2.1 - 0.45, 0, None)
    r = np.clip(f * 3.0, 0, 6)
    g = np.clip(f * 1.6 - 0.15, 0, 4)
    bl = np.clip(f * 0.6 - 0.35, 0, 2)
    return np.stack([r, g * 0.9, bl * 0.6], -1) * 0.9


def smoke(t, amount, tint=(0.35, 0.3, 0.28), speed=(30, -20)):
    q = 4
    n = scroll("smoke", t * speed[0], t * speed[1], H // q, W // q)
    n = np.clip((n - 0.35) * 1.8, 0, 1) * amount
    return cv2.resize(n, (W, H))[..., None] * col(*tint)


# ---------- 粒子 ----------

class Particles:
    def __init__(self, n, seed):
        rng = np.random.default_rng(seed)
        self.p = rng.random((n, 4)).astype(np.float32)   # x, y, 深度, 相位

    def snow(self, img, t, amount, wind=0.25, fall=0.18):
        if amount <= 0:
            return
        lay = np.zeros((H, W), np.float32)
        x0, y0, z, ph = self.p.T
        sp = 0.4 + 1.6 * z
        y = (y0 + t * fall * sp) % 1.0
        x = (x0 + t * wind * sp + 0.01 * np.sin(t * 2 + ph * 6.28)) % 1.0
        for xi, yi, zi in zip(x, y, z):
            px, py = int(xi * W), int(yi * H)
            r = 1 + int(zi * 3.5)
            dx = int(wind * 30 * zi)
            cv2.line(lay, (px, py), (px - dx, py - int(fall * 40 * zi)), float(0.4 + 0.6 * zi), r, cv2.LINE_AA)
        lay = cv2.GaussianBlur(lay, (0, 0), 1.2)
        img += lay[..., None] * col(0.85, 0.9, 1.0) * amount

    def embers(self, img, t, amount, rise=0.12):
        if amount <= 0:
            return
        lay = np.zeros((H, W), np.float32)
        x0, y0, z, ph = self.p.T
        y = (y0 - t * rise * (0.5 + z)) % 1.0
        x = (x0 + 0.03 * np.sin(t * 1.5 + ph * 6.28) + t * 0.02) % 1.0
        flick = 0.5 + 0.5 * np.sin(t * 9 + ph * 40)
        for xi, yi, zi, fi in zip(x, y, z, flick):
            cv2.circle(lay, (int(xi * W), int(yi * H)), 1 + int(zi * 2.5), float(fi * (0.5 + zi)), -1, cv2.LINE_AA)
        glow = cv2.GaussianBlur(lay, (0, 0), 4)
        img += (lay * 2.0 + glow * 2.5)[..., None] * col(1.0, 0.45, 0.12) * amount


# ---------- 輪廓光 ----------

def rim(mask, dx, dy, blur=1.5):
    """mask 往光源方向位移後的差, 作為剪影的邊緣光."""
    M = np.float32([[1, 0, -dx], [0, 1, -dy]])
    shifted = cv2.warpAffine(mask, M, (mask.shape[1], mask.shape[0]))
    r = np.clip(mask - shifted, 0, 1)
    return cv2.GaussianBlur(r, (0, 0), blur)


def composite_silhouette(img, mask, body=(0.01, 0.01, 0.012), rim_col=None, rim_dir=(6, -3), rim_k=1.0):
    m = mask[..., None]
    img *= 1 - m
    img += m * col(*body)
    if rim_col is not None:
        img += rim(mask, *rim_dir)[..., None] * col(*rim_col) * rim_k


# ---------- 文字 ----------

def font(name, size):
    return ImageFont.truetype(f"{FONT_DIR}/{name}", int(size))


def text_mask(text, name, size, tracking=0.0):
    f = font(name, size)
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


def title_text(img, text, name, size, cx, cy, alpha, tracking, blur=0.0, color=(0.92, 0.9, 0.86)):
    m = text_mask(text, name, size, tracking)
    if blur > 0.3:
        m = cv2.GaussianBlur(m, (0, 0), blur)
    place(img, m, cx, cy, col(*color), alpha)


# ---------- 後製 ----------

GRAIN = np.random.default_rng(77)


def shake(img, amount, t):
    if amount <= 0.01:
        return img
    dx = amount * 14 * math.sin(t * 91.0) * math.cos(t * 37.0)
    dy = amount * 10 * math.sin(t * 73.0 + 1.0)
    M = np.float32([[1.02, 0, dx - W * 0.01], [0, 1.02, dy - H * 0.01]])
    return cv2.warpAffine(img, M, (W, H), borderMode=cv2.BORDER_REFLECT)


def post(img, grade=(1.0, 1.0, 1.0), lift=0.0):
    q = 4
    small = cv2.resize(np.maximum(img - 0.8, 0), (W // q, H // q), interpolation=cv2.INTER_AREA)
    b1 = cv2.GaussianBlur(small, (0, 0), 3)
    b2 = cv2.GaussianBlur(small, (0, 0), 14)
    img = img + cv2.resize(b1 * 0.6 + b2 * 0.5, (W, H))
    img = img * col(*grade) + lift
    x = np.maximum(img, 0)
    img = (x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14)
    vr = ((XX - W / 2) / (W / 2)) ** 2 + ((YY - H / 2) / (H / 2)) ** 2
    img *= (1 - 0.32 * vr)[..., None]
    img += GRAIN.normal(0, 0.014, (H, W, 1)).astype(np.float32)
    img = np.clip(img, 0, 1)
    img[:BAR_H] = 0
    img[H - BAR_H:] = 0
    return img
