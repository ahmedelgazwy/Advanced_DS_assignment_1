"""Tests specific to BloomFilter.

AI-assisted: generated with Claude Code (see README, "AI usage").
"""

from __future__ import annotations

import pytest

from login_checker import BloomFilter
from login_checker.bloom_filter import optimal_num_bits, optimal_num_hashes
from login_checker.dataset import generate_absent_logins, generate_logins


def test_optimal_parameters_match_hand_computed_values():
    # m = ceil(-n ln p / ln(2)^2), k = round(m/n ln 2)
    assert optimal_num_bits(1000, 0.01) == 9586
    assert optimal_num_hashes(9586, 1000) == 7
    assert optimal_num_bits(1000, 0.001) == 14378
    assert optimal_num_hashes(14378, 1000) == 10


def test_constructor_uses_optimal_parameters():
    bloom = BloomFilter(capacity=1000, fp_rate=0.01)
    assert (bloom.num_bits, bloom.num_hashes) == (9586, 7)


@pytest.mark.parametrize("capacity, fp_rate", [(0, 0.01), (100, 0.0), (100, 1.0), (100, -0.1)])
def test_invalid_arguments_raise(capacity, fp_rate):
    with pytest.raises(ValueError):
        BloomFilter(capacity, fp_rate)


def test_expected_fp_rate_follows_the_formula():
    bloom = BloomFilter(capacity=1000, fp_rate=0.01)
    assert bloom.expected_fp_rate() == 0.0
    bloom.add_all(generate_logins(1000))
    assert bloom.expected_fp_rate() == pytest.approx(0.01, rel=0.05)


def test_measured_fp_rate_is_close_to_theory():
    bloom = BloomFilter(capacity=5000, fp_rate=0.01)
    bloom.add_all(generate_logins(5000))
    absent = list(generate_absent_logins(20_000))
    measured = sum(bloom.contains(login) for login in absent) / len(absent)
    # 20k queries at p = 1% have a standard deviation of about 0.07%
    assert measured == pytest.approx(bloom.expected_fp_rate(), abs=0.003)


def test_overfilled_filter_degrades_to_mostly_false_positives():
    bloom = BloomFilter(capacity=10, fp_rate=0.01)
    bloom.add_all(generate_logins(2000))
    assert bloom.expected_fp_rate() > 0.9
    absent = list(generate_absent_logins(500))
    assert sum(bloom.contains(login) for login in absent) > 400


def test_memory_matches_the_bit_array():
    bloom = BloomFilter(capacity=10_000, fp_rate=0.01)
    assert bloom.memory_bytes() >= bloom.num_bits // 8
    assert bloom.memory_bytes() < bloom.num_bits // 8 + 100  # only object overhead on top
