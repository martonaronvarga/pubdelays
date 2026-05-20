"""SLURM submission helpers for the pubdelays CLI."""

from __future__ import annotations

import shlex
import subprocess
from dataclasses import dataclass, field, replace
from pathlib import Path


@dataclass(frozen=True)
class SlurmResources:
    """Resource request fields rendered into ``#SBATCH`` directives."""

    cpus_per_task: int
    mem: str
    time: str
    partition: str = ""
    account: str = ""
    qos: str = ""


@dataclass(frozen=True)
class SlurmJob:
    """Scheduler script model used before dry-run printing or sbatch submission."""

    name: str
    command: list[str] | str
    resources: SlurmResources
    log_dir: Path
    array: str | None = None
    array_throttle: int | None = None
    dependency: str | None = None
    setup: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SlurmSubmission:
    job_id: str
    command: tuple[str, ...]
    stdout: str
    stderr: str
    script: str


@dataclass(frozen=True)
class SlurmStatus:
    job_id: str
    state: str
    name: str
    reason: str


class SlurmSubmissionError(RuntimeError):
    """Raised when sbatch rejects a generated job script."""

    def __init__(self, *, message: str, returncode: int, stdout: str, stderr: str, script: str) -> None:
        super().__init__(message)
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.script = script


class SlurmQueryError(RuntimeError):
    """Raised when SLURM job inspection fails."""

    def __init__(self, *, message: str, returncode: int, stdout: str, stderr: str) -> None:
        super().__init__(message)
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def shell_join(parts: list[str]) -> str:
    return " ".join(shlex.quote(str(part)) for part in parts)


def sbatch_directives(job: SlurmJob) -> list[str]:
    """Render the scheduler header for a job without shell body commands."""
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
        array_spec = job.array
        if job.array_throttle and job.array_throttle > 0:
            array_spec = f"{array_spec}%{job.array_throttle}"
        lines.append(f"#SBATCH --array={array_spec}")
    if job.dependency:
        lines.append(f"#SBATCH --dependency={job.dependency}")
    return lines


def build_sbatch_script(job: SlurmJob) -> str:
    """Build the complete bash script sent to ``sbatch`` or printed in dry-runs."""
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
    """Submit and inspect SLURM jobs with explicit errors."""

    def __init__(self, sbatch: str = "sbatch", sacct: str = "sacct") -> None:
        self.sbatch = sbatch
        self.sacct = sacct

    def submit_details(self, script: str) -> SlurmSubmission:
        command = (self.sbatch, "--parsable")
        try:
            result = subprocess.run(
                list(command),
                input=script,
                text=True,
                capture_output=True,
                check=False,
            )
        except OSError as exc:
            raise SlurmSubmissionError(
                message=f"failed to execute {self.sbatch}: {exc}",
                returncode=127,
                stdout="",
                stderr=str(exc),
                script=script,
            ) from exc
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
        return SlurmSubmission(job_id=job_id, command=command, stdout=result.stdout, stderr=result.stderr, script=script)

    def submit(self, script: str) -> str:
        return self.submit_details(script).job_id

    def status(self, job_id: str) -> list[SlurmStatus]:
        command = [self.sacct, "-j", job_id, "--format=JobID,State,JobName%80,Reason", "--noheader", "--parsable2"]
        try:
            result = subprocess.run(command, text=True, capture_output=True, check=False)
        except OSError as exc:
            raise SlurmQueryError(
                message=f"failed to execute {self.sacct}: {exc}",
                returncode=127,
                stdout="",
                stderr=str(exc),
            ) from exc
        if result.returncode != 0:
            raise SlurmQueryError(
                message=f"sacct failed with exit code {result.returncode}: {result.stderr.strip()}",
                returncode=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
            )
        return parse_sacct_status(result.stdout)


def parse_sacct_status(output: str) -> list[SlurmStatus]:
    """Parse ``sacct --parsable2`` output into typed scheduler rows."""
    statuses: list[SlurmStatus] = []
    for line in output.splitlines():
        if not line.strip():
            continue
        job_id, state, name, reason, *_rest = [*line.split("|"), "", "", "", ""]
        statuses.append(SlurmStatus(job_id=job_id, state=state, name=name, reason=reason))
    return statuses


def submit_sbatch(script: str) -> str:
    return SlurmSubmitter().submit(script)


def query_max_array_size(scontrol: str = "scontrol") -> int | None:
    """Query SLURM ``MaxArraySize`` from ``scontrol show config``.

    Returns ``None`` when the value cannot be determined.
    """
    try:
        result = subprocess.run(
            [scontrol, "show", "config"],
            text=True,
            capture_output=True,
            check=False,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    for line in result.stdout.splitlines():
        if "MaxArraySize" in line:
            parts = line.split("=")
            if len(parts) >= 2:
                try:
                    return int(parts[-1].strip())
                except ValueError:
                    return None
    return None
