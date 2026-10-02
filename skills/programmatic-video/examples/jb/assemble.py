"""jb: 30 秒原創諜報預告 (Bourne 風格, 虛構角色): AI 生成鏡頭 + 程式做的監控介面, 地圖, 字卡, 剪接, 調色與配樂.

素材在 gen/ (PixelForge 生成): shot_a.mp4 ... shot_e.mp4
用法:
    python assemble.py               輸出 bourne.mp4 (1280x720, 24fps)
    python assemble.py 60 200 500    只輸出指定影格 PNG 到 check/
"""
import math
import os
import sys

import av
import cv2
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts"))
from videokit import col, ease, ease_out, encode, place, text_mask, to_u8, whip  # noqa: E402
from audio import (DUR, LINES, MON_CUTS, T_A, T_B, T_BLACK, T_C, T_D, T_E, T_GLITCH,  # noqa: E402
                   T_LOCK, T_MAP, T_MATCH, T_MON, T_TITLE, build_audio, type_times)

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS = 1280, 720, 24
N = int(DUR * FPS)
BAR = 92                      # 2.39:1 遮幅
BAHN = "bahnschrift.ttf"
MONO = "consola.ttf"

# (素材, 素材起點, 時間軸起點, 終點, 速度)
CUTS = (("a", 0.2, T_A, T_GLITCH, 1.0),
        ("b", 2.0, T_B, T_MAP, 0.85),
        ("c2", 0.2, T_C, T_D, 0.55),
        ("d", 0.2, T_D, T_MON, 1.0),
        ("a", 1.2, MON_CUTS[0], MON_CUTS[1], 1.0),
        ("c2", 0.6, MON_CUTS[1], MON_CUTS[2], 1.0),
        ("b", 4.0, MON_CUTS[2], MON_CUTS[3], 1.0),
        ("d", 2.6, MON_CUTS[3], T_BLACK, 1.0),
        ("e", 0.6, T_E, T_TITLE, 1.0))
B_SRC0 = 2.0                  # 監視器鏡頭的素材起點
TARGET_B = (70, 770, 605)     # 追蹤起點: (素材格, x, y), 1280x720 座標, 看過素材後設定

_CLIPS = {}
_TRACK = None
_MAP = None


# ---------- 素材 ----------

def fit(fr):
    h, w = fr.shape[:2]
    s = max(W / w, H / h)
    big = cv2.resize(fr, (int(math.ceil(w * s)), int(math.ceil(h * s))), interpolation=cv2.INTER_AREA)
    y0, x0 = (big.shape[0] - H) // 2, (big.shape[1] - W) // 2
    return big[y0:y0 + H, x0:x0 + W]


def clip(name):
    if name not in _CLIPS:
        c = av.open(os.path.join(HERE, "gen", f"shot_{name}.mp4"))
        if name == "b":   # 以底部為基準放大 1.2 倍, 讓走道上的人物離開下方遮幅
            _CLIPS[name] = [cv2.resize(f.to_ndarray(format="rgb24")[117:704, 118:1162], (W, H), interpolation=cv2.INTER_CUBIC)
                            for f in c.decode(video=0)]
        else:
            _CLIPS[name] = [fit(f.to_ndarray(format="rgb24")) for f in c.decode(video=0)]
        c.close()
    return _CLIPS[name]


def frame_at(name, src_t):
    fr = clip(name)
    return fr[min(max(int(round(src_t * FPS)), 0), len(fr) - 1)].astype(np.float32) / 255


def track_b():
    """在監視器鏡頭裡以樣板比對追蹤一位行人, 結果快取到檔案."""
    global _TRACK
    if _TRACK is not None:
        return _TRACK
    path = os.path.join(HERE, "gen", "track_b.npy")
    if os.path.exists(path):
        _TRACK = np.load(path)
        return _TRACK
    frs = [cv2.cvtColor(f, cv2.COLOR_RGB2GRAY) for f in clip("b")]
    i0, x0_, y0_ = TARGET_B
    r, s = 24, 28
    pts = {}
    for order in (range(i0, len(frs)), range(i0, -1, -1)):
        x, y = x0_, y0_
        tpl = frs[i0][y - r:y + r, x - r:x + r]
        for i in order:
            g = frs[i]
            ya, xa = max(y - r - s, 0), max(x - r - s, 0)
            win = g[ya:min(y + r + s, H), xa:min(x + r + s, W)]
            res = cv2.matchTemplate(win, tpl, cv2.TM_CCOEFF_NORMED)
            _, _, _, loc = cv2.minMaxLoc(res)
            x, y = xa + loc[0] + r, ya + loc[1] + r
            cur = g[y - r:y + r, x - r:x + r]
            if cur.shape == tpl.shape:
                tpl = (0.85 * tpl + 0.15 * cur).astype(np.uint8)
            pts[i] = (x, y)
    pts = [pts[i] for i in range(len(frs))]
    p = np.array(pts, np.float32)
    k = np.ones(5) / 5
    p = np.stack([np.convolve(np.pad(p[:, i], 2, mode="edge"), k, "valid") for i in range(2)], 1)
    np.save(path, p)
    _TRACK = p
    return p


