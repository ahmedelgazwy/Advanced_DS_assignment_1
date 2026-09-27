# Phase 1 — Theory Notes: Complexity of the Five Login Checkers

> Drafted with AI assistance (Claude Code). See the AI-usage statement in the README.
> These notes are the source for the "Complexity Analysis" section of the report.

The **login checker problem**: given a set $S$ of $n$ existing logins, decide
quickly whether a new login $x$ is already in $S$. Every structure below
supports two operations:

- `add(x)` — record $x$ as taken;
- `contains(x)` — answer "taken?" for $x$.

---

## 0. Notation

| Symbol | Meaning |
|---|---|
| $n$ | number of stored logins |
| $L$ | average login length in characters; hashing a login costs $\Theta(L)$, comparing two logins costs $O(L)$ |
| $M$ | number of buckets in the hash table |
| $\alpha$ | load factor: $n/M$ (hash table) or $n/(Bb)$ (cuckoo filter) |
| $m$ | number of bits in the Bloom filter |
| $k$ | number of hash functions in the Bloom filter |
| $p$ | Bloom filter false-positive (FP) probability |
| $B$ | number of buckets in the cuckoo filter |
| $b$ | slots (entries) per cuckoo bucket |
| $f$ | fingerprint length in bits |
| $\varepsilon$ | cuckoo filter FP probability |
| $\text{MaxKicks}$ | maximum evictions before a cuckoo insert gives up |

---

## 1. Linear search over an unsorted list

**How it works.** Logins are appended to a list. `contains(x)` compares $x$ with
each element in turn and stops at the first match.

| Operation | Cost | Justification |
|---|---|---|
| Build ($n$ appends) | $O(n)$ | each append is amortized $O(1)$ (dynamic array with geometric growth) |
| Lookup, hit | $\frac{n+1}{2}$ comparisons expected $\Rightarrow O(nL)$ | target equally likely at each of the $n$ positions [Knuth §6.1] |
| Lookup, miss | exactly $n$ comparisons $\Rightarrow \Theta(n)$ comparisons, $O(nL)$ time | every element must be ruled out |
| Insert | $O(1)$ amortized | append (the caller checks `contains` first) |
| Space | $\Theta(nL)$ | the list stores every login; $O(1)$ extra space |

A "miss" (the login is free) is the **common case** in the login checker, and it
is also the worst case for linear search.

---

## 2. Binary search over a sorted array

**How it works.** Logins are kept in lexicographic order. `contains(x)` compares
$x$ with the middle element and discards the half that cannot contain it.

| Operation | Cost | Justification |
|---|---|---|
| Build | $O(n \log n)$ comparisons $\Rightarrow O(L\, n\log n)$ | comparison sort (Timsort in CPython) |
| Lookup (hit or miss) | at most $\lfloor \log_2 n \rfloor + 1$ comparisons $\Rightarrow O(L \log n)$ | the interval halves each step [Knuth §6.2.1, Alg. B] |
| Insert (keep sorted) | $O(\log n)$ to find the slot + $O(n)$ to shift | array insertion moves the suffix |
| Space | $\Theta(nL)$ | same as the list; iterative search uses $O(1)$ extra space |

For $n = 10^9$, a lookup needs at most $\lfloor\log_2 10^9\rfloor + 1 = 30$ comparisons.

---

## 3. Hash table with separate chaining

**How it works.** An array of $M$ buckets. A login $x$ is stored in bucket
$h(x) \bmod M$. Each bucket holds a short list of the logins that hash to it.

Under **simple uniform hashing**, the expected chain length is $\alpha = n/M$, and
[CLRS, Thms 11.1–11.2]:

$$
\mathbb{E}[\text{unsuccessful search}] = \Theta(1+\alpha), \qquad
\mathbb{E}[\text{successful search}] = \Theta(1+\alpha).
$$

The implementation **doubles** $M$ whenever $\alpha > 0.75$, so $\alpha = \Theta(1)$.

