"""程序化剪影: 人物, 龍, 鐵王座, 城堡.

所有函式都畫在 uint8 遮罩上 (255 為實心), 以 cv2 的 LINE_AA 與 shift 取得次像素精度.
角度慣例: 0 為垂直向下, 正值朝人物面向的方向轉, 180 為正上方.
"""
import math

import cv2
import numpy as np

S = 16      # cv2 shift=4


def _p(x, y):
    return (int(round(x * S)), int(round(y * S)))


def seg(m, a, b, th):
    cv2.line(m, _p(*a), _p(*b), 255, max(int(th), 1), cv2.LINE_AA, shift=4)


def poly(m, pts):
    p = np.round(np.asarray(pts, np.float64) * S).astype(np.int32)
    cv2.fillPoly(m, [p], 255, cv2.LINE_AA, shift=4)


def disk(m, c, r):
    cv2.circle(m, _p(*c), int(round(r * S)), 255, -1, cv2.LINE_AA, shift=4)


def limb(origin, length, ang_deg, facing):
    a = math.radians(ang_deg)
    return (origin[0] + facing * length * math.sin(a), origin[1] + length * math.cos(a))


# ---------- 人物 ----------

def human(m, x, y, h, facing=1, walk=0.0, phase=0.0, arm_r=(10, 10), arm_l=(-10, -10), lean=0.0,
          sword=None, cloak=0.0, wind=0.0, t=0.0, hood=False, back_view=False, spear=False):
    """x, y 為雙腳中點, h 為身高 px.

    arm_r / arm_l: (上臂角, 前臂角), sword: 劍的角度 (握在右手) 或 None.
    """
    lean_x = math.sin(math.radians(lean)) * h * 0.3 * facing
    hip = (x + lean_x * 0.2, y - h * 0.50)
    neck = (x + lean_x, y - h * 0.84)
    head = (neck[0] + facing * h * 0.01, neck[1] - h * 0.075)
    sh = (neck[0], neck[1] + h * 0.04)

    # 腿
    if back_view:
        for side, ph in ((-1, 0.0), (1, math.pi)):
            lift = max(0.0, math.sin(phase + ph)) * walk
            hx = hip[0] + side * h * 0.05
            foot = (hx + side * h * 0.01, y - lift * h * 0.06)
            knee = ((hx + foot[0]) / 2, (hip[1] + foot[1]) / 2)
            seg(m, (hx, hip[1]), knee, h * 0.07)
            seg(m, knee, foot, h * 0.055)
    else:
        for ph in (0.0, math.pi):
            sw = math.sin(phase + ph)
            thigh = 25 * walk * sw
            bend = (35 * walk * max(0.0, math.sin(phase + ph + 1.2))) + 3
            knee = limb(hip, h * 0.25, thigh, facing)
            foot = limb(knee, h * 0.25, thigh - bend, facing)
            seg(m, hip, knee, h * 0.095)
            seg(m, knee, foot, h * 0.075)
            seg(m, foot, (foot[0] + facing * h * 0.05, foot[1]), h * 0.035)

    # 軀幹
    sw_ = h * (0.12 if back_view else 0.095)
    hw_ = h * (0.08 if back_view else 0.075)
    poly(m, [(sh[0] - sw_, sh[1]), (sh[0] + sw_, sh[1]), (hip[0] + hw_, hip[1] + h * 0.03),
             (hip[0] - hw_, hip[1] + h * 0.03)])
    seg(m, neck, (neck[0], neck[1] - h * 0.03), h * 0.05)
    disk(m, head, h * 0.058)
    poly(m, [(hip[0] - hw_ * 1.15, hip[1] - h * 0.02), (hip[0] + hw_ * 1.15, hip[1] - h * 0.02),
             (hip[0] + hw_ * 1.3, hip[1] + h * 0.13), (hip[0] - hw_ * 1.3, hip[1] + h * 0.13)])
    if hood:
        poly(m, [(head[0] - h * 0.075, head[1] + h * 0.02), (head[0], head[1] - h * 0.09),
                 (head[0] + h * 0.075, head[1] + h * 0.02), (head[0] + h * 0.06, head[1] + h * 0.09),
                 (head[0] - h * 0.06, head[1] + h * 0.09)])

    # 手臂
    hand_r = None
    for (ua, fa), side in ((arm_r, 1), (arm_l, -1)):
        s0 = (sh[0] + (side * sw_ * 0.85 if back_view else 0), sh[1] + h * 0.02)
        el = limb(s0, h * 0.18, ua, facing)
        hd = limb(el, h * 0.17, fa, facing)
        seg(m, s0, el, h * 0.065)
        seg(m, el, hd, h * 0.052)
        disk(m, s0, h * 0.05)
        disk(m, hd, h * 0.024)
        if side == 1:
            hand_r = hd

    tip = None
    if sword is not None and hand_r is not None:
        tip = limb(hand_r, h * 0.48, sword, facing)
        guard_a = limb(hand_r, h * 0.05, sword + 90, facing)
        guard_b = limb(hand_r, h * 0.05, sword - 90, facing)
        seg(m, hand_r, tip, h * 0.018)
        seg(m, guard_a, guard_b, h * 0.016)
        seg(m, hand_r, limb(hand_r, h * 0.07, sword + 180, facing), h * 0.02)
    if spear:
        base = limb(hand_r, h * 0.35, 0, facing)
        tip = limb(hand_r, h * 0.85, 180 + 8, facing)
        seg(m, base, tip, h * 0.014)
        poly(m, [tip, limb(tip, h * 0.06, 170, facing), limb(tip, h * 0.06, 200, facing)])

    # 披風: 由肩膀垂下, 被風吹向後方
    if cloak > 0:
        n = 9
        back = -facing if not back_view else 1
        pts_out = []
        for i in range(n + 1):
            u = i / n
            yy = sh[1] + u * h * 0.62 * cloak
            flutter = math.sin(t * 7 + u * 5) * 0.035 + math.sin(t * 11.3 + u * 9) * 0.015
            dx = (wind * (u ** 1.3) * 0.32 + flutter * (0.3 + wind) * u) * h
            if back_view:
                pts_out.append((sh[0] + sw_ * (1.0 + 0.35 * u) + dx, yy))
            else:
                pts_out.append((sh[0] + back * (sw_ * 0.4 + dx + h * 0.03 * u), yy))
        if back_view:
            left = [(sh[0] - sw_ * (1.0 + 0.35 * (i / n)) + (wind * ((i / n) ** 1.3) * 0.32
                     + (math.sin(t * 7 + i / n * 5 + 1.3) * 0.035) * (0.3 + wind) * (i / n)) * h,
                     sh[1] + (i / n) * h * 0.62 * cloak) for i in range(n + 1)]
            poly(m, pts_out + left[::-1])
        else:
            front = [(sh[0] - back * sw_ * 0.3, sh[1]), (hip[0] - back * hw_ * 0.5, sh[1] + h * 0.62 * cloak * 0.9)]
            poly(m, [front[0]] + pts_out + [front[1]])
    return hand_r, tip


