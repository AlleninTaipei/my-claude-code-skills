"""5 秒 iPhone 17 概念廣告, 純程式產生畫面與音訊.

用法:
    python render.py              輸出 iphone17.mp4
    python render.py 10 50 97     只輸出指定影格的 PNG, 用來檢查畫面
"""
import math
import os
import sys

import av
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1920, 1080
FPS = 30
DUR = 5.0
N = int(FPS * DUR)
SR = 48000
HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = "C:/Windows/Fonts"

IMPACT_F = 97          # 螢幕點亮與重擊音效的影格
TITLE_F = 112          # 標題出現的影格

YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)
RNG = np.random.default_rng(7)


# ---------- 共用工具 ----------

def clamp01(x):
    return min(max(x, 0.0), 1.0)


def ease(x):
    x = clamp01(x)
    return x * x * (3 - 2 * x)


def ease_out(x):
    x = clamp01(x)
    return 1 - (1 - x) ** 3


def ease_io(x):
    x = clamp01(x)
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def rrect_sdf(px, py, hx, hy, rx, ry):
    """圓角矩形的 signed distance, 角落可為橢圓."""
    rx = max(rx, 1e-3)
    ry = max(ry, 1e-3)
    rx = min(rx, hx) if hx > 0 else rx
    qx = (np.abs(px) - (hx - rx)) * (ry / rx)
    qy = np.abs(py) - (hy - ry)
    ox = np.maximum(qx, 0)
    oy = np.maximum(qy, 0)
    return np.sqrt(ox * ox + oy * oy) + np.minimum(np.maximum(qx, qy), 0) - ry


def cover(sdf, aa=1.0):
    return np.clip(0.5 - sdf / aa, 0.0, 1.0)


def rgb(*c):
    return np.array(c, dtype=np.float32)


# ---------- 手機 ----------

BRUSH = (RNG.standard_normal(4096).astype(np.float32))
BRUSH = cv2.GaussianBlur(BRUSH.reshape(-1, 1), (1, 0), 0, sigmaY=1.2).ravel()


def draw_phone(img, cx, cy, ph, theta, t, screen=0.0, glint=0.0, ai=0.0):
    """以正交投影繞 Y 軸旋轉的手機. theta=0 為背面, pi 為正面."""
    Hh = ph / 2
    Wh = Hh * 0.485
    r = Wh * 0.40
    d = Hh * 0.042
    c, s = math.cos(theta), math.sin(theta)
    ac, asn = abs(c), abs(s)
    A = Wh * ac + d * asn

    x0, x1 = int(max(cx - A - 8, 0)), int(min(cx + A + 8, W))
    y0, y1 = int(max(cy - Hh - 8, 0)), int(min(cy + Hh + 8, H))
    if x1 <= x0 or y1 <= y0:
        return
    px = XX[y0:y1, x0:x1] - cx
    py = YY[y0:y1, x0:x1] - cy

    sil_sdf = rrect_sdf(px, py, A, Hh, r * ac + d * asn, r)
    sil = cover(sil_sdf)
    foff = -d * s
    face_hx = max(Wh * ac, 0.5)
    face = cover(rrect_sdf(px - foff, py, face_hx, Hh, max(r * ac, 0.3), r)) * sil
    band = np.clip(sil - face, 0, 1)

    hgt = py / Hh  # -1 頂端, 1 底部
    out = np.zeros(px.shape + (3,), np.float32)

    # 側邊鈦金屬框
    if asn > 0.01:
        side = 1.0 if s > 0 else -1.0
        bx = np.clip((px - foff) * side - face_hx, 0, None) / max(2 * d * asn, 1e-3)
        curve = 0.45 + 0.55 * np.sin(np.pi * np.clip(bx, 0, 1))
        rows = np.clip((py + Hh).astype(np.int32), 0, len(BRUSH) - 1)
        brush = 1.0 + 0.06 * BRUSH[rows]
        lum = (0.30 + 0.35 * (1 - (hgt + 1) / 2)) * curve * brush * (0.6 + 0.6 * asn)
        out += (lum[..., None] * rgb(0.78, 0.74, 0.70)) * band[..., None]

    lx = (px - foff) / max(ac, 0.04)
    ly = py
    aa = 1.0 / max(ac, 0.08)

    if c >= 0:
        col = back_face(lx, ly, Wh, Hh, r, s, t, glint, aa)
    else:
        col = front_face(-lx, ly, Wh, Hh, r, s, t, screen, ai, aa)
    out += col * face[..., None]

    # 輪廓邊光
    rim = sil * np.clip(1 + sil_sdf / 2.5, 0, 1) * (0.25 + 0.35 * np.clip(-hgt, 0, 1))
    out += rim[..., None] * rgb(0.75, 0.82, 1.0)

    reg = img[y0:y1, x0:x1]
    img[y0:y1, x0:x1] = reg * (1 - sil[..., None]) + out


