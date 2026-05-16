"""SQLite manifest for auditable and process-safe pipeline bookkeeping."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1


@dataclass(frozen=True)
class ManifestRow:
    stage: str
    status: str
    input_path: str = ""
    output_path: str = ""
    input_sha256: str = ""
    output_sha256: str = ""
    input_bytes: int | None = None
    output_bytes: int | None = None
    records: int | None = None
    deleted: int | None = None
    started_at: str = ""
    finished_at: str = ""
    elapsed_seconds: float | None = None
    worker: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)
    error: str = ""


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def sha256_file(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def file_size(path: Path | None) -> int | None:
    if path is None:
        return None
    p = Path(path)
    if not p.exists():
        return None
    return p.stat().st_size


class Manifest:
    """Small SQLite-backed append-only manifest.

    SQLite WAL mode and ``busy_timeout`` make concurrent SLURM-array writes safe
    for ordinary append workloads. Each pipeline task writes one row after it
    finishes, so no shared progress text file is needed.
    """

    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialise()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path, timeout=60.0, isolation_level=None)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=60000")
        try:
            yield conn
        finally:
            conn.close()

    def _initialise(self) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS manifest_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stage TEXT NOT NULL,
                    status TEXT NOT NULL,
                    input_path TEXT NOT NULL DEFAULT '',
                    output_path TEXT NOT NULL DEFAULT '',
                    input_sha256 TEXT NOT NULL DEFAULT '',
                    output_sha256 TEXT NOT NULL DEFAULT '',
                    input_bytes INTEGER,
                    output_bytes INTEGER,
                    records INTEGER,
                    deleted INTEGER,
                    started_at TEXT NOT NULL DEFAULT '',
                    finished_at TEXT NOT NULL DEFAULT '',
                    elapsed_seconds REAL,
                    worker TEXT NOT NULL DEFAULT '',
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    error TEXT NOT NULL DEFAULT ''
                )
                """
            )
            conn.execute(
                "INSERT OR REPLACE INTO manifest_meta(key, value) VALUES (?, ?)",
                ("schema_version", str(SCHEMA_VERSION)),
            )

    def append(self, row: ManifestRow) -> None:
        payload = asdict(row)
        metadata = payload.pop("metadata") or {}
        payload["metadata_json"] = json.dumps(
            metadata, sort_keys=True, ensure_ascii=False
        )
        columns = [
            "stage",
            "status",
            "input_path",
            "output_path",
            "input_sha256",
            "output_sha256",
            "input_bytes",
            "output_bytes",
            "records",
            "deleted",
            "started_at",
            "finished_at",
            "elapsed_seconds",
            "worker",
            "metadata_json",
            "error",
        ]
        values = [payload.get(column) for column in columns]
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                f"INSERT INTO runs ({', '.join(columns)}) VALUES ({', '.join(['?'] * len(columns))})",
                values,
            )
            conn.execute("COMMIT")

    def rows(self, *, limit: int = 20) -> list[dict[str, Any]]:
        with self.connect() as conn:
            cur = conn.execute(
                """
                SELECT id, stage, status, input_path, output_path, records, deleted,
                       started_at, finished_at, elapsed_seconds, error
                FROM runs
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            )
            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row, strict=False)) for row in cur.fetchall()]


def default_worker() -> str:
    parts = [f"pid={os.getpid()}"]
    task_id = os.environ.get("SLURM_ARRAY_TASK_ID")
    job_id = os.environ.get("SLURM_JOB_ID")
    if job_id:
        parts.append(f"slurm_job={job_id}")
    if task_id:
        parts.append(f"slurm_array_task={task_id}")
    return ";".join(parts)
