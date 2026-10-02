"""jb: 30 秒原創諜報預告 (Bourne 風格) 的配樂與音效, 120 BPM, D 小調. 時間常數與 assemble.py 共用."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts"))
from videokit import SR, Mixer, env, fft_filter, saw, sweep_sine  # noqa: E402

BPM = 120
BEAT = 60 / BPM
DUR = 30.0

# 段落邊界 (秒), 畫面與音訊共用
T_A = 2.0        # 雨夜街頭
T_GLITCH = 5.5   # 訊號干擾轉場
T_B = 6.0        # 車站監視器
T_MATCH = 8.5    # 臉部比對確認
T_MAP = 9.5      # 訊號追蹤地圖
T_LOCK = 11.25   # 地圖鎖定
T_C = 12.0       # 屋頂奔跑, 鼓組進場
T_D = 15.75      # 隧道飛車 (甩鏡)
T_MON = 19.5     # 快剪蒙太奇
MON_CUTS = (19.5, 20.0, 20.5, 21.0)
T_BLACK = 21.5   # 黑場標語
T_E = 22.0       # 清晨橋上
T_TITLE = 26.0   # 片尾字卡

TYPE_START, TYPE_STEP = 0.25, 0.055   # 片頭打字機
LINES = ("ASSET 17", "STATUS: UNKNOWN")

D2, F2, A2, C2, BB1 = 73.42, 87.31, 110.0, 65.41, 58.27
CHORDS = ((D2, F2, A2), (BB1, D2, F2), (D2, F2, A2), (C2, 82.41, 98.0))   # Dm Bb Dm C, 每小節換


def type_times():
    """回傳每個字元的打字時間, 與畫面同步."""
    out, t = [], TYPE_START
    for li, line in enumerate(LINES):
        for _ in line:
            out.append(t)
            t += TYPE_STEP
        t += 0.25
    return out


def build_audio():
    mx = Mixer(DUR, seed=17)
    t, nz = mx.t, mx.noise

    def tone(f, t0, a, d, amp, pan=0.0, rv=0.2):
        mx.add(np.sin(2 * np.pi * f * t) * env(t, t0, a, d) * amp, pan, rv)

    # 低音持續音: 開場到橋段前
    drone = np.sin(2 * np.pi * D2 / 2 * t) + 0.4 * fft_filter(saw(t, D2), hi=200)
    swell = np.clip(t / 1.5, 0, 1) * (0.7 + 0.3 * np.clip((t - 2) / 10, 0, 1))
    mx.add(drone * swell * mx.gate(0, T_BLACK, 0.05) * 0.16, 0, 0.2)

    # 片頭打字聲
    for tt in type_times():
        mx.add(fft_filter(nz, lo=2500, hi=9000) * env(t, tt, 0.0005, 0.012) * 0.25, 0.15, 0.1)
    tone(880, 1.75, 0.002, 0.15, 0.05)

    # 弦樂斷奏 16 分音符, 2s 到蒙太奇結束
    pattern = (0, 0, 2, 0, 1, 0, 2, 1)
    strings = np.zeros(mx.n)
    step = BEAT / 4
    k = 0
    t0 = T_A
    while t0 < T_BLACK - 0.01:
        chord = CHORDS[int((t0 - T_A) // 2) % 4]
        f = chord[pattern[k % 8]] * 4
        g = mx.gate(t0, t0 + step * 0.8, 0.004)
        strings += (saw(t, f) + saw(t, f * 1.004)) * env(t, t0, 0.006, 0.07) * g * (1.0 if k % 4 == 0 else 0.7)
        t0 += step
        k += 1
    level = 0.035 + 0.045 * np.clip((t - T_A) / (T_C - T_A), 0, 1)
    mx.add(fft_filter(strings, lo=120, hi=2200) * level, -0.3, 0.3)

    # 貝斯 8 分音符, 監視器段起
    bass = np.zeros(mx.n)
    t0 = T_B
    while t0 < T_BLACK - 0.01:
        root = CHORDS[int((t0 - T_A) // 2) % 4][0]
        bass += saw(t, root) * env(t, t0, 0.004, 0.16) * mx.gate(t0, t0 + BEAT / 2 * 0.9, 0.004)
        t0 += BEAT / 2
    mx.add(fft_filter(bass, hi=320) * 0.22 * (mx.gate(T_B, T_MAP + 1.9, 0.05) + mx.gate(T_C, T_BLACK, 0.01)), 0, 0.05)

    # 腳踏鈸
    t0 = T_B
    while t0 < T_BLACK - 0.01:
        on = (t0 - T_B) / step
        amp = 0.05 if t0 < T_C else 0.09
        if int(round(on)) % 2 == 1 or t0 >= T_C:
            mx.add(fft_filter(nz, lo=7000) * env(t, t0, 0.0005, 0.025) * amp, 0.3, 0.05)
        t0 += step

    # 訊號干擾
    burst = fft_filter(nz, lo=400, hi=7000) * (np.sign(np.sin(2 * np.pi * 37 * t)) * 0.5 + 0.5)
    mx.add(burst * mx.gate(T_GLITCH, T_B, 0.01) * 0.3, 0, 0.1)
    mx.add(sweep_sine(t, T_GLITCH + 0.45, 300, 60, 0.05) * env(t, T_GLITCH + 0.45, 0.002, 0.2) * 0.5)

    # 監視器嗶聲與比對確認
    for i in range(4):
        tone(1760, T_B + 0.5 + i * 0.5, 0.002, 0.04, 0.04, 0.4, 0.1)
    tone(1175, T_MATCH, 0.002, 0.09, 0.09, 0, 0.2)
    tone(1568, T_MATCH + 0.12, 0.002, 0.25, 0.09, 0, 0.3)
    mx.boom(T_MATCH, 0.35)

    # 地圖: 資料嗶聲, 鎖定, riser 後先靜再爆發
    rng = np.random.default_rng(3)
    for tt in np.sort(rng.uniform(T_MAP + 0.1, T_LOCK, 14)):
        tone(rng.choice((2093, 2637, 3136)), tt, 0.001, 0.03, 0.025, rng.uniform(-0.6, 0.6), 0.2)
    tone(988, T_LOCK, 0.002, 0.4, 0.08, 0, 0.4)
    mx.riser(T_LOCK, T_C - 0.03, 0.55)

    # 鼓組: 屋頂到蒙太奇
    mx.boom(T_C, 1.0)
    t0 = T_C
    while t0 < T_BLACK - 0.01:
        b = round((t0 - T_C) / BEAT)
        mx.kick(t0, 0.8)
        if b % 2 == 1:
            mx.add(fft_filter(nz, lo=900, hi=6000) * env(t, t0, 0.001, 0.09) * 0.32, 0, 0.35)
        t0 += BEAT
    for tt in (15.0, 15.25, 15.375, 15.5, 15.625):
        mx.taiko(tt, 0.7)

    # 甩鏡 whoosh 與隧道車聲
    u = np.exp(-((t - T_D) / 0.12) ** 2)
    mx.add(fft_filter(nz, lo=500, hi=5000) * u * 0.45, 0, 0.2)
    eng_f = 70 + 30 * np.clip((t - T_D) / 3.5, 0, 1)
    eng = saw(np.cumsum(eng_f) / SR, 1.0) + 0.5 * saw(np.cumsum(eng_f * 2.01) / SR, 1.0)
    mx.add(fft_filter(eng, hi=400) * mx.gate(T_D, T_MON, 0.3) * 0.08, 0.2, 0.1)
    for tt in np.arange(T_D + 0.2, T_MON, 0.62):
        mx.add(fft_filter(nz, lo=300, hi=2500) * np.exp(-((t - tt) / 0.08) ** 2) * 0.12, -0.4, 0.2)

    # 蒙太奇: 每個剪接點一記重擊, riser 到黑場
    for tt in MON_CUTS:
        mx.braam(tt, amp=0.42)
    mx.riser(20.3, T_BLACK - 0.02, 0.45)
    mx.boom(T_BLACK, 0.7)

    # 橋段: 襯底和鐘聲, 標題前靜音
    pad = sum(fft_filter(saw(t, f * 2) + saw(t, f * 2.006), hi=700) for f in (D2, F2, A2))
    mx.add(pad * mx.gate(T_E, T_TITLE - 0.35, 1.2) * 0.035, -0.2, 0.6)
    for tt, f in ((T_E + 0.1, 880.0), (T_E + 1.6, 698.46), (T_E + 3.1, 587.33)):
        bell = sum(np.sin(2 * np.pi * f * p * t) * a for p, a in ((1, 1.0), (2.0, 0.4), (3.01, 0.2)))
        mx.add(bell * env(t, tt, 0.003, 1.3) * 0.05, 0, 0.7)

    # 片尾
    mx.braam(T_TITLE, amp=1.6)
    mx.add(sweep_sine(t, T_TITLE, 90, 26, 0.3) * env(t, T_TITLE, 0.003, 2.2) * 0.55)
    mx.add(fft_filter(nz, lo=1500, hi=8000) * mx.gate(T_TITLE, T_TITLE + 0.3, 0.005) * 0.12, 0, 0.2)
    bell = sum(np.sin(2 * np.pi * 587.33 * p * t) * a for p, a in ((1, 1.0), (2.0, 0.5), (3.01, 0.25)))
    mx.add(bell * env(t, 27.6, 0.003, 1.2) * 0.05, 0, 0.8)

    return mx.master(fade_out=0.8)


if __name__ == "__main__":
    from videokit import loudness_report
    print(loudness_report(build_audio(), step=1.5))
