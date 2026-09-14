"""Render an edited walkthrough from checked-in real output. No model calls.

pip install pillow
python scripts/render_demo.py

Requires FFmpeg. Produces MP4, README poster, short GIF, and review frames.
"""

import json
import subprocess
from pathlib import Path

from demo_visuals import INK, LINE, MUTED, PAPER, RED, ROOT, font, reference_frame, text
from PIL import Image, ImageDraw, PngImagePlugin

ASSETS = ROOT / "docs/assets"
DATA = ROOT / "docs/demo-data"
DURATION = 36
FPS = 24


def wrap(draw, x, y, value, width, size=24, fill=INK, line_height=None):
    line_height = line_height or size * 1.35
    words = str(value).split()
    line = ""
    for word in words:
        candidate = (line + " " + word).strip()
        if draw.textlength(candidate, font=font(size)) > width and line:
            text(draw, (x, y), line, size, fill)
            y += line_height
            line = word
        else:
            line = candidate
    if line:
        text(draw, (x, y), line, size, fill)
    return y + line_height


def header(draw, page, t):
    draw.ellipse((56, 39, 94, 77), fill=RED)
    draw.line((51, 65, 99, 49), fill=PAPER, width=4)
    text(draw, (110, 31), "ekonte", 40)
    text(draw, (255, 48), "API", 18, MUTED, True)
    text(draw, (927, 48), "Python + HTTP / MIT", 19, MUTED)
    draw.line((56, 96, 1224, 96), fill=LINE, width=1)
    labels = ["Reference", "Structure", "New briefs", "Validation", "Try it"]
    text(draw, (56, 663), f"{page + 1:02d} / {labels[page]}", 18, MUTED, True)
    text(draw, (650, 663), "Real API output · Edited walkthrough · No audio", 17, MUTED)
    draw.rectangle((0, 714, 1280, 720), fill=LINE)
    draw.rectangle((0, 714, int(1280 * t / DURATION), 720), fill=RED)


def title(draw, heading, subtitle):
    text(draw, (56, 119), heading, 49)
    text(draw, (58, 188), subtitle, 23, MUTED)


def terminal(draw, x, y, lines, width=1168, size=22):
    draw.rounded_rectangle((x, y, x + width, y + len(lines) * 35 + 48), radius=12, fill=INK)
    for i, (line, color) in enumerate(lines):
        text(draw, (x + 24, y + 23 + i * 35), line, size, color, True)


