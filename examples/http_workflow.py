"""python examples/http_workflow.py reference.mp4 'Your production brief'"""

import os
import sys
import time
from pathlib import Path

import httpx

headers = {"Authorization": "Bearer " + os.getenv("EKONTE_API_KEY", "")}
with httpx.Client(base_url="http://127.0.0.1:8421", headers=headers, timeout=120) as client:

    def completed(response):
        response.raise_for_status()
        url = response.json()["status_url"]
        for _ in range(900):
            response = client.get(url)
            response.raise_for_status()
            job = response.json()
            if job["state"] == "succeeded":
                return job["result"]
            if job["state"] == "failed":
                raise RuntimeError(job["error"])
            time.sleep(2)
        raise TimeoutError("job did not finish within 30 minutes")

    with Path(sys.argv[1]).open("rb") as video:
        analysis = completed(
            client.post(
                "/v1/analyses", content=video, headers={"Content-Type": "application/octet-stream"}
            )
        )
    Path("analysis.json").write_text(__import__("json").dumps(analysis, indent=2))
    plan = completed(
        client.post(
            "/v1/storyboards",
            json={"analysis": analysis, "brief": sys.argv[2], "creator_mode": "subject"},
        )
    )
    Path("storyboard.json").write_text(__import__("json").dumps(plan, indent=2))
    print("Saved analysis.json and storyboard.json. Reuse analysis.json for your next brief.")
