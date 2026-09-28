"""Tests for the benchmark and plotting scripts, including a tiny end-to-end run.

AI-assisted: generated with Claude Code (see README, "AI usage").
"""

from __future__ import annotations

import csv
import sys

import numpy as np
import pytest

from scripts import plot_results, run_benchmarks


def test_size_ladder_uses_1_2_5_steps():
    assert run_benchmarks.size_ladder(1_000, 20_000) == [1_000, 2_000, 5_000, 10_000, 20_000]
    streamed_sizes = [20_000_000, 50_000_000, 100_000_000]
    assert run_benchmarks.size_ladder(10_000_001, 100_000_000) == streamed_sizes
    assert run_benchmarks.size_ladder(5, 4) == []


def test_loglog_slope_recovers_known_exponents():
    n = np.array([1e4, 1e5, 1e6, 1e7])
    assert plot_results.loglog_slope(n, 3 * n) == pytest.approx(1.0)
    assert plot_results.loglog_slope(n, np.full(4, 2.0)) == pytest.approx(0.0, abs=1e-9)
    assert np.isnan(plot_results.loglog_slope(np.array([1e3, 2e3]), np.array([1.0, 2.0])))


def test_format_bytes():
    assert plot_results.format_bytes(1.2e9) == "1.2 GB"
    assert plot_results.format_bytes(71_000_000_000) == "71 GB"
    assert plot_results.format_bytes(512) == "512 B"


def test_benchmark_and_plot_scripts_run_end_to_end(tmp_path, monkeypatch):
    missing = str(tmp_path / "missing.txt.gz")  # forces in-memory generation
    argv = ["run_benchmarks", "--max-n", "2000", "--stream-max-n", "5000", "--tradeoff-n", "2000",
            "--repeats", "1", "--data", missing, "--absent", missing, "--out-dir", str(tmp_path)]
    monkeypatch.setattr(sys, "argv", argv)
    run_benchmarks.main()

    with open(tmp_path / "benchmark.csv", newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    stored = [row for row in rows if row["mode"] == "stored"]
    streamed = [row for row in rows if row["mode"] == "streamed"]
    assert len(stored) == 2 * 5  # n = 1000 and 2000, five structures each
    assert {row["structure"] for row in streamed} == {"Bloom filter", "Cuckoo filter"}
    assert all(float(row["lookup_us"]) > 0 for row in rows)

    monkeypatch.setattr(sys, "argv", ["plot_results", "--results", str(tmp_path)])
    plot_results.main()
    for name in ("lookup_time", "build_time", "memory", "false_positive_rate",
                 "binary_search_log", "space_accuracy_tradeoff"):
        assert (tmp_path / "figures" / f"{name}.pdf").exists()
    assert "Linear search" in (tmp_path / "summary.md").read_text(encoding="utf-8")
