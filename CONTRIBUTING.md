# Contributing

Install `.[api,gemini,dev]`, run `pytest -q`, and run `ruff check src tests examples`. Tests must not require credentials or network access. FFmpeg and ffprobe are needed for synthetic video tests.

Useful contributions: provider adapters, timestamp/segmentation evaluation fixtures, multilingual pacing, structured label evaluation, and editor integrations. Open an issue describing the input, expected behavior, and observed output before a large change.

Keep the Python core independent of HTTP/database state. Preserve explicit uncertainty and return pacing violations rather than silently deleting meaningful words. Add behavioral regression tests when changing the schema or beat constraints.

Share only synthetic or permissioned media. Do not attach API keys, private reference videos, or full user briefs to issues. Schema changes need a versioning decision and documentation. Contributions are under the repository's MIT license.
