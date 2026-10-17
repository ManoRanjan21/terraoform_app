from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from app.module_io import build_next_module_inputs

PROJECT_ROOT = Path(__file__).resolve().parent.parent
US_EAST_DIR = PROJECT_ROOT / "s3_us_east"
EU_WEST_DIR = PROJECT_ROOT / "s3_eu_west_1"


class TerraformError(RuntimeError):
    def __init__(self, command: list[str], cwd: Path, result: subprocess.CompletedProcess[str]):
        super().__init__(
            f"Command failed ({result.returncode}) in {cwd}: {' '.join(command)}\n"
            f"{result.stdout}\n{result.stderr}"
        )
        self.command = command
        self.cwd = cwd
        self.result = result


def _tfvars_value(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    return '"{0}"'.format(value)


def write_tfvars(stack_dir: Path, variables: dict) -> None:
    lines = ["{0} = {1}\n".format(name, _tfvars_value(value)) for name, value in variables.items()]
    (stack_dir / "terraform.tfvars").write_text("".join(lines))


def run_terraform(stack_dir: Path, args: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    command = ["terraform", *args]
    result = subprocess.run(
        command,
        cwd=stack_dir,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise TerraformError(command, stack_dir, result)
    return result


def state_key(bucket_name: str) -> str:
    return f"{bucket_name}/terraform.tfstate"


def init_plan_apply(stack_dir: Path, bucket_name: str, env: dict[str, str]) -> dict[str, str]:
    init_result = run_terraform(
        stack_dir,
        [
            "init",
            "-input=false",
            "-reconfigure",
            f"-backend-config=key={state_key(bucket_name)}",
        ],
        env,
    )
    plan_result = run_terraform(stack_dir, ["plan", "-input=false", "-out=tfplan"], env)
    apply_result = run_terraform(stack_dir, ["apply", "-input=false", "-auto-approve", "tfplan"], env)
    output_result = run_terraform(stack_dir, ["output", "-json"], env)

    parsed = json.loads(output_result.stdout)
    outputs = {name: data["value"] for name, data in parsed.items()}
    outputs["_init_stdout"] = init_result.stdout
    outputs["_plan_stdout"] = plan_result.stdout
    outputs["_apply_stdout"] = apply_result.stdout
    return outputs


def _public_outputs(raw: dict) -> dict:
    return {key: value for key, value in raw.items() if not key.startswith("_")}


def deploy_stacks(bucket_name: str, env: dict[str, str]) -> dict:
    write_tfvars(US_EAST_DIR, {"bucket_name": bucket_name})
    us_east_outputs = init_plan_apply(US_EAST_DIR, bucket_name, env)

    next_inputs = build_next_module_inputs(_public_outputs(us_east_outputs))
    second_state_key = next_inputs.get("bucket_name", "{0}-module1".format(bucket_name))
    write_tfvars(EU_WEST_DIR, next_inputs)
    eu_west_outputs = init_plan_apply(EU_WEST_DIR, second_state_key, env)

    return {
        "s3_us_east": {
            "s3_name": us_east_outputs["s3_name"],
            "s3_location": us_east_outputs["s3_location"],
            "init": us_east_outputs["_init_stdout"],
            "plan": us_east_outputs["_plan_stdout"],
            "apply": us_east_outputs["_apply_stdout"],
        },
        "chained_inputs": next_inputs,
        "s3_eu_west_1": {
            "s3_name": eu_west_outputs["s3_name"],
            "s3_location": eu_west_outputs["s3_location"],
            "init": eu_west_outputs["_init_stdout"],
            "plan": eu_west_outputs["_plan_stdout"],
            "apply": eu_west_outputs["_apply_stdout"],
        },
    }


def build_process_env(deployment_overrides: dict[str, str]) -> dict[str, str]:
    env = {**os.environ, **deployment_overrides}
    env.pop("AWS_PROFILE", None)
    env.pop("AWS_DEFAULT_PROFILE", None)
    return env
