from __future__ import annotations

from fastapi import BackgroundTasks, FastAPI, HTTPException

from app.credentials import deployment_env, write_backend_profile
from app.job_store import create_job, find_existing_job, get_job, public_payload, update_job
from app.models import DeployRequest
from app.terraform_runner import TerraformError, build_process_env, deploy_stacks

app = FastAPI(title="S3 Terraform Orchestrator")

ACTIVE_STATUSES = {"in_progress", "completed"}


def _run_deploy(job_id: str, request: DeployRequest) -> None:
    if request.backend is not None:
        write_backend_profile(request.backend)

    env = build_process_env(deployment_env(request.deployment))
    try:
        result = deploy_stacks(request.bucket_name, env)
        update_job(
            job_id,
            status="completed",
            message="Provisioning completed",
            result=result,
            error=None,
        )
    except TerraformError as exc:
        update_job(
            job_id,
            status="failed",
            message="Provisioning failed",
            result=None,
            error={
                "command": exc.command,
                "cwd": str(exc.cwd),
                "stdout": exc.result.stdout,
                "stderr": exc.result.stderr,
            },
        )
    except Exception as exc:
        update_job(
            job_id,
            status="failed",
            message="Provisioning failed",
            result=None,
            error={"message": str(exc)},
        )


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/deploy")
def deploy(request: DeployRequest, background_tasks: BackgroundTasks) -> dict:
    payload = public_payload(request)
    existing = find_existing_job(payload)

    if existing and existing.get("status") in ACTIVE_STATUSES:
        status = existing["status"]
        return {
            "already_exists": True,
            "job_id": existing["job_id"],
            "status": status,
            "message": (
                "Payload already exists and it is in progress"
                if status == "in_progress"
                else "Payload already exists and it is completed"
            ),
            "payload": existing.get("payload", payload),
        }

    job = create_job(payload)
    background_tasks.add_task(_run_deploy, job["job_id"], request)
    return {
        "already_exists": False,
        "job_id": job["job_id"],
        "status": job["status"],
        "message": "Provisioning triggered",
        "payload": payload,
    }


@app.get("/deploy/{job_id}")
def deploy_status(job_id: str) -> dict:
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return job
