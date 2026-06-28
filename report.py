"""Whole-corpus breakdown across all 57 modes individually (no family merging),
plus bar-chart PNGs. Reproduces the original .pde counters, aggregated over the
entire data/ tree:

  present[n] = chords compatible with mode n     (== configsCount)
  sure[n]    = chords that spell mode n exactly   (== sureConfigsCount)

Usage:
  python report.py                       # whole corpus -> modes_corpus.csv + graphs
  python report.py --weighted            # weight counts by sonority duration
  python report.py --composers Bach Mozart   # restrict to some folders (still one aggregate)
  python report.py --min-dur-frac 0.125  # hysteresis: drop sonorities < 1/8 beat
"""
import argparse
import csv
from functools import lru_cache
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

from modes import (MODE_BITS, MODE_NAMES, MODE_FAMILIES, FAMILIES, N_MODES,
                   pcs_to_bits, mode_axis_label, mode_example)
from midi_chords import parse_notes, build_sonorities, bar_ticks, bar_masses

HERE = Path(__file__).parent
DATA = HERE / "data"
GRAPHS = HERE / "graphs"

FAMILY_COLORS = {f: plt.get_cmap("tab10")(i) for i, f in enumerate(FAMILIES)}
BAR_COLORS = [FAMILY_COLORS[MODE_FAMILIES[i]] for i in range(N_MODES)]


@lru_cache(maxsize=None)
def mode_hits(pc_bits):
    """(present[57] tuple, exact_mode_index or -1) for a sonority's PC mask."""
    present = tuple((pc_bits & ~mb) == 0 for mb in MODE_BITS)
    exact = next((i for i, mb in enumerate(MODE_BITS) if pc_bits == mb), -1)
    return present, exact


def iter_midis(selected):
    for p in sorted(DATA.rglob("*.mid")):
        if selected is None or p.parent.name in selected:
            yield p


def bar_hits(mass, tol):
    """For one bar's {pc: duration}: (present[57] bools, exact_index or -1).

    present[n] is True when mode n covers >= (1-tol) of the bar's duration-mass
    (tol=0 -> the mode must contain ALL of the bar's notes). exact when the bar's
    pitch-class set equals a mode exactly.
    """
    total = sum(mass.values())
    if total == 0:
        return None
    present = []
    for mb in MODE_BITS:
        inside = sum(d for pc, d in mass.items() if (mb >> pc) & 1)
        present.append(inside / total >= 1 - tol)
    bits = pcs_to_bits(mass.keys())
    exact = next((i for i, mb in enumerate(MODE_BITS) if bits == mb), -1)
    return tuple(present), exact


def aggregate(files, weighted, min_dur_frac, unit, tol):
    """Sum present/sure counts over all files into one corpus-wide profile.

    unit='sonority': every constant-active-note interval is a unit (weighted by
                     duration if --weighted), compatibility = mode contains it.
    unit='bar':      every bar is one equal unit (fair proportions), and a mode
                     is 'present' if it covers >= (1-tol) of the bar's mass.
    """
    present = [0.0] * N_MODES
    sure = [0.0] * N_MODES
    total = 0.0
    used = errors = 0
    files = list(files)
    for i, path in enumerate(files, 1):
        try:
            notes, tpb, _ = parse_notes(str(path))
        except Exception as e:
            errors += 1
            print(f"  ! {path.name}: {type(e).__name__}: {e}")
            continue
        if not notes:
            continue

        if unit == "bar":
            units = []
            for mass in bar_masses(notes, bar_ticks(str(path), tpb)):
                hit = bar_hits(mass, tol)
                if hit:
                    units.append(hit)  # (present_bools, exact)
        else:
            son = build_sonorities(notes, min_duration=int(round(min_dur_frac * tpb)))
            units = [(*mode_hits(pcs_to_bits(s.pitches)),
                      s.duration if weighted else 1) for s in son]

        if not units:
            continue
        used += 1
        for u in units:
            pres, exact = u[0], u[1]
            w = u[2] if unit != "bar" else 1  # bars are equal-weight units
            total += w
            for k in range(N_MODES):
                if pres[k]:
                    present[k] += w
            if exact >= 0:
                sure[exact] += w
        if i % 200 == 0:
            print(f"  ...{i}/{len(files)}")
    return present, sure, total, used, errors


