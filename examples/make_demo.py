"""Create six seconds of synthetic hard cuts. No third-party media."""

import subprocess
import sys

subprocess.run(
    [
        "ffmpeg",
        "-v",
        "error",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "color=c=red:s=320x240:r=24:d=2",
        "-f",
        "lavfi",
        "-i",
        "color=c=blue:s=320x240:r=24:d=2",
        "-f",
        "lavfi",
        "-i",
        "color=c=green:s=320x240:r=24:d=2",
        "-filter_complex",
        "[0:v][1:v][2:v]concat=n=3:v=1:a=0[out]",
        "-map",
        "[out]",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        sys.argv[1],
    ],
    check=True,
)
