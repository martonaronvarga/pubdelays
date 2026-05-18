from __future__ import annotations

from pathlib import Path

from pubdelays.slurm import SlurmJob, SlurmResources, build_sbatch_script


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
