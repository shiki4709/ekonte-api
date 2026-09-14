"""Original geometric reference frames. No stock or third-party video."""

import math
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
PAPER = "#F5F2EB"
INK = "#17181A"
RED = "#E0322C"
MUTED = "#62605C"
LINE = "#D5D0C7"


@lru_cache(maxsize=64)
def font(size, mono=False):
    name = "JetBrainsMono" if mono else "SpaceGrotesk"
    return ImageFont.truetype(str(ROOT / "docs/assets/fonts" / f"{name}.ttf"), size)


def text(draw, xy, value, size=24, fill=INK, mono=False):
    draw.text(xy, str(value), font=font(size, mono), fill=fill)


def reference_frame(t, size=(640, 360)):
    """Four 3-second shots. Shapes are intentionally abstract, not product footage."""
    scene = min(int(t / 3), 3)
    phase = (t % 3) / 3
    image = Image.new("RGB", (640, 360), [PAPER, RED, INK, "#DED7C9"][scene])
    draw = ImageDraw.Draw(image)
    if scene == 0:
        r = 92 + int(math.sin(phase * math.pi) * 8)
        draw.ellipse((320 - r, 165 - r, 320 + r, 165 + r), fill=RED)
        draw.line((204, 193, 433, 134), fill=PAPER, width=10)
    elif scene == 1:
        for i in range(7):
            x = int(65 + i * 82 + 5 * math.sin(phase * math.pi))
            draw.rounded_rectangle((x, 82, x + 35, 240), radius=17, fill=PAPER)
    elif scene == 2:
        for i in range(4):
            r = 40 + i * 24 + int(phase * 3)
            draw.ellipse((320 - r, 163 - r, 320 + r, 163 + r), outline=RED, width=9)
    else:
        for i in range(3):
            x = 183 + 112 * i
            draw.ellipse((x - 42, 122, x + 42, 206), fill=[INK, RED, PAPER][i])
    fg = PAPER if scene in (1, 2) else INK
    text(draw, (26, 24), "EKONTE / MOTION STUDY", 16, fg, mono=True)
    text(draw, (26, 305), ["FORM", "RHYTHM", "HOLD", "RESOLVE"][scene], 27, fg)
    text(draw, (527, 310), f"{scene + 1} / 4", 17, fg, mono=True)
    return image.resize(size, Image.Resampling.LANCZOS)
