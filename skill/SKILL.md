---
name: iphone-screencast-promo
description: Turn an iPhone screen recording into a square promo video - phone mockup, slow camera zooms that follow the action, tap circles, sped-up typing, clean 9:41 status bar.
---

# iPhone screencast → promo video

Output: 1080×1080, 60 fps H.264. The recording sits in an iPhone mockup (titanium rim,
side buttons, soft shadow) on a light grey background. The camera makes few, slow moves
(cosine ease, zoom in log space), every tap gets a grey circle with a white ring (a long
press grows while held), typing is sped up, and the recording's status bar (clock, red
recording pill) is replaced by a clean 9:41 bar with a Dynamic Island. Two scripts below do
all of it; the work is choosing the timing, camera and taps for each recording.

## 1. Set up

```bash
W=<scratch dir>/promo; mkdir -p $W/frames
# write render.py and find_events.py from the end of this file into a separate scripts dir
ffprobe -v error -show_entries stream=width,height,r_frame_rate:format=duration -of compact INPUT.mp4
ffmpeg -v error -i INPUT.mp4 -vf "fps=30,scale=576:1280" -start_number 0 $W/frames/%04d.png
```
Frames must start at `0000.png`, be 576×1280 at 30 fps (any iPhone recording scales to this).
Needs python3 with Pillow and numpy, and ffmpeg.

## 2. Understand the recording

- Contact sheet, 2 frames/s, to see the story:
  `ffmpeg -v error -i INPUT.mp4 -vf "fps=2,scale=160:-1,tile=14x6" -frames:v 1 $W/sheet.png`, then look at it.
- `python3 find_events.py $W` prints every change with its bounding box. A small box that
  appears alone (a row or button lighting up, a glass button swelling) is a touch-down: its
  time is the tap time, its centre is the tap point. A full-screen box right after it is
  the transition. Repeating small boxes over the keyboard are typing.
- Write down: each tap (time, x, y), long presses (hold = until the menu appears),
  typing stretches, where on screen each scene's action is (top / middle / bottom),
  and when the recording effectively ends (last meaningful change + ~1.5 s).

## 3. Write `$W/config.json`

```json
{
  "src_end": 40.6,
  "speed": [[5.6, 10.25, 1.6], [13.8, 18.5, 1.6]],
  "cam": [[0.0, 1.0, 288, 640], [1.2, 1.0, 288, 640], [2.6, 1.3, 288, 505],
          [23.4, 1.3, 288, 505], [24.6, 1.3, 288, 775], [26.9, 1.3, 288, 775],
          [28.1, 1.3, 288, 505], [34.6, 1.3, 288, 505], [35.9, 1.55, 288, 700],
          [38.8, 1.55, 288, 700], [40.6, 1.0, 288, 640]],
  "taps": [[1.00, 504, 124, 0], [2.63, 200, 716, 0], [35.70, 110, 764, 0.6]]
}
```
All times are SOURCE seconds; x/y are in the 576×1280 frame (centre = 288, 640).

- `speed`: `[start, end, factor]` stretches to speed up, usually typing at 1.6×. Taps inside
  them still land right (they are keyed to source time).
- `cam`: `[t, zoom, cx, cy]` keyframes, interpolated between neighbours. Rules that made
  the user happy:
  - **Few and slow.** Start at zoom 1 for ~1 s, push in to ~1.3 once, and hold that framing
    through the whole flow. Moves take 1.2–1.8 s. No zoom per tap.
  - **Show the phone edge near the action.** When the action is in the top part (nav bar,
    lists, form fields) use cy ≈ 505 at zoom 1.3, so the top of the phone with the island and
    9:41 is in frame. When something happens at the bottom (a bottom sheet, a tab bar) pan to
    cy ≈ 775 so the bottom edge shows. Otherwise stay centred.
  - One stronger push (~1.55) only for a moment that needs detail (a long-press menu).
  - End with a long pull out to zoom 1 at `src_end`.
  - At zoom z the visible source height is 1280 / (0.93·z) … check that each tap point
    is inside the frame at its time.
- `taps`: `[t, x, y, hold]`; `hold` > 0 for a long press (seconds until release / menu).
  Don't mark individual key presses while typing.

## 4. Preview, then render