def render(t, analysis, studio, developer, validation, capture):
    page = 0 if t < 6 else 1 if t < 14 else 2 if t < 22 else 3 if t < 30 else 4
    image = Image.new("RGB", (1280, 720), PAPER)
    draw = ImageDraw.Draw(image)
    header(draw, page, t)
    if page == 0:
        text(draw, (56, 158), "Keep the structure.", 52)
        text(draw, (56, 225), "Change the story.", 52)
        wrap(
            draw,
            58,
            333,
            "One reference video. Reusable beats.\nNew production plans.",
            450,
            27,
            MUTED,
        )
        text(draw, (58, 468), "VIDEO → JSON → STORYBOARD", 19, RED, True)
        image.paste(reference_frame(t * 2, (592, 333)), (632, 198))
        text(draw, (636, 552), "Original geometric reference · 12 seconds", 19, MUTED)
    elif page == 1:
        title(
            draw,
            "A timeline you can build on.",
            "Actual extraction: four beats, with explicit narration budgets.",
        )
        for i, beat in enumerate(analysis["beats"]):
            x = 56 + i * 296
            image.paste(reference_frame(i * 3 + 1, (280, 158)), (x, 258))
            text(draw, (x, 437), f"{beat['start']:04.1f}—{beat['end']:04.1f}s", 25, INK, True)
            text(draw, (x, 482), beat["shot"], 17, MUTED, True)
            value = "SILENT" if beat["max_words"] == 0 else f"≤ {beat['max_words']} words"
            text(draw, (x, 526), value, 27, RED if beat["max_words"] == 0 else INK)
            draw.line((x, 580, x + 280, 580), fill=LINE, width=1)
        text(
            draw,
            (58, 606),
            f"engine: {analysis['engine']}  ·  schema: {analysis['schema_version']}  ·  labels: model",
            18,
            MUTED,
            True,
        )
    elif page == 2:
        title(
            draw, "One analysis. Two new briefs.", "Both plans reuse the same saved Analysis JSON."
        )
        for x, name, plan in [(56, "North Studio", studio), (664, "Ekonte API", developer)]:
            text(draw, (x, 252), name, 30)
            draw.line((x, 299, x + 560, 299), fill=LINE, width=1)
            for i, beat in enumerate(plan["beats"]):
                y = 323 + i * 62
                text(draw, (x, y), f"{beat['start']:02.0f}–{beat['end']:02.0f}s", 19, MUTED, True)
                if beat["line"] is None:
                    text(draw, (x + 116, y - 3), "line: null", 24, RED, True)
                else:
                    wrap(draw, x + 116, y - 3, beat["line"], 435, 24)
            count = len(plan["violations"])
            text(draw, (x, 590), f"{count} pacing violations", 20, MUTED)
    elif page == 3:
        title(
            draw,
            "Silence is part of the contract.",
            "The validator catches an intentional invalid edit. No AI call required.",
        )
        text(draw, (57, 274), "0", 152, RED, True)
        text(draw, (58, 463), "words allowed at 03–06s", 25)
        text(draw, (58, 512), "Generation preserves line: null.", 23, MUTED)
        issue = next(v for v in validation["violations"] if v["code"] == "silent_beat")
        terminal(
            draw,
            580,
            260,
            [
                ("# Add speech to beat 1 (03–06s)", "#C4BEB5"),
                ("validate_pacing(analysis, edited)", "#F5F2EB"),
                ("", PAPER),
                ("{", PAPER),
                ('  "code": "silent_beat",', "#FF8D84"),
                (f'  "actual_words": {issue["actual_words"]},', PAPER),
                ('  "max_words": 0', PAPER),
                ("}", PAPER),
            ],
            width=644,
            size=20,
        )
    else:
        title(
            draw,
            "Start with your next reference.",
            "Install from GitHub. Try offline extraction without an API key.",
        )
        terminal(
            draw,
            56,
            255,
            [
                ("git clone https://github.com/shiki4709/ekonte-api.git", PAPER),
                ("cd ekonte-api", PAPER),
                ("python -m venv .venv && source .venv/bin/activate", PAPER),
                ("pip install -e '.[api,gemini]'", PAPER),
                ("ekonte analyze docs/assets/reference.mp4 --offline -o analysis.json", "#FF8D84"),
            ],
            size=22,
        )
        text(draw, (59, 515), "Python 3.11+ / FFmpeg required", 20, MUTED)
        text(draw, (59, 573), "github.com/shiki4709/ekonte-api", 31)
    return image


def main():
    inputs = [
        json.loads((DATA / name).read_text())
        for name in (
            "analysis.json",
            "studio-plan.json",
            "developer-plan.json",
            "validation.json",
            "capture.json",
        )
    ]
    proc = subprocess.Popen(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-f",
            "rawvideo",
            "-pixel_format",
            "rgb24",
            "-video_size",
            "1280x720",
            "-framerate",
            str(FPS),
            "-i",
            "-",
            "-an",
            "-c:v",
            "libx264",
            "-crf",
            "21",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(ASSETS / "ekonte-demo.mp4"),
        ],
        stdin=subprocess.PIPE,
    )
    for frame in range(DURATION * FPS):
        proc.stdin.write(render(frame / FPS, *inputs).tobytes())
    proc.stdin.close()
    if proc.wait():
        raise RuntimeError("demo encoding failed")
    info = PngImagePlugin.PngInfo()
    info.add_text(
        "Source",
        "Rendered by scripts/render_demo.py from real API capture and original geometric source.",
    )
    render(9, *inputs).save(ASSETS / "demo-poster.png", pnginfo=info)
    for t in (1, 9, 17, 25, 33):
        render(t, *inputs).save(Path("/tmp") / f"ekonte-demo-review-{t}.png", pnginfo=info)
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-i",
            str(ASSETS / "ekonte-demo.mp4"),
            "-t",
            "14",
            "-filter_complex",
            "fps=6,scale=800:-1:flags=lanczos,split[a][b];[a]palettegen=stats_mode=diff[p];"
            "[b][p]paletteuse=dither=bayer:bayer_scale=3",
            "-loop",
            "0",
            str(ASSETS / "demo-preview.gif"),
        ],
        check=True,
    )
    print("Rendered 36-second MP4, 14-second GIF preview, poster, and five review frames.")


if __name__ == "__main__":
    main()
