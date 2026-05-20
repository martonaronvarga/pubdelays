from __future__ import annotations

from pathlib import Path

import polars as pl

from pubdelays.aggregate import aggregate_outputs, iter_article_paths
from pubdelays.schema import CANONICAL_ARTICLE_COLUMNS


def canonical_frame(title: str) -> pl.DataFrame:
    values = {col: [""] for col in CANONICAL_ARTICLE_COLUMNS}
    values["title"] = [title]
    return pl.DataFrame(values)


def write_shard(path: Path, title: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    canonical_frame(title).write_parquet(path)


def test_aggregation_discovers_only_article_shards_and_ignores_filter_sidecars(
    tmp_path: Path,
) -> None:
    shard = tmp_path / "articles-shard-00000-of-00001.parquet"
    sidecar = tmp_path / "articles-shard-00000-of-00001.filters.csv"
    unrelated = tmp_path / "notes.csv"
    write_shard(shard, "kept")
    sidecar.write_text("stage,count\nraw_records,1\n", encoding="utf-8")
    unrelated.write_text("title\nnot an article shard\n", encoding="utf-8")

    assert iter_article_paths(tmp_path) == [shard]

    parquet = tmp_path / "processed.parquet"
    csv = tmp_path / "processed.csv"
    rows = aggregate_outputs(tmp_path, [parquet, csv])

    assert rows == 1
    assert pl.read_parquet(parquet)["title"].to_list() == ["kept"]
    assert pl.read_csv(csv)["title"].to_list() == ["kept"]
