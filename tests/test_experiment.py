"""Tests for the shared measurement helpers and an end-to-end demo run.

AI-assisted: generated with Claude Code (see README, "AI usage").
"""

from __future__ import annotations

import gc
import sys

import demo
from login_checker import BloomFilter, HashTable, LinearSearchChecker
from login_checker.experiment import (
    checker_factories,
    false_positive_rate,
    format_table,
    gc_paused,
    mean_lookup_seconds,
    timed_build,
)


def test_checker_factories_build_the_five_structures_in_order():
    factories = checker_factories(capacity=100)
    names = ["Linear search", "Binary search", "Hash table", "Bloom filter", "Cuckoo filter"]
    assert list(factories) == names
    assert [factory().name for factory in factories.values()] == names


def test_timed_build_returns_a_loaded_checker(logins):
    checker, seconds = timed_build(HashTable, logins)
    assert len(checker) == len(logins)
    assert seconds > 0


def test_mean_lookup_seconds_is_positive(logins):
    checker, _ = timed_build(LinearSearchChecker, logins[:100])
    assert mean_lookup_seconds(checker, logins[:10]) > 0


def test_false_positive_rate(logins, absent_logins):
    exact, _ = timed_build(HashTable, logins)
    assert false_positive_rate(exact, absent_logins) == 0.0
    overfilled, _ = timed_build(lambda: BloomFilter(capacity=10), logins)
    assert false_positive_rate(overfilled, absent_logins) > 0.9


def test_gc_paused_restores_the_previous_state():
    assert gc.isenabled()
    with gc_paused():
        assert not gc.isenabled()
    assert gc.isenabled()


def test_format_table_aligns_columns():
    table = format_table(["Name", "Value"], [["a", 1], ["long name", 22]])
    lines = table.splitlines()
    assert lines[0] == "Name       Value"
    assert lines[1] == "---------  -----"
    assert lines[3] == "long name  22"
    assert all(line == line.rstrip() for line in lines)


def test_demo_runs_end_to_end(monkeypatch, capsys, tmp_path):
    argv = ["demo.py", "--n", "2000", "--data", str(tmp_path / "missing.txt.gz")]
    monkeypatch.setattr(sys, "argv", argv)
    demo.main()
    output = capsys.readouterr().out
    assert "generated in memory" in output
    for section in ("1. Building", "2. Is this login taken?", "3. Sign-up", "4. Deleting"):
        assert section in output
    assert "reserved" in output and "rejected" in output
