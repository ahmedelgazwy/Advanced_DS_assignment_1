"""Tests for the hash helpers.

AI-assisted: generated with Claude Code (see README, "AI usage").
"""

from __future__ import annotations

import hashlib

from login_checker.hashing import MASK64, hash64, hash_pair, mix64


def test_hash64_matches_blake2b_and_is_deterministic():
    expected = int.from_bytes(hashlib.blake2b(b"alice", digest_size=8).digest(), "little")
    assert hash64("alice") == expected
    assert hash64("alice") == hash64("alice")


def test_hash_pair_splits_one_128_bit_digest():
    digest = int.from_bytes(hashlib.blake2b(b"alice", digest_size=16).digest(), "little")
    assert hash_pair("alice") == (digest & MASK64, digest >> 64)


def test_hashes_are_64_bit_and_distinct(logins):
    values = [hash64(login) for login in logins]
    assert all(0 <= value <= MASK64 for value in values)
    assert len(set(values)) == len(logins)
    for login in logins[:100]:
        h1, h2 = hash_pair(login)
        assert 0 <= h1 <= MASK64 and 0 <= h2 <= MASK64 and h1 != h2


def test_unicode_logins_hash_without_errors():
    assert hash64("用户名") != hash64("josé")


def test_hash64_spreads_logins_evenly(logins):
    """Every one of 16 buckets should get close to its fair share."""
    counts = [0] * 16
    for login in logins:
        counts[hash64(login) % 16] += 1
    fair_share = len(logins) / 16
    assert all(0.7 * fair_share < count < 1.3 * fair_share for count in counts)


def test_mix64_is_injective_on_small_inputs():
    outputs = [mix64(value) for value in range(10_000)]
    assert len(set(outputs)) == len(outputs)
    assert all(0 <= value <= MASK64 for value in outputs)
