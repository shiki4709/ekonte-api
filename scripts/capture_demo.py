"""Produce the demo's reference and real API outputs. Requires Gemini credentials.

pip install -e '.[gemini]' pillow
export GOOGLE_API_KEY=...
python scripts/capture_demo.py

Only the generated reference is sent to Gemini. Model output can vary on reruns.
"""

import json
import subprocess

from demo_visuals import ROOT, reference_frame

from ekonte import StoryboardRequest, analyze, storyboard, validate_pacing
from ekonte.providers import GeminiProvider


class CountedProvider:
    def __init__(self):
        self.inner = GeminiProvider()
        self.calls = 0

    def complete(self, prompt, media, schema):
        self.calls += 1
        return self.inner.complete(prompt, media, schema)


def dump(path, data):
    if hasattr(data, "model_dump"):
        data = data.model_dump(mode="json")
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def main():
    assets = ROOT / "docs/assets"
    data = ROOT / "docs/demo-data"
    data.mkdir(exist_ok=True)
    source = assets / "reference.mp4"
    proc = subprocess.Popen(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-f",
            "rawvideo",
            "-pixel_format",
            "rgb24",
            "-video_size",
            "640x360",
            "-framerate",
            "24",
            "-i",
            "-",
            "-an",
            "-c:v",
            "libx264",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(source),
        ],
        stdin=subprocess.PIPE,
    )
    for frame in range(12 * 24):
        proc.stdin.write(reference_frame(frame / 24).tobytes())
    proc.stdin.close()
    if proc.wait():
        raise RuntimeError("reference encoding failed")
    provider = CountedProvider()
    analysis = analyze(source, provider=provider)
    if len(analysis.beats) != 4 or analysis.engine != "sensory":
        raise ValueError("reference did not produce the four expected sensory beats")
    if not all(b.label_source == "model" for b in analysis.beats):
        raise ValueError("visual analysis was unavailable; do not publish a simulated result")
    dump(data / "analysis.json", analysis)
    analysis_calls = provider.calls
    briefs = {
        "studio": "Create a NEW production plan for a fictional studio named North Studio. "
        "Borrow only the timing and shot categories, not the source words or graphics. "
        "Do not use EKONTE, MOTION STUDY, FORM, RHYTHM, HOLD or RESOLVE as overlay. "
        'Beat 0: show NORTH STUDIO and say "Make room for movement." '
        "Beat 1: show a white square stretching into a line, no speech. "
        "Beat 2: show the line becoming a wave, no speech. "
        'Beat 3: show NORTH STUDIO and say "A different perspective." '
        "This is fictional; do not invent clients or awards.",
        "developer": "Create a NEW production plan introducing Ekonte, an open-source API. "
        "Borrow only timing and shot categories, not the source overlay or shapes. "
        "Do not use MOTION STUDY, FORM, RHYTHM, HOLD or RESOLVE as overlay. "
        'Beat 0: show VIDEO TO JSON and say "Turn video into structure." '
        "Beat 1: show four JSON beat entries in a code editor, no speech. "
        "Beat 2: show that timeline feeding two new briefs, no speech. "
        'Beat 3: show OPEN SOURCE and say "Build your next story." '
        "Do not claim performance gains.",
    }
    for name, brief in briefs.items():
        plan = storyboard(StoryboardRequest(analysis=analysis, brief=brief), provider=provider)
        dump(data / f"{name}-plan.json", plan)
    # An intentional mutation proves the deterministic validator catches speech in silence.
    bad = plan.beats[1].model_copy(update={"line": "This beat should stay silent."})
    violations = validate_pacing(analysis, [plan.beats[0], bad, *plan.beats[2:]])
    dump(
        data / "validation.json",
        {
            "intentional_mutation": {"beat_id": 1, "line": bad.line},
            "violations": [v.model_dump() for v in violations],
        },
    )
    dump(
        data / "capture.json",
        {
            "package_version": "0.1.0",
            "reference": "original geometric motion study",
            "provider": "Gemini",
            "model": provider.inner.model,
            "analysis_calls": analysis_calls,
            "generation_calls": provider.calls - analysis_calls,
            "briefs": briefs,
            "presentation": "Edited walkthrough visualizing real outputs; not a real-time screen recording.",
        },
    )
    print("Captured original reference, one analysis, two storyboards, and validation evidence.")


if __name__ == "__main__":
    main()
