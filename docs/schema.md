# Schema 1.0

`Analysis` is the reusable artifact, independent of job IDs or a particular brief. It carries `schema_version: "1.0"`. All times are seconds. Each beat has a sequential zero-based ID and a positive duration; beats must cover the full video without gaps.

| Field | Meaning / evidence |
|---|---|
| `duration` | ffprobe container/video duration, capped at 180 seconds |
| `segmentation` | `cuts`, `visual` changes, or interpolated `sentences` |
| `engine` | Heuristic `sensory`, `spectacle`, `explainer`, `talking`, `story`; `unknown` when transcription is unavailable |
| `engine_signals` | Recorded coverage, mean scene duration, scene count, text and setup fractions; not confidence scores |
| `transcript_source` | `provided`, `model`, `no_audio`, or `unavailable` |
| `alignment` | `interpolated` words within transcript segments, or `none` |
| `beats[].shot / angle / function` | Model descriptions; `UNKNOWN` when unavailable |
| `beats[].label_source` | `model` or `unavailable`; no numeric confidence is invented |
| `beats[].spoken` | Aligned transcript words, never lip-reading guesses |
| `beats[].max_words` | Narration budget; zero means intentional silence |
| `beats[].keyframe_base64` | Optional JPEG; null by default |
| `warnings` | Quality/fallback context that downstream clients should preserve |

An engine label classifies how the reference is carried; `creator_mode` controls the voice of a new storyboard. Neither is the segmentation method. `creator_mode` is `subject`, `story`, `explainer`, or `reaction`.

Sensory formats permit speech in the first/last beats; spectacle formats permit first/middle/last. These are editorial policies, not claims that the reference speaks at precisely those locations. Whitespace words/second are measured from available segments and clamped to 2–4; default is 2.3. Nonverbal engines cap that rate. Overlapping segments are merged for coverage but not force-aligned for rate/word placement.

Generated `Storyboard` results contain a beat array and `violations`. Structure is pinned to the reference and zero-budget lines are nulled. Other overflow may remain after one best-effort model repair and is reported. `validate_pacing` is deterministic and checks all beats, including the final one.

The checked-in [synthetic analysis](../examples/analysis.json) and [validation input](../examples/validation.json) demonstrate the contract without claiming to be real model output. `/openapi.json` describes HTTP requests and the job envelope; [analysis.schema.json](analysis.schema.json) and [storyboard.schema.json](storyboard.schema.json) describe completed results.
