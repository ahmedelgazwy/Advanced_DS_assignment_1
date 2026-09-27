"""Synthetic login-name dataset.

Each login is a random lowercase prefix (4-10 letters) followed by a
fixed-width, 7-character base-36 encoding of its index, e.g. ``qmwkz00002bf``.

Why this format:

* **Guaranteed unique without a set.** The suffix encodes the index, so two
  logins with different indices can never be equal.
* **Guaranteed-absent queries.** Stored ("present") logins use indices below
  ``ABSENT_START``; logins used as negative queries use indices from
  ``ABSENT_START`` upwards, so they can never appear in any dataset.
* **Streamable and nested.** Logins are produced lazily from a seeded RNG, so
  the first ``n`` logins are the same whatever total size is generated. The
  dataset for a smaller ``n`` is simply a prefix of the full file.

AI-assisted: generated with Claude Code (see README, "AI usage").
"""

from __future__ import annotations

import gzip
import io
import random
from contextlib import contextmanager
from itertools import islice
from pathlib import Path
from typing import IO, Iterable, Iterator, Sequence

ALPHABET36 = "0123456789abcdefghijklmnopqrstuvwxyz"
LETTERS = "abcdefghijklmnopqrstuvwxyz"
SUFFIX_WIDTH = 7
SUFFIX_LIMIT = 36**SUFFIX_WIDTH  # 78,364,164,096 distinct suffixes
ABSENT_START = SUFFIX_LIMIT // 2  # first index reserved for absent logins
PREFIX_MIN_LEN = 4
PREFIX_MAX_LEN = 10
DEFAULT_SEED = 42
ABSENT_SEED = 43


def encode_suffix(index: int) -> str:
    """Encode an index as a fixed-width base-36 string.

    Args:
        index: Integer in ``[0, SUFFIX_LIMIT)``.

    Returns:
        ``SUFFIX_WIDTH`` characters from ``0-9a-z``, zero-padded.

    Raises:
        ValueError: If the index is out of range.
    """
    if not 0 <= index < SUFFIX_LIMIT:
        raise ValueError(f"index {index} is outside [0, {SUFFIX_LIMIT})")
    chars = []
    for _ in range(SUFFIX_WIDTH):
        index, digit = divmod(index, 36)
        chars.append(ALPHABET36[digit])
    return "".join(reversed(chars))


def _generate(start: int, count: int, seed: int) -> Iterator[str]:
    """Yield ``count`` logins for indices ``start, start + 1, ...``.

    Args:
        start: Index of the first login.
        count: Number of logins to yield.
        seed: Seed for the prefix RNG.

    Returns:
        Iterator of login strings.
    """
    rng = random.Random(seed)
    choices = rng.choices
    length_span = PREFIX_MAX_LEN - PREFIX_MIN_LEN + 1
    for index in range(start, start + count):
        length = PREFIX_MIN_LEN + int(rng.random() * length_span)
        yield "".join(choices(LETTERS, k=length)) + encode_suffix(index)


def generate_logins(count: int, seed: int = DEFAULT_SEED) -> Iterator[str]:
    """Lazily generate ``count`` unique stored logins.

    Args:
        count: Number of logins, at most ``ABSENT_START``.
        seed: RNG seed; the same seed always gives the same logins.

    Returns:
        Iterator of unique login strings (indices ``0 .. count - 1``).

    Raises:
        ValueError: If ``count`` is negative or too large.
    """
    if not 0 <= count <= ABSENT_START:
        raise ValueError(f"count must be in [0, {ABSENT_START}]")
    return _generate(0, count, seed)


def generate_absent_logins(count: int, seed: int = ABSENT_SEED) -> Iterator[str]:
    """Lazily generate logins guaranteed not to be in any stored dataset.

    Args:
        count: Number of logins, at most ``SUFFIX_LIMIT - ABSENT_START``.
        seed: RNG seed for the prefixes.

    Returns:
        Iterator of unique login strings whose indices start at
        ``ABSENT_START``.

    Raises:
        ValueError: If ``count`` is negative or too large.
    """
    if not 0 <= count <= SUFFIX_LIMIT - ABSENT_START:
        raise ValueError(f"count must be in [0, {SUFFIX_LIMIT - ABSENT_START}]")
    return _generate(ABSENT_START, count, seed)


def make_queries(
    logins: Sequence[str],
    absent: Sequence[str],
    count: int,
    hit_ratio: float = 0.5,
    seed: int = DEFAULT_SEED,
) -> list[tuple[str, bool]]:
    """Build a shuffled mix of present and absent lookup queries.

    Args:
        logins: Stored logins to sample hits from (with replacement).
        absent: Logins known to be absent; the first ones are used as misses.
        count: Total number of queries.
        hit_ratio: Fraction of queries that are present logins.
        seed: RNG seed for sampling and shuffling.

    Returns:
        List of ``(login, is_member)`` pairs in random order.

    Raises:
        ValueError: If there are not enough logins or absent logins.
    """
    num_hits = round(count * hit_ratio)
    num_misses = count - num_hits
    if num_hits and not logins:
        raise ValueError("cannot sample hits from an empty login list")
    if num_misses > len(absent):
        raise ValueError(f"need {num_misses} absent logins, got {len(absent)}")
    rng = random.Random(seed)
    queries = [(logins[rng.randrange(len(logins))], True) for _ in range(num_hits)]
    queries.extend((login, False) for login in absent[:num_misses])
    rng.shuffle(queries)
    return queries


@contextmanager
def _open_text(path: Path, mode: str) -> Iterator[IO[str]]:
    """Open a UTF-8 text file, transparently gzip-compressed if it ends in .gz.

    Compressed files are written with ``mtime=0`` and no file name in the
    gzip header, so regenerating a dataset gives byte-identical output (the
    same SHA-256 as the published files).

    Args:
        path: File path.
        mode: ``"r"`` to read or ``"w"`` to write.

    Returns:
        Context manager yielding a text handle with ``\\n`` line endings.
    """
    if path.suffix != ".gz":
        with open(path, mode, encoding="utf-8", newline="\n") as handle:
            yield handle
        return
    with open(path, mode + "b") as raw, gzip.GzipFile(
        filename="", mode=mode + "b", fileobj=raw, mtime=0, compresslevel=6
    ) as compressed, io.TextIOWrapper(compressed, encoding="utf-8", newline="\n") as handle:
        yield handle


def save_logins(path: str | Path, logins: Iterable[str]) -> int:
    """Write logins to a text file, one per line (gzip if the name ends in .gz).

    Args:
        path: Destination file.
        logins: Logins to write; may be a lazy iterator.

    Returns:
        Number of logins written.
    """
    count = 0
    with _open_text(Path(path), "w") as handle:
        for login in logins:
            handle.write(login + "\n")
            count += 1
    return count


def load_logins(path: str | Path, limit: int | None = None) -> list[str]:
    """Read logins from a file written by :func:`save_logins`.

    Args:
        path: Source file (plain text or .gz).
        limit: Read only the first ``limit`` logins; None reads all.

    Returns:
        List of login strings in file order.
    """
    with _open_text(Path(path), "r") as handle:
        return [line.rstrip("\n") for line in islice(handle, limit)]
