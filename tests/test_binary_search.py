"""Tests specific to BinarySearchChecker.

AI-assisted: generated with Claude Code (see README, "AI usage").
"""

from __future__ import annotations

import random

from login_checker import BinarySearchChecker


def build(logins: list[str]) -> BinarySearchChecker:
    """Bulk-load a checker with the given logins."""
    checker = BinarySearchChecker()
    checker.add_all(logins)
    return checker


def test_lower_bound_positions():
    checker = build(["b", "d", "f"])
    expected = {"a": 0, "b": 0, "c": 1, "d": 1, "e": 2, "f": 2, "g": 3}
    for login, position in expected.items():
        assert checker._lower_bound(login) == position


def test_finds_first_middle_and_last_elements(logins):
    checker = build(logins)
    ordered = sorted(logins)
    for login in (ordered[0], ordered[len(ordered) // 2], ordered[-1]):
        assert checker.contains(login)


def test_logins_outside_the_range_are_absent():
    checker = build(["m", "n", "o"])
    assert not checker.contains("a")  # smaller than everything
    assert not checker.contains("z")  # larger than everything
    assert not checker.contains("mm")  # between two elements


def test_empty_and_single_element():
    checker = BinarySearchChecker()
    assert not checker.contains("alice")
    checker.add("alice")
    assert checker.contains("alice")
    assert not checker.contains("bob")


def test_single_adds_keep_the_array_sorted(logins):
    shuffled = logins[:500]
    random.Random(7).shuffle(shuffled)
    checker = BinarySearchChecker()
    for login in shuffled:
        checker.add(login)
    assert checker._items == sorted(shuffled)


def test_add_after_bulk_load_keeps_the_array_sorted(logins):
    checker = build(logins[:1000])
    for login in logins[1000:1100]:
        checker.add(login)
    checker.add_all(logins[1100:1200])
    assert checker._items == sorted(logins[:1200])
