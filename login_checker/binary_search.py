"""Binary search over a sorted array.

Logins are kept in lexicographic order, so a lookup can halve the search
interval at every step: O(log n) comparisons. The price is paid on updates:
inserting one login shifts the larger elements, O(n).

AI-assisted: generated with Claude Code (see README, "AI usage").
"""

from __future__ import annotations

import sys
from typing import Iterable

from login_checker.base import LoginChecker


class BinarySearchChecker(LoginChecker):
    """Exact login checker backed by a sorted list."""

    name = "Binary search"
    __slots__ = ("_items",)

    def __init__(self) -> None:
        """Create an empty checker.

        Returns:
            None.
        """
        self._items: list[str] = []

    def add(self, login: str) -> None:
        """Insert a login at its sorted position.

        Finding the position takes O(log n); shifting the tail takes O(n).

        Args:
            login: Username to store.

        Returns:
            None.
        """
        self._items.insert(self._lower_bound(login), login)

    def add_all(self, logins: Iterable[str]) -> None:
        """Bulk-load logins: append them all, then sort once, O(n log n).

        Sorting uses Python's built-in Timsort. It is only the build step;
        the search itself (:meth:`_lower_bound`) is implemented here.

        Args:
            logins: Iterable of usernames to store.

        Returns:
            None.
        """
        self._items.extend(logins)
        self._items.sort()

    def contains(self, login: str) -> bool:
        """Binary-search for the login, O(log n) comparisons.

        Args:
            login: Username to look up.

        Returns:
            True if the login is stored, False otherwise.
        """
        position = self._lower_bound(login)
        return position < len(self._items) and self._items[position] == login

    def _lower_bound(self, login: str) -> int:
        """Find the first position whose login is not smaller than ``login``.

        The loop keeps the invariant: everything left of ``low`` is smaller
        than ``login`` and everything from ``high`` onwards is not.

        Args:
            login: Username to locate.

        Returns:
            Index in ``[0, n]`` where ``login`` is, or would be inserted.
        """
        items = self._items
        low, high = 0, len(items)
        while low < high:
            mid = (low + high) // 2
            if items[mid] < login:
                low = mid + 1
            else:
                high = mid
        return low

    def memory_bytes(self) -> int:
        """Size of the list plus every stored string.

        Returns:
            Approximate memory use in bytes.
        """
        return sys.getsizeof(self._items) + sum(sys.getsizeof(item) for item in self._items)

    def __len__(self) -> int:
        """Return the number of stored logins."""
        return len(self._items)
