"""X870E Taichi 主機板的程序化貼圖與物件定義.

座標單位為 mm, 原點在主機板左上角 (背板 I/O 在左側), x 向右, y 向下, h 為高度.
貼圖以 K px/mm 繪製.
"""
import math

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

K = 12.0
BW_MM, BH_MM = 277.0, 305.0
TW, TH = int(BW_MM * K), int(BH_MM * K)
FONT = "C:/Windows/Fonts/bahnschrift.ttf"

GOLD = (214, 172, 104)
GOLD_DIM = (120, 96, 60)


def P(v):
    return int(round(v * K))


def font(size, weight="Bold"):
    f = ImageFont.truetype(FONT, int(size))
    f.set_variation_by_name(weight)
    return f


# ---------- 物件 ----------
# kind: tex 有貼圖頂面, flat 只畫純色頂面
OBJECTS = [
    dict(name="io", rect=(4, 4, 46, 158), h=38, kind="tex", side=(30, 30, 34), metal=0.9, gold=True),
    dict(name="vrm", rect=(46, 8, 162, 36), h=30, kind="tex", side=(34, 34, 38), metal=1.0, gold=True),
    dict(name="eps1", rect=(166, 4, 184, 14), h=11, kind="flat", side=(14, 14, 16), top=(22, 22, 25), metal=0.1),
    dict(name="eps2", rect=(188, 4, 206, 14), h=11, kind="flat", side=(14, 14, 16), top=(22, 22, 25), metal=0.1),
    dict(name="socket", rect=(78, 52, 132, 118), h=4, kind="tex", side=(120, 120, 126), metal=1.0, gold=False),
    dict(name="atx24", rect=(264, 72, 274, 128), h=10, kind="flat", side=(14, 14, 16), top=(22, 22, 25), metal=0.1),
    dict(name="pcie1", rect=(48, 170, 140, 178.5), h=11, kind="tex", side=(110, 112, 118), metal=1.0, gold=False),
    dict(name="m2a", rect=(48, 184, 200, 238), h=6, kind="tex", side=(32, 32, 36), metal=0.8, gold=True),
    dict(name="pcie2", rect=(48, 244, 140, 252.5), h=10, kind="tex", side=(16, 16, 18), metal=0.2, gold=False),
    dict(name="m2b", rect=(48, 258, 200, 290), h=5, kind="tex", side=(32, 32, 36), metal=0.8, gold=True),
    dict(name="chipset", rect=(206, 184, 268, 248), h=12, kind="tex", side=(34, 34, 38), metal=0.9, gold=True),
    dict(name="audio", rect=(4, 166, 44, 298), h=5, kind="tex", side=(30, 30, 34), metal=0.6, gold=True),
    dict(name="hdr1", rect=(270, 140, 275, 176), h=6, kind="flat", side=(14, 14, 16), top=(24, 24, 27), metal=0.1),
]
for i, x in enumerate((160, 168.5, 180, 188.5)):
    OBJECTS.append(dict(name=f"dimm{i}", rect=(x, 30, x + 6.5, 163), h=7, kind="tex",
                        side=(18, 18, 20), metal=0.3, gold=False))
for i in range(12):
    x = 52 + i * 9
    OBJECTS.append(dict(name=f"chk{i}", rect=(x, 39, x + 7, 46), h=6, kind="flat",
                        side=(60, 60, 64), top=(92, 92, 98), metal=0.6))
for i in range(10):
    y = 46 + i * 9.5
    OBJECTS.append(dict(name=f"chl{i}", rect=(49, y, 56, y + 7), h=6, kind="flat",
                        side=(60, 60, 64), top=(92, 92, 98), metal=0.6))
for i, x in enumerate(range(60, 250, 24)):
    OBJECTS.append(dict(name=f"bh{i}", rect=(x, 295, x + 14, 300), h=6, kind="flat",
                        side=(14, 14, 16), top=(24, 24, 27), metal=0.1))

SOCKET_C = (105.0, 85.0)

