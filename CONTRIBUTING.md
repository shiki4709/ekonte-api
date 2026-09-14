# Contributing

Install `.[api,gemini,dev]`, run `pytest -q`, and run `ruff check src tests examples`. Tests must not require credentials or network access. FFmpeg and ffprobe are needed for synthetic video tests.

Useful contributions: provider adapters, timestamp/segmentation evaluation fixtures, multilingual pacing, structured label evaluation, and editor integrations. Open an issue describing the input, expected behavior, and observed output before a large change.

Keep the Python core independent of HTTP/database state. Preserve explicit uncertainty and return pacing violations rather than silently deleting meaningful words. Add behavioral regression tests when changing the schema or beat constraints.

Share only synthetic or permissioned media. Do not attach API keys, private reference videos, or full user briefs to issues. Schema changes need a versioning decision and documentation. Contributions are under the repository's MIT license.

## Documentation and translations

English `README.md` is the canonical overview. Japanese and Simplified Chinese versions live in `docs/i18n`. Keep commands, JSON keys, endpoint paths, and model/environment variable names unchanged when translating. Translate the explanations, not the wire format.

When a behavior or command changes, update the matching translated sections or explicitly mark them out of date. Update the source-version/date note at the bottom of each translated README. Additional languages are welcome when a contributor can review the translation; include a reciprocal language link in every README.

Do not imply that translated documentation means the speech-budget algorithm is validated for that language. Preserve the limitations concerning whitespace word counting, model inference, and the experimental release.

## Demo assets

The checked-in demo visualizes a real captured run. See [reproduction instructions](docs/demo.md#reproduce). Rendering saved outputs needs Pillow and FFmpeg but no API key. Recapturing makes paid provider calls and can change the results. Keep both the raw evidence and the accompanying description accurate; do not present mock output as a live run.

If a change touches the demo scripts, run `ruff check scripts` as well. Check local documentation links and inspect the rendered frames before submitting updated media. Font licenses must remain next to redistributed font files.

## Pull requests

Explain the user-visible problem, the final behavior, and the checks you ran. Use the PR template; screenshots or short videos help when changing documentation visuals. Keep unrelated refactors separate.
