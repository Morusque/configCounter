"""Single-track inspector: detect a best-fit mode per bar and draw a piano-roll
with each bar shaded by its detected mode and every out-of-mode note highlighted.

This is a validation tool: compare the shaded modes / red notes against what you
hear. If the red notes are genuine passing tones/ornaments, the detection is
sound; if they are structural, the detected mode is wrong.

Detection (best-fit, not mere compatibility):
  For each bar, take the duration-weighted pitch-class mass. Keep the modes that
  cover >= (1 - tol) of that mass; among them pick the *tightest* (fewest notes),
  breaking ties toward common tonal scales. -> exactly one mode per bar.

Usage:
  python inspect_track.py --file "data/Clementi/sonatina op36 n1 1mov.mid"
  python inspect_track.py --file PATH --bars 0 32 --tol 0.05
"""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

from modes import (MODE_BITS, MODE_FAMILIES, FAMILIES, N_MODES, mode_example)
from midi_chords import parse_notes, bar_ticks, bar_masses

HERE = Path(__file__).parent
GRAPHS = HERE / "graphs"
PCNAME = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

FAMILY_COLORS = {f: plt.get_cmap("tab10")(i) for i, f in enumerate(FAMILIES)}
# Preference order when several modes fit equally: common tonal scales first.
FAM_RANK = {"Major": 0, "HarmonicMinor": 1, "MelodicMajor": 2, "HarmonicMajor": 3,
            "HalfWholeDim": 4, "Augmented": 5, "WholeTone": 6}


def coverage(pc_mass, total, mode_index):
    mb = MODE_BITS[mode_index]
    inside = sum(m for pc, m in pc_mass.items() if (mb >> pc) & 1)
    return inside / total if total else 0.0


def rank_modes(pc_mass, tol):
    """Modes that cover >= (1-tol) of the bar's mass, best first.

    Ordered by common-family-first, then highest coverage, then lowest index.
    Note: NO 'fewest notes' bias -- that wrongly favours exotic 6-note scales on
    sparse bars. If nothing meets the threshold, return the single best-covering
    mode (the bar is genuinely chromatic).
    """
    total = sum(pc_mass.values())
    if total == 0:
        return [], 0.0
    scored = []
    for i in range(N_MODES):
        cov = coverage(pc_mass, total, i)
        scored.append((FAM_RANK[MODE_FAMILIES[i]], -cov, i, cov))
    scored.sort()
    meeting = [(i, cov) for fr, ncov, i, cov in scored if cov >= 1 - tol]
    if meeting:
        return meeting, total
    best = scored[0]
    return [(best[2], best[3])], total


def detect_sticky(bar_mass, tol):
    """Per-bar best-fit with temporal continuity: keep the previous bar's mode
    while it still covers >= (1-tol) of the current bar; only switch when forced."""
    detected = []
    prev = None
    for mass in bar_mass:
        total = sum(mass.values())
        if total == 0:
            detected.append(None)
            continue
        cands, _ = rank_modes(mass, tol)
        cand_ids = {i for i, _ in cands}
        if prev is not None and prev in cand_ids:
            chosen = prev
        else:
            chosen = cands[0][0]
        prev = chosen
        detected.append((chosen, coverage(mass, total, chosen)))
    return detected