def walk_pose(phase, amount=1.0):
    s = math.sin(phase)
    return dict(walk=amount, phase=phase, arm_r=(-18 * s * amount, -8 * s * amount + 12),
                arm_l=(18 * s * amount, 8 * s * amount + 12))


# ---------- 龍 ----------

def dragon(m, x, y, L, flap, t, facing=1, mouth=0.0):
    """x, y 為胸口位置, L 為身長 px, flap 介於 -1 (下) 與 1 (上)."""
    pts = []
    for i in range(60):
        s = i / 59
        bx = x - facing * (s - 0.25) * L
        by = y + math.sin(s * math.pi * 1.6 - t * 3.0) * 0.05 * L * s + (s - 0.25) * 0.08 * L
        if s < 0.25:   # 頸部向前上方彎
            k = (0.25 - s) / 0.25
            by -= 0.10 * L * k ** 1.5
        pts.append((bx, by))
    for i, (px, py) in enumerate(pts):
        s = i / 59
        if s < 0.25:
            r = 0.018 + 0.03 * (s / 0.25)
        elif s < 0.45:
            r = 0.048 + 0.012 * math.sin((s - 0.25) / 0.2 * math.pi)
        else:
            r = 0.048 * (1 - (s - 0.45) / 0.55) ** 1.4 + 0.004
        disk(m, (px, py), r * L)
    hx, hy = pts[0]
    jaw = 0.06 * L * mouth
    poly(m, [(hx, hy - 0.02 * L), (hx + facing * 0.11 * L, hy - 0.005 * L), (hx + facing * 0.10 * L, hy + 0.01 * L),
             (hx, hy + 0.025 * L)])
    seg(m, (hx, hy + 0.01 * L), (hx + facing * 0.09 * L, hy + 0.02 * L + jaw), 0.022 * L)
    for k in (-1, 1):
        seg(m, (hx - facing * 0.01 * L, hy - 0.02 * L), (hx - facing * 0.07 * L, hy - (0.07 + 0.01 * k) * L), 0.01 * L)
    # 尾刺
    tx, ty = pts[-1]
    poly(m, [(tx, ty - 0.02 * L), (tx - facing * 0.06 * L, ty), (tx, ty + 0.02 * L)])

    # 翅膀: 遠側翅膀稍小
    sx, sy = pts[18]
    for scale, off in ((0.85, -0.03), (1.0, 0.0)):
        up = (0.35 + 0.65 * flap) * scale
        el = (sx - facing * 0.10 * L + off * L, sy - 0.32 * L * up - 0.02 * L)
        wr = (el[0] - facing * 0.18 * L, el[1] - 0.22 * L * up + 0.06 * L)
        fingers = []
        for j, (dx, dy) in enumerate(((-0.30, 0.30), (-0.20, 0.42), (-0.06, 0.48), (0.08, 0.40))):
            fingers.append((wr[0] + facing * (dx - 0.05) * L * scale, wr[1] + dy * L * scale * (0.25 + 0.55 * max(up, 0.0))))
        body_back = pts[30]
        memb = [(sx, sy), el, wr] + fingers[:1] + [((fingers[0][0] + fingers[1][0]) / 2 + facing * 0.02 * L,
                                                    (fingers[0][1] + fingers[1][1]) / 2 - 0.05 * L)] + fingers[1:2] + \
               [((fingers[1][0] + fingers[2][0]) / 2, (fingers[1][1] + fingers[2][1]) / 2 - 0.05 * L)] + fingers[2:3] + \
               [((fingers[2][0] + fingers[3][0]) / 2, (fingers[2][1] + fingers[3][1]) / 2 - 0.04 * L)] + fingers[3:] + \
               [body_back]
        poly(m, memb)
        seg(m, (sx, sy), el, 0.03 * L)
        seg(m, el, wr, 0.022 * L)
        for f in fingers:
            seg(m, wr, f, 0.008 * L)
        seg(m, wr, (wr[0] + facing * 0.03 * L, wr[1] - 0.04 * L), 0.012 * L)
    return pts[0][0] + facing * 0.11 * L, pts[0][1]