| Operation | Cost | Justification |
|---|---|---|
| Hash one login | $\Theta(L)$ | reads every character |
| Lookup (expected) | $O(L + 1 + \alpha) = O(L)$, i.e. $O(1)$ in $n$ | Thms 11.1–11.2 with bounded $\alpha$ |
| Lookup (worst) | $O(nL)$ | every key lands in one bucket |
| Insert | $O(1)$ expected, **amortized** | a resize rehashes $n$ keys, but after doubling the next resize happens only after another $\Theta(n)$ inserts; total resize work over $n$ inserts is $O(n)$ (aggregate method, [CLRS 4th ed. §16.4, "Dynamic tables"]) |
| Space | $\Theta(nL + M) = \Theta(nL)$ | all logins are stored plus $M = \Theta(n)$ bucket pointers |

---

## 4. Bloom filter [Bloom 1970; Broder & Mitzenmacher 2004]

**How it works.** A bit array of $m$ bits, all 0 at the start, and $k$ hash
functions $h_1,\dots,h_k : U \to \{0,\dots,m-1\}$.

- `add(x)`: set bits $h_1(x),\dots,h_k(x)$ to 1.
- `contains(x)`: if **any** of those $k$ bits is 0, $x$ is **definitely absent**.
  If all are 1, $x$ is **probably present**.

There are **no false negatives**: a stored login always finds its bits set.
Standard Bloom filters **cannot delete**, because clearing a bit may erase other logins.

### 4.1 False-positive rate (derivation)
After inserting $n$ elements with $k$ hash functions each, the probability that a
specific bit is still 0 is

$$
\left(1 - \tfrac{1}{m}\right)^{kn} \approx e^{-kn/m}.
$$

A false positive for a non-member requires all $k$ probed bits to be 1:

$$
\boxed{\,p \approx \left(1 - e^{-kn/m}\right)^{k}\,}
$$

[Broder & Mitzenmacher 2004, §2.1; Mitzenmacher & Upfal §5.5.3]. This classic
formula slightly underestimates the exact rate for small $m$ [Bose et al. 2008].
The error is negligible at our sizes.

### 4.2 Optimal parameters
Minimizing $p$ over $k$ gives

$$
k^{*} = \frac{m}{n}\ln 2, \qquad p = 2^{-k^*} \approx 0.6185^{\,m/n}.
$$

Solving for $m$ given a target $p$:

$$
\boxed{\,m = -\frac{n \ln p}{(\ln 2)^2} \approx 1.44\, n \log_2 \frac{1}{p}\,}
$$

For $p = 1\%$: $m/n = 9.585$ bits per login and $k = 6.64 \to 7$.

### 4.3 Complexity

| Operation | Cost | Justification |
|---|---|---|
| Insert | $O(L + k)$ | hash once, then set $k$ bits (double hashing, §4.4) |
| Lookup | $O(L + k)$ worst case | at most $k$ bit tests |
| Lookup, miss (expected) | $\le 2$ bit tests | at $k^*$ about half of the bits are 1, so the first 0 bit arrives after a geometric number of probes with mean $\le 2$ |
| Build | $O(n(L + k))$ | $n$ inserts |
| Space | $m$ bits $= \Theta(n \log(1/p))$ | **independent of $L$**; the logins themselves are not stored |

### 4.4 Double hashing [Kirsch & Mitzenmacher 2006]
Computing $k$ independent hashes is unnecessary. With two hashes $h_a, h_b$,

$$
g_i(x) = \big(h_a(x) + i\cdot h_b(x)\big) \bmod m,\qquad i = 0,\dots,k-1,
$$

gives the same asymptotic FP rate. Each login is therefore hashed only once, at
$\Theta(L)$ cost.

