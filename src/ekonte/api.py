"""Optional FastAPI server. Run one worker per data directory."""

import os
import secrets
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from pydantic import Field

from .core import analyze, rewrite, storyboard
from .jobs import BusyError, Jobs
from .models import Model, RewriteRequest, StoryboardRequest, ValidateRequest, Violation
from .pacing import validate_pacing
from .providers import GeminiProvider


class Accepted(Model):
    id: str
    status_url: str


class Job(Model):
    id: str
    state: Literal["queued", "running", "succeeded", "failed"]
    stage: str
    result: dict | None
    error: str | None


class Validation(Model):
    valid: bool
    violations: list[Violation] = Field(default_factory=list)


def create_app(
    data_dir: str | Path | None = None,
    api_key: str | None = None,
    provider_factory=GeminiProvider,
    max_upload_bytes=100 * 1024 * 1024,
):
    token = api_key if api_key is not None else os.getenv("EKONTE_API_KEY")
    directory = Path(data_dir or os.getenv("EKONTE_DATA_DIR", ".ekonte"))

    @asynccontextmanager
    async def lifespan(app):
        app.state.jobs = Jobs(directory)
        uploads = directory / "uploads"
        uploads.mkdir(exist_ok=True)
        # No work survives a restart. Remove only our own abandoned upload files.
        for path in uploads.glob("upload-*.video"):
            path.unlink(missing_ok=True)
        yield
        app.state.jobs.close()

    def auth(authorization: str = Header(default="")):
        if token and not secrets.compare_digest(authorization, "Bearer " + token):
            raise HTTPException(401, "invalid bearer token")

    app = FastAPI(
        title="Ekonte API",
        version="0.1.0",
        lifespan=lifespan,
        description="Reusable video structure and timing-aware production storyboards.",
        dependencies=[Depends(auth)],
    )

    # Bound JSON requests too, before FastAPI materializes/parses the body.
    @app.middleware("http")
    async def limit_body(request, call_next):
        from fastapi.responses import JSONResponse

        if request.method == "POST" and request.url.path != "/v1/analyses":
            content = bytearray()
            async for chunk in request.stream():
                content.extend(chunk)
                if len(content) > 2 * 1024 * 1024:
                    return JSONResponse({"detail": "JSON body exceeds 2 MiB"}, status_code=413)
            request._body = bytes(content)
        return await call_next(request)

    def provider():
        try:
            return provider_factory()
        except (ValueError, ImportError):
            raise HTTPException(
                503, "configure GOOGLE_API_KEY and install the gemini extra"
            ) from None

    def enqueue(work):
        try:
            job = app.state.jobs.submit(work)
        except BusyError:
            raise HTTPException(429, "job queue is full", headers={"Retry-After": "5"}) from None
        return Accepted(id=job, status_url=f"/v1/jobs/{job}")

    @app.post(
        "/v1/analyses",
        status_code=202,
        response_model=Accepted,
        openapi_extra={
            "requestBody": {
                "required": True,
                "content": {
                    "application/octet-stream": {"schema": {"type": "string", "format": "binary"}}
                },
            }
        },
    )
    async def analyses(request: Request, offline: bool = False, include_keyframes: bool = False):
        if request.headers.get("content-type", "").split(";")[0] not in (
            "application/octet-stream",
            "video/mp4",
            "video/quicktime",
            "video/webm",
        ):
            raise HTTPException(415, "send raw video bytes with application/octet-stream")
        model = None if offline else provider()
        try:
            app.state.jobs.reserve()
        except BusyError:
            raise HTTPException(429, "job queue is full", headers={"Retry-After": "5"}) from None
        path = None
        handed_off = False
        try:
            with tempfile.NamedTemporaryFile(
                prefix="upload-", suffix=".video", dir=directory / "uploads", delete=False
            ) as fp:
                path = Path(fp.name)
                size = 0
                async for chunk in request.stream():
                    size += len(chunk)
                    if size > max_upload_bytes:
                        raise HTTPException(413, "video exceeds upload limit")
                    fp.write(chunk)
            if size == 0:
                raise HTTPException(422, "video is empty")
            # submit owns the reservation and cleanup from this point, including failures.
            handed_off = True
            job = app.state.jobs.submit(
                lambda progress: analyze(
                    path, provider=model, include_keyframes=include_keyframes, progress=progress
                ),
                cleanup=lambda: path.unlink(missing_ok=True),
                reserved=True,
            )
            return Accepted(id=job, status_url=f"/v1/jobs/{job}")
        finally:
            if not handed_off:
                if path:
                    path.unlink(missing_ok=True)
                app.state.jobs.release()

    @app.get("/v1/jobs/{job_id}", response_model=Job)
    def get_job(job_id: str):
        job = app.state.jobs.get(job_id)
        if job is None:
            raise HTTPException(404, "unknown or expired job")
        return job

    @app.post("/v1/storyboards", status_code=202, response_model=Accepted)
    def create_storyboard(req: StoryboardRequest):
        model = provider()
        return enqueue(lambda progress: storyboard(req, provider=model))

    @app.post("/v1/storyboards/beat/rewrite", status_code=202, response_model=Accepted)
    def rewrite_beat(req: RewriteRequest):
        if req.beat_id >= len(req.analysis.beats):
            raise HTTPException(422, "unknown beat ID")
        model = provider()
        return enqueue(lambda progress: rewrite(req, provider=model))

    @app.post("/v1/pacing/validate", response_model=Validation)
    def pacing(req: ValidateRequest):
        violations = validate_pacing(req.analysis, req.beats)
        return Validation(valid=not violations, violations=violations)

    return app
