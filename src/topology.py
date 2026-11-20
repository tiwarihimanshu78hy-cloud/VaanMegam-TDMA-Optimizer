"""topology.py - Builds the original communication graph G from JSON coordinates."""
import json
import math

import networkx as nx

RADIO_RANGE_M = 500.0  # Assignment: radios can communicate within 500 meters


def parse_nodes(json_text):
    """Parse a JSON string into {node_name: (x, y)} and validate the input."""
    try:
        data = json.loads(json_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")

    if not isinstance(data, dict) or not data:
        raise ValueError('JSON must be a non-empty object: {"Node_01": [x, y], ...}')

    coords = {}
    for name, xy in data.items():
        ok = (
            isinstance(xy, list)
            and len(xy) == 2
            and all(
                isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
                for v in xy
            )
        )
        if not ok:
            raise ValueError(f"{name}: coordinate must be [x, y] (two numbers), got {xy!r}")
        coords[name] = (float(xy[0]), float(xy[1]))
    return coords


def distance(a, b):
    """Euclidean distance in meters: sqrt((x1-x2)^2 + (y1-y2)^2)."""
    return math.hypot(a[0] - b[0], a[1] - b[1])


def build_graph(coords, radio_range=RADIO_RANGE_M):
    """Undirected graph G. Every node is added (including isolated ones);
    an edge exists when the distance is <= radio_range."""
    G = nx.Graph()
    for name, pos in coords.items():
        G.add_node(name, pos=pos)

    names = list(coords)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            u, v = names[i], names[j]
            if distance(coords[u], coords[v]) <= radio_range:
                G.add_edge(u, v)
    return G
