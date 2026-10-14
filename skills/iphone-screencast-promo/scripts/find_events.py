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
