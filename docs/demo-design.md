# Demo design and reproduction notes

This documents the README/demo assets only; it is not a product design system.

## Visual direction

- Preserve the existing `assets/ekonte-lockup.svg`: ink wordmark, red circle, white diagonal cut, and translucent outer circle. The video header draws a simplified circle/cut motif and typesets its wordmark separately.
- Use warm paper `#F5F2EB`, ink `#17181A`, Ekonte red `#E0322C`, muted text `#62605C`, and rules `#D5D0C7`. Reference shot four adds `#DED7C9`; terminal text uses paper, `#C4BEB5`, and pale red `#FF8D84`.
- Space Grotesk carries headings and prose; JetBrains Mono carries commands, timestamps, budgets, and chapter numbers. Both fonts are bundled with their SIL OFL licenses.
- Keep flat backgrounds, generous whitespace, thin rules, and a limited red accent. The original abstract reference echoes the logo through circles and diagonal cuts.

## Composition and pacing

The walkthrough is 1280 × 720 at 24 fps, lasts 36 seconds, and has five chapters:

| Time | Chapter | Composition |
| --- | --- | --- |
| 0–6s | Reference | Left headline and workflow; right animated 12-second geometric reference played at twice its source speed. |
| 6–14s | Structure | Four columns with reference frames, measured beat times, shot labels, and narration budgets. |
| 14–22s | New briefs | Two columns compare production-plan lines using the same saved analysis. |
| 22–30s | Validation | Large zero-word budget beside the actual silent-beat validation result. |
| 30–36s | Try it | Installation commands and offline extraction example. |

A repeated header, numbered chapter footer, and bottom progress line orient viewers. Main content uses 56px side margins. Typical headings are 49–52px, prose 23–27px, and metadata 17–20px.

## Accessibility and presentation

- The MP4 has no audio; essential meaning appears as on-screen text. English, Japanese, and Simplified Chinese WebVTT files and the written [demo explanation](demo.md) provide companion access.
- Silence is labeled `SILENT` or `line: null`; color alone never communicates that state.
- Motion is confined to the opening geometric reference and progress line; later chapters hold static layouts for reading. A static poster is available alongside the animated preview.
- The GIF covers only the first 14 seconds, scaled to 800px wide at 6 fps. Link the full MP4 for all chapters and legible command text; small embedded playback is not the intended reading size.
- These choices are not a claim of audited accessibility conformance.

## Evidence and provenance

`demo-data/capture.json` records Gemini `gemini-2.5-flash`, one analysis call, two generation calls, and the exact briefs. The analysis, two plans, and validator result are checked in beside it. The reference is an original four-shot, 12-second geometric study, not customer footage. North Studio is fictional.

The walkthrough visualizes those saved outputs; it is not a screen recording, latency benchmark, or generated final customer video. The validation chapter intentionally inserts speech into a silent beat. PNG source metadata and detailed asset/license provenance are in [assets/README.md](assets/README.md).

## Regeneration

Run from the repository root with Python 3.11+ and FFmpeg available:

```sh
python -m pip install -e '.[gemini]' pillow
python scripts/render_demo.py
```

Rendering makes no model calls. It overwrites the MP4, GIF, and poster using checked-in evidence and writes five review frames to `/tmp/ekonte-demo-review-{1,9,17,25,33}.png`.

To deliberately refresh the source and evidence, set `GOOGLE_API_KEY` in your environment and run `python scripts/capture_demo.py` before rendering. That sends the original reference to Gemini and incurs provider calls; model output may vary. Review all five chapters and the JSON together after recapture, including the four-beat structure, silent budgets, text wrapping, and pacing results. Update companion captions and prose if the demonstrated content changes.
