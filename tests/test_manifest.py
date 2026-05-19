from __future__ import annotations

import json
from pathlib import Path

from pubdelays.cli import main
from pubdelays.manifest import Manifest, ManifestRow


def append_rows(path: Path) -> None:
    manifest = Manifest(path)
    manifest.append(
        ManifestRow(stage="transform", status="success", output_path="ok.parquet", records=3)
    )
    manifest.append(
        ManifestRow(
            stage="aggregate",
            status="failed",
            input_path="missing",
            output_path="out.parquet",
            error="boom",
        )
    )
    manifest.append(
        ManifestRow(stage="aggregate", status="skipped", metadata={"reason": "existing"})
    )


def test_manifest_summary_preserves_stage_status_and_counts(tmp_path: Path, capsys) -> None:
    manifest_path = tmp_path / "manifest.sqlite"
    append_rows(manifest_path)

    code = main(["manifest", "summary", "--manifest", str(manifest_path), "--json"])

    rows = json.loads(capsys.readouterr().out)
    assert code == 0
    assert {row["status"] for row in rows} == {"success", "failed", "skipped"}
    assert any(row["stage"] == "transform" and row["records"] == 3 for row in rows)


def test_manifest_failed_and_show_json_are_machine_readable(tmp_path: Path, capsys) -> None:
    manifest_path = tmp_path / "manifest.sqlite"
    append_rows(manifest_path)

    failed_code = main(["manifest", "failed", "--manifest", str(manifest_path), "--json"])
    failed_rows = json.loads(capsys.readouterr().out)
    show_code = main(["manifest", "show", "--manifest", str(manifest_path), "--json"])
    show_rows = json.loads(capsys.readouterr().out)

    assert failed_code == 0
    assert failed_rows[0]["status"] == "failed"
    assert failed_rows[0]["error"] == "boom"
    assert show_code == 0
    assert show_rows[0]["status"] == "skipped"
    assert show_rows[0]["metadata"] == {"reason": "existing"}


def test_manifest_retry_script_contains_only_failed_work(tmp_path: Path, capsys) -> None:
    manifest_path = tmp_path / "manifest.sqlite"
    append_rows(manifest_path)

    code = main(["manifest", "retry-script", "--manifest", str(manifest_path)])

    output = capsys.readouterr().out
    assert code == 0
    assert "retry aggregate" in output
    assert "out.parquet" in output
    assert "ok.parquet" not in output


def test_aggregate_failure_records_manifest_error(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.sqlite"
    bad_input = tmp_path / "articles-shard-00000-of-00001.parquet"
    bad_input.write_text("not parquet", encoding="utf-8")

    try:
        main(
            [
                "aggregate",
                "--input",
                str(bad_input),
                "--output",
                str(tmp_path / "out.parquet"),
                "--manifest",
                str(manifest_path),
            ]
        )
    except Exception:
        pass

    rows = Manifest(manifest_path).rows(status="failed")
    assert rows[0]["stage"] == "aggregate"
    assert rows[0]["error"]


def test_manifest_check_archives_corrupt_sqlite_without_sqlite_cli(tmp_path: Path) -> None:
    manifest_path = tmp_path / "pipeline.sqlite"
    archive_dir = tmp_path / "archive"
    manifest_path.write_text("not sqlite", encoding="utf-8")
    Path(f"{manifest_path}-wal").write_text("wal", encoding="utf-8")

    code = main([
        "manifest",
        "check",
        "--manifest",
        str(manifest_path),
        "--cleanup",
        "--archive-dir",
        str(archive_dir),
    ])

    assert code == 1
    assert not manifest_path.exists()
    assert not Path(f"{manifest_path}-wal").exists()
    assert list(archive_dir.glob("pipeline.sqlite.corrupt.*"))
    assert list(archive_dir.glob("pipeline.sqlite-wal.corrupt.*"))


def test_manifest_collect_merges_per_task_manifests(tmp_path: Path) -> None:
    input_dir = tmp_path / "slurm" / "parse"
    append_rows(input_dir / "1-0.sqlite")
    append_rows(input_dir / "1-1.sqlite")
    target = tmp_path / "pipeline.sqlite"

    code = main([
        "manifest",
        "collect",
        "--manifest",
        str(target),
        "--input-dir",
        str(input_dir),
    ])

    rows = Manifest(target).rows(limit=10)
    assert code == 0
    assert len(rows) == 6
    assert sum(1 for row in rows if row["status"] == "failed") == 2
