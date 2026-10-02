"""30 秒 Game of Thrones 概念預告, 純程式產生畫面與音訊.

用法:
    python render.py               輸出 got.mp4
    python render.py 60 150 300    只輸出指定影格的 PNG 到 check/
"""
import math
import os
import sys
from multiprocessing import Pool

import av
import cv2
import numpy as np
from PIL import Image

import figures as F
from audio import build_audio, SR, CLASHES, BEAT
from fx import (W, H, BAR_H, XX, YY, Particles, clamp01, col, composite_silhouette, ease, ease_in, ease_io,
                ease_out, fire_field, lerp, post, scroll, shake, smoke, text_mask, place, title_text)

FPS = 30
DUR = 30.0
N = int(FPS * DUR)
HERE = os.path.dirname(os.path.abspath(__file__))
WORKERS = 12
SERIF = "constan.ttf"
SERIF_B = "constanb.ttf"

SNOW = Particles(700, 1)
SNOW_FAR = Particles(900, 2)
EMBER = Particles(260, 3)
DUST = Particles(200, 4)


def walk_phase(t):
    return t * math.pi / BEAT      # 每兩拍走一個完整步態


def sky(top, bottom, horizon=0.6):
    u = np.clip((YY[:, :1] - BAR_H) / ((H - 2 * BAR_H) * horizon), 0, 1)
    g = col(*top) * (1 - u[..., None]) + col(*bottom) * u[..., None]
    return np.broadcast_to(g, (H, W, 3)).copy()


