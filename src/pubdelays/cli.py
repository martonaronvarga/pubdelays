"""Command-line entrypoint for the PubMed/MEDLINE pipeline."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
import tempfile
import urllib.request
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .parser.medline import parse_medline_xml
from .transform import ExternalInputs, transform_files

PUBMED_BASE_URLS = {
    "baseline": "https://ftp.ncbi.nlm.nih.gov/pubmed/baseline/",
    "updatefiles": "https://ftp.ncbi.nlm.nih.gov/pubmed/updatefiles/",
}


@dataclass(frozen=True)
class ParseStats:
    input_path: str
    output_path: str
    records: int
    deleted: int
    skipped: bool = False


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


def output_path_for(input_path: Path, output_dir: Path, fmt: str) -> Path:
    extension = "jsonl" if fmt == "jsonl" else "json"
    return output_dir / f"{input_path.name}.{extension}"


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
) -> ParseStats:
    input_path = Path(input_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if resume and output_path.exists() and output_path.stat().st_size > 0:
        return ParseStats(str(input_path), str(output_path), 0, 0, skipped=True)

    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{output_path.name}.", suffix=".tmp", dir=str(output_path.parent)
    )
    os.close(fd)
    tmp_path = Path(tmp_name)

    records = 0
    deleted = 0
    try:
        iterator = parse_medline_xml(
            input_path,
            year_info_only=year_info_only,
            nlm_category=nlm_category,
            author_list=author_list,
            reference_list=reference_list,
            parse_downto_mesh_subterms=parse_mesh_subterms,
            min_pub_year=min_pub_year,
        )

        if fmt == "jsonl":
            with tmp_path.open("w", encoding="utf-8") as handle:
                for record in iterator:
                    records += 1
                    if record.get("delete"):
                        deleted += 1
                    handle.write(
                        json.dumps(record, ensure_ascii=False, separators=(",", ":"))
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

        tmp_path.replace(output_path)
        return ParseStats(str(input_path), str(output_path), records, deleted)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise


def cmd_parse(args: argparse.Namespace) -> int:
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    xml_paths = list_xml_paths(input_dir)
    if not xml_paths:
        print(f"No XML files found in {input_dir}", file=sys.stderr)
        return 1

    jobs = args.jobs if args.jobs is not None else max((os.cpu_count() or 2) - 1, 1)
    kwargs = {
        "fmt": args.format,
        "resume": args.resume,
        "year_info_only": args.year_info_only,
        "nlm_category": args.nlm_category,
        "author_list": args.author_list,
        "reference_list": args.reference_list,
        "parse_mesh_subterms": args.parse_mesh_subterms,
        "min_pub_year": args.min_pub_year,
    }

    manifest_path = output_dir / "parse_manifest.csv"
    output_dir.mkdir(parents=True, exist_ok=True)
    write_header = not manifest_path.exists()

    total_records = 0
    total_deleted = 0
    skipped = 0

    with manifest_path.open("a", newline="", encoding="utf-8") as manifest_handle:
        writer = csv.DictWriter(
            manifest_handle,
            fieldnames=["input_path", "output_path", "records", "deleted", "skipped"],
        )
        if write_header:
            writer.writeheader()

        if jobs == 1:
            stats_iter = (
                parse_one(
                    path, output_path_for(path, output_dir, args.format), **kwargs
                )
                for path in xml_paths
            )
            for stats in stats_iter:
                writer.writerow(stats.__dict__)
                total_records += stats.records
                total_deleted += stats.deleted
                skipped += int(stats.skipped)
                print(
                    f"parsed {stats.input_path} -> {stats.output_path} ({stats.records} records)"
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
                    writer.writerow(stats.__dict__)
                    manifest_handle.flush()
                    total_records += stats.records
                    total_deleted += stats.deleted
                    skipped += int(stats.skipped)
                    status = "skipped" if stats.skipped else "parsed"
                    print(
                        f"{status} {stats.input_path} -> {stats.output_path} ({stats.records} records)"
                    )

    print(
        f"Done: files={len(xml_paths)}, skipped={skipped}, records={total_records}, deleted={total_deleted}"
    )
    return 0


def validate_json_file(path: Path) -> tuple[bool, int]:
    count = 0
    try:
        if path.suffix == ".jsonl":
            with path.open("r", encoding="utf-8") as handle:
                for line_number, line in enumerate(handle, start=1):
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
        print(f"INVALID {path}: {exc}", file=sys.stderr)
        return False, count


def cmd_validate(args: argparse.Namespace) -> int:
    paths: list[Path]
    input_path = Path(args.input)
    if input_path.is_dir():
        paths = sorted(
            list(input_path.rglob("*.json")) + list(input_path.rglob("*.jsonl"))
        )
    else:
        paths = [input_path]

    failures = 0
    total_records = 0
    for path in paths:
        ok, count = validate_json_file(path)
        total_records += count
        if ok:
            print(f"OK {path}: {count} records")
        else:
            failures += 1
    print(f"Validated {len(paths)} files, records={total_records}, failures={failures}")
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
    url = args.url
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    with urllib.request.urlopen(url) as response:
        text = response.read().decode("utf-8")

    rows = parse_j_medline(text)
    with output.open("w", newline="", encoding="utf-8") as handle:
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

    print(f"Wrote {len(rows)} journal rows to {output}")
    return 0


def index_links(url: str) -> list[str]:
    with urllib.request.urlopen(url) as response:
        html = response.read().decode("utf-8", errors="replace")
    return sorted(set(re.findall(r'href="([^"]+\.(?:gz|md5))"', html)))


def download_file(url: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_path.with_name(f".{output_path.name}.tmp")
    with urllib.request.urlopen(url) as response, tmp_path.open("wb") as handle:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            handle.write(chunk)
    tmp_path.replace(output_path)


def md5sum(path: Path) -> str:
    digest = hashlib.md5()  # nosec: used only to verify NCBI-provided MD5 sidecar files
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_md5_sidecar(content: str) -> tuple[str, str] | None:
    """Parse common PubMed/Unix MD5 sidecar formats.

    Accepted examples:
    - ``d41d8cd98f00b204e9800998ecf8427e  pubmed25n0001.xml.gz``
    - ``MD5 (pubmed25n0001.xml.gz) = d41d8cd98f00b204e9800998ecf8427e``
    """
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
    base_url = PUBMED_BASE_URLS[args.source]
    output_dir = Path(args.output_dir)
    links = index_links(base_url)
    if args.limit is not None:
        links = links[: args.limit]

    for link in links:
        target = output_dir / link
        if args.resume and target.exists() and target.stat().st_size > 0:
            print(f"skip {target}")
            continue
        print(f"download {base_url}{link} -> {target}")
        download_file(base_url + link, target)

    failures = []
    for md5_path in sorted(output_dir.glob("*.md5")):
        if not verify_md5_file(md5_path):
            failures.append(str(md5_path))

    if failures:
        print("MD5 failures:", file=sys.stderr)
        for failure in failures:
            print(f"  {failure}", file=sys.stderr)
        return 1

    print(f"Downloaded {len(links)} files into {output_dir}; MD5 checks passed")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pubdelays-pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    parse = subparsers.add_parser(
        "parse", help="parse MEDLINE XML/XML.GZ files to JSONL or JSON"
    )
    parse.add_argument("--input-dir", required=True)
    parse.add_argument("--output-dir", required=True)
    parse.add_argument("--jobs", type=int, default=None)
    parse.add_argument("--format", choices=["jsonl", "json"], default="jsonl")
    parse.add_argument("--resume", action="store_true")
    parse.add_argument("--year-info-only", action="store_true")
    parse.add_argument("--nlm-category", action="store_true")
    parse.add_argument("--author-list", action="store_true")
    parse.add_argument("--reference-list", action="store_true")
    parse.add_argument("--parse-mesh-subterms", action="store_true")
    parse.add_argument("--min-pub-year", type=int, default=None)
    parse.set_defaults(func=cmd_parse)

    validate = subparsers.add_parser("validate", help="validate JSON or JSONL outputs")
    validate.add_argument("input")
    validate.set_defaults(func=cmd_validate)

    journals = subparsers.add_parser(
        "journals", help="download and parse NLM J_Medline.txt"
    )
    journals.add_argument(
        "--url", default="https://ftp.ncbi.nlm.nih.gov/pubmed/J_Medline.txt"
    )
    journals.add_argument("--output", required=True)
    journals.set_defaults(func=cmd_journals)

    transform = subparsers.add_parser(
        "transform", help="transform parsed JSONL/JSON records into the analysis TSV"
    )
    transform.add_argument(
        "--input", required=True, help="parsed JSONL/JSON file or directory"
    )
    transform.add_argument("--output", required=True, help="output TSV path")
    transform.add_argument(
        "--filters-output", default=None, help="optional filter-count CSV path"
    )
    transform.add_argument("--scimago", default=None, help="optional Scimago CSV path")
    transform.add_argument(
        "--web-of-science", default=None, help="optional Web of Science CSV path"
    )
    transform.add_argument("--doaj", default=None, help="optional DOAJ CSV path")
    transform.add_argument(
        "--norwegian-list", default=None, help="optional Norwegian Register CSV path"
    )
    transform.add_argument(
        "--retraction-watch", default=None, help="optional Retraction Watch CSV path"
    )
    transform.set_defaults(func=_cmd_transform)

    download = subparsers.add_parser(
        "download", help="download PubMed baseline or updatefiles with MD5 verification"
    )
    download.add_argument(
        "--source", choices=sorted(PUBMED_BASE_URLS), default="baseline"
    )
    download.add_argument("--output-dir", required=True)
    download.add_argument("--resume", action="store_true")
    download.add_argument(
        "--limit",
        type=int,
        default=None,
        help="debug/test only: download first N links",
    )
    download.set_defaults(func=cmd_download)

    return parser


def _optional_path(value: str | None) -> Path | None:
    return Path(value) if value else None


def _cmd_transform(args: argparse.Namespace) -> int:
    result = transform_files(
        Path(args.input),
        Path(args.output),
        filters_path=_optional_path(args.filters_output),
        external=ExternalInputs(
            scimago=_optional_path(args.scimago),
            web_of_science=_optional_path(args.web_of_science),
            doaj=_optional_path(args.doaj),
            norwegian_list=_optional_path(args.norwegian_list),
            retraction_watch=_optional_path(args.retraction_watch),
        ),
    )
    print(f"Wrote transformed articles to {result.output_path}")
    if result.filters_path is not None:
        print(f"Wrote filter counts to {result.filters_path}")
    for stage, count in result.counts.items():
        print(f"{stage}: {count}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
