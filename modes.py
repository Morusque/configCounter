"""The 57 "modes" = pitch-class templates, ported from countConfigs.pde.

Each family is generated as the 12 (or fewer, for symmetric scales) left-rotations
of a base pitch-class set, matching the ordering in the original Processing sketch.
A rotation by k maps mask[i] -> base[(i + k) % 12], which reproduces the .pde rows
exactly (verified against the first rows of each family).
"""

# Base pitch-class sets (semitones from an arbitrary 0), and how many rotations the
# .pde stores for each. Symmetric scales repeat, so fewer distinct rotations.
_FAMILIES = [
    ("Major",          {0, 2, 4, 5, 7, 9, 11}, 12),
    ("MelodicMajor",   {0, 2, 4, 5, 7, 8, 10}, 12),
    ("HarmonicMajor",  {0, 2, 4, 5, 7, 8, 11}, 12),
    ("HarmonicMinor",  {0, 2, 3, 5, 7, 8, 11}, 12),
    ("Augmented",      {0, 3, 4, 7, 8, 11},     4),
    ("HalfWholeDim",   {0, 1, 3, 4, 6, 7, 9, 10}, 3),
    ("WholeTone",      {0, 2, 4, 6, 8, 10},     2),
]


def _rotate(base_set, k):
    """Boolean[12]: present[i] is True when base contains (i + k) % 12."""
    return tuple(((i + k) % 12) in base_set for i in range(12))


def _build():
    modes = []      # list[tuple[bool*12]]
    names = []      # human-readable label, e.g. "HarmonicMinor+6"
    families = []   # family name per index
    for fam, base, n_rot in _FAMILIES:
        for k in range(n_rot):
            modes.append(_rotate(base, k))
            names.append(f"{fam}+{k}")
            families.append(fam)
    return modes, names, families


MODES, MODE_NAMES, MODE_FAMILIES = _build()
N_MODES = len(MODES)  # 57

# Precompute the integer size (number of pitch classes) of each mode.
MODE_SIZE = [sum(m) for m in MODES]

# 12-bit mask per mode (bit i set when pitch class i is allowed). Lets the hot
# compatibility test become a single bitwise op:  (pc_bits & ~mode_bits) == 0.
MODE_BITS = [sum(1 << i for i in range(12) if m[i]) for m in MODES]

# Family name -> list of mode indices, and the ordered list of distinct families.
FAMILIES = []
FAMILY_INDICES = {}
for _i, _f in enumerate(MODE_FAMILIES):
    if _f not in FAMILY_INDICES:
        FAMILY_INDICES[_f] = []
        FAMILIES.append(_f)
    FAMILY_INDICES[_f].append(_i)

assert N_MODES == 57, f"expected 57 modes, got {N_MODES}"


def pcs_to_bits(pcset):
    """Pack an iterable of pitch classes into a 12-bit mask."""
    b = 0
    for pc in pcset:
        b |= 1 << pc
    return b


def is_compatible(pcset, mode):
    """True if every pitch class present in pcset is allowed by mode."""
    for pc in pcset:
        if not mode[pc]:
            return False
    return True


# ---- human-readable example names -----------------------------------------
# Each mode is one transposition of its family's base scale (defined rooted on
# C). A left-rotation by k transposes the pitch classes DOWN by k semitones, so
# the example tonic is (12 - k) % 12. The example is just ONE realization (e.g.
# "C Major"); the same pitch-class set is also D Dorian, etc.
KEYNAME = ["C", "Db", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
FAMILY_SHORT = {"Major": "Maj", "MelodicMajor": "MelMaj", "HarmonicMajor": "HarMaj",
                "HarmonicMinor": "HarMin", "Augmented": "Aug",
                "HalfWholeDim": "HWDim", "WholeTone": "WT"}


def mode_root(i):
    """Pitch class of the example tonic for mode i."""
    fam = MODE_FAMILIES[i]
    rot = i - FAMILY_INDICES[fam][0]
    return (12 - rot) % 12


def mode_example(i):
    """Full example name, e.g. 'C Major', 'Ab Major', 'C HarmonicMinor'."""
    return f"{KEYNAME[mode_root(i)]} {MODE_FAMILIES[i]}"


def mode_axis_label(i):
    """Compact label for graph axes, e.g. '4  Ab Maj'."""
    return f"{i}  {KEYNAME[mode_root(i)]} {FAMILY_SHORT[MODE_FAMILIES[i]]}"
