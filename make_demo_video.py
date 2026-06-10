#!/usr/bin/env python3
"""
make_demo_video.py — screenshot-based demo recorder with TTS narration.

Drives a demo via AppleScript/JS, screenshots each step, generates TTS audio
with OpenAI, then assembles everything into a polished MP4 with ffmpeg.

Requirements:
    pip install google-genai   (already installed in sonic/.venv)
    brew install ffmpeg

Setup before running:
    1. GEMINI_API_KEY must be set in your environment (same key SyncSnake uses)
    2. Chrome must be visible on DISPLAY (default: display 1)
    3. Chrome Tab 1 = Phoenix spans
       Chrome Tab 2 = swipe deck (this script auto-starts serve_deck.py and points
       the tab at http://localhost:8000/app.html so the live Refresh beat works)
    4. Phoenix running at localhost:6006

Usage:
    python make_demo_video.py              # record full demo
    python make_demo_video.py --script     # print narration only
    python make_demo_video.py --segment 4  # test a single segment
"""

import argparse
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# Load .env from same directory as this script
_env_file = Path(__file__).parent / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

# ── Config ────────────────────────────────────────────────────────────────────

DISPLAY = 1          # screencapture -D number (1 = primary display)
TTS_VOICE = "Zephyr" # Gemini voices: Zephyr, Aoede, Charon, Kore, Puck, Orbit, Fenrir
TTS_MODEL = "gemini-3.1-flash-tts-preview"
WORK_DIR = Path("/tmp/demo_frames")
OUTPUT = Path.home() / "Desktop/syncsnake_demo.mp4"

# Resolve a working ffmpeg. The Homebrew ffmpeg on this machine is broken
# (missing libbluray.2.dylib), so prefer the static binary bundled with
# imageio-ffmpeg (installed in the sonic venv) and fall back to PATH.
def _resolve_ffmpeg() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"

FFMPEG = _resolve_ffmpeg()

CHROME_SWIPE_TAB = 2
CHROME_PHOENIX_TAB = 1
PHOENIX_SPANS = "http://localhost:6006/projects/UHJvamVjdDoy/spans"
PHOENIX_TRACE = "http://localhost:6006/projects/UHJvamVjdDoy/traces/3b5fc28498fc17ff5e1360f80528342e"
PHOENIX_DATASET = "http://localhost:6006/datasets/RGF0YXNldDox/examples"

# Swipe deck is served by serve_deck.py so the live Refresh button works on camera.
DECK_PORT = 8000
DECK_DIR = "/Users/maryann/sync_licensing_agent/deck"
SWIPE_DECK_URL = f"http://localhost:{DECK_PORT}/app.html"

# ── AppleScript helpers ───────────────────────────────────────────────────────

def _osascript(script: str):
    """Run an AppleScript, writing it to a temp file to avoid shell-escaping issues."""
    with tempfile.NamedTemporaryFile(suffix=".applescript", mode="w", delete=False) as f:
        f.write(script)
        tmp = f.name
    try:
        subprocess.run(["osascript", tmp], capture_output=True)
    finally:
        os.unlink(tmp)


def activate_chrome(tab: int):
    _osascript(f"""
tell application "Google Chrome"
    activate
    tell window 1
        set active tab index to {tab}
    end tell
end tell
""")
    time.sleep(0.6)


def chrome_js(tab: int, js: str):
    """Execute JavaScript in a Chrome tab."""
    # Escape backslashes and double quotes for AppleScript string literal
    safe = js.replace("\\", "\\\\").replace('"', '\\"')
    _osascript(f"""
tell application "Google Chrome"
    tell window 1
        tell tab {tab}
            execute javascript "{safe}"
        end tell
    end tell
end tell
""")
    time.sleep(0.4)


def activate_terminal():
    _osascript('tell application "Terminal" to activate')
    time.sleep(0.4)


def chrome_navigate(tab: int, url: str):
    _osascript(f"""
tell application "Google Chrome"
    activate
    tell window 1
        set active tab index to {tab}
        set URL of tab {tab} to "{url}"
    end tell
end tell
""")
    time.sleep(2.0)  # let page load


def _deck_server_up() -> bool:
    import urllib.request
    try:
        urllib.request.urlopen(SWIPE_DECK_URL, timeout=1)
        return True
    except Exception:
        return False


