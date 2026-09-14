# Related projects and positioning

Reviewed September 14, 2026 against these projects' public READMEs. This is not exhaustive and does not assert that undocumented functionality is absent. No competitor code was copied.

## Closest overlap: BrightWayAI/video-analyzer

Its [README](https://github.com/BrightWayAI/video-analyzer) describes scene-based frames, Whisper transcription, Claude visual analysis, stylistic fingerprints, document/Markdown storyboards, and MCP tools. “Video to storyboard” alone is therefore not a defensible unique claim.

Ekonte emphasizes the next operation: applying an extracted timeline to a new brief. Its inspectable artifact carries per-beat speech budgets; a zero budget survives both generation and rewriting. A deterministic validator makes incomplete plans and timing overflow visible to downstream tools. This is a product focus, not proof that another project cannot do it.

## Complement: PySceneDetect

[PySceneDetect](https://github.com/Breakthrough/PySceneDetect) is a scene detection library and CLI. Ekonte optionally uses it and credits it rather than positioning its detection algorithms as an invention. Ekonte adds estimated transcript alignment, descriptive labels, generation, and narration constraints.

## Broader platform: VideoDB Director

[Director](https://github.com/video-db/Director) documents video agents for search, editing, compilation, generation, and streaming on VideoDB infrastructure. Ekonte's scope is smaller: a local reusable JSON artifact and production planning. It does not replace indexing, rendering, or streaming infrastructure.

## Different starting input: AI-storyboard-generator

[AI-storyboard-generator](https://github.com/dseditor/AI-storyboard-generator) documents an initial-image/story-outline workflow, generated cuts, and video generation with Gemini/ComfyUI. Ekonte starts with existing video, preserves its temporal structure, and writes a new plan. Ekonte does not create storyboard illustrations or render video.

## What to demonstrate

1. Analyze one reference, save the JSON, produce two briefs without re-analysis.
2. Use a sensory example to show silent middle beats surviving a rewrite.
3. Deliberately overflow a two-second beat and show an actionable validator result.
4. Run offline without credentials and show unavailable labels honestly.

Before claiming quality superiority, build a permissioned evaluation set covering hard cuts, slides, talking heads, music, silence, and multiple languages. Report segmentation error, transcript alignment error, human label agreement, pacing violations, and per-video processing cost. v0.1 includes synthetic correctness tests, not that benchmark.
