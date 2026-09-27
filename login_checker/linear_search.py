"""Linear search over an unsorted list.

Logins are appended to a list, and a lookup compares the query with every
stored login until it finds a match. A lookup costs O(n) comparisons: about
(n + 1) / 2 for a hit and exactly n for a miss, which is the common case
when checking whether a new login is free.

AI-assisted: generated with Claude Code (see README, "AI usage").
"""

from __future__ import annotations

import sys
from typing import Iterable

from login_checker.base import LoginChecker


class LinearSearchChecker(LoginChecker):
    """Exact login checker backed by an unsorted list."""

    name = "Linear search"
    __slots__ = ("_items",)

    def __init__(self) -> None:
        """Create an empty checker.

        Returns:
            None.
        """
        self._items: list[str] = []

    def add(self, login: str) -> None:
        """Append a login in amortized O(1).

        Args:
            login: Username to store.

        Returns:
            None.
        """
        self._items.append(login)

    def add_all(self, logins: Iterable[str]) -> None:
        """Append many logins in O(n) total.

        Args:
            logins: Iterable of usernames to store.

        Returns:
            None.
        """
        self._items.extend(logins)

    def contains(self, login: str) -> bool:
        """Scan the list from the start until the login is found, O(n).

        An explicit loop is used on purpose: ``login in list`` would run the
        same scan in C and hide the cost being measured.

        Args:
            login: Username to look up.

        Returns:
            True if the login is stored, False otherwise.
        """
        for item in self._items:
            if item == login:
                return True
        return False

    def memory_bytes(self) -> int:
        """Size of the list plus every stored string.

        Returns:
            Approximate memory use in bytes.
        """
        return sys.getsizeof(self._items) + sum(sys.getsizeof(item) for item in self._items)

    def __len__(self) -> int:
        """Return the number of stored logins."""
        return len(self._items)
