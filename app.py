"""Flask backend that runs the real minimax.py algorithms and streams
their execution as an ordered list of events for the frontend to animate.
"""
import math
import os

from flask import Flask, jsonify, render_template, request

import minimax as mm
from tic_tac_toe_routes import ttt_bp

app = Flask(__name__)
# Needed only so the new Tic-Tac-Toe feature can keep each player's game in
# a signed session cookie (see tic_tac_toe_routes.py). The original routes
# below do not use sessions at all, so this has no effect on them.
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key-for-local-demo")
app.register_blueprint(ttt_bp)


def enumerate_labels(node, label):
    """Return the label of this node plus every descendant label, in order."""
    labels = [label]
    if isinstance(node, list):
        for i, child in enumerate(node):
            labels.extend(enumerate_labels(child, f"{label}.{i}"))
    return labels


def build_tree_json(node, label="Root"):
    """Describe the game tree as nested JSON the frontend can draw."""
    if not isinstance(node, list):
        return {"label": label, "leaf": True, "value": node}
    return {
        "label": label,
        "leaf": False,
        "children": [build_tree_json(child, f"{label}.{i}") for i, child in enumerate(node)],
    }


def expand_prune_events(events):
    """Replace each prune event's raw child nodes with the full list of
    descendant labels that were skipped, so the frontend never has to
    guess at tree shape and never marks a pruned node as visited."""
    result = []
    for ev in events:
        if ev.get("type") == "prune":
            pruned_labels = []
            for item in ev["pruned"]:
                pruned_labels.extend(enumerate_labels(item["node"], item["label"]))
            new_ev = {k: v for k, v in ev.items() if k != "pruned"}
            new_ev["pruned_labels"] = pruned_labels
            result.append(new_ev)
        else:
            result.append(ev)
    return result


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/tree")
def api_tree():
    return jsonify(build_tree_json(mm.GAME_TREE))


@app.route("/api/run")
def api_run():
    algo = request.args.get("algo", "minimax")
    events = []

    def on_event(ev):
        events.append(ev)

    if algo == "alphabeta":
        mm.nodes_visited = 0
        root_value = mm.alphabeta(
            mm.GAME_TREE, 0, -math.inf, math.inf, True,
            trace=False, label="Root", on_event=on_event,
        )
        ab_nodes = mm.nodes_visited

        # Also compute plain minimax's node count (no events) purely for
        # the "nodes saved" comparison stat shown in the UI.
        mm.nodes_visited = 0
        mm.minimax(mm.GAME_TREE, 0, True, trace=False, label="Root", on_event=None)
        mm_nodes = mm.nodes_visited

        return jsonify({
            "algorithm": "alphabeta",
            "events": expand_prune_events(events),
            "root_value": root_value,
            "nodes_visited": ab_nodes,
            "minimax_nodes_visited": mm_nodes,
            "nodes_saved": mm_nodes - ab_nodes,
        })

    mm.nodes_visited = 0
    root_value = mm.minimax(
        mm.GAME_TREE, 0, True, trace=False, label="Root", on_event=on_event,
    )
    nodes = mm.nodes_visited
    return jsonify({
        "algorithm": "minimax",
        "events": expand_prune_events(events),
        "root_value": root_value,
        "nodes_visited": nodes,
        "minimax_nodes_visited": nodes,
        "nodes_saved": 0,
    })


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
