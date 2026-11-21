"""emane_bridge.py - Converts the Python TDMA schedule into an EMANE TDMA schedule XML file.

Mapping (one frame per multiframe, so the frame length equals the number of slots):
  our slot s             -> <slot index="s" nodes="NEM ids that transmit in slot s"/>
  Node_01 .. Node_16     -> NEM ids 1 .. 16 (natural sort order)
Slots that are not listed are receive slots for every NEM in the schedule (EMANE behaviour).

NOTE: the generated XML was accepted by EMANE 1.5.3's own tool (emaneevent-tdmaschedule exited
with code 0). It has not been run inside a full EMANE emulation, so packet delivery according
to the schedule is NOT verified.
"""
import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from conflict_graph import build_conflict_graph
from report import natural_key
from scheduler import best_schedule
from topology import RADIO_RANGE_M, build_graph, parse_nodes
from validator import validate_schedule

DEFAULT_OUTPUT = "emane/configuration/tdma-schedule.xml"


def nem_ids(nodes):
    """Node name -> NEM id (1-based, natural sort order: Node_01 -> 1, Node_16 -> 16)."""
    return {n: i for i, n in enumerate(sorted(nodes, key=natural_key), start=1)}


def build_schedule_xml(slot_of, slot_duration_us=1000, slot_overhead_us=0, bandwidth="1M",
                       frequency="2.4G", power="0", service_class="0", datarate="1M"):
    """Return the EMANE TDMA schedule XML (as a string) for a {node: slot} schedule."""
    if not slot_of:
        raise ValueError("Cannot build a schedule for zero nodes")
    if slot_duration_us <= 0 or slot_overhead_us < 0 or slot_overhead_us >= slot_duration_us:
        raise ValueError("Slot duration must be positive and larger than the slot overhead")

    ids = nem_ids(slot_of)
    num_slots = max(slot_of.values()) + 1

    root = ET.Element("emane-tdma-schedule")
    ET.SubElement(root, "structure", {
        "frames": "1",
        "slots": str(num_slots),
        "slotduration": str(slot_duration_us),
        "slotoverhead": str(slot_overhead_us),
        "bandwidth": bandwidth,
    })
    multiframe = ET.SubElement(root, "multiframe", {
        "frequency": frequency,
        "power": power,
        "class": service_class,
        "datarate": datarate,
    })
    frame = ET.SubElement(multiframe, "frame", {"index": "0"})
    for s in range(num_slots):
        members = sorted(ids[n] for n, v in slot_of.items() if v == s)
        if members:
            ET.SubElement(frame, "slot", {"index": str(s), "nodes": ",".join(map(str, members))})

    ET.indent(root)
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode") + "\n"


def parse_schedule_xml(xml_text):
    """Read a schedule XML back into {nem_id: slot}. Used to verify the round trip."""
    root = ET.fromstring(xml_text)
    if root.tag != "emane-tdma-schedule":
        raise ValueError(f"Unexpected root element: {root.tag}")
    slot_of_nem = {}
    for slot in root.iter("slot"):
        index = int(slot.get("index"))
        for nem in slot.get("nodes", "").split(","):
            nem = int(nem)
            if nem in slot_of_nem:
                raise ValueError(f"NEM {nem} appears in more than one slot")
            slot_of_nem[nem] = index
    return slot_of_nem


def main(argv=None):
    p = argparse.ArgumentParser(description="Generate an EMANE TDMA schedule XML from node coordinates")
    p.add_argument("json_string", nargs="?", help="node coordinates as a JSON string")
    p.add_argument("--file", help="read the node coordinates from this JSON file instead")
    p.add_argument("--range", type=float, default=RADIO_RANGE_M, dest="radio_range")
    p.add_argument("--slot-us", type=int, default=1000, help="slot duration in microseconds (default 1000 = 1 ms)")
    p.add_argument("--datarate", default="1M",
                   help="slot data rate, e.g. 1M (default 1M, a rate present in EMANE's shipped PCR curve file)")
    p.add_argument("--output", default=DEFAULT_OUTPUT, help=f"XML output path (default {DEFAULT_OUTPUT})")
    args = p.parse_args(sys.argv[1:] if argv is None else argv)
    if (args.json_string is None) == (args.file is None):
        p.error("provide the coordinates as a JSON string or with --file (exactly one of the two)")

    try:
        text = Path(args.file).read_text() if args.file else args.json_string
        coords = parse_nodes(text)
        slot_of, _ = best_schedule(build_conflict_graph(build_graph(coords, args.radio_range)))
        ok, problems = validate_schedule(coords, slot_of, args.radio_range)
        if not ok:
            print("Error: schedule failed verification:", *problems, sep="\n  - ", file=sys.stderr)
            return 1
        xml_text = build_schedule_xml(slot_of, slot_duration_us=args.slot_us, datarate=args.datarate)
    except (OSError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(xml_text)

    frame_us = (max(slot_of.values()) + 1) * args.slot_us
    print(f"Wrote {out}  ({max(slot_of.values()) + 1} slots x {args.slot_us} us = {frame_us} us frame)")
    print("NEM id -> node -> slot")
    for node, nem in nem_ids(slot_of).items():
        print(f"  NEM {nem:>2} -> {node} -> slot {slot_of[node]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
