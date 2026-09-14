"""Check local documentation links and the published demo evidence. No network calls."""

import json
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

from ekonte import Analysis, Storyboard, validate_pacing

ROOT = Path(__file__).resolve().parents[1]


def main():
    errors = []
    files = [ROOT / "README.md", *ROOT.glob("*.md"), *ROOT.glob("docs/**/*.md")]
    files = sorted(set(files))
    links = 0
    for file in files:
        content = file.read_text()
        targets = re.findall(r'\]\(([^\s)]+)(?:\s+"[^"]*")?\)', content)
        targets += re.findall(r'(?:src|srcset|href)="([^"]+)"', content)
        for target in targets:
            url = urlsplit(target.strip("<>"))
            if url.scheme or url.netloc or not url.path:
                continue
            links += 1
            if not (file.parent / unquote(url.path)).exists():
                errors.append(f"{file.relative_to(ROOT)}: missing {target}")
    data = ROOT / "docs/demo-data"
    analysis = Analysis.model_validate_json((data / "analysis.json").read_text())
    if len(analysis.beats) != 4 or [b.max_words for b in analysis.beats] != [6, 0, 0, 6]:
        errors.append("demo analysis no longer matches the narrated four-beat example")
    for name in ("studio", "developer"):
        plan = Storyboard.model_validate_json((data / f"{name}-plan.json").read_text())
        if validate_pacing(analysis, plan.beats) or plan.violations:
            errors.append(f"{name} plan no longer matches the demo claim of zero violations")
    captured = json.loads((data / "validation.json").read_text())
    if not any(v["code"] == "silent_beat" and v["beat_id"] == 1 for v in captured["violations"]):
        errors.append("missing intentional silent-beat violation evidence")
    for lang in ("en", "ja", "zh-CN"):
        vtt = (ROOT / f"docs/assets/demo.{lang}.vtt").read_text()
        if not vtt.startswith("WEBVTT\n") or vtt.count(" --> ") != 5:
            errors.append(f"invalid demo caption structure: {lang}")
    if errors:
        raise SystemExit("\n".join(errors))
    print(
        f"Checked {len(files)} Markdown files, {links} local links, demo outputs, and three caption tracks."
    )


if __name__ == "__main__":
    main()
