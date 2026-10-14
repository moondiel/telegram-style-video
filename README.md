# Telegram Style Video

Turn an iPhone screen recording into a polished square promo video.

The recording goes inside an iPhone mockup on a light background. The camera moves slowly to where things happen, every tap gets a circle, typing is sped up, and the clock and red recording pill are replaced by a clean 9:41 status bar. Output: MP4, 1080×1080, 60 fps.

## How to use

1. Put the skill into Claude (once):
   - **Claude Code:** `cp -r skills/telegram-style-video ~/.claude/skills/`
   - **claude.ai / Claude app:** zip the `skills/telegram-style-video` folder, then Settings → Capabilities → Skills → Upload skill.
2. Send Claude your iPhone screen recording and write: **"Make a promo video from this screencast."**
3. Ask for changes in plain words: "fewer zooms", "show the edges of the phone", "zoom in on the menu".

That's it.

## Cursor and other AI agents

Works in any agent that can run terminal commands; it does best if the agent can also look at images.

1. Copy the folder into your project: `cp -r skills/telegram-style-video <your-project>/skills/`
2. Add this to the agent's instructions file — Cursor: `.cursor/rules/telegram-style-video.mdc`, Codex: `AGENTS.md`, Gemini CLI: `GEMINI.md`, Copilot: `.github/copilot-instructions.md`:

```
When I ask for a promo video from an iPhone screen recording,
follow skills/telegram-style-video/SKILL.md and run its scripts.
```

3. Give the agent the recording and ask: **"Make a promo video from this screencast."**

## Skills

- [Telegram Style Video](skills/telegram-style-video/SKILL.md) — finds the taps in the recording from frame differences, places a calm camera (one push in, top or bottom edge of the phone shown when the action is there, one stronger push for details, a long pull out at the end), speeds up typing, and renders the video. Ships two scripts: `render.py` (mockup, camera, tap circles, status bar, ffmpeg encode) and `find_events.py` (tap and transition finder), plus a real example config.

## Without Claude

Needs Python 3.9+, `pip install -r requirements.txt`, and ffmpeg (`brew install ffmpeg`). Follow the steps in [SKILL.md](skills/telegram-style-video/SKILL.md): extract frames, find taps, write `config.json`, render.
