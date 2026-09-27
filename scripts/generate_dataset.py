"""Generate the synthetic login dataset used by the benchmarks.

Writes three files to the output directory:

* ``logins_<n>.txt.gz``  - ``n`` unique stored logins, one per line;
* ``absent_<a>.txt.gz``  - ``a`` logins guaranteed not to be stored (misses);
* ``manifest.json``      - seeds, sizes and SHA-256 checksums.

Usage (from the repository root)::

    python -m scripts.generate_dataset                  # 10M logins, 100k absent
    python -m scripts.generate_dataset --n 100000       # small dataset

AI-assisted: generated with Claude Code (see README, "AI usage").
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Iterator

from login_checker.dataset import (
    ABSENT_SEED,
    DEFAULT_SEED,
    generate_absent_logins,
    generate_logins,
    save_logins,
)

DEFAULT_N = 10_000_000
DEFAULT_ABSENT = 100_000
PROGRESS_STEP = 1_000_000


def sha256_of(path: Path) -> str:
    """Compute the SHA-256 checksum of a file.

    Args:
        path: File to hash.

    Returns:
        Hex digest string.
    """
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def with_progress(logins: Iterator[str], total: int) -> Iterator[str]:
    """Pass logins through unchanged, printing progress every million.

    Args:
        logins: Logins to forward.
        total: Expected number of logins (for the message).

    Returns:
        Iterator yielding the same logins.
    """
    for count, login in enumerate(logins, start=1):
        if count % PROGRESS_STEP == 0:
            print(f"  {count:,} / {total:,}", flush=True)
        yield login


def parse_args() -> argparse.Namespace:
    """Parse command-line options.

    Returns:
        Namespace with ``n``, ``absent``, ``seed``, ``absent_seed`` and ``out_dir``.
    """
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--n", type=int, default=DEFAULT_N, help="number of stored logins")
    parser.add_argument("--absent", type=int, default=DEFAULT_ABSENT, help="number of misses")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="seed for stored logins")
    parser.add_argument("--absent-seed", type=int, default=ABSENT_SEED, help="seed for misses")
    parser.add_argument("--out-dir", type=Path, default=Path("data"), help="output directory")
    return parser.parse_args()


def main() -> None:
    """Generate the dataset files and the manifest.

    Returns:
        None.
    """
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    logins_path = args.out_dir / f"logins_{args.n}.txt.gz"
    absent_path = args.out_dir / f"absent_{args.absent}.txt.gz"

    start = time.perf_counter()
    print(f"Writing {args.n:,} stored logins to {logins_path} ...")
    save_logins(logins_path, with_progress(generate_logins(args.n, args.seed), args.n))
    print(f"Writing {args.absent:,} absent logins to {absent_path} ...")
    save_logins(absent_path, generate_absent_logins(args.absent, args.absent_seed))

    manifest = {
        "description": "Synthetic login names for the COSC 520 login checker benchmark",
        "format": "gzip-compressed UTF-8 text, one login per line",
        "login_pattern": "4-10 random lowercase letters + 7-char base-36 index",
        "stored": {"file": logins_path.name, "count": args.n, "seed": args.seed},
        "absent": {"file": absent_path.name, "count": args.absent, "seed": args.absent_seed},
        "sha256": {path.name: sha256_of(path) for path in (logins_path, absent_path)},
        "bytes": {path.name: path.stat().st_size for path in (logins_path, absent_path)},
    }
    manifest_path = args.out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Done in {time.perf_counter() - start:.1f}s; manifest written to {manifest_path}")


if __name__ == "__main__":
    main()
