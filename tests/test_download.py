from __future__ import annotations

import hashlib
from pathlib import Path
from urllib.error import URLError

import pytest

from pubdelays.cli import (
    complete_download,
    download_file,
    expected_md5_sidecar,
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
