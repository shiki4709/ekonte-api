"""Local media extraction. No API keys or application state."""

import base64
import json
from pathlib import Path

from .media_process import checked


def probe(path: Path) -> tuple[float, bool]:
    data = json.loads(
        checked(
            ["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)]
        )
    )
    videos = [s for s in data.get("streams", []) if s.get("codec_type") == "video"]
    if not videos:
        raise ValueError("input has no video stream")
    if any(s.get("width", 0) * s.get("height", 0) > 3840 * 2160 for s in videos):
        raise ValueError("maximum video resolution is 3840×2160")
    candidates = [data.get("format", {}).get("duration")]
    candidates += [s.get("duration") for s in videos]
    durations = []
    for value in candidates:
        try:
            durations.append(float(value))
        except (TypeError, ValueError):
            pass
    duration = max(durations, default=0)
    if not 0 < duration <= 180:
        raise ValueError("video duration must be between 0 and 180 seconds")
    return duration, any(s.get("codec_type") == "audio" for s in data.get("streams", []))


def frames(path: Path, scenes: list, directory: Path) -> list[str]:
    result = []
    for i, (start, end) in enumerate(scenes):
        out = directory / f"frame-{i}.jpg"
        checked(
            [
                "ffmpeg",
                "-v",
                "error",
                "-y",
                "-ss",
                str((start + end) / 2),
                "-i",
                str(path),
                "-frames:v",
                "1",
                "-vf",
                "scale=320:-2",
                "-q:v",
                "6",
                str(out),
            ]
        )
        if not out.exists():
            raise RuntimeError(f"could not extract keyframe for beat {i}")
        result.append(base64.b64encode(out.read_bytes()).decode())
    return result


def audio(path: Path, directory: Path) -> bytes:
    out = directory / "audio.mp3"
    checked(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-i",
            str(path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-b:a",
            "48k",
            str(out),
        ]
    )
    return out.read_bytes()
