"""Cuckoo filter (Fan, Andersen, Kaminsky & Mitzenmacher, CoNEXT 2014).

A table of ``B`` buckets with ``b`` slots each. Every slot holds an ``f``-bit
fingerprint of a login (0 marks an empty slot). Each login has two candidate
buckets (partial-key cuckoo hashing):

    i1 = h(x) mod B,        i2 = alt(i1, fp) = (H(fp) - i1) mod B.

``alt`` is its own inverse (``alt(alt(i)) = i``), so a fingerprint can be
moved to its other bucket without knowing the original login. The paper uses
``i1 XOR H(fp)``, which needs ``B`` to be a power of two; subtraction works
for any ``B``, so the table is sized exactly instead of being rounded up.

* Lookup and delete check two buckets: O(b) = O(1).
* Insert places the fingerprint in a free slot of either bucket; if both are
  full it evicts a random fingerprint and moves it to its alternate bucket,
  up to ``max_kicks`` times.
* False-positive rate: at most 2b / 2^f.

If an insert runs out of kicks, the last evicted fingerprint is parked in a
one-entry "victim" stash (as in the authors' reference implementation) so no
stored login is lost; the next insert then raises
:class:`CuckooFilterFullError`.

AI-assisted: generated with Claude Code (see README, "AI usage").
"""

from __future__ import annotations

import math
import random
import sys
from array import array

from login_checker.base import LoginChecker
from login_checker.hashing import hash_pair, mix64

MAX_FINGERPRINT_BITS = 16


class CuckooFilterFullError(Exception):
    """Raised when the cuckoo filter cannot store another login."""


def fingerprint_bits_for(fp_rate: float, bucket_size: int) -> int:
    """Smallest fingerprint length that meets a false-positive target.

    From ``fp_rate <= 2b / 2^f``: ``f = ceil(log2(2b / fp_rate))``.

    Args:
        fp_rate: Target false-positive probability, in (0, 1).
        bucket_size: Slots per bucket ``b``.

    Returns:
        Fingerprint length ``f`` in bits.
    """
    return math.ceil(math.log2(2 * bucket_size / fp_rate))