def clouds(img, t, tint, amount, speed=12.0, y0=0.0, y1=0.6):
    q = 4
    n = scroll("cloud", t * speed, 0, H // q, W // q)
    n = np.clip((n - 0.4) * 2.2, 0, 1)
    band = np.clip(1 - np.abs(np.linspace(0, 1, H // q)[:, None] - (y0 + y1) / 2) / ((y1 - y0) / 2), 0, 1)
    img += cv2.resize(n * band, (W, H))[..., None] * col(*tint) * amount


def zoom(img, s, cx, cy):
    M = np.float32([[s, 0, cx - s * cx], [0, s, cy - s * cy]])
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def ridge(x, base, amp, seed, freq=1.0):
    rng = np.random.default_rng(seed)
    y = np.full_like(x, base, dtype=np.float32)
    for k in range(5):
        f = freq * (0.002 + rng.random() * 0.004) * (2 ** k)
        y += amp / (2 ** k) * np.sin(x * f + rng.random() * 6.28)
    return y


def fill_below(mask_shape, ys):
    return (YY >= ys[None, :]).astype(np.float32)


# ---------- 1. 長城 ----------

def shot_wall(t):
    img = sky((0.012, 0.018, 0.04), (0.08, 0.11, 0.16), 0.55)
    clouds(img, t, (0.10, 0.12, 0.17), 0.8, 10, 0.0, 0.55)
    mx, my = W * 0.76, H * 0.27
    d = np.hypot(XX - mx, YY - my)
    img += (np.exp(-d / 26) ** 4 * 2.0 + np.exp(-d / 160) * 0.18)[..., None] * col(0.85, 0.92, 1.0)

    top = H * 0.50 + (XX[0] - W / 2) * 0.012
    wall = fill_below(None, top)
    ice = scroll("ice", 0, 0, H, W)
    ice = cv2.blur(ice, (3, 81))
    depth = np.clip((YY - top[None, :]) / (H * 0.5), 0, 1)
    ice_col = (col(0.20, 0.32, 0.46) * (0.55 + 0.6 * ice[..., None])) * (1 - 0.55 * depth[..., None])
    edge = np.exp(-((YY - top[None, :]) / 3.0) ** 2) * 0.9
    img = img * (1 - wall[..., None]) + ice_col * wall[..., None]
    img += edge[..., None] * col(0.7, 0.85, 1.0)
    mist = np.clip((YY - H * 0.70) / (H * 0.2), 0, 1) * (0.5 + 0.5 * scroll("smoke", t * 40, 0, H, W))
    img += mist[..., None] * col(0.16, 0.2, 0.26)

    m = np.zeros((H, W), np.uint8)
    fx = W * 0.56
    F.human(m, fx, float(top[int(fx)]), 150, facing=1, back_view=True, cloak=1.15, wind=0.35 + 0.1 * math.sin(t),
            t=t, hood=True, arm_r=(6, 4), arm_l=(-4, -2), sword=5)
    composite_silhouette(img, m.astype(np.float32) / 255, body=(0.01, 0.012, 0.018),
                         rim_col=(0.7, 0.85, 1.0), rim_dir=(4, -3), rim_k=1.4)
    img += smoke(t, 0.35, (0.12, 0.14, 0.18), (60, 0))
    SNOW_FAR.snow(img, t, 0.35, wind=0.12, fall=0.08)
    SNOW.snow(img, t, 0.8, wind=0.2, fall=0.15)
    img = zoom(img, 1 + 0.12 * ease_io(t / 5), fx, H * 0.48)

    a = ease((t - 1.6) / 0.8) * (1 - ease((t - 4.0) / 0.5))
    title_text(img, "HBO PRESENTS", SERIF, 40, W / 2, H * 0.74, a, 22, blur=6 * (1 - ease((t - 1.6) / 1.2)))
    return img, (0.88, 1.0, 1.18)


# ---------- 2. 行軍 ----------

def banner(m, x, top_y, h, t, k):
    F.seg(m, (x, top_y + h * 0.9), (x, top_y), max(h * 0.012, 1))
    pts = [(x, top_y)]
    for i in range(8):
        u = i / 7
        pts.append((x + h * 0.32 * u, top_y + h * 0.02 * math.sin(t * 6 + u * 4 + k)))
    for i in range(7, -1, -1):
        u = i / 7
        pts.append((x + h * 0.32 * u, top_y + h * 0.18 + h * 0.03 * math.sin(t * 6 + u * 4 + k + 0.6)))
    F.poly(m, pts)


def shot_march(t):
    lt = t - 5
    img = sky((0.10, 0.12, 0.15), (0.34, 0.37, 0.41), 0.65)
    clouds(img, lt, (0.08, 0.08, 0.09), 1.0, 25, 0.0, 0.6)
    xs = XX[0]
    pan = lt * 60
    for k, (base, amp, shade) in enumerate(((0.52, 70, 0.24), (0.58, 45, 0.18))):
        ys = ridge(xs + pan * (0.2 + 0.2 * k), H * base, amp, 10 + k)
        m = fill_below(None, ys)
        img = img * (1 - m[..., None]) + col(shade, shade + 0.02, shade + 0.05) * m[..., None]

    ph = walk_phase(t)
    speed = 95.0
    far_y = ridge(xs + pan * 0.6, H * 0.665, 18, 21)
    far = np.zeros((H, W), np.uint8)
    for i in range(46):
        x = (i * 52 + speed * 0.6 * lt - pan * 0.6) % (W + 200) - 100
        y = float(far_y[int(np.clip(x, 0, W - 1))])
        F.human(far, x, y, 62, facing=1, cloak=0.6, wind=0.2, t=t + i, spear=True, **F.walk_pose(ph + i * 0.7))
        if i % 9 == 4:
            banner(far, x + 6, y - 110, 120, t, i)
    far_m = far.astype(np.float32) / 255
    img = img * (1 - far_m[..., None]) + col(0.10, 0.11, 0.13) * far_m[..., None]
    ground = fill_below(None, far_y + 6)
    img = img * (1 - ground[..., None]) + col(0.07, 0.075, 0.085) * ground[..., None]
    img += smoke(lt, 0.35, (0.25, 0.27, 0.3), (90, 0))

    near_y = ridge(xs + pan * 1.3, H * 0.84, 14, 31)
    near = np.zeros((H, W), np.uint8)
    for i in range(12):
        x = (i * 190 + 30 + speed * 1.3 * lt - pan * 1.3) % (W + 400) - 200
        y = float(near_y[int(np.clip(x, 0, W - 1))]) + 10
        F.human(near, x, y, 230, facing=1, cloak=0.95, wind=0.3, t=t + i * 0.37, spear=i % 3 != 1,
                sword=None, **F.walk_pose(ph + i * 1.3))
        if i % 4 == 2:
            banner(near, x + 18, y - 420, 420, t, i)
    nm = near.astype(np.float32) / 255
    g2 = fill_below(None, near_y)
    nm = np.maximum(nm, g2)
    composite_silhouette(img, nm, body=(0.015, 0.016, 0.02), rim_col=(0.5, 0.55, 0.62), rim_dir=(0, -3), rim_k=0.8)
    SNOW_FAR.snow(img, t, 0.6, wind=0.55, fall=0.14)
    SNOW.snow(img, t, 1.0, wind=0.7, fall=0.22)
    a = ease((lt - 0.7) / 0.7) * (1 - ease((lt - 4.0) / 0.5))
    title_text(img, "SEVEN KINGDOMS.", SERIF, 72, W / 2, H * 0.32, a, 20 + 8 * (1 - a), blur=5 * (1 - a))
    return img, (0.92, 0.98, 1.08)


# ---------- 3. 龍 ----------

def shot_dragon(t):
    lt = t - 10
    img = sky((0.03, 0.012, 0.012), (0.55, 0.16, 0.04), 0.75)
    img -= smoke(lt, 0.45, (0.25, 0.10, 0.04), (25, -12))
    img = np.maximum(img, 0)
    q = 2
    fire = fire_field(lt, H // q, W // q, height=0.55, speed=180)
    img += cv2.resize(fire, (W, H)) * 0.9
    cm = np.zeros((H, W), np.uint8)
    F.castle(cm, W * 0.52, H * 0.875, 300, seed=2)
    F.castle(cm, W * 0.15, H * 0.875, 180, seed=5)
    cmf = cm.astype(np.float32) / 255
    cmf = np.maximum(cmf, (YY > H * 0.87).astype(np.float32))
    composite_silhouette(img, cmf, body=(0.02, 0.008, 0.005), rim_col=(1.4, 0.5, 0.12), rim_dir=(0, -4), rim_k=1.2)

    u = lt / 5
    dx = lerp(-0.25 * W, 1.45 * W, u)
    dy = H * 0.40 + 25 * math.sin(lt * 2.5)
    flap = math.sin(lt * 2 * math.pi / (2 * BEAT))
    breath = clamp01((lt - 2.0) / 0.3) * (1 - clamp01((lt - 3.5) / 0.3))
    dm = np.zeros((H, W), np.uint8)
    mouth = F.dragon(dm, dx, dy, 880, flap, lt, facing=1, mouth=breath)
    composite_silhouette(img, dm.astype(np.float32) / 255, body=(0.012, 0.006, 0.006),
                         rim_col=(1.2, 0.45, 0.12), rim_dir=(0, 5), rim_k=1.6)
    if breath > 0:
        mx, my = mouth
        cone = np.zeros((H, W), np.uint8)
        L = 900 * breath
        F.poly(cone, [(mx, my), (mx + L * 0.75, my + L * 0.55), (mx + L * 0.45, my + L * 0.85)])
        cone_f = cv2.GaussianBlur(cone.astype(np.float32) / 255, (0, 0), 22)
        along = np.clip(((XX - mx) * 0.6 + (YY - my) * 0.8) / max(L, 1), 0, 1)
        n1 = scroll("fire", -lt * 700, -lt * 900, H, W)
        n2 = scroll("fire", 300 - lt * 400, 200 - lt * 1300, H, W)
        turb = np.clip((n1 * 0.6 + n2 * 0.4 - 0.3) * 2.2, 0, None) ** 1.5
        flame = cone_f * turb * (1 - along) ** 0.7 * breath * 1.6
        core = np.clip(1 - along * 2.5, 0, 1) * cone_f * breath
        img += flame[..., None] * (col(1.7, 0.45, 0.08) + (1 - along)[..., None] * col(0.6, 0.45, 0.1))
        img += core[..., None] * col(0.9, 0.55, 0.18)
        img += cv2.GaussianBlur(flame, (0, 0), 50)[..., None] * col(1.4, 0.45, 0.1)
    EMBER.embers(img, t, 1.0)
    a = ease((lt - 3.6) / 0.6) * (1 - ease((lt - 4.6) / 0.35))
    title_text(img, "FIRE AND BLOOD.", SERIF, 72, W / 2, H * 0.30, a, 20 + 8 * (1 - a), blur=5 * (1 - a))
    return img, (1.08, 0.98, 0.9)


# ---------- 4. 決鬥 ----------

IDLE = dict(arm_r=(45, 100), sword=135, arm_l=(20, 60))


def fighter_pose(t, me):
    """me: 0 或 1. CLASHES 中依序交替攻擊."""
    pose = dict(IDLE)
    step = 0.0
    for k, tc in enumerate(CLASHES):
        attacker = k % 2
        if t < tc - 0.55 or t > tc + 0.45:
            continue
        if attacker == me:
            if t < tc - 0.15:
                u = ease((t - (tc - 0.55)) / 0.4)
                pose = dict(arm_r=(lerp(45, 165, u), lerp(100, 175, u)), sword=lerp(135, 215, u), arm_l=(20, 60))
            elif t < tc:
                u = ease_in((t - (tc - 0.15)) / 0.15)
                pose = dict(arm_r=(lerp(165, 80, u), lerp(175, 90, u)), sword=lerp(215, 100, u), arm_l=(30, 70))
                step = 40 * u
            else:
                u = ease((t - tc) / 0.45)
                pose = dict(arm_r=(lerp(80, 45, u), lerp(90, 100, u)), sword=lerp(100, 135, u), arm_l=(30, 60))
                step = 40 * (1 - u)
        else:
            if t < tc:
                u = ease((t - (tc - 0.4)) / 0.35)
                pose = dict(arm_r=(lerp(45, 100, u), lerp(100, 150, u)), sword=lerp(135, 165, u), arm_l=(20, 60))
            else:
                u = ease((t - tc) / 0.45)
                pose = dict(arm_r=(lerp(100, 45, u), lerp(150, 100, u)), sword=lerp(165, 135, u), arm_l=(20, 60))
                step = -25 * math.sin(u * math.pi)
    return pose, step


SPARK_RNG = np.random.default_rng(12)
SPARK_DIRS = [(SPARK_RNG.uniform(0, 2 * math.pi), SPARK_RNG.uniform(200, 900)) for _ in range(60)]


def shot_duel(t):
    lt = t - 15
    img = sky((0.02, 0.01, 0.012), (0.35, 0.10, 0.03), 0.8)
    img -= smoke(lt, 0.4, (0.2, 0.08, 0.03), (40, -15))
    img = np.maximum(img, 0)
    q = 2
    img += cv2.resize(fire_field(lt, H // q, W // q, height=0.75, speed=200, seed_x=400), (W, H)) * 0.8
    ground_y = H * 0.80
    xs = XX[0]
    gy = ridge(xs, ground_y + 6, 8, 41)
    m = np.zeros((H, W), np.uint8)
    xa, xb = W * 0.40, W * 0.60
    pa, sa = fighter_pose(t, 0)
    pb, sb = fighter_pose(t, 1)
    _, tip_a = F.human(m, xa + sa, ground_y, 400, facing=1, cloak=0.8, wind=0.25, t=t, lean=8, **pa)
    _, tip_b = F.human(m, xb - sb, ground_y, 400, facing=-1, cloak=0.8, wind=0.25, t=t + 1, lean=8, **pb)
    mf = np.maximum(m.astype(np.float32) / 255, fill_below(None, gy))
    composite_silhouette(img, mf, body=(0.012, 0.006, 0.005), rim_col=(1.3, 0.5, 0.15), rim_dir=(0, -4), rim_k=1.3)
    img += rim_side(mf)

    # 火花
    hit = None
    for tc in CLASHES:
        if 0 <= t - tc < 0.6:
            hit = tc
    if hit is not None:
        age = t - hit
        cx, cy = W / 2, ground_y - 400 * 0.86
        lay = np.zeros((H, W), np.float32)
        for a, v in SPARK_DIRS:
            x0 = cx + math.cos(a) * v * age
            y0 = cy + math.sin(a) * v * age + 900 * age * age
            x1 = cx + math.cos(a) * v * max(age - 0.03, 0)
            y1 = cy + math.sin(a) * v * max(age - 0.03, 0) + 900 * max(age - 0.03, 0) ** 2
            cv2.line(lay, (int(x1), int(y1)), (int(x0), int(y0)), 1.0, 2, cv2.LINE_AA)
        fade = math.exp(-age / 0.18)
        img += (lay * 3.0 + cv2.GaussianBlur(lay, (0, 0), 5) * 3.0)[..., None] * col(1.0, 0.75, 0.35) * fade
        flash = math.exp(-age / 0.05)
        d = np.hypot(XX - cx, YY - cy)
        img += (np.exp(-d / 90) * 4.0 * flash)[..., None] * col(1.0, 0.9, 0.7)
    EMBER.embers(img, t, 0.8)
    return img, (1.06, 0.98, 0.92)


def rim_side(mf):
    from fx import rim
    r = rim(mf, 4, 0) + rim(mf, -4, 0)
    return r[..., None] * col(0.9, 0.35, 0.1) * 0.6


# ---------- 5. 王座廳 ----------

def shot_throne(t):
    lt = t - 20
    img = sky((0.01, 0.012, 0.016), (0.03, 0.035, 0.045), 1.0)
    # 背牆的窗
    win = np.zeros((H, W), np.uint8)
    for wx in (0.30, 0.5, 0.70):
        cx = W * wx
        F.poly(win, [(cx - 45, H * 0.56), (cx + 45, H * 0.56), (cx + 45, H * 0.33), (cx, H * 0.27), (cx - 45, H * 0.33)])
    for wx in (0.30, 0.5, 0.70):
        cx = int(W * wx)
        cv2.line(win, (cx, int(H * 0.29)), (cx, int(H * 0.56)), 0, 5)
        cv2.line(win, (cx - 45, int(H * 0.44)), (cx + 45, int(H * 0.44)), 0, 5)
    wf = cv2.GaussianBlur(win.astype(np.float32) / 255, (0, 0), 1.5)
    img += wf[..., None] * col(0.5, 0.65, 0.85) * 1.1
    # 光束
    beams = np.zeros((H, W), np.uint8)
    for wx in (0.30, 0.5, 0.70):
        cx = W * wx
        F.poly(beams, [(cx - 45, H * 0.33), (cx + 45, H * 0.33), (cx + 260 + (wx - 0.5) * 300, H * 0.95),
                       (cx - 120 + (wx - 0.5) * 300, H * 0.95)])
    bf = cv2.GaussianBlur(beams.astype(np.float32) / 255, (0, 0), 30)
    bf *= 0.6 + 0.4 * scroll("smoke", lt * 25, lt * 10, H, W)
    img += bf[..., None] * col(0.35, 0.45, 0.6) * 0.55
    # 地板
    floor = np.clip((YY - H * 0.70) / (H * 0.3), 0, 1)
    img += floor[..., None] * col(0.05, 0.06, 0.075)
    # 柱子
    cm = np.zeros((H, W), np.uint8)
    for k, (x0, w0) in enumerate(((0.04, 0.10), (0.17, 0.06), (0.77, 0.06), (0.86, 0.10))):
        F.poly(cm, [(W * x0, 0), (W * (x0 + w0), 0), (W * (x0 + w0), H), (W * x0, H)])
    composite_silhouette(img, cm.astype(np.float32) / 255, body=(0.012, 0.014, 0.018),
                         rim_col=(0.3, 0.4, 0.55), rim_dir=(3, 0), rim_k=0.6)
    tm = np.zeros((H, W), np.uint8)
    F.throne(tm, W / 2, H * 0.70, 430)
    composite_silhouette(img, tm.astype(np.float32) / 255, body=(0.012, 0.012, 0.014),
                         rim_col=(0.75, 0.85, 1.0), rim_dir=(0, -3), rim_k=0.55)
    # 走向王座的人
    u = ease_out(clamp01((lt - 0.2) / 4.2) * 0.85 + 0.15 * clamp01((lt - 0.2) / 4.2))
    fy = lerp(H * 1.02, H * 0.745, u)
    fh = lerp(560, 150, u)
    fm = np.zeros((H, W), np.uint8)
    F.human(fm, W * 0.5 + 10, fy, fh, back_view=True, cloak=1.1, wind=0.08, t=t, walk=1.0 * (1 - 0.9 * ease((lt - 4.2) / 0.3)),
            phase=walk_phase(t), arm_r=(5, 4), arm_l=(-5, -4))
    composite_silhouette(img, fm.astype(np.float32) / 255, body=(0.008, 0.009, 0.012),
                         rim_col=(0.6, 0.75, 1.0), rim_dir=(0, -3), rim_k=1.0)
    DUST.embers(img, t, 0.0)
    dust = np.zeros((H, W, 3), np.float32)
    DUST.snow(dust, t, 0.5, wind=0.02, fall=0.01)
    img += dust * bf[..., None] * 3
    img = zoom(img, 1 + 0.10 * ease_io(lt / 4.4), W / 2, H * 0.55)
    a = ease((lt - 2.4) / 0.7) * (1 - ease((lt - 4.0) / 0.4))
    title_text(img, "ONE THRONE.", SERIF, 72, W / 2, H * 0.195, a, 22 + 8 * (1 - a), blur=5 * (1 - a))
    return img, (0.92, 1.0, 1.08)


# ---------- 6. 標題 ----------

def shot_title(t):
    lt = t - 25
    img = sky((0.008, 0.008, 0.01), (0.03, 0.025, 0.025), 1.0)
    img += smoke(lt, 0.25, (0.14, 0.1, 0.08), (20, -6))
    EMBER.embers(img, t, 0.6, rise=0.06)
    SNOW_FAR.snow(img, t, 0.25, wind=0.08, fall=0.05)

    a = ease_out(lt / 1.4)
    tr = lerp(70, 28, ease_out(lt / 2.0))
    m = text_mask("GAME OF THRONES", SERIF_B, 128, tr)
    m = cv2.GaussianBlur(m, (0, 0), 0.1 + 12 * (1 - a))
    th, tw = m.shape
    gy = np.linspace(0, 1, th, dtype=np.float32)[:, None]
    metal = 0.55 + 0.45 * np.exp(-((gy - 0.42) / 0.12) ** 2) - 0.2 * gy
    emb = np.clip(m - np.roll(np.roll(m, 2, 0), 2, 1), -1, 1)
    gx = np.arange(tw, dtype=np.float32)[None, :]
    sweep = np.exp(-((gx + gy * 120 - lerp(-300, tw + 300, ease_io((lt - 0.8) / 1.8))) / 90) ** 2) * 2.2
    colr = (metal + 0.35 * emb + sweep)[..., None] * col(0.92, 0.88, 0.80)
    place(img, m, W / 2, H * 0.47, colr, a)
    glow = cv2.GaussianBlur(m, (0, 0), 25)
    place(img, glow, W / 2, H * 0.47, col(0.5, 0.25, 0.08), 0.35 * a)

    a2 = ease((lt - 1.3) / 0.8)
    title_text(img, "WINTER IS COMING", SERIF, 34, W / 2, H * 0.59, a2, 16)
    lw = 220 * ease_out((lt - 1.3) / 1.0)
    for s in (-1, 1):
        x0 = W / 2 + s * 250
        xa, xb = sorted((x0, x0 + s * lw))
        img[int(H * 0.59) - 1:int(H * 0.59) + 1, int(xa):int(xb)] += col(0.6, 0.55, 0.48) * a2
    a3 = ease((lt - 2.0) / 0.8)
    title_text(img, "THE COMPLETE SAGA  ·  STREAMING ON HBO MAX", SERIF, 24, W / 2, H * 0.69, a3 * 0.8, 8,
               color=(0.7, 0.7, 0.72))
    img *= 1 - ease((lt - 4.2) / 0.75)
    return img, (1.02, 1.0, 0.97)


SHOTS = ((0, 5, shot_wall), (5, 10, shot_march), (10, 15, shot_dragon), (15, 20, shot_duel),
         (20, 25, shot_throne), (25, 30.01, shot_title))


def render(f):
    t = f / FPS
    for a, b, fn in SHOTS:
        if a <= t < b:
            img, grade = fn(t)
            start, end = a, b
            break
    # 段落轉場: 段尾短暫黑場, 段首閃光
    if end < 30 and end != 25:
        img *= 1 - ease((t - (end - 0.17)) / 0.17)
    if 24.35 <= t < 25:
        img *= 1 - ease((t - 24.35) / 0.25)
    if start > 0:
        img = img + 0.35 * math.exp(-(t - start) / 0.07)
    sh = 0.0
    for tb in (5, 10, 15, 20, 25):
        if t >= tb:
            sh = max(sh, math.exp(-(t - tb) / 0.25))
    for tc in CLASHES:
        if t >= tc:
            sh = max(sh, 1.2 * math.exp(-(t - tc) / 0.15))
    img = shake(img, sh, t)
    out = post(img, grade)
    return (out * 255 + 0.5).astype(np.uint8)


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
        encode(os.path.join(HERE, "got.mp4"))
