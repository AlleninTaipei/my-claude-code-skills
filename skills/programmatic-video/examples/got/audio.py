"""原創史詩配樂: 96 BPM, D 小調. 大提琴固定音型, 低音銅管 braam, 太鼓, 合唱, 音效."""
import numpy as np

SR = 48000
BEAT = 0.625
BAR = 2.5
CLASHES = (16.25, 17.5, 18.75, 19.375)

D2, F2, A2, D3, E3, F3, G3, A3 = 73.42, 87.31, 110.0, 146.83, 164.81, 174.61, 196.0, 220.0


def fft_filter(x, lo=None, hi=None, order=2):
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
        return np.where(x < 0, 0.0, np.where(x < attack, x / max(attack, 1e-4), np.exp(-np.maximum(x - attack, 0) / decay)))


def saw(t, f):
    return 2 * ((t * f) % 1.0) - 1


def sweep_sine(t, t0, f_hi, f_lo, k):
    x = np.clip(t - t0, 0, None)
    return np.sin(2 * np.pi * np.cumsum(f_lo + (f_hi - f_lo) * np.exp(-x / k)) / SR)


def reverb(x, seconds=3.5, decay=0.9, seed=0):
    n = int(SR * seconds)
    rng = np.random.default_rng(seed)
    ir = rng.standard_normal(n) * np.exp(-np.arange(n) / (SR * decay))
    ir = fft_filter(ir, hi=5000)
    ir /= np.sqrt((ir ** 2).sum())
    size = 1 << int(np.ceil(np.log2(len(x) + n)))
    return np.fft.irfft(np.fft.rfft(x, size) * np.fft.rfft(ir, size), size)[:len(x)]


