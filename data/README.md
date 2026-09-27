# Dataset

Synthetic login names used by the benchmarks.

**Download:** https://github.com/ahmedelgazwy/Advanced_DS_assignment_1/releases/tag/dataset-v1

| File | Contents | Size |
|---|---|---|
| `logins_10000000.txt.gz` | 10,000,000 unique stored logins, one per line | 78 MB |
| `absent_100000.txt.gz` | 100,000 logins guaranteed **not** to be stored (used as misses) | 0.8 MB |
| `manifest.json` | seeds, counts and SHA-256 checksums of both files | 1 KB |

The large files are not committed to git. Place them in this folder, or
regenerate them (about 40 seconds):

```bash
python -m scripts.generate_dataset
```

Generation is deterministic. The same seeds produce byte-identical files, so
the SHA-256 checksums in `manifest.json` can be used to verify a download or a
regeneration.

## Login format

```
ahftrxck0000000
fnaf0000001
ofpvausi0000002
```

Each login is **4–10 random lowercase letters** followed by a **7-character
base-36 index** (average length 14 characters).

- **Unique by construction.** The suffix encodes the index, so no two logins can be equal.
- **Absent logins can never collide.** Stored logins use indices below 36⁷/2, and absent logins use indices from 36⁷/2 upwards.
- **Nested.** The first *n* lines are exactly the dataset of size *n*. The benchmarks read a prefix of the file for each *n*.

Code: [`login_checker/dataset.py`](../login_checker/dataset.py).