# 訊號走線: 由插槽連到記憶體與 PCIe, 供資料脈衝動畫使用
TRACES = []
for i, y in enumerate(np.arange(58, 114, 3.2)):
    xe = (163, 171.5, 183, 191.5)[i % 4]
    TRACES.append([(132, y), (145 + (i % 3) * 2, y), (150 + (i % 3) * 2, y + 3), (xe, y + 3)])
for i, x in enumerate(np.arange(84, 128, 3.0)):
    TRACES.append([(x, 118), (x, 140 + (i % 4) * 3), (x - 8, 150 + (i % 4) * 3), (x - 8, 170)])
for i, y in enumerate(np.arange(190, 240, 4.5)):
    TRACES.append([(206, y), (200, y)])
for i, x in enumerate(np.arange(212, 262, 5)):
    TRACES.append([(x, 248), (x, 256), (x - 6, 262), (x - 6, 290)])


# ---------- 繪圖小工具 ----------

def gear_poly(cx, cy, r, teeth, rot=0.0, depth=0.12, n_per=6):
    pts = []
    for k in range(teeth):
        a0 = rot + 2 * math.pi * k / teeth
        step = 2 * math.pi / teeth
        for frac, rr in ((0.0, 1 - depth), (0.15, 1 - depth), (0.25, 1.0), (0.5, 1.0), (0.6, 1 - depth)):
            a = a0 + frac * step
            pts.append((cx + r * rr * math.cos(a), cy + r * rr * math.sin(a)))
    return np.array(pts, np.float32)


def draw_gear(img, cx, cy, r, teeth, color, th, rot=0.0, spokes=5):
    g = gear_poly(cx, cy, r, teeth, rot)
    cv2.polylines(img, [np.round(g * 16).astype(np.int32)], True, color, th, cv2.LINE_AA, shift=4)
    for rr in (0.62, 0.22):
        cv2.circle(img, (int(cx * 16), int(cy * 16)), int(r * rr * 16), color, th, cv2.LINE_AA, shift=4)
    for k in range(spokes):
        a = rot + 2 * math.pi * k / spokes
        p0 = (int((cx + r * 0.22 * math.cos(a)) * 16), int((cy + r * 0.22 * math.sin(a)) * 16))
        p1 = (int((cx + r * 0.62 * math.cos(a)) * 16), int((cy + r * 0.62 * math.sin(a)) * 16))
        cv2.line(img, p0, p1, color, th, cv2.LINE_AA, shift=4)


def brushed(h, w, base, amp, rng, horizontal=True):
    n = rng.standard_normal((h, w)).astype(np.float32)
    n = cv2.blur(n, (61, 1) if horizontal else (1, 61))
    n = n / (n.std() + 1e-6)
    grad = np.linspace(1.08, 0.88, h, dtype=np.float32)[:, None]
    out = np.clip(np.array(base, np.float32)[None, None, :] * grad[..., None] + n[..., None] * amp, 0, 255)
    return out.astype(np.uint8)


def paste_text(rgba, text, cx, cy, size, color, weight="Bold", rotate=0, tracking=0, alpha=255):
    f = font(size, weight)
    widths = [f.getlength(c) for c in text]
    tw = int(sum(widths) + tracking * (len(text) - 1)) + 8
    th = int(size * 1.4)
    im = Image.new("L", (tw, th), 0)
    d = ImageDraw.Draw(im)
    x = 4
    for c, w in zip(text, widths):
        d.text((x, th / 2), c, font=f, fill=255, anchor="lm")
        x += w + tracking
    if rotate:
        im = im.rotate(rotate, expand=True, resample=Image.BICUBIC)
    m = np.asarray(im, np.float32) / 255 * (alpha / 255)
    hh, ww = m.shape
    x0, y0 = int(cx - ww / 2), int(cy - hh / 2)
    reg = rgba[y0:y0 + hh, x0:x0 + ww, :3].astype(np.float32)
    reg = reg * (1 - m[..., None]) + np.array(color, np.float32) * m[..., None]
    rgba[y0:y0 + hh, x0:x0 + ww, :3] = reg.astype(np.uint8)


def rect_px(r):
    return P(r[0]), P(r[1]), P(r[2]), P(r[3])


# ---------- 底板 ----------

