from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest

from pubdelays.cli import build_parser, build_slurm_job
from pubdelays.slurm import (
    SlurmJob,
    SlurmResources,
    SlurmSubmissionError,
    SlurmSubmitter,
    build_sbatch_script,
    parse_sacct_status,
)


def test_sbatch_script_includes_array_resources_and_dependency(tmp_path: Path) -> None:
    job = SlurmJob(
        name="pubdelays-transform",
        command='uv run pubdelays-pipeline transform-shard --shard-index "$SLURM_ARRAY_TASK_ID"',
        resources=SlurmResources(cpus_per_task=4, mem="24G", time="06:00:00", partition="cpu"),
        log_dir=tmp_path / "logs",
        array="0-63",
        dependency="afterok:123",
    )

    script = build_sbatch_script(job)

    assert "#SBATCH --array=0-63" in script
    assert "#SBATCH --dependency=afterok:123" in script
    assert "#SBATCH --cpus-per-task=4" in script
    assert "#SBATCH --mem=24G" in script
    assert "#SBATCH --partition=cpu" in script
    assert 'transform-shard --shard-index "$SLURM_ARRAY_TASK_ID"' in script


def test_submitter_raises_explicit_error_on_sbatch_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(*_args: Any, **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=["sbatch", "--parsable"], returncode=1, stdout="job hint", stderr="bad qos"
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(SlurmSubmissionError) as excinfo:
        SlurmSubmitter().submit("#!/usr/bin/env bash\nfalse\n")

    assert excinfo.value.returncode == 1
    assert excinfo.value.stdout == "job hint"
    assert excinfo.value.stderr == "bad qos"
    assert "bad qos" in str(excinfo.value)


def test_submitter_rejects_empty_parsable_job_id(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(*_args: Any, **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=["sbatch", "--parsable"], returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(SlurmSubmissionError, match="no parsable job id"):
        SlurmSubmitter().submit("#!/usr/bin/env bash\ntrue\n")


def test_submitter_returns_submission_trace(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(*_args: Any, **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=["sbatch", "--parsable"], returncode=0, stdout="12345;cluster\n", stderr="queued"
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    submission = SlurmSubmitter().submit_details("#!/usr/bin/env bash\ntrue\n")

    assert submission.job_id == "12345;cluster"
    assert submission.command == ("sbatch", "--parsable")
    assert submission.stderr == "queued"
    assert "true" in submission.script


def test_build_slurm_download_external_job_uses_configured_source() -> None:
    args = build_parser().parse_args(
        [
            "slurm",
            "submit",
            "download-external",
            "--external-source",
            "publisher",
            "--start-year",
            "2023",
            "--end-year",
            "2024",
            "--dry-run",
        ]
    )

    job, metadata = build_slurm_job(args, "download-external")

    assert metadata == {"stage": "download-external"}
    assert job.name == "pubdelays-download-external"
    assert "download-external" in job.command
    assert "--source" in job.command
    assert "publisher" in job.command
    assert "--start-year" in job.command
    assert "2023" in job.command


def test_parse_sacct_status_returns_typed_rows() -> None:
    statuses = parse_sacct_status("12345|COMPLETED|pubdelays-parse|None\n12345_7|FAILED|pubdelays-parse|OutOfMemory\n")

    assert statuses[0].job_id == "12345"
    assert statuses[0].state == "COMPLETED"
    assert statuses[1].job_id == "12345_7"
    assert statuses[1].reason == "OutOfMemory"
