"""report.py - Builds the Slot x Node matrix and the text optimization report."""
import re

W = 64  # width of the '=' banner lines


def natural_key(name):
    """Sort Node_2 before Node_10 (numbers compared as numbers)."""
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", name)]


def build_matrix(slot_of, nodes):
    """Slot x Node Boolean matrix: matrix[s][j] == 1 when nodes[j] transmits in slot s."""
    num_slots = max(slot_of.values()) + 1 if slot_of else 0
    return [[1 if slot_of[n] == s else 0 for n in nodes] for s in range(num_slots)]


def verify_matrix(matrix, nodes, slot_of):
    """Each node (column) must have exactly one 1, located in the row of its mapped slot."""
    for j, n in enumerate(nodes):
        column = [row[j] for row in matrix]
        if sum(column) != 1 or column[slot_of[n]] != 1:
            return False
    return True


def _label(name):
    return name[5:] if name.startswith("Node_") else name


def format_report(coords, radio_range, slot_of, ok, problems, matrix_ok):
    """Return the full report as a string (layout follows the assignment sample)."""
    nodes = sorted(coords, key=natural_key)
    matrix = build_matrix(slot_of, nodes)
    labels = [_label(n) for n in nodes]
    w = max(2, max(len(x) for x in labels))
    rule = "-" * 89

    out = []
    out.append("=" * W)
    out.append(" TDMA TOPOLOGY OPTIMIZATION REPORT ")
    out.append("=" * W)
    out.append(f"Total Nodes Processed : {len(nodes)}")
    out.append(f"Configured Radio Range : {radio_range} meters")
    out.append(f"Optimized Frame Length : {len(matrix)} unique timeslots (Lower is better)")
    out.append("-" * 65)
    out.append("NODE -> SLOT ASSIGNMENTS:")
    for n in nodes:
        out.append(f" {n}: Slot {slot_of[n]}")
    out.append("STRUCTURAL TDMA SCHEDULE MATRIX (Slot x Node Boolean Matrix):")
    out.append("Slot \\ Node | " + " | ".join(x.rjust(w) for x in labels))
    out.append(rule)
    for s, row in enumerate(matrix):
        out.append(f"{('Slot ' + format(s, '02d')):<11} | " + " | ".join(str(v).rjust(w) for v in row))
    out.append(rule)
    if ok and matrix_ok:
        out.append("Execution finalized cleanly. Schedule verified conflict-free.")
    else:
        out.append("WARNING: schedule FAILED verification.")
        for p in problems:
            out.append(f"  - {p}")
        if not matrix_ok:
            out.append("  - Schedule matrix does not match the node-to-slot mapping")
    out.append("=" * W)
    return "\n".join(out)
