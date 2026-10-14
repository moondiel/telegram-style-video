---
name: telegram-style-video
description: Turn an iPhone screen recording into a polished square promo video — the recording inside an iPhone mockup on a light background, slow camera zooms that follow the action, tap circles, sped-up typing, and a clean 9:41 status bar instead of the clock and red recording pill. Use this skill whenever the user sends an iPhone screencast / screen recording and wants a promo, demo, concept, launch or "Dribbble-style" video of an app flow — even if they only say "make a video from this", "make it look nice", or point at a reference video in this style. Also use it for follow-ups on such a video, like "fewer zooms", "smoother", "show the edges of the phone", "zoom in on the menu".
tools: Read, Write, Bash
---

# Telegram Style Video

A raw screen recording looks like a bug report. The same recording inside a phone, with a camera that calmly moves to where things happen and a circle on every tap, looks like a product launch. This skill does that with two scripts; the only real work is deciding **when the taps happen and where the camera looks**.

The core mindset: **the camera is a calm narrator, not a cameraman chasing every tap.** Few moves, all of them slow. Every extra zoom makes it look cheaper.

Output: MP4, 1080×1080, 60 fps, H.264. Needs `python3` with Pillow + numpy, and `ffmpeg`.

---

## Workflow

Scripts live next to this file in `scripts/`. Use a scratch working dir `W`.

### 1. Extract frames

```bash
mkdir -p $W/frames
ffmpeg -v error -i INPUT.mp4 -vf "fps=30,scale=576:1280" -start_number 0 $W/frames/%04d.png
```

Always 576×1280, 30 fps, starting at `0000.png` — any iPhone recording scales to this.

### 2. Read the story

- Contact sheet (2 frames/s) — look at it to understand the flow:
  `ffmpeg -v error -i INPUT.mp4 -vf "fps=2,scale=160:-1,tile=14x6" -frames:v 1 $W/sheet.png`
- `python3 scripts/find_events.py $W` — every change on screen with its bounding box:
  - a **small box on its own** (row or button lights up, glass button swells) = touch-down → its time is the tap time, its centre is the tap point;
  - a **full-screen box** right after = the transition the tap caused;
  - **small boxes repeating over the keyboard** = typing.
- Note: every tap, long presses (hold until the menu appears), typing stretches, whether each scene's action is at the top / middle / bottom, and where the recording really ends (last meaningful change + ~1.5 s).

### 3. Write `$W/config.json`

```json
{
  "src_end": 40.6,
  "speed": [[5.6, 10.25, 1.6]],
  "cam":  [[0.0, 1.0, 288, 640], [1.2, 1.0, 288, 640], [2.6, 1.3, 288, 505], [40.6, 1.0, 288, 640]],
  "taps": [[1.00, 504, 124, 0], [35.70, 110, 764, 0.6]]
}
```

All times are **source** seconds; x/y in the 576×1280 frame (centre 288, 640). Full real example: `example/config.json`.

| Field | Meaning |
|---|---|
| `src_end` | where the video ends |
| `speed` | `[start, end, factor]` — speed up typing, usually 1.6× |
| `cam` | `[time, zoom, cx, cy]` keyframes, eased between |
| `taps` | `[time, x, y, hold]` — hold > 0 for a long press |
| `bg` | optional background: `"#RRGGBB"` or `["#centre", "#edge"]` for a gradient. Default light grey. Use it when the user asks for a different background colour |

**Camera rules — pick them automatically, don't ask the user:**

| Situation | Camera |
|---|---|
| Opening | zoom 1 for ~1 s, then one push in to ~1.3 |
| Action in the top half (nav bar, lists, form fields) | hold zoom 1.3 at **cy ≈ 505** — top edge of the phone, Dynamic Island and 9:41 in frame |
| Action at the bottom (sheet, tab bar, toast) | pan to **cy ≈ 775** — bottom edge in frame |
| A detail matters (long-press menu, small control) | one stronger push to ~1.55 |
| Ending | long pull out to zoom 1 at `src_end` |

- Every move takes **1.2–1.8 s**. Never zoom per tap. Hold one framing as long as the action stays in that area.
- Visible source height ≈ `1280 / (0.93·zoom)` — check each tap point is inside the frame at its time.
- Don't mark individual key presses while typing.

### 4. Preview, render, check

```bash
PREVIEW=3,8,16,26 python3 scripts/render.py $W     # stills at OUTPUT times → $W/prev_*.png
python3 scripts/render.py $W $W/promo.mp4          # ~3 min for 40 s
ffmpeg -v error -i $W/promo.mp4 -vf "fps=1,scale=220:-1,tile=8x5" -frames:v 1 $W/check.png
```

Output time ≠ source time: a 0.6 s intro comes first and sped-up stretches shrink. Look at the stills and the 1 fps sheet: circles on the right spot, tap points in frame, edges visible where intended, nothing cut. Fix the config and rerun.

### 5. Output

Deliver the MP4 and say in one or two lines how the camera behaves (where it pushes in, where it shows the top / bottom edge). Mention anything you could not place confidently (e.g. a tap with no visible highlight).

---

## Follow-up edits

Change only what was asked; keep everything else identical.

- **"Fewer / smoother zooms"** → drop keyframes, merge holds, lengthen moves.
- **"Show the edges"** → move cy toward 505 (action near the top) or 775 (near the bottom); leave centred scenes as they are.
- **"Zoom in on X"** → one push to ~1.55 around X, then back to the previous framing.
- **Circles off** → re-check the tap time in `find_events.py` output (the touch-down, not the transition).
