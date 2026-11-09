"""Narration script. Each scene: list of (pause_before_seconds, line). Line ids are scene:index."""

SCRIPT = {
    "open": [
        (2.0, "This is the grid."),
        (1.4, "A world with no weather, and no seasons."),
        (1.2, "There is only one law."),
    ],
    "law": [
        (1.0, "Wherever an empty space has exactly three living neighbours..."),
        (0.5, "life begins."),
        (1.1, "With two or three neighbours, a living thing endures."),
        (1.2, "With fewer, it dies of loneliness."),
        (1.0, "With more, of overcrowding."),
        (1.1, "It is not a gentle law. But it is the same for everyone."),
    ],
    "still": [
        (1.2, "This is the block."),
        (0.8, "It has done nothing for eleven thousand generations."),
        (0.7, "It is, by every measure, thriving."),
        (1.3, "Nearby, a beehive. A loaf. A boat."),
        (0.8, "None of them has ever seen a bee. Or bread. Or the sea."),
    ],
    "osc": [
        (1.0, "Some prefer to keep busy, without going anywhere."),
        (1.0, "The blinker."),
        (1.2, "And the pulsar, which repeats its display every three generations,"),
        (0.6, "for an audience of no one."),
    ],
    "glider": [
        (1.5, "But some, leave."),
        (1.2, "The glider."),
        (1.0, "Five cells, walking diagonally into the dark."),
        (1.1, "It travels by falling apart, and putting itself back together, every four generations."),
        (1.1, "It has never once looked back."),
    ],
    "eater": [
        (1.0, "Out here, there are others."),
        (1.6, "The eater does not hunt."),
        (1.2, "It simply waits."),
        (3.6, "And four generations later, it is whole again, as though nothing had happened."),
        (0.9, "There is no malice in it. Only arithmetic."),
    ],
    "gun": [
        (1.2, "This is a Gahsper glider gun."),
        (1.4, "Every thirty generations, she sends another child out into the dark."),
        (1.4, "She has sent thousands. None have written."),
        (1.3, "She will never see any of them again."),
    ],
    "rpent": [
        (1.0, "And then, there is this."),
        (1.0, "Five cells. Unremarkable."),
        (1.2, "Left alone, it will burn for eleven hundred and three generations."),
        (7.4, "It throws off gliders like sparks."),
        (1.2, "It consumes everything it touches."),
        (4.0, "And then, at last,"),
        (1.6, "it is still."),
        (1.3, "Blocks. Beehives. A few blinkers, breathing in the ruins."),
        (1.2, "A world, made from a catastrophe."),
        (1.2, "As most worlds are."),
    ],
    "end": [
        (1.6, "And somewhere, far from here, one glider is still going."),
        (1.4, "It has no destination."),
        (1.2, "It will never arrive."),
        (1.5, "It is, by every measure,"),
        (0.7, "thriving."),
    ],
}

ORDER = ["open", "law", "still", "osc", "glider", "eater", "gun", "rpent", "end"]
VOICE, SPEED = "bm_george", 0.9
