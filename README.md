<img width="1920" height="1080" alt="yoomy-frame-2 15s" src="https://github.com/user-attachments/assets/529b094b-78f3-4dbb-8034-40a51e91718d" />
# Telegram Style Video

Turn an iPhone screen recording into a polished square promo video.

The recording goes inside an iPhone mockup on a light background. The camera moves slowly to where things happen, every tap gets a circle, typing is sped up, and the clock and red recording pill are replaced by a clean 9:41 status bar. Output: MP4, 1080×1080, 60 fps.

## How to use

You don't need git or a terminal for Claude.

1. Download **[telegram-style-video-skill.zip](telegram-style-video-skill.zip)** (open the file, then the download button on the right).
2. Add it to Claude once: claude.ai or the Claude app → Settings → Capabilities → Skills → **Upload skill** → pick the zip.
3. Open a new chat, attach your iPhone screen recording and write: **"Make a promo video from this screencast."**
4. Ask for changes in plain words: "fewer zooms", "show the edges of the phone", "zoom in on the menu".

**Claude Code** instead of the app: clone the repo and run `cp -r skills/telegram-style-video ~/.claude/skills/`.

## Cursor and other AI agents

Works in any agent that can run terminal commands; it does best if the agent can also look at images.

1. Download the repo (Code → Download ZIP, or `git clone`) and copy the folder into your project: `cp -r skills/telegram-style-video <your-project>/skills/`
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