def plot_profile(values, title, out_png, ylabel):
    fig, ax = plt.subplots(figsize=(16, 5))
    ax.bar(range(N_MODES), values, color=BAR_COLORS)
    ax.set_xticks(range(N_MODES))
    ax.set_xticklabels([mode_axis_label(i) for i in range(N_MODES)],
                       rotation=90, fontsize=6)
    ax.set_xlim(-0.6, N_MODES - 0.4)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend(handles=[Patch(color=FAMILY_COLORS[f], label=f) for f in FAMILIES],
              fontsize=8, ncol=7, loc="upper center", bbox_to_anchor=(0.5, -0.18))
    fig.tight_layout()
    fig.savefig(out_png, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {out_png}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--composers", nargs="*", default=None,
                    help="restrict to these folder names (default: whole corpus)")
    ap.add_argument("--weighted", action="store_true",
                    help="weight counts by sonority duration instead of raw count")
    ap.add_argument("--min-dur-frac", type=float, default=0.0,
                    help="hysteresis: drop sonorities shorter than this many beats")
    ap.add_argument("--normalize", action="store_true",
                    help="scale each profile so it sums to 1 (compare shape, not level)")
    ap.add_argument("--unit", choices=["sonority", "bar"], default="sonority",
                    help="counting unit: per-sonority (default) or per-bar (fixed)")
    ap.add_argument("--tol", type=float, default=0.0,
                    help="bar unit only: mass fraction allowed outside a mode (default 0)")
    args = ap.parse_args()

    base = "corpus" if not args.composers else "+".join(sorted(args.composers))
    label = base if args.unit == "sonority" else f"{base}_bar"
    present, sure, total, used, errors = aggregate(
        iter_midis(args.composers), args.weighted, args.min_dur_frac,
        args.unit, args.tol)
    if total == 0:
        print("no units found")
        return
    unit_word = "bars" if args.unit == "bar" else "chords"
    print(f"\n{label}: files={used}  {unit_word}={int(total)}  errors={errors}")

    present_frac = [v / total for v in present]
    sure_frac = [v / total for v in sure]
    if args.normalize:
        sp, ss = sum(present_frac) or 1, sum(sure_frac) or 1
        present_frac = [v / sp for v in present_frac]
        sure_frac = [v / ss for v in sure_frac]

    # Tidy CSV: one row per mode.
    out_csv = HERE / f"modes_{label}.csv"
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["mode_index", "mode_name", "example", "family",
                    "present_count", "present_frac", "sure_count", "sure_frac"])
        for i in range(N_MODES):
            w.writerow([i, MODE_NAMES[i], mode_example(i), MODE_FAMILIES[i],
                        int(present[i]), round(present_frac[i], 6),
                        int(sure[i]), round(sure_frac[i], 6)])
    print(f"wrote {out_csv}")

    GRAPHS.mkdir(exist_ok=True)
    if args.unit == "bar":
        unit = "fraction of bars"
    else:
        unit = "duration fraction" if args.weighted else "fraction of chords"
    suffix = "_norm" if args.normalize else ""
    plot_profile(present_frac, f"{label} - modes present ({unit})",
                 GRAPHS / f"{label}_present{suffix}.png", f"{unit} compatible")
    if any(sure_frac):
        plot_profile(sure_frac, f"{label} - modes spelled exactly ({unit})",
                     GRAPHS / f"{label}_sure{suffix}.png", f"{unit} exact match")


if __name__ == "__main__":
    main()
