Machine: 11th Gen Intel(R) Core(TM) i7-11800H @ 2.30GHz, 16 GiB RAM, Windows-10-10.0.26200-SP0, Python 3.10.2

## All five structures at n = 10,000,000

| Structure | Build (s) | Lookup (µs) | Hit (µs) | Miss (µs) | Memory (MB) | Bytes/login | FP rate | Lookup slope | Build slope |
|---|---|---|---|---|---|---|---|---|---|
| Linear search | 0.09 | 201,724.90 | 104,670.69 | 298,779.11 | 710.0 | 71.0 | 0 (exact) | 1.04 | 1.23 |
| Binary search | 10.51 | 8.83 | 8.08 | 9.58 | 710.0 | 71.0 | 0 (exact) | 0.26 | 1.29 |
| Hash table | 47.85 | 1.94 | 1.82 | 2.06 | 1,359.6 | 136.0 | 0 (exact) | 0.11 | 1.08 |
| Bloom filter | 49.38 | 3.18 | 4.09 | 2.27 | 12.0 | 1.2 | 1.04% | 0.09 | 1.10 |
| Cuckoo filter | 35.78 | 3.30 | 2.46 | 4.14 | 22.2 | 2.2 | 0.73% | 0.08 | 1.08 |

## Filters streamed beyond the stored sizes

| Structure | n | Build (s) | Lookup (µs) | Memory (MB) | Bytes/login | FP rate |
|---|---|---|---|---|---|---|
| Bloom filter | 20,000,000 | 97 | 3.91 | 24.0 | 1.20 | 1.04% |
| Cuckoo filter | 20,000,000 | 69 | 3.54 | 44.4 | 2.22 | 0.75% |
| Bloom filter | 50,000,000 | 310 | 4.78 | 59.9 | 1.20 | 1.00% |
| Cuckoo filter | 50,000,000 | 216 | 4.19 | 111.1 | 2.22 | 0.70% |
| Bloom filter | 100,000,000 | 713 | 4.40 | 119.8 | 1.20 | 0.99% |
| Cuckoo filter | 100,000,000 | 455 | 3.40 | 222.2 | 2.22 | 0.68% |
