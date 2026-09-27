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
│   └── hashing.py          #   BLAKE2b-based hash helpers (hash64, hash_pair, mix64)
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
