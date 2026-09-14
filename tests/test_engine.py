"""A video's ENGINE decides whether narration should exist at all.

speech_rate() falls back to 2.3 words/sec whenever the reference has no
transcript, so a silent ASMR reference was budgeted like a talking-head reel
and REMIX_SYS ("compose the ENTIRE narration as ONE flowing monologue")
dutifully filled it. These tests pin the engine classification, the narration
budget it implies, and the engagement snapshot that makes the classification
testable later.
"""

from ekonte import engine


class TestSpeechCoverage:
    def test_silent_reference_is_zero(self):
        assert engine.speech_coverage([], 102.0) == 0.0

    def test_talking_head_is_near_one(self):
        segs = [{"start": 0.0, "end": 9.5}]
        assert engine.speech_coverage(segs, 10.0) == 0.95

    def test_sparse_speech_is_low(self):
        segs = [{"start": 0.0, "end": 3.0}, {"start": 90.0, "end": 95.0}]
        assert round(engine.speech_coverage(segs, 100.0), 3) == 0.08

    def test_never_exceeds_one(self):
        segs = [{"start": 0.0, "end": 30.0}, {"start": 0.0, "end": 30.0}]
        assert engine.speech_coverage(segs, 30.0) == 1.0

    def test_zero_duration_does_not_divide_by_zero(self):
        assert engine.speech_coverage([{"start": 0, "end": 1}], 0) == 0.0


class TestClassifyEngine:
    def test_vocabulary_is_closed(self):
        # the format library's open emotion vocabulary produced 123 labels,
        # 75% singletons, and could not aggregate. This one must stay small.
        assert len(engine.ENGINES) == 5
        assert set(engine.ENGINES) == {"sensory", "spectacle", "explainer", "talking", "story"}

    def test_silent_slow_video_is_sensory(self):
        # the pudding ASMR shape: 102s, 22 held shots, no speech
        sig = engine.engine_signals(
            segs=[], scenes=[(i * 4.6, i * 4.6 + 4.6) for i in range(22)], dur=102.0, mode="cuts"
        )
        assert engine.classify_engine(sig) == "sensory"

    def test_silent_fast_cut_video_is_spectacle(self):
        sig = engine.engine_signals(
            segs=[], scenes=[(i * 1.2, i * 1.2 + 1.2) for i in range(25)], dur=30.0, mode="cuts"
        )
        assert engine.classify_engine(sig) == "spectacle"

    def test_slide_mode_is_explainer(self):
        sig = engine.engine_signals(
            segs=[{"start": 0, "end": 40}], scenes=[(0, 20), (20, 40)], dur=40.0, mode="slides"
        )
        assert engine.classify_engine(sig) == "explainer"

    def test_heavy_on_screen_text_is_explainer(self):
        analysis = [{"i": i, "txt": "point %d" % i} for i in range(8)]
        sig = engine.engine_signals(
            segs=[{"start": 0, "end": 30}],
            scenes=[(i * 4, i * 4 + 4) for i in range(8)],
            dur=32.0,
            mode="cuts",
            analysis=analysis,
        )
        assert engine.classify_engine(sig) == "explainer"

    def test_single_long_take_with_speech_is_talking(self):
        sig = engine.engine_signals(
            segs=[{"start": 0, "end": 28}], scenes=[(0, 15), (15, 30)], dur=30.0, mode="cuts"
        )
        assert engine.classify_engine(sig) == "talking"

    def test_cut_video_with_speech_is_story(self):
        sig = engine.engine_signals(
            segs=[{"start": 0, "end": 20}],
            scenes=[(i * 3, i * 3 + 3) for i in range(10)],
            dur=30.0,
            mode="cuts",
        )
        assert engine.classify_engine(sig) == "story"

    def test_always_returns_a_member_of_the_closed_set(self):
        sig = engine.engine_signals(segs=[], scenes=[], dur=0.0, mode="cuts")
        assert engine.classify_engine(sig) in engine.ENGINES

    def test_signals_are_recorded_for_later_reclassification(self):
        # thresholds are a first guess; keeping the raw signals means a board
        # can be re-labelled later without re-ripping the video.
        sig = engine.engine_signals(segs=[], scenes=[(0, 5)], dur=5.0, mode="cuts")
        for key in ("coverage", "mean_scene", "n_scenes", "dur", "mode", "text_frac"):
            assert key in sig


