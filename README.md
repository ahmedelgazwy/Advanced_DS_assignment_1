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
│   ├── dataset.py          #   synthetic login generator, query mix, file I/O
│   └── experiment.py       #   shared timing helpers and table formatting
├── demo.py                 # live comparison of the five structures
├── scripts/
│   └── generate_dataset.py # CLI: writes data/*.txt.gz and data/manifest.json
├── tests/                  # pytest suite (114 tests, about 2 s)
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

## Demo

```bash
python demo.py                              # 100,000 logins, built-in examples (~2 s)
python demo.py --n 1000000                  # a bigger dataset (~15 s)
python demo.py --check alice fnaf0000001    # check your own logins
python demo.py --interactive                # type logins to sign up
```

The demo reads logins from `data/logins_10000000.txt.gz` when the file exists
and otherwise generates the same logins in memory. It then does four things:

1. builds all five structures and compares build time, memory, lookup time and false-positive rate;
2. checks example logins, including a real false positive found for each filter;
3. runs the sign-up flow (`register` accepts a free name once and rejects the repeat);
4. deletes an account, showing that the hash table and cuckoo filter can remove a login but a Bloom filter cannot.

Example output (Intel i7-11800H, Python 3.10):

```
1. Building the five structures
Structure      Build (s)  Memory (MB)  Bytes/login  Lookup (us)  False positives
-------------  ---------  -----------  -----------  -----------  ---------------
Linear search  0.00       7.10         71.0         1,406.51     none (exact)
Binary search  0.02       7.10         71.0         2.08         none (exact)
Hash table     0.34       14.55        145.5        1.16         none (exact)
Bloom filter   0.28       0.12         1.2          2.04         1.03%
Cuckoo filter  0.22       0.23         2.3          2.13         0.72%

2. Is this login taken?
Login               Linear search  Binary search  Hash table  Bloom filter  Cuckoo filter  Note
------------------  -------------  -------------  ----------  ------------  -------------  ----------------------------------------------
'ahftrxck0000000'   taken          taken          taken       taken         taken          stored
'sdmri000000'       free           free           free        free          free           never registered
'tasoxbahzi00002j'  free           free           free        taken         free           never registered: Bloom filter false positive
'zfapi00001r'       free           free           free        free          taken          never registered: Cuckoo filter false positive
```

## Running the tests

```bash
python -m pytest
```

The suite runs in about two seconds and needs no dataset files.

| File | What it checks |
|---|---|
| `tests/test_common.py` | the contract every structure must satisfy, run once per structure: no false negatives, `register`, special logins (empty, Unicode, 10,000 characters), exact structures never wrong, filters' FP rate near target, filters far smaller than exact structures |
| `tests/test_binary_search.py` | lower-bound positions, boundaries, sortedness after single and bulk inserts |
| `tests/test_hash_table.py` | power-of-two capacity, resizing, short chains, duplicates, removal, worst case with every login in one chain |
| `tests/test_bloom_filter.py` | optimal `m` and `k` against hand-computed values, measured vs. theoretical FP rate, overfilling, memory |
| `tests/test_cuckoo_filter.py` | `f` formula, table sizing, alternate bucket is an involution, FP bound, removal, full-filter behaviour and victim stash, duplicate limit |
| `tests/test_hashing.py` | determinism, agreement with BLAKE2b, 64-bit range, even spread |
| `tests/test_dataset.py` | uniqueness, format, seeding, prefix property, absent logins never collide, query mix, file round trips, the generator script |
| `tests/test_experiment.py` | timing helpers, table formatting, and an end-to-end run of `demo.py` |

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
