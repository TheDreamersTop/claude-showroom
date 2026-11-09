"""Conway's Game of Life (B3/S23) on a bounded grid, plus a pattern library."""
import numpy as np

PATTERNS = {
    "block": ["OO", "OO"],
    "beehive": [".OO.", "O..O", ".OO."],
    "loaf": [".OO.", "O..O", ".O.O", "..O."],
    "boat": ["OO.", "O.O", ".O."],
    "tub": [".O.", "O.O", ".O."],
    "ship": ["OO.", "O.O", ".OO"],
    "pond": [".OO.", "O..O", "O..O", ".OO."],
    "blinker": ["OOO"],
    "toad": [".OOO", "OOO."],
    "beacon": ["OO..", "OO..", "..OO", "..OO"],
    "glider": [".O.", "..O", "OOO"],          # travels +x +y (down-right)
    "lwss": [".O..O", "O....", "O...O", "OOOO."],  # travels -x
    "eater": ["OO..", "O.O.", "..O.", "..OO"],
    "rpent": [".OO", "OO.", ".O."],
    "pulsar": [
        "..OOO...OOO..",
        ".............",
        "O....O.O....O",
        "O....O.O....O",
        "O....O.O....O",
        "..OOO...OOO..",
        ".............",
        "..OOO...OOO..",
        "O....O.O....O",
        "O....O.O....O",
        "O....O.O....O",
        ".............",
        "..OOO...OOO..",
    ],
    "pentadecathlon": ["..O....O..", "OO.OOOO.OO", "..O....O.."],
    "gosper": [
        "........................O...........",
        "......................O.O...........",
        "............OO......OO............OO",
        "...........O...O....OO............OO",
        "OO........O.....O...OO..............",
        "OO........O...O.OO....O.O...........",
        "..........O.....O.......O...........",
        "...........O...O....................",
        "............OO......................",
    ],
}


def pattern(name, flip_x=False, flip_y=False, rot=0):
    rows = PATTERNS[name]
    a = np.array([[c == "O" for c in r] for r in rows], dtype=bool)
    if flip_x:
        a = a[:, ::-1]
    if flip_y:
        a = a[::-1, :]
    return np.rot90(a, rot)


class World:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.cells = np.zeros((h, w), dtype=bool)
        self.age = np.zeros((h, w), dtype=np.float32)
        self.gen = 0

    def place(self, name, x, y, **kw):
        p = pattern(name, **kw)
        ph, pw = p.shape
        self.cells[y:y + ph, x:x + pw] |= p
        return self

    def step(self):
        c = self.cells.astype(np.uint8)
        n = np.zeros_like(c)
        n[1:, :] += c[:-1, :]; n[:-1, :] += c[1:, :]
        n[:, 1:] += c[:, :-1]; n[:, :-1] += c[:, 1:]
        n[1:, 1:] += c[:-1, :-1]; n[:-1, :-1] += c[1:, 1:]
        n[1:, :-1] += c[:-1, 1:]; n[:-1, 1:] += c[1:, :-1]
        new = (n == 3) | (self.cells & (n == 2))
        self.age = np.where(new, np.where(self.cells, self.age + 1, 0), 0).astype(np.float32)
        self.births = new & ~self.cells
        self.deaths = self.cells & ~new
        self.cells = new
        self.gen += 1
        return self
