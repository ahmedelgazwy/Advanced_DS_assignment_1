"""Tests for the synthetic dataset and its generator script.

AI-assisted: generated with Claude Code (see README, "AI usage").
"""

from __future__ import annotations

import json
import re
import sys

import pytest

from login_checker.dataset import (
    ABSENT_START,
    SUFFIX_LIMIT,
    SUFFIX_WIDTH,
    encode_suffix,
    generate_absent_logins,
    generate_logins,
    load_logins,
    make_queries,
    save_logins,
)
from scripts import generate_dataset

LOGIN_PATTERN = re.compile(r"[a-z]{4,10}[0-9a-z]{7}")  # letters + base-36 suffix


def test_encode_suffix():
    assert encode_suffix(0) == "0000000"
    assert encode_suffix(35) == "000000z"
    assert encode_suffix(36) == "0000010"
    assert encode_suffix(SUFFIX_LIMIT - 1) == "zzzzzzz"
    for bad in (-1, SUFFIX_LIMIT):
        with pytest.raises(ValueError):
            encode_suffix(bad)


def test_logins_are_unique_and_well_formed():
    logins = list(generate_logins(20_000))
    assert len(set(logins)) == len(logins)
    assert all(LOGIN_PATTERN.fullmatch(login) for login in logins)


def test_suffix_encodes_the_index():
    for index, login in enumerate(generate_logins(1000)):
        assert int(login[-SUFFIX_WIDTH:], 36) == index


def test_generation_is_deterministic_and_seeded():
    assert list(generate_logins(100, seed=1)) == list(generate_logins(100, seed=1))
    assert list(generate_logins(100, seed=1)) != list(generate_logins(100, seed=2))


def test_smaller_dataset_is_a_prefix_of_a_larger_one():
    assert list(generate_logins(100)) == list(generate_logins(1000))[:100]


def test_absent_logins_never_collide_with_stored_logins():
    stored = set(generate_logins(20_000))
    absent = list(generate_absent_logins(5000))
    assert stored.isdisjoint(absent)
    assert all(int(login[-SUFFIX_WIDTH:], 36) >= ABSENT_START for login in absent)


def test_count_is_validated_eagerly():
    with pytest.raises(ValueError):
        generate_logins(-1)
    with pytest.raises(ValueError):
        generate_logins(ABSENT_START + 1)


def test_make_queries_mix_and_labels(logins, absent_logins):
    queries = make_queries(logins, absent_logins, count=1000, hit_ratio=0.3)
    stored = set(logins)
    assert len(queries) == 1000
    assert sum(is_member for _, is_member in queries) == 300
    assert all((login in stored) == is_member for login, is_member in queries)
    assert queries == make_queries(logins, absent_logins, count=1000, hit_ratio=0.3)


def test_make_queries_edge_ratios_and_errors(logins, absent_logins):
    only_hits = make_queries(logins, absent_logins, 50, hit_ratio=1.0)
    only_misses = make_queries(logins, absent_logins, 50, hit_ratio=0.0)
    assert all(is_member for _, is_member in only_hits)
    assert not any(is_member for _, is_member in only_misses)
    with pytest.raises(ValueError):
        make_queries(logins, absent_logins[:10], count=100, hit_ratio=0.5)
    with pytest.raises(ValueError):
        make_queries([], absent_logins, count=10, hit_ratio=0.5)


@pytest.mark.parametrize("file_name", ["logins.txt", "logins.txt.gz"])
def test_save_and_load_round_trip(tmp_path, file_name):
    path = tmp_path / file_name
    logins = list(generate_logins(500)) + ["josé", "用户名"]
    assert save_logins(path, logins) == len(logins)
    assert load_logins(path) == logins
    assert load_logins(path, limit=10) == logins[:10]


def test_gzip_output_is_byte_identical_across_runs(tmp_path):
    first, second = tmp_path / "a.txt.gz", tmp_path / "b.txt.gz"
    save_logins(first, generate_logins(1000))
    save_logins(second, generate_logins(1000))
    assert first.read_bytes() == second.read_bytes()


def test_generate_dataset_script_writes_files_and_manifest(tmp_path, monkeypatch):
    argv = ["generate_dataset", "--n", "300", "--absent", "50", "--out-dir", str(tmp_path)]
    monkeypatch.setattr(sys, "argv", argv)
    generate_dataset.main()
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    for file_name, checksum in manifest["sha256"].items():
        assert generate_dataset.sha256_of(tmp_path / file_name) == checksum
    assert load_logins(tmp_path / "logins_300.txt.gz") == list(generate_logins(300))
    assert len(load_logins(tmp_path / "absent_50.txt.gz")) == 50
