"""Tests specific to HashTable.

AI-assisted: generated with Claude Code (see README, "AI usage").
"""

from __future__ import annotations

from login_checker import HashTable
from login_checker.hash_table import next_power_of_two


def test_next_power_of_two():
    assert [next_power_of_two(v) for v in (1, 2, 3, 8, 9, 1000)] == [1, 2, 4, 8, 16, 1024]


def test_capacity_is_a_power_of_two_with_a_minimum():
    assert HashTable(capacity=100).capacity == 128
    assert HashTable(capacity=1).capacity == HashTable.MIN_CAPACITY


def test_resize_keeps_all_logins_and_bounds_the_load(logins):
    table = HashTable(capacity=8)
    for login in logins:
        table.add(login)
    assert table.capacity > 8
    assert table.load_factor <= HashTable.MAX_LOAD
    assert all(table.contains(login) for login in logins)


def test_chains_stay_short_after_resizing(logins):
    """Resizing must spread logins over the new slots, keeping lookups O(1)."""
    table = HashTable(capacity=8)
    table.add_all(logins)
    chain_lengths = [len(bucket) for bucket in table._slots if bucket is not None]
    assert max(chain_lengths) <= 8
    assert len(chain_lengths) > table.capacity // 4  # many slots are in use


def test_duplicate_add_is_ignored():
    table = HashTable()
    table.add("alice")
    table.add("alice")
    assert len(table) == 1


def test_remove(logins):
    table = HashTable()
    table.add_all(logins)
    assert table.remove(logins[0]) is True
    assert table.remove(logins[0]) is False  # already gone
    assert not table.contains(logins[0])
    assert table.remove("never-added") is False
    assert len(table) == len(logins) - 1
    assert all(table.contains(login) for login in logins[1:])


def test_all_collisions_still_give_correct_answers(logins, absent_logins):
    """Worst case: a constant hash puts every login in one chain (O(n) lookups)."""
    table = HashTable(hash_function=lambda login: 0)
    table.add_all(logins[:300])
    assert all(table.contains(login) for login in logins[:300])
    assert not any(table.contains(login) for login in absent_logins[:300])
    assert table.remove(logins[150])
    assert not table.contains(logins[150])
    assert all(table.contains(login) for login in logins[:300] if login != logins[150])
