import subprocess
import sys

import pytest

from ekonte.models import Analysis, Beat


@pytest.fixture
def reference():
    return Analysis(
        duration=6,
        segmentation="cuts",
        engine="sensory",
        engine_signals={},
        transcript_source="provided",
        alignment="none",
        beats=[
            Beat(
                id=i,
                start=i * 2,
                end=(i + 1) * 2,
                max_words=0 if i == 1 else 4,
                shot="PRODUCT_SHOT",
                angle="CLOSE_UP",
                function="PROOF",
            )
            for i in range(3)
        ],
    )


@pytest.fixture
def video(tmp_path):
    out = tmp_path / "demo.mp4"
    subprocess.run([sys.executable, "examples/make_demo.py", str(out)], check=True)
    return out
