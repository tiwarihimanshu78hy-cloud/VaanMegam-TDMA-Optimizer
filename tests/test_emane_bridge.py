"""Tests for the EMANE schedule bridge (XML structure and round trip; EMANE itself is not needed)."""
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from conflict_graph import build_conflict_graph
from emane_bridge import build_schedule_xml, main, nem_ids, parse_schedule_xml
from scheduler import best_schedule
from topology import build_graph, parse_nodes
from validator import validate_schedule

ROOT = Path(__file__).resolve().parent.parent


def grid_schedule():
    coords = parse_nodes((ROOT / "config" / "nodes.json").read_text())
    slot_of, _ = best_schedule(build_conflict_graph(build_graph(coords)), restarts=20)
    return coords, slot_of


def test_structure_matches_schedule():
    coords, slot_of = grid_schedule()
    root = ET.fromstring(build_schedule_xml(slot_of))
    structure = root.find("structure")
    assert root.tag == "emane-tdma-schedule"
    assert structure.get("slots") == str(max(slot_of.values()) + 1)
    assert structure.get("frames") == "1"
    assert structure.get("slotduration") == "1000"      # 1 ms slots


def test_every_node_transmits_in_exactly_one_slot():
    coords, slot_of = grid_schedule()
    xml_text = build_schedule_xml(slot_of)
    listed = [int(n) for s in ET.fromstring(xml_text).iter("slot") for n in s.get("nodes").split(",")]
    assert sorted(listed) == list(range(1, 17))


def test_round_trip_is_collision_free():
    coords, slot_of = grid_schedule()
    by_nem = parse_schedule_xml(build_schedule_xml(slot_of))
    names = {nem: name for name, nem in nem_ids(coords).items()}
    rebuilt = {names[nem]: s for nem, s in by_nem.items()}
    assert rebuilt == slot_of
    assert validate_schedule(coords, rebuilt) == (True, [])


def test_custom_slot_duration():
    root = ET.fromstring(build_schedule_xml({"A": 0, "B": 1}, slot_duration_us=2500))
    assert root.find("structure").get("slotduration") == "2500"


@pytest.mark.parametrize("kwargs", [{"slot_duration_us": 0}, {"slot_duration_us": 100, "slot_overhead_us": 100}])
def test_bad_timing_rejected(kwargs):
    with pytest.raises(ValueError):
        build_schedule_xml({"A": 0}, **kwargs)


def test_empty_schedule_rejected():
    with pytest.raises(ValueError):
        build_schedule_xml({})


def test_duplicate_nem_in_xml_rejected():
    bad = '<emane-tdma-schedule><multiframe><frame index="0"><slot index="0" nodes="1"/><slot index="1" nodes="1"/></frame></multiframe></emane-tdma-schedule>'
    with pytest.raises(ValueError):
        parse_schedule_xml(bad)


def test_cli_writes_file(tmp_path, capsys):
    out = tmp_path / "sched.xml"
    code = main(["--file", str(ROOT / "config" / "nodes.json"), "--output", str(out)])
    assert code == 0 and out.exists()
    assert "NEM  1 -> Node_01 -> slot 0" in capsys.readouterr().out
    assert len(parse_schedule_xml(out.read_text())) == 16


def test_cli_rejects_bad_input(capsys):
    assert main(['{"A":[1,2,3]}']) == 2


def test_default_datarate_is_1m():
    root = ET.fromstring(build_schedule_xml({"A": 0, "B": 1}))
    assert root.find("multiframe").get("datarate") == "1M"
    assert root.find("structure").get("bandwidth") == "1M"


def test_cli_datarate_option(tmp_path):
    out = tmp_path / "s.xml"
    assert main(["--file", str(ROOT / "config" / "nodes.json"), "--datarate", "2M", "--output", str(out)]) == 0
    assert ET.fromstring(out.read_text()).find("multiframe").get("datarate") == "2M"