# ---------- 調色與後製 ----------

GRAIN = np.random.default_rng(5).normal(0, 1, (4, H, W, 1)).astype(np.float32)
YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)
VIG = 1 - 0.28 * (((XX - W / 2) / (W / 2)) ** 2 + ((YY - H / 2) / (H / 2)) ** 2)[..., None]


def grade(img, warm=1.0):
    """諜報片的冷青陰影加暖色高光, 低飽和."""
    lum = img.mean(axis=2, keepdims=True)
    img = lum + (img - lum) * 0.82
    shadow = np.clip(1 - lum * 2.2, 0, 1)
    high = np.clip(lum * 1.6 - 0.6, 0, 1)
    img = img + shadow * col(-0.015, 0.006, 0.02) + high * col(0.03, 0.01, -0.02) * warm
    img = np.clip(img, 0, 1)
    return img * img * (3 - 2 * img) * 0.4 + img * 0.6


def finish(img, f):
    img = img * VIG + GRAIN[f % 4] * 0.014
    img = np.clip(img, 0, 1)
    img[:BAR] = 0
    img[H - BAR:] = 0
    return img


def glitch(img, amt, seed):
    """訊號干擾: 水平切片錯位, RGB 分離, 雜訊塊."""
    if amt <= 0.01:
        return img
    rng = np.random.default_rng(seed)
    out = img.copy()
    for _ in range(int(6 + 18 * amt)):
        y0 = rng.integers(0, H - 8)
        h = rng.integers(3, int(10 + 60 * amt))
        out[y0:y0 + h] = np.roll(out[y0:y0 + h], int(rng.normal(0, 80 * amt)), axis=1)
    sh = int(10 * amt)
    out[..., 0] = np.roll(out[..., 0], sh, axis=1)
    out[..., 2] = np.roll(out[..., 2], -sh, axis=1)
    for _ in range(int(4 * amt)):
        y0, x0 = rng.integers(0, H - 40), rng.integers(0, W - 120)
        out[y0:y0 + rng.integers(8, 40), x0:x0 + rng.integers(40, 160)] = rng.random()
    return out


def text_left(img, s, fontname, size, x, cy, color, alpha=1.0, tracking=0.0):
    if not s:
        return
    m = text_mask(s, fontname, size, tracking)
    place(img, m, x + m.shape[1] / 2 - 10, cy, color, alpha)


def text_center(img, s, fontname, size, cy, color, alpha=1.0, tracking=0.0):
    m = text_mask(s, fontname, size, tracking)
    if m.shape[1] > W - 40:
        c0 = (m.shape[1] - (W - 40)) // 2
        m = m[:, c0:c0 + W - 40]
    place(img, m, W / 2, cy, color, alpha)


