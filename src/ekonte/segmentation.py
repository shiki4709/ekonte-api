"""Scene and transcript algorithms extracted from Ekonte."""

import re
from pathlib import Path

from . import media_process

SCENE_THRESHOLD = 0.28

MIN_SCENE_SEC = 0.6

MAX_SCENES = 60


def fill_scene_gaps(scenes: list, dur: float, min_gap: float = 1.0) -> list:
    """Make the scene timeline contiguous. Dropping sub-MIN_SCENE_SEC shots
    leaves holes where rapid-cut montages were - content and speech in a hole
    would otherwise belong to no scene. Each hole >= min_gap becomes a scene."""
    if not scenes:
        return scenes
    out = []
    prev_end = 0.0
    for a, b in scenes:
        if a - prev_end >= min_gap:
            out.append((prev_end, a))
        out.append((a, b))
        prev_end = b
    return out


def detect_scenes(path: Path, dur: float) -> list[tuple[float, float]]:
    # preferred: PySceneDetect (AdaptiveDetector handles fast cuts robustly)
    psd_scenes = []
    try:
        from scenedetect import AdaptiveDetector, detect

        raw = detect(str(path), AdaptiveDetector())
        psd_scenes = [
            (s.seconds, e.seconds) for s, e in raw if e.seconds - s.seconds >= MIN_SCENE_SEC
        ]
    except ImportError:
        pass
    # ffmpeg heuristic (always run as fallback/comparison)
    p = media_process.run(
        [
            "ffmpeg",
            "-i",
            str(path),
            "-vf",
            f"select='gt(scene,{SCENE_THRESHOLD})',metadata=print",
            "-an",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
    )
    if p.returncode:
        raise RuntimeError("FFmpeg scene detection failed")
    times = [float(m) for m in re.findall(r"pts_time:([0-9.]+)", p.stderr)]
    cuts, last = [], -10.0
    for t in times:
        if t - last >= MIN_SCENE_SEC:
            cuts.append(t)
            last = t
    bounds = [0.0] + cuts + [dur]
    ffmpeg_scenes = [
        (bounds[i], bounds[i + 1])
        for i in range(len(bounds) - 1)
        if bounds[i + 1] - bounds[i] >= 0.3
    ]
    # Prefer PySceneDetect when it returns usable results (≥3 scenes); fall back to ffmpeg
    scenes = (
        psd_scenes
        if len(psd_scenes) >= 3
        else (ffmpeg_scenes if len(ffmpeg_scenes) > len(psd_scenes) else psd_scenes)
    )
    scenes = fill_scene_gaps(scenes, dur)[:MAX_SCENES]
    # Extend last scene to video end so no content is lost
    if scenes and scenes[-1][1] < dur - 0.5:
        scenes[-1] = (scenes[-1][0], dur)
    return scenes


SLIDE_SCENE_RATE = 8.0

SLIDE_MIN_DUR = 20.0

SENTENCE_MIN_SEC = 1.2

_SENT_SPLIT = re.compile(r"(?<=[.!?…？！。])\s+")

SOFT_SCENE_PROBE = 0.015

SOFT_MIN_SCORE = 0.03

SOFT_MIN_GAP = 1.2

SOFT_MIN_BEATS = 4


def soft_cut_events(path: Path) -> list[tuple[float, float]]:
    """One sensitive ffmpeg pass returning (time, scene_score) candidates.
    Static-camera videos change via overlay/graphic pop-ins whose scores sit
    far below SCENE_THRESHOLD, so the normal detector never sees them."""
    p = media_process.run(
        [
            "ffmpeg",
            "-i",
            str(path),
            "-vf",
            f"select='gt(scene,{SOFT_SCENE_PROBE})',metadata=print",
            "-an",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
    )
    if p.returncode:
        raise RuntimeError("FFmpeg visual change detection failed")
    events, t = [], None
    for line in p.stderr.splitlines():
        m = re.search(r"pts_time:([0-9.]+)", line)
        if m:
            t = float(m.group(1))
            continue
        m = re.search(r"lavfi\.scene_score=([0-9.]+)", line)
        if m and t is not None:
            events.append((t, float(m.group(1))))
            t = None
    return events


def pick_soft_cuts(events: list, dur: float) -> list[tuple[float, float]]:
    """Choose visual-change beat boundaries: strongest switches first, minimum
    spacing enforced, count capped so beats average >= ~2s."""
    strong = [(t, s) for t, s in events if s >= SOFT_MIN_SCORE and 0.5 < t < dur - 0.5]
    if not strong:
        return []
    cap = min(MAX_SCENES - 1, max(1, int(dur / 2.0)))
    kept: list[float] = []
    for t, _ in sorted(strong, key=lambda e: -e[1]):
        if len(kept) >= cap:
            break
        if all(abs(t - k) >= SOFT_MIN_GAP for k in kept):
            kept.append(t)
    if not kept:
        return []
    bounds = [0.0] + sorted(kept) + [dur]
    return [(bounds[i], bounds[i + 1]) for i in range(len(bounds) - 1)]


def is_slide_style(scenes: list, dur: float, segs: list) -> bool:
    """Static-camera videos (brain-rot explainers, slide decks over a talking
    head) change VISUALS with the script, not the camera - scene detection sees
    almost nothing, so beats must come from the narration instead."""
    return bool(segs) and dur >= SLIDE_MIN_DUR and len(scenes) <= dur / SLIDE_SCENE_RATE


def sentence_scenes(segs: list, dur: float) -> list[tuple[float, float]]:
    """One beat per spoken sentence. Sentence times are interpolated inside
    each transcript segment proportionally to word count; silence gaps stay
    with the preceding beat so the timeline is contiguous."""
    spans: list[list[float]] = []
    for s in segs:
        text = str(s.get("text", "")).strip()
        if not text:
            continue
        parts = [p for p in _SENT_SPLIT.split(text) if p.strip()]
        total_words = sum(len(p.split()) for p in parts) or 1
        t = float(s["start"])
        seg_dur = max(0.0, float(s["end"]) - float(s["start"]))
        for p in parts:
            d = seg_dur * len(p.split()) / total_words
            spans.append([t, t + d])
            t += d
    if not spans:
        return []
    merged = [spans[0][:]]
    for a, b in spans[1:]:
        prev = merged[-1]
        if (prev[1] - prev[0]) < SENTENCE_MIN_SEC or (b - a) < SENTENCE_MIN_SEC:
            prev[1] = b
        else:
            merged.append([a, b])
    for i in range(len(merged) - 1):  # absorb inter-segment silence
        merged[i][1] = merged[i + 1][0]
    merged[0][0] = 0.0
    # transcript timestamps may overrun the real video - a beat past the end
    # makes downstream ffmpeg seeks come back with zero packets
    clamped = [(min(a, dur), min(b, dur)) for a, b in merged]
    clamped = [(a, b) for a, b in clamped if b - a >= 0.3]
    if clamped:
        clamped[-1] = (clamped[-1][0], dur)
    return clamped[:MAX_SCENES]


SPEECH_RATE_DEFAULT = 2.3


def word_budget(seconds: float, rate: float = SPEECH_RATE_DEFAULT) -> int:
    """Speakable words for a beat at the given pace (words/sec)."""
    return max(2, round(seconds * rate))


def speech_rate(segs: list) -> float:
    """Words/sec measured from the reference's own transcript. The budget must
    breathe at the reference's pace - a 3.2 w/s reel capped at a constant
    2.3 w/s reads word-starved. Clamped to a speakable range; falls back to
    the default when there's no timestamped speech to measure."""
    words = sum(len(str(s.get("text") or "").split()) for s in segs or [])
    time = sum(max(0.0, float(s.get("end", 0)) - float(s.get("start", 0))) for s in segs or [])
    if not words or time <= 0:
        return SPEECH_RATE_DEFAULT
    return min(4.0, max(2.0, words / time))


def words_by_scene(segs: list, scenes: list) -> list[str]:
    """Assign each transcript word to exactly ONE scene by its estimated time.

    Coarse segments (Gemini transcription returns whole sentences spanning
    several scenes) would otherwise be duplicated into every scene they touch.
    Words are spread evenly across their segment's span; each lands in the
    scene containing its midpoint, or the nearest scene if it falls in a gap."""
    buckets: list[list[str]] = [[] for _ in scenes]
    for s in segs:
        words = str(s.get("text", "")).split()
        if not words:
            continue
        step = max(float(s["end"]) - float(s["start"]), 1e-6) / len(words)
        for k, w in enumerate(words):
            t = float(s["start"]) + (k + 0.5) * step
            idx = next((j for j, (a, b) in enumerate(scenes) if a <= t < b), None)
            if idx is None:  # gap between scenes - nearest scene wins
                idx = min(
                    range(len(scenes)),
                    key=lambda j: min(abs(t - scenes[j][0]), abs(t - scenes[j][1])),
                )
            buckets[idx].append(w)
    return [" ".join(b) for b in buckets]
