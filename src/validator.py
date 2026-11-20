"""validator.py - Independently checks a finished schedule for collisions.

This module deliberately does NOT use topology.py, conflict_graph.py or networkx.
It recomputes every conflict directly from the raw coordinates, so a bug in the
scheduler or in the conflict graph cannot hide itself here.
"""
import math
from itertools import combinations

from topology import RADIO_RANGE_M


def validate_schedule(coords, slot_of, radio_range=RADIO_RANGE_M):
    """
    Check a {node: slot} schedule against {node: (x, y)} coordinates.
    Returns (ok, problems) where problems is a list of human-readable strings.
    """
    problems = []
    names = list(coords)

    # 1. Every node has exactly one slot, and nothing extra is scheduled.
    missing = [n for n in names if n not in slot_of]
    extra = [n for n in slot_of if n not in coords]
    if missing:
        problems.append(f"Nodes without a slot: {sorted(missing)}")
    if extra:
        problems.append(f"Scheduled nodes not in input: {sorted(extra)}")
    for n, s in slot_of.items():
        if isinstance(s, bool) or not isinstance(s, int) or s < 0:
            problems.append(f"{n}: invalid slot {s!r} (must be a non-negative integer)")
    if problems:
        return False, problems

    # 2. Recompute 1-hop adjacency straight from the coordinates.
    adj = {n: set() for n in names}
    for u, v in combinations(names, 2):
        (x1, y1), (x2, y2) = coords[u], coords[v]
        if math.hypot(x1 - x2, y1 - y2) <= radio_range:
            adj[u].add(v)
            adj[v].add(u)

    # 3. Check every pair: 1-hop neighbors or a common neighbor must differ in slot.
    for u, v in combinations(names, 2):
        if slot_of[u] != slot_of[v]:
            continue
        if v in adj[u]:
            problems.append(f"{u} and {v} are direct neighbors but share slot {slot_of[u]}")
        else:
            common = sorted(adj[u] & adj[v])
            if common:
                problems.append(
                    f"{u} and {v} share neighbor {common[0]} but share slot {slot_of[u]}"
                )
    return len(problems) == 0, problems