### 4.5 Lower bound
Any structure that answers membership with FP rate $\varepsilon$ needs at least
$n \log_2(1/\varepsilon)$ bits [Carter et al. 1978]. A Bloom filter uses
$1.44\times$ this bound.

---

## 5. Cuckoo filter [Fan et al. 2014]

**How it works.** A table of $B$ buckets with $b$ slots each. Each slot holds an
$f$-bit **fingerprint** of a login, and 0 marks an empty slot. The filter uses
**partial-key cuckoo hashing**, so each login has two candidate buckets:

$$
i_1 = h(x) \bmod B, \qquad i_2 = i_1 \oplus h(\mathrm{fp}(x)).
$$

Because $i_2$ depends only on $i_1$ and the fingerprint, a fingerprint can be moved
to its other bucket **without the original login**. This matters because the filter
does not store the login.

- `add(x)`: if $i_1$ or $i_2$ has a free slot, store $\mathrm{fp}(x)$ there.
  Otherwise **evict** a random fingerprint from one of the two buckets, move it
  to *its* alternate bucket, and repeat up to MaxKicks times. If that still fails,
  the table is considered full.
- `contains(x)`: look for $\mathrm{fp}(x)$ in buckets $i_1$ and $i_2$ only.
- `remove(x)`: delete one copy of $\mathrm{fp}(x)$ from $i_1$ or $i_2$. Deletion is
  **supported**, unlike in a Bloom filter. It is safe only for logins that were
  actually inserted.

### 5.1 False-positive rate
A lookup compares against at most $2b$ stored fingerprints. Each one matches a
random non-member with probability $2^{-f}$:

$$
\varepsilon = 1 - \left(1 - 2^{-f}\right)^{2b} \;\le\; \boxed{\frac{2b}{2^{f}}}
\quad\Longrightarrow\quad
f \ge \left\lceil \log_2 \frac{1}{\varepsilon} + \log_2 (2b) \right\rceil .
$$

For $\varepsilon = 1\%$ and $b = 4$: $f = \lceil 9.64 \rceil = 10$ bits, which
gives an upper bound of $8/1024 = 0.78\%$.

### 5.2 Space
With load factor $\alpha$ (the fraction of occupied slots), the cost per login is

$$
\boxed{\,C = \frac{f}{\alpha} = \frac{\log_2(1/\varepsilon) + \log_2(2b)}{\alpha}\ \text{bits}\,}
$$

The achievable maximum load depends on the bucket size [Fan et al. 2014, §4]:
$b=1 \to 50\%$, $b=2 \to 84\%$, $b=4 \to 95\%$, $b=8 \to 98\%$.
With $b = 4$, $\alpha = 0.95$ and $\varepsilon = 1\%$: $C \approx 10.5$ bits per login.

### 5.3 Complexity

| Operation | Cost | Justification |
|---|---|---|
| Lookup | $O(L + b) = O(L)$ | hash once, then scan 2 buckets ($\le 2b$ slots), always |
| Delete | $O(L + b)$ | same two buckets |
| Insert (expected) | $O(L)$ amortized | constant expected number of evictions while $\alpha$ stays below the maximum load |
| Insert (worst) | $O(L + b \cdot \text{MaxKicks})$ | bounded by the eviction limit, then "full" |
| Space | $B \cdot b \cdot f = n f/\alpha$ bits $= \Theta(n \log(1/\varepsilon))$ | independent of $L$ |

### 5.4 Cuckoo vs. Bloom
- **Lookup cost:** cuckoo always probes 2 buckets (about 2 cache lines). A Bloom filter probes up to $k$ random bits (7 at $p = 1\%$).
- **Deletion:** cuckoo supports it; a standard Bloom filter does not.
- **Space:** $1.44\log_2(1/\varepsilon)$ (Bloom) vs. $(\log_2(1/\varepsilon)+3)/0.95$ (plain cuckoo, $b = 4$). The two are equal at $\log_2(1/\varepsilon) \approx 8$, i.e. $\varepsilon \approx 0.4\%$. Below that, the cuckoo filter is smaller. Fan et al. report a crossover of $\varepsilon < 3\%$ for their *semi-sorted* variant, which saves one more bit per entry.

