"""Benchmark the five login checkers and write the results as CSV files.

Three experiments:

1. **Stored** - all five structures for n = 1,000 ... 10,000,000 (1-2-5
   steps), each built ``--repeats`` times; the median time is reported.
2. **Streamed** - the Bloom and cuckoo filters for n = 20M ... 100M. Filters
   do not keep the logins, so these are generated chunk by chunk and never
   held in memory together. Built once per size.
3. **Trade-off** - Bloom vs. cuckoo at several false-positive targets:
   bits per login against the measured false-positive rate.

Outputs (in ``--out-dir``): ``benchmark.csv``, ``tradeoff.csv`` and
``environment.json``. Rows are written as soon as they are measured, so an
interrupted run keeps its partial results.

Usage (from the repository root)::

    python -m scripts.run_benchmarks            # full run, about 1 hour
    python -m scripts.run_benchmarks --quick    # setup check, under a minute

AI-assisted: generated with Claude Code (see README, "AI usage").
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import random
import statistics
import sys
import time
from datetime import datetime, timezone
from itertools import islice
from pathlib import Path
from typing import Callable, Iterator

from login_checker import BloomFilter, CuckooFilter, LinearSearchChecker, LoginChecker
from login_checker.dataset import generate_absent_logins, generate_logins, load_logins
from login_checker.experiment import (
    checker_factories,
    false_positive_rate,
    mean_lookup_seconds,
    timed_add_all,
    timed_build,
)

MIN_N = 1_000
QUERY_COUNT = 20_000  # lookups per measurement: half hits, half misses
LINEAR_BUDGET = 200_000_000  # cap on list elements linear search scans per measurement
MIN_LINEAR_QUERIES = 20
ABSENT_COUNT = 100_000  # misses available for lookups and false-positive rates
STREAM_CHUNK = 1_000_000
STREAM_HIT_SAMPLE = 10_000
FP_TARGETS = [0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1]
FILTER_CLASSES: list[type[LoginChecker]] = [BloomFilter, CuckooFilter]

BENCHMARK_FIELDS = [
    "structure", "n", "mode", "repeats", "build_s", "lookup_us", "hit_us", "miss_us",
    "queries", "memory_bytes", "bytes_per_login", "fp_measured", "fp_expected", "fp_bound",
]
TRADEOFF_FIELDS = ["structure", "n", "fp_target", "bits_theory", "bits_actual", "fp_measured"]


def size_ladder(low: int, high: int) -> list[int]:
    """Sizes 1, 2 and 5 times each power of ten within ``[low, high]``.

    Args:
        low: Smallest size.
        high: Largest size.

    Returns:
        Increasing list of sizes.
    """
    sizes, power = [], 1
    while power <= high:
        sizes += [step * power for step in (1, 2, 5) if low <= step * power <= high]
        power *= 10
    return sizes


def load_or_generate(
    path: Path, count: int, generator: Callable[[int], Iterator[str]]
) -> list[str]:
    """Read ``count`` logins from a dataset file, or generate them if it is missing.

    Args:
        path: Dataset file (see data/README.md).
        count: Number of logins needed.
        generator: Fallback that yields the same logins lazily.

    Returns:
        List of ``count`` logins.
    """
    if path.exists():
        logins = load_logins(path, limit=count)
        if len(logins) == count:
            print(f"Loaded {count:,} logins from {path}")
            return logins
    print(f"Generating {count:,} logins ({path} not found or too small)")
    return list(generator(count))


def sample_hits(logins: list[str], count: int, seed: int) -> list[str]:
    """Pick stored logins uniformly at random (with replacement).

    Args:
        logins: Stored logins.
        count: Number of samples.
        seed: RNG seed.

    Returns:
        List of ``count`` logins.
    """
    rng = random.Random(seed)
    return [logins[rng.randrange(len(logins))] for _ in range(count)]


def describe(checker: LoginChecker, absent: list[str]) -> dict[str, object]:
    """Memory and error statistics of a loaded structure.

    Args:
        checker: Loaded structure.
        absent: Never-added logins for measuring false positives.

    Returns:
        Row fields: memory, bytes per login and false-positive rates (the
        latter left empty for exact structures, which cannot err).
    """
    memory = checker.memory_bytes()
    row: dict[str, object] = {
        "memory_bytes": memory,
        "bytes_per_login": round(memory / len(checker), 3),
        "fp_measured": "", "fp_expected": "", "fp_bound": "",
    }
    if checker.is_probabilistic:
        row["fp_measured"] = false_positive_rate(checker, absent)
        row["fp_expected"] = checker.expected_fp_rate()
        bound = checker.fp_rate_bound() if isinstance(checker, CuckooFilter) else None
        row["fp_bound"] = bound if bound is not None else row["fp_expected"]
    return row


def measure_stored(
    name: str, factory: Callable[[], LoginChecker], logins: list[str], absent: list[str],
    repeats: int,
) -> dict[str, object]:
    """Build one structure ``repeats`` times and time its lookups.

    Args:
        name: Structure name.
        factory: Creates an empty structure.
        logins: Logins to store.
        absent: Never-added logins (misses).
        repeats: Number of builds; medians are reported.

    Returns:
        One ``benchmark.csv`` row.
    """
    n = len(logins)
    queries = QUERY_COUNT
    if name == LinearSearchChecker.name:
        queries = max(MIN_LINEAR_QUERIES, min(QUERY_COUNT, LINEAR_BUDGET // n))
    hits, misses = sample_hits(logins, queries // 2, seed=n), absent[: queries // 2]
    builds, hit_times, miss_times = [], [], []
    row: dict[str, object] = {}
    for repeat in range(repeats):
        checker, build_seconds = timed_build(factory, logins)
        builds.append(build_seconds)
        hit_times.append(mean_lookup_seconds(checker, hits))
        miss_times.append(mean_lookup_seconds(checker, misses))
        if repeat == 0:
            row = describe(checker, absent)
        del checker
    hit_us, miss_us = statistics.median(hit_times) * 1e6, statistics.median(miss_times) * 1e6
    return {
        "structure": name, "n": n, "mode": "stored", "repeats": repeats,
        "build_s": statistics.median(builds), "lookup_us": (hit_us + miss_us) / 2,
        "hit_us": hit_us, "miss_us": miss_us, "queries": 2 * (queries // 2), **row,
    }


def measure_streamed(n: int, absent: list[str]) -> list[dict[str, object]]:
    """Build both filters for ``n`` generated logins, one chunk at a time.

    Args:
        n: Number of logins.
        absent: Never-added logins (misses).

    Returns:
        One ``benchmark.csv`` row per filter.
    """
    filters, build_seconds = {}, {}
    for cls in FILTER_CLASSES:
        filters[cls.name], build_seconds[cls.name] = timed_build(lambda cls=cls: cls(n), [])
    hits: list[str] = []
    stride = max(1, n // STREAM_HIT_SAMPLE)
    stream = generate_logins(n)
    done = 0
    while chunk := list(islice(stream, STREAM_CHUNK)):
        hits.extend(chunk[::stride])
        for name, checker in filters.items():
            build_seconds[name] += timed_add_all(checker, chunk)
        done += len(chunk)
        if done % (10 * STREAM_CHUNK) == 0:
            print(f"    streamed {done:,} / {n:,}", flush=True)
    hits = hits[: QUERY_COUNT // 2]
    misses = absent[: QUERY_COUNT // 2]
    rows = []
    for name, checker in filters.items():
        hit_us = mean_lookup_seconds(checker, hits) * 1e6
        miss_us = mean_lookup_seconds(checker, misses) * 1e6
        rows.append({
            "structure": name, "n": n, "mode": "streamed", "repeats": 1,
            "build_s": build_seconds[name], "lookup_us": (hit_us + miss_us) / 2,
            "hit_us": hit_us, "miss_us": miss_us, "queries": len(hits) + len(misses),
            **describe(checker, absent),
        })
    return rows


def theoretical_bits(checker: LoginChecker) -> int:
    """Bits of the filter's table as the analysis counts them.

    Args:
        checker: A Bloom or cuckoo filter.

    Returns:
        ``m`` for a Bloom filter; ``B * b * f`` for a cuckoo filter.
    """
    if isinstance(checker, CuckooFilter):
        return checker.num_buckets * checker.bucket_size * checker.fingerprint_bits
    return checker.num_bits


def measure_tradeoff(logins: list[str], absent: list[str]) -> list[dict[str, object]]:
    """Space vs. accuracy of both filters over several false-positive targets.

    Args:
        logins: Logins to store.
        absent: Never-added logins for measuring false positives.

    Returns:
        One ``tradeoff.csv`` row per filter and target.
    """
    n, rows = len(logins), []
    for fp_target in FP_TARGETS:
        for cls in FILTER_CLASSES:
            checker = cls(n, fp_target)
            checker.add_all(logins)
            rows.append({
                "structure": cls.name, "n": n, "fp_target": fp_target,
                "bits_theory": theoretical_bits(checker) / n,
                "bits_actual": checker.memory_bytes() * 8 / n,
                "fp_measured": false_positive_rate(checker, absent),
            })
    return rows


def cpu_name() -> str:
    """Best-effort human-readable CPU model name.

    Returns:
        The CPU brand string, or ``platform.processor()`` as a fallback.
    """
    try:
        import winreg  # Windows only

        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
        )
        return str(winreg.QueryValueEx(key, "ProcessorNameString")[0]).strip()
    except (ImportError, OSError):
        pass
    try:
        with open("/proc/cpuinfo", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("model name"):
                    return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or "unknown"


def total_ram_bytes() -> int | None:
    """Best-effort physical memory size.

    Returns:
        Bytes of RAM, or None if it cannot be determined.
    """
    try:
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    except (AttributeError, ValueError, OSError):
        pass
    try:
        import ctypes

        kilobytes = ctypes.c_ulonglong()
        if ctypes.windll.kernel32.GetPhysicallyInstalledSystemMemory(ctypes.byref(kilobytes)):
            return kilobytes.value * 1024
    except (AttributeError, OSError):
        pass
    return None


def environment_info(args: argparse.Namespace) -> dict[str, object]:
    """Describe the machine and settings of this run.

    Args:
        args: Parsed command-line options.

    Returns:
        JSON-serializable dictionary.
    """
    return {
        "date_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "cpu": cpu_name(),
        "logical_cpus": os.cpu_count(),
        "ram_bytes": total_ram_bytes(),
        "os": platform.platform(),
        "python": sys.version.split()[0],
        "max_n": args.max_n,
        "stream_max_n": args.stream_max_n,
        "repeats": args.repeats,
        "query_count": QUERY_COUNT,
        "linear_budget": LINEAR_BUDGET,
        "fp_rate": 0.01,
    }


def parse_args() -> argparse.Namespace:
    """Parse command-line options; ``--quick`` shrinks every experiment.

    Returns:
        Namespace with the run settings.
    """
    parser = argparse.ArgumentParser(description="Benchmark the five login checkers.")
    parser.add_argument("--quick", action="store_true", help="small run to check the setup")
    parser.add_argument("--max-n", type=int, default=10_000_000, help="largest stored n")
    parser.add_argument("--stream-max-n", type=int, default=100_000_000,
                        help="largest streamed n for the filters (0 to skip)")
    parser.add_argument("--tradeoff-n", type=int, default=1_000_000, help="n for the trade-off")
    parser.add_argument("--repeats", type=int, default=3, help="builds per measurement")
    parser.add_argument("--data", type=Path, default=Path("data/logins_10000000.txt.gz"))
    parser.add_argument("--absent", type=Path, default=Path("data/absent_100000.txt.gz"))
    parser.add_argument("--out-dir", type=Path, default=None,
                        help="output folder (default results/, or results/quick/ with --quick)")
    args = parser.parse_args()
    if args.quick:
        args.max_n, args.stream_max_n, args.tradeoff_n, args.repeats = 100_000, 0, 20_000, 1
    if args.out_dir is None:
        args.out_dir = Path("results/quick" if args.quick else "results")
    return args


def main() -> None:
    """Run the three experiments and write the CSV files.

    Returns:
        None.
    """
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "environment.json").write_text(
        json.dumps(environment_info(args), indent=2) + "\n", encoding="utf-8"
    )
    start = time.perf_counter()
    logins = load_or_generate(args.data, args.max_n, generate_logins)
    absent = load_or_generate(args.absent, ABSENT_COUNT, generate_absent_logins)

    with open(args.out_dir / "benchmark.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=BENCHMARK_FIELDS)
        writer.writeheader()
        print("\n1. Stored experiment (all five structures)")
        for n in size_ladder(MIN_N, args.max_n):
            subset = logins if n == len(logins) else logins[:n]
            for name, factory in checker_factories(n).items():
                row = measure_stored(name, factory, subset, absent, args.repeats)
                writer.writerow(row)
                handle.flush()
                print(f"  n={n:>11,}  {name:14} build {row['build_s']:8.3f}s  "
                      f"lookup {row['lookup_us']:12,.2f}us  [{time.perf_counter() - start:6.0f}s]")
        print("\n2. Streamed experiment (filters only)")
        for n in size_ladder(args.max_n + 1, args.stream_max_n):
            for row in measure_streamed(n, absent):
                writer.writerow(row)
                handle.flush()
                print(f"  n={n:>11,}  {row['structure']:14} build {row['build_s']:8.1f}s  "
                      f"lookup {row['lookup_us']:8.2f}us  [{time.perf_counter() - start:6.0f}s]")

    print(f"\n3. Trade-off experiment (n = {args.tradeoff_n:,})")
    tradeoff_logins = logins[: args.tradeoff_n] if args.tradeoff_n <= len(logins) else list(
        generate_logins(args.tradeoff_n)
    )
    with open(args.out_dir / "tradeoff.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=TRADEOFF_FIELDS)
        writer.writeheader()
        writer.writerows(measure_tradeoff(tradeoff_logins, absent))
    print(f"\nDone in {time.perf_counter() - start:.0f}s; results in {args.out_dir}/")


if __name__ == "__main__":
    main()
