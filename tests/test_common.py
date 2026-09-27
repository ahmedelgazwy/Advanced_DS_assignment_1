"""Contract tests that every login checker must pass.

Each test runs once per structure through the parametrized factory fixtures
in ``conftest.py``. Linear search has no behaviour beyond this contract, so it
has no dedicated test file.

AI-assisted: generated with Claude Code (see README, "AI usage").
"""

from __future__ import annotations

from conftest import ALL_FACTORIES, EXACT_FACTORIES, FILTER_FACTORIES, NUM_LOGINS

SPECIAL_LOGINS = ["", "a", "josé", "用户名", "with space", "UPPER", "x" * 10_000]


def test_empty_checker_contains_nothing(make_checker, logins):
    checker = make_checker()
    assert len(checker) == 0
    assert not any(checker.contains(login) for login in logins[:200])


def test_add_then_contains_has_no_false_negatives(make_checker, logins):
    checker = make_checker()
    for login in logins:
        checker.add(login)
    assert len(checker) == NUM_LOGINS
    assert all(checker.contains(login) for login in logins)


def test_add_all_then_contains_has_no_false_negatives(make_checker, logins):
    checker = make_checker()
    checker.add_all(logins)
    assert len(checker) == NUM_LOGINS
    assert all(checker.contains(login) for login in logins)


def test_exact_checkers_never_report_absent_logins(make_exact_checker, logins, absent_logins):
    checker = make_exact_checker()
    checker.add_all(logins)
    assert not any(checker.contains(login) for login in absent_logins)


def test_filters_false_positive_rate_is_near_target(make_filter, logins, absent_logins):
    checker = make_filter()
    checker.add_all(logins)
    false_positives = sum(checker.contains(login) for login in absent_logins)
    assert false_positives / len(absent_logins) < 0.03  # target 1%, generous margin


def test_register_reserves_free_login_once(make_checker):
    checker = make_checker()
    assert checker.register("alice") is True
    assert checker.register("alice") is False
    assert checker.contains("alice")


def test_in_operator_matches_contains(make_checker):
    checker = make_checker()
    checker.add("alice")
    assert "alice" in checker
    assert 42 not in checker  # non-strings are never contained


def test_special_logins_are_found(make_checker):
    checker = make_checker()
    for login in SPECIAL_LOGINS:
        checker.add(login)
    assert all(checker.contains(login) for login in SPECIAL_LOGINS)


def test_exact_checkers_are_case_sensitive(make_exact_checker):
    checker = make_exact_checker()
    checker.add("Alice")
    assert checker.contains("Alice")
    assert not checker.contains("alice")


def test_duplicate_add_keeps_login_findable(make_checker):
    checker = make_checker()
    checker.add("alice")
    checker.add("alice")
    assert checker.contains("alice")


def test_memory_is_positive_and_does_not_shrink(make_checker, logins):
    checker = make_checker()
    before = checker.memory_bytes()
    checker.add_all(logins)
    after = checker.memory_bytes()
    assert 0 < before <= after
    if checker.is_probabilistic:
        assert after == before  # filters allocate their whole table up front


def test_filters_use_less_memory_than_exact_structures(logins):
    sizes = {}
    for name, factory in ALL_FACTORIES.items():
        checker = factory()
        checker.add_all(logins)
        sizes[name] = checker.memory_bytes()
    smallest_exact = min(sizes[name] for name in EXACT_FACTORIES)
    for name in FILTER_FACTORIES:
        assert sizes[name] * 5 < smallest_exact
