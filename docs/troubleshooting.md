# Troubleshooting

## `ffmpeg` or `ffprobe` is not found

Install FFmpeg (`brew install ffmpeg` on macOS, or `sudo apt-get install ffmpeg` on Ubuntu/Debian), then confirm both `ffmpeg -version` and `ffprobe -version` work in the shell that starts Ekonte.

## The `ekonte` command is not found

Activate the environment where you installed the package: `source .venv/bin/activate`. From the repository root run `python -m pip install -e '.[api,gemini]'`. For Windows PowerShell, activate with `.venv\Scripts\Activate.ps1` and set variables using `$env:GOOGLE_API_KEY = 'your-key'`.

## Missing Gemini configuration or HTTP 503

Install the `gemini` extra and export `GOOGLE_API_KEY` in the server's environment. Ekonte does not automatically read `.env` files. Use `--offline` in the CLI or `?offline=true` on `/v1/analyses` for extraction without a provider. Storyboard generation needs a provider.

## `UNKNOWN` labels or `engine: unknown`

Offline mode does not label images or transcribe audio. An audio track without a supplied/generated transcript means speech coverage is unknown, not zero. Read `transcript_source`, `label_source`, and `warnings`. Pass an explicit transcript if you have one; only use an empty list when you know no speech is present.

## Upload returns 415, 413, or 422

Use `Content-Type: application/octet-stream` and `curl --data-binary @video.mp4`, not multipart form data. Uploads must be nonempty and at most 100 MiB. JSON bodies are limited to 2 MiB. For JSON validation errors, inspect the response's `detail` field. Input videos must have a video stream, a valid duration up to 180 seconds, and dimensions no larger than 3840×2160.

## Authentication returns 401

Send `Authorization: Bearer <EKONTE_API_KEY>` using the token configured on the server. This is the server-access token, not the Gemini key. Do not put either token into issue reports. The interactive docs show an `authorization` header parameter for each operation when a token is configured.

## Queue is full, or HTTP 429

The server admits up to eight jobs/uploads and executes two jobs concurrently. Wait and retry using the response's `Retry-After` hint. Run one server process per data directory; multiple Uvicorn workers are not supported by this job store.

## A job fails with `processing_failed`

The HTTP error deliberately omits provider payloads and local paths. Confirm media limits, run offline analysis locally to isolate media problems, and check that the Gemini account can use the configured model. If reporting a bug, provide a synthetic reproduction and dependency versions. Do not attach confidential video or API responses containing private information.

## A job disappears or says `worker_interrupted`

Results expire after 24 hours. Save the completed `result` JSON if you need it longer. A restarted server marks queued/running work as failed and removes abandoned upload files. Resubmit the video; automatic resumption is not implemented.

## A generated storyboard still has pacing violations

Generation makes one repair attempt and returns remaining violations. Review or rewrite the affected beats; do not treat successful HTTP completion as guaranteed creative quality. Validation also checks the last beat. Word budgets use whitespace tokenization and are not validated for unsegmented Japanese or Chinese text.

## The demo video or captions do not play in GitHub

Use the MP4 in [release assets](https://github.com/shiki4709/ekonte-api/releases/tag/v0.1.0) or download it directly from the [repository](assets/ekonte-demo.mp4). Separate VTT captions may require a compatible external player. A [static preview](assets/demo-poster.png) and [multilingual transcript](demo.md#captions-and-transcript) are always available. The video has no audio track.

## Model output differs from the demo

The demo records one real run on a synthetic reference with explicit briefs; it is not a benchmark or an output guarantee. The source, briefs, results, and rendering scripts are published so the distinction is inspectable.