def ensure_deck_server():
    """Start serve_deck.py if the deck isn't already being served (needed for live Refresh)."""
    if _deck_server_up():
        return
    env = dict(os.environ, PORT=str(DECK_PORT))
    subprocess.Popen(
        [sys.executable, f"{DECK_DIR}/serve_deck.py"],
        env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    for _ in range(20):
        if _deck_server_up():
            print(f"deck server up at {SWIPE_DECK_URL}")
            return
        time.sleep(0.5)
    print(f"WARNING: deck server did not come up at {SWIPE_DECK_URL}")

# ── Screenshot / audio / video ────────────────────────────────────────────────

def screenshot(path: str):
    subprocess.run(["screencapture", "-x", f"-D{DISPLAY}", path], check=True)
    time.sleep(0.2)


def tts(text: str, path: str):
    """Generate speech via Gemini TTS and save as MP3."""
    import wave
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        sys.exit("google-genai not installed — run: pip install google-genai")

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        sys.exit("GEMINI_API_KEY not set in environment")

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=TTS_MODEL,
        contents=text,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=TTS_VOICE
                    )
                )
            ),
        ),
    )

    # Gemini returns raw 24kHz 16-bit mono PCM
    pcm_bytes = response.candidates[0].content.parts[0].inline_data.data

    # Write PCM → WAV → MP3
    wav_path = path.replace(".mp3", ".wav")
    with wave.open(wav_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)   # 16-bit
        wf.setframerate(24000)
        wf.writeframes(pcm_bytes)
    subprocess.run(
        [FFMPEG, "-y", "-i", wav_path, path],
        capture_output=True, check=True,
    )
    os.unlink(wav_path)


def audio_duration(path: str) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True,
    )
    return float(result.stdout.strip())


def make_clip(image: str, audio: str, output: str):
    """Combine a still image + audio into a video clip (length = audio duration)."""
    subprocess.run([
        FFMPEG, "-y",
        "-loop", "1", "-i", image,
        "-i", audio,
        "-c:v", "libx264", "-tune", "stillimage",
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        output,
    ], capture_output=True, check=True)


def concat_clips(clip_paths: list[str], output: str):
    list_file = str(WORK_DIR / "clips.txt")
    with open(list_file, "w") as f:
        for c in clip_paths:
            f.write(f"file '{c}'\n")
    subprocess.run([
        FFMPEG, "-y", "-f", "concat", "-safe", "0",
        "-i", list_file, "-c", "copy", output,
    ], capture_output=True, check=True)

# ── Demo segments ─────────────────────────────────────────────────────────────
#
# Each segment is a dict:
#   action   — callable, runs before the screenshot (use None for no action)
#   narration — the spoken line for that screen
#
# To adapt this for a different project:
#   1. Replace the action callables with whatever drives your UI
#   2. Rewrite the narration strings
#   3. Adjust DISPLAY and OUTPUT at the top

def seg_action_browse_agencies():
    activate_chrome(CHROME_SWIPE_TAB)
    chrome_js(CHROME_SWIPE_TAB, "setMode('browse'); loadDeck('agencies');")

def seg_action_browse_libraries():
    chrome_js(CHROME_SWIPE_TAB, "loadDeck('music_libraries');")

def seg_action_browse_supervisors():
    chrome_js(CHROME_SWIPE_TAB, "loadDeck('supervisors');")

def seg_action_decide_autoplay():
    chrome_js(CHROME_SWIPE_TAB, "loadDeck('agencies');")
    chrome_js(CHROME_SWIPE_TAB, "document.getElementById('mDecide').click();")
    chrome_js(CHROME_SWIPE_TAB, "setAuto(true);")

def seg_action_manual_swipes():
    chrome_js(CHROME_SWIPE_TAB, "setAuto(false); advance('save');")
    time.sleep(0.8)
    chrome_js(CHROME_SWIPE_TAB, "advance('save');")
    time.sleep(0.8)
    chrome_js(CHROME_SWIPE_TAB, "advance('pass');")

def seg_action_terminal():
    activate_terminal()

def seg_action_phoenix_spans():
    chrome_navigate(CHROME_PHOENIX_TAB, PHOENIX_SPANS)

def seg_action_phoenix_trace():
    chrome_navigate(CHROME_PHOENIX_TAB, PHOENIX_TRACE)

def seg_action_phoenix_dataset():
    chrome_navigate(CHROME_PHOENIX_TAB, PHOENIX_DATASET)

def seg_action_live_refresh():
    activate_chrome(CHROME_SWIPE_TAB)
    chrome_js(CHROME_SWIPE_TAB, "setMode('browse'); loadDeck('agencies');")
    chrome_js(CHROME_SWIPE_TAB, "document.getElementById('bRefresh').click();")
    time.sleep(1.4)  # let the refresh fetch + re-render land

def seg_action_saved_cards():
    activate_chrome(CHROME_SWIPE_TAB)
    chrome_js(CHROME_SWIPE_TAB, "loadDeck('__saved__');")


