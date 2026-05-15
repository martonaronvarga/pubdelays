"""Command-line entrypoint for the PubMed/MEDLINE publication-delay pipeline."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
import time
import urllib.request
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Callable

from pubdelays.aggregate import aggregate_articles
from pubdelays.external import (
    preprocess_doaj,
    preprocess_npi,
    preprocess_retraction_watch,
    preprocess_scimago,
    preprocess_wos,
)
from pubdelays.fs import atomic_output_path, complete_file
from pubdelays.manifest import (
    Manifest,
    ManifestRow,
    default_worker,
    file_size,
    sha256_file,
    utc_now,
)
from pubdelays.parser.medline import parse_medline_xml
from pubdelays.transform import ExternalInputs, transform_files
from pubdelays.ui import err, info, ok, print_kv_table, warn

PUBMED_BASE_URLS = {
    "baseline": "https://ftp.ncbi.nlm.nih.gov/pubmed/baseline/",
    "updatefiles": "https://ftp.ncbi.nlm.nih.gov/pubmed/updatefiles/",
}

DEFAULT_MANIFEST = Path("data/manifests/pipeline.sqlite")


@dataclass(frozen=True)
class ParseStats:
    input_path: str
    output_path: str
    records: int
    deleted: int
    skipped: bool = False


def manifest_from_args(args: argparse.Namespace) -> Manifest:
    return Manifest(Path(getattr(args, "manifest", DEFAULT_MANIFEST)))


def elapsed(start: float) -> float:
    return round(time.time() - start, 3)


def maybe_sha256(path: Path | None, enabled: bool = True) -> str:
    if not enabled or path is None:
        return ""
    p = Path(path)
    if not p.exists() or not p.is_file():
        return ""
    return sha256_file(p)


def append_manifest(
    manifest: Manifest,
    *,
    stage: str,
    status: str,
    started_at: str,
    start_seconds: float,
    input_path: Path | None = None,
    output_path: Path | None = None,
    records: int | None = None,
    deleted: int | None = None,
    metadata: dict[str, Any] | None = None,
    error_message: str = "",
    checksum: bool = True,
) -> None:
    manifest.append(
        ManifestRow(
            stage=stage,
            status=status,
            input_path=str(input_path or ""),
            output_path=str(output_path or ""),
            input_sha256=maybe_sha256(input_path, checksum),
            output_sha256=maybe_sha256(output_path, checksum),
            input_bytes=file_size(input_path),
            output_bytes=file_size(output_path),
            records=records,
            deleted=deleted,
            started_at=started_at,
            finished_at=utc_now(),
            elapsed_seconds=elapsed(start_seconds),
            worker=default_worker(),
            metadata=metadata or {},
            error=error_message,
        )
    )


def list_xml_paths(path_dir: str | Path) -> list[Path]:
    path = Path(path_dir).expanduser()
    if not path.exists():
        return []
    suffixes = {".xml", ".nxml"}
    return sorted(
        candidate
        for candidate in path.rglob("*")
        if candidate.is_file()
        and (candidate.suffix in suffixes or candidate.name.endswith(".xml.gz"))
    )


def list_json_paths(path_dir: str | Path) -> list[Path]:
    path = Path(path_dir).expanduser()
    if not path.exists():
        return []
    return sorted(list(path.rglob("*.jsonl")) + list(path.rglob("*.json")))


def output_path_for(input_path: Path, output_dir: Path, fmt: str) -> Path:
    extension = "jsonl" if fmt == "jsonl" else "json"
    return output_dir / f"{input_path.name}.{extension}"


def transform_output_path_for(
    input_path: Path, output_dir: Path, fmt: str = "parquet"
) -> Path:
    suffix = "parquet" if fmt == "parquet" else fmt
    return output_dir / f"{input_path.name}.{suffix}"


def filters_output_path_for(input_path: Path, output_dir: Path) -> Path:
    return output_dir / f"{input_path.name}.filters.csv"


def parse_one(
    input_path: str | Path,
    output_path: str | Path,
    *,
    fmt: str,
    resume: bool,
    year_info_only: bool,
    nlm_category: bool,
    author_list: bool,
    reference_list: bool,
    parse_mesh_subterms: bool,
    min_pub_year: int | None,
    manifest_path: str | Path | None = None,
    checksum: bool = True,
) -> ParseStats:
    input_path = Path(input_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = Manifest(Path(manifest_path)) if manifest_path else None
    started_at = utc_now()
    start_seconds = time.time()

    try:
        if resume and complete_file(output_path):
            stats = ParseStats(str(input_path), str(output_path), 0, 0, skipped=True)
            if manifest:
                append_manifest(
                    manifest,
                    stage="parse",
                    status="skipped",
                    input_path=input_path,
                    output_path=output_path,
                    records=0,
                    deleted=0,
                    started_at=started_at,
                    start_seconds=start_seconds,
                    metadata={"format": fmt, "reason": "existing_output"},
                    checksum=checksum,
                )
            return stats

        records = 0
        deleted = 0
        iterator = parse_medline_xml(
            input_path,
            year_info_only=year_info_only,
            nlm_category=nlm_category,
            author_list=author_list,
            reference_list=reference_list,
            parse_downto_mesh_subterms=parse_mesh_subterms,
            min_pub_year=min_pub_year,
        )

        with atomic_output_path(output_path) as tmp_path:
            if fmt == "jsonl":
                with tmp_path.open("w", encoding="utf-8") as handle:
                    for record in iterator:
                        records += 1
                        if record.get("delete"):
                            deleted += 1
                        handle.write(
                            json.dumps(
                                record, ensure_ascii=False, separators=(",", ":")
                            )
                        )
                        handle.write("\n")
            else:
                data = []
                for record in iterator:
                    records += 1
                    if record.get("delete"):
                        deleted += 1
                    data.append(record)
                with tmp_path.open("w", encoding="utf-8") as handle:
                    json.dump(data, handle, ensure_ascii=False)
                    handle.write("\n")

        if manifest:
            append_manifest(
                manifest,
                stage="parse",
                status="success",
                input_path=input_path,
                output_path=output_path,
                records=records,
                deleted=deleted,
                started_at=started_at,
                start_seconds=start_seconds,
                metadata={"format": fmt, "min_pub_year": min_pub_year},
                checksum=checksum,
            )
        return ParseStats(str(input_path), str(output_path), records, deleted)
    except Exception as exc:
        if manifest:
            append_manifest(
                manifest,
                stage="parse",
                status="failed",
                input_path=input_path,
                output_path=output_path,
                records=0,
                deleted=0,
                started_at=started_at,
                start_seconds=start_seconds,
                error_message=repr(exc),
                checksum=checksum,
            )
        raise


def parse_kwargs(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "fmt": args.format,
        "resume": args.resume,
        "year_info_only": args.year_info_only,
        "nlm_category": args.nlm_category,
        "author_list": args.author_list,
        "reference_list": args.reference_list,
        "parse_mesh_subterms": args.parse_mesh_subterms,
        "min_pub_year": args.min_pub_year,
        "manifest_path": args.manifest,
        "checksum": not args.no_checksum,
    }


def cmd_parse_one(args: argparse.Namespace) -> int:
    stats = parse_one(Path(args.input), Path(args.output), **parse_kwargs(args))
    status = "skipped" if stats.skipped else "parsed"
    ok(f"{status} {stats.input_path} -> {stats.output_path}")
    print_kv_table({"records": stats.records, "deleted": stats.deleted})
    return 0


def cmd_parse(args: argparse.Namespace) -> int:
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    xml_paths = list_xml_paths(input_dir)
    if not xml_paths:
        err(f"No XML files found in {input_dir}")
        return 1

    jobs = args.jobs if args.jobs is not None else max((os.cpu_count() or 2) - 1, 1)
    kwargs = parse_kwargs(args)
    total_records = 0
    total_deleted = 0
    skipped = 0

    info(f"parse files={len(xml_paths)} jobs={jobs} output={output_dir}")
    if jobs == 1:
        iterator = (
            parse_one(path, output_path_for(path, output_dir, args.format), **kwargs)
            for path in xml_paths
        )
        for stats in iterator:
            total_records += stats.records
            total_deleted += stats.deleted
            skipped += int(stats.skipped)
            ok(
                f"{'skipped' if stats.skipped else 'parsed'} {Path(stats.input_path).name}"
            )
    else:
        with ProcessPoolExecutor(max_workers=jobs) as executor:
            futures = [
                executor.submit(
                    parse_one,
                    path,
                    output_path_for(path, output_dir, args.format),
                    **kwargs,
                )
                for path in xml_paths
            ]
            for future in as_completed(futures):
                stats = future.result()
                total_records += stats.records
                total_deleted += stats.deleted
                skipped += int(stats.skipped)
                ok(
                    f"{'skipped' if stats.skipped else 'parsed'} {Path(stats.input_path).name}"
                )

    print_kv_table(
        {
            "files": len(xml_paths),
            "skipped": skipped,
            "records": total_records,
            "deleted": total_deleted,
        }
    )
    return 0


def validate_json_file(path: Path) -> tuple[bool, int]:
    count = 0
    try:
        if path.suffix == ".jsonl":
            with path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    if not line.strip():
                        continue
                    json.loads(line)
                    count += 1
        else:
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
                count = len(data) if isinstance(data, list) else 1
        return True, count
    except Exception as exc:
        err(f"INVALID {path}: {exc}")
        return False, count


def cmd_validate(args: argparse.Namespace) -> int:
    manifest = manifest_from_args(args)
    started_at = utc_now()
    start_seconds = time.time()
    input_path = Path(args.input)
    paths = list_json_paths(input_path) if input_path.is_dir() else [input_path]
    failures = 0
    total_records = 0
    for path in paths:
        ok_file, count = validate_json_file(path)
        total_records += count
        if ok_file:
            ok(f"{path}: {count} records")
        else:
            failures += 1
    append_manifest(
        manifest,
        stage="validate-json",
        status="failed" if failures else "success",
        input_path=input_path,
        records=total_records,
        deleted=failures,
        started_at=started_at,
        start_seconds=start_seconds,
        metadata={"files": len(paths), "failures": failures},
        checksum=not args.no_checksum,
    )
    print_kv_table(
        {"files": len(paths), "records": total_records, "failures": failures}
    )
    return 1 if failures else 0


def parse_j_medline(text: str) -> list[dict[str, str]]:
    keys = [
        "JrId",
        "JournalTitle",
        "MedAbbr",
        "ISSN (Print)",
        "ISSN (Online)",
        "IsoAbbr",
        "NlmId",
    ]
    records: list[dict[str, str]] = []
    current = dict.fromkeys(keys, "")
    for line in text.splitlines():
        if line.startswith("-"):
            if any(current.values()):
                records.append(dict(current))
            current = dict.fromkeys(keys, "")
            continue
        if ":" in line:
            key, value = map(str.strip, line.split(":", 1))
            if key in current:
                current[key] = value
    if any(current.values()):
        records.append(dict(current))
    return records


def cmd_journals(args: argparse.Namespace) -> int:
    manifest = manifest_from_args(args)
    started_at = utc_now()
    start_seconds = time.time()
    output = Path(args.output)
    with urllib.request.urlopen(args.url) as response:
        text = response.read().decode("utf-8")
    rows = parse_j_medline(text)
    with atomic_output_path(output) as tmp_path:
        with tmp_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "JrId",
                    "JournalTitle",
                    "MedAbbr",
                    "ISSN (Print)",
                    "ISSN (Online)",
                    "IsoAbbr",
                    "NlmId",
                ],
            )
            writer.writeheader()
            writer.writerows(rows)
    append_manifest(
        manifest,
        stage="journals",
        status="success",
        output_path=output,
        records=len(rows),
        started_at=started_at,
        start_seconds=start_seconds,
        metadata={"url": args.url},
        checksum=not args.no_checksum,
    )
    ok(f"wrote {len(rows)} journal rows to {output}")
    return 0


def index_links(url: str) -> list[str]:
    with urllib.request.urlopen(url) as response:
        html = response.read().decode("utf-8", errors="replace")
    return sorted(set(re.findall(r'href="([^"]+\.(?:gz|md5))"', html)))


def download_file(url: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with atomic_output_path(output_path) as tmp_path:
        with urllib.request.urlopen(url) as response, tmp_path.open("wb") as handle:
            while chunk := response.read(1024 * 1024):
                handle.write(chunk)


def md5sum(path: Path) -> str:
    digest = hashlib.md5(usedforsecurity=False)
    with Path(path).open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def parse_md5_sidecar(content: str) -> tuple[str, str] | None:
    content = content.strip()
    if not content:
        return None
    ncbi_match = re.match(
        r"MD5 \((?P<filename>[^)]+)\) = (?P<md5>[0-9a-fA-F]{32})", content
    )
    if ncbi_match:
        return ncbi_match.group("md5").lower(), ncbi_match.group("filename")
    unix_match = re.match(r"(?P<md5>[0-9a-fA-F]{32})\s+\*?(?P<filename>.+)", content)
    if unix_match:
        return unix_match.group("md5").lower(), Path(unix_match.group("filename")).name
    return None


def verify_md5_file(md5_path: Path) -> bool:
    parsed = parse_md5_sidecar(md5_path.read_text(encoding="utf-8"))
    if parsed is None:
        return False
    expected, filename = parsed
    data_path = md5_path.parent / Path(filename).name
    return data_path.exists() and md5sum(data_path) == expected


def cmd_download(args: argparse.Namespace) -> int:
    manifest = manifest_from_args(args)
    started_at = utc_now()
    start_seconds = time.time()
    base_url = PUBMED_BASE_URLS[args.source]
    output_dir = Path(args.output_dir)
    links = index_links(base_url)
    if args.limit is not None:
        links = links[: args.limit]
    downloaded = 0
    skipped = 0
    for link in links:
        target = output_dir / link
        if args.resume and complete_file(target):
            skipped += 1
            warn(f"skip {target}")
            continue
        info(f"download {base_url}{link} -> {target}")
        download_file(base_url + link, target)
        downloaded += 1
    failures = [
        str(path)
        for path in sorted(output_dir.glob("*.md5"))
        if not verify_md5_file(path)
    ]
    append_manifest(
        manifest,
        stage="download",
        status="failed" if failures else "success",
        output_path=output_dir,
        records=downloaded,
        deleted=len(failures),
        started_at=started_at,
        start_seconds=start_seconds,
        metadata={
            "source": args.source,
            "links": len(links),
            "skipped": skipped,
            "failures": failures,
        },
        checksum=False,
    )
    if failures:
        err("MD5 failures")
        for failure in failures:
            err(f"  {failure}")
        return 1
    ok(
        f"downloaded={downloaded} skipped={skipped} into {output_dir}; MD5 checks passed"
    )
    return 0


def _optional_path(value: str | None) -> Path | None:
    return Path(value) if value else None


def external_inputs_from_args(args: argparse.Namespace) -> ExternalInputs:
    return ExternalInputs(
        scimago=_optional_path(args.scimago),
        web_of_science=_optional_path(args.web_of_science),
        doaj=_optional_path(args.doaj),
        norwegian_list=_optional_path(args.norwegian_list),
        retraction_watch=_optional_path(args.retraction_watch),
    )


def cmd_transform_one(args: argparse.Namespace) -> int:
    manifest = manifest_from_args(args)
    started_at = utc_now()
    start_seconds = time.time()
    input_path = Path(args.input)
    output_path = Path(args.output)
    if args.resume and complete_file(output_path):
        append_manifest(
            manifest,
            stage="transform",
            status="skipped",
            input_path=input_path,
            output_path=output_path,
            started_at=started_at,
            start_seconds=start_seconds,
            metadata={"reason": "existing_output"},
            checksum=not args.no_checksum,
        )
        warn(f"skip existing {output_path}")
        return 0
    result = transform_files(
        input_path,
        output_path,
        filters_path=_optional_path(args.filters_output),
        external=external_inputs_from_args(args),
        min_received=date.fromisoformat(args.min_received),
    )
    append_manifest(
        manifest,
        stage="transform",
        status="success",
        input_path=input_path,
        output_path=output_path,
        records=result.counts.get("final_rows", 0),
        started_at=started_at,
        start_seconds=start_seconds,
        metadata={
            "counts": dict(result.counts),
            "filters_path": str(result.filters_path or ""),
        },
        checksum=not args.no_checksum,
    )
    ok(f"wrote {result.output_path}")
    print_kv_table(result.counts)
    return 0


def cmd_transform(args: argparse.Namespace) -> int:
    input_path = Path(args.input)
    output_dir = Path(args.output_dir)
    inputs = list_json_paths(input_path) if input_path.is_dir() else [input_path]
    if not inputs:
        err(f"No JSON/JSONL files found in {input_path}")
        return 1
    jobs = args.jobs if args.jobs is not None else 1
    common = {
        "fmt": "unused",
    }
    del common
    info(f"transform files={len(inputs)} jobs={jobs} output_dir={output_dir}")

    payloads: list[dict[str, Any]] = []
    for path in inputs:
        payload = {key: value for key, value in vars(args).items() if key != "func"}
        payload["input"] = str(path)
        payload["output"] = str(
            transform_output_path_for(path, output_dir, args.format)
        )
        payload["filters_output"] = str(filters_output_path_for(path, output_dir))
        payloads.append(payload)

    if jobs == 1:
        for payload in payloads:
            transform_worker(payload)
    else:
        with ProcessPoolExecutor(max_workers=jobs) as executor:
            futures = [
                executor.submit(transform_worker, payload) for payload in payloads
            ]
            for future in as_completed(futures):
                future.result()
    return 0


def transform_worker(payload: dict[str, Any]) -> int:
    args = argparse.Namespace(**payload)
    return cmd_transform_one(args)


def _preprocess_stage(
    args: argparse.Namespace,
    *,
    stage: str,
    input_path: Path,
    output_path: Path,
    func: Callable[[], int],
) -> int:
    manifest = manifest_from_args(args)
    started_at = utc_now()
    start_seconds = time.time()
    try:
        if args.resume and complete_file(output_path):
            append_manifest(
                manifest,
                stage=stage,
                status="skipped",
                input_path=input_path,
                output_path=output_path,
                started_at=started_at,
                start_seconds=start_seconds,
                metadata={"reason": "existing_output"},
                checksum=not args.no_checksum,
            )
            warn(f"skip existing {output_path}")
            return 0
        rows = func()
        append_manifest(
            manifest,
            stage=stage,
            status="success",
            input_path=input_path,
            output_path=output_path,
            records=rows,
            started_at=started_at,
            start_seconds=start_seconds,
            checksum=not args.no_checksum,
        )
        ok(f"{stage}: wrote {rows} rows to {output_path}")
        return 0
    except Exception as exc:
        append_manifest(
            manifest,
            stage=stage,
            status="failed",
            input_path=input_path,
            output_path=output_path,
            started_at=started_at,
            start_seconds=start_seconds,
            error_message=repr(exc),
            checksum=not args.no_checksum,
        )
        raise


def cmd_external_scimago(args: argparse.Namespace) -> int:
    return _preprocess_stage(
        args,
        stage="external-scimago",
        input_path=Path(args.input_dir),
        output_path=Path(args.output),
        func=lambda: preprocess_scimago(
            Path(args.input_dir),
            Path(args.output),
            start_year=args.start_year,
            end_year=args.end_year,
        ),
    )


def cmd_external_wos(args: argparse.Namespace) -> int:
    return _preprocess_stage(
        args,
        stage="external-wos",
        input_path=Path(args.input),
        output_path=Path(args.output),
        func=lambda: preprocess_wos(Path(args.input), Path(args.output)),
    )


def cmd_external_npi(args: argparse.Namespace) -> int:
    return _preprocess_stage(
        args,
        stage="external-npi",
        input_path=Path(args.input),
        output_path=Path(args.output),
        func=lambda: preprocess_npi(Path(args.input), Path(args.output)),
    )


def cmd_external_retraction_watch(args: argparse.Namespace) -> int:
    return _preprocess_stage(
        args,
        stage="external-retraction-watch",
        input_path=Path(args.input),
        output_path=Path(args.output),
        func=lambda: preprocess_retraction_watch(Path(args.input), Path(args.output)),
    )


def cmd_external_doaj(args: argparse.Namespace) -> int:
    return _preprocess_stage(
        args,
        stage="external-doaj",
        input_path=Path(args.input),
        output_path=Path(args.output),
        func=lambda: preprocess_doaj(Path(args.input), Path(args.output)),
    )


def cmd_aggregate(args: argparse.Namespace) -> int:
    manifest = manifest_from_args(args)
    started_at = utc_now()
    start_seconds = time.time()
    input_path = Path(args.input)
    output_path = Path(args.output)
    if args.resume and complete_file(output_path):
        append_manifest(
            manifest,
            stage="aggregate",
            status="skipped",
            input_path=input_path,
            output_path=output_path,
            started_at=started_at,
            start_seconds=start_seconds,
            metadata={"reason": "existing_output"},
            checksum=not args.no_checksum,
        )
        warn(f"skip existing {output_path}")
        return 0
    rows = aggregate_tsvs(input_path, output_path)
    append_manifest(
        manifest,
        stage="aggregate",
        status="success",
        input_path=input_path,
        output_path=output_path,
        records=rows,
        started_at=started_at,
        start_seconds=start_seconds,
        checksum=not args.no_checksum,
    )
    ok(f"aggregate: wrote {rows} rows to {output_path}")
    return 0


def cmd_list_inputs(args: argparse.Namespace) -> int:
    if args.kind == "xml":
        paths = list_xml_paths(args.input_dir)
    elif args.kind == "json":
        paths = list_json_paths(args.input_dir)
    else:
        paths = sorted(Path(args.input_dir).rglob(args.glob))
    output = Path(args.output)
    with atomic_output_path(output) as tmp_path:
        tmp_path.write_text("".join(f"{path}\n" for path in paths), encoding="utf-8")
    ok(f"listed {len(paths)} {args.kind} paths in {output}")
    return 0


def cmd_init_dirs(args: argparse.Namespace) -> int:
    dirs = [
        "data/raw_data/pubmed/xmls",
        "data/raw_data/scimago",
        "data/raw_data/web_of_science",
        "data/raw_data/directory_of_open_access_journals",
        "data/raw_data/norwegian_publication_indicator",
        "data/raw_data/retraction_watch",
        "data/temp_data/pubmed/jsonl",
        "data/temp_data/article_parquet",
        "data/processed_data",
        "data/manifests",
        "data/external",
    ]
    for directory in dirs:
        Path(directory).mkdir(parents=True, exist_ok=True)
    ok("created canonical data directories")
    return 0


def cmd_preflight(args: argparse.Namespace) -> int:
    checks = {
        "PubMed XML dir": Path(args.pubmed_xml_dir),
        "Scimago dir": Path(args.scimago_dir),
        "Web of Science CSV": Path(args.web_of_science),
        "DOAJ CSV": Path(args.doaj),
        "NPI CSV": Path(args.norwegian_list),
        "Retraction Watch CSV": Path(args.retraction_watch),
    }
    failures = 0
    for label, path in checks.items():
        exists = path.exists()
        if exists:
            ok(f"{label}: {path}")
        else:
            warn(f"missing {label}: {path}")
            failures += 1
    xml_count = (
        len(list_xml_paths(args.pubmed_xml_dir))
        if Path(args.pubmed_xml_dir).exists()
        else 0
    )
    print_kv_table({"xml_files": xml_count, "missing_inputs": failures})
    return 1 if failures else 0


def cmd_transform_shard(args: argparse.Namespace) -> int:
    manifest = manifest_from_args(args)
    started_at = utc_now()
    start_seconds = time.time()
    input_list = Path(args.input_list)
    paths = [
        Path(line.strip())
        for line in input_list.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    selected = [
        path
        for index, path in enumerate(paths)
        if index % args.shards == args.shard_index
    ]
    output_dir = Path(args.output_dir)
    output_path = (
        output_dir
        / f"articles-shard-{args.shard_index:05d}-of-{args.shards:05d}.{args.format}"
    )
    filters_path = (
        output_dir
        / f"articles-shard-{args.shard_index:05d}-of-{args.shards:05d}.filters.csv"
    )

    if not selected:
        warn(f"empty shard {args.shard_index}/{args.shards}")
        return 0
    if args.resume and complete_file(output_path):
        append_manifest(
            manifest,
            stage="transform-shard",
            status="skipped",
            input_path=input_list,
            output_path=output_path,
            started_at=started_at,
            start_seconds=start_seconds,
            metadata={
                "reason": "existing_output",
                "shard_index": args.shard_index,
                "shards": args.shards,
            },
            checksum=not args.no_checksum,
        )
        warn(f"skip existing {output_path}")
        return 0

    result = transform_files(
        selected,
        output_path,
        filters_path=filters_path,
        external=external_inputs_from_args(args),
        min_received=date.fromisoformat(args.min_received),
    )
    append_manifest(
        manifest,
        stage="transform-shard",
        status="success",
        input_path=input_list,
        output_path=output_path,
        records=result.counts.get("final_rows", 0),
        started_at=started_at,
        start_seconds=start_seconds,
        metadata={
            "counts": dict(result.counts),
            "shard_index": args.shard_index,
            "shards": args.shards,
            "inputs": len(selected),
        },
        checksum=not args.no_checksum,
    )
    ok(f"transform-shard {args.shard_index}/{args.shards}: wrote {result.output_path}")
    print_kv_table(result.counts)
    return 0


def cmd_manifest(args: argparse.Namespace) -> int:
    manifest = manifest_from_args(args)
    rows = manifest.rows(limit=args.limit)
    if not rows:
        warn("manifest is empty")
        return 0
    for row in rows:
        print_kv_table(row)
        print("---")
    return 0


def add_common_stage_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--manifest", default=str(DEFAULT_MANIFEST), help="SQLite manifest path"
    )
    parser.add_argument(
        "--no-checksum", action="store_true", help="skip SHA-256 manifest checksums"
    )
    parser.add_argument(
        "--resume", action="store_true", help="skip existing non-empty outputs"
    )


def add_parse_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--format", choices=["jsonl", "json"], default="jsonl")
    parser.add_argument("--year-info-only", action="store_true")
    parser.add_argument("--nlm-category", action="store_true")
    parser.add_argument("--author-list", action="store_true")
    parser.add_argument("--reference-list", action="store_true")
    parser.add_argument("--parse-mesh-subterms", action="store_true")
    parser.add_argument("--min-pub-year", type=int, default=None)
    add_common_stage_args(parser)


def add_external_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--scimago", default=None)
    parser.add_argument("--web-of-science", default=None)
    parser.add_argument("--doaj", default=None)
    parser.add_argument("--norwegian-list", default=None)
    parser.add_argument("--retraction-watch", default=None)
    parser.add_argument("--min-received", default="2013-01-01")
    add_common_stage_args(parser)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pubdelays-pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_dirs = subparsers.add_parser(
        "init-dirs", help="create canonical data directories"
    )
    init_dirs.set_defaults(func=cmd_init_dirs)

    preflight = subparsers.add_parser(
        "preflight", help="check expected raw-data locations before a run"
    )
    preflight.add_argument("--pubmed-xml-dir", default="data/raw_data/pubmed/xmls")
    preflight.add_argument("--scimago-dir", default="data/raw_data/scimago")
    preflight.add_argument(
        "--web-of-science", default="data/raw_data/web_of_science/wos.csv"
    )
    preflight.add_argument(
        "--doaj",
        default="data/raw_data/directory_of_open_access_journals/doaj_2025_05_15.csv",
    )
    preflight.add_argument(
        "--norwegian-list",
        default="data/raw_data/norwegian_publication_indicator/norwegian_list_2025_05_14.csv",
    )
    preflight.add_argument(
        "--retraction-watch",
        default="data/raw_data/retraction_watch/retraction_watch.csv",
    )
    preflight.set_defaults(func=cmd_preflight)

    parse_one_p = subparsers.add_parser(
        "parse-one", help="parse one MEDLINE XML/XML.GZ file"
    )
    parse_one_p.add_argument("--input", required=True)
    parse_one_p.add_argument("--output", required=True)
    add_parse_options(parse_one_p)
    parse_one_p.set_defaults(func=cmd_parse_one)

    parse_p = subparsers.add_parser(
        "parse", help="parse all MEDLINE XML/XML.GZ files in a directory"
    )
    parse_p.add_argument("--input-dir", required=True)
    parse_p.add_argument("--output-dir", required=True)
    parse_p.add_argument("--jobs", type=int, default=None)
    add_parse_options(parse_p)
    parse_p.set_defaults(func=cmd_parse)

    validate = subparsers.add_parser("validate", help="validate JSON or JSONL outputs")
    validate.add_argument("input")
    add_common_stage_args(validate)
    validate.set_defaults(func=cmd_validate)

    journals = subparsers.add_parser(
        "journals", help="download and parse NLM J_Medline.txt"
    )
    journals.add_argument(
        "--url", default="https://ftp.ncbi.nlm.nih.gov/pubmed/J_Medline.txt"
    )
    journals.add_argument("--output", required=True)
    add_common_stage_args(journals)
    journals.set_defaults(func=cmd_journals)

    transform_one = subparsers.add_parser(
        "transform-one", help="transform one parsed JSON/JSONL file to one TSV"
    )
    transform_one.add_argument("--input", required=True)
    transform_one.add_argument("--output", required=True)
    transform_one.add_argument("--filters-output", default=None)
    add_external_args(transform_one)
    transform_one.set_defaults(func=cmd_transform_one)

    transform = subparsers.add_parser(
        "transform", help="transform JSON/JSONL files to per-file article outputs"
    )
    transform.add_argument("--input", required=True)
    transform.add_argument("--output-dir", required=True)
    transform.add_argument("--jobs", type=int, default=1)
    transform.add_argument(
        "--format", choices=["parquet", "tsv", "csv"], default="parquet"
    )
    add_external_args(transform)
    transform.set_defaults(func=cmd_transform)

    transform_shard = subparsers.add_parser(
        "transform-shard", help="transform one modulo shard of a JSONL input list"
    )
    transform_shard.add_argument("--input-list", required=True)
    transform_shard.add_argument("--output-dir", required=True)
    transform_shard.add_argument("--shard-index", type=int, required=True)
    transform_shard.add_argument("--shards", type=int, required=True)
    transform_shard.add_argument(
        "--format", choices=["parquet", "tsv", "csv"], default="parquet"
    )
    add_external_args(transform_shard)
    transform_shard.set_defaults(func=cmd_transform_shard)

    aggregate = subparsers.add_parser(
        "aggregate", help="aggregate per-file article shards into one processed dataset"
    )
    aggregate.add_argument("--input", required=True)
    aggregate.add_argument("--output", required=True)
    add_common_stage_args(aggregate)
    aggregate.set_defaults(func=cmd_aggregate)

    download = subparsers.add_parser(
        "download", help="download PubMed baseline/updatefiles with MD5 verification"
    )
    download.add_argument(
        "--source", choices=sorted(PUBMED_BASE_URLS), default="baseline"
    )
    download.add_argument("--output-dir", default="data/raw_data/pubmed/xmls")
    download.add_argument(
        "--limit", type=int, default=None, help="debug only: first N links"
    )
    add_common_stage_args(download)
    download.set_defaults(func=cmd_download)

    scimago = subparsers.add_parser(
        "external-scimago", help="clean raw Scimago yearly CSVs"
    )
    scimago.add_argument("--input-dir", required=True)
    scimago.add_argument("--output", required=True)
    scimago.add_argument("--start-year", type=int, default=2015)
    scimago.add_argument("--end-year", type=int, default=2024)
    add_common_stage_args(scimago)
    scimago.set_defaults(func=cmd_external_scimago)

    wos = subparsers.add_parser("external-wos", help="clean raw Web of Science CSV")
    wos.add_argument("--input", required=True)
    wos.add_argument("--output", required=True)
    add_common_stage_args(wos)
    wos.set_defaults(func=cmd_external_wos)

    doaj = subparsers.add_parser("external-doaj", help="clean raw DOAJ CSV")
    doaj.add_argument("--input", required=True)
    doaj.add_argument("--output", required=True)
    add_common_stage_args(doaj)
    doaj.set_defaults(func=cmd_external_doaj)

    npi = subparsers.add_parser(
        "external-npi", help="clean raw Norwegian Publication Indicator CSV"
    )
    npi.add_argument("--input", required=True)
    npi.add_argument("--output", required=True)
    add_common_stage_args(npi)
    npi.set_defaults(func=cmd_external_npi)

    rw = subparsers.add_parser(
        "external-retraction-watch", help="clean raw Retraction Watch CSV"
    )
    rw.add_argument("--input", required=True)
    rw.add_argument("--output", required=True)
    add_common_stage_args(rw)
    rw.set_defaults(func=cmd_external_retraction_watch)

    list_inputs = subparsers.add_parser(
        "list-inputs", help="write an input file list for SLURM arrays"
    )
    list_inputs.add_argument("--input-dir", required=True)
    list_inputs.add_argument("--output", required=True)
    list_inputs.add_argument("--kind", choices=["xml", "json", "glob"], default="xml")
    list_inputs.add_argument("--glob", default="*")
    list_inputs.set_defaults(func=cmd_list_inputs)

    manifest = subparsers.add_parser("manifest", help="print recent manifest rows")
    manifest.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    manifest.add_argument("--limit", type=int, default=20)
    manifest.set_defaults(func=cmd_manifest)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