def back_face(lx, ly, Wh, Hh, r, s, t, glint, aa):
    base = rgb(0.045, 0.06, 0.11)
    col = np.broadcast_to(base, lx.shape + (3,)).copy()
    col *= (0.85 + 0.25 * (1 - (ly / Hh + 1) / 2))[..., None]
    sp = (s * 1.6 + glint * 2.2 - 0.6) * Wh
    sheen = np.exp(-(((lx - sp) + 0.35 * ly) / (0.45 * Wh)) ** 2) * 0.22
    col += sheen[..., None] * rgb(0.6, 0.72, 1.0)

    # 相機平台
    pcx, pcy = -0.42 * Wh, -Hh + 0.58 * Wh
    ps = rrect_sdf(lx - pcx, ly - pcy, 0.48 * Wh, 0.48 * Wh, 0.24 * Wh, 0.24 * Wh)
    pm = cover(ps, aa)
    pcol = col * 1.35 + 0.025
    pedge = np.clip(1 + ps / 3.0, 0, 1) * pm * 0.25
    col = col * (1 - pm[..., None]) + pcol * pm[..., None] + pedge[..., None]

    R = 0.17 * Wh
    for ox, oy in ((-0.2, -0.2), (-0.2, 0.2), (0.2, 0.0)):
        col = lens(col, lx - (pcx + ox * Wh), ly - (pcy + oy * Wh), R, s, glint, aa)

    for (ox, oy, rad, cc) in ((0.24, -0.27, 0.055, rgb(0.55, 0.5, 0.38)),
                              (0.24, 0.27, 0.045, rgb(0.03, 0.03, 0.04))):
        dd = np.hypot(lx - (pcx + ox * Wh), ly - (pcy + oy * Wh)) - rad * Wh
        m = cover(dd, aa)
        col = col * (1 - m[..., None]) + cc * m[..., None]
    return col


def lens(col, dx, dy, R, s, glint, aa):
    dist = np.hypot(dx, dy)
    rr = dist / R
    m = cover(dist - R, aa)
    if not m.any():
        return col
    ring = (0.28 + 0.30 * np.clip(-dy / R, -1, 1) * 0.5 + 0.12) * np.ones_like(rr)
    ring = ring[..., None] * rgb(0.80, 0.80, 0.84)
    glass = np.broadcast_to(rgb(0.008, 0.01, 0.018), rr.shape + (3,)).copy()
    glass += (np.exp(-((rr - 0.56) / 0.05) ** 2) * 0.10)[..., None] * rgb(0.25, 0.4, 1.0)
    glass += (np.exp(-((rr - 0.32) / 0.06) ** 2) * 0.08)[..., None] * rgb(0.6, 0.3, 1.0)
    gx, gy = (-0.35 + 0.6 * s + 0.9 * glint) * R, -0.38 * R
    spec = np.exp(-((dx - gx) ** 2 + (dy - gy) ** 2) / (0.13 * R) ** 2)
    glass += (spec * (0.5 + 2.2 * glint))[..., None] * rgb(1.0, 0.97, 0.92)
    spec2 = np.exp(-((dx + 0.3 * R) ** 2 + (dy - 0.3 * R) ** 2) / (0.06 * R) ** 2)
    glass += (spec2 * 0.25)[..., None]
    inner = np.clip((0.80 - rr) * R / aa + 0.5, 0, 1)
    lc = ring * (1 - inner[..., None]) + glass * inner[..., None]
    edge = np.exp(-((rr - 1.0) / 0.04) ** 2) * 0.2
    lc += edge[..., None]
    return col * (1 - m[..., None]) + lc * m[..., None]


