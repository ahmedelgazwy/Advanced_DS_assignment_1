"""Measurement helpers shared by the demo and the benchmark.

Provides the five structures under one configuration, timing functions
that pause the garbage collector (as ``timeit`` does) so that collection
pauses do not distort the measurements, and a plain-text table formatter.

AI-assisted: generated with Claude Code (see README, "AI usage").
"""

from __future__ import annotations

import gc
import time
from contextlib import contextmanager
from typing import Callable, Iterator, Sequence

from login_checker.base import LoginChecker
from login_checker.binary_search import BinarySearchChecker
from login_checker.bloom_filter import BloomFilter
from login_checker.cuckoo_filter import CuckooFilter
from login_checker.hash_table import HashTable
from login_checker.linear_search import LinearSearchChecker

DEFAULT_FP_RATE = 0.01


def checker_factories(
    capacity: int, fp_rate: float = DEFAULT_FP_RATE
) -> dict[str, Callable[[], LoginChecker]]:
    """Factories for the five structures, keyed by display name.

    Args:
        capacity: Expected number of logins; sizes the two filters.
        fp_rate: Target false-positive rate for the two filters.

    Returns:
        Ordered mapping from structure name to a zero-argument factory.
    """
    return {
        LinearSearchChecker.name: LinearSearchChecker,
        BinarySearchChecker.name: BinarySearchChecker,
        HashTable.name: HashTable,
        BloomFilter.name: lambda: BloomFilter(capacity, fp_rate),
        CuckooFilter.name: lambda: CuckooFilter(capacity, fp_rate),
    }


@contextmanager
def gc_paused() -> Iterator[None]:
    """Disable the cyclic garbage collector for the duration of a block.

    Returns:
        Context manager; the previous GC state is restored on exit.
    """
    was_enabled = gc.isenabled()
    gc.disable()
    try:
        yield
    finally:
        if was_enabled:
            gc.enable()


def timed_build(
    factory: Callable[[], LoginChecker], logins: Sequence[str]
) -> tuple[LoginChecker, float]:
    """Create a structure and bulk-load it, measuring the wall-clock time.

    Args:
        factory: Zero-argument function returning an empty checker.
        logins: Logins to load.

    Returns:
        Tuple ``(checker, seconds)``.
    """
    with gc_paused():
        start = time.perf_counter()
        checker = factory()
        checker.add_all(logins)
        elapsed = time.perf_counter() - start
    return checker, elapsed


def timed_add_all(checker: LoginChecker, logins: Sequence[str]) -> float:
    """Bulk-load logins into an existing structure, measuring the time.

    Used to build a filter chunk by chunk when the logins do not fit in
    memory at once.

    Args:
        checker: Structure to load.
        logins: Logins to add.

    Returns:
        Seconds taken.
    """
    with gc_paused():
        start = time.perf_counter()
        checker.add_all(logins)
        return time.perf_counter() - start


def mean_lookup_seconds(checker: LoginChecker, queries: Sequence[str]) -> float:
    """Average time of one ``contains`` call over a list of queries.

    Args:
        checker: Structure to query.
        queries: Logins to look up (must not be empty).

    Returns:
        Mean seconds per lookup.
    """
    contains = checker.contains
    with gc_paused():
        start = time.perf_counter()
        for login in queries:
            contains(login)
        elapsed = time.perf_counter() - start
    return elapsed / len(queries)


def false_positive_rate(checker: LoginChecker, absent: Sequence[str]) -> float:
    """Fraction of never-added logins that the checker reports as taken.

    Args:
        checker: Structure to query.
        absent: Logins known not to be stored (must not be empty).

    Returns:
        Measured false-positive rate in [0, 1].
    """
    return sum(1 for login in absent if checker.contains(login)) / len(absent)


def format_table(headers: Sequence[str], rows: Sequence[Sequence[object]]) -> str:
    """Render rows as a plain-text table with aligned columns.

    Args:
        headers: Column titles.
        rows: Table rows; cells are converted with ``str``.

    Returns:
        Multi-line string: the header, a rule, then one line per row.
    """
    cells = [[str(cell) for cell in row] for row in rows]
    widths = [max(len(text) for text in column) for column in zip(headers, *cells)]
    lines = [headers, ["-" * width for width in widths], *cells]
    return "\n".join(
        "  ".join(text.ljust(width) for text, width in zip(line, widths)).rstrip() for line in lines
    )
