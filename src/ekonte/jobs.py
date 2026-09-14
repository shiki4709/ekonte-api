"""Single-process bounded workers with durable SQLite results and expiry."""

import json
import logging
import sqlite3
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


class BusyError(Exception):
    pass


class Jobs:
    def __init__(self, directory: Path, workers=2, capacity=8, ttl=86400):
        directory.mkdir(parents=True, exist_ok=True)
        self.db = directory / "jobs.sqlite3"
        self.ttl = ttl
        self.slots = threading.BoundedSemaphore(capacity)
        self.executor = ThreadPoolExecutor(max_workers=workers)
        with self.connect() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS jobs "
                "(id TEXT PRIMARY KEY, state TEXT, stage TEXT, result TEXT, "
                "error TEXT, updated REAL)"
            )
            db.execute(
                "UPDATE jobs SET state='failed', error='worker_interrupted', updated=? "
                "WHERE state IN ('queued','running')",
                (time.time(),),
            )
        self.expire()

    def connect(self):
        return sqlite3.connect(self.db, timeout=10)

    def expire(self):
        with self.connect() as db:
            db.execute(
                "DELETE FROM jobs WHERE updated < ? AND state IN ('succeeded','failed')",
                (time.time() - self.ttl,),
            )

    def reserve(self):
        if not self.slots.acquire(blocking=False):
            raise BusyError("job queue is full")

    def release(self):
        self.slots.release()

    def submit(self, work, cleanup=lambda: None, reserved=False):
        if not reserved:
            self.reserve()
        self.expire()
        job = uuid.uuid4().hex
        try:
            with self.connect() as db:
                db.execute(
                    "INSERT INTO jobs VALUES (?,?,?,?,?,?)",
                    (job, "queued", "queued", None, None, time.time()),
                )
            self.executor.submit(self._run, job, work, cleanup)
        except Exception:
            self.release()
            cleanup()
            raise
        return job

    def _run(self, job, work, cleanup):
        def progress(stage):
            with self.connect() as db:
                db.execute(
                    "UPDATE jobs SET state='running', stage=?, updated=? WHERE id=?",
                    (stage, time.time(), job),
                )

        try:
            progress("starting")
            result = work(progress)
            if hasattr(result, "model_dump"):
                result = result.model_dump(mode="json")
            with self.connect() as db:
                db.execute(
                    "UPDATE jobs SET state='succeeded', stage='done', result=?, updated=? "
                    "WHERE id=?",
                    (json.dumps(result), time.time(), job),
                )
        except Exception:
            # Do not persist provider responses, credentials, or paths in public errors.
            logging.getLogger(__name__).warning("Job %s failed", job)
            with self.connect() as db:
                db.execute(
                    "UPDATE jobs SET state='failed', error='processing_failed', updated=? "
                    "WHERE id=?",
                    (time.time(), job),
                )
        finally:
            try:
                cleanup()
            finally:
                self.release()

    def get(self, job):
        self.expire()
        with self.connect() as db:
            row = db.execute(
                "SELECT id,state,stage,result,error FROM jobs WHERE id=?", (job,)
            ).fetchone()
        if not row:
            return None
        return dict(
            zip(
                ("id", "state", "stage", "result", "error"),
                (*row[:3], json.loads(row[3]) if row[3] else None, row[4]),
            )
        )

    def close(self):
        self.executor.shutdown(wait=True)