SEGMENTS = [
    {
        "action": seg_action_browse_agencies,
        "narration": (
            "SyncSnake is an AI research agent that finds sync licensing opportunities "
            "for independent musicians. Here it's running as a live swipe deck — "
            "browse by category: agencies, supervisors, music libraries, and more."
        ),
    },
    {
        "action": seg_action_browse_libraries,
        "narration": (
            "The catalogue covers production music libraries, indie game studios looking "
            "for original soundtracks, advertising agencies, grant programs, and film festivals — "
            "all researched by AI agents in real time."
        ),
    },
    {
        "action": seg_action_browse_supervisors,
        "narration": (
            "Music supervisors at major studios and streaming platforms. "
            "Each card shows submission policy, notable projects, and contact details "
            "pulled directly from the agent's research."
        ),
    },
    {
        "action": seg_action_decide_autoplay,
        "narration": (
            "Switch to Decide mode: the deck auto-plays through results sorted by urgency. "
            "Swipe right to save an opportunity, left to pass. "
            "The animations use real eject physics."
        ),
    },
    {
        "action": seg_action_manual_swipes,
        "narration": (
            "Save the ones worth pursuing, pass on the rest. "
            "SyncSnake handles the research so you can focus on the decision."
        ),
    },
    {
        "action": seg_action_terminal,
        "narration": (
            "Under the hood: a Google ADK multi-agent pipeline. "
            "One command launches SyncSnake with full tracing enabled."
        ),
    },
    {
        "action": None,
        "narration": (
            "A validator checks the existing catalogue. A scout plans which topics need fresh research. "
            "Then five sub-agents fan out in parallel — each calling Gemini 2.5 Flash "
            "with a specialized prompt for their category."
        ),
    },
    {
        "action": seg_action_phoenix_spans,
        "narration": (
            "Every agent call is traced in Arize Phoenix. "
            "Here's the full span tree from a completed run — "
            "ADK orchestrator, sub-agents, and the MCP tool calls "
            "that fetch the faithfulness evaluator prompt at runtime."
        ),
    },
    {
        "action": seg_action_phoenix_trace,
        "narration": (
            "SyncSnake uses Phoenix's faithfulness evaluator to score every sub-agent's output. "
            "Results that score below the threshold are blocked from merging into the final catalogue — "
            "the agent enforces its own quality bar."
        ),
    },
    {
        "action": seg_action_phoenix_dataset,
        "narration": (
            "Scored examples write back to a Phoenix dataset after every run. "
            "The planner agent reads this history on the next run, "
            "skipping topics that consistently underperform "
            "and focusing effort where results are strongest."
        ),
    },
    {
        "action": seg_action_live_refresh,
        "narration": (
            "And the loop closes. The results from that traced run flow straight back "
            "into the deck — one tap on Refresh pulls the latest catalogue the agent built, live."
        ),
    },
    {
        "action": seg_action_saved_cards,
        "narration": (
            "Back in the deck: here are the opportunities saved during this session. "
            "Full details, direct links, submission guidelines. "
            "Everything the agent found, curated and ready to act on."
        ),
    },
    {
        "action": None,
        "narration": (
            "SyncSnake. AI research agent for sync licensing. "
            "Built with Google ADK, Gemini 2.5 Flash, and Arize Phoenix."
        ),
    },
]

# ── CLI ───────────────────────────────────────────────────────────────────────

def print_script():
    total = len(SEGMENTS)
    print(f"\n{'='*60}")
    print("SYNCSNAKE DEMO — NARRATION SCRIPT")
    print(f"{'='*60}")
    print(f"Voice: {TTS_VOICE} ({TTS_MODEL})")
    print(f"Segments: {total}")
    print()
    for i, seg in enumerate(SEGMENTS, 1):
        print(f"[{i:02d}/{total}]  {seg['narration']}")
        print()


def run_demo(segments: list[dict]):
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    clips = []

    print(f"Recording {len(segments)} segments to {WORK_DIR}")
    print(f"Output: {OUTPUT}\n")

    # Make sure the deck is served (so the live Refresh button works) and that
    # the deck tab is pointed at the server URL rather than a file:// path.
    ensure_deck_server()
    chrome_navigate(CHROME_SWIPE_TAB, SWIPE_DECK_URL)

    for i, seg in enumerate(segments):
        tag = f"seg_{i:02d}"
        img = str(WORK_DIR / f"{tag}.png")
        audio = str(WORK_DIR / f"{tag}.mp3")
        clip = str(WORK_DIR / f"{tag}.mp4")

        print(f"[{i+1}/{len(segments)}] action...", end=" ", flush=True)
        if seg["action"]:
            seg["action"]()
        time.sleep(0.8)

        print("screenshot...", end=" ", flush=True)
        screenshot(img)

        print("TTS...", end=" ", flush=True)
        tts(seg["narration"], audio)

        print("clip...", end=" ", flush=True)
        make_clip(img, audio, clip)
        clips.append(clip)
        print("done")

    print("\nConcatenating clips...")
    concat_clips(clips, str(OUTPUT))
    print(f"\nVideo saved to: {OUTPUT}")
    print("Next: open in QuickTime, export as 1080p, upload to YouTube.")


def main():
    global TTS_VOICE
    parser = argparse.ArgumentParser(description="SyncSnake demo video recorder")
    parser.add_argument("--script", action="store_true", help="Print narration script and exit")
    parser.add_argument("--segment", type=int, metavar="N", help="Test a single segment (1-indexed)")
    parser.add_argument("--voice", default=TTS_VOICE, help=f"Gemini voice name (default: {TTS_VOICE})")
    args = parser.parse_args()

    TTS_VOICE = args.voice

    if args.script:
        print_script()
        return

    if args.segment:
        idx = args.segment - 1
        if idx < 0 or idx >= len(SEGMENTS):
            sys.exit(f"Segment must be 1–{len(SEGMENTS)}")
        run_demo([SEGMENTS[idx]])
        return

    run_demo(SEGMENTS)


if __name__ == "__main__":
    main()