```bash
PREVIEW=3,8,16,26 python3 render.py $W        # OUTPUT-time stills -> $W/prev_*.png
python3 render.py $W $W/promo.mp4             # ~3 min for 40 s on 4 cores
ffmpeg -v error -i $W/promo.mp4 -vf "fps=1,scale=220:-1,tile=8x5" -frames:v 1 $W/check.png
```
Output time differs from source time: a 0.6 s intro (phone settles in) comes first and
sped-up stretches shrink. Look at the stills and the 1 fps sheet: taps on the right spot,
tap points inside the frame, edges visible where intended, nothing cut. Fix config, rerun.

When the user asks for changes: "fewer / smoother zooms" → drop keyframes and lengthen moves;
"show the edges" → move cy toward 505 / 775 as above; keep everything else as it was.

## render.py

```python
"""Promo render: an iPhone screencast inside an iPhone mockup on a light background, with slow
camera moves that follow the action, tap indicators, sped-up typing and a clean 9:41 status bar.

Usage:
  python3 render.py <workdir> [out.mp4]          # full render (60 fps, 1080x1080)
  PREVIEW=3,12.5 python3 render.py <workdir>     # stills at those OUTPUT times -> <workdir>/prev_*.png
<workdir> holds frames/0000.png... (576x1280, 30 fps, from 0) and config.json:
  {"src_end": 40.6, "speed": [[5.6, 10.25, 1.6]],
   "cam":  [[t, zoom, cx, cy], ...],          # source seconds, 576x1280 pixel coords
   "taps": [[t, x, y, hold_seconds], ...]}
"""
import math
import os
import subprocess
import sys
from multiprocessing import Pool

import json

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.getcwd()
FRAMES = os.path.join(HERE, "frames")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "out.mp4")
with open(os.path.join(HERE, "config.json")) as f:
    CONFIG = json.load(f)
PREVIEW = os.environ.get("PREVIEW")  # e.g. "5,20,31.6" -> write stills instead

SRC_FPS = 30.0
SRC_COUNT = len(os.listdir(FRAMES))
FPS = 60
SIZE = 1080

# ---- geometry (2x of the 576x1280 recording) -------------------------------------------
K = 2                       # supersampling of the phone layer
PT = 1280 / 874 * K         # px per point in the layer (screen is 874pt tall)
SW, SH = 576 * K, 1280 * K
SCREEN_R = int(55 * PT)
BEZEL = int(11 * PT)
RIM = int(2.2 * PT)
PAD = int(70 * PT)          # room for the shadow and side buttons
OX = PAD + BEZEL + RIM      # screen origin inside the layer
OY = PAD + BEZEL + RIM
LW = SW + 2 * OX
LH = SH + 2 * OY
BODY = (PAD, PAD, LW - PAD, LH - PAD)
BODY_R = SCREEN_R + BEZEL + RIM

FIT_SCALE = (SIZE * 0.93) / (LH - 2 * PAD)   # zoom 1: phone body = 93% of the frame height


def ease(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x) if x < 1 else 1.0


def ease_cam(x):
    # smoother than smoothstep: ease-in-out quint-ish (camera moves in the reference are soft)
    x = min(1.0, max(0.0, x))
    return 0.5 - 0.5 * math.cos(math.pi * x)


# ---- timeline: output time -> source time (typing is sped up) ----------------------------
INTRO = 0.6
OUTRO = 0.8
SPEED = [tuple(x) for x in CONFIG.get("speed", [])]
SRC_END = float(CONFIG["src_end"])


def build_time_map():
    segs = []  # (out_start, src_start, src_end, speed)
    t_out = INTRO
    t_src = 0.0
    for a, b, sp in SPEED:
        if a > t_src:
            segs.append((t_out, t_src, a, 1.0))
            t_out += a - t_src
        segs.append((t_out, a, b, sp))
        t_out += (b - a) / sp
        t_src = b
    segs.append((t_out, t_src, SRC_END, 1.0))
    t_out += SRC_END - t_src
    return segs, t_out + OUTRO


SEGS, DURATION = build_time_map()


def src_time(t):
    if t < INTRO:
        return 0.0
    for out0, s0, s1, sp in SEGS:
        if t < out0 + (s1 - s0) / sp:
            return s0 + (t - out0) * sp
    return SRC_END


# ---- camera keyframes in source time: (t, zoom, cx, cy) in 1x screen px -------------------
CAM = [tuple(x) for x in CONFIG["cam"]]


def camera(ts, t_out):
    if ts <= CAM[0][0]:
        z, cx, cy = CAM[0][1:]
    elif ts >= CAM[-1][0]:
        z, cx, cy = CAM[-1][1:]
    else:
        for (t0, z0, x0, y0), (t1, z1, x1, y1) in zip(CAM, CAM[1:]):
            if t0 <= ts <= t1:
                e = ease_cam((ts - t0) / (t1 - t0))
                # interpolate zoom in log space so zooming feels even
                z = math.exp(math.log(z0) + (math.log(z1) - math.log(z0)) * e)
                cx = x0 + (x1 - x0) * e
                cy = y0 + (y1 - y0) * e
                break
    # intro: phone settles in from slightly smaller
    if t_out < INTRO + 0.4:
        z *= 0.94 + 0.06 * ease_cam(t_out / (INTRO + 0.4))
    # outro: gentle push out
    end0 = DURATION - OUTRO
    if t_out > end0:
        z *= 1.0 - 0.04 * ease_cam((t_out - end0) / OUTRO)
    return z, cx, cy


# ---- taps (source time, x, y, hold seconds) ----------------------------------------------
TAPS = [tuple(x) for x in CONFIG.get("taps", [])]


def tap_layers(ts):
    out = []
    for t0, x, y, hold in TAPS:
        appear = t0 - 0.12
        end = t0 + 0.12 + hold
        if ts < appear or ts > end + 0.28:
            continue
        if ts < t0:
            a = ease((ts - appear) / 0.12)
            sc = 1.18 - 0.18 * a
        elif ts <= end:
            a = 1.0
            sc = 1.0 - (0.06 * ease((ts - t0) / 0.1)) + (0.1 * ease((ts - t0) / max(hold, 0.01)) if hold else 0)
        else:
            k = ease((ts - end) / 0.28)
            a = 1.0 - k
            sc = (1.04 if hold else 0.94) + 0.12 * k
        out.append((x, y, a, sc))
    return out


# ---- static layers -----------------------------------------------------------------------
def rounded_mask(size, box, r):
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).rounded_rectangle(box, r, fill=255)
    return m


def build_static():
    layer = Image.new("RGBA", (LW, LH), (0, 0, 0, 0))

    # shadow
    sh = Image.new("L", (LW, LH), 0)
    d = ImageDraw.Draw(sh)
    d.rounded_rectangle((BODY[0] + 20, BODY[1] + 70, BODY[2] - 20, BODY[3] + 40), BODY_R, fill=80)
    sh = sh.filter(ImageFilter.GaussianBlur(70))
    sh2 = Image.new("L", (LW, LH), 0)
    ImageDraw.Draw(sh2).rounded_rectangle((BODY[0] + 10, BODY[1] + 18, BODY[2] - 10, BODY[3] + 10), BODY_R, fill=70)
    sh2 = sh2.filter(ImageFilter.GaussianBlur(18))
    shadow = np.maximum(np.array(sh, dtype=np.uint16), np.array(sh2, dtype=np.uint16)).astype(np.uint8)
    sl = Image.new("RGBA", (LW, LH), (20, 22, 35, 0))
    sl.putalpha(Image.fromarray(shadow))
    layer = Image.alpha_composite(layer, sl)

    d = ImageDraw.Draw(layer)
    # side buttons (behind the body)
    btn = (58, 58, 62, 255)
    bh = LH - 2 * PAD
    w = int(2.6 * PT)
    for y0, y1 in ((0.170, 0.205), (0.245, 0.315), (0.335, 0.405)):
        d.rounded_rectangle((BODY[0] - w, PAD + bh * y0, BODY[0] + 8, PAD + bh * y1), w, fill=btn)
    d.rounded_rectangle((BODY[2] - 8, PAD + bh * 0.255, BODY[2] + w, PAD + bh * 0.375), w, fill=btn)

    # titanium rim: vertical gradient, then black bezel
    rim = Image.new("RGBA", (LW, LH), (0, 0, 0, 0))
    grad = np.zeros((LH, LW, 4), dtype=np.uint8)
    ys = np.linspace(0, 1, LH)[:, None]
    base = (78 - 24 * ys).astype(np.uint8)
    grad[..., 0] = base
    grad[..., 1] = base
    grad[..., 2] = (base + 4).clip(0, 255)
    grad[..., 3] = 255
    rim = Image.fromarray(grad, "RGBA")
    layer.paste(rim, (0, 0), rounded_mask((LW, LH), BODY, BODY_R))
    inner = (BODY[0] + RIM, BODY[1] + RIM, BODY[2] - RIM, BODY[3] - RIM)
    layer.paste((8, 8, 10, 255), (0, 0, LW, LH), rounded_mask((LW, LH), inner, BODY_R - RIM))
    # thin highlight on the rim edge
    hl = Image.new("RGBA", (LW, LH), (0, 0, 0, 0))
    ImageDraw.Draw(hl).rounded_rectangle(BODY, BODY_R, outline=(150, 150, 156, 120), width=2)
    layer = Image.alpha_composite(layer, hl)

    screen_mask = rounded_mask((SW, SH), (0, 0, SW - 1, SH - 1), SCREEN_R)
    return layer, screen_mask


def build_background():
    yy, xx = np.mgrid[0:SIZE, 0:SIZE].astype(np.float32)
    r = np.sqrt((xx - SIZE / 2) ** 2 + (yy - SIZE * 0.45) ** 2) / (SIZE * 0.72)
    r = np.clip(r, 0, 1)
    c0 = np.array([238, 238, 243], np.float32)
    c1 = np.array([222, 223, 230], np.float32)
    img = c0 + (c1 - c0) * (r[..., None] ** 1.4)
    noise = np.random.default_rng(3).normal(0, 0.8, img.shape[:2])[..., None]  # avoid banding
    return Image.fromarray(np.clip(img + noise, 0, 255).astype(np.uint8), "RGB").convert("RGBA")


def load_font(size):
    for path in ("/usr/share/fonts/opentype/inter/Inter-SemiBold.otf",
                 "/System/Library/Fonts/SFNS.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size)


FONT = load_font(int(17 * PT))


def clean_status_bar(src):
    """Replace the recording's status bar (time, mute bell, red recording pill) with a clean
    9:41 bar and a real Dynamic Island."""
    a = np.array(src, dtype=np.float32)
    top, bot = 8, 86
    ra = a[top - 2:top, :, :].mean(axis=0)
    rb = a[bot:bot + 2, :, :].mean(axis=0)
    ws = np.linspace(0, 1, bot - top)[:, None, None]
    a[top:bot] = ra[None] * (1 - ws) + rb[None] * ws
    img = Image.fromarray(a.clip(0, 255).astype(np.uint8), "RGB")
    lum = 0.299 * ra[:, 0].mean() + 0.587 * ra[:, 1].mean() + 0.114 * ra[:, 2].mean()
    return img, (255, 255, 255) if lum < 110 else (0, 0, 0)


def draw_status(img, color):
    d = ImageDraw.Draw(img)
    cy = 47 * K
    # time
    d.text((76 * K, cy + 1), "9:41", font=FONT, fill=color, anchor="mm")
    # island
    iw, ih = 125 * PT, 37 * PT
    d.rounded_rectangle((SW / 2 - iw / 2, 11 * PT, SW / 2 + iw / 2, 11 * PT + ih), ih / 2, fill=(0, 0, 0))
    # signal
    x = 432 * K
    for i in range(4):
        h = (4 + i * 2.6) * PT
        d.rounded_rectangle((x + i * 4.8 * PT, cy + 5.5 * PT - h, x + i * 4.8 * PT + 3.1 * PT, cy + 5.5 * PT), 1.0 * PT, fill=color)
    # wifi: three arcs + dot
    wx, wy = 476 * K, cy + 5.2 * PT
    for i, rr in enumerate((11.5, 7.6, 3.7)):
        r = rr * PT
        d.arc((wx - r, wy - r, wx + r, wy + r), 225, 315, fill=color, width=int(2.3 * PT))
    d.ellipse((wx - 1.5 * PT, wy - 2.6 * PT, wx + 1.5 * PT, wy + 0.4 * PT), fill=color)
    # battery
    bx, bw, bh2 = 503 * K, 25 * PT, 12 * PT
    d.rounded_rectangle((bx, cy - bh2 / 2, bx + bw, cy + bh2 / 2), 3.6 * PT, outline=color, width=int(1.1 * PT))
    d.rounded_rectangle((bx + 2 * PT, cy - bh2 / 2 + 2 * PT, bx + bw - 2 * PT, cy + bh2 / 2 - 2 * PT), 2.2 * PT, fill=color)
    d.rounded_rectangle((bx + bw + 1.2 * PT, cy - 2.2 * PT, bx + bw + 2.6 * PT, cy + 2.2 * PT), 1 * PT, fill=color)


def draw_taps(img, ts):
    taps = tap_layers(ts)
    if not taps:
        return img
    over = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(over)
    for x, y, a, sc in taps:
        r = 22 * PT * sc
        X, Y = x * K, y * K
        d.ellipse((X - r, Y - r, X + r, Y + r), fill=(70, 70, 78, int(95 * a)),
                  outline=(255, 255, 255, int(200 * a)), width=int(1.6 * PT))
    return Image.alpha_composite(img.convert("RGBA"), over)


_static = None


def init():
    global _static
    layer, mask = build_static()
    _static = (layer, mask, build_background())


def render(t_out):
    layer, mask, bg = _static
    ts = src_time(t_out)
    idx = min(SRC_COUNT - 1, int(round(ts * SRC_FPS)))
    src = Image.open(os.path.join(FRAMES, "%04d.png" % idx)).convert("RGB")
    src, color = clean_status_bar(src)
    screen = src.resize((SW, SH), Image.LANCZOS)
    draw_status(screen, color)
    screen = draw_taps(screen, ts)

    phone = layer.copy()
    phone.paste(screen, (OX, OY), mask)

    z, cx, cy = camera(ts, t_out)
    s = FIT_SCALE * z
    fx, fy = OX + cx * K, OY + cy * K
    half = SIZE / 2 / s + 4
    x0 = max(0, int(math.floor(fx - half)))
    y0 = max(0, int(math.floor(fy - half)))
    x1 = min(LW, int(math.ceil(fx + half)))
    y1 = min(LH, int(math.ceil(fy + half)))
    crop = phone.crop((x0, y0, x1, y1))
    cw, ch = max(1, round((x1 - x0) * s)), max(1, round((y1 - y0) * s))
    small = crop.resize((cw, ch), Image.LANCZOS)
    sx, sy = cw / (x1 - x0), ch / (y1 - y0)
    ox = SIZE / 2 + (x0 - fx) * sx
    oy = SIZE / 2 + (y0 - fy) * sy
    placed = small.transform((SIZE, SIZE), Image.AFFINE, (1, 0, -ox, 0, 1, -oy), resample=Image.BILINEAR)
    frame = Image.alpha_composite(bg, placed).convert("RGB")
    return frame.tobytes()


def main():
    n = int(round(DURATION * FPS))
    if PREVIEW:
        init()
        for t in PREVIEW.split(","):
            data = render(float(t))
            Image.frombytes("RGB", (SIZE, SIZE), data).save(os.path.join(HERE, "prev_%s.png" % t))
        return
    print("duration %.2fs, %d frames" % (DURATION, n), flush=True)
    enc = subprocess.Popen([
        "ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (SIZE, SIZE),
        "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "16",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", OUT], stdin=subprocess.PIPE)
    with Pool(4, initializer=init) as pool:
        for i, data in enumerate(pool.imap(render, [i / FPS for i in range(n)], chunksize=4)):
            enc.stdin.write(data)
            if i % 300 == 0:
                print(i, flush=True)
    enc.stdin.close()
    enc.wait()
    print("done", OUT)


if __name__ == "__main__":
    main()
```

## find_events.py

```python
"""Lists what changes on screen, frame by frame, to find taps and transitions.

Usage: python3 find_events.py <workdir>      (reads <workdir>/frames/*.png, 576x1280, 30 fps)
Each line: source time, changed pixel count, bounding box of the change (576x1280 coords).
A small box that appears alone (a row or button lighting up) is a touch-down: its centre is
the tap point and its time is the tap time. A full-screen box right after it is the
transition the tap caused. Boxes repeating on the keyboard are typing.
"""
import os
import sys

import numpy as np
from PIL import Image

frames = os.path.join(sys.argv[1], "frames")
names = sorted(os.listdir(frames))
prev = None
for i, name in enumerate(names):
    a = np.asarray(Image.open(os.path.join(frames, name)).convert("L"), dtype=np.float32)[::2, ::2]
    if prev is not None:
        m = np.abs(a - prev) > 12
        m[:30, :] = False  # status bar clock / recording pill
        n = int(m.sum())
        if n > 40:
            ys, xs = np.where(m)
            print("%6.2f n=%6d  x%d-%d y%d-%d" % (i / 30, n, xs.min() * 2, xs.max() * 2, ys.min() * 2, ys.max() * 2))
    prev = a
```
