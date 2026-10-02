"""30 秒 ASRock X870E Taichi 概念廣告, 純程式產生畫面與音訊.

用法:
    python render.py               輸出 taichi.mp4
    python render.py 60 150 300    只輸出指定影格的 PNG 到 check/
"""
import math
import os
import sys
from multiprocessing import Pool

import av
import cv2
import numpy as np
from PIL import Image, ImageDraw

import board as B
from audio import build_audio, SR

W, H = 1920, 1080
FPS = 30
DUR = 30.0
N = int(FPS * DUR)
HERE = os.path.dirname(os.path.abspath(__file__))
WORKERS = 12

YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)
GOLD_HDR = np.array([1.0, 0.74, 0.40], np.float32)


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


# ---------- 素材, 每個 worker 各自建立一次 ----------

ASSETS = {}


def assets():
    if not ASSETS:
        ASSETS["base"] = B.pyramid(B.build_base(), 4)
        ASSETS["tops"] = {k: (B.pyramid(f, 4), B.pyramid(e, 4)) for k, (f, e) in B.build_tops().items()}
        ASSETS["noise"] = np.random.default_rng(5)
    return ASSETS


# ---------- 相機 ----------

class Cam:
    def __init__(self, target, dist, az, el, fov):
        tx, ty, th = target
        self.target = np.array([tx, ty, -th], np.float64)
        self.eye = self.target + dist * np.array([math.sin(az) * math.cos(el), math.cos(az) * math.cos(el),
                                                   -math.sin(el)])
        fwd = self.target - self.eye
        fwd /= np.linalg.norm(fwd)
        up = np.array([0, 0, -1.0]) if el < 1.45 else np.array([0, -1.0, 0])
        right = np.cross(fwd, up)
        right /= np.linalg.norm(right)
        up2 = np.cross(right, fwd)
        self.R = np.stack([right, -up2, fwd])
        self.f = (W / 2) / math.tan(math.radians(fov) / 2)

    def proj(self, pts):
        """pts: (N, 3) 的 (x, y, h) mm. 回傳 (N, 2) 螢幕座標與深度."""
        p = np.asarray(pts, np.float64)
        w = np.stack([p[:, 0], p[:, 1], -p[:, 2]], 1)
        c = (w - self.eye) @ self.R.T
        z = c[:, 2]
        xy = np.stack([self.f * c[:, 0] / z + W / 2, self.f * c[:, 1] / z + H / 2], 1)
        return xy, z


def bbox(pts, pad=2):
    x0 = max(int(math.floor(pts[:, 0].min())) - pad, 0)
    y0 = max(int(math.floor(pts[:, 1].min())) - pad, 0)
    x1 = min(int(math.ceil(pts[:, 0].max())) + pad, W)
    y1 = min(int(math.ceil(pts[:, 1].max())) + pad, H)
    return x0, y0, x1, y1


def poly_fill(img, pts, color, alpha=1.0):
    x0, y0, x1, y1 = bbox(pts)
    if x1 <= x0 or y1 <= y0:
        return None
    m = np.zeros((y1 - y0, x1 - x0), np.uint8)
    p = np.round((pts - [x0, y0]) * 16).astype(np.int32)
    cv2.fillPoly(m, [p], 255, cv2.LINE_AA, shift=4)
    a = (m.astype(np.float32) / 255 * alpha)[..., None]
    reg = img[y0:y1, x0:x1]
    reg *= 1 - a
    reg += np.asarray(color, np.float32) * a
    return x0, y0, a[..., 0]


def line_add(img, p0, p1, color, th=2):
    pts = np.array([p0, p1], np.float32)
    x0, y0, x1, y1 = bbox(pts, th + 2)
    if x1 <= x0 or y1 <= y0:
        return
    m = np.zeros((y1 - y0, x1 - x0), np.uint8)
    a = tuple(int((v - o) * 16) for v, o in zip(p0, (x0, y0)))
    b = tuple(int((v - o) * 16) for v, o in zip(p1, (x0, y0)))
    cv2.line(m, a, b, 255, th, cv2.LINE_AA, shift=4)
    img[y0:y1, x0:x1] += (m.astype(np.float32) / 255)[..., None] * np.asarray(color, np.float32)


