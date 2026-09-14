"""Versioned, validated wire format. All timestamps are seconds."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Engine = Literal["sensory", "spectacle", "explainer", "talking", "story", "unknown"]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Segment(Model):
    start: float = Field(ge=0)
    end: float = Field(gt=0)
    text: str = Field(max_length=10000)

    @model_validator(mode="after")
    def ordered(self):
        if self.end <= self.start:
            raise ValueError("end must be after start")
        return self


class Beat(Model):
    id: int = Field(ge=0)
    start: float = Field(ge=0)
    end: float = Field(gt=0)
    shot: str = "UNKNOWN"
    angle: str = "UNKNOWN"
    function: str = "UNKNOWN"
    rationale: str | None = None
    overlay: str | None = None
    spoken: str | None = None
    max_words: int = Field(ge=0)
    label_source: Literal["model", "unavailable"] = "unavailable"
    keyframe_base64: str | None = None

    @model_validator(mode="after")
    def ordered(self):
        if self.end <= self.start:
            raise ValueError("end must be after start")
        return self


class Analysis(Model):
    schema_version: Literal["1.0"] = "1.0"
    duration: float = Field(gt=0, le=180)
    segmentation: Literal["cuts", "visual", "sentences"]
    engine: Engine
    engine_signals: dict[str, float | int | str]
    transcript_source: Literal["provided", "model", "unavailable", "no_audio"]
    alignment: Literal["interpolated", "none"]
    beats: list[Beat] = Field(min_length=1, max_length=60)
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def timeline(self):
        last = 0.0
        for i, beat in enumerate(self.beats):
            if beat.id != i or abs(beat.start - last) > 0.02:
                raise ValueError("beats must be contiguous with zero-based sequential IDs")
            last = beat.end
        if abs(last - self.duration) > 0.02:
            raise ValueError("beats must cover the full duration")
        return self


class StoryboardRequest(Model):
    analysis: Analysis
    brief: str = Field(min_length=1, max_length=12000)
    creator_mode: Literal["story", "explainer", "reaction", "subject"] = "subject"


class PlanBeat(Model):
    id: int = Field(ge=0)
    start: float = Field(ge=0)
    end: float = Field(gt=0)
    shot: str
    angle: str
    function: str
    action: str = Field(max_length=4000)
    line: str | None = Field(default=None, max_length=4000)
    overlay: str | None = Field(default=None, max_length=2000)
    sound: str | None = Field(default=None, max_length=2000)


class Violation(Model):
    beat_id: int
    code: Literal["word_budget", "silent_beat", "missing_beat", "unexpected_beat", "structure"]
    actual_words: int = 0
    max_words: int = 0


class Storyboard(Model):
    schema_version: Literal["1.0"] = "1.0"
    creator_mode: str
    beats: list[PlanBeat]
    violations: list[Violation]
    warnings: list[str] = Field(default_factory=list)


class RewriteRequest(StoryboardRequest):
    storyboard: Storyboard
    beat_id: int = Field(ge=0)


class ValidateRequest(Model):
    analysis: Analysis
    beats: list[PlanBeat] = Field(max_length=60)