def build_audio(dur):
    n = int(SR * dur)
    t = np.arange(n) / SR
    rng = np.random.default_rng(31)
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

    bands_f = np.geomspace(120, 9000, 9)
    bands = [fft_filter(noise, lo=f / 1.5, hi=f * 1.5) for f in bands_f]

    def swept_noise(f_curve):
        lf = np.log(np.clip(f_curve, 120, 9000))
        return sum(b * np.exp(-((lf - np.log(f)) / 0.35) ** 2) for f, b in zip(bands_f, bands))

    def braam(t0, amp=1.0, notes=(D2 / 2, D2, A2, D3)):
        g = env(t, t0, 0.04, 1.6)
        open_ = 200 + 1800 * env(t, t0, 0.08, 0.7)
        sig = sum(saw(t, f) + saw(t, f * 1.007) for f in notes)
        # 以三段固定濾波近似隨時間打開的濾波器
        lo = fft_filter(sig, hi=250)
        mid = fft_filter(sig, hi=900)
        hi_ = fft_filter(sig, hi=2500)
        w = np.clip((open_ - 200) / 1800, 0, 1)
        out = lo * (1 - w) + (mid * 0.6 + hi_ * 0.4) * w
        add(out * g * 0.12 * amp, 0, 0.35)
        add(sweep_sine(t, t0, 120, 30, 0.08) * env(t, t0, 0.003, 1.0) * 0.7 * amp, 0, 0.1)
        add(fft_filter(noise, hi=1500) * env(t, t0, 0.001, 0.3) * 0.35 * amp, 0, 0.5)

    def taiko(t0, amp=1.0):
        add(sweep_sine(t, t0, 140, 55, 0.04) * env(t, t0, 0.002, 0.35) * 0.7 * amp, 0, 0.4)
        add(fft_filter(noise, lo=80, hi=900) * env(t, t0, 0.001, 0.06) * 0.35 * amp, 0, 0.5)

    def riser(a, b, amp=0.5):
        u = np.clip((t - a) / (b - a), 0, 1)
        add(swept_noise(200 * 40 ** u) * u ** 2.5 * gate(a, b, 0.008) * amp, 0, 0.3)

    # 風聲, 開場與行軍段
    wind_env = gate(0, 10.0, 0.5) * (0.6 + 0.4 * np.sin(t * 0.9) ** 2) + gate(25, 30, 1.0) * 0.4
    wind = swept_noise(500 + 400 * np.sin(t * 0.7) + 250 * np.sin(t * 1.9))
    add(wind * wind_env * 0.22, 0.2, 0.2)

    # 低音持續音
    drone = (np.sin(2 * np.pi * D2 / 2 * t) + 0.5 * fft_filter(saw(t, D2), hi=220)) * gate(0, 24.35, 1.0)
    add(drone * np.clip(t / 3, 0, 1) * 0.22, 0, 0.2)

    # 大提琴固定音型 (原創): 8 分音符, 2.5s 起
    pattern = (D3, A2, F3, A2, D3, A2, E3, A2, D3, A2, G3, A2, F3, A2, E3, A2)
    cello = np.zeros(n)
    step = BEAT / 2
    k = 0
    t0 = 2.5
    while t0 < 24.3:
        f = pattern[k % len(pattern)]
        if t0 >= 10.0 and t0 < 20.0:
            f_mul = 1.0
        else:
            f_mul = 1.0
        vib = 1 + 0.004 * np.sin(2 * np.pi * 5.5 * t)
        seg_env = env(t, t0, 0.035, 0.22) * gate(t0, t0 + step * 0.95, 0.01)
        cello += saw(t * vib, f * f_mul) * seg_env
        k += 1
        t0 += step
    cello = fft_filter(cello, hi=1400) + fft_filter(cello, lo=2000, hi=4000) * 0.1
    cello_amp = np.clip((t - 2.5) / 2.5, 0, 1) * 0.12 + np.clip((t - 10) / 0.1, 0, 1) * 0.04
    add(cello * cello_amp * gate(2.5, 24.35, 0.05), -0.25, 0.4)
    # 低八度加厚, 10s 起
    add(fft_filter(np.roll(cello, 0), hi=600) * gate(10.0, 20.0, 0.05) * 0.05, 0.25, 0.3)

    # 行軍鼓 5 - 10s
    for i in range(int(5.0 / BEAT)):
        tb = 5.0 + i * BEAT
        taiko(tb, 0.45 if i % 2 else 0.7)
        add(fft_filter(noise, lo=1500, hi=6000) * env(t, tb + BEAT / 2, 0.001, 0.05) * 0.10, 0.3, 0.4)

    # 10 - 20s: 重鼓組
    for i in range(int(10.0 / (BEAT / 2))):
        tb = 10.0 + i * BEAT / 2
        pos = i % 8
        if pos in (0, 3, 4, 6):
            taiko(tb, 1.0 if pos == 0 else 0.6)
        if pos in (2, 6):
            add(fft_filter(noise, lo=1200, hi=7000) * env(t, tb, 0.001, 0.09) * 0.25, 0, 0.5)

    # 龍吼與火焰
    for t0, dur_ in ((10.6, 1.0), (13.0, 0.8)):
        u = np.clip((t - t0) / dur_, 0, 1)
        f0 = 380 + 300 * np.sin(np.pi * u) - 150 * u
        ph = 2 * np.pi * np.cumsum(f0 * (1 + 0.03 * np.sin(2 * np.pi * 31 * t))) / SR
        roar = np.sign(np.sin(ph)) * 0.6 + np.sin(2 * ph) * 0.4
        roar = fft_filter(roar, lo=300, hi=3500) + fft_filter(noise, lo=800, hi=4000) * 0.4
        add(roar * np.sin(np.pi * u) ** 0.6 * gate(t0, t0 + dur_, 0.02) * 0.22, 0.2, 0.6)
    fire_env = np.clip((t - 12.0) / 0.3, 0, 1) * np.clip((13.9 - t) / 0.4, 0, 1)
    add(fft_filter(noise, hi=900) * fire_env * 0.5, 0, 0.3)
    add(swept_noise(np.full(n, 1800.0)) * fire_env * 0.15, 0.3, 0.3)

    # 劍擊
    for i, tc in enumerate(CLASHES):
        clang = sum(np.sin(2 * np.pi * f * t) * a for f, a in ((1460, 1.0), (2370, 0.7), (3520, 0.5), (5130, 0.3)))
        add(clang * env(t, tc, 0.001, 0.35) * 0.16, (-0.3, 0.3)[i % 2], 0.7)
        add(fft_filter(noise, lo=2000) * env(t, tc, 0.0005, 0.03) * 0.5, 0, 0.3)
        add(swept_noise(300 * 25 ** np.clip((t - tc + 0.18) / 0.18, 0, 1)) * gate(tc - 0.18, tc, 0.005) * 0.25)

    # 合唱 'ah': 15 - 24.3s
    choir_src = sum(saw(t, f * (1 + 0.003 * k_)) for k_, f in enumerate((D3, F3, A3, D3 * 2)))
    choir = sum(fft_filter(choir_src, lo=fm / 1.25, hi=fm * 1.25) * a for fm, a in ((800, 1.0), (1150, 0.6), (2900, 0.2)))
    ch_env = np.clip((t - 15) / 3, 0, 1) * gate(15, 24.35, 0.3) * (0.6 + 0.4 * np.clip((t - 20) / 2, 0, 1))
    add(choir * ch_env * 0.05, 0, 0.8)

    # 王座廳: 腳步與心跳
    for i in range(int(4.2 / BEAT) + 1):
        tb = 20.2 + i * BEAT
        add(fft_filter(noise, lo=100, hi=1500) * env(t, tb, 0.002, 0.05) * 0.25, 0, 0.7)
    for i in range(4):
        tb = 20.0 + i * 1.25
        taiko(tb, 0.35)
        taiko(tb + 0.2, 0.25)

    # 段落 braam 與 riser
    for tb, amp in ((5.0, 0.8), (10.0, 1.0), (15.0, 1.0), (20.0, 1.0)):
        braam(tb, amp)
        riser(tb - 1.2, tb - 0.02, 0.35)
    riser(23.0, 24.35, 0.6)
    braam(25.0, 1.5, notes=(D2 / 2, D2, F2, A2, D3))
    add(sweep_sine(t, 25.0, 90, 26, 0.3) * env(t, 25.0, 0.003, 2.5) * 0.6)

    # 標題後的尾奏: 固定音型片段, 慢且輕
    for i, f in enumerate((D3, A2, F3, A2, E3, A2, D3)):
        tb = 26.25 + i * BEAT
        add(fft_filter(saw(t, f), hi=1000) * env(t, tb, 0.05, 0.5) * gate(tb, tb + BEAT, 0.02) * 0.06, -0.2, 0.7)

    wl = reverb(wet, seed=1)
    wr = reverb(wet, seed=2)
    mix = np.stack([fft_filter(L + 0.5 * wl, lo=22, order=1), fft_filter(R + 0.5 * wr, lo=22, order=1)])
    mix = np.tanh(mix / np.abs(mix).max() * 1.8)
    mix *= np.clip((dur - t) / 0.6, 0, 1)
    mix /= np.abs(mix).max() / 0.89
    return mix.astype(np.float32)
