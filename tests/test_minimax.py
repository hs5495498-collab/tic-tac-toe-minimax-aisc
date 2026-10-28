import math
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import minimax as mm
from app import app as flask_app


def test_minimax_root_value():
    mm.nodes_visited = 0
    value = mm.minimax(mm.GAME_TREE, 0, True, trace=False)
    assert value == 5


def test_minimax_nodes_visited():
    mm.nodes_visited = 0
    mm.minimax(mm.GAME_TREE, 0, True, trace=False)
    assert mm.nodes_visited == 15


def test_alphabeta_root_value():
    mm.nodes_visited = 0
    value = mm.alphabeta(mm.GAME_TREE, 0, -math.inf, math.inf, True, trace=False)
    assert value == 5


def test_alphabeta_nodes_visited():
    mm.nodes_visited = 0
    mm.alphabeta(mm.GAME_TREE, 0, -math.inf, math.inf, True, trace=False)
    assert mm.nodes_visited == 11


def test_alphabeta_matches_minimax_value():
    mm.nodes_visited = 0
    mm_value = mm.minimax(mm.GAME_TREE, 0, True, trace=False)
    mm.nodes_visited = 0
    ab_value = mm.alphabeta(mm.GAME_TREE, 0, -math.inf, math.inf, True, trace=False)
    assert mm_value == ab_value


def test_nodes_saved_by_pruning():
    mm.nodes_visited = 0
    mm.minimax(mm.GAME_TREE, 0, True, trace=False)
    mm_nodes = mm.nodes_visited

    mm.nodes_visited = 0
    mm.alphabeta(mm.GAME_TREE, 0, -math.inf, math.inf, True, trace=False)
    ab_nodes = mm.nodes_visited

    assert mm_nodes - ab_nodes == 4


def test_on_event_default_none_does_not_change_behavior():
    """on_event is optional instrumentation; omitting it must behave
    identically to the original algorithm."""
    mm.nodes_visited = 0
    without_callback = mm.alphabeta(mm.GAME_TREE, 0, -math.inf, math.inf, True, trace=False)
    nodes_without = mm.nodes_visited

    mm.nodes_visited = 0
    with_callback = mm.alphabeta(
        mm.GAME_TREE, 0, -math.inf, math.inf, True, trace=False, on_event=lambda e: None
    )
    nodes_with = mm.nodes_visited

    assert without_callback == with_callback
    assert nodes_without == nodes_with


def test_alphabeta_prunes_leaf_9_and_subtree():
    captured = []

    def capture(ev):
        if ev["type"] == "prune":
            captured.append(ev)

    mm.nodes_visited = 0
    mm.alphabeta(mm.GAME_TREE, 0, -math.inf, math.inf, True, trace=False, on_event=capture)

    assert len(captured) == 2

    def flatten(node):
        if isinstance(node, list):
            values = []
            for child in node:
                values.extend(flatten(child))
            return values
        return [node]

    all_pruned_values = []
    for ev in captured:
        for item in ev["pruned"]:
            all_pruned_values.extend(flatten(item["node"]))

    assert 9 in all_pruned_values
    assert 0 in all_pruned_values
    assert -1 in all_pruned_values


def test_event_order_matches_real_execution():
    """The sequence of 'enter' events must follow the exact recursive
    call order of the real algorithm (left-to-right, depth-first)."""
    order = []

    def on_event(ev):
        if ev["type"] == "enter":
            order.append(ev["label"])

    mm.nodes_visited = 0
    mm.minimax(mm.GAME_TREE, 0, True, trace=False, on_event=on_event)

    expected = [
        "Root",
        "Root.0", "Root.0.0", "Root.0.0.0", "Root.0.0.1",
        "Root.0.1", "Root.0.1.0", "Root.0.1.1",
        "Root.1", "Root.1.0", "Root.1.0.0", "Root.1.0.1",
        "Root.1.1", "Root.1.1.0", "Root.1.1.1",
    ]
    assert order == expected


# --- Flask endpoint tests -------------------------------------------------

def test_api_tree_endpoint_shape():
    client = flask_app.test_client()
    res = client.get("/api/tree")
    assert res.status_code == 200
    data = res.get_json()
    assert data["label"] == "Root"
    assert data["leaf"] is False
    assert len(data["children"]) == 2


def test_api_run_minimax_endpoint():
    client = flask_app.test_client()
    res = client.get("/api/run?algo=minimax")
    assert res.status_code == 200
    data = res.get_json()
    assert data["algorithm"] == "minimax"
    assert data["root_value"] == 5
    assert data["nodes_visited"] == 15
    assert data["nodes_saved"] == 0


def test_api_run_alphabeta_endpoint():
    client = flask_app.test_client()
    res = client.get("/api/run?algo=alphabeta")
    assert res.status_code == 200
    data = res.get_json()
    assert data["algorithm"] == "alphabeta"
    assert data["root_value"] == 5
    assert data["nodes_visited"] == 11
    assert data["minimax_nodes_visited"] == 15
    assert data["nodes_saved"] == 4


def test_api_run_alphabeta_prune_events_cover_leaf_9_and_subtree():
    client = flask_app.test_client()
    res = client.get("/api/run?algo=alphabeta")
    data = res.get_json()

    prune_events = [e for e in data["events"] if e["type"] == "prune"]
    assert len(prune_events) == 2

    all_pruned_labels = set()
    for ev in prune_events:
        all_pruned_labels.update(ev["pruned_labels"])

    # Leaf 9 lives at Root.0.1.1; the [0, -1] subtree lives under Root.1.1.
    assert all_pruned_labels == {"Root.0.1.1", "Root.1.1", "Root.1.1.0", "Root.1.1.1"}


def test_api_run_alphabeta_never_marks_pruned_nodes_as_evaluated():
    """A pruned node must never also receive an 'enter' (visited) event —
    otherwise the frontend would falsely show a skipped branch as evaluated."""
    client = flask_app.test_client()
    res = client.get("/api/run?algo=alphabeta")
    data = res.get_json()

    entered_labels = {e["label"] for e in data["events"] if e["type"] == "enter"}
    pruned_labels = set()
    for e in data["events"]:
        if e["type"] == "prune":
            pruned_labels.update(e["pruned_labels"])

    assert entered_labels.isdisjoint(pruned_labels)
    # And the overall node count the backend reports must match the number
    # of distinct nodes actually entered.
    assert len(entered_labels) == data["nodes_visited"]