def warp_plane(img, metal, cam, tex_levels, rect_mm, h, metal_k, emis_levels=None, emis_col=None):
    """把某個平面貼圖以透視投影貼到畫面上 (預乘 alpha 或不透明 RGB)."""
    x0m, y0m, x1m, y1m = rect_mm
    corners = np.array([[x0m, y0m, h], [x1m, y0m, h], [x1m, y1m, h], [x0m, y1m, h]])
    dst, z = cam.proj(corners)
    if (z < 5).any():
        return
    bx0, by0, bx1, by1 = bbox(dst)
    if bx1 <= bx0 or by1 <= by0:
        return
    # 依縮小倍率選 mip 層級
    tw0 = tex_levels[0].shape[1]
    span = np.linalg.norm(dst[1] - dst[0]) + np.linalg.norm(dst[2] - dst[1])
    tspan = tex_levels[0].shape[1] + tex_levels[0].shape[0]
    ratio = tspan / max(span, 1.0)
    lvl = int(np.clip(math.floor(math.log2(max(ratio, 1.0))), 0, len(tex_levels) - 1))
    tex = tex_levels[lvl]
    th_, tw_ = tex.shape[:2]
    src = np.array([[0, 0], [tw_, 0], [tw_, th_], [0, th_]], np.float32)
    M = cv2.getPerspectiveTransform(src, (dst - [bx0, by0]).astype(np.float32))
    if emis_levels is not None and emis_col is not None:
        tex = tex.copy()
        tex[..., :3] += emis_levels[lvl][..., None] * emis_col
    out = cv2.warpPerspective(tex, M, (bx1 - bx0, by1 - by0), flags=cv2.INTER_LINEAR,
                              borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    reg = img[by0:by1, bx0:bx1]
    if out.shape[2] == 4:
        a = out[..., 3:4]
        reg *= 1 - a
        reg += out[..., :3]
        mreg = metal[by0:by1, bx0:bx1]
        mreg *= 1 - a[..., 0]
        mreg += a[..., 0] * metal_k
    else:
        mask = cv2.warpPerspective(np.ones((th_, tw_), np.float32), M, (bx1 - bx0, by1 - by0),
                                   flags=cv2.INTER_LINEAR)[..., None]
        reg *= 1 - mask
        reg += out * mask


SIDE_SHADE = {(-1, 0): 0.45, (1, 0): 0.85, (0, -1): 0.35, (0, 1): 0.65}


def draw_object(img, metal, cam, o, A, emis_col):
    x0, y0, x1, y1 = o["rect"]
    h = o["h"]
    eye = cam.eye
    side_col = np.array(o["side"], np.float32) / 255
    faces = (((-1, 0), [(x0, y1), (x0, y0)]), ((1, 0), [(x1, y0), (x1, y1)]),
             ((0, -1), [(x0, y0), (x1, y0)]), ((0, 1), [(x1, y1), (x0, y1)]))
    for (nx, ny), ((ax, ay), (bx, by)) in faces:
        cxm, cym = (ax + bx) / 2, (ay + by) / 2
        to_eye = (eye[0] - cxm) * nx + (eye[1] - cym) * ny
        if to_eye <= 0:
            continue
        quad = np.array([[ax, ay, 0], [bx, by, 0], [bx, by, h], [ax, ay, h]])
        pts, z = cam.proj(quad)
        if (z < 5).any():
            return
        res = poly_fill(img, pts, side_col * SIDE_SHADE[(nx, ny)])
        if res is not None:
            sx, sy, a = res
            mreg = metal[sy:sy + a.shape[0], sx:sx + a.shape[1]]
            mreg *= 1 - a
            mreg += a * o["metal"] * 0.5
        line_add(img, pts[2], pts[3], (0.22, 0.22, 0.24), 2)
        if h >= 20:
            for fr in (0.2, 0.4, 0.6, 0.8):
                g, _ = cam.proj(np.array([[ax, ay, h * fr], [bx, by, h * fr]]))
                line_add(img, g[0], g[1], (-0.05, -0.05, -0.05), 3)
                line_add(img, g[0] + [0, 2], g[1] + [0, 2], (0.05, 0.05, 0.055), 1)
    if o["kind"] == "tex":
        lv, el = A["tops"][o["name"]]
        warp_plane(img, metal, cam, lv, o["rect"], h, o["metal"], el, emis_col)
    else:
        quad = np.array([[x0, y0, h], [x1, y0, h], [x1, y1, h], [x0, y1, h]])
        pts, z = cam.proj(quad)
        if (z < 5).any():
            return
        res = poly_fill(img, pts, np.array(o["top"], np.float32) / 255)
        if res is not None:
            sx, sy, a = res
            mreg = metal[sy:sy + a.shape[0], sx:sx + a.shape[1]]
            mreg *= 1 - a
            mreg += a * o["metal"]
    if o.get("gold"):
        quad = np.array([[x0, y0, h], [x1, y0, h], [x1, y1, h], [x0, y1, h]])
        pts, _ = cam.proj(quad)
        for k in range(4):
            line_add(img, pts[k], pts[(k + 1) % 4], GOLD_HDR * 0.55, 2)


def draw_traces(img, cam, t, amount, speed=90.0):
    """沿 PCB 走線跑的資料脈衝."""
    if amount <= 0:
        return
    layer = np.zeros((H, W), np.uint8)
    for i, tr in enumerate(B.TRACES):
        pts = np.array(tr, np.float64)
        seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
        L = seg.sum()
        cum = np.concatenate([[0], np.cumsum(seg)])
        head = ((t * speed + i * 37.0) % (L + 40)) - 5
        tail = 18.0
        ss = np.linspace(max(head - tail, 0), min(head, L), 12)
        if ss[-1] <= ss[0]:
            continue
        xs = np.interp(ss, cum, pts[:, 0])
        ys = np.interp(ss, cum, pts[:, 1])
        sp, z = cam.proj(np.stack([xs, ys, np.full_like(xs, 0.2)], 1))
        if (z < 5).any():
            continue
        p = np.round(sp * 16).astype(np.int32)
        for k in range(len(p) - 1):
            v = int(255 * (k + 1) / len(p))
            cv2.line(layer, tuple(p[k]), tuple(p[k + 1]), v, 2, cv2.LINE_AA, shift=4)
    f = layer.astype(np.float32) / 255
    glow = cv2.GaussianBlur(f, (0, 0), 6)
    img += (f * 2.2 + glow * 3.0)[..., None] * np.array([0.35, 0.75, 1.0], np.float32) * amount


def draw_hud(img, cam, t, amount):
    """插槽周圍的全息 HUD 圓環."""
    if amount <= 0:
        return
    layer = np.zeros((H, W), np.uint8)
    cx, cy = B.SOCKET_C
    for r, dash, spd in ((40, 48, 0.4), (46, 96, -0.25), (52, 12, 0.15)):
        for k in range(dash):
            if k % 2:
                continue
            a0 = 2 * math.pi * k / dash + t * spd
            a1 = 2 * math.pi * (k + 0.8) / dash + t * spd
            aa = np.linspace(a0, a1, 6)
            pts3 = np.stack([cx + r * np.cos(aa), cy + r * np.sin(aa), np.full(6, 4.5)], 1)
            sp, z = cam.proj(pts3)
            if (z < 5).any():
                continue
            cv2.polylines(layer, [np.round(sp * 16).astype(np.int32)], False, 255, 2, cv2.LINE_AA, shift=4)
    ang = t * 2.2
    p3 = np.array([[cx + 40 * math.cos(ang), cy + 40 * math.sin(ang), 4.5],
                   [cx + 58 * math.cos(ang), cy + 58 * math.sin(ang), 4.5]])
    sp, z = cam.proj(p3)
    if (z > 5).all():
        cv2.line(layer, tuple(np.round(sp[0] * 16).astype(int)), tuple(np.round(sp[1] * 16).astype(int)),
                 255, 3, cv2.LINE_AA, shift=4)
    f = layer.astype(np.float32) / 255
    img += (f * 1.2 + cv2.GaussianBlur(f, (0, 0), 5) * 1.5)[..., None] * GOLD_HDR * amount


def draw_board(img, cam, t, traces=0.0, hud=0.0, argb=0.6, sweep=None):
    A = assets()
    metal = np.zeros((H, W), np.float32)
    warp_plane(img, metal, cam, A["base"], (0, 0, B.BW_MM, B.BH_MM), 0.0, 0.0)
    draw_traces(img, cam, t, traces)
    hue = t * 0.25
    emis_col = np.array([0.5 + 0.5 * math.cos(2 * math.pi * (hue + k)) for k in (0.0, 0.33, 0.67)],
                        np.float32) * np.array([1.0, 0.7, 1.0], np.float32) * 2.2 * argb
    order = sorted(B.OBJECTS, key=lambda o: -np.linalg.norm(
        cam.eye - np.array([(o["rect"][0] + o["rect"][2]) / 2, (o["rect"][1] + o["rect"][3]) / 2, -o["h"] / 2])))
    for o in order:
        draw_object(img, metal, cam, o, A, emis_col)
    draw_hud(img, cam, t, hud)
    if sweep is not None:
        pos, inten = sweep
        band = np.exp(-(((XX + 0.45 * YY) - pos) / 140.0) ** 2)
        img += (band * metal * inten)[..., None] * np.array([1.0, 0.95, 0.88], np.float32)


# ---------- 背景, 粒子, 文字 ----------

PART = np.random.default_rng(9).random((220, 3)).astype(np.float32)
PART_V = (np.random.default_rng(10).random((220, 2)).astype(np.float32) - 0.5) * 0.025


def background(glow=0.12, tint=(0.25, 0.32, 0.55), cy=0.55):
    img = np.full((H, W, 3), 0.008, np.float32)
    g = np.exp(-((XX - W / 2) ** 2 + (YY - H * cy) ** 2) / (0.45 * W) ** 2) * glow
    img += g[..., None] * np.array(tint, np.float32)
    return img


def particles(img, t, amount, color=(1.0, 0.85, 0.6)):
    if amount <= 0:
        return
    q = 4
    buf = np.zeros((H // q, W // q), np.float32)
    pos = (PART[:, :2] + PART_V * t * (1 + 2 * PART[:, 2:3])) % 1.0
    for (x, y), z in zip(pos, PART[:, 2]):
        cv2.circle(buf, (int(x * W / q), int(y * H / q)), 1 + int(z * 2), float(0.3 + 0.7 * z), -1)
    buf = cv2.GaussianBlur(buf, (0, 0), 1.5)
    img += cv2.resize(buf, (W, H))[..., None] * np.array(color, np.float32) * 0.5 * amount


def text_mask(text, size, weight="Bold", tracking=0.0):
    f = B.font(size, weight)
    widths = [f.getlength(c) for c in text]
    tw = int(sum(widths) + tracking * (len(text) - 1)) + 10
    th = int(size * 1.5)
    im = Image.new("L", (tw, th), 0)
    d = ImageDraw.Draw(im)
    x = 5
    for c, w in zip(text, widths):
        d.text((x, th * 0.5), c, font=f, fill=255, anchor="lm")
        x += w + tracking
    return np.asarray(im, np.float32) / 255


def put_text(img, text, x, y, size, color, alpha=1.0, weight="Bold", tracking=0.0, anchor="l",
             reveal=1.0, rise=0.0, shine=None):
    """在畫面上合成文字. reveal 由下往上的遮罩露出比例, rise 為向上位移像素."""
    if alpha <= 0.002:
        return
    m = text_mask(text, size, weight, tracking)
    th, tw = m.shape
    if anchor == "c":
        x0 = int(x - tw / 2)
    elif anchor == "r":
        x0 = int(x - tw)
    else:
        x0 = int(x)
    y0 = int(y - th / 2 + rise)
    if reveal < 1.0:
        cut = int(th * (1 - reveal))
        m = m.copy()
        m[:cut] = 0
        m = np.roll(m, -int(th * 0.4 * (1 - reveal)), axis=0)
    xa, ya = max(x0, 0), max(y0, 0)
    xb, yb = min(x0 + tw, W), min(y0 + th, H)
    if xb <= xa or yb <= ya:
        return
    mm = m[ya - y0:yb - y0, xa - x0:xb - x0][..., None] * alpha
    col = np.broadcast_to(np.asarray(color, np.float32), mm.shape[:2] + (3,)).copy()
    if shine is not None:
        gx = np.arange(xa, xb, dtype=np.float32)[None, :]
        gy = np.arange(ya, yb, dtype=np.float32)[:, None]
        col += (np.exp(-((gx + 0.4 * gy - shine) / 70) ** 2) * 1.4)[..., None]
    reg = img[ya:yb, xa:xb]
    reg *= 1 - mm
    reg += col * mm


def bar(img, x, y, w, h, color, alpha=1.0):
    if w <= 0 or alpha <= 0:
        return
    x0, x1 = int(max(x, 0)), int(min(x + w, W))
    if x1 <= x0:
        return
    img[int(y):int(y + h), x0:x1] = img[int(y):int(y + h), x0:x1] * (1 - alpha) + np.asarray(color) * alpha


def scrim(img, yc, anchor, amount):
    """字卡後方的暗色漸層, 讓文字在機板上仍清楚."""
    if amount <= 0:
        return
    y0, y1 = int(max(yc - 300, 0)), int(min(yc + 300, H))
    xs = np.arange(W, dtype=np.float32)
    d = xs if anchor == "l" else (W - xs) if anchor == "r" else np.abs(xs - W / 2) * 1.6
    hm = np.clip(1 - d / 1150, 0, 1) ** 1.2
    vm = np.exp(-((np.arange(y0, y1, dtype=np.float32) - yc) / 200) ** 4)
    img[y0:y1] *= (1 - amount * vm[:, None] * hm[None, :])[..., None]


def caption(img, t, t0, title, sub, x, y, size=120, title_col=None, anchor="l"):
    """常用的兩行字卡: 大標題加說明, 進場時由下往上露出, 離場淡出."""
    a_in = ease_out((t - t0) / 0.45)
    a_sub = ease_out((t - t0 - 0.2) / 0.45)
    scrim(img, y + size * 0.4, anchor, 0.93 * ease_out((t - t0 + 0.2) / 0.5))
    title_col = GOLD_HDR * 1.05 if title_col is None else title_col
    put_text(img, title, x, y, size, title_col, alpha=a_in, weight="Bold", tracking=4,
             anchor=anchor, reveal=a_in, rise=30 * (1 - a_in))
    bw = 160 * ease_out((t - t0 - 0.1) / 0.5)
    bx = x if anchor == "l" else x - bw / 2
    bar(img, bx, y + size * 0.62, bw, 4, GOLD_HDR, a_in)
    put_text(img, sub, x, y + size * 0.62 + 46, 36, (0.86, 0.87, 0.9), alpha=a_sub, weight="SemiLight",
             tracking=10, anchor=anchor, rise=16 * (1 - a_sub))


# ---------- 分鏡 ----------

def shot_intro(t):
    img = background(0.10, (0.5, 0.36, 0.2), 0.5)
    particles(img, t, 0.5)
    layer = np.zeros((H, W, 3), np.uint8)
    far = np.zeros((H, W, 3), np.uint8)
    zoom = 1 + 6 * ease_in((t - 3.25) / 0.75)
    cx, cy = W / 2, H * 0.45

    def g(x, y, r, teeth, rot, th, col, delay, dst):
        reveal = ease_out((t - delay) / 1.6)
        if reveal <= 0:
            return
        X = cx + (x - cx) * zoom
        Y = cy + (y - cy) * zoom
        R = r * zoom
        poly = B.gear_poly(X, Y, R, teeth, rot)
        k = max(int(len(poly) * reveal), 2)
        cv2.polylines(dst, [np.round(poly[:k] * 16).astype(np.int32)], reveal >= 1, col, th, cv2.LINE_AA, shift=4)
        for rr in (0.62, 0.22):
            cv2.ellipse(dst, (int(X * 16), int(Y * 16)), (int(R * rr * 16), int(R * rr * 16)), 0, 0,
                        360 * reveal, col, th, cv2.LINE_AA, shift=4)
        if reveal > 0.6:
            for s in range(6):
                a = rot + 2 * math.pi * s / 6
                p0 = (int((X + R * 0.22 * math.cos(a)) * 16), int((Y + R * 0.22 * math.sin(a)) * 16))
                p1 = (int((X + R * 0.62 * math.cos(a)) * 16), int((Y + R * 0.62 * math.sin(a)) * 16))
                cv2.line(dst, p0, p1, col, th, cv2.LINE_AA, shift=4)

    w1 = 0.35 * t
    g(cx, cy, 230, 24, w1, 3, (255, 255, 255), 0.0, layer)
    g(cx + 230 + 128, cy - 20, 140, 14, -w1 * 24 / 14 + 0.11, 3, (255, 255, 255), 0.35, layer)
    g(cx - 230 - 86, cy + 60, 96, 10, -w1 * 24 / 10 + 0.2, 2, (255, 255, 255), 0.6, layer)
    g(cx - 420, cy - 260, 380, 40, w1 * 0.4, 2, (255, 255, 255), 0.2, far)
    g(cx + 520, cy + 300, 300, 32, -w1 * 0.5, 2, (255, 255, 255), 0.45, far)
    near = layer.astype(np.float32)[..., 0] / 255
    farf = cv2.GaussianBlur(far.astype(np.float32)[..., 0] / 255, (0, 0), 6)
    lum = near * 1.6 + farf * 0.5 + cv2.GaussianBlur(near, (0, 0), 8) * 0.8
    img += lum[..., None] * GOLD_HDR
    a = ease((t - 1.1) / 0.6) * (1 - ease((t - 3.2) / 0.3))
    put_text(img, "EVERY DETAIL. ENGINEERED.", W / 2, H * 0.84, 40, (0.9, 0.9, 0.92), alpha=a,
             weight="SemiLight", tracking=18 - 6 * ease_out((t - 1.1) / 2), anchor="c")
    img += ease_in((t - 3.6) / 0.4) * 1.4
    return img, None


def shot_vrm(t):
    u = (t - 4) / 4
    cam = Cam((62 + 88 * ease_io(u), 24, 14), 240 - 20 * u, -0.42 + 0.3 * u, 0.6, 26)
    img = background(0.06)
    draw_board(img, cam, t, argb=0.8, sweep=(-600 + 3400 * ease_io(clamp01((t - 4.6) / 2.6)), 0.9))
    particles(img, t, 0.25)
    caption(img, t, 4.7, "24+2+1 PHASE", "110A SPS POWER STAGES", W - 130, H * 0.16, 112, anchor="r")
    return img, (W / 2, H / 2, 420, 1100)


def shot_socket(t):
    u = (t - 8) / 4
    cam = Cam((105, 85, 2), 270 - 60 * ease_io(u), -0.7 + 0.9 * u, 1.05 - 0.12 * u, 30)
    img = background(0.05)
    draw_board(img, cam, t, hud=ease((t - 8.4) / 0.8), argb=0.5,
               sweep=(-400 + 3000 * ease_io(clamp01((t - 8.8) / 2.4)), 1.0))
    particles(img, t, 0.2)
    caption(img, t, 8.9, "AMD SOCKET AM5", "READY FOR RYZEN 9000 SERIES", W - 130, H * 0.74, 96, anchor="r")
    return img, (W / 2, H / 2, 480, 1150)


def shot_dimm(t):
    u = (t - 12) / 2
    cam = Cam((176, 92 + 26 * u, 4), 250, 0.95 - 0.25 * u, 0.58, 30)
    img = background(0.05, (0.2, 0.4, 0.7))
    draw_board(img, cam, t, traces=1.0, argb=0.6)
    caption(img, t, 12.3, "DDR5", "NEXT-GEN MEMORY, UNLEASHED", 130, H * 0.72, 120)
    return img, (W / 2, H / 2, 450, 1150)


def shot_pcie(t):
    u = (t - 14) / 2
    cam = Cam((92 + 34 * u, 176, 6), 235, -0.3 + 0.18 * u, 0.72, 30)
    img = background(0.05, (0.2, 0.4, 0.7))
    draw_board(img, cam, t, traces=1.0, argb=0.6, sweep=(-500 + 3200 * ease_io(u), 0.8))
    caption(img, t, 14.3, "PCIe 5.0", "x16 GRAPHICS  ·  BLAZING M.2", W - 130, H * 0.16, 112, anchor="r")
    return img, (W / 2, H / 2, 450, 1150)


def shot_connect(t):
    u = (t - 16) / 4
    cam = Cam((40, 82, 22), 300 - 50 * u, 1.35 - 0.25 * u, 0.5, 32)
    img = background(0.08, (0.2, 0.35, 0.8))
    draw_board(img, cam, t, argb=1.0)
    img *= 0.5
    # 由背板 I/O 射出的光流
    q = 2
    lay = np.zeros((H // q, W // q), np.float32)
    rng = np.random.default_rng(int(t * 1000) % 7 + 1)
    for k in range(60):
        yy = (k * 97 % 523) / 523
        y = int((0.18 + 0.64 * yy) * H / q)
        speed = 0.8 + (k % 7) * 0.25
        head = ((t * speed + k * 0.137) % 1.4 - 0.2) * W / q
        L = (80 + (k % 5) * 50) / q * 2
        cv2.line(lay, (int(head - L), y), (int(head), y), 0.5 + 0.5 * (k % 3) / 2, 1, cv2.LINE_AA)
    lay = lay + cv2.GaussianBlur(lay, (0, 0), 4) * 1.5
    img += cv2.resize(lay, (W, H))[..., None] * np.array([0.3, 0.6, 1.0], np.float32) * 0.9
    out = ease_in((t - 19.4) / 0.6)
    for i, (t0, big, small) in enumerate(((16.05, "USB4", "40Gbps"), (17.05, "WI-FI 7", "NEXT-GEN WIRELESS"),
                                          (18.05, "5G LAN", "5 GIGABIT ETHERNET"))):
        a = ease_out((t - t0) / 0.35) * (1 - out)
        pop = 1 + 0.25 * (1 - ease_out((t - t0) / 0.5))
        y = H * (0.26 + 0.24 * i)
        put_text(img, big, W - 140 + 300 * out, y, int(118 * pop), (0.96, 0.97, 1.0), alpha=a,
                 tracking=4, anchor="r")
        put_text(img, small, W - 140 + 300 * out, y + 74, 34, GOLD_HDR, alpha=a * ease_out((t - t0 - 0.15) / 0.4),
                 weight="SemiLight", tracking=10, anchor="r")
    return img, None


def hero_cam(t):
    if t < 25:
        u = (t - 20) / 5
        return Cam((140, 150, 8), 780 - 170 * ease_out(u), -0.8 + 0.62 * ease_io(u), 0.78 + 0.12 * u, 30)
    u = (t - 25) / 5
    return Cam((140, 150, 8), 610 + 30 * u, -0.18 + 0.14 * u, 0.9, 30)


def shot_hero(t):
    img = background(0.22, (0.3, 0.35, 0.6), 0.5)
    draw_board(img, hero_cam(t), t, argb=1.0, traces=0.5 * ease((t - 21) / 1),
               sweep=(-800 + 4200 * ease_io(clamp01((t - 20.8) / 3.0)), 1.1))
    particles(img, t, 0.3)
    return img, None


def shot_title(t):
    img = background(0.22, (0.3, 0.35, 0.6), 0.5)
    draw_board(img, hero_cam(t), t, argb=1.0, traces=0.5)
    dim = 1 - 0.62 * ease((t - 25) / 0.8)
    img = img * dim
    img = cv2.GaussianBlur(img, (0, 0), 1 + 7 * ease((t - 25) / 1.0))
    particles(img, t, 0.4)
    a1 = ease_out((t - 25.35) / 0.6)
    put_text(img, "ASRock", W / 2, H * 0.34, 58, (0.95, 0.95, 0.97), alpha=a1, tracking=8 + 10 * (1 - a1),
             anchor="c")
    a2 = ease_out((t - 25.7) / 0.8)
    put_text(img, "X870E TAICHI", W / 2, H * 0.48, 168, GOLD_HDR * 1.05, alpha=a2,
             tracking=6 + 40 * (1 - a2), anchor="c", reveal=a2, shine=-400 + 2800 * ease_io((t - 26.4) / 1.6))
    bw = 520 * ease_out((t - 26.1) / 0.7)
    bar(img, W / 2 - bw / 2, H * 0.58, bw, 3, GOLD_HDR, a2)
    a3 = ease_out((t - 26.5) / 0.7)
    put_text(img, "ENGINEERED FOR THE NEXT ERA", W / 2, H * 0.635, 36, (0.82, 0.83, 0.86), alpha=a3,
             weight="SemiLight", tracking=16, anchor="c")
    img *= 1 - ease((t - 29.1) / 0.85)
    return img, None


SHOTS = ((0, 4, shot_intro), (4, 8, shot_vrm), (8, 12, shot_socket), (12, 14, shot_dimm),
         (14, 16, shot_pcie), (16, 20, shot_connect), (20, 25, shot_hero), (25, 30.01, shot_title))


def shot_at(t):
    for a, b, fn in SHOTS:
        if a <= t < b:
            return fn(t)
    return SHOTS[-1][2](t)


def whip(img, amount, vertical=False):
    k = int(amount * 140)
    if k < 3:
        return img
    ker = np.ones((1, k), np.float32) / k
    if vertical:
        ker = ker.T
    return cv2.filter2D(img, -1, ker, borderType=cv2.BORDER_REFLECT)


# ---------- 後製 ----------

def post(img, focus):
    if focus is not None:
        fx, fy, r0, r1 = focus
        blur = cv2.GaussianBlur(img, (0, 0), 5)
        m = np.clip((np.hypot(XX - fx, YY - fy) - r0) / (r1 - r0), 0, 1)[..., None]
        img = img * (1 - m) + blur * m
    q = 4
    small = cv2.resize(np.maximum(img - 0.75, 0), (W // q, H // q), interpolation=cv2.INTER_AREA)
    b1 = cv2.GaussianBlur(small, (0, 0), 3)
    b2 = cv2.GaussianBlur(small, (0, 0), 14)
    streak = cv2.blur(small.mean(axis=2), (151, 1))[..., None] * np.array([0.45, 0.6, 1.0], np.float32)
    img = img + cv2.resize(b1 * 0.6 + b2 * 0.45 + streak * 1.3, (W, H))
    x = np.maximum(img * 0.95, 0)
    img = (x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14)
    vr = ((XX - W / 2) / (W / 2)) ** 2 + ((YY - H / 2) / (H / 2)) ** 2
    img *= (1 - 0.3 * vr)[..., None]
    img += assets()["noise"].normal(0, 0.010, (H, W, 1)).astype(np.float32)
    return np.clip(img, 0, 1)


def render(f):
    t = f / FPS
    img, focus = shot_at(t)
    # 轉場
    if 11.85 <= t < 12.0 or 13.85 <= t < 14.0:
        nxt, _ = shot_at(math.ceil(t) + 0.0)
        k = ease((t - (math.ceil(t) - 0.15)) / 0.15)
        img = img * (1 - k) + nxt * k + k * (1 - k) * 1.2
    for tb, vert in ((8.0, False), (16.0, True)):
        d = abs(t - tb)
        if d < 0.17:
            img = whip(img, 1 - d / 0.17, vert)
    for tb, s in ((4.0, 1.4), (20.0, 1.8), (25.0, 0.6)):
        if t >= tb:
            img = img + s * math.exp(-((t - tb) / 0.12) ** 2)
    if 16 <= t < 20.0:
        focus = None
    out = post(img, focus)
    return (out * 255 + 0.5).astype(np.uint8)


# ---------- 輸出 ----------

def encode(path):
    audio = build_audio(DUR)
    out = av.open(path, "w")
    vs = out.add_stream("libx264", rate=FPS)
    vs.width, vs.height, vs.pix_fmt = W, H, "yuv420p"
    vs.options = {"crf": "18", "preset": "medium"}
    ast = out.add_stream("aac", rate=SR, layout="stereo")
    ast.bit_rate = 256000
    chunk, a_pos = 1024, 0
    with Pool(WORKERS) as pool:
        for f, frame in enumerate(pool.imap(render, range(N), chunksize=2)):
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
            if f % 30 == 29:
                print(f"frame {f + 1}/{N}", flush=True)
    for p in vs.encode():
        out.mux(p)
    for p in ast.encode():
        out.mux(p)
    out.close()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        os.makedirs(os.path.join(HERE, "check"), exist_ok=True)
        frames = [int(a) for a in sys.argv[1:]]
        with Pool(min(WORKERS, len(frames))) as pool:
            for f, im in zip(frames, pool.map(render, frames)):
                Image.fromarray(im).save(os.path.join(HERE, "check", f"f{f:03d}.png"))
        print("saved", frames)
    else:
        encode(os.path.join(HERE, "taichi.mp4"))
