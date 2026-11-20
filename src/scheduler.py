"""scheduler.py - Colors the conflict graph; each color is a TDMA time slot."""
import random


def greedy_schedule(C, order=None):
    """
    Greedy coloring: give each node the smallest slot not already used by any of its
    conflict neighbors. This is a heuristic and is not guaranteed to be optimal.
    Returns: {node: slot}
    """
    if order is None:
        order = sorted(C.nodes())
    slot = {}
    for n in order:
        used = {slot[m] for m in C.neighbors(n) if m in slot}
        s = 0
        while s in used:
            s += 1
        slot[n] = s
    return slot


def dsatur_schedule(C, rng=None):
    """
    DSATUR heuristic. Repeatedly pick the uncolored node with the highest saturation
    (number of different slots already used by its conflict neighbors). Ties are broken
    by higher conflict degree, then by name (or randomly if rng is given).
    Returns: {node: slot}
    """
    slot = {}
    uncolored = set(C.nodes())
    while uncolored:
        def key(n):
            sat = len({slot[m] for m in C.neighbors(n) if m in slot})
            tie = rng.random() if rng else 0
            return (sat, C.degree(n), tie, n)

        n = max(uncolored, key=key)
        used = {slot[m] for m in C.neighbors(n) if m in slot}
        s = 0
        while s in used:
            s += 1
        slot[n] = s
        uncolored.remove(n)
    return slot


def frame_length(slot):
    """Number of unique slots (= frame length)."""
    return max(slot.values()) + 1 if slot else 0


def best_schedule(C, restarts=200, seed=0):
    """
    Try several heuristics and keep the schedule with the fewest slots:
      1. greedy in name order
      2. greedy in largest-degree-first order
      3. DSATUR (deterministic)
      4. `restarts` random-order greedy runs and `restarts` randomized-DSATUR runs
    Returns: (best_slot_map, log) where log is a list of (strategy_name, frame_length).
    """
    rng = random.Random(seed)  # fixed seed -> same result on every run
    nodes = sorted(C.nodes())
    candidates = [
        ("greedy (name order)", greedy_schedule(C, nodes)),
        ("greedy (largest degree first)", greedy_schedule(C, sorted(nodes, key=lambda n: -C.degree(n)))),
        ("DSATUR", dsatur_schedule(C)),
    ]
    for i in range(restarts):
        order = nodes[:]
        rng.shuffle(order)
        candidates.append((f"greedy (random order #{i})", greedy_schedule(C, order)))
        candidates.append((f"DSATUR (random ties #{i})", dsatur_schedule(C, rng)))

    log = [(name, frame_length(s)) for name, s in candidates]
    best_name, best = min(candidates, key=lambda c: frame_length(c[1]))  # first minimum wins
    return best, log
