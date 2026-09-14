"""Heuristic format classification and narration policies extracted from Ekonte.

Thresholds have not been validated against engagement. Raw measurements are
returned so integrations can inspect decisions and evaluate other classifiers.
"""

from datetime import UTC, datetime

SENSORY = "sensory"  # ASMR, texture, sound. The picture and the audio carry it.
SPECTACLE = "spectacle"  # transformation, process, montage. The payoff is visual.
EXPLAINER = "explainer"  # slides, overlays, information delivery.
TALKING = "talking"  # piece to camera, long takes.
STORY = "story"  # confessional first person. Narrative progression.

ENGINES = (SENSORY, SPECTACLE, EXPLAINER, TALKING, STORY)

# Below this share of runtime carrying speech, narration is not the engine.
NONVERBAL_MAX_COVERAGE = 0.15
# Held shots read as sensory; rapid cuts read as spectacle.
SENSORY_MIN_MEAN_SCENE = 3.0
# Most scenes carrying an overlay means the text is doing the explaining.
EXPLAINER_MIN_TEXT_FRAC = 0.6
# A piece to camera is a couple of long takes that talk almost throughout.
TALKING_MAX_SCENES = 4
TALKING_MIN_COVERAGE = 0.7
# Jump cuts make a piece to camera look like a many-scene video, so scene count
# alone called a 7-cut recipe a "story". One framing throughout is the real tell.
TALKING_MIN_SETUP_FRAC = 0.8
# Caps for the few beats a non-verbal video still speaks on. A silent reference
# yields the 2.3 w/s default, which measured nothing; do not inherit it.
SENSORY_MAX_RATE = 2.0
SPECTACLE_MAX_RATE = 2.3


def speech_coverage(segs: list | None, dur: float) -> float:
    """Share of runtime that carries speech, in [0, 1].

    Distinct from speech RATE: a video can speak quickly in two short bursts and
    be silent for the rest. Rate alone cannot tell that apart from a monologue.
    """
    if not dur or dur <= 0:
        return 0.0
    intervals = sorted(
        (max(0.0, float(s.get("start", 0))), min(dur, float(s.get("end", 0)))) for s in segs or []
    )
    spoken, last = 0.0, 0.0
    for start, end in intervals:
        spoken += max(0.0, end - max(start, last))
        last = max(last, end)
    return min(1.0, spoken / dur)


def engine_signals(
    segs: list | None, scenes: list, dur: float, mode: str, analysis: list | None = None
) -> dict:
    """The measurements classify_engine() reads. Stored on the board verbatim so
    a later, better classifier can re-label old boards from these numbers."""
    n = len(scenes or [])
    lengths = [max(0.0, float(b) - float(a)) for a, b in (scenes or [])]
    withtxt = sum(1 for a in (analysis or []) if (a or {}).get("txt"))
    setups = [((a or {}).get("shot"), (a or {}).get("angle")) for a in (analysis or [])]
    modal = max((setups.count(x) for x in set(setups)), default=0)
    return {
        "coverage": round(speech_coverage(segs, dur), 4),
        "mean_scene": round(sum(lengths) / n, 2) if n else 0.0,
        "n_scenes": n,
        "dur": round(float(dur or 0), 1),
        "mode": mode,
        "text_frac": round(withtxt / len(analysis), 4) if analysis else 0.0,
        "setup_frac": round(modal / len(setups), 4) if setups else 0.0,
    }


def classify_engine(signals: dict) -> str:
    """One of ENGINES. Order matters: the verbal/non-verbal split is the
    well-grounded one and is decided first. The splits inside each half are
    heuristics awaiting data."""
    sig = signals or {}
    if sig.get("coverage", 0.0) < NONVERBAL_MAX_COVERAGE:
        return SENSORY if sig.get("mean_scene", 0.0) >= SENSORY_MIN_MEAN_SCENE else SPECTACLE
    if sig.get("mode") in ("slides", "visual"):
        return EXPLAINER
    if sig.get("text_frac", 0.0) >= EXPLAINER_MIN_TEXT_FRAC:
        return EXPLAINER
    if sig.get("coverage", 0.0) >= TALKING_MIN_COVERAGE and (
        sig.get("n_scenes", 0) <= TALKING_MAX_SCENES
        or sig.get("setup_frac", 0.0) >= TALKING_MIN_SETUP_FRAC
    ):
        return TALKING
    return STORY


def speaking_beats(engine: str, n_beats: int) -> set:
    """Beat indices allowed to carry a spoken line.

    A non-verbal video is not a silent one. ASMR ads still set up with a line and
    land with a line; what they do not do is talk over the part the viewer came
    for. Everything between the ends gets a zero word budget, which the existing
    generation policy turns into line: null.
    """
    if n_beats <= 0:
        return set()
    if engine == SENSORY:
        return {0, n_beats - 1}
    if engine == SPECTACLE:
        return {0, n_beats // 2, n_beats - 1}
    return set(range(n_beats))


def engine_rate(engine: str, measured_rate: float) -> float:
    """Words per second for the beats that do speak."""
    if engine == SENSORY:
        return min(measured_rate, SENSORY_MAX_RATE)
    if engine == SPECTACLE:
        return min(measured_rate, SPECTACLE_MAX_RATE)
    return measured_rate


_BRIEFS = {
    SENSORY: (
        "\n\nENGINE: SENSORY. The reference barely speaks. Its hold on the viewer "
        "is texture, sound and timing, so words are the thing that would break it. "
        "Only the beats whose max_words is above 0 may carry a line; every other "
        "beat MUST set line to null. Do not compensate by filling overlay with "
        "captions either. Put the work in action: name the exact sound to capture "
        "(the tap, the scrape, the pour, the plop), what moves in frame, and how "
        "long to hold. Use sound for sound design, not as an aside."
    ),
    SPECTACLE: (
        "\n\nENGINE: SPECTACLE. The reference sells a visible change, not an "
        "account of one. Only the beats whose max_words is above 0 may carry a "
        "line; every other beat MUST set line to null. Let the picture do the "
        "turn. Use action to describe precisely what the viewer sees change."
    ),
}


def engine_brief(engine: str) -> str:
    """Nonverbal direction added to the storyboard generation prompt."""
    return _BRIEFS.get(engine, "")


_ENGAGEMENT_FIELDS = (
    ("views", "view_count"),
    ("likes", "like_count"),
    ("comments", "comment_count"),
    ("shares", "repost_count"),
)


def engagement_from_info(info: dict | None, now: datetime | None = None) -> dict:
    """Optional helper: normalize public counters without inventing missing values."""
    if not info:
        return {}
    at = (now or datetime.now(UTC)).astimezone(UTC)
    snap = {"fetched_at": at.strftime("%Y-%m-%dT%H:%M:%SZ")}
    for key, field in _ENGAGEMENT_FIELDS:
        value = info.get(field)
        if isinstance(value, (int, float)):
            snap[key] = int(value)
    posted = info.get("timestamp")
    if isinstance(posted, (int, float)):
        snap["posted_at"] = datetime.fromtimestamp(posted, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    uploader = info.get("uploader")
    if isinstance(uploader, str) and uploader.strip():
        snap["uploader"] = uploader.strip()
    return snap
