import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

from .core import analyze, storyboard
from .models import Segment, StoryboardRequest
from .providers import GeminiProvider


def main():
    parser = argparse.ArgumentParser(
        description="Ekonte: video → reusable structure → production plan"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    a = sub.add_parser("analyze", help="analyze a local video (or optional social URL)")
    a.add_argument("video")
    a.add_argument("--offline", action="store_true")
    a.add_argument("--keyframes", action="store_true")
    a.add_argument("--transcript", type=Path, help="JSON array of start/end/text segments")
    a.add_argument("-o", "--output", type=Path)
    s = sub.add_parser("storyboard", help="generate from a saved analysis and brief")
    s.add_argument("analysis", type=Path)
    s.add_argument("--brief", required=True)
    s.add_argument(
        "--mode", default="subject", choices=["story", "subject", "explainer", "reaction"]
    )
    s.add_argument("-o", "--output", type=Path)
    serve = sub.add_parser("serve", help="start optional HTTP API")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8421)
    args = parser.parse_args()
    try:
        if args.command == "serve":
            if args.host not in ("127.0.0.1", "localhost", "::1") and not os.getenv(
                "EKONTE_API_KEY"
            ):
                parser.error("set EKONTE_API_KEY before binding to a non-loopback address")
            import uvicorn

            from .api import create_app

            uvicorn.run(create_app(), host=args.host, port=args.port)
            return
        provider = None if getattr(args, "offline", False) else GeminiProvider()
        if args.command == "analyze":
            transcript = None
            if args.transcript:
                transcript = [
                    Segment.model_validate(s) for s in json.loads(args.transcript.read_text())
                ]
            with tempfile.TemporaryDirectory(prefix="ekonte-download-") as temp:
                path = args.video
                if path.startswith("https://"):
                    from .download import download

                    path = download(path, Path(temp))
                result = analyze(
                    path, provider=provider, transcript=transcript, include_keyframes=args.keyframes
                )
        else:
            result = storyboard(
                StoryboardRequest(
                    analysis=json.loads(args.analysis.read_text()),
                    brief=args.brief,
                    creator_mode=args.mode,
                ),
                provider=provider,
            )
        output = result.model_dump_json(indent=2) + "\n"
        if args.output:
            args.output.write_text(output)
        else:
            print(output, end="")
    except (ValueError, RuntimeError, ImportError, OSError) as exc:
        print(f"ekonte: {exc}", file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
