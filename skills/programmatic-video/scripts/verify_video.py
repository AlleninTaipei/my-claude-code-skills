"""驗證成品 MP4: 串流, 長度, 實際可解碼的影格數, 音訊每段音量.

用法: python verify_video.py video.mp4 [--step 2.5]
"""
import argparse

import av
import numpy as np


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--step", type=float, default=2.0)
    a = ap.parse_args()

    c = av.open(a.path)
    for s in c.streams:
        dur = float(s.duration * s.time_base) if s.duration else None
        print(f"{s.type:6s} {s.codec_context.name:6s} duration={dur}")
    v = c.streams.video[0]
    print(f"video {v.codec_context.width}x{v.codec_context.height} @ {v.average_rate} fps")
    n = sum(1 for _ in c.decode(video=0))
    print(f"decoded video frames: {n}")
    c.close()

    c = av.open(a.path)
    if not c.streams.audio:
        print("NO AUDIO STREAM")
        return
    chunks = [fr.to_ndarray() for fr in c.decode(audio=0)]
    sr = c.streams.audio[0].codec_context.sample_rate
    audio = np.concatenate(chunks, axis=1).astype(np.float32)
    print(f"audio {audio.shape[0]}ch {sr} Hz, {audio.shape[1] / sr:.2f}s, peak {np.abs(audio).max():.3f}")
    for s in np.arange(0, audio.shape[1] / sr, a.step):
        seg = audio[:, int(s * sr):int((s + a.step) * sr)]
        db = 20 * np.log10(np.sqrt((seg ** 2).mean()) + 1e-9)
        print(f"  {s:5.1f}s  {db:6.1f} dB  {'#' * max(int((db + 40) / 1.5), 0)}")


if __name__ == "__main__":
    main()