class TestNarrationBudget:
    def test_sensory_speaks_only_at_the_ends(self):
        assert engine.speaking_beats("sensory", 22) == {0, 21}

    def test_spectacle_speaks_at_ends_and_turn(self):
        assert engine.speaking_beats("spectacle", 10) == {0, 5, 9}

    def test_verbal_engines_speak_everywhere(self):
        for name in ("story", "explainer", "talking"):
            assert engine.speaking_beats(name, 4) == {0, 1, 2, 3}

    def test_single_beat_video_still_speaks(self):
        assert engine.speaking_beats("sensory", 1) == {0}

    def test_zero_beats_is_empty(self):
        assert engine.speaking_beats("sensory", 0) == set()

    def test_sensory_rate_ignores_the_meaningless_default(self):
        # a silent reference yields SPEECH_RATE_DEFAULT, which describes no
        # measured speech at all. The hook and payoff must not inherit it.
        assert engine.engine_rate("sensory", 2.3) < 2.3

    def test_verbal_engine_keeps_the_measured_rate(self):
        assert engine.engine_rate("story", 3.4) == 3.4

    def test_unknown_engine_falls_back_to_speaking_everywhere(self):
        assert engine.speaking_beats("nonsense", 3) == {0, 1, 2}
        assert engine.engine_rate("nonsense", 2.9) == 2.9


class TestEngineBrief:
    def test_sensory_brief_directs_sound_not_monologue(self):
        brief = engine.engine_brief("sensory")
        low = brief.lower()
        assert "sound" in low
        assert "monologue" not in low

    def test_story_engine_adds_nothing(self):
        # story is what REMIX_SYS already describes; no contradictory second voice
        assert engine.engine_brief("story") == ""

    def test_every_engine_has_a_brief_entry(self):
        for name in engine.ENGINES:
            assert isinstance(engine.engine_brief(name), str)


class TestEngagementSnapshot:
    INFO = {
        "view_count": 1200000,
        "like_count": 84000,
        "comment_count": 910,
        "repost_count": 5100,
        "timestamp": 1750000000,
        "uploader": "example_creator",
        "title": "pudding asmr",
        "id": "7abc",
    }

    def test_maps_yt_dlp_fields_to_stable_names(self):
        e = engine.engagement_from_info(self.INFO)
        assert e["views"] == 1200000
        assert e["likes"] == 84000
        assert e["comments"] == 910
        assert e["shares"] == 5100

    def test_records_when_the_snapshot_was_taken(self):
        # a like count with no timestamp cannot be compared to anything later
        e = engine.engagement_from_info(self.INFO)
        assert e["fetched_at"].endswith("Z")

    def test_keeps_uploader_and_post_time(self):
        e = engine.engagement_from_info(self.INFO)
        assert e["uploader"] == "example_creator"
        assert e["posted_at"].startswith("20")

    def test_missing_fields_are_omitted_not_zeroed(self):
        # Instagram has no repost_count; a zero would read as "nobody shared it"
        e = engine.engagement_from_info({"view_count": 10, "like_count": 2})
        assert "shares" not in e
        assert e["views"] == 10

    def test_stores_no_derived_ratios(self):
        # engagement rate invites fitting a score to numbers already seen
        e = engine.engagement_from_info(self.INFO)
        assert not any("rate" in k or "ratio" in k for k in e)

    def test_survives_a_none_info(self):
        assert engine.engagement_from_info(None) == {}

    def test_does_not_mutate_the_input(self):
        original = dict(self.INFO)
        engine.engagement_from_info(self.INFO)
        assert self.INFO == original


def test_overlapping_speech_is_counted_once():
    assert engine.speech_coverage([{"start": 0, "end": 4}, {"start": 2, "end": 6}], 10) == 0.6
