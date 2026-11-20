"""Automated tests for the TDMA schedule planner (run with: pytest -v)."""
import json
import random
from itertools import combinations
from pathlib import Path

import networkx as nx
import pytest

from conflict_graph import build_conflict_graph
from main import main
from report import build_matrix, natural_key, verify_matrix
from scheduler import best_schedule, dsatur_schedule, frame_length, greedy_schedule
from topology import build_graph, parse_nodes
from validator import validate_schedule

ROOT = Path(__file__).resolve().parent.parent


def plan(coords_dict):
    """Run the full pipeline on a {name: [x, y]} dict. Returns (coords, G, slot_of)."""
    coords = parse_nodes(json.dumps(coords_dict))
    G = build_graph(coords)
    slot_of, _ = best_schedule(build_conflict_graph(G), restarts=20)
    return coords, G, slot_of


def grid_16():
    return {f"Node_{r * 4 + c + 1:02d}": [c * 300.0, r * 300.0] for r in range(4) for c in range(4)}


# ---- TEST 1: three nodes in a line (A and C share neighbor B) ----
def test_1_three_node_chain_all_different():
    coords, G, slot = plan({"A": [0, 0], "B": [400, 0], "C": [800, 0]})
    assert set(G.edges()) == {("A", "B"), ("B", "C")}
    assert len(set(slot.values())) == 3
    assert slot["A"] != slot["C"]
    assert validate_schedule(coords, slot) == (True, [])


# ---- TEST 2: two disconnected nodes can reuse one slot ----
def test_2_disconnected_nodes_share_slot():
    coords, G, slot = plan({"A": [0, 0], "B": [2000, 0]})
    assert G.number_of_edges() == 0
    assert slot["A"] == slot["B"]
    assert frame_length(slot) == 1


# ---- TEST 3: more than two hops apart -> spatial reuse ----
def test_3_spatial_reuse_beyond_two_hops():
    coords, G, slot = plan({"A": [0, 0], "B": [400, 0], "C": [800, 0], "D": [1200, 0]})
    assert nx.shortest_path_length(G, "A", "D") == 3
    assert frame_length(slot) == 3          # only possible because A and D reuse a slot
    assert slot["A"] == slot["D"]
    assert validate_schedule(coords, slot)[0]


# ---- TEST 4: fully connected graph needs one slot per node ----
def test_4_fully_connected_all_different():
    nodes = {f"N{i}": [i * 10.0, 0.0] for i in range(6)}
    coords, G, slot = plan(nodes)
    assert G.number_of_edges() == 6 * 5 // 2
    assert len(set(slot.values())) == 6


# ---- TEST 5: isolated nodes all share slot 0 ----
def test_5_isolated_nodes_share_one_slot():
    nodes = {f"N{i}": [i * 1000.0, 0.0] for i in range(5)}
    coords, G, slot = plan(nodes)
    assert len(list(nx.isolates(G))) == 5
    assert set(slot.values()) == {0}


# ---- TEST 6: sixteen-node sample topology, full schedule + CLI ----
def test_6_sixteen_node_grid():
    coords, G, slot = plan(grid_16())
    assert len(slot) == 16
    assert G.number_of_edges() == 42
    assert validate_schedule(coords, slot) == (True, [])
    assert frame_length(slot) == 9          # 3x3 blocks are cliques, so 9 is also the lower bound
    assert len(set(slot.values())) < 16     # spatial reuse really happened
    nodes = sorted(coords, key=natural_key)
    matrix = build_matrix(slot, nodes)
    assert verify_matrix(matrix, nodes, slot)
    assert all(sum(row[j] for row in matrix) == 1 for j in range(16))


def test_6b_cli_end_to_end(capsys, tmp_path):
    out_file = tmp_path / "schedule.txt"
    code = main(["--file", str(ROOT / "config" / "nodes.json"), "--output", str(out_file)])
    text = capsys.readouterr().out
    assert code == 0
    assert "Total Nodes Processed : 16" in text
    assert "9 unique timeslots" in text
    assert "Schedule verified conflict-free." in text
    assert out_file.read_text().strip() == text.strip()


# ---- TEST 7: random topologies, checked by the validator AND a networkx oracle ----
def test_7_random_topologies_no_collisions():
    for seed in range(200):
        rng = random.Random(seed)
        area = rng.choice([600, 1200, 2000, 3000])
        raw = {f"Node_{i:02d}": [round(rng.uniform(0, area), 1), round(rng.uniform(0, area), 1)]
               for i in range(1, 17)}
        coords, G, slot = plan(raw)

        ok, problems = validate_schedule(coords, slot)
        assert ok, f"seed {seed}: {problems}"

        # Second, different oracle: shortest paths straight from networkx
        for u, v in combinations(G.nodes(), 2):
            if nx.has_path(G, u, v) and nx.shortest_path_length(G, u, v) <= 2:
                assert slot[u] != slot[v], f"seed {seed}: {u},{v} collide"


# ---- Extra tests: boundaries, edge cases, and the validator itself ----
def test_boundary_exactly_500m_is_a_link():
    on = build_graph(parse_nodes('{"A":[0,0],"B":[500,0]}'))
    off = build_graph(parse_nodes('{"A":[0,0],"B":[500.01,0]}'))
    assert on.has_edge("A", "B")
    assert not off.has_edge("A", "B")


def test_duplicate_coordinates_get_different_slots():
    coords, G, slot = plan({"A": [10, 10], "B": [10, 10]})
    assert G.has_edge("A", "B")
    assert slot["A"] != slot["B"]


@pytest.mark.parametrize("bad", ['{oops', '[]', '{}', '{"A":[1,2,3]}', '{"A":["x",1]}', '{"A":[1,true]}'])
def test_invalid_json_inputs_rejected(bad):
    with pytest.raises(ValueError):
        parse_nodes(bad)


def test_validator_catches_one_hop_clash():
    coords = parse_nodes('{"A":[0,0],"B":[300,0]}')
    ok, problems = validate_schedule(coords, {"A": 0, "B": 0})
    assert not ok and "direct neighbors" in problems[0]


def test_validator_catches_two_hop_clash():
    coords = parse_nodes('{"A":[0,0],"B":[400,0],"C":[800,0]}')
    ok, problems = validate_schedule(coords, {"A": 0, "B": 1, "C": 0})
    assert not ok and "share neighbor B" in problems[0]


def test_validator_catches_missing_node():
    coords = parse_nodes('{"A":[0,0],"B":[900,0]}')
    assert not validate_schedule(coords, {"A": 0})[0]


def test_matrix_check_detects_tampering():
    slot = {"A": 0, "B": 1}
    nodes = ["A", "B"]
    matrix = build_matrix(slot, nodes)
    matrix[1][0] = 1                        # give A a second slot
    assert not verify_matrix(matrix, nodes, slot)


def test_every_heuristic_gives_valid_schedules():
    coords = parse_nodes(json.dumps(grid_16()))
    C = build_conflict_graph(build_graph(coords))
    for slot in (greedy_schedule(C), dsatur_schedule(C), best_schedule(C, restarts=5)[0]):
        assert validate_schedule(coords, slot)[0]