class CuckooFilter(LoginChecker):
    """Probabilistic login checker that stores short fingerprints."""

    name = "Cuckoo filter"
    is_probabilistic = True
    __slots__ = (
        "_table", "_num_buckets", "_bucket_size", "_fingerprint_bits",
        "_fingerprint_mask", "_alt_offsets", "_max_kicks", "_count", "_victim", "_rng",
    )

    def __init__(
        self,
        capacity: int,
        fp_rate: float = 0.01,
        bucket_size: int = 4,
        max_load: float = 0.9,
        max_kicks: int = 500,
        seed: int = 0,
    ) -> None:
        """Size the filter for ``capacity`` logins at the target error rate.

        Args:
            capacity: Expected number of logins ``n``; must be positive.
            fp_rate: Target false-positive probability; sets ``f``.
            bucket_size: Slots per bucket ``b`` (the paper recommends 4).
            max_load: Planned fraction of occupied slots; the table gets
                ``ceil(n / (b * max_load))`` buckets.
            max_kicks: Evictions tried before an insert gives up.
            seed: Seed for the random choices made during eviction.

        Returns:
            None.

        Raises:
            ValueError: If an argument is out of range, or ``fp_rate`` needs
                fingerprints longer than 16 bits.
        """
        if capacity < 1 or bucket_size < 1 or max_kicks < 0:
            raise ValueError("capacity and bucket_size must be positive, max_kicks >= 0")
        if not 0 < fp_rate < 1 or not 0 < max_load <= 1:
            raise ValueError("fp_rate must be in (0, 1) and max_load in (0, 1]")
        self._fingerprint_bits = max(1, fingerprint_bits_for(fp_rate, bucket_size))
        if self._fingerprint_bits > MAX_FINGERPRINT_BITS:
            raise ValueError(f"fp_rate too small: needs more than {MAX_FINGERPRINT_BITS}-bit fingerprints")
        self._fingerprint_mask = (1 << self._fingerprint_bits) - 1
        self._bucket_size = bucket_size
        self._num_buckets = math.ceil(capacity / (bucket_size * max_load))
        typecode = "B" if self._fingerprint_bits <= 8 else "H"
        self._table = array(typecode, [0]) * (self._num_buckets * bucket_size)
        # H(fp) mod B for every possible fingerprint, precomputed once.
        self._alt_offsets = array(
            "L", (mix64(fp) % self._num_buckets for fp in range(self._fingerprint_mask + 1))
        )
        self._max_kicks = max_kicks
        self._count = 0
        self._victim: tuple[int, int] | None = None
        self._rng = random.Random(seed)

    @property
    def num_buckets(self) -> int:
        """Number of buckets (B)."""
        return self._num_buckets

    @property
    def bucket_size(self) -> int:
        """Slots per bucket (b)."""
        return self._bucket_size

    @property
    def fingerprint_bits(self) -> int:
        """Fingerprint length in bits (f)."""
        return self._fingerprint_bits

    @property
    def load_factor(self) -> float:
        """Fraction of slots in use (alpha)."""
        return self._count / (self._num_buckets * self._bucket_size)

    @property
    def is_full(self) -> bool:
        """True once an insert has failed; further inserts will raise."""
        return self._victim is not None

    def expected_fp_rate(self) -> float:
        """Upper bound on the false-positive rate, ``2b / 2^f``.

        Returns:
            The bound as a probability.
        """
        return 2 * self._bucket_size / 2**self._fingerprint_bits

    def _locate(self, login: str) -> tuple[int, int]:
        """Compute a login's fingerprint and primary bucket.

        Args:
            login: Username to hash.

        Returns:
            Tuple ``(fingerprint, i1)``; the fingerprint is never 0, because
            0 marks an empty slot.
        """
        h1, h2 = hash_pair(login)
        return (h2 & self._fingerprint_mask) or 1, h1 % self._num_buckets

    def _alt_index(self, index: int, fingerprint: int) -> int:
        """The other candidate bucket of a fingerprint stored in ``index``.

        Args:
            index: One of the fingerprint's two buckets.
            fingerprint: The stored fingerprint.

        Returns:
            ``(H(fp) - index) mod B``; applying it twice returns ``index``.
        """
        return (self._alt_offsets[fingerprint] - index) % self._num_buckets

    def _bucket_has(self, index: int, fingerprint: int) -> bool:
        """Check whether a bucket holds a fingerprint.

        Args:
            index: Bucket number.
            fingerprint: Fingerprint to look for.

        Returns:
            True if one of the bucket's slots holds it.
        """
        start = index * self._bucket_size
        table = self._table
        for slot in range(start, start + self._bucket_size):
            if table[slot] == fingerprint:
                return True
        return False

    def _bucket_insert(self, index: int, fingerprint: int) -> bool:
        """Put a fingerprint in the first free slot of a bucket.

        Args:
            index: Bucket number.
            fingerprint: Fingerprint to store.

        Returns:
            True if stored, False if the bucket is full.
        """
        start = index * self._bucket_size
        table = self._table
        for slot in range(start, start + self._bucket_size):
            if table[slot] == 0:
                table[slot] = fingerprint
                return True
        return False

    def _bucket_remove(self, index: int, fingerprint: int) -> bool:
        """Clear one slot of a bucket that holds a fingerprint.

        Args:
            index: Bucket number.
            fingerprint: Fingerprint to delete.

        Returns:
            True if a copy was removed, False if none was found.
        """
        start = index * self._bucket_size
        table = self._table
        for slot in range(start, start + self._bucket_size):
            if table[slot] == fingerprint:
                table[slot] = 0
                return True
        return False

    def _place(self, index: int, fingerprint: int) -> None:
        """Store a fingerprint in bucket ``index`` or its alternate, evicting if needed.

        Performs the cuckoo random walk: swap the fingerprint with a random
        resident of a full bucket, move the evicted one to its alternate
        bucket, and repeat up to ``max_kicks`` times. If the walk fails, the
        fingerprint still being carried is parked in the victim stash.

        Args:
            index: One of the fingerprint's two buckets.
            fingerprint: Fingerprint to store.

        Returns:
            None.
        """
        if self._bucket_insert(index, fingerprint):
            return
        alt_index = self._alt_index(index, fingerprint)
        if self._bucket_insert(alt_index, fingerprint):
            return
        rng, table, bucket_size = self._rng, self._table, self._bucket_size
        if rng.random() < 0.5:
            index = alt_index
        for _ in range(self._max_kicks):
            slot = index * bucket_size + rng.randrange(bucket_size)
            fingerprint, table[slot] = table[slot], fingerprint
            index = self._alt_index(index, fingerprint)
            if self._bucket_insert(index, fingerprint):
                return
        self._victim = (index, fingerprint)

    def add(self, login: str) -> None:
        """Insert a login's fingerprint; O(1) expected, at most ``max_kicks`` evictions.

        Args:
            login: Username to store.

        Returns:
            None.

        Raises:
            CuckooFilterFullError: If an earlier insert already failed.
        """
        if self._victim is not None:
            raise CuckooFilterFullError(
                f"cuckoo filter is full ({self._count} logins, load {self.load_factor:.1%})"
            )
        fingerprint, index = self._locate(login)
        self._place(index, fingerprint)
        self._count += 1

    def contains(self, login: str) -> bool:
        """Look for the login's fingerprint in its two buckets, O(b).

        Args:
            login: Username to look up.

        Returns:
            False if the login is definitely absent; True if it is probably
            present (false positives are possible, false negatives are not).
        """
        fingerprint, index = self._locate(login)
        if self._bucket_has(index, fingerprint):
            return True
        alt_index = self._alt_index(index, fingerprint)
        if self._bucket_has(alt_index, fingerprint):
            return True
        victim = self._victim
        return victim is not None and victim[1] == fingerprint and victim[0] in (index, alt_index)

    def remove(self, login: str) -> bool:
        """Delete one copy of a login's fingerprint, O(b).

        Only remove logins that were actually added: removing a false
        positive would delete another login's fingerprint.

        Args:
            login: Username to delete.

        Returns:
            True if a matching fingerprint was removed, False otherwise.
        """
        fingerprint, index = self._locate(login)
        alt_index = self._alt_index(index, fingerprint)
        victim = self._victim
        if self._bucket_remove(index, fingerprint) or self._bucket_remove(alt_index, fingerprint):
            self._count -= 1
            if victim is not None:  # a slot is free now: retry the parked fingerprint
                self._victim = None
                self._place(*victim)
            return True
        if victim is not None and victim[1] == fingerprint and victim[0] in (index, alt_index):
            self._victim = None
            self._count -= 1
            return True
        return False

    def memory_bytes(self) -> int:
        """Size of the fingerprint table plus the precomputed offsets.

        Returns:
            Memory use in bytes; logins themselves are not stored.
        """
        return sys.getsizeof(self._table) + sys.getsizeof(self._alt_offsets)

    def __len__(self) -> int:
        """Return the number of stored logins."""
        return self._count
