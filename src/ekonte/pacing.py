"""Deterministic checks. Validation never calls a model or silently truncates text."""

from .models import Analysis, PlanBeat, Violation


def validate_pacing(analysis: Analysis, beats: list[PlanBeat]) -> list[Violation]:
    expected = {b.id: b for b in analysis.beats}
    seen = set()
    violations = []
    for beat in beats:
        ref = expected.get(beat.id)
        if ref is None or beat.id in seen:
            violations.append(Violation(beat_id=beat.id, code="unexpected_beat"))
            continue
        seen.add(beat.id)
        if any(
            getattr(beat, key) != getattr(ref, key)
            for key in ("start", "end", "shot", "angle", "function")
        ):
            violations.append(Violation(beat_id=beat.id, code="structure"))
        words = len((beat.line or "").split())
        if words > ref.max_words:
            violations.append(
                Violation(
                    beat_id=beat.id,
                    code="silent_beat" if ref.max_words == 0 else "word_budget",
                    actual_words=words,
                    max_words=ref.max_words,
                )
            )
    for missing in expected.keys() - seen:
        violations.append(Violation(beat_id=missing, code="missing_beat"))
    return sorted(violations, key=lambda v: (v.beat_id, v.code))
