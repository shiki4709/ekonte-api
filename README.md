# Ekonte API · 絵コンテ

**Turn a reference video into reusable structure. Write a new production plan to the same beat.**

[![Tests](https://github.com/shiki4709/ekonte-api/actions/workflows/ci.yml/badge.svg)](https://github.com/shiki4709/ekonte-api/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Ekonte extracts timed beats from short-form video, aligns speech to those beats, and attaches shot labels and narration budgets. Save that JSON once, then generate different storyboards without processing the reference again.

Built for developers making creative research tools, video editors, and production workflows. Extracted from the Ekonte storyboard app. **v0.1 is an experimental developer release.**

```text
reference.mp4 → analyze → Analysis JSON ─┬→ brief A → storyboard A
                                       ├→ brief B → storyboard B
                                       └→ your editor / search index / agent
```

## What makes it useful

- **Structure becomes an input.** Scene timing, shot type, angle, and beat function survive into the next storyboard as explicit fields.
- **Silence is a constraint.** Sensory and spectacle formats get zero-word middle beats. Generation and single-beat rewrites enforce those beats with `line: null`.
- **Pacing is inspectable.** Word budgets use reference speech rate when available. The deterministic validator reports overflow, changed structure, and missing or duplicate beats—including the closing beat.
- **Static-camera references get a fallback.** Graphic changes or interpolated sentence boundaries can provide beats when hard cuts are sparse.
- **Unknown stays unknown.** Missing transcription does not classify a video as silent. Model labels and estimated word alignment are identified in the schema.
- **Use only what you need.** Core package + FFmpeg for offline extraction; optional HTTP server, Gemini provider, PySceneDetect, and social downloader.

This is a production-planning tool. It does not render finished videos or predict virality.

## Try it without an API key

Python 3.11+ and FFmpeg/ffprobe are required for video analysis.

```bash
# macOS: brew install ffmpeg
# Ubuntu/Debian: sudo apt-get install ffmpeg

git clone https://github.com/shiki4709/ekonte-api.git
cd ekonte-api
python -m venv .venv
source .venv/bin/activate
pip install -e '.[api,gemini]'

# Create a tiny synthetic reference; no downloaded media required.
python examples/make_demo.py /tmp/ekonte-demo.mp4
ekonte analyze /tmp/ekonte-demo.mp4 --offline -o analysis.json
```

Offline mode extracts timing and optional keyframes. It does not generate visual labels or transcribe audio. The core installation needs only `pip install -e .`; extras above enable the next examples. This release installs from GitHub; it is not a PyPI publication.

## Analyze once, generate twice

```bash
export GOOGLE_API_KEY='your-key'
ekonte analyze reference.mp4 -o analysis.json

ekonte storyboard analysis.json --brief 'Show how our ceramic cup is made.' -o cup.json
ekonte storyboard analysis.json --brief 'Show the texture of our handmade soap.' -o soap.json
```

Gemini receives extracted audio and keyframes for online analysis, then brief/analysis text for generation. Your provider account pays for those calls. Offline analysis and pacing validation make no model calls. Set `EKONTE_MODEL` to override the default `gemini-2.5-flash`; custom models must support the provider's JSON schema and configuration.

```python
from ekonte import analyze, storyboard, StoryboardRequest, validate_pacing
from ekonte.providers import GeminiProvider

provider = GeminiProvider()
analysis = analyze('reference.mp4', provider=provider)
plan = storyboard(
    StoryboardRequest(analysis=analysis, brief='Show how our ceramic cup is made.'),
    provider=provider,
)
print(plan.model_dump_json(indent=2))
print(validate_pacing(analysis, plan.beats))
```

Pass `transcript=[Segment(start=0, end=2, text='...')]` to use your own timestamped transcript. Pass `[]` only when you know there is no speech. Use `include_keyframes=True` when you need base64 JPEGs; they are omitted by default. A custom provider implements `complete(prompt, media, schema)`; Gemini is the only bundled provider.

## HTTP API

```bash
# Optional for localhost; required by `ekonte serve` for non-loopback binding.
export EKONTE_API_KEY='choose-a-long-random-token'
ekonte serve

curl -X POST 'http://127.0.0.1:8421/v1/analyses?offline=true' \
  -H "Authorization: Bearer $EKONTE_API_KEY" \
  -H 'Content-Type: application/octet-stream' \
  --data-binary @/tmp/ekonte-demo.mp4
# {"id":"...","status_url":"/v1/jobs/..."}

curl -H "Authorization: Bearer $EKONTE_API_KEY" \
  http://127.0.0.1:8421/v1/jobs/REPLACE_WITH_JOB_ID
```

Send raw video bytes, **not multipart form data**. Interactive docs: `http://127.0.0.1:8421/docs`. OpenAPI: `/openapi.json`. Poll `state` until `succeeded` or `failed`; `result` contains the analysis or storyboard JSON. Jobs retain results for 24 hours; expiry returns 404.

| Endpoint | Request | Response |
|---|---|---|
| `POST /v1/analyses` | Raw video; `offline`, `include_keyframes` query options | 202 job |
| `GET /v1/jobs/{id}` | Job ID | State, stage, result/error |
| `POST /v1/storyboards` | `{analysis, brief, creator_mode}` | 202 job |
| `POST /v1/storyboards/beat/rewrite` | `{analysis, brief, creator_mode, storyboard, beat_id}` | 202 job |
| `POST /v1/pacing/validate` | `{analysis, beats}` | `{valid, violations}`; no model |

Reuse the completed analysis **result**, rather than the job envelope, in storyboard requests. See [the runnable HTTP example](examples/http_workflow.py) and [the schema guide](docs/schema.md).

## How it differs from related projects

Based on their documented workflows, reviewed September 14, 2026. This is a scope comparison, not a benchmark.

| Project | Documented focus | Ekonte's focus |
|---|---|---|
| [PySceneDetect](https://github.com/Breakthrough/PySceneDetect) | Scene cut/transition detection and splitting | Builds on detection with transcript-aligned beats and production constraints. PySceneDetect is an optional dependency. |
| [BrightWayAI/video-analyzer](https://github.com/BrightWayAI/video-analyzer) | Frame analysis, transcription, stylistic fingerprints, storyboard breakdowns, MCP | Closest overlap. Ekonte centers on transferring a reference structure into a new brief, with per-beat speech budgets and a standalone validator. |
| [VideoDB Director](https://github.com/video-db/Director) | Video agents for search, editing, generation, and streaming on VideoDB | A small local Python library and optional HTTP API for reference-to-plan workflows. |
| [AI-storyboard-generator](https://github.com/dseditor/AI-storyboard-generator) | Initial image + story outline → generated storyboards and videos | Existing video → reusable timing/shot structure → new written production plan. |

See [comparison notes and boundaries](docs/comparison.md). We do not claim exclusive features or better output quality.

## Deployment and limits

```bash
docker build -t ekonte-api .
docker run --rm -p 127.0.0.1:8421:8421 \
  -e GOOGLE_API_KEY -e EKONTE_API_KEY \
  -v ekonte-data:/data ekonte-api
```

- One server process per data directory: two worker threads, eight admitted jobs/uploads. Full queues return 429. SQLite keeps completed results across restarts; interrupted work is marked failed, not automatically retried.
- Up to 180 seconds, 100 MiB, 3840×2160 input; up to 60 beats. JSON bodies are capped at 2 MiB. Individual FFmpeg calls and provider requests have timeouts.
- Raw uploads are deleted after processing; abandoned uploads are removed on startup. Results may contain reference dialogue, overlays, and optional keyframes until expiry. Expiry removes database rows; it is not secure disk erasure.
- Use the server for a trusted user/team. One bearer token grants access to all jobs; this release has no per-user isolation. Use HTTPS and a reverse proxy with request/upload timeouts for remote access. FFmpeg processing is not a hardened hostile-media sandbox.
- Label quality, sentence boundaries, speech rate, and format heuristics need evaluation on real videos. Whitespace word counting is primarily suitable for space-delimited languages. No forced alignment or retention-performance benchmark is included.
- Generation pins structural fields and silence, retries pacing once, and reports remaining violations. It does not guarantee factuality or originality; review generated plans before production.

Optional: `pip install -e '.[scenes]'` enables PySceneDetect; without it the FFmpeg detector is used. `pip install -e '.[download]'` allows `ekonte analyze 'https://www.instagram.com/reel/...'`. Downloads are a CLI/Python adapter, not a public HTTP URL-fetch endpoint. Use media you have permission to process; source platforms may restrict downloading.

## Development

```bash
pip install -e '.[api,gemini,dev]'
pytest -q
ruff check src tests examples
python -m build
```

Tests use synthetic video and fake providers: no credentials or paid services required. See [CONTRIBUTING.md](CONTRIBUTING.md). MIT licensed; FFmpeg, optional dependencies, and source media retain their own licenses.
