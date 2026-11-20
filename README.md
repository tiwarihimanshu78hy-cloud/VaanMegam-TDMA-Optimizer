# TDMA Schedule Planner and Optimizer

Centralized Python scheduler for a TDMA wireless network (Vaan Megam Networks assignment, Part 1).
Given static 2-D coordinates of radios, it builds a communication graph, applies Distance-2
(two-hop) graph colouring, and prints a conflict-free Node -> Slot mapping and a Slot x Node
Boolean matrix. Slots are reused by nodes that are more than two hops apart (spatial reuse).

## Setup

    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt

## Usage

JSON string (as in the assignment):

    python src/main.py '{"Node_01":[0.0,0.0],"Node_02":[300.0,0.0],"Node_03":[600.0,0.0]}'

JSON file, saving the report:

    python src/main.py --file config/nodes.json --output output/schedule.txt

Options: `--range METERS` (default 500), `--output FILE`, `--verbose` (heuristic details).
Exit codes: 0 = verified conflict-free schedule, 1 = verification failed, 2 = invalid input.
The assignment expects 16 nodes; any other count runs but prints a warning.

## How it works

1. `topology.py` validates the JSON and builds the undirected graph G. An edge exists when the
   Euclidean distance is <= 500 m (inclusive). Isolated nodes stay in the graph.
2. `conflict_graph.py` builds G^2: two nodes conflict when their hop distance in G is 1
   (direct link) or 2 (common neighbour, the hidden-terminal case).
3. `scheduler.py` colours G^2; each colour is a time slot. Heuristics: greedy colouring (name
   order and largest-degree-first), DSATUR, and 200 random-order greedy plus 200 randomized
   DSATUR restarts (fixed seed, so results are reproducible). The valid schedule with the
   fewest slots is kept. Minimum colouring is NP-hard, so the result is not guaranteed optimal.
4. `validator.py` re-checks the final schedule independently from the raw coordinates (it does
   not reuse the graph code), and `report.py` checks that the matrix matches the mapping.
5. `report.py` prints the optimization report in the assignment's format.

## Results (config/nodes.json: 4x4 grid, 300 m spacing)

- 16 nodes, 42 links, 9 unique time slots, no collisions (see `output/schedule.txt`).
- 9 equals the clique lower bound of G^2 (every 3x3 block of nodes is mutually in conflict),
  so 9 slots is optimal for this topology. For other topologies the lower bound is printed
  with `--verbose`; optimality is only claimed when the two numbers match.
- Spatial reuse: for example Node_01, Node_04, Node_13 and Node_16 share Slot 0.

## Tests

    python -m pytest -v

21 tests cover: 3-node chain, disconnected nodes, spatial reuse beyond two hops, fully connected
graph, isolated nodes, the 16-node topology, 200 random topologies (checked by the validator and
by a separate networkx shortest-path check), the 500 m boundary, duplicate coordinates, invalid
JSON, the validator itself and the matrix check.

## Project structure

    src/            main.py (CLI), topology.py, conflict_graph.py, scheduler.py,
                    validator.py, report.py
    config/         nodes.json (sample input)
    output/         schedule.txt (sample report)
    tests/          test_scheduler.py
    emane/          Part 2 (bonus) material
    docs/           project documentation (PDF)
    presentation/   slides (PPT)

## Assumptions and limitations

- Unit-disk model: every radio has the same 500 m range; links are symmetric.
- Static topology; no obstacles, fading or mobility. One transmitter per slot per node.
- Heuristic colouring: slot count may exceed the true minimum on some topologies.

## Part 2 (bonus): EMANE

Status: not started yet (this section will be updated honestly with what was actually done).
