from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
from urllib.error import URLError

import pytest

from pubdelays.cli import (
    complete_download,
    contained_download_path,
    download_file,
    expected_md5_sidecar,
    external_download_plans,
    index_links,
    main,
    md5sum,
    parse_md5_sidecar,
    verify_download_pair,
    verify_md5_file,
)


def sidecar_text(path: Path, data: bytes) -> str:
    digest = hashlib.md5(data, usedforsecurity=False).hexdigest()
    return f"MD5 ({path.name}) = {digest}\n"


def test_parse_md5_sidecar_accepts_ncbi_and_unix_formats() -> None:
    digest = "0" * 32
    assert parse_md5_sidecar(f"MD5 (pubmed.xml.gz) = {digest}\n") == (
        digest,
        "pubmed.xml.gz",
    )
    assert parse_md5_sidecar(f"{digest}  *pubmed.xml.gz\n") == (
        digest,
        "pubmed.xml.gz",
    )
    assert parse_md5_sidecar("bad") is None


def test_verify_download_pair_requires_matching_sidecar(tmp_path: Path) -> None:
    data = b"pubmed"
    target = tmp_path / "pubmed.xml.gz"
    target.write_bytes(data)
    expected_md5_sidecar(target).write_text(sidecar_text(target, data), encoding="utf-8")

    assert md5sum(target) == hashlib.md5(data, usedforsecurity=False).hexdigest()
    assert verify_md5_file(expected_md5_sidecar(target))
    assert verify_download_pair(target)
    assert complete_download(target)


def test_verify_download_pair_rejects_missing_and_mismatched_sidecars(tmp_path: Path) -> None:
    target = tmp_path / "pubmed.xml.gz"
    target.write_bytes(b"actual")

    assert not verify_download_pair(target)

    expected_md5_sidecar(target).write_text(
        "MD5 (pubmed.xml.gz) = 00000000000000000000000000000000\n",
        encoding="utf-8",
    )
    assert not verify_download_pair(target)


def test_download_resume_skips_only_complete_verified_data(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    target = tmp_path / "pubmed.xml.gz"
    target.write_bytes(b"corrupt partial")
    calls = 0

    class Response:
        def __enter__(self) -> Response:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self, _size: int) -> bytes:
            nonlocal calls
            calls += 1
            return b"fresh" if calls == 1 else b""

    monkeypatch.setattr("urllib.request.urlopen", lambda *_args, **_kwargs: Response())

    stats = download_file("https://example.test/pubmed.xml.gz", target, resume=True, retries=1)

    assert stats.downloaded
    assert target.read_bytes() == b"fresh"


def test_download_resume_skips_existing_md5_sidecar(tmp_path: Path) -> None:
    sidecar = tmp_path / "pubmed.xml.gz.md5"
    sidecar.write_text("present", encoding="utf-8")

    stats = download_file("https://example.test/pubmed.xml.gz.md5", sidecar, resume=True, retries=1)

    assert stats.skipped
    assert not stats.downloaded


def test_download_failure_leaves_previous_file_intact(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    target = tmp_path / "pubmed.xml.gz"
    target.write_bytes(b"previous")

    def fail(*_args: object, **_kwargs: object) -> object:
        raise URLError("offline")

    monkeypatch.setattr("urllib.request.urlopen", fail)

    with pytest.raises(RuntimeError):
        download_file("https://example.test/pubmed.xml.gz", target, resume=False, retries=1)
    assert target.read_bytes() == b"previous"


def test_download_index_links_ignores_path_like_hrefs(monkeypatch: pytest.MonkeyPatch) -> None:
    class Response:
        def __enter__(self) -> Response:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self) -> bytes:
            return b'''
<a href="pubmed25n0001.xml.gz">ok</a>
<a href="pubmed25n0001.xml.gz.md5">ok</a>
<a href="../escaped.xml.gz">bad</a>
<a href="nested/escaped.xml.gz">bad</a>
<a href="/tmp/escaped.xml.gz">bad</a>
'''

    monkeypatch.setattr("urllib.request.urlopen", lambda *_args, **_kwargs: Response())

    assert index_links("https://example.test/") == ["pubmed25n0001.xml.gz", "pubmed25n0001.xml.gz.md5"]


def test_download_path_rejects_links_outside_output_dir(tmp_path: Path) -> None:
    assert contained_download_path(tmp_path, "pubmed25n0001.xml.gz") == tmp_path / "pubmed25n0001.xml.gz"

    with pytest.raises(ValueError):
        contained_download_path(tmp_path, "../escaped.xml.gz")
    with pytest.raises(ValueError):
        contained_download_path(tmp_path, "/tmp/escaped.xml.gz")