def front_face(lx, ly, Wh, Hh, r, s, t, screen, ai, aa):
    col = np.broadcast_to(rgb(0.01, 0.01, 0.012), lx.shape + (3,)).copy()
    inset = 0.05 * Wh
    ss = rrect_sdf(lx, ly, Wh - inset, Hh - inset, r - inset, r - inset)
    sm = cover(ss, aa)

    scr = np.broadcast_to(rgb(0.012, 0.014, 0.02), lx.shape + (3,)).copy()
    refl = np.exp(-(((lx - (s * 2.0 - 0.3) * Wh) + 0.5 * ly) / (0.5 * Wh)) ** 2) * 0.06
    scr += refl[..., None]

    if screen > 0:
        isl_y = -Hh + inset + 0.12 * Wh
        rad = np.hypot(lx, ly - isl_y)
        front = screen * (2.2 * Hh)
        reveal = np.clip((front - rad) / (0.25 * Wh), 0, 1)
        wave = np.exp(-((rad - front) / (0.12 * Wh)) ** 2) * (1 - screen) * 1.6
        wp = np.broadcast_to(rgb(0.02, 0.01, 0.04), lx.shape + (3,)).copy()
        for bx, by, br, bc, ph in ((0.35, -0.45, 1.0, rgb(1.0, 0.42, 0.08), 0.0),
                                   (-0.45, 0.05, 1.1, rgb(0.85, 0.12, 0.55), 1.7),
                                   (0.25, 0.55, 1.2, rgb(0.12, 0.35, 1.0), 3.1)):
                bxx = (bx + 0.08 * math.sin(t * 1.3 + ph)) * Wh
                byy = (by + 0.05 * math.cos(t * 1.1 + ph)) * Hh
                g = np.exp(-((lx - bxx) ** 2 + (ly - byy) ** 2) / (br * Wh) ** 2)
                wp += g[..., None] * bc * 0.95
        scr = scr * (1 - reveal[..., None]) + wp * reveal[..., None]
        scr += wave[..., None] * rgb(0.9, 0.95, 1.0)

    if ai > 0:
        ang = np.arctan2(ly, lx)
        hue = (ang / (2 * np.pi) + t * 0.35) % 1.0
        ring_col = np.stack([0.5 + 0.5 * np.cos(2 * np.pi * (hue + k)) for k in (0.0, 0.33, 0.67)], -1)
        ring_col = ring_col * rgb(1.0, 0.75, 1.0) + rgb(0.1, 0.05, 0.15)
        glow = np.exp(np.minimum(ss, 0) / (0.07 * Wh)) * ai * 0.9
        scr += glow[..., None] * ring_col

    col = col * (1 - sm[..., None]) + scr * sm[..., None]

    isl = rrect_sdf(lx, ly - (-Hh + inset + 0.12 * Wh), 0.19 * Wh, 0.055 * Wh, 0.055 * Wh, 0.055 * Wh)
    im = cover(isl, aa)
    col = col * (1 - im[..., None])
    return col


# ---------- 光效與粒子 ----------

PART = RNG.random((160, 3)).astype(np.float32)
PART_V = (RNG.random((160, 2)).astype(np.float32) - 0.5) * 0.03