def detect_independent(bar_mass, tol):
    """Per-bar best-fit with NO continuity: each bar judged on its own notes.

    Avoids the path-dependence of the sticky rule (a repeated phrase is labeled
    the same wherever it occurs), at the cost of more flicker between neighbouring
    keys that share notes."""
    detected = []
    for mass in bar_mass:
        total = sum(mass.values())
        if total == 0:
            detected.append(None)
            continue
        cands, _ = rank_modes(mass, tol)
        detected.append((cands[0][0], coverage(mass, total, cands[0][0])))
    return detected


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--tol", type=float, default=0.05,
                    help="fraction of bar mass allowed outside the mode (default 0.05)")
    ap.add_argument("--bars", type=int, nargs=2, default=None,
                    metavar=("START", "END"), help="bar range to draw (default: first 32)")
    ap.add_argument("--independent", action="store_true",
                    help="judge each bar on its own (no sticky carry-over from previous bars)")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    path = args.file
    notes, tpb, hanging = parse_notes(path)
    if not notes:
        print("no notes")
        return
    bt = bar_ticks(path, tpb)
    bar_mass = bar_masses(notes, bt)
    n_bars = len(bar_mass)
    b0, b1 = (args.bars if args.bars else (0, min(32, n_bars)))

    detect = detect_independent if args.independent else detect_sticky
    detected = detect(bar_mass, args.tol)  # per bar: (mode_index, coverage) or None

    # ---- draw ----
    fig, ax = plt.subplots(figsize=(min(2 + (b1 - b0) * 0.7, 30), 7))
    pitches = [n.pitch for n in notes if b0 * bt <= n.start < b1 * bt]
    ymin, ymax = (min(pitches) - 2, max(pitches) + 2) if pitches else (48, 84)

    used_families = set()
    for b in range(b0, b1):
        res = detected[b]
        x0, x1 = b * bt, (b + 1) * bt
        if res:
            mi, cov = res
            fam = MODE_FAMILIES[mi]
            used_families.add(fam)
            ax.axvspan(x0, x1, color=FAMILY_COLORS[fam], alpha=0.18, zorder=0)
            ax.text((x0 + x1) / 2, ymax - 0.5, f"{mode_example(mi)}\n#{mi} · {cov*100:.0f}%",
                    ha="center", va="top", fontsize=7, rotation=0)
        ax.axvline(x0, color="0.7", linewidth=0.6, zorder=1)
    ax.axvline(b1 * bt, color="0.7", linewidth=0.6, zorder=1)

    n_red = 0
    for n in notes:
        if n.end <= b0 * bt or n.start >= b1 * bt:
            continue
        b = min(max(n.start // bt, 0), n_bars - 1)
        res = detected[b]
        in_mode = res is not None and ((MODE_BITS[res[0]] >> n.pc) & 1)
        if in_mode:
            ax.plot([n.start, n.end], [n.pitch, n.pitch], color="0.2",
                    linewidth=3, solid_capstyle="butt", zorder=2)
        else:
            ax.plot([n.start, n.end], [n.pitch, n.pitch], color="crimson",
                    linewidth=4, solid_capstyle="butt", zorder=3)
            n_red += 1

    ax.set_ylim(ymin, ymax)
    ax.set_xlim(b0 * bt, b1 * bt)
    ax.set_xticks([b * bt for b in range(b0, b1 + 1)])
    ax.set_xticklabels([str(b + 1) for b in range(b0, b1 + 1)], fontsize=7)
    ax.set_xlabel("bar")
    ax.set_ylabel("MIDI pitch")
    yticks = [p for p in range(ymin, ymax + 1) if p % 12 == 0]
    ax.set_yticks(yticks)
    ax.set_yticklabels([f"{PCNAME[p%12]}{p//12 - 1}" for p in yticks])
    ax.set_title(f"{Path(path).name}  -  bars {b0+1}-{b1}  "
                 f"(red = out-of-mode notes, tol={args.tol})")
    handles = [Patch(color=FAMILY_COLORS[f], alpha=0.5, label=f) for f in FAMILIES
               if f in used_families]
    handles.append(plt.Line2D([], [], color="crimson", lw=4, label="out-of-mode note"))
    ax.legend(handles=handles, fontsize=8, ncol=len(handles),
              loc="upper center", bbox_to_anchor=(0.5, -0.09))

    GRAPHS.mkdir(exist_ok=True)
    out = args.out or str(GRAPHS / (Path(path).stem + "_inspect.png"))
    fig.tight_layout()
    fig.savefig(out, dpi=130, bbox_inches="tight")
    plt.close(fig)

    total_bars = b1 - b0
    red_frac = n_red / sum(1 for n in notes if b0*bt <= n.start < b1*bt) if notes else 0
    print(f"file: {Path(path).name}  tpb={tpb} bar_ticks={bt} bars={n_bars} hanging={hanging}")
    print(f"drawn bars {b0+1}-{b1}: {n_red} out-of-mode notes ({red_frac*100:.1f}% of notes)")
    # quick text timeline
    print("bar : detected mode (coverage)")
    for b in range(b0, b1):
        res = detected[b]
        if res:
            print(f"  {b+1:>3} : #{res[0]:<2} {mode_example(res[0]):<18} {res[1]*100:.0f}%")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