---

## 6. Summary table (goes into the report)

| Structure | Build | Lookup (avg) | Lookup (worst) | Insert | Space | Errors | Delete |
|---|---|---|---|---|---|---|---|
| Linear search | $O(n)$ | $O(nL)$ | $O(nL)$ | $O(1)$ amort. | $\Theta(nL)$ | none | yes, $O(n)$ |
| Binary search | $O(L\,n\log n)$ | $O(L\log n)$ | $O(L\log n)$ | $O(n)$ | $\Theta(nL)$ | none | yes, $O(n)$ |
| Hash table (chaining) | $O(nL)$ exp. | $O(L)$ exp. | $O(nL)$ | $O(L)$ exp. amort. | $\Theta(nL)$ | none | yes, $O(L)$ exp. |
| Bloom filter | $O(n(L+k))$ | $O(L+k)$ | $O(L+k)$ | $O(L+k)$ | $m = 1.44\,n\log_2\frac1p$ bits | FP $\approx (1-e^{-kn/m})^k$ | **no** |
| Cuckoo filter | $O(nL)$ exp. | $O(L+b)$ | $O(L+b)$ | $O(L)$ exp., $\le$ MaxKicks | $n f/\alpha$ bits | FP $\le 2b/2^f$ | yes |

Neither filter ever produces a **false negative**. This matters for the login
checker: a false negative would allow a duplicate account, while a false positive
only tells a user that a free name is taken. In practice a filter screens requests
first, and only a "probably taken" answer is confirmed against the database.

---

## 7. Back-of-envelope: what $n = 10^9$ would cost

The table assumes CPython on a 64-bit machine. A login in our dataset has
$L \approx 14$ characters, and `sys.getsizeof` of a 14-character ASCII `str` is
63 bytes. A list adds an 8-byte pointer per element.

| Structure | Bytes per login | Total at $n = 10^9$ | Fits in 15.7 GB RAM? |
|---|---|---|---|
| List / sorted array | $\approx 63 + 8 = 71$ | $\approx 71$ GB | no |
| Hash table (chaining) | $\approx 71$ + slot array + bucket lists (measured in Phase 7) | $\gtrsim 100$ GB | no |
| Bloom filter, $p = 1\%$ | $9.585/8 = 1.2$ | **1.2 GB** ($k = 7$) | yes |
| Cuckoo filter, $\varepsilon = 1\%$ (theory, $f=10$, $\alpha=0.95$) | $10.5/8 = 1.3$ | **1.3 GB** | yes |
| Cuckoo filter (our Python storage: 16-bit slots, $\alpha \le 0.9$) | $\approx 17.8/8 = 2.2$ | $\approx 2.2$ GB | yes |

**Consequence for the experiments.** The exact structures cannot hold $10^9$
Python strings on this machine (15.7 GB RAM, Intel i7-11800H). We therefore
benchmark all five structures up to the largest $n$ that fits (target $10^7$,
decided in Phase 7) and extrapolate with the measured growth rates. The two
filters do not store the strings, so they can additionally be streamed to much
larger $n$.

---

## 8. Parameter choices for this project