def particles(img, t, amount):
    if amount <= 0:
        return
    q = 4
    buf = np.zeros((H // q, W // q, 3), np.float32)
    pos = (PART[:, :2] + PART_V * t * (1 + 2 * PART[:, 2:3])) % 1.0
    xs = (pos[:, 0] * (W // q)).astype(int)
    ys = (pos[:, 1] * (H // q)).astype(int)
    lum = (0.3 + 0.7 * PART[:, 2]) * amount
    for x, y, l, z in zip(xs, ys, lum, PART[:, 2]):
        cv2.circle(buf, (int(x), int(y)), 1 + int(z * 2), (float(l), float(l) * 0.9, float(l) * 0.8), -1)
    buf = cv2.GaussianBlur(buf, (0, 0), 1.5)
    img += cv2.resize(buf, (W, H), interpolation=cv2.INTER_LINEAR) * 0.6


def lens_flare(img, sx, sy, inten):
    """以 OpenCV 畫光暈鬼影, 沿著光源與畫面中心的連線排列."""
    if inten <= 0.01:
        return
    q = 4
    layer = np.zeros((H // q, W // q, 3), np.float32)
    cx, cy = W / 2, H / 2
    ghosts = ((0.6, 18, (0.25, 0.45, 1.0)), (0.2, 34, (0.6, 0.3, 1.0)),
              (-0.3, 12, (1.0, 0.6, 0.2)), (-0.7, 48, (0.2, 0.8, 0.6)),
              (-1.1, 22, (0.4, 0.5, 1.0)))
    for k, rad, color in ghosts:
        gx = cx + (sx - cx) * k
        gy = cy + (sy - cy) * k
        cv2.circle(layer, (int(gx / q), int(gy / q)), rad, tuple(v * 0.12 for v in color), -1)
    cv2.circle(layer, (int(sx / q), int(sy / q)), 10, (1.2, 1.1, 1.0), -1)
    layer = cv2.GaussianBlur(layer, (0, 0), 3)
    star = np.zeros_like(layer)
    cv2.line(star, (0, int(sy / q)), (W // q, int(sy / q)), (0.35, 0.55, 1.0), 2)
    star = cv2.GaussianBlur(star, (0, 0), 2)
    star *= np.exp(-((np.arange(W // q, dtype=np.float32) - sx / q) / (W / q * 0.25)) ** 2)[None, :, None]
    img += cv2.resize(layer + star, (W, H)) * inten


def post(img, t, focus=None):
    if focus is not None:
        fx, fy, r0, r1 = focus
        blur = cv2.GaussianBlur(img, (0, 0), 7)
        dist = np.hypot(XX - fx, YY - fy)
        m = np.clip((dist - r0) / (r1 - r0), 0, 1)[..., None]
        img = img * (1 - m) + blur * m

    q = 4
    small = cv2.resize(np.maximum(img - 0.8, 0), (W // q, H // q), interpolation=cv2.INTER_AREA)
    b1 = cv2.GaussianBlur(small, (0, 0), 4)
    b2 = cv2.GaussianBlur(small, (0, 0), 16)
    lum = small.mean(axis=2)
    streak = cv2.blur(lum, (121, 1))[..., None] * rgb(0.35, 0.55, 1.0)
    img = img + cv2.resize(b1 * 0.7 + b2 * 0.5 + streak * 1.6, (W, H))

    a, b_, c_, d_, e_ = 2.51, 0.03, 2.43, 0.59, 0.14
    x = np.maximum(img * 0.9, 0)
    img = (x * (a * x + b_)) / (x * (c_ * x + d_) + e_)

    vr = ((XX - W / 2) / (W / 2)) ** 2 + ((YY - H / 2) / (H / 2)) ** 2
    img *= (1 - 0.28 * vr)[..., None]
    img += RNG.normal(0, 0.012, (H, W, 1)).astype(np.float32)
    return np.clip(img, 0, 1)


# ---------- 文字 ----------

def text_layer(text, font_file, size, cx, cy, tracking, blur):
    font = ImageFont.truetype(os.path.join(FONT_DIR, font_file), size)
    widths = [font.getlength(ch) for ch in text]
    total = sum(widths) + tracking * (len(text) - 1)
    im = Image.new("L", (W, H), 0)
    dr = ImageDraw.Draw(im)
    x = cx - total / 2
    for ch, w in zip(text, widths):
        dr.text((x, cy), ch, font=font, fill=255, anchor="lm")
        x += w + tracking
    if blur > 0.3:
        im = im.filter(ImageFilter.GaussianBlur(blur))
    return np.asarray(im, np.float32) / 255.0


# ---------- 分鏡 ----------

def bg(level, glow_xy=None, glow=0.0, tint=(0.25, 0.35, 0.7)):
    img = np.full((H, W, 3), level, np.float32)
    if glow_xy is not None and glow > 0:
        gx, gy = glow_xy
        g = np.exp(-((XX - gx) ** 2 + (YY - gy) ** 2) / (0.35 * W) ** 2) * glow
        img += g[..., None] * rgb(*tint)
    return img


def shot_macro(f):
    """相機模組特寫, 緩慢推近, 光線掃過鏡頭."""
    t = f / FPS
    u = clamp01((f - 18) / (70 - 18))
    ph = H * (2.9 + 0.6 * ease_io(u))
    theta = -0.32 + 0.22 * ease_io(u)
    glint = ease(clamp01((f - 42) / 18))
    img = bg(0.01, (W * 0.5, H * 0.5), 0.05)
    Hh = ph / 2
    Wh = Hh * 0.485
    ac = abs(math.cos(theta))
    pcx, pcy = -0.42 * Wh, -Hh + 0.58 * Wh
    tx = W * 0.5 + 40 * (u - 0.5)
    ty = H * 0.5
    d = Hh * 0.042
    cx = tx - (-d * math.sin(theta) + ac * pcx)
    cy = ty - pcy
    particles(img, t, 0.25)
    draw_phone(img, cx, cy, ph, theta, t, glint=glint)
    # 主鏡頭位置當作光暈來源
    R = 0.17 * Wh
    sx = cx - d * math.sin(theta) + ac * (pcx + 0.2 * Wh + (-0.35 + 0.6 * math.sin(theta) + 0.9 * glint) * R)
    sy = cy + pcy - 0.38 * R
    peak = math.exp(-((f - 54) / 6.0) ** 2)
    lens_flare(img, sx, sy, 1.4 * peak)
    return img, (tx, ty, 380, 1100)


def shot_open(f):
    """黑畫面中的一道光線展開, 再上下分開露出特寫."""
    t = f / FPS
    img = bg(0.0)
    L = W * 0.95 * ease_out(t / 0.55)
    taper = np.exp(-((XX - W / 2) / (L / 2 + 1)) ** 6)
    gap = H * 0.5 * ease_io((f - 18) / 12)
    focus = None
    if gap > 0.5:
        macro, focus = shot_macro(f)
        m = cover(np.abs(YY - H / 2) - gap, 2.0)[..., None]
        img = img * (1 - m) + macro * m
    for yc in ({H / 2} if gap <= 0.5 else (H / 2 - gap, H / 2 + gap)):
        core = np.exp(-((YY - yc) / 1.6) ** 2) * 2.2
        halo = np.exp(-((YY - yc) / 45) ** 2) * 0.18
        fade = 1 - ease(gap / (H * 0.5))
        line = (core + halo) * taper * min(1.0, t / 0.15) * fade
        img += line[..., None] * rgb(0.75, 0.86, 1.0)
    particles(img, t, 0.35)
    return img, focus


def shot_turn(f, sub=0.0):
    """手機由背面轉到正面, 同時拉遠, 螢幕點亮."""
    ff = f + sub
    t = ff / FPS
    u = clamp01((ff - 70) / (100 - 70))
    theta = -0.35 + (math.pi + 0.35) * ease_io(u)
    ph = H * (1.7 - 0.92 * ease_out(u))
    screen = clamp01((ff - IMPACT_F) / 12)
    ai = ease(clamp01((ff - IMPACT_F - 4) / 10))
    img = bg(0.012, (W / 2, H / 2), 0.10 + 0.25 * ease(screen))
    particles(img, t, 0.15)
    draw_phone(img, W / 2, H / 2, ph, theta, t, screen=ease_out(screen) if screen > 0 else 0.0,
               glint=0.3 * u, ai=ai)
    return img


def shot_title(f):
    t = f / FPS
    u = ease_io((f - TITLE_F) / 16)
    cx = W * (0.5 - 0.17 * u)
    ph = H * (0.78 - 0.04 * u)
    theta = math.pi - 0.22 * u
    img = bg(0.012, (cx, H / 2), 0.35 - 0.1 * u)
    particles(img, t, 0.12)
    draw_phone(img, cx, H / 2, ph, theta, t, screen=1.0, ai=1.0)

    a1 = ease((f - TITLE_F - 9) / 14)
    if a1 > 0:
        m = text_layer("iPhone 17", "segoeuisl.ttf", 150, W * 0.67, H * 0.46,
                       28 * (1 - a1) + 2, 14 * (1 - a1))
        grad = (1.0 - 0.22 * np.clip((YY - (H * 0.46 - 75)) / 150, 0, 1))[..., None]
        shine_x = W * (0.45 + 0.5 * clamp01((f - 128) / 18))
        shine = np.exp(-((XX - shine_x + 0.3 * (YY - H * 0.46)) / 60) ** 2)[..., None] * 0.9
        col = rgb(0.96, 0.97, 1.0) * grad + shine
        img = img * (1 - m[..., None] * a1) + col * (m[..., None] * a1)
    a2 = ease((f - TITLE_F - 18) / 12)
    if a2 > 0:
        m = text_layer("Intelligence, forged in light.", "segoeuil.ttf", 46, W * 0.67, H * 0.58,
                       4 + 6 * (1 - a2), 6 * (1 - a2))
        img = img * (1 - m[..., None] * a2) + rgb(0.62, 0.66, 0.75) * (m[..., None] * a2)
    return img


def render(f):
    t = f / FPS
    focus = None
    if f < 30:
        img, focus = shot_open(f)
    elif f < 70:
        img, focus = shot_macro(f)
        flash = math.exp(-((f - 69) / 2.2) ** 2)
        img += flash * 0.9
    elif f < TITLE_F:
        if 76 <= f <= 94:
            img = sum(shot_turn(f, s) for s in (-0.33, 0.0, 0.33)) / 3
        else:
            img = shot_turn(f)
        flash = math.exp(-((f - 70) / 2.5) ** 2) * 0.9 + math.exp(-((f - IMPACT_F) / 2.0) ** 2) * 0.5
        img += flash
    else:
        img = shot_title(f)
    out = post(img, t, focus)
    return (out * 255 + 0.5).astype(np.uint8)


# ---------- 音訊 ----------

def lp(x, fc):
    """一階低通, fc 可為隨時間變化的陣列."""
    fc = np.broadcast_to(np.asarray(fc, np.float64), x.shape)
    a = np.exp(-2 * np.pi * fc / SR).tolist()
    xs = x.tolist()
    y = [0.0] * len(xs)
    z = 0.0
    for i, v in enumerate(xs):
        z = v + a[i] * (z - v)
        y[i] = z
    return np.array(y)


def env(t, t0, attack, decay):
    x = t - t0
    e = np.where(x < 0, 0.0, np.where(x < attack, x / max(attack, 1e-4), np.exp(-(x - attack) / decay)))
    return e


def sweep_sine(t, t0, f_hi, f_lo, k):
    x = np.clip(t - t0, 0, None)
    freq = f_lo + (f_hi - f_lo) * np.exp(-x / k)
    return np.sin(2 * np.pi * np.cumsum(freq) / SR)


def saw(t, f):
    return 2 * ((t * f) % 1.0) - 1


def reverb(x, seconds=1.8, decay=0.45, seed=0):
    n = int(SR * seconds)
    rng = np.random.default_rng(seed)
    ir = rng.standard_normal(n) * np.exp(-np.arange(n) / (SR * decay))
    ir /= np.sqrt((ir ** 2).sum())
    size = 1 << int(np.ceil(np.log2(len(x) + n)))
    y = np.fft.irfft(np.fft.rfft(x, size) * np.fft.rfft(ir, size), size)[:len(x)]
    return y


def build_audio():
    n = int(SR * DUR)
    t = np.arange(n) / SR
    noise = RNG.standard_normal(n)
    dry = np.zeros((2, n))
    wet = np.zeros(n)

    def gate(a, b, fade=0.01):
        return np.clip((t - a) / fade, 0, 1) * np.clip((b - t) / fade, 0, 1)

    # 0 - 1s: 光線出現, 低頻上升
    g = gate(0.0, 1.0, 0.02)
    rise = lp(noise, 150 * (40 ** np.clip(t / 1.0, 0, 1))) * (np.clip(t, 0, 1) ** 2.5) * 0.9 * g
    sub = np.sin(2 * np.pi * np.cumsum(40 + 70 * np.clip(t, 0, 1) ** 2) / SR) * np.clip(t, 0, 1) ** 2 * 0.35 * g
    dry += rise + sub

    # 0.55 - 1.0s: 光線分開的 whoosh
    wsh = lp(noise, 300 + 6000 * np.exp(-((t - 0.85) / 0.12) ** 2)) - lp(noise, 200)
    dry += wsh * np.exp(-((t - 0.85) / 0.13) ** 2) * 1.4

    # 1.0s: 進入特寫的重拍
    kick = sweep_sine(t, 1.0, 140, 46, 0.035) * env(t, 1.0, 0.002, 0.45) * 0.9
    click = np.diff(noise, prepend=0) * env(t, 1.0, 0.0005, 0.006) * 0.25
    dry += kick + click

    # 1.0 - 3.1s: 脈動低音, 襯底和弦, hi-hat
    g2 = gate(1.0, 3.1, 0.015)
    step = 0.25
    bass = np.zeros(n)
    for k in range(int((3.1 - 1.0) / step) + 1):
        t0 = 1.0 + k * step
        bass += env(t, t0, 0.004, 0.14)
    bass_sig = lp(saw(t, 55.0), 380) * bass * 0.55 * g2
    dry += bass_sig
    hats = np.zeros(n)
    for k in range(int((3.1 - 1.5) / 0.125) + 1):
        t0 = 1.5 + k * 0.125
        hats += env(t, t0, 0.001, 0.025) * (0.5 + 0.5 * (k % 2 == 0))
    hat_sig = np.diff(np.diff(noise, prepend=0), prepend=0) * hats * 0.05 * g2
    dry[0] += hat_sig * 0.7
    dry[1] += hat_sig * 1.0

    chord = (110.0, 164.81, 207.65, 246.94, 277.18)
    pad_l = sum(saw(t, f * 1.003) for f in chord)
    pad_r = sum(saw(t, f * 0.997) for f in chord)
    pad_amp1 = np.clip((t - 1.0) / 1.5, 0, 1) * g2 * 0.05
    pad_lf = lp(pad_l, 900) * pad_amp1
    pad_rf = lp(pad_r, 900) * pad_amp1
    dry[0] += pad_lf
    dry[1] += pad_rf
    wet += (pad_lf + pad_rf) * 0.5

    # 1.73s: 光掃過鏡頭的閃光音
    chime = np.zeros(n)
    for fr, amp in ((1760, 1.0), (2637, 0.6), (3520, 0.35), (5274, 0.2)):
        chime += np.sin(2 * np.pi * fr * t) * amp * env(t, 1.75, 0.003, 0.35)
    dry += chime * 0.07
    wet += chime * 0.18

    # 2.4 - 3.1s: 第二段上升, 3.1 - 3.23s 留白
    g3 = gate(2.4, 3.1, 0.012)
    r2 = np.clip((t - 2.4) / 0.7, 0, 1)
    rise2 = lp(noise, 400 * (25 ** r2)) * r2 ** 2 * 0.8 * g3
    tone = lp(np.sin(2 * np.pi * np.cumsum(110 * (4 ** r2)) / SR), 3000) * r2 ** 3 * 0.18 * g3
    dry += rise2 + tone

    # 3.23s: 螢幕點亮的主重擊
    ti = IMPACT_F / FPS
    boom = sweep_sine(t, ti, 160, 34, 0.05) * env(t, ti, 0.002, 0.9) * 1.0
    burst = lp(noise, 2500) * env(t, ti, 0.001, 0.22) * 0.8
    ring = sum(np.sin(2 * np.pi * 196 * p * t) * a for p, a in ((1, 1), (2.76, 0.6), (5.40, 0.35), (8.93, 0.2)))
    ring = ring * env(t, ti, 0.001, 0.9) * 0.10
    dry += boom + burst + ring
    wet += burst * 0.5 + ring * 2.0

    pad_amp2 = env(t, ti, 0.25, 3.0) * 0.065 * np.clip((DUR - t) / 0.6, 0, 1)
    pl2 = lp(sum(saw(t, f * 2 * 1.002) for f in chord) + pad_l, 3500) * pad_amp2
    pr2 = lp(sum(saw(t, f * 2 * 0.998) for f in chord) + pad_r, 3500) * pad_amp2
    dry[0] += pl2
    dry[1] += pr2
    wet += (pl2 + pr2) * 0.6

    # 3.73s 與 4.07s: 標題出現的鐘聲
    bell = np.zeros(n)
    for t0, base in ((TITLE_F / FPS, 880.0), ((TITLE_F + 10) / FPS, 1108.73)):
        for p, a in ((1, 1.0), (1.5, 0.45), (2, 0.35), (3.01, 0.15)):
            bell += np.sin(2 * np.pi * base * p * t) * a * env(t, t0, 0.004, 0.6)
    dry += bell * 0.06
    wet += bell * 0.2

    wl = reverb(wet, seed=1)
    wr = reverb(wet, seed=2)
    mix = dry + 0.55 * np.stack([wl, wr])
    mix = np.tanh(mix * 1.1)
    mix *= np.clip((DUR - t) / 0.25, 0, 1)
    mix /= np.abs(mix).max() / 0.89
    return mix.astype(np.float32)


# ---------- 輸出 ----------

def encode(path):
    audio = build_audio()
    out = av.open(path, "w")
    vs = out.add_stream("libx264", rate=FPS)
    vs.width, vs.height, vs.pix_fmt = W, H, "yuv420p"
    vs.options = {"crf": "16", "preset": "slow"}
    as_ = out.add_stream("aac", rate=SR, layout="stereo")
    as_.bit_rate = 256000

    chunk = 1024
    a_pos = 0
    for f in range(N):
        frame = av.VideoFrame.from_ndarray(render(f), format="rgb24")
        for p in vs.encode(frame):
            out.mux(p)
        target = int((f + 1) / FPS * SR)
        while a_pos < target:
            seg = audio[:, a_pos:a_pos + chunk]
            if seg.shape[1] < chunk:
                seg = np.pad(seg, ((0, 0), (0, chunk - seg.shape[1])))
            af = av.AudioFrame.from_ndarray(np.ascontiguousarray(seg), format="fltp", layout="stereo")
            af.sample_rate = SR
            af.pts = a_pos
            for p in as_.encode(af):
                out.mux(p)
            a_pos += chunk
        print(f"\rframe {f + 1}/{N}", end="", flush=True)
    for p in vs.encode():
        out.mux(p)
    for p in as_.encode():
        out.mux(p)
    out.close()
    print()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        os.makedirs(os.path.join(HERE, "check"), exist_ok=True)
        for a in sys.argv[1:]:
            f = int(a)
            Image.fromarray(render(f)).save(os.path.join(HERE, "check", f"f{f:03d}.png"))
            print("saved", f)
    else:
        encode(os.path.join(HERE, "iphone17.mp4"))
