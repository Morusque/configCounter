"""Per-file modal analysis -> CSV, grouped by composer (parent folder name).

Usage:
  python analyze.py                         # whole data/ tree -> metrics.csv
  python analyze.py --composers Haydn Rachmaninov --out test_metrics.csv
  python analyze.py --min-dur-frac 0.125    # hysteresis: drop sonorities < 1/8 beat
"""
import argparse
import csv
from functools import lru_cache
from pathlib import Path

from modes import (MODE_BITS, MODE_SIZE, N_MODES, FAMILIES, FAMILY_INDICES,
                   pcs_to_bits)
from midi_chords import parse_notes, build_sonorities

DATA = Path(__file__).parent / "data"

# Bitmask of all modes belonging to each family, for quick "fits some X" tests.
_FAMILY_MASKS = {f: [MODE_BITS[i] for i in idx] for f, idx in FAMILY_INDICES.items()}


@lru_cache(maxsize=None)
def _facts(pc_bits):
    """Pure function of a sonority's pitch-class mask -> reusable facts.

    Memoized across the whole corpus: there are only a few hundred distinct
    pitch-class sets in practice, so the 57-mode loop runs that many times total
    instead of once per sonority.
    """
    compat = 0          # how many of the 57 modes contain this sonority
    pinned = False      # does it spell *exactly* a full scale (chord == mode)?
    for m, mbits in enumerate(MODE_BITS):
        if pc_bits & ~mbits == 0:        # sonority ⊆ mode
            compat += 1
            if pc_bits == mbits:
                pinned = True
    fam_fits = {}
    for f, masks in _FAMILY_MASKS.items():
        fam_fits[f] = any(pc_bits & ~mb == 0 for mb in masks)
    return compat, pinned, fam_fits


def analyze_file(path):
    notes, tpb, hanging = parse_notes(str(path))
    son = build_sonorities(notes, min_duration=int(round(MIN_DUR_FRAC * tpb)))
    total = sum(s.duration for s in son)
    if total == 0:
        return None

    w_compat = 0.0          # duration-weighted sum of compatible-mode counts
    w_pinned = 0.0
    fam_cov = {f: 0.0 for f in FAMILIES}
    for s in son:
        compat, pinned, fam_fits = _facts(pcs_to_bits(s.pitches))
        d = s.duration
        w_compat += compat * d
        if pinned:
            w_pinned += d
        for f, fits in fam_fits.items():
            if fits:
                fam_cov[f] += d

    row = {
        "composer": path.parent.name,
        "file": path.name,
        "tpb": tpb,
        "n_notes": len(notes),
        "n_sonorities": len(son),
        "dur_beats": round(total / tpb, 1),
        "hanging": hanging,
        "avg_modes_compat": round(w_compat / total, 3),
        "pinned_frac": round(w_pinned / total, 4),
    }
    for f in FAMILIES:
        row[f"cov_{f}"] = round(fam_cov[f] / total, 4)
    return row


def iter_midis(composers=None):
    for p in DATA.rglob("*"):
        if p.suffix.lower() == ".mid":
            if composers is None or p.parent.name in composers:
                yield p


def main():
    global MIN_DUR_FRAC
    ap = argparse.ArgumentParser()
    ap.add_argument("--composers", nargs="*", default=None)
    ap.add_argument("--out", default="metrics.csv")
    ap.add_argument("--min-dur-frac", type=float, default=0.0,
                    help="hysteresis threshold as a fraction of a beat")
    args = ap.parse_args()
    MIN_DUR_FRAC = args.min_dur_frac

    files = sorted(iter_midis(args.composers))
    rows, errors = [], 0
    for i, path in enumerate(files, 1):
        try:
            r = analyze_file(path)
            if r:
                rows.append(r)
        except Exception as e:
            errors += 1
            print(f"  ! {path.name}: {type(e).__name__}: {e}")
        if i % 100 == 0:
            print(f"  ...{i}/{len(files)}")

    if not rows:
        print("no rows produced")
        return
    cols = list(rows[0].keys())
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    print(f"\nwrote {len(rows)} rows ({errors} errors) -> {args.out}")
    print(f"cache: {_facts.cache_info()}")

    # quick per-composer summary of the headline metric
    by = {}
    for r in rows:
        by.setdefault(r["composer"], []).append(r)
    print("\ncomposer            files  avg_modes_compat  cov_Major  cov_HarmMinor  cov_WholeTone")
    for comp in sorted(by):
        rs = by[comp]
        n = len(rs)
        amc = sum(x["avg_modes_compat"] for x in rs) / n
        cmaj = sum(x["cov_Major"] for x in rs) / n
        chm = sum(x["cov_HarmonicMinor"] for x in rs) / n
        cwt = sum(x["cov_WholeTone"] for x in rs) / n
        print(f"  {comp:<18}{n:>5}{amc:>17.2f}{cmaj:>11.3f}{chm:>15.3f}{cwt:>14.3f}")


if __name__ == "__main__":
    MIN_DUR_FRAC = 0.0
    main()
