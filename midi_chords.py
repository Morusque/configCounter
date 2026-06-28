"""MIDI parsing + chord/sonority extraction.

Reimplements buildChordsFromNotes() from countConfigs.pde with three fixes:

  1. Hanging notes (NOTE_ON without NOTE_OFF) are dropped instead of poisoning
     every later chord (in the .pde they got stopTick == -1 and stayed active
     until end of file).
  2. Each sonority carries its DURATION, so transient legato overlaps contribute
     ~nothing to duration-weighted statistics instead of counting like a held chord.
  3. An optional minimum-duration filter (hysteresis) discards sonorities shorter
     than a threshold, treating brief overlaps as transitions rather than chords.
"""

from dataclasses import dataclass
from collections import defaultdict
import io
import mido


def _open_midi(path):
    """Load a MidiFile, transparently unwrapping RIFF/RMID containers.

    Some files (e.g. several Rachmaninov preludes here) are RMID: a standard
    MIDI stream wrapped in a RIFF 'RMID' chunk. mido only reads the bare SMF, so
    if the file starts with 'RIFF' we hand it the embedded data from 'MThd' on.
    """
    with open(path, "rb") as f:
        head = f.read(4)
    if head == b"RIFF":
        data = open(path, "rb").read()
        idx = data.find(b"MThd")
        if idx != -1:
            return mido.MidiFile(file=io.BytesIO(data[idx:]))
    return mido.MidiFile(path)

# General MIDI percussion is channel 10 in 1-based numbering == index 9 here.
# (Note: the original .pde skipped channel == 10, i.e. index 10 / 1-based ch 11,
#  which is the wrong channel for GM drums. We use the correct one.)
DRUM_CHANNEL = 9


@dataclass
class Note:
    start: int
    end: int
    pitch: int
    velocity: int
    channel: int

    @property
    def pc(self):
        return self.pitch % 12


@dataclass
class Sonority:
    """A maximal time interval over which the set of sounding notes is constant."""
    start: int
    end: int
    pitches: frozenset  # pitch classes (0-11) sounding during the interval

    @property
    def duration(self):
        return self.end - self.start


def parse_notes(path, skip_drums=True):
    """Return (notes, ticks_per_beat, n_hanging).

    Pairs NOTE_ON/NOTE_OFF per track using FIFO matching (the same convention as
    the .pde's closeNote, but scoped per track so cross-track unisons can't
    cross-match). Zero/negative-length notes and hanging notes are dropped.
    """
    mid = _open_midi(path)
    notes = []
    n_hanging = 0
    for track in mid.tracks:
        t = 0
        open_notes = defaultdict(list)  # (channel, pitch) -> [(start, velocity), ...]
        for msg in track:
            t += msg.time
            if msg.type == "note_on" and msg.velocity > 0:
                open_notes[(msg.channel, msg.note)].append((t, msg.velocity))
            elif msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
                stack = open_notes.get((msg.channel, msg.note))
                if stack:
                    start, vel = stack.pop(0)  # FIFO
                    if skip_drums and msg.channel == DRUM_CHANNEL:
                        continue
                    if t > start:
                        notes.append(Note(start, t, msg.note, vel, msg.channel))
        n_hanging += sum(len(v) for v in open_notes.values())
    notes.sort(key=lambda n: (n.start, n.pitch))
    return notes, mid.ticks_per_beat, n_hanging


def build_sonorities(notes, min_duration=0):
    """Sweep-line over note on/off events -> list[Sonority].

    Each Sonority spans a maximal interval during which the active note set is
    constant. At equal ticks, note-offs are processed before note-ons so a note
    ending exactly when another begins is NOT counted as simultaneous.

    min_duration: drop sonorities shorter than this many ticks (hysteresis).
    """
    events = []
    for n in notes:
        events.append((n.start, 1, n.pitch))
        events.append((n.end, -1, n.pitch))
    # (tick, delta): -1 sorts before +1, so offs precede ons at the same tick.
    events.sort(key=lambda e: (e[0], e[1]))

    sonorities = []
    active = defaultdict(int)  # pitch -> number of overlapping notes at that pitch
    last_tick = None
    for tick, delta, pitch in events:
        if last_tick is not None and tick != last_tick and active:
            pcset = frozenset(p % 12 for p in active)
            if pcset:
                sonorities.append(Sonority(last_tick, tick, pcset))
        active[pitch] += delta
        if active[pitch] <= 0:
            del active[pitch]
        last_tick = tick

    if min_duration > 0:
        sonorities = [s for s in sonorities if s.duration >= min_duration]
    return sonorities


def pc_duration_histogram(sonorities):
    """Duration-weighted pitch-class histogram (12 bins, in ticks)."""
    hist = [0] * 12
    for s in sonorities:
        for pc in s.pitches:
            hist[pc] += s.duration
    return hist


def bar_ticks(path, tpb):
    """Ticks per bar from the first time signature in the file (default 4/4)."""
    mid = _open_midi(path)
    for track in mid.tracks:
        for msg in track:
            if msg.type == "time_signature":
                return tpb * msg.numerator * 4 // msg.denominator
    return tpb * 4


def bar_masses(notes, bt):
    """List of per-bar {pitch_class: duration} dicts, notes clipped to each bar.

    This is the 'fixed time unit' view: every bar is one independent unit, so a
    repeated phrase is analyzed identically regardless of its context.
    """
    if not notes or bt <= 0:
        return []
    n_bars = max(n.end for n in notes) // bt + 1
    masses = [defaultdict(float) for _ in range(n_bars)]
    for n in notes:
        first, last = n.start // bt, (n.end - 1) // bt
        for b in range(first, last + 1):
            lo, hi = max(n.start, b * bt), min(n.end, (b + 1) * bt)
            if hi > lo:
                masses[b][n.pc] += hi - lo
    return masses