# ---------- 鐵王座 ----------

def throne(m, cx, base_y, h, seed=4):
    rng = np.random.default_rng(seed)
    w = h * 0.55
    # 台階
    for i in range(5):
        sw = w * (1.6 - i * 0.12)
        y1 = base_y - i * h * 0.045
        poly(m, [(cx - sw / 2, y1), (cx + sw / 2, y1), (cx + sw / 2 * 0.98, y1 - h * 0.045),
                 (cx - sw / 2 * 0.98, y1 - h * 0.045)])
    seat_y = base_y - h * 0.38
    top = base_y - h * 0.22
    poly(m, [(cx - w * 0.45, top), (cx + w * 0.45, top), (cx + w * 0.40, seat_y), (cx - w * 0.40, seat_y)])
    poly(m, [(cx - w * 0.30, seat_y), (cx + w * 0.30, seat_y), (cx + w * 0.26, base_y - h * 0.85),
             (cx - w * 0.26, base_y - h * 0.85)])
    # 扶手
    for s in (-1, 1):
        poly(m, [(cx + s * w * 0.30, seat_y), (cx + s * w * 0.52, seat_y - h * 0.02),
                 (cx + s * w * 0.52, seat_y + h * 0.04), (cx + s * w * 0.30, seat_y + h * 0.06)])
    # 劍
    for i in range(120):
        u = rng.uniform(-1, 1)
        bx = cx + u * w * 0.42
        by = base_y - h * rng.uniform(0.35, 0.85)
        ang = 180 + u * 55 + rng.normal(0, 10)
        length = h * rng.uniform(0.18, 0.5) * (1.0 - 0.4 * abs(u))
        a = math.radians(ang)
        tip = (bx + length * math.sin(a), by + length * math.cos(a))
        seg(m, (bx, by), tip, max(h * 0.008, 1))
        g = math.radians(ang + 90)
        gp = (bx + length * 0.12 * math.sin(a), by + length * 0.12 * math.cos(a))
        seg(m, (gp[0] - h * 0.02 * math.sin(g), gp[1] - h * 0.02 * math.cos(g)),
            (gp[0] + h * 0.02 * math.sin(g), gp[1] + h * 0.02 * math.cos(g)), max(h * 0.006, 1))
    for i in range(30):   # 側面向外的劍
        s = rng.choice([-1, 1])
        bx = cx + s * w * rng.uniform(0.3, 0.5)
        by = base_y - h * rng.uniform(0.25, 0.55)
        ang = s * rng.uniform(60, 130)
        length = h * rng.uniform(0.1, 0.25)
        a = math.radians(ang)
        seg(m, (bx, by), (bx + length * math.sin(a), by + length * math.cos(a)), max(h * 0.007, 1))


# ---------- 城堡與地形 ----------

def castle(m, x, base_y, h, seed=1):
    rng = np.random.default_rng(seed)
    w = h * 2.2
    poly(m, [(x - w / 2, base_y), (x + w / 2, base_y), (x + w / 2, base_y - h * 0.35), (x - w / 2, base_y - h * 0.35)])
    for i in range(7):
        tx = x - w / 2 + (i + 0.5) * w / 7 + rng.uniform(-0.05, 0.05) * w
        th = h * rng.uniform(0.55, 1.0)
        tw = h * rng.uniform(0.12, 0.2)
        poly(m, [(tx - tw / 2, base_y), (tx + tw / 2, base_y), (tx + tw / 2, base_y - th), (tx - tw / 2, base_y - th)])
        if rng.random() < 0.6:
            poly(m, [(tx - tw * 0.6, base_y - th), (tx + tw * 0.6, base_y - th), (tx, base_y - th - tw * 1.3)])
        else:
            for k in range(3):
                bx = tx - tw / 2 + k * tw / 2.5
                poly(m, [(bx, base_y - th), (bx + tw / 5, base_y - th), (bx + tw / 5, base_y - th - tw * 0.25),
                         (bx, base_y - th - tw * 0.25)])
