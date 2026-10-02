"""程序化配樂: 120 BPM, D 小調, 和弦 Dm - Bb - F - C."""
import numpy as np

SR = 48000
BEAT = 0.5
BAR = 2.0


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
    return np.where(x < 0, 0.0, np.where(x < attack, x / max(attack, 1e-4), np.exp(-(x - attack) / decay)))


def saw(t, f):
    return 2 * ((t * f) % 1.0) - 1


def sweep_sine(t, t0, f_hi, f_lo, k):
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


def build_audio(dur):
    n = int(SR * dur)
    t = np.arange(n) / SR
    rng = np.random.default_rng(21)
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

    # 頻段噪音, 用來組 riser 與 whoosh
    bands_f = np.geomspace(150, 10000, 9)
    bands = [fft_filter(noise, lo=f / 1.5, hi=f * 1.5, order=2) for f in bands_f]

    def swept_noise(f_curve):
        lf = np.log(np.clip(f_curve, 150, 10000))
        out = np.zeros(n)
        for f, b in zip(bands_f, bands):
            out += b * np.exp(-((lf - np.log(f)) / 0.35) ** 2)
        return out

    def riser(a, b, amp=0.5, f0=200, f1=8000):
        u = np.clip((t - a) / (b - a), 0, 1)
        sig = swept_noise(f0 * (f1 / f0) ** u) * u ** 2.2 * gate(a, b, 0.01) * amp
        add(sig, 0, 0.3)

    def whoosh(tc, width=0.25, amp=0.7):
        f = 300 * (30 ** np.exp(-((t - tc) / width) ** 2))
        add(swept_noise(f) * np.exp(-((t - tc) / width) ** 2) * amp, 0, 0.3)

    def boom(t0, amp=1.0, low=32):
        add(sweep_sine(t, t0, 180, low, 0.06) * env(t, t0, 0.002, 1.1) * amp, 0, 0.15)
        add(fft_filter(noise, hi=1800) * env(t, t0, 0.001, 0.35) * 0.6 * amp, 0, 0.6)

    def crash(t0, amp=0.18):
        add(fft_filter(noise, lo=5000) * env(t, t0, 0.001, 1.2) * amp, 0, 0.4)

    # 0 - 4s: 齒輪 tick-tock 與低頻持續音
    for k in range(8):
        t0 = k * BEAT
        hi = k % 2 == 0
        click = fft_filter(noise, lo=2500 if hi else 900, hi=6000 if hi else 2000) * env(t, t0, 0.0005, 0.012)
        add(click * (0.5 if hi else 0.4), 0.3 if hi else -0.3, 0.5)
    drone = (np.sin(2 * np.pi * 36.71 * t) + 0.4 * fft_filter(saw(t, 73.42), hi=300)) * gate(0, 4.0, 0.05)
    add(drone * np.clip(t / 2.5, 0, 1) * 0.3, 0, 0.2)
    riser(2.2, 4.0, 0.55)
    whoosh(3.85, 0.18, 0.8)

    # 4 - 19.5s: 主段落鼓組
    chord_roots = (73.42, 58.27, 87.31, 65.41)
    chords = ((146.83, 174.61, 220.0, 293.66), (116.54, 146.83, 174.61, 233.08),
              (174.61, 220.0, 261.63, 349.23), (130.81, 164.81, 196.0, 261.63))
    sc = np.ones(n)
    drum_end = 19.5
    for k in range(int((drum_end - 4.0) / BEAT)):
        t0 = 4.0 + k * BEAT
        add(sweep_sine(t, t0, 160, 46, 0.03) * env(t, t0, 0.002, 0.28) * 0.95)
        add(np.diff(noise, prepend=0) * env(t, t0, 0.0004, 0.004) * 0.15)
        sc -= 0.7 * env(t, t0, 0.005, 0.13)
        if k % 2 == 1:
            clap = fft_filter(noise, lo=900, hi=6000)
            cenv = env(t, t0, 0.001, 0.012) + env(t, t0 + 0.011, 0.001, 0.012) + env(t, t0 + 0.022, 0.001, 0.16)
            add(clap * cenv * 0.35, 0, 0.5)
        ho = t0 + BEAT / 2
        add(fft_filter(noise, lo=7000) * env(t, ho, 0.001, 0.05) * 0.16, 0.4)
        add(fft_filter(noise, lo=8000) * env(t, t0 + 0.125, 0.001, 0.02) * 0.06, -0.4)
        add(fft_filter(noise, lo=8000) * env(t, t0 + 0.375, 0.001, 0.02) * 0.06, -0.4)
    sc = np.clip(sc, 0.25, 1)
    for tc in (4.0, 8.0, 12.0, 16.0):
        crash(tc)

    # 低音: 反拍 8 分音符
    bass = np.zeros(n)
    for k in range(int((drum_end - 4.0) / (BEAT / 2))):
        t0 = 4.0 + k * BEAT / 2
        if k % 2 == 0:
            continue
        root = chord_roots[int((t0 - 4.0) // BAR) % 4]
        bass += saw(t, root) * env(t, t0, 0.003, 0.11) * gate(t0, t0 + 0.24, 0.005)
    add(fft_filter(bass, hi=700) * 0.38)
    sub = np.zeros(n)
    for b in range(int((drum_end - 4.0) / BAR) + 1):
        t0 = 4.0 + b * BAR
        sub += np.sin(2 * np.pi * chord_roots[b % 4] / 2 * t) * gate(t0, min(t0 + BAR, drum_end), 0.02)
    add(sub * sc * 0.25)

    # 襯底和弦, 隨 kick 做 sidechain
    pad = np.zeros(n)
    padr = np.zeros(n)
    for b in range(int((25 - 4.0) / BAR) + 1):
        t0 = 4.0 + b * BAR
        g = gate(t0, t0 + BAR, 0.03)
        for f in chords[b % 4]:
            pad += (saw(t, f * 1.004) + saw(t, f * 0.996 * 2) * 0.3) * g
            padr += (saw(t, f * 0.996) + saw(t, f * 1.004 * 2) * 0.3) * g
    pad_amp = gate(4.0, 25.0, 0.3) * 0.045
    pl = fft_filter(pad, hi=1600) * pad_amp
    pr = fft_filter(padr, hi=1600) * pad_amp
    pl[t < 20] *= sc[t < 20]
    pr[t < 20] *= sc[t < 20]
    L += pl
    R += pr
    wet += (pl + pr) * 0.4

    # 12 - 16s: 16 分音符琶音, 對應資料脈衝畫面
    arp = np.zeros(n)
    arp_pan = np.zeros(n)
    for k in range(int(4.0 / 0.125)):
        t0 = 12.0 + k * 0.125
        ch = chords[int((t0 - 4.0) // BAR) % 4]
        f = ch[(0, 2, 3, 1, 2, 3)[k % 6]] * 4
        e = env(t, t0, 0.002, 0.07) * gate(t0, t0 + 0.12, 0.004)
        arp += saw(t, f) * e
        arp_pan += e * (1 if k % 2 else -1)
    arp = fft_filter(arp, hi=4500) * 0.07
    L += arp * (1 - 0.4 * np.clip(arp_pan, 0, 1))
    R += arp * (1 - 0.4 * np.clip(-arp_pan, 0, 1))
    wet += arp * 0.6

    # 轉場
    riser(7.3, 8.0, 0.35)
    whoosh(7.95, 0.12, 0.7)
    riser(15.2, 16.0, 0.35)
    whoosh(15.95, 0.12, 0.7)
    for tc in (11.95, 13.95):
        whoosh(tc, 0.1, 0.45)

    # 16, 17, 18s: 規格字卡的重音和弦
    for i, t0 in enumerate((16.05, 17.05, 18.05)):
        ch = chords[(i + 2) % 4]
        stab = sum(saw(t, f * 2) + saw(t, f * 2.008) for f in ch)
        add(fft_filter(stab, hi=3500) * env(t, t0, 0.003, 0.22) * 0.06, (-0.3, 0, 0.3)[i], 0.7)
        boom(t0, 0.45, 45)

    # 19 - 20s: 鼓組抽掉, 上升到主視覺
    riser(18.7, 20.0, 0.7, 150, 10000)
    rise_tone = np.sin(2 * np.pi * np.cumsum(110 * 4 ** np.clip((t - 18.7) / 1.3, 0, 1)) / SR)
    add(fft_filter(rise_tone, hi=3000) * np.clip((t - 18.7) / 1.3, 0, 1) ** 3 * gate(18.7, 19.95, 0.01) * 0.12)

    # 20 - 25s: 電影感段落, 低音銅管和弦與大鼓
    boom(20.0, 1.2, 30)
    crash(20.0, 0.25)
    brass = np.zeros(n)
    for b in range(3):
        t0 = 20.0 + b * BAR
        g = gate(t0, t0 + BAR, 0.08)
        for f in chords[b % 4]:
            brass += (saw(t, f / 2) + saw(t, f / 2 * 1.006)) * g * np.clip((t - t0) / 0.5, 0, 1)
    brass_amp = gate(20.0, 25.0, 0.4)
    add(fft_filter(brass, hi=900) * brass_amp * 0.06, 0, 0.5)
    for k in range(10):
        t0 = 20.0 + k * BEAT
        if k % 2 == 0 and t0 < 24.0:
            add(sweep_sine(t, t0, 110, 62, 0.05) * env(t, t0, 0.002, 0.45) * 0.6, 0, 0.4)
            add(fft_filter(noise, lo=200, hi=1200) * env(t, t0, 0.001, 0.08) * 0.25, 0, 0.5)
    # 24 - 25s: 小鼓滾奏
    roll_t = 24.0
    step = 0.125
    while roll_t < 25.0:
        a = 0.08 + 0.25 * (roll_t - 24.0)
        add(fft_filter(noise, lo=800, hi=7000) * env(t, roll_t, 0.001, 0.05) * a, 0, 0.4)
        step = max(0.03, step * 0.86)
        roll_t += step
    riser(23.8, 25.0, 0.5)

    # 25s: 收尾重擊與持續和弦
    boom(25.0, 1.3, 28)
    crash(25.0, 0.3)
    final = sum(saw(t, f) + saw(t, f * 1.005) + saw(t, f * 2.003) * 0.4 for f in (146.83, 220.0, 293.66, 329.63, 440.0))
    fin_env = env(t, 25.0, 0.02, 3.5) * np.clip((dur - t) / 1.2, 0, 1)
    add(fft_filter(final, hi=2500) * fin_env * 0.05, 0, 0.6)
    add(np.sin(2 * np.pi * 36.71 * t) * fin_env * 0.25)
    for k in range(int((29.5 - 26.5) / BEAT)):
        t0 = 26.5 + k * BEAT
        hi = k % 2 == 0
        add(fft_filter(noise, lo=2500 if hi else 900, hi=6000 if hi else 2000) * env(t, t0, 0.0005, 0.012) * 0.22,
            0.3 if hi else -0.3, 0.6)
    bell = np.zeros(n)
    for p, a in ((1, 1.0), (2.0, 0.5), (3.01, 0.25), (4.2, 0.12)):
        bell += np.sin(2 * np.pi * 587.33 * p * t) * a * env(t, 26.0, 0.003, 1.2)
    add(bell * 0.07, 0, 0.8)

    wl = reverb(wet, seed=1)
    wr = reverb(wet, seed=2)
    mix = np.stack([L + 0.45 * wl, R + 0.45 * wr])
    mix = fft_filter(mix[0], lo=25, order=1), fft_filter(mix[1], lo=25, order=1)
    mix = np.stack(mix)
    mix = np.tanh(mix / np.abs(mix).max() * 2.0)
    mix *= np.clip((dur - t) / 0.4, 0, 1)
    mix /= np.abs(mix).max() / 0.89
    return mix.astype(np.float32)