def build_base():
    rng = np.random.default_rng(3)
    img = np.full((TH, TW, 3), (11, 11, 13), np.uint8)
    img = np.clip(img.astype(np.int16) + rng.integers(-2, 3, (TH, TW, 1)), 0, 255).astype(np.uint8)

    # 走線
    dirs = [(1, 0), (0, 1), (-1, 0), (0, -1), (0.707, 0.707), (-0.707, 0.707)]
    for _ in range(650):
        x, y = rng.uniform(0, BW_MM), rng.uniform(0, BH_MM)
        pts = [(x, y)]
        d = dirs[rng.integers(0, 4)]
        for _ in range(rng.integers(2, 6)):
            L = rng.uniform(4, 35)
            x, y = x + d[0] * L, y + d[1] * L
            pts.append((x, y))
            d = dirs[rng.integers(0, len(dirs))]
        p = np.round(np.array(pts) * K * 16).astype(np.int32)
        cv2.polylines(img, [p], False, (21, 22, 26), int(rng.integers(2, 4)), cv2.LINE_AA, shift=4)
    for tr in TRACES:
        p = np.round(np.array(tr) * K * 16).astype(np.int32)
        cv2.polylines(img, [p], False, (30, 28, 24), 3, cv2.LINE_AA, shift=4)

    # SMD 元件
    for _ in range(1400):
        x, y = rng.uniform(5, BW_MM - 5), rng.uniform(5, BH_MM - 5)
        w, h = (rng.uniform(1.0, 2.2), rng.uniform(0.5, 1.2))
        if rng.random() < 0.5:
            w, h = h, w
        col = [(46, 40, 34), (24, 24, 26), (70, 66, 60)][rng.integers(0, 3)]
        cv2.rectangle(img, (P(x), P(y)), (P(x + w), P(y + h)), col, -1, cv2.LINE_AA)
    # 電容
    for _ in range(26):
        x, y = rng.uniform(150, 260), rng.uniform(170, 290)
        cv2.circle(img, (P(x), P(y)), P(3), (52, 52, 56), -1, cv2.LINE_AA)
        cv2.circle(img, (P(x), P(y)), P(2.2), (30, 30, 32), 2, cv2.LINE_AA)

    # AM5 LGA 觸點
    x0, y0 = P(SOCKET_C[0] - 22), P(SOCKET_C[1] - 22)
    cv2.rectangle(img, (x0, y0), (P(SOCKET_C[0] + 22), P(SOCKET_C[1] + 22)), (20, 19, 18), -1)
    pitch = 0.88
    n = int(42 / pitch)
    for i in range(n):
        for j in range(n):
            px = SOCKET_C[0] - 21 + i * pitch
            py = SOCKET_C[1] - 21 + j * pitch
            if abs(px - SOCKET_C[0]) < 7 and abs(py - SOCKET_C[1]) < 9:
                continue
            cv2.circle(img, (P(px) * 4, P(py) * 4), 9, (160, 124, 64), -1, cv2.LINE_AA, shift=2)
    cv2.rectangle(img, (P(SOCKET_C[0] - 6), P(SOCKET_C[1] - 8)), (P(SOCKET_C[0] + 6), P(SOCKET_C[1] + 8)),
                  (34, 32, 30), -1)

    # 絲印
    for txt, (x, y) in (("PCIE1", (50, 168)), ("M2_1", (202, 186)), ("DDR5_A1", (160, 167)),
                        ("DDR5_B1", (180, 167)), ("CPU_FAN1", (210, 20)), ("X870E TAICHI", (214, 140)),
                        ("ATX12V1", (166, 18)), ("PCIE2", (50, 242)), ("BIOS", (240, 278))):
        cv2.putText(img, txt, (P(x), P(y)), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (88, 88, 94), 2, cv2.LINE_AA)

    # 螺絲孔
    for x, y in ((8, 10), (8, 160), (140, 10), (268, 10), (140, 160), (268, 160), (8, 296), (140, 296), (268, 296)):
        cv2.circle(img, (P(x), P(y)), P(4.2), (150, 150, 155), -1, cv2.LINE_AA)
        cv2.circle(img, (P(x), P(y)), P(2.0), (6, 6, 7), -1, cv2.LINE_AA)

    # 板邊金線
    cv2.rectangle(img, (P(1.2), P(1.2)), (TW - P(1.2), TH - P(1.2)), GOLD_DIM, 3, cv2.LINE_AA)

    # 凸起物件的環境遮蔽陰影
    f = img.astype(np.float32)
    sh = np.zeros((TH, TW), np.float32)
    for o in OBJECTS:
        a, b, c, d = rect_px(o["rect"])
        e = P(o["h"] * 0.12)
        cv2.rectangle(sh, (a - e, b - e), (c + e, d + e), 1.0, -1)
    sh = cv2.GaussianBlur(sh, (0, 0), K * 2.5)
    f *= (1 - 0.75 * np.clip(sh, 0, 1))[..., None]
    return f / 255.0


