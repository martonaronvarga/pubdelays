"""SLURM submission helpers for the pubdelays CLI."""

from __future__ import annotations

import shlex
import subprocess
from dataclasses import dataclass, field, replace
from pathlib import Path


@dataclass(frozen=True)
class SlurmResources:
    cpus_per_task: int
    mem: str
    time: str
    partition: str = ""
    account: str = ""
    qos: str = ""


@dataclass(frozen=True)
class SlurmJob:
    name: str
    command: list[str] | str
    resources: SlurmResources
    log_dir: Path
    array: str | None = None
    dependency: str | None = None
    setup: list[str] = field(default_factory=list)


class SlurmSubmissionError(RuntimeError):
    """Raised when sbatch rejects a generated job script."""

    def __init__(self, *, message: str, returncode: int, stdout: str, stderr: str, script: str) -> None:
        super().__init__(message)
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.script = script


def shell_join(parts: list[str]) -> str:
    return " ".join(shlex.quote(str(part)) for part in parts)


def sbatch_directives(job: SlurmJob) -> list[str]:
    resources = job.resources
    lines = [
        f"#SBATCH --job-name={job.name}",
        f"#SBATCH --cpus-per-task={resources.cpus_per_task}",
        f"#SBATCH --mem={resources.mem}",
        f"#SBATCH --time={resources.time}",
        f"#SBATCH --output={job.log_dir}/%x-%A_%a.out"
        if job.array
        else f"#SBATCH --output={job.log_dir}/%x-%j.out",
        f"#SBATCH --error={job.log_dir}/%x-%A_%a.err"
        if job.array
        else f"#SBATCH --error={job.log_dir}/%x-%j.err",
    ]
    if resources.partition:
        lines.append(f"#SBATCH --partition={resources.partition}")
    if resources.account:
        lines.append(f"#SBATCH --account={resources.account}")
    if resources.qos:
        lines.append(f"#SBATCH --qos={resources.qos}")
    if job.array:
        lines.append(f"#SBATCH --array={job.array}")
    if job.dependency:
        lines.append(f"#SBATCH --dependency={job.dependency}")
    return lines


def build_sbatch_script(job: SlurmJob) -> str:
    body = [
        "#!/usr/bin/env bash",
        *sbatch_directives(job),
        "set -euo pipefail",
        f"mkdir -p {shlex.quote(str(job.log_dir))}",
    ]
    body.extend(job.setup)
    if isinstance(job.command, str):
        body.append(job.command)
    else:
        body.append(shell_join(job.command))
    return "\n".join(body) + "\n"


def with_dependency(job: SlurmJob, dependency: str | None) -> SlurmJob:
    return replace(job, dependency=dependency)


class SlurmSubmitter:
    """Submit generated SLURM scripts through sbatch with explicit errors."""

    def __init__(self, sbatch: str = "sbatch") -> None:
        self.sbatch = sbatch

    def submit(self, script: str) -> str:
        result = subprocess.run(
            [self.sbatch, "--parsable"],
            input=script,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            raise SlurmSubmissionError(
                message=f"sbatch failed with exit code {result.returncode}: {result.stderr.strip()}",
                returncode=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                script=script,
            )
        job_id = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else ""
        if not job_id:
            raise SlurmSubmissionError(
                message="sbatch succeeded but returned no parsable job id",
                returncode=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                script=script,
            )
        return job_id


def submit_sbatch(script: str) -> str:
    return SlurmSubmitter().submit(script)
