# telegram-video

Turn an iPhone screen recording into a polished square promo video.

The recording goes inside an iPhone mockup on a light background. The camera moves slowly to where things happen, every tap gets a circle, typing is sped up, and the clock and red recording pill are replaced by a clean 9:41 status bar. Output: MP4, 1080×1080, 60 fps.

## How to use

1. Put the skill into Claude (once):
   - **Claude Code:** `cp -r skills/iphone-screencast-promo ~/.claude/skills/`
   - **claude.ai / Claude app:** zip the `skills/iphone-screencast-promo` folder, then Settings → Capabilities → Skills → Upload skill.
2. Send Claude your iPhone screen recording and write: **"Make a promo video from this screencast."**
3. Ask for changes in plain words: "fewer zooms", "show the edges of the phone", "zoom in on the menu".

That's it.

## Skills

- [iPhone Screencast → Promo Video](skills/iphone-screencast-promo/SKILL.md) — finds the taps in the recording from frame differences, places a calm camera (one push in, top or bottom edge of the phone shown when the action is there, one stronger push for details, a long pull out at the end), speeds up typing, and renders the video. Ships two scripts: `render.py` (mockup, camera, tap circles, status bar, ffmpeg encode) and `find_events.py` (tap and transition finder), plus a real example config.

## Without Claude

Needs Python 3.9+, `pip install -r requirements.txt`, and ffmpeg (`brew install ffmpeg`). Follow the steps in [SKILL.md](skills/iphone-screencast-promo/SKILL.md): extract frames, find taps, write `config.json`, render.
