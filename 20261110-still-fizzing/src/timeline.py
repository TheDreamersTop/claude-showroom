"""Single source of truth for timing. Music is 92 bpm, 4/4. Bar 0 starts at T0."""
BPM = 92
BEAT = 60.0 / BPM
BAR = 4 * BEAT
T0 = 1.40          # first downbeat (cut to 1958), after the cold-open pop in black


def bar(b, beat=0.0):
    return T0 + b * BAR + beat * BEAT


# era -> (first bar, n bars)
ERAS = [('1958', 0, 2), ('1966', 2, 3), ('1974', 5, 2), ('1987', 7, 2), ('2026', 9, 5), ('hero', 14, 2), ('pop', 16, 1), ('end', 17, 2)]
END = bar(19) + 1.6   # tail after the final chord
