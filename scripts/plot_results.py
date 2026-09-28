"""Plot the benchmark results and summarize them for the report.

Reads ``benchmark.csv``, ``tradeoff.csv`` and ``environment.json`` written by
``scripts.run_benchmarks`` and writes, into the same results folder:

* ``figures/*.pdf`` (for LaTeX) and ``figures/*.png`` (for the README);
* ``slopes.csv`` - growth rates fitted on log-log axes;
* ``summary.md`` - tables of the key numbers.

Usage (from the repository root)::

    python -m scripts.plot_results                          # results/
    python -m scripts.plot_results --results results/quick  # the --quick run

AI-assisted: generated with Claude Code (see README, "AI usage").
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # render to files; no display needed
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

# Validated categorical palette (fixed order) plus one marker per structure,
# so identity never depends on color alone.
STYLES = {
    "Linear search": ("#2a78d6", "o"),
    "Binary search": ("#eb6834", "s"),
    "Hash table": ("#1baf7a", "^"),
    "Bloom filter": ("#eda100", "D"),
    "Cuckoo filter": ("#e87ba4", "v"),
}
FILTERS = ["Bloom filter", "Cuckoo filter"]
INK, INK_SECONDARY, GRID, AXIS = "#0b0b0b", "#52514e", "#e1e0d9", "#c3c2b7"
FIT_MIN_N = 10_000  # below this, fixed per-call overhead hides the growth rate
EXTRAPOLATE_TO = 1_000_000_000

plt.rcParams.update({
    "figure.figsize": (6.4, 3.9),
    "savefig.dpi": 200,
    "savefig.bbox": "tight",
    "font.size": 9.5,
    "axes.titlesize": 10.5,
    "axes.titleweight": "bold",
    "axes.titlecolor": INK,
    "axes.labelcolor": INK_SECONDARY,
    "axes.edgecolor": AXIS,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.color": GRID,
    "grid.linewidth": 0.6,
    "xtick.color": INK_SECONDARY,
    "ytick.color": INK_SECONDARY,
    "text.color": INK,
    "legend.frameon": False,
    "legend.fontsize": 8.5,
    "lines.linewidth": 1.6,
    "lines.markersize": 6,
})


def read_csv(path: Path) -> list[dict[str, str]]:
    """Read a CSV file into a list of rows.

    Args:
        path: CSV file with a header line.

    Returns:
        One dictionary per row (values are strings).
    """
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def series(rows: list[dict[str, str]], name: str, field: str, mode: str | None = None):
    """Extract one structure's (n, value) points, sorted by n.

    Args:
        rows: ``benchmark.csv`` rows.
        name: Structure name.
        field: Column to read.
        mode: ``"stored"``, ``"streamed"`` or None for both.

    Returns:
        Tuple of numpy arrays ``(n, values)``.
    """
    points = sorted(
        (int(row["n"]), float(row[field]))
        for row in rows
        if row["structure"] == name and (mode is None or row["mode"] == mode) and row[field]
    )
    return np.array([p[0] for p in points]), np.array([p[1] for p in points])


def loglog_slope(n: np.ndarray, values: np.ndarray) -> float:
    """Least-squares slope of log(value) against log(n) for n >= FIT_MIN_N.

    A slope of 1 means linear growth, 0 means constant time.

    Args:
        n: Sizes.
        values: Measurements.

    Returns:
        The fitted exponent, or NaN with fewer than two points.
    """
    keep = n >= FIT_MIN_N
    if keep.sum() < 2:
        return float("nan")
    return float(np.polyfit(np.log10(n[keep]), np.log10(values[keep]), 1)[0])


def plot_series(ax, rows, name: str, field: str, label: str) -> None:
    """Draw stored points as a solid line and streamed points as hollow markers.

    Args:
        ax: Matplotlib axes.
        rows: ``benchmark.csv`` rows.
        name: Structure name.
        field: Column to plot.
        label: Legend label.

    Returns:
        None.
    """
    color, marker = STYLES[name]
    n, values = series(rows, name, field, "stored")
    ax.plot(n, values, color=color, marker=marker, markeredgecolor="white",
            markeredgewidth=0.8, label=label)
    n_stream, v_stream = series(rows, name, field, "streamed")
    if len(n_stream):
        ax.plot(np.r_[n[-1:], n_stream], np.r_[values[-1:], v_stream], color=color,
                linestyle="--", marker=marker, markerfacecolor="white", markevery=slice(1, None))


def guide_line(ax, n: np.ndarray, anchor_n: float, anchor_value: float, text: str) -> None:
    """Draw a thin gray reference line proportional to n through an anchor point.

    Args:
        ax: Matplotlib axes.
        n: Sizes spanning the line.
        anchor_n: Size the line passes through.
        anchor_value: Value at ``anchor_n``.
        text: Label at the right end.

    Returns:
        None.
    """
    values = anchor_value * n / anchor_n
    ax.plot(n, values, color=AXIS, linewidth=1.0, linestyle=":", zorder=0)
    ax.annotate(text, (n[-1], values[-1]), textcoords="offset points", xytext=(4, 0),
                color=INK_SECONDARY, fontsize=8, va="center")


def streamed_legend_entry() -> Line2D:
    """Legend handle explaining the hollow streamed markers."""
    return Line2D([], [], color=INK_SECONDARY, linestyle="--", marker="o",
                  markerfacecolor="white", label="streamed (filters only)")


def plot_lookup(rows, slopes: dict) -> plt.Figure:
    """Average lookup time vs. n for all five structures (log-log)."""
    fig, ax = plt.subplots()
    for name in STYLES:
        plot_series(ax, rows, name, "lookup_us", f"{name} (slope {slopes[name, 'lookup_us']:.2f})")
    n, linear = series(rows, "Linear search", "lookup_us", "stored")
    guide_line(ax, n, n[len(n) // 2], linear[len(n) // 2] * 3, "∝ n")
    ax.set(xscale="log", yscale="log", xlabel="Number of stored logins n",
           ylabel="Mean lookup time (µs)", title="Lookup time: 50% hits, 50% misses")
    handles = [*ax.get_legend_handles_labels()[0], streamed_legend_entry()]
    ax.legend(handles=handles, loc="upper left")
    return fig


def plot_build(rows, slopes: dict) -> plt.Figure:
    """Build time vs. n for all five structures (log-log)."""
    fig, ax = plt.subplots()
    for name in STYLES:
        plot_series(ax, rows, name, "build_s", f"{name} (slope {slopes[name, 'build_s']:.2f})")
    n, hash_build = series(rows, "Hash table", "build_s", "stored")
    guide_line(ax, n, n[-1], hash_build[-1] * 3, "∝ n")
    ax.set(xscale="log", yscale="log", xlabel="Number of stored logins n",
           ylabel="Build time (s)", title="Build time (bulk load of n logins)")
    handles = [*ax.get_legend_handles_labels()[0], streamed_legend_entry()]
    ax.legend(handles=handles, loc="upper left")
    return fig


def format_bytes(value: float, _position=None) -> str:
    """Tick formatter: 1e9 -> '1 GB'.

    Args:
        value: Number of bytes.

    Returns:
        Short human-readable size.
    """
    for unit, size in (("TB", 1e12), ("GB", 1e9), ("MB", 1e6), ("KB", 1e3)):
        if value >= size:
            return f"{value / size:.3g} {unit}"
    return f"{value:.3g} B"


def plot_memory(rows, ram_bytes: int | None) -> plt.Figure:
    """Total memory vs. n, extrapolated to one billion logins."""
    fig, ax = plt.subplots()
    endpoints: dict[str, float] = {}
    for name in STYLES:
        color, _ = STYLES[name]
        plot_series(ax, rows, name, "memory_bytes", name)
        n, per_login = series(rows, name, "bytes_per_login")
        endpoints[name] = per_login[-1] * EXTRAPOLATE_TO
        ax.plot([n[-1], EXTRAPOLATE_TO], [per_login[-1] * n[-1], endpoints[name]], color=color,
                linestyle=":", linewidth=1.2)
    labelled: list[float] = []
    for name, value in sorted(endpoints.items(), key=lambda item: item[1]):
        if any(abs(value / other - 1) < 0.05 for other in labelled):
            continue  # linear and binary search coincide; label once
        names = " / ".join(k.split()[0] for k, v in endpoints.items() if abs(v / value - 1) < 0.05)
        ax.annotate(f"{names}: {format_bytes(value)}", (EXTRAPOLATE_TO, value),
                    textcoords="offset points", xytext=(5, 0), va="center", fontsize=8,
                    color=INK_SECONDARY)
        labelled.append(value)
    if ram_bytes:
        ax.axhline(ram_bytes, color=INK_SECONDARY, linewidth=1.0, linestyle="-.")
        ax.annotate(f"RAM of test machine ({ram_bytes / 2**30:.0f} GiB)", (1e3, ram_bytes),
                    textcoords="offset points", xytext=(2, 4), fontsize=8, color=INK_SECONDARY)
    ax.set(xscale="log", yscale="log", xlabel="Number of stored logins n", ylabel="Memory",
           title="Memory use (dotted: extrapolated to n = 10⁹)")
    ax.yaxis.set_major_formatter(FuncFormatter(format_bytes))
    ax.legend(loc="lower right")
    return fig


def plot_fp_rate(rows) -> plt.Figure:
    """Measured vs. theoretical false-positive rate of both filters across n."""
    fig, ax = plt.subplots()
    theory_labels = {"Bloom filter": "theory (1 − e^(−kn/m))^k",
                     "Cuckoo filter": "expected 1 − (1 − 2^(−f))^(2bα)"}
    for name in FILTERS:
        color, marker = STYLES[name]
        n, measured = series(rows, name, "fp_measured")
        _, expected = series(rows, name, "fp_expected")
        ax.plot(n, measured * 100, color=color, marker=marker, markeredgecolor="white",
                label=f"{name}: measured")
        ax.plot(n, expected * 100, color=color, linestyle="--", linewidth=1.2,
                label=f"{name}: {theory_labels[name]}")
    _, bound = series(rows, "Cuckoo filter", "fp_bound")
    ax.axhline(bound[0] * 100, color=AXIS, linestyle=":", linewidth=1.0)
    ax.annotate("cuckoo bound 2b/2^f", (n[0], bound[0] * 100), textcoords="offset points",
                xytext=(2, 3), fontsize=8, color=INK_SECONDARY)
    ax.set(xscale="log", xlabel="Number of stored logins n", ylabel="False-positive rate (%)",
           title="False-positive rate (target 1%, 100,000 absent logins)")
    ax.set_ylim(0, max(1.3, ax.get_ylim()[1]))
    ax.legend(loc="lower right")
    return fig


def plot_binary_log(rows, cache_mb: float) -> plt.Figure:
    """Binary search: time vs. log2(n), and time per comparison vs. n.

    The algorithm makes ceil(log2(n + 1)) comparisons, so lookup time is a
    straight line in log2(n) while the data fits in the CPU cache. Beyond
    that, each comparison waits for main memory and the line bends upward.

    Args:
        rows: ``benchmark.csv`` rows.
        cache_mb: Last-level cache size of the test machine, in MB.

    Returns:
        Figure with two panels.
    """
    fig, (left, right) = plt.subplots(1, 2, figsize=(7.6, 3.3))
    color, marker = STYLES["Binary search"]
    n, lookup = series(rows, "Binary search", "lookup_us", "stored")
    _, per_login = series(rows, "Binary search", "bytes_per_login", "stored")
    cache_n = cache_mb * 1e6 / per_login[-1]  # logins whose data fills the cache
    in_cache = n <= cache_n
    x = np.log2(n)
    slope, intercept = np.polyfit(x[in_cache], lookup[in_cache], 1)
    r_squared = np.corrcoef(x[in_cache], lookup[in_cache])[0, 1] ** 2
    left.plot(x, lookup, color=color, marker=marker, markeredgecolor="white", linestyle="none",
              label="measured")
    left.plot(x, slope * x + intercept, color=INK_SECONDARY, linewidth=1.0,
              label=f"fit while in cache: {slope:.2f} µs/doubling (R² = {r_squared:.2f})")
    left.set(xlabel="log₂ n", ylabel="Mean lookup time (µs)", title="Lookup time vs. log₂ n")
    left.legend(loc="upper left")

    comparisons = np.ceil(np.log2(n + 1))
    right.plot(n, lookup * 1000 / comparisons, color=color, marker=marker,
               markeredgecolor="white")
    right.axvline(cache_n, color=INK_SECONDARY, linewidth=1.0, linestyle="-.")
    right.annotate(f"data exceeds {cache_mb:g} MB L3 cache", (cache_n, 0.97),
                   xycoords=("data", "axes fraction"), textcoords="offset points",
                   xytext=(-4, 0), ha="right", va="top", fontsize=8, color=INK_SECONDARY)
    right.set(xscale="log", xlabel="Number of stored logins n",
              ylabel="Time per comparison (ns)", title="Cost of one comparison")
    right.set_ylim(bottom=0)
    fig.tight_layout()
    return fig


def plot_tradeoff(tradeoff) -> plt.Figure:
    """Space vs. accuracy: bits per login against measured false-positive rate."""
    fig, ax = plt.subplots()
    bits = np.linspace(3, 20, 100)
    ax.plot(bits, 2.0**-bits, color=AXIS, linewidth=1.2, label="lower bound: ε = 2^(−bits)")
    variants = [
        ("Bloom filter", "bits_theory", "Bloom filter (m/n bits)", True),
        ("Cuckoo filter", "bits_theory", "Cuckoo filter, theory (f/α bits)", True),
        ("Cuckoo filter", "bits_actual", "Cuckoo filter, stored in 8/16-bit slots", False),
    ]
    for name, field, label, theory in variants:
        color, marker = STYLES[name]
        points = sorted((float(r[field]), float(r["fp_measured"])) for r in tradeoff
                        if r["structure"] == name)
        style = {"markeredgecolor": "white"} if theory else {
            "markerfacecolor": "white", "markeredgecolor": color, "linestyle": "none"}
        ax.plot([p[0] for p in points], [p[1] for p in points], color=color, marker=marker,
                label=label, **style)
    ax.set(yscale="log", xlabel="Bits per login", ylabel="Measured false-positive rate",
           title=f"Space vs. accuracy (n = {int(tradeoff[0]['n']):,})")
    ax.set_xlim(3, 20)
    ax.set_ylim(1e-4, 0.3)
    ax.legend(loc="upper right")
    return fig


def fitted_slopes(rows) -> dict[tuple[str, str], float]:
    """Log-log growth rates of lookup and build time for every structure.

    Args:
        rows: ``benchmark.csv`` rows.

    Returns:
        Mapping ``(structure, field) -> slope`` (stored and streamed points).
    """
    return {(name, field): loglog_slope(*series(rows, name, field))
            for name in STYLES for field in ("lookup_us", "build_s")}


def write_summary(path: Path, rows, slopes, env: dict) -> None:
    """Write markdown tables of the key numbers for the report and README.

    Args:
        path: Output file.
        rows: ``benchmark.csv`` rows.
        slopes: Output of :func:`fitted_slopes`.
        env: Contents of ``environment.json``.

    Returns:
        None.
    """
    largest = max(int(row["n"]) for row in rows if row["mode"] == "stored")
    lines = [
        f"Machine: {env.get('cpu')}, {(env.get('ram_bytes') or 0) / 2**30:.0f} GiB RAM, "
        f"{env.get('os')}, Python {env.get('python')}",
        "",
        f"## All five structures at n = {largest:,}",
        "",
        "| Structure | Build (s) | Lookup (µs) | Hit (µs) | Miss (µs) | Memory (MB) | Bytes/login "
        "| FP rate | Lookup slope | Build slope |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        if int(row["n"]) != largest or row["mode"] != "stored":
            continue
        name = row["structure"]
        fp_rate = f"{float(row['fp_measured']):.2%}" if row["fp_measured"] else "0 (exact)"
        lines.append(
            f"| {name} | {float(row['build_s']):.2f} | {float(row['lookup_us']):,.2f} "
            f"| {float(row['hit_us']):,.2f} | {float(row['miss_us']):,.2f} "
            f"| {int(row['memory_bytes']) / 1e6:,.1f} | {float(row['bytes_per_login']):.1f} "
            f"| {fp_rate} | {slopes[name, 'lookup_us']:.2f} | {slopes[name, 'build_s']:.2f} |"
        )
    streamed = [row for row in rows if row["mode"] == "streamed"]
    if streamed:
        lines += [
            "", "## Filters streamed beyond the stored sizes", "",
            "| Structure | n | Build (s) | Lookup (µs) | Memory (MB) | Bytes/login | FP rate |",
            "|---|---|---|---|---|---|---|",
        ]
        lines += [
            f"| {row['structure']} | {int(row['n']):,} | {float(row['build_s']):,.0f} "
            f"| {float(row['lookup_us']):.2f} | {int(row['memory_bytes']) / 1e6:,.1f} "
            f"| {float(row['bytes_per_login']):.2f} | {float(row['fp_measured']):.2%} |"
            for row in streamed
        ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    """Create all figures, the slope table and the summary.

    Returns:
        None.
    """
    parser = argparse.ArgumentParser(description="Plot the benchmark results.")
    parser.add_argument("--results", type=Path, default=Path("results"), help="results folder")
    parser.add_argument("--cache-mb", type=float, default=24.0,
                        help="last-level CPU cache size in MB (i7-11800H: 24)")
    args = parser.parse_args()
    results = args.results
    rows = read_csv(results / "benchmark.csv")
    tradeoff = read_csv(results / "tradeoff.csv")
    env = json.loads((results / "environment.json").read_text(encoding="utf-8"))
    slopes = fitted_slopes(rows)

    figures_dir = results / "figures"
    figures_dir.mkdir(exist_ok=True)
    figures = {
        "lookup_time": plot_lookup(rows, slopes),
        "build_time": plot_build(rows, slopes),
        "memory": plot_memory(rows, env.get("ram_bytes")),
        "false_positive_rate": plot_fp_rate(rows),
        "binary_search_log": plot_binary_log(rows, args.cache_mb),
        "space_accuracy_tradeoff": plot_tradeoff(tradeoff),
    }
    for name, figure in figures.items():
        for extension in ("pdf", "png"):
            figure.savefig(figures_dir / f"{name}.{extension}")
        plt.close(figure)

    with open(results / "slopes.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["structure", "metric", "loglog_slope", "fit_min_n"])
        for (name, field), slope in slopes.items():
            writer.writerow([name, field, round(slope, 4), FIT_MIN_N])
    write_summary(results / "summary.md", rows, slopes, env)
    print(f"Wrote {len(figures)} figures to {figures_dir}/, slopes.csv and summary.md")


if __name__ == "__main__":
    main()