def test_external_download_plans_use_configured_public_urls(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
[pipeline]
manifest = "data/manifests/pipeline.sqlite"
parse_inputs = "data/manifests/parse_inputs.txt"
transform_inputs = "data/manifests/transform_inputs.txt"
[pubmed]
xml_dir = "data/raw_data/pubmed/xmls"
jsonl_dir = "data/temp_data/pubmed/jsonl"
[external.raw]
scimago_dir = "data/raw_data/scimago"
web_of_science_csv = "data/raw_data/web_of_science/wos.csv"
doaj_csv = "data/raw_data/directory_of_open_access_journals/doaj.csv"
norwegian_list_csv = "data/raw_data/norwegian_publication_indicator/npi.csv"
retraction_watch_csv = "data/raw_data/retraction_watch/retraction_watch.csv"
publisher_csv = "data/raw_data/publisher_metadata/publishers.csv"
[external.download]
doaj_url = "https://example.test/doaj.csv"
retraction_watch_url = "https://example.test/rw.csv"
scimago_url_template = "https://example.test/scimagojr-{year}.csv"
publisher_url = "https://example.test/publishers.csv"
[external.processed]
scimago = "data/processed_data/scimago.csv"
web_of_science = "data/processed_data/web_of_science.csv"
doaj = "data/processed_data/doaj.csv"
norwegian_list = "data/processed_data/norwegian_list.csv"
retraction_watch = "data/processed_data/retraction_watch.csv"
publisher = "data/processed_data/publisher_metadata.csv"
pubmed_journals = "data/external/pubmed-journals.csv"
[transform]
article_shard_dir = "data/temp_data/article_parquet"
article_shard_format = "parquet"
min_received = "2013-01-01"
default_shards = 64
[aggregate]
processed_parquet = "data/processed_data/processed.parquet"
processed_csv = "data/processed_data/processed.csv"
summary_dir = "data/processed_data/summaries"
""".strip(),
        encoding="utf-8",
    )
    args = argparse.Namespace(config=config_path, source="all", start_year=2023, end_year=2024)

    plans = external_download_plans(args)

    assert [plan.source for plan in plans] == ["doaj", "retraction-watch", "scimago", "scimago", "publisher"]
    assert plans[0].url == "https://example.test/doaj.csv"
    assert plans[1].output_path == tmp_path / "data/raw_data/retraction_watch/retraction_watch.csv"
    assert plans[2].url == "https://example.test/scimagojr-2023.csv"
    assert plans[4].output_path == tmp_path / "data/raw_data/publisher_metadata/publishers.csv"


def test_external_download_all_skips_optional_unconfigured_sources(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
[pipeline]
manifest = "data/manifests/pipeline.sqlite"
parse_inputs = "data/manifests/parse_inputs.txt"
transform_inputs = "data/manifests/transform_inputs.txt"
[pubmed]
xml_dir = "data/raw_data/pubmed/xmls"
jsonl_dir = "data/temp_data/pubmed/jsonl"
[external.raw]
scimago_dir = "data/raw_data/scimago"
web_of_science_csv = "data/raw_data/web_of_science/wos.csv"
doaj_csv = "data/raw_data/directory_of_open_access_journals/doaj.csv"
norwegian_list_csv = "data/raw_data/norwegian_publication_indicator/npi.csv"
retraction_watch_csv = "data/raw_data/retraction_watch/retraction_watch.csv"
publisher_csv = "data/raw_data/publisher_metadata/publishers.csv"
[external.download]
doaj_url = "https://example.test/doaj.csv"
retraction_watch_url = "https://example.test/rw.csv"
[external.processed]
scimago = "data/processed_data/scimago.csv"
web_of_science = "data/processed_data/web_of_science.csv"
doaj = "data/processed_data/doaj.csv"
norwegian_list = "data/processed_data/norwegian_list.csv"
retraction_watch = "data/processed_data/retraction_watch.csv"
publisher = "data/processed_data/publisher_metadata.csv"
pubmed_journals = "data/external/pubmed-journals.csv"
[transform]
article_shard_dir = "data/temp_data/article_parquet"
article_shard_format = "parquet"
min_received = "2013-01-01"
default_shards = 64
[aggregate]
processed_parquet = "data/processed_data/processed.parquet"
processed_csv = "data/processed_data/processed.csv"
summary_dir = "data/processed_data/summaries"
""".strip(),
        encoding="utf-8",
    )
    args = argparse.Namespace(config=config_path, source="all", start_year=2023, end_year=2024)

    plans = external_download_plans(args)

    assert [plan.source for plan in plans] == ["doaj", "retraction-watch"]


def test_download_external_dry_run_reports_configured_targets(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
[pipeline]
manifest = "data/manifests/pipeline.sqlite"
parse_inputs = "data/manifests/parse_inputs.txt"
transform_inputs = "data/manifests/transform_inputs.txt"
[pubmed]
xml_dir = "data/raw_data/pubmed/xmls"
jsonl_dir = "data/temp_data/pubmed/jsonl"
[external.raw]
scimago_dir = "data/raw_data/scimago"
web_of_science_csv = "data/raw_data/web_of_science/wos.csv"
doaj_csv = "data/raw_data/directory_of_open_access_journals/doaj.csv"
norwegian_list_csv = "data/raw_data/norwegian_publication_indicator/npi.csv"
retraction_watch_csv = "data/raw_data/retraction_watch/retraction_watch.csv"
publisher_csv = "data/raw_data/publisher_metadata/publishers.csv"
[external.download]
doaj_url = "https://example.test/doaj.csv"
[external.processed]
scimago = "data/processed_data/scimago.csv"
web_of_science = "data/processed_data/web_of_science.csv"
doaj = "data/processed_data/doaj.csv"
norwegian_list = "data/processed_data/norwegian_list.csv"
retraction_watch = "data/processed_data/retraction_watch.csv"
publisher = "data/processed_data/publisher_metadata.csv"
pubmed_journals = "data/external/pubmed-journals.csv"
[transform]
article_shard_dir = "data/temp_data/article_parquet"
article_shard_format = "parquet"
min_received = "2013-01-01"
default_shards = 64
[aggregate]
processed_parquet = "data/processed_data/processed.parquet"
processed_csv = "data/processed_data/processed.csv"
summary_dir = "data/processed_data/summaries"
""".strip(),
        encoding="utf-8",
    )

    assert main(["--config", str(config_path), "download-external", "--source", "doaj", "--dry-run"]) == 0
    captured = capsys.readouterr()
    assert "https://example.test/doaj.csv" in captured.out
    assert "data/raw_data/directory_of_open_access_journals/doaj.csv" in captured.out