# ---------- 頂面貼圖 ----------

def build_tops():
    rng = np.random.default_rng(11)
    tops = {}
    for o in OBJECTS:
        if o["kind"] != "tex":
            continue
        a, b, c, d = rect_px(o["rect"])
        w, h = c - a, d - b
        rgba = np.zeros((h, w, 4), np.uint8)
        emis = np.zeros((h, w), np.float32)
        rgba[..., 3] = 255
        name = o["name"]

        if name == "io":
            rgba[..., :3] = brushed(h, w, (38, 38, 43), 5, rng, horizontal=False)
            for k in range(0, h, P(3)):
                cv2.line(rgba, (P(3), k), (w - P(3), k + P(6)), (32, 32, 36, 255), 2, cv2.LINE_AA)
            draw_gear(rgba, w * 0.5, h * 0.66, w * 0.40, 18, GOLD + (255,), 3, rot=0.2)
            draw_gear(rgba, w * 0.75, h * 0.86, w * 0.22, 11, GOLD_DIM + (255,), 2, rot=0.5)
            paste_text(rgba, "TAICHI", w * 0.48, h * 0.30, P(9), (226, 226, 230), rotate=90, tracking=P(1.5))
            cv2.rectangle(rgba, (P(1.5), P(1.5)), (w - P(1.5), h - P(1.5)), GOLD + (255,), 3, cv2.LINE_AA)
            cv2.line(emis, (w - P(4), P(10)), (w - P(4), h - P(10)), 1.0, P(1.2), cv2.LINE_AA)
        elif name == "vrm":
            rgba[..., :3] = brushed(h, w, (44, 44, 50), 6, rng)
            for k in range(P(3), h - P(2), P(2.6)):
                cv2.line(rgba, (P(2), k), (w - P(14), k), (18, 18, 21, 255), P(0.9), cv2.LINE_AA)
                cv2.line(rgba, (P(2), k + P(0.9)), (w - P(14), k + P(0.9)), (70, 70, 78, 255), 1, cv2.LINE_AA)
            draw_gear(rgba, w - P(7), h / 2, P(5.5), 10, GOLD + (255,), 2, rot=0.3)
            cv2.rectangle(rgba, (P(1.2), P(1.2)), (w - P(1.2), h - P(1.2)), GOLD + (255,), 3, cv2.LINE_AA)
        elif name == "socket":
            rgba[..., :3] = brushed(h, w, (168, 168, 174), 10, rng)
            cx, cy = P(SOCKET_C[0]) - a, P(SOCKET_C[1]) - b
            cv2.rectangle(rgba, (cx - P(23), cy - P(23)), (cx + P(23), cy + P(23)), (0, 0, 0, 0), -1)
            cv2.rectangle(rgba, (cx - P(24), cy - P(24)), (cx + P(24), cy + P(24)), (120, 120, 126, 255), 3, cv2.LINE_AA)
            cv2.line(rgba, (w - P(2), P(4)), (w - P(2), h - P(4)), (210, 210, 215, 255), P(1.6), cv2.LINE_AA)
            tri = np.array([[P(3), h - P(3)], [P(8), h - P(3)], [P(3), h - P(8)]], np.int32)
            cv2.fillConvexPoly(rgba, tri, GOLD + (255,), cv2.LINE_AA)
        elif name.startswith("dimm"):
            rgba[..., :3] = (20, 20, 23)
            cv2.line(rgba, (w // 2, P(6)), (w // 2, h - P(6)), (4, 4, 5, 255), P(1.6))
            for yy in (0, h - P(6)):
                cv2.rectangle(rgba, (0, yy), (w, yy + P(6)), (66, 66, 72, 255), -1)
            cv2.line(rgba, (P(0.6), P(6)), (P(0.6), h - P(6)), (48, 48, 54, 255), 2)
        elif name == "pcie1":
            rgba[..., :3] = brushed(h, w, (176, 178, 184), 10, rng)
            cv2.line(rgba, (P(14), h // 2), (w - P(4), h // 2), (8, 8, 9, 255), P(2.2))
            cv2.line(rgba, (P(4), h // 2), (P(12), h // 2), (8, 8, 9, 255), P(2.2))
            cv2.rectangle(rgba, (1, 1), (w - 2, h - 2), (230, 230, 236, 255), 2, cv2.LINE_AA)
        elif name == "pcie2":
            rgba[..., :3] = (18, 18, 20)
            cv2.line(rgba, (P(14), h // 2), (w - P(4), h // 2), (4, 4, 5, 255), P(2.2))
        elif name in ("m2a", "m2b"):
            rgba[..., :3] = brushed(h, w, (40, 40, 45), 5, rng)
            for k in range(-h, w, P(4)):
                cv2.line(rgba, (k, h), (k + h, 0), (34, 34, 38, 255), 2, cv2.LINE_AA)
            draw_gear(rgba, w - P(16), h / 2, h * 0.36, 14, GOLD + (255,), 3, rot=0.1 if name == "m2a" else 0.6)
            label = "BLAZING M.2" if name == "m2a" else "TAICHI"
            paste_text(rgba, label, w * 0.42, h / 2, P(7), (215, 215, 220), tracking=P(1.2))
            cv2.rectangle(rgba, (P(1.2), P(1.2)), (w - P(1.2), h - P(1.2)), GOLD + (255,), 3, cv2.LINE_AA)
        elif name == "chipset":
            rgba[..., :3] = brushed(h, w, (42, 42, 47), 6, rng)
            draw_gear(rgba, w / 2, h / 2, w * 0.40, 20, GOLD + (255,), 3, rot=0.15)
            draw_gear(rgba, w / 2, h / 2, w * 0.26, 12, GOLD_DIM + (255,), 2, rot=0.4)
            paste_text(rgba, "X870E", w / 2, h * 0.86, P(5), (210, 210, 216), tracking=P(0.8))
            cv2.circle(emis, (w // 2, h // 2), int(w * 0.46), 1.0, P(1.0), cv2.LINE_AA)
            cv2.rectangle(rgba, (P(1.2), P(1.2)), (w - P(1.2), h - P(1.2)), GOLD + (255,), 3, cv2.LINE_AA)
        elif name == "audio":
            rgba[..., :3] = brushed(h, w, (36, 36, 41), 5, rng, horizontal=False)
            paste_text(rgba, "TAICHI AUDIO", w / 2, h / 2, P(5), (190, 190, 196), rotate=90, tracking=P(1))
            cv2.rectangle(rgba, (P(1.2), P(1.2)), (w - P(1.2), h - P(1.2)), GOLD + (255,), 3, cv2.LINE_AA)
            cv2.line(emis, (P(3), P(8)), (P(3), h - P(8)), 1.0, P(0.9), cv2.LINE_AA)

        f = rgba.astype(np.float32) / 255.0
        f[..., :3] *= f[..., 3:4]   # 預乘 alpha
        emis = cv2.GaussianBlur(emis, (0, 0), 3) * f[..., 3]
        tops[name] = (f, emis)
    return tops


def pyramid(img, levels=3):
    out = [img]
    for _ in range(levels - 1):
        prev = out[-1]
        out.append(cv2.resize(prev, (max(prev.shape[1] // 2, 1), max(prev.shape[0] // 2, 1)),
                              interpolation=cv2.INTER_AREA))
    return out