def brackets(img, cx, cy, half, color, thick=2, arm=12, tall=1.6):
    m = np.zeros((H, W), np.uint8)
    x0, y0, x1, y1 = int(cx - half), int(cy - half * tall), int(cx + half), int(cy + half * tall)
    for (px, py, dx, dy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
        cv2.line(m, (px, py), (px + dx * arm, py), 255, thick, cv2.LINE_AA)
        cv2.line(m, (px, py), (px, py + dy * arm), 255, thick, cv2.LINE_AA)
    a = (m.astype(np.float32) / 255)[..., None]
    img *= 1 - a
    img += a * color


# ---------- 程式鏡頭 ----------

def shot_cold(t):
    img = np.zeros((H, W, 3), np.float32)
    tt = type_times()
    k = sum(1 for x in tt if x <= t)
    shown = []
    for line in LINES:
        n = min(k, len(line))
        shown.append(line[:n])
        k -= n
    y = (H / 2 - 26, H / 2 + 22)
    for i, s in enumerate(shown):
        text_left(img, s, MONO, 30, 470, y[i], col(0.86, 0.9, 0.88) if i == 0 else col(0.95, 0.32, 0.26))
    cur = len(shown[-1]) if shown[-1] else len(shown[0])
    line_i = 1 if shown[-1] else 0
    if int(t * 4) % 2 == 0:
        x = 470 + text_mask(shown[line_i] or " ", MONO, 30).shape[1] - 16 if cur else 470
        img[int(y[line_i] - 14):int(y[line_i] + 14), int(x):int(x) + 14] = 0.85
    text_left(img, "INTERNAL // EYES ONLY", MONO, 14, 470, H / 2 - 74, col(0.4, 0.45, 0.45), ease(t / 0.4))
    return img * (1 - ease((t - 1.85) / 0.15))


def map_base():
    global _MAP
    if _MAP is not None:
        return _MAP
    rng = np.random.default_rng(11)
    S = 1600
    m = np.zeros((S, S), np.uint8)
    for i in range(70):
        if i % 2:
            y = rng.uniform(0, S)
            cv2.line(m, (0, int(y)), (S, int(y + rng.normal(0, 120))), 120 if i % 7 else 230, 1 + (i % 7 == 0), cv2.LINE_AA)
        else:
            x = rng.uniform(0, S)
            cv2.line(m, (int(x), 0), (int(x + rng.normal(0, 120)), S), 120 if i % 7 else 230, 1 + (i % 7 == 0), cv2.LINE_AA)
    # 小巷: 短線段, 讓街區有密度
    alley = np.zeros((S, S), np.uint8)
    for _ in range(900):
        x, y = rng.uniform(0, S, 2)
        ang = rng.choice((0.0, math.pi / 2)) + rng.normal(0, 0.12)
        ln = rng.uniform(30, 110)
        cv2.line(alley, (int(x), int(y)), (int(x + ln * math.cos(ang)), int(y + ln * math.sin(ang))), 255, 1, cv2.LINE_AA)
    blocks = cv2.resize(rng.random((40, 40)).astype(np.float32), (S, S), interpolation=cv2.INTER_NEAREST)
    river = np.zeros((S, S), np.uint8)
    xs = np.arange(0, S, 8)
    pts = np.stack([xs, 980 + 160 * np.sin(xs / 260) + 60 * np.sin(xs / 90)], 1).astype(np.int32)
    cv2.polylines(river, [pts], False, 255, 46, cv2.LINE_AA)
    road = m.astype(np.float32) / 255
    rv = cv2.GaussianBlur(river.astype(np.float32) / 255, (0, 0), 2)
    img = np.ones((S, S, 3), np.float32) * col(0.015, 0.028, 0.04) * (0.8 + 0.5 * blocks[..., None])
    img += road[..., None] * col(0.09, 0.2, 0.24) * (1 - rv[..., None])
    img += (alley.astype(np.float32) / 255)[..., None] * col(0.04, 0.09, 0.11) * (1 - rv[..., None])
    img = img * (1 - rv[..., None]) + rv[..., None] * col(0.02, 0.06, 0.1)
    grid = ((np.arange(S) % 100) == 0).astype(np.float32)
    img += (grid[None, :, None] + grid[:, None, None]) * 0.025
    _MAP = img
    return img


ROUTE = np.array([(300, 1350), (420, 1180), (610, 1120), (700, 930), (760, 820), (930, 760), (1010, 640), (1120, 600)], np.float32)
MAP_TARGET = ROUTE[-1]


def shot_map(t):
    lt = t - T_MAP
    base = map_base()
    z = 1.0 + 0.22 * ease_out(lt / 2.5)
    cx, cy = 800 + (MAP_TARGET[0] - 800) * ease(lt / 2.5) * 0.6, 820 + (MAP_TARGET[1] - 820) * ease(lt / 2.5) * 0.6
    sc = W / 1200 * z
    M = np.float32([[sc, 0, W / 2 - cx * sc], [0, sc, H / 2 - cy * sc]])
    img = cv2.warpAffine(base, M, (W, H))
    # 路線逐段畫出
    seg = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(ROUTE, axis=0), axis=1))])
    L = seg[-1] * ease_out(lt / 1.7)
    pts = [ROUTE[0]]
    for i in range(1, len(ROUTE)):
        if seg[i] <= L:
            pts.append(ROUTE[i])
        else:
            u = (L - seg[i - 1]) / (seg[i] - seg[i - 1])
            pts.append(ROUTE[i - 1] + (ROUTE[i] - ROUTE[i - 1]) * max(u, 0))
            break
    p = np.array(pts, np.float32)
    p = (p * sc + [W / 2 - cx * sc, H / 2 - cy * sc]).astype(np.int32)
    m = np.zeros((H, W), np.uint8)
    cv2.polylines(m, [p], False, 255, 3, cv2.LINE_AA)
    a = m.astype(np.float32) / 255
    glow = cv2.GaussianBlur(a, (0, 0), 6)
    img += (a * 0.9 + glow * 1.2)[..., None] * col(1.0, 0.28, 0.2)
    head = p[-1]
    tx, ty = (MAP_TARGET * sc + [W / 2 - cx * sc, H / 2 - cy * sc])
    locked = t >= T_LOCK
    if locked:
        r = 18 + 40 * ((t - T_LOCK) * 1.6 % 1)
        mm = np.zeros((H, W), np.uint8)
        cv2.circle(mm, (int(tx), int(ty)), int(r), 255, 2, cv2.LINE_AA)
        cv2.circle(mm, (int(tx), int(ty)), 7, 255, -1, cv2.LINE_AA)
        cv2.line(mm, (int(tx) - 60, int(ty)), (int(tx) - 26, int(ty)), 255, 1, cv2.LINE_AA)
        cv2.line(mm, (int(tx) + 26, int(ty)), (int(tx) + 60, int(ty)), 255, 1, cv2.LINE_AA)
        a2 = mm.astype(np.float32)[..., None] / 255 * (1 - 0.6 * ((t - T_LOCK) * 1.6 % 1))
        img += a2 * col(1.0, 0.3, 0.22)
    else:
        img[max(head[1] - 4, 0):head[1] + 4, max(head[0] - 4, 0):head[0] + 4] = col(1, 0.9, 0.85)
    # 介面文字
    g = col(0.55, 0.8, 0.78)
    text_left(img, "SIGNAL TRACE // SECTOR 7", MONO, 16, 60, BAR + 34, g)
    status = "TARGET LOCKED" if locked else "TRIANGULATING" + "." * (int(lt * 6) % 4)
    text_left(img, status, MONO, 22, 60, BAR + 64, col(1.0, 0.35, 0.28) if locked else g)
    lat = 52.5163 + 0.0042 * ease(lt / 1.7)
    lon = 13.3777 + 0.0123 * ease(lt / 1.7)
    text_left(img, f"{lat:.4f} N   {lon:.4f} E", MONO, 16, W - 330, H - BAR - 30, g)
    return img


