# Login Checker — COSC 520 Assignment 1

How fast can we answer *"is this username already taken?"* for millions of
users? This project implements five set-membership data structures from
scratch in Python, analyses their time and space complexity, and benchmarks
them on a synthetic dataset of login names.

| Structure | Module | Answer |
|---|---|---|
| Linear search over a list | `login_checker/linear_search.py` | exact |
| Binary search over a sorted array | `login_checker/binary_search.py` | exact |
| Hash table (separate chaining) | `login_checker/hash_table.py` | exact |
| Bloom filter | `login_checker/bloom_filter.py` | probabilistic: false positives, never false negatives |
| Cuckoo filter | `login_checker/cuckoo_filter.py` | probabilistic: false positives, never false negatives |

All five are implemented by hand. No library data structures are used: no
`dict`/`set` as the hash table, no `bisect`, and no Bloom/cuckoo packages. The
only library primitive is the BLAKE2b hash *function* from Python's standard
`hashlib`.

## Repository layout

```
.
├── login_checker/          # the library
│   ├── base.py             #   LoginChecker: interface shared by all five structures
│   ├── linear_search.py    #   LinearSearchChecker
│   ├── binary_search.py    #   BinarySearchChecker
│   ├── hash_table.py       #   HashTable (separate chaining, doubling at load 0.75)
│   ├── bloom_filter.py     #   BloomFilter (bit array, double hashing)
│   ├── cuckoo_filter.py    #   CuckooFilter (4-slot buckets, fingerprints, victim stash)
│   ├── hashing.py          #   BLAKE2b-based hash helpers (hash64, hash_pair, mix64)
│   └── dataset.py          #   synthetic login generator, query mix, file I/O
├── scripts/
│   └── generate_dataset.py # CLI: writes data/*.txt.gz and data/manifest.json
├── tests/                  # pytest suite (107 tests, about 1 s)
├── data/                   # dataset folder (large files downloaded or generated)
├── docs/
│   └── theory.md           # complexity analysis, formulas, references
├── requirements.txt        # pinned dependencies
└── pyproject.toml          # pytest configuration
```

## Setup

Requires **Python 3.10 or newer**. Run the commands from the repository root.

**Windows (PowerShell)**
```powershell
py -3.10 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**macOS / Linux**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

No installation of the package itself is needed; every command is run from
the repository root.

## Running the tests

```bash
python -m pytest
```

The suite runs in about a second and needs no dataset files.

| File | What it checks |
|---|---|
| `tests/test_common.py` | the contract every structure must satisfy, run once per structure: no false negatives, `register`, special logins (empty, Unicode, 10,000 characters), exact structures never wrong, filters' FP rate near target, filters far smaller than exact structures |
| `tests/test_binary_search.py` | lower-bound positions, boundaries, sortedness after single and bulk inserts |
| `tests/test_hash_table.py` | power-of-two capacity, resizing, short chains, duplicates, removal, worst case with every login in one chain |
| `tests/test_bloom_filter.py` | optimal `m` and `k` against hand-computed values, measured vs. theoretical FP rate, overfilling, memory |
| `tests/test_cuckoo_filter.py` | `f` formula, table sizing, alternate bucket is an involution, FP bound, removal, full-filter behaviour and victim stash, duplicate limit |
| `tests/test_hashing.py` | determinism, agreement with BLAKE2b, 64-bit range, even spread |
| `tests/test_dataset.py` | uniqueness, format, seeding, prefix property, absent logins never collide, query mix, file round trips, the generator script |

## Usage

Every structure implements the same `LoginChecker` interface:

```python
from login_checker import BloomFilter, HashTable

checker = BloomFilter(capacity=1_000_000, fp_rate=0.01)
checker.register("alice")   # True: the name was free and is now taken
checker.register("alice")   # False: already taken
"bob" in checker            # False: definitely free

table = HashTable()         # exact structures also support removal
table.register("alice")     # True
table.remove("alice")       # True
```

| Method | Meaning |
|---|---|
| `add(login)` | record a login as taken |
| `contains(login)` / `login in checker` | is the login (probably) taken? |
| `register(login)` | check, then add if free; returns whether it succeeded |
| `add_all(logins)` | bulk load |
| `memory_bytes()`, `len(checker)` | size information |
| `remove(login)` | `HashTable` and `CuckooFilter` only (a Bloom filter cannot delete) |

## Dataset

10 million synthetic, guaranteed-unique logins plus 100,000 guaranteed-absent
logins for miss queries.

- **Download:** https://github.com/ahmedelgazwy/Advanced_DS_assignment_1/releases/tag/dataset-v1. Put the files in `data/`.
- **Or regenerate** byte-identical files (about 40 s): `python -m scripts.generate_dataset`
- **Or a smaller one:** `python -m scripts.generate_dataset --n 100000`

The format and guarantees are described in [data/README.md](data/README.md).

## Theory

The time and space complexity of each structure, the Bloom and cuckoo filter
false-positive formulas, and the parameter choices are in
[docs/theory.md](docs/theory.md).

## AI usage

This project was developed with the help of an AI coding assistant (Claude
Code, Anthropic), as allowed by the course policy with disclosure. The
assistant helped draft the plan and generated the code, tests and
documentation. The author directed the work phase by phase and reviewed each
phase before the next one started. Every file produced with AI assistance
carries the line `AI-assisted: generated with Claude Code` in its header.
