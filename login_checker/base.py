"""Common interface shared by every login checker.

All five data structures answer the same question - "is this login already
taken?" - so they all implement :class:`LoginChecker`. The demo, the
benchmarks and the shared unit tests only talk to this interface, which is
what lets them treat the structures interchangeably.

AI-assisted: generated with Claude Code (see README, "AI usage").
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable


class LoginChecker(ABC):
    """Abstract set-membership structure for login names.

    Exact structures (list, sorted array, hash table) never make mistakes.
    Probabilistic filters (Bloom, cuckoo) may report a free login as taken
    (false positive) but never report a taken login as free (false negative).
    """

    #: Human-readable name used in tables and plots.
    name: str = "LoginChecker"
    #: True if ``contains`` can return false positives.
    is_probabilistic: bool = False

    __slots__ = ()

    @abstractmethod
    def add(self, login: str) -> None:
        """Record a login as taken.

        The login-checker workflow calls ``contains`` first (see
        :meth:`register`), so callers normally add only new logins.

        Args:
            login: Username to store.

        Returns:
            None.
        """

    @abstractmethod
    def contains(self, login: str) -> bool:
        """Check whether a login is (probably) taken.

        Args:
            login: Username to look up.

        Returns:
            True if the login is taken (for filters: probably taken),
            False if it is definitely free.
        """

    @abstractmethod
    def memory_bytes(self) -> int:
        """Estimate the memory used by the structure.

        Returns:
            Approximate size in bytes of everything the structure owns
            (containers plus stored strings, where applicable).
        """

    @abstractmethod
    def __len__(self) -> int:
        """Return the number of logins added so far."""

    def expected_fp_rate(self) -> float:
        """Theoretical false-positive rate at the current number of logins.

        Returns:
            0.0 for exact structures; filters override this with their formula.
        """
        return 0.0

    def __contains__(self, login: object) -> bool:
        """Support the ``login in checker`` syntax.

        Args:
            login: Value to look up; non-strings are never contained.

        Returns:
            Same result as :meth:`contains` for strings, else False.
        """
        return isinstance(login, str) and self.contains(login)

    def add_all(self, logins: Iterable[str]) -> None:
        """Add many logins; subclasses may override with a faster bulk load.

        Args:
            logins: Iterable of usernames to store.

        Returns:
            None.
        """
        for login in logins:
            self.add(login)

    def register(self, login: str) -> bool:
        """Reserve a login if it is free (the login-checker workflow).

        Args:
            login: Username requested by a new user.

        Returns:
            True if the login was free and is now reserved, False if it was
            (reported as) already taken.
        """
        if self.contains(login):
            return False
        self.add(login)
        return True
