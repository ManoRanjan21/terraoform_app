from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
JOBS_FILE = DATA_DIR / "jobs.json"
PAYLOADS_DIR = DATA_DIR / "payloads"

_lock = threading.Lock()


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def payload_key(payload: dict) -> str:
    return payload["bucket_name"]


def public_payload(request) -> dict:
    return {"bucket_name": request.bucket_name}


def _empty_store() -> dict:
    return {"jobs": {}, "payload_index": {}}


def _read_store() -> dict:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not JOBS_FILE.exists():
        return _empty_store()
    try:
        data = json.loads(JOBS_FILE.read_text())
    except json.JSONDecodeError:
        return _empty_store()
    data.setdefault("jobs", {})
    data.setdefault("payload_index", {})
    return data


def _write_store(store: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    JOBS_FILE.write_text(json.dumps(store, indent=2) + "\n")


def _write_payload_file(job_id: str, payload: dict) -> None:
    PAYLOADS_DIR.mkdir(parents=True, exist_ok=True)
    path = PAYLOADS_DIR / f"{job_id}.json"
    path.write_text(json.dumps(payload, indent=2) + "\n")


def find_existing_job(payload: dict) -> Optional[dict]:
    key = payload_key(payload)
    with _lock:
        store = _read_store()
        job_id = store["payload_index"].get(key)
        if not job_id:
            return None
        return store["jobs"].get(job_id)


def create_job(payload: dict) -> dict:
    job_id = str(uuid4())
    now = _utcnow()
    job = {
        "job_id": job_id,
        "status": "in_progress",
        "message": "Provisioning started",
        "payload": payload,
        "created_at": now,
        "updated_at": now,
        "result": None,
        "error": None,
    }
    with _lock:
        store = _read_store()
        store["jobs"][job_id] = job
        store["payload_index"][payload_key(payload)] = job_id
        _write_store(store)
        _write_payload_file(job_id, payload)
    return job


def get_job(job_id: str) -> Optional[dict]:
    with _lock:
        return _read_store()["jobs"].get(job_id)


def update_job(job_id: str, **fields) -> Optional[dict]:
    with _lock:
        store = _read_store()
        job = store["jobs"].get(job_id)
        if job is None:
            return None
        job.update(fields)
        job["updated_at"] = _utcnow()
        store["jobs"][job_id] = job
        _write_store(store)
        return job