def cctv(img, st, f, box=True):
    """監視器介面. st 是 shot_b 的素材時間."""
    lt = (st - B_SRC0) / 0.85
    lum = img.mean(axis=2, keepdims=True)
    img = lum * col(0.78, 0.96, 0.84) * 1.05
    img = img * (0.93 + 0.07 * ((YY[..., None] % 3) > 0))
    img = img + GRAIN[f % 4] * 0.03
    p = track_b()
    src_i = min(int(round(st * FPS)), len(p) - 1)
    x, y = p[src_i]
    matched = lt >= T_MATCH - T_B
    c = col(1.0, 0.3, 0.25) if matched else col(0.92, 0.95, 0.92)
    vis = box and y < H - BAR - 26
    if vis:
        brackets(img, x, y + 4, 30, c, tall=2.3)
    pct = 61.0 + 36.4 * ease((lt - 0.4) / (T_MATCH - T_B - 0.4))
    label = f"MATCH {pct:4.1f}%" if not matched else "MATCH CONFIRMED  97.4%"
    if vis:
        text_left(img, label, MONO, 16, x + 38, y - 56, c)
    w = col(0.9, 0.93, 0.9)
    s = int(7 + lt)
    text_left(img, f"CAM 04  CONCOURSE   2026-10-02  23:41:{s:02d}", MONO, 15, 40, BAR + 26, w)
    if int(lt * 2) % 2 == 0:
        cv2.circle(img, (W - 92, BAR + 26), 6, (1.0, 0.2, 0.2), -1, cv2.LINE_AA)
    text_left(img, "REC", MONO, 15, W - 80, BAR + 26, w)
    return img


