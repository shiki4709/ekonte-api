import json
import subprocess
from pathlib import Path

import pytest
from pydantic import ValidationError

from ekonte import Analysis, analyze, storyboard, validate_pacing
from ekonte.core import rewrite
from ekonte.models import Beat, PlanBeat, RewriteRequest, Segment, StoryboardRequest


class FakeProvider:
    def __init__(self, overflow=False, malformed=False):
        self.calls = []
        self.overflow = overflow
        self.malformed = malformed

    def complete(self, prompt, media, schema):
        self.calls.append(prompt)
        if schema["title"] == "Transcript":
            return {"segments": [{"start": 0, "end": 5.9, "text": "one two three four five six"}]}
        if schema["title"] == "Labels":
            context = json.loads(prompt.split("\n")[-1])
            return {
                "beats": [
                    dict(
                        id=b["id"],
                        shot="PRODUCT_SHOT",
                        angle="CLOSE_UP",
                        function="PROOF",
                        rationale="visible process",
                        overlay=None,
                    )
                    for b in context
                ]
            }
        refs = json.JSONDecoder().raw_decode(prompt.split("BEATS:\n")[1])[0]
        if self.malformed:
            refs = refs[:-1]
        return {
            "beats": [
                dict(
                    id=b["id"],
                    start=999,
                    end=1000,
                    shot="WRONG",
                    angle="WRONG",
                    function="WRONG",
                    action="Pour the liquid.",
                    line="this line is much too long for the provided budget"
                    if self.overflow
                    else "Feel the texture.",
                )
                for b in refs
            ]
        }


def test_generation_pins_structure_and_silence(reference):
    provider = FakeProvider()
    result = storyboard(
        StoryboardRequest(analysis=reference, brief="A handmade cup", creator_mode="reaction"),
        provider=provider,
    )
    assert result.beats[1].line is None
    assert result.beats[0].start == 0
    assert result.beats[0].shot == "PRODUCT_SHOT"
    assert not result.violations
    assert result.creator_mode == "reaction"
    assert "Creator voice: reaction" in provider.calls[0]


def test_rewrite_keeps_zero_budget(reference):
    provider = FakeProvider()
    req = StoryboardRequest(analysis=reference, brief="A handmade cup")
    first = storyboard(req, provider=provider)
    result = rewrite(
        RewriteRequest(**req.model_dump(), storyboard=first, beat_id=1), provider=provider
    )
    assert result.beats[1].line is None
    assert result.beats[0] == first.beats[0]
    assert result.beats[2] == first.beats[2]


def test_pacing_reports_final_beat_overflow_after_repair(reference):
    provider = FakeProvider(overflow=True)
    result = storyboard(StoryboardRequest(analysis=reference, brief="A cup"), provider=provider)
    assert len(provider.calls) == 2
    assert {v.beat_id for v in result.violations} == {0, 2}
    assert result.beats[1].line is None


def test_missing_generated_beats_fail(reference):
    with pytest.raises(ValueError, match="missing"):
        storyboard(
            StoryboardRequest(analysis=reference, brief="A cup"),
            provider=FakeProvider(malformed=True),
        )


def test_validate_detects_duplicate_missing_and_structure(reference):
    beat = PlanBeat(
        id=0,
        start=1,
        end=2,
        shot="X",
        angle="X",
        function="X",
        action="test",
        line="one two three four five",
    )
    violations = validate_pacing(reference, [beat, beat])
    assert {v.code for v in violations} == {
        "structure",
        "word_budget",
        "unexpected_beat",
        "missing_beat",
    }


def test_schema_rejects_gaps_nan_and_bad_timestamps(reference):
    data = reference.model_dump()
    data["beats"][1]["start"] = 2.5
    with pytest.raises(ValidationError):
        Analysis.model_validate(data)
    with pytest.raises(ValidationError):
        Beat(id=0, start=0, end=float("nan"), max_words=1)
    with pytest.raises(ValidationError):
        Segment(start=3, end=2, text="backwards")


def test_real_video_offline_and_serialization(video):
    result = analyze(video, include_keyframes=True)
    assert result.duration == 6
    assert len(result.beats) == 3
    assert result.transcript_source == "no_audio"
    assert all(b.keyframe_base64 for b in result.beats)
    assert Analysis.model_validate_json(result.model_dump_json()) == result


def test_unknown_audio_does_not_become_silence(video, tmp_path):
    out = tmp_path / "with-audio.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-i",
            str(video),
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=6",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-shortest",
            str(out),
        ],
        check=True,
    )
    result = analyze(out)
    assert result.engine == "unknown"
    assert result.transcript_source == "unavailable"
    assert all(b.max_words > 0 for b in result.beats)
    online = analyze(out, provider=FakeProvider())
    assert online.transcript_source == "model"
    assert online.alignment == "interpolated"
    assert all(b.label_source == "model" for b in online.beats)


def test_single_shot_video_is_valid(tmp_path):
    out = tmp_path / "single.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=red:s=160x120:d=1",
            "-c:v",
            "libx264",
            str(out),
        ],
        check=True,
    )
    result = analyze(out)
    assert len(result.beats) == 1
    assert result.beats[0].end == 1


def test_transcript_is_assigned_once(video):
    result = analyze(
        video, transcript=[Segment(start=0, end=6, text="one two three four five six")]
    )
    assert " ".join(b.spoken for b in result.beats) == "one two three four five six"
    with pytest.raises(ValueError, match="exceed"):
        analyze(video, transcript=[Segment(start=0, end=20, text="bad")])


def test_fixture_and_schema_are_valid():
    Analysis.model_validate_json(Path("examples/analysis.json").read_text())
    assert json.loads(Path("docs/analysis.schema.json").read_text()) == Analysis.model_json_schema()
