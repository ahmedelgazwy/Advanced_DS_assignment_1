"""Bloom filter (Bloom 1970).

A bit array of ``m`` bits and ``k`` hash functions. Adding a login sets its
``k`` bits; a lookup reports "probably taken" only if all ``k`` bits are set.
There are no false negatives. The false-positive rate after ``n`` inserts is

    p ~= (1 - exp(-k * n / m)) ** k,

which is minimized by k = (m / n) ln 2. For a target rate ``p`` this needs
m = -n ln p / (ln 2)^2 bits, about 9.6 bits per login for p = 1%.

The ``k`` bit positions come from double hashing (Kirsch & Mitzenmacher 2006):
g_i(x) = h1(x) + i * h2(x) mod m, so each login is hashed only once.

AI-assisted: generated with Claude Code (see README, "AI usage").
"""

from __future__ import annotations

import math
import sys

from login_checker.base import LoginChecker
from login_checker.hashing import hash_pair

LN2 = math.log(2)


def optimal_num_bits(capacity: int, fp_rate: float) -> int:
    """Bits needed for ``capacity`` logins at false-positive rate ``fp_rate``.

    Args:
        capacity: Expected number of logins ``n``.
        fp_rate: Target false-positive probability ``p``, in (0, 1).

    Returns:
        ``m = ceil(-n ln p / (ln 2)^2)``.
    """
    return math.ceil(-capacity * math.log(fp_rate) / LN2**2)


def optimal_num_hashes(num_bits: int, capacity: int) -> int:
    """Number of hash functions that minimizes the false-positive rate.

    Args:
        num_bits: Size of the bit array ``m``.
        capacity: Expected number of logins ``n``.

    Returns:
        ``k = round((m / n) ln 2)``, at least 1.
    """
    return max(1, round(num_bits / capacity * LN2))


class BloomFilter(LoginChecker):
    """Probabilistic login checker backed by a bit array."""

    name = "Bloom filter"
    is_probabilistic = True
    __slots__ = ("_bits", "_num_bits", "_num_hashes", "_count")

    def __init__(self, capacity: int, fp_rate: float = 0.01) -> None:
        """Size the filter for ``capacity`` logins at the target error rate.

        Args:
            capacity: Expected number of logins ``n``; must be positive.
            fp_rate: Target false-positive probability, in (0, 1).

        Returns:
            None.

        Raises:
            ValueError: If an argument is out of range.
        """
        if capacity < 1:
            raise ValueError("capacity must be positive")
        if not 0 < fp_rate < 1:
            raise ValueError("fp_rate must be in (0, 1)")
        self._num_bits = optimal_num_bits(capacity, fp_rate)
        self._num_hashes = optimal_num_hashes(self._num_bits, capacity)
        self._bits = bytearray((self._num_bits + 7) // 8)
        self._count = 0

    @property
    def num_bits(self) -> int:
        """Size of the bit array (m)."""
        return self._num_bits

    @property
    def num_hashes(self) -> int:
        """Number of hash functions (k)."""
        return self._num_hashes

    def _probe_start(self, login: str) -> tuple[int, int]:
        """First bit position and step for the login's double-hashing sequence.

        ``(h1 + i*h2) mod m`` equals ``(start + i*step) mod m`` with both
        values reduced first, which keeps the arithmetic on small integers.

        Args:
            login: Username to hash.

        Returns:
            Tuple ``(start, step)`` with ``0 <= start < m`` and ``0 < step < m``.
        """
        h1, h2 = hash_pair(login)
        return h1 % self._num_bits, h2 % self._num_bits or 1

    def add(self, login: str) -> None:
        """Set the login's ``k`` bits, O(k).

        Args:
            login: Username to store.

        Returns:
            None.
        """
        position, step = self._probe_start(login)
        bits, num_bits = self._bits, self._num_bits
        for _ in range(self._num_hashes):
            bits[position >> 3] |= 1 << (position & 7)
            position += step
            if position >= num_bits:
                position -= num_bits
        self._count += 1

    def contains(self, login: str) -> bool:
        """Test the login's ``k`` bits, stopping at the first zero bit, O(k).

        Args:
            login: Username to look up.

        Returns:
            False if the login is definitely absent; True if it is probably
            present (false positives are possible, false negatives are not).
        """
        position, step = self._probe_start(login)
        bits, num_bits = self._bits, self._num_bits
        for _ in range(self._num_hashes):
            if not bits[position >> 3] & (1 << (position & 7)):
                return False
            position += step
            if position >= num_bits:
                position -= num_bits
        return True

    def expected_fp_rate(self) -> float:
        """Theoretical false-positive rate for the logins added so far.

        Returns:
            ``(1 - exp(-k n / m)) ** k``.
        """
        k, m = self._num_hashes, self._num_bits
        return (1.0 - math.exp(-k * self._count / m)) ** k

    def memory_bytes(self) -> int:
        """Size of the bit array; logins themselves are not stored.

        Returns:
            Memory use in bytes.
        """
        return sys.getsizeof(self._bits)

    def __len__(self) -> int:
        """Return the number of ``add`` calls (duplicates cannot be detected)."""
        return self._count
