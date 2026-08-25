"""Build aggregate, publication-safe evidence for a completed final run."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import polars as pl


def _read(path: Path) -> pl.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"required final-run evidence is missing: {path}")
    return pl.read_csv(path, infer_schema=False)


def _save_cohort_flow(table: pl.DataFrame, output: Path) -> None:
    import matplotlib.pyplot as plt

    stages = table["stage"].to_list()
    counts = table["count"].cast(pl.Int64, strict=False).fill_null(0).to_list()
    figure, axis = plt.subplots(figsize=(10, 6))
    axis.barh(stages[::-1], counts[::-1], color="#28536b")
    axis.set(xlabel="Articles or records retained", ylabel="Ordered checkpoint")
    axis.ticklabel_format(axis="x", style="plain")
    figure.tight_layout()
    figure.savefig(output)
    plt.close(figure)


def _save_annual_delays(table: pl.DataFrame, output: Path) -> None:
    import matplotlib.pyplot as plt

    frame = table.with_columns(
        pl.col("article_year").cast(pl.Int64),
        *[
            pl.col(column).cast(pl.Float64, strict=False)
            for column in table.columns
            if column != "article_year"
        ],
    ).sort("article_year")
    years = frame["article_year"].to_list()
    figure, axis = plt.subplots(figsize=(9, 5.5))
    for prefix, label, color in (
        ("acceptance_delay", "Receipt to acceptance", "#28536b"),
        ("publication_delay", "Acceptance to publication", "#b05a3c"),
    ):
        median = frame[f"{prefix}_median_days"].to_list()
        p25 = frame[f"{prefix}_p25_days"].to_list()
        p75 = frame[f"{prefix}_p75_days"].to_list()
        axis.plot(years, median, marker="o", label=label, color=color)
        axis.fill_between(years, p25, p75, alpha=0.18, color=color)
    axis.set(xlabel="Publication year", ylabel="Delay (days)")
    axis.legend(frameon=False)
    figure.tight_layout()
    figure.savefig(output)
    plt.close(figure)


def _save_join_coverage(table: pl.DataFrame, output: Path) -> None:
    import matplotlib.pyplot as plt

    joins = (
        table.filter(
            (pl.col("record_type") == "join")
            & (pl.col("year") == "__all__")
            & (pl.col("metric") == "matched")
        )
        .select("source", pl.col("percent").cast(pl.Float64, strict=False))
        .sort("percent")
    )
    figure, axis = plt.subplots(figsize=(8, 5))
    axis.barh(joins["source"].to_list(), joins["percent"].to_list(), color="#3d7d6e")
    axis.set(xlabel="Matched incoming articles (%)", ylabel="External source", xlim=(0, 100))
    figure.tight_layout()
    figure.savefig(output)
    plt.close(figure)


def build_evidence(run_dir: Path, output_dir: Path) -> dict[str, Path]:
    """Write aggregate JSON and vector figures without article-level material."""
    run_dir = Path(run_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    filter_counts = _read(run_dir / "filter_counts.csv")
    eligibility = _read(run_dir / "validation_tables" / "outcome_eligibility.csv")
    validation = _read(run_dir / "validation_tables" / "validation_checks.csv")
    delays = _read(run_dir / "summaries" / "delay_distribution.csv")
    joins = _read(run_dir / "quality" / "stage_and_join_debrief.csv")
    variables = _read(run_dir / "quality" / "variable_quality_debrief.csv")

    summary_path = output_dir / "run_summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "filter_counts": filter_counts.to_dicts(),
                "outcome_eligibility": eligibility.to_dicts(),
                "validation_checks": validation.to_dicts(),
                "annual_delays": delays.to_dicts(),
                "join_coverage": joins.filter(
                    (pl.col("record_type") == "join")
                    & (pl.col("year") == "__all__")
                ).to_dicts(),
                "variable_quality_overall": variables.filter(
                    pl.col("year") == "__all__"
                ).to_dicts(),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    outputs = {
        "summary": summary_path,
        "cohort_flow": output_dir / "cohort_flow.svg",
        "annual_delays": output_dir / "annual_delays.svg",
        "join_coverage": output_dir / "join_coverage.svg",
    }
    _save_cohort_flow(filter_counts, outputs["cohort_flow"])
    _save_annual_delays(delays, outputs["annual_delays"])
    _save_join_coverage(joins, outputs["join_coverage"])
    return outputs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build publication-safe final-run evidence.")
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    outputs = build_evidence(Path(args.run_dir), Path(args.output_dir))
    print(f"wrote {len(outputs)} evidence outputs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
