"""Hash table with separate chaining.

An array of ``capacity`` slots; login ``x`` lives in slot
``hash(x) & (capacity - 1)``. Each non-empty slot holds a short list (a
"chain") of the logins that hash there. Buckets are created lazily, so an
empty slot costs only one pointer.

With load factor ``alpha = n / capacity`` kept at most 0.75 by doubling,
lookups take O(1 + alpha) = O(1) expected time (CLRS Theorems 11.1-11.2) and
inserts take O(1) amortized time.

AI-assisted: generated with Claude Code (see README, "AI usage").
"""

from __future__ import annotations

import sys
from typing import Callable

from login_checker.base import LoginChecker
from login_checker.hashing import hash64


def next_power_of_two(value: int) -> int:
    """Round up to the nearest power of two.

    Args:
        value: Positive integer.

    Returns:
        Smallest power of two that is ``>= value``.
    """
    return 1 << (value - 1).bit_length()


class HashTable(LoginChecker):
    """Exact login checker backed by a chained hash table."""

    name = "Hash table"
    MAX_LOAD = 0.75
    MIN_CAPACITY = 8
    __slots__ = ("_slots", "_mask", "_size", "_hash")

    def __init__(
        self, capacity: int = MIN_CAPACITY, hash_function: Callable[[str], int] = hash64
    ) -> None:
        """Create an empty table.

        Args:
            capacity: Initial number of slots; rounded up to a power of two.
            hash_function: Maps a login to a non-negative integer. Only
                replaced in tests (e.g. to force collisions).

        Returns:
            None.
        """
        capacity = next_power_of_two(max(capacity, self.MIN_CAPACITY))
        self._slots: list[list[str] | None] = [None] * capacity
        self._mask = capacity - 1
        self._size = 0
        self._hash = hash_function

    @property
    def capacity(self) -> int:
        """Number of slots (buckets) in the table."""
        return len(self._slots)

    @property
    def load_factor(self) -> float:
        """Stored logins per slot (alpha)."""
        return self._size / len(self._slots)

    def add(self, login: str) -> None:
        """Insert a login unless it is already present; O(1) expected, amortized.

        Args:
            login: Username to store.

        Returns:
            None.
        """
        index = self._hash(login) & self._mask
        bucket = self._slots[index]
        if bucket is None:
            self._slots[index] = [login]
        else:
            for item in bucket:
                if item == login:
                    return
            bucket.append(login)
        self._size += 1
        if self._size > self.MAX_LOAD * len(self._slots):
            self._resize(2 * len(self._slots))

    def contains(self, login: str) -> bool:
        """Scan only the login's own bucket; O(1) expected.

        Args:
            login: Username to look up.

        Returns:
            True if the login is stored, False otherwise.
        """
        bucket = self._slots[self._hash(login) & self._mask]
        if bucket is not None:
            for item in bucket:
                if item == login:
                    return True
        return False

    def remove(self, login: str) -> bool:
        """Delete a login if present; O(1) expected.

        Args:
            login: Username to delete.

        Returns:
            True if the login was found and removed, False otherwise.
        """
        index = self._hash(login) & self._mask
        bucket = self._slots[index]
        if bucket is None:
            return False
        for position, item in enumerate(bucket):
            if item == login:
                bucket[position] = bucket[-1]  # order inside a chain is irrelevant
                bucket.pop()
                if not bucket:
                    self._slots[index] = None
                self._size -= 1
                return True
        return False

    def _resize(self, new_capacity: int) -> None:
        """Move every login into a new slot array (rehashing), O(n).

        Args:
            new_capacity: New number of slots; must be a power of two.

        Returns:
            None.
        """
        old_slots = self._slots
        self._slots = [None] * new_capacity
        self._mask = new_capacity - 1
        slots, mask, hash_function = self._slots, self._mask, self._hash
        for bucket in old_slots:
            if bucket is None:
                continue
            for login in bucket:
                index = hash_function(login) & mask
                if slots[index] is None:
                    slots[index] = [login]
                else:
                    slots[index].append(login)

    def memory_bytes(self) -> int:
        """Size of the slot array, the chains and every stored string.

        Returns:
            Approximate memory use in bytes.
        """
        total = sys.getsizeof(self._slots)
        for bucket in self._slots:
            if bucket is not None:
                total += sys.getsizeof(bucket) + sum(sys.getsizeof(item) for item in bucket)
        return total

    def __len__(self) -> int:
        """Return the number of stored logins."""
        return self._size
