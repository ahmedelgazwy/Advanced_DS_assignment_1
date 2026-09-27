"""Hash primitives shared by the hash table, Bloom filter and cuckoo filter.

BLAKE2b from the standard library (``hashlib``) is used as the underlying
hash *function*; it is not a data-structure implementation. Unlike the
built-in ``hash()``, which is randomized per process, BLAKE2b gives the same
value on every run, so false-positive rates are reproducible.

AI-assisted: generated with Claude Code (see README, "AI usage").
"""

from __future__ import annotations

import hashlib

MASK64 = (1 << 64) - 1


def hash64(login: str) -> int:
    """Hash a login to a 64-bit integer.

    Args:
        login: Username to hash.

    Returns:
        Unsigned 64-bit hash value.
    """
    digest = hashlib.blake2b(login.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "little")


def hash_pair(login: str) -> tuple[int, int]:
    """Hash a login to two independent 64-bit integers.

    One 128-bit BLAKE2b digest is split into two halves, so the string is
    read only once. Used for double hashing (Bloom filter) and for the
    bucket/fingerprint pair (cuckoo filter).

    Args:
        login: Username to hash.

    Returns:
        Tuple ``(h1, h2)`` of unsigned 64-bit hash values.
    """
    digest = hashlib.blake2b(login.encode("utf-8"), digest_size=16).digest()
    value = int.from_bytes(digest, "little")
    return value & MASK64, value >> 64


def mix64(value: int) -> int:
    """Scramble an integer with the SplitMix64 finalizer.

    Used to hash small cuckoo-filter fingerprints so that a login's two
    candidate buckets are spread across the whole table.

    Args:
        value: Non-negative integer below 2**64.

    Returns:
        Unsigned 64-bit mixed value.
    """
    value = (value ^ (value >> 30)) * 0xBF58476D1CE4E5B9 & MASK64
    value = (value ^ (value >> 27)) * 0x94D049BB133111EB & MASK64
    return value ^ (value >> 31)