def shot_title(t, f):
    lt = t - T_TITLE
    img = np.zeros((H, W, 3), np.float32)
    # 背景: 橋段最後一格, 大幅模糊壓暗
    bg = grade(frame_at("e", 0.6 + (T_TITLE - T_E)))
    bg = cv2.GaussianBlur(bg, (0, 0), 14) * 0.16
    img += bg
    a = ease(lt / 0.35)
    tr = 30 - 18 * ease_out(lt / 2.5)
    j = max(0.0, 1 - lt / 0.45)
    text_center(img, "ASROCK AI CENTER", BAHN, 76, H / 2 - 14, col(0.95, 0.95, 0.95), a, tr)
    a2 = ease((lt - 0.9) / 0.6)
    text_center(img, "GENERATED SHOTS  \u00b7  CODED FINISH", MONO, 19, H / 2 + 68, col(0.82, 0.85, 0.87), a2, 5)
    lw = int(120 * ease_out((lt - 0.5) / 0.8))
    if lw > 0:
        img[int(H / 2 + 36):int(H / 2 + 38), W // 2 - lw:W // 2 + lw] = col(0.9, 0.28, 0.22)
    img = glitch(img, j, f)
    return img * (1 - ease((lt - 3.3) / 0.6))


# ---------- 合成 ----------

def gen_frame(t):
    for name, s0, a, b, sp in CUTS:
        if a <= t < b:
            return name, s0 + (t - a) * sp, a, b
    return None


def render(f):
    t = f / FPS
    if t < T_A:
        img = shot_cold(t)
    elif T_GLITCH <= t < T_B:
        u = (t - T_GLITCH) / (T_B - T_GLITCH)
        src = grade(frame_at("a", 0.2 + (T_GLITCH - T_A))) if u < 0.5 else cctv(frame_at("b", B_SRC0), B_SRC0, f)
        img = glitch(src, 0.4 + 0.6 * math.sin(math.pi * u), f)
    elif T_MAP <= t < T_C:
        img = shot_map(t)
        if t < T_MAP + 0.12:
            img = glitch(img, 0.7, f)
    elif T_BLACK <= t < T_E:
        img = np.zeros((H, W, 3), np.float32)
        lt = t - T_BLACK
        text_center(img, "NOW HE REMEMBERS.", BAHN, 40, H / 2, col(0.93, 0.93, 0.93), ease(lt / 0.12) * (1 - ease((lt - 0.4) / 0.1)), 10)
    elif t >= T_TITLE:
        img = shot_title(t, f)
    else:
        name, st, a, b = gen_frame(t)
        img = frame_at(name, st)
        if name == "b":
            img = cctv(img, st, f, box=(a == T_B))
        else:
            img = grade(img)
        if name == "e":
            s = 1 + 0.05 * ease((t - T_E) / 4)
            M = np.float32([[s, 0, W / 2 - s * W / 2], [0, s, H / 2 - s * H / 2]])
            img = cv2.warpAffine(img, M, (W, H), borderMode=cv2.BORDER_REFLECT)
            img *= ease((t - T_E) / 0.5)
        # 甩鏡: 屋頂到隧道
        if abs(t - T_D) < 0.17:
            img = whip(img, 1 - abs(t - T_D) / 0.17)
        # 剪接閃光
        if a in (T_C,) + MON_CUTS and t - a < 0.12:
            img = img + 0.35 * math.exp(-(t - a) / 0.04)
        # 蒙太奇標語
        if T_MON <= t < T_BLACK:
            lt = t - T_MON
            line = "THEY TOOK HIS NAME." if lt < 1.0 else "NOT HIS INSTINCTS."
            img = img * 0.7
            text_center(img, line, BAHN, 40, H - BAR - 60, col(0.95, 0.95, 0.95), 1.0, 10)
        if name == "a" and a == T_A:
            img *= ease((t - T_A) / 0.25)
    return to_u8(finish(img, f))


if __name__ == "__main__":
    if len(sys.argv) > 1:
        os.makedirs(os.path.join(HERE, "check"), exist_ok=True)
        from PIL import Image
        for s in sys.argv[1:]:
            f = int(s)
            Image.fromarray(render(f)).save(os.path.join(HERE, "check", f"f{f:03d}.png"))
            print("check", f)
    else:
        audio = build_audio()
        encode(os.path.join(HERE, "bourne.mp4"), render, N, FPS, audio, size=(W, H), workers=6, crf=20)
