"""把多張 PNG 或成品影片的指定影格拼成縮圖總表, 方便一次檢查.

用法:
    python contact_sheet.py out.png check/*.png              拼接 PNG
    python contact_sheet.py out.png video.mp4 60 150 300     從影片抽格
選項: --cols 3 --width 640
"""
import argparse
import glob

from PIL import Image


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("inputs", nargs="+")
    ap.add_argument("--cols", type=int, default=3)
    ap.add_argument("--width", type=int, default=640)
    a = ap.parse_args()

    ims = []
    if a.inputs[0].lower().endswith((".mp4", ".mov", ".mkv")):
        import av
        want = {int(x) for x in a.inputs[1:]}
        c = av.open(a.inputs[0])
        for i, fr in enumerate(c.decode(video=0)):
            if i in want:
                ims.append(fr.to_image())
            if want and i >= max(want):
                break
    else:
        files = []
        for p in a.inputs:
            files += sorted(glob.glob(p)) or [p]
        ims = [Image.open(f).convert("RGB") for f in files]
    if not ims:
        raise SystemExit("no frames")
    w = a.width
    h = int(w * ims[0].height / ims[0].width)
    rows = (len(ims) + a.cols - 1) // a.cols
    sheet = Image.new("RGB", (w * a.cols, h * rows))
    for i, im in enumerate(ims):
        sheet.paste(im.resize((w, h)), ((i % a.cols) * w, (i // a.cols) * h))
    sheet.save(a.out)
    print(f"{len(ims)} frames -> {a.out}")


if __name__ == "__main__":
    main()
