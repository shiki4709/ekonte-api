"""Bound FFmpeg execution time; reject network protocols in local media inputs."""

import subprocess


def run(cmd, **kwargs):
    cmd = list(cmd)
    if cmd[0] in ("ffmpeg", "ffprobe"):
        # Uploaded playlists must not turn local analysis into a network fetch.
        cmd[1:1] = [
            "-protocol_whitelist",
            "file,pipe",
            "-format_whitelist",
            "mov,matroska,webm,avi,mpegts,flv",
            "-max_alloc",
            "268435456",
        ]
        if cmd[0] == "ffmpeg":
            cmd[1:1] = ["-nostdin", "-threads", "2", "-filter_threads", "2"]
    return subprocess.run(cmd, timeout=240, check=False, **kwargs)


def checked(cmd):
    result = run(cmd, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f"{cmd[0]} could not process this media")
    return result.stdout
