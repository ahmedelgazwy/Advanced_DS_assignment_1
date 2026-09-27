"""Tests specific to CuckooFilter.

AI-assisted: generated with Claude Code (see README, "AI usage").
"""

from __future__ import annotations

import math
import random

import pytest

from login_checker import CuckooFilter, CuckooFilterFullError
from login_checker.cuckoo_filter import fingerprint_bits_for
from login_checker.dataset import generate_absent_logins, generate_logins


def fill_until_full(cuckoo: CuckooFilter, limit: int) -> list[str]:
    """Add fresh logins until the filter reports it is full.

    Args:
        cuckoo: Filter to fill.
        limit: Maximum number of logins to try.

    Returns:
        The logins that were added successfully.
    """
    stored = []
    for login in generate_logins(limit):
        try:
            cuckoo.add(login)
        except CuckooFilterFullError:
            break
        stored.append(login)
    return stored


def test_fingerprint_bits_formula():
    # f = ceil(log2(2b / eps))
    assert fingerprint_bits_for(0.01, 4) == 10
    assert fingerprint_bits_for(0.03, 4) == 9
    assert fingerprint_bits_for(0.05, 4) == 8


def test_table_is_sized_for_the_planned_load():
    cuckoo = CuckooFilter(capacity=1000, bucket_size=4, max_load=0.9)
    assert cuckoo.num_buckets == math.ceil(1000 / (4 * 0.9))
    assert cuckoo.fingerprint_bits == 10


@pytest.mark.parametrize(
    "kwargs",
    [{"capacity": 0}, {"fp_rate": 0.0}, {"fp_rate": 1e-6}, {"max_load": 0.0}, {"bucket_size": 0}],
)
def test_invalid_arguments_raise(kwargs):
    with pytest.raises(ValueError):
        CuckooFilter(**{"capacity": 100, **kwargs})


def test_alternate_bucket_is_an_involution():
    cuckoo = CuckooFilter(capacity=10_000)
    rng = random.Random(0)
    for _ in range(2000):
        index = rng.randrange(cuckoo.num_buckets)
        fingerprint = rng.randint(1, 2**cuckoo.fingerprint_bits - 1)
        alt_index = cuckoo._alt_index(index, fingerprint)
        assert 0 <= alt_index < cuckoo.num_buckets
        assert cuckoo._alt_index(alt_index, fingerprint) == index


def test_fingerprints_are_never_zero_and_fit_in_f_bits(logins):
    cuckoo = CuckooFilter(capacity=len(logins))
    for login in logins:
        fingerprint, index = cuckoo._locate(login)
        assert 1 <= fingerprint < 2**cuckoo.fingerprint_bits
        assert 0 <= index < cuckoo.num_buckets


def test_measured_fp_rate_respects_the_bound():
    cuckoo = CuckooFilter(capacity=5000, fp_rate=0.01)
    cuckoo.add_all(generate_logins(5000))
    absent = list(generate_absent_logins(20_000))
    measured = sum(cuckoo.contains(login) for login in absent) / len(absent)
    # Bound 2b/2^f = 0.78%; the margin absorbs sampling noise of 20k queries.
    assert measured <= 1.25 * cuckoo.expected_fp_rate()


def test_remove(logins):
    cuckoo = CuckooFilter(capacity=len(logins))
    cuckoo.add_all(logins)
    for login in logins[:1000]:
        assert cuckoo.remove(login) is True
    assert len(cuckoo) == len(logins) - 1000
    assert all(cuckoo.contains(login) for login in logins[1000:])
    assert cuckoo.remove("never-added") is False


def test_full_filter_raises_but_loses_nothing():
    cuckoo = CuckooFilter(capacity=200, max_load=1.0)
    stored = fill_until_full(cuckoo, limit=1000)
    assert cuckoo.is_full
    assert cuckoo.load_factor > 0.85  # 4-slot buckets fill to ~95% (Fan et al.)
    assert all(cuckoo.contains(login) for login in stored)  # includes the victim
    with pytest.raises(CuckooFilterFullError):
        cuckoo.add("one-too-many")


def test_remove_on_a_full_filter_reinserts_the_victim():
    cuckoo = CuckooFilter(capacity=200, max_load=1.0)
    stored = fill_until_full(cuckoo, limit=1000)
    for login in stored[:20]:
        assert cuckoo.remove(login)
    assert not cuckoo.is_full
    assert all(cuckoo.contains(login) for login in stored[20:])
    cuckoo.add("fits-again")
    assert cuckoo.contains("fits-again")


def test_repeated_duplicates_eventually_fill_their_buckets():
    """A login's fingerprint has only 2 buckets, so at most 2b copies fit."""
    cuckoo = CuckooFilter(capacity=1000, bucket_size=4)
    with pytest.raises(CuckooFilterFullError):
        for _ in range(2 * cuckoo.bucket_size + 2):
            cuckoo.add("alice")


def test_short_fingerprints_use_one_byte_slots():
    one_byte = CuckooFilter(capacity=10_000, fp_rate=0.05)  # f = 8
    two_byte = CuckooFilter(capacity=10_000, fp_rate=0.01)  # f = 10
    assert one_byte.fingerprint_bits == 8
    assert one_byte.memory_bytes() < two_byte.memory_bytes()


def test_load_factor_counts_stored_logins(logins):
    cuckoo = CuckooFilter(capacity=len(logins), max_load=0.9)
    cuckoo.add_all(logins)
    assert cuckoo.load_factor == pytest.approx(0.9, abs=0.01)
    assert cuckoo.expected_fp_rate() == 2 * 4 / 2**10