| Structure | Parameters | Reason |
|---|---|---|
| Hash function (shared) | BLAKE2b [Aumasson et al. 2013] from `hashlib`, 128-bit digest split into two 64-bit values $(h_a, h_b)$ | deterministic across runs (Python's built-in `hash()` is randomized per process); C-implemented, so it is fast; good distribution. This is a hash *primitive*, not a data-structure library. |
| Hash table | initial capacity 8 (a power of two), max load 0.75, capacity doubles on resize | keeps $\alpha = \Theta(1)$; index is `h & (M-1)` |
| Bloom filter | $p = 0.01 \Rightarrow m = \lceil 9.585\,n \rceil$, $k = 7$; double hashing | standard textbook target |
| Cuckoo filter | $\varepsilon = 0.01 \Rightarrow f = 10$; $b = 4$; MaxKicks $= 500$; table sized for $\alpha \le 0.9$ | the paper's recommended $b$ and MaxKicks; load kept below the 95% maximum to leave headroom |

### Deviations from the paper (to be stated in the report)
1. **Alternate-bucket formula.** We use $i_2 = (h(\mathrm{fp}) - i_1) \bmod B$
   instead of $i_1 \oplus h(\mathrm{fp})$. It is still an involution, since
   $h - (h - i) = i$, so the alternate of $i_2$ is $i_1$. Unlike XOR, it works for
   **any** $B$, not only powers of two. The table can therefore be sized to exactly
   $\lceil n/(b\alpha)\rceil$ buckets instead of being rounded up to the next power
   of two, which can waste up to $2\times$ the memory.
2. **Victim stash.** When MaxKicks is exhausted, the last evicted fingerprint is
   kept in a one-entry stash, as in the authors' reference implementation, so that
   no stored login is lost. A second failure raises a "filter full" error.
3. **Storage width.** Python has no bit-packed arrays of arbitrary width, so an
   $f = 10$ bit fingerprint is stored in a 16-bit `array('H')` slot. The FP rate
   follows $f$; the memory follows the 16-bit slot width. Both numbers are reported.

---

## References

1. B. H. Bloom. 1970. Space/Time Trade-offs in Hash Coding with Allowable Errors. *Commun. ACM* 13, 7, 422–426. https://doi.org/10.1145/362686.362692
2. A. Broder and M. Mitzenmacher. 2004. Network Applications of Bloom Filters: A Survey. *Internet Mathematics* 1, 4, 485–509. https://doi.org/10.1080/15427951.2004.10129096
3. A. Kirsch and M. Mitzenmacher. 2006. Less Hashing, Same Performance: Building a Better Bloom Filter. In *ESA 2006*, LNCS 4168, 456–467. https://doi.org/10.1007/11841036_42
4. B. Fan, D. G. Andersen, M. Kaminsky, and M. D. Mitzenmacher. 2014. Cuckoo Filter: Practically Better Than Bloom. In *CoNEXT '14*, 75–88. https://doi.org/10.1145/2674005.2674994
5. R. Pagh and F. F. Rodler. 2004. Cuckoo Hashing. *J. Algorithms* 51, 2, 122–144. https://doi.org/10.1016/j.jalgor.2003.12.002
6. T. H. Cormen, C. E. Leiserson, R. L. Rivest, and C. Stein. 2022. *Introduction to Algorithms* (4th ed.). MIT Press.
7. D. E. Knuth. 1998. *The Art of Computer Programming, Vol. 3: Sorting and Searching* (2nd ed.). Addison-Wesley.
8. L. Carter, R. Floyd, J. Gill, G. Markowsky, and M. Wegman. 1978. Exact and Approximate Membership Testers. In *STOC '78*, 59–65. https://doi.org/10.1145/800133.804332
9. M. Mitzenmacher and E. Upfal. 2017. *Probability and Computing* (2nd ed.). Cambridge University Press.
10. P. Bose, H. Guo, E. Kranakis, A. Maheshwari, P. Morin, J. Morrison, M. Smid, and Y. Tang. 2008. On the False-Positive Rate of Bloom Filters. *Information Processing Letters* 108, 4, 210–213. https://doi.org/10.1016/j.ipl.2008.05.018
11. J.-P. Aumasson, S. Neves, Z. Wilcox-O'Hearn, and C. Winnerlein. 2013. BLAKE2: Simpler, Smaller, Fast as MD5. In *ACNS 2013*, LNCS 7954, 119–135. https://doi.org/10.1007/978-3-642-38980-1_8
