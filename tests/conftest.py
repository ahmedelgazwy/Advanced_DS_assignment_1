"""Shared pytest fixtures: checker factories and sample logins.

AI-assisted: generated with Claude Code (see README, "AI usage").
"""

from __future__ import annotations

from typing import Callable

import pytest

from login_checker import (
    BinarySearchChecker,
    BloomFilter,
    CuckooFilter,
    HashTable,
    LinearSearchChecker,
    LoginChecker,
)
from login_checker.dataset import generate_absent_logins, generate_logins

NUM_LOGINS = 2_000

EXACT_FACTORIES: dict[str, Callable[[], LoginChecker]] = {
    "linear_search": LinearSearchChecker,
    "binary_search": BinarySearchChecker,
    "hash_table": HashTable,
}
FILTER_FACTORIES: dict[str, Callable[[], LoginChecker]] = {
    "bloom_filter": lambda: BloomFilter(capacity=NUM_LOGINS, fp_rate=0.01),
    "cuckoo_filter": lambda: CuckooFilter(capacity=NUM_LOGINS, fp_rate=0.01),
}
ALL_FACTORIES = {**EXACT_FACTORIES, **FILTER_FACTORIES}


@pytest.fixture(params=list(ALL_FACTORIES))
def make_checker(request: pytest.FixtureRequest) -> Callable[[], LoginChecker]:
    """Factory for each of the five structures (the test runs once per structure)."""
    return ALL_FACTORIES[request.param]


@pytest.fixture(params=list(EXACT_FACTORIES))
def make_exact_checker(request: pytest.FixtureRequest) -> Callable[[], LoginChecker]:
    """Factory for each exact structure (never wrong)."""
    return EXACT_FACTORIES[request.param]


@pytest.fixture(params=list(FILTER_FACTORIES))
def make_filter(request: pytest.FixtureRequest) -> Callable[[], LoginChecker]:
    """Factory for each probabilistic filter, sized for ``NUM_LOGINS`` logins."""
    return FILTER_FACTORIES[request.param]


@pytest.fixture(scope="session")
def logins() -> list[str]:
    """``NUM_LOGINS`` unique logins (do not mutate: shared by all tests)."""
    return list(generate_logins(NUM_LOGINS))


@pytest.fixture(scope="session")
def absent_logins() -> list[str]:
    """``NUM_LOGINS`` logins guaranteed not to be in ``logins``."""
    return list(generate_absent_logins(NUM_LOGINS))
