"""Login checker demo: build the five structures and compare them live.

Usage (from the repository root)::

    python demo.py                              # 100,000 logins, built-in examples
    python demo.py --n 1000000                  # a bigger dataset
    python demo.py --check alice fnaf0000001    # check your own logins
    python demo.py --interactive                # type logins to sign up

Logins come from ``data/logins_10000000.txt.gz`` when it exists (see
data/README.md); otherwise the same logins are generated in memory.

AI-assisted: generated with Claude Code (see README, "AI usage").
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

from login_checker import BloomFilter, CuckooFilter, HashTable, LinearSearchChecker, LoginChecker
from login_checker.dataset import generate_absent_logins, generate_logins, load_logins, make_queries
from login_checker.experiment import (
    checker_factories,
    false_positive_rate,
    format_table,
    mean_lookup_seconds,
    timed_build,
)

DEFAULT_DATA = Path("data/logins_10000000.txt.gz")
QUERY_COUNT = 20_000  # lookups timed per structure (50% hits, 50% misses)
LINEAR_BUDGET = 20_000_000  # max list elements linear search may scan in total
ABSENT_COUNT = 20_000  # never-registered logins used to measure false positives
DISPLAY_WIDTH = 24
NEW_LOGIN = "new_user_2026"


def load_demo_logins(count: int, path: Path) -> tuple[list[str], str]:
    """Read the first ``count`` logins from the dataset file, or generate them.

    Args:
        count: Number of logins wanted.
        path: Dataset file to read if it exists.

    Returns:
        Tuple ``(logins, description of where they came from)``.
    """
    if path.exists():
        logins = load_logins(path, limit=count)
        if len(logins) == count:
            return logins, f"loaded from {path}"
    return list(generate_logins(count)), "generated in memory (dataset file not found)"


def shorten(login: str) -> str:
    """Abbreviate long logins so tables stay readable.

    Args:
        login: Login to display.

    Returns:
        The login quoted, cut to ``DISPLAY_WIDTH`` characters if needed.
    """
    text = login if len(login) <= DISPLAY_WIDTH else login[: DISPLAY_WIDTH - 3] + "..."
    return repr(text)


def status_row(login: str, checkers: dict[str, LoginChecker], note: str = "") -> list[str]:
    """One table row: each structure's answer for a login.

    Args:
        login: Login to check.
        checkers: Structures keyed by name.
        note: Optional text for the last column.

    Returns:
        Row cells: the login, one "taken"/"free" per structure, the note.
    """
    answers = ["taken" if checker.contains(login) else "free" for checker in checkers.values()]
    return [shorten(login), *answers, note]


def build_structures(logins: list[str], absent: list[str]) -> dict[str, LoginChecker]:
    """Build every structure, print a comparison table and return them.

    Args:
        logins: Logins to store.
        absent: Never-registered logins (misses and false-positive tests).

    Returns:
        The five loaded structures keyed by name.
    """
    queries = [login for login, _ in make_queries(logins, absent, QUERY_COUNT)]
    linear_queries = queries[: max(10, min(QUERY_COUNT, LINEAR_BUDGET // len(logins)))]
    checkers, rows = {}, []
    for name, factory in checker_factories(len(logins)).items():
        checker, build_seconds = timed_build(factory, logins)
        sample = linear_queries if isinstance(checker, LinearSearchChecker) else queries
        lookup_us = mean_lookup_seconds(checker, sample) * 1e6
        memory = checker.memory_bytes()
        errors = "none (exact)"
        if checker.is_probabilistic:
            errors = f"{false_positive_rate(checker, absent):.2%}"
        rows.append([
            name, f"{build_seconds:.2f}", f"{memory / 1e6:.2f}", f"{memory / len(logins):.1f}",
            f"{lookup_us:,.2f}", errors,
        ])
        checkers[name] = checker
    headers = [
        "Structure", "Build (s)", "Memory (MB)", "Bytes/login", "Lookup (us)", "False positives",
    ]
    print(format_table(headers, rows))
    return checkers


def check_logins(checkers: dict[str, LoginChecker], examples: Iterable[tuple[str, str]]) -> None:
    """Print every structure's answer for each example login.

    Args:
        checkers: Structures keyed by name.
        examples: Pairs ``(login, note)``.

    Returns:
        None.
    """
    rows = [status_row(login, checkers, note) for login, note in examples]
    print(format_table(["Login", *checkers, "Note"], rows))


def default_examples(
    logins: list[str], absent: list[str], checkers: dict[str, LoginChecker]
) -> list[tuple[str, str]]:
    """Built-in examples: stored logins, free logins and real false positives.

    Args:
        logins: Stored logins.
        absent: Never-registered logins.
        checkers: Structures keyed by name.

    Returns:
        List of ``(login, note)`` pairs.
    """
    examples = [
        (logins[0], "stored"),
        (logins[-1], "stored"),
        (absent[0], "never registered"),
        ("alice", "never registered"),
    ]
    for name in (BloomFilter.name, CuckooFilter.name):
        false_positive = next((login for login in absent if checkers[name].contains(login)), None)
        if false_positive is not None:
            examples.append((false_positive, f"never registered: {name} false positive"))
    return examples


def signup_flow(checkers: dict[str, LoginChecker], login: str) -> None:
    """Show ``register`` accepting a free login once and rejecting a repeat.

    Args:
        checkers: Structures keyed by name.
        login: A login not yet stored.

    Returns:
        None.
    """
    rows = []
    for attempt in ("first attempt", "second attempt"):
        results = [
            "reserved" if checker.register(login) else "rejected" for checker in checkers.values()
        ]
        rows.append([f"register({login!r}), {attempt}", *results])
    print(format_table(["Action", *checkers], rows))


def deletion_demo(checkers: dict[str, LoginChecker], login: str) -> None:
    """Delete a login where supported and show that a Bloom filter cannot.

    Args:
        checkers: Structures keyed by name.
        login: A stored login to delete.

    Returns:
        None.
    """
    for name in (HashTable.name, CuckooFilter.name):
        removed = checkers[name].remove(login)
        state = "taken" if checkers[name].contains(login) else "free"
        print(f"  {name + ':':15} remove({login!r}) -> {removed}; now {state}")
    bloom_state = "taken" if checkers[BloomFilter.name].contains(login) else "free"
    print(
        f"  {BloomFilter.name + ':':15} no remove operation (bits are shared); "
        f"still reports {bloom_state}"
    )


def interactive_signup(checkers: dict[str, LoginChecker]) -> None:
    """Let the user type logins; free ones are registered in every structure.

    Args:
        checkers: Structures keyed by name.

    Returns:
        None.
    """
    exact = checkers[HashTable.name]
    print("Type a login to sign up (empty line to quit).")
    while True:
        try:
            login = input("login> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not login:
            break
        if exact.contains(login):
            check_logins(checkers, [(login, "already taken")])
            continue
        check_logins(checkers, [(login, "before sign-up")])
        wrongly_rejected = [
            name for name, checker in checkers.items() if not checker.register(login)
        ]
        if wrongly_rejected:
            print(f"  free, but rejected by {', '.join(wrongly_rejected)} (false positive)")
        else:
            print("  free: registered in all five structures")


def parse_args() -> argparse.Namespace:
    """Parse command-line options.

    Returns:
        Namespace with ``n``, ``data``, ``check`` and ``interactive``.
    """
    parser = argparse.ArgumentParser(description="Compare the five login checkers live.")
    parser.add_argument("--n", type=int, default=100_000, help="number of stored logins")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA, help="dataset file to read")
    parser.add_argument("--check", nargs="+", metavar="LOGIN", help="logins to check")
    parser.add_argument("--interactive", action="store_true", help="type logins to sign up")
    return parser.parse_args()


def main() -> None:
    """Run the demo.

    Returns:
        None.
    """
    args = parse_args()
    logins, source = load_demo_logins(args.n, args.data)
    absent = list(generate_absent_logins(ABSENT_COUNT))
    print(f"Login checker demo: n = {len(logins):,} logins, {source}\n")

    print("1. Building the five structures")
    checkers = build_structures(logins, absent)

    print("\n2. Is this login taken?")
    if args.check:
        check_logins(checkers, [(login, "") for login in args.check])
    else:
        check_logins(checkers, default_examples(logins, absent, checkers))

    print("\n3. Sign-up: register() checks, then adds the login if it is free")
    signup_flow(checkers, NEW_LOGIN)

    print("\n4. Deleting an account")
    deletion_demo(checkers, NEW_LOGIN)

    if args.interactive:
        print("\n5. Interactive sign-up")
        interactive_signup(checkers)


if __name__ == "__main__":
    main()
