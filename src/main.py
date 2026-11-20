"""main.py - CLI for the TDMA Schedule Planner and Optimizer.

Examples:
  python src/main.py '{"Node_01":[0,0],"Node_02":[300,0],...}'
  python src/main.py --file config/nodes.json --output output/schedule.txt
"""
import argparse
import sys
from pathlib import Path

import networkx as nx

from conflict_graph import build_conflict_graph
from report import build_matrix, format_report, natural_key, verify_matrix
from scheduler import best_schedule
from topology import RADIO_RANGE_M, build_graph, parse_nodes
from validator import validate_schedule

OFFICIAL_NODE_COUNT = 16


def parse_args(argv):
    p = argparse.ArgumentParser(description="Distance-2 TDMA schedule planner and optimizer")
    p.add_argument("json_string", nargs="?",
                   help='node coordinates as JSON, e.g. \'{"Node_01":[0.0,0.0],"Node_02":[300.0,0.0]}\'')
    p.add_argument("--file", help="read the node coordinates from this JSON file instead")
    p.add_argument("--range", type=float, default=RADIO_RANGE_M, dest="radio_range",
                   help="radio range in meters (default: 500)")
    p.add_argument("--output", help="also save the report to this file")
    p.add_argument("--verbose", action="store_true", help="print heuristic details")
    args = p.parse_args(argv)
    if (args.json_string is None) == (args.file is None):
        p.error("provide the coordinates as a JSON string or with --file (exactly one of the two)")
    if args.radio_range <= 0:
        p.error("--range must be positive")
    return args


def main(argv=None):
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        text = Path(args.file).read_text() if args.file else args.json_string
        coords = parse_nodes(text)
    except (OSError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

    if len(coords) != OFFICIAL_NODE_COUNT:
        print(f"Warning: expected {OFFICIAL_NODE_COUNT} nodes, got {len(coords)}", file=sys.stderr)

    G = build_graph(coords, args.radio_range)
    C = build_conflict_graph(G)
    slot_of, log = best_schedule(C)

    ok, problems = validate_schedule(coords, slot_of, args.radio_range)
    nodes = sorted(coords, key=natural_key)
    matrix_ok = verify_matrix(build_matrix(slot_of, nodes), nodes, slot_of)

    report = format_report(coords, args.radio_range, slot_of, ok, problems, matrix_ok)
    print(report)

    if args.verbose:
        best_name, best_len = min(log, key=lambda x: x[1])
        lower_bound = max(len(c) for c in nx.find_cliques(C))
        print(f"\nStrategies tried : {len(log)}")
        print(f"Best strategy    : {best_name} -> {best_len} slots")
        print(f"Clique lower bound: {lower_bound} slots"
              + (" (result is provably optimal)" if best_len == lower_bound else ""))

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report + "\n")

    return 0 if (ok and matrix_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
