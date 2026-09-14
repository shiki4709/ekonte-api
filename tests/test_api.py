import threading
import time

import pytest
from fastapi.testclient import TestClient
from test_core import FakeProvider

from ekonte.api import create_app
from ekonte.jobs import BusyError, Jobs


def wait(client, response, headers=None):
    assert response.status_code == 202, response.text
    response = client.get(response.json()["status_url"], headers=headers)
    url = "/v1/jobs/" + response.json()["id"]
    for _ in range(200):
        job = client.get(url, headers=headers).json()
        if job["state"] in ("succeeded", "failed"):
            return job
        time.sleep(0.025)
    raise AssertionError("job timed out")


def test_auth_upload_poll_cleanup_and_restart(tmp_path, video):
    app = create_app(tmp_path, api_key="test-token")
    headers = {"Authorization": "Bearer test-token", "Content-Type": "application/octet-stream"}
    with TestClient(app) as client:
        assert client.get("/v1/jobs/missing").status_code == 401
        response = client.post(
            "/v1/analyses?offline=true", content=video.read_bytes(), headers=headers
        )
        result = wait(client, response, headers)
        assert result["state"] == "succeeded"
        assert result["result"]["duration"] == 6
        # Worker cleanup follows the database success update.
    assert not list((tmp_path / "uploads").iterdir())
    with TestClient(create_app(tmp_path, api_key="test-token")) as client:
        assert (
            client.get("/v1/jobs/" + result["id"], headers=headers).json()["state"] == "succeeded"
        )


def test_upload_limits_empty_and_media_type(tmp_path):
    with TestClient(create_app(tmp_path, api_key="", max_upload_bytes=4)) as client:
        assert (
            client.post(
                "/v1/analyses?offline=true",
                content=b"hello",
                headers={"Content-Type": "application/octet-stream"},
            ).status_code
            == 413
        )
        assert (
            client.post(
                "/v1/analyses?offline=true",
                content=b"",
                headers={"Content-Type": "application/octet-stream"},
            ).status_code
            == 422
        )
        assert client.post("/v1/analyses?offline=true", json={}).status_code == 415
        assert not list((tmp_path / "uploads").iterdir())
        assert client.get("/v1/jobs/missing").status_code == 404


def test_generation_and_validation_http(tmp_path, reference):
    with TestClient(create_app(tmp_path, api_key="", provider_factory=FakeProvider)) as client:
        request = {
            "analysis": reference.model_dump(),
            "brief": "A cup",
            "creator_mode": "explainer",
        }
        job = wait(client, client.post("/v1/storyboards", json=request))
        assert job["state"] == "succeeded"
        assert job["result"]["creator_mode"] == "explainer"
        validation = client.post(
            "/v1/pacing/validate",
            json={"analysis": reference.model_dump(), "beats": job["result"]["beats"]},
        )
        assert validation.json() == {"valid": True, "violations": []}
        request.update(storyboard=job["result"], beat_id=1)
        rewritten = wait(client, client.post("/v1/storyboards/beat/rewrite", json=request))
        assert rewritten["result"]["beats"][1]["line"] is None
        assert "/v1/analyses" in client.get("/openapi.json").json()["paths"]
        assert client.post("/v1/storyboards", json={"brief": "missing analysis"}).status_code == 422
        assert (
            client.post("/v1/storyboards", content=b" " * (2 * 1024 * 1024 + 1)).status_code == 413
        )


def test_failed_job_is_sanitized_and_upload_removed(tmp_path):
    with TestClient(create_app(tmp_path, api_key="")) as client:
        response = client.post(
            "/v1/analyses?offline=true",
            content=b"not video",
            headers={"Content-Type": "application/octet-stream"},
        )
        result = wait(client, response)
        assert result["state"] == "failed"
        assert result["error"] == "processing_failed"
    assert not list((tmp_path / "uploads").iterdir())


def test_bounded_jobs_restart_expiry_and_redaction(tmp_path):
    jobs = Jobs(tmp_path, workers=1, capacity=1)
    event = threading.Event()
    job = jobs.submit(lambda progress: (event.wait(5), {"ok": True})[1])
    with pytest.raises(BusyError):
        jobs.submit(lambda progress: {})
    event.set()
    jobs.close()
    assert jobs.get(job)["state"] == "succeeded"
    with jobs.connect() as db:
        db.execute(
            "INSERT INTO jobs VALUES ('orphan','running','working',NULL,NULL,?)", (time.time(),)
        )
    restarted = Jobs(tmp_path)
    assert restarted.get("orphan")["error"] == "worker_interrupted"
    with restarted.connect() as db:
        db.execute("UPDATE jobs SET updated=0")
    assert restarted.get(job) is None
    restarted.close()
