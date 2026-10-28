"""Flask routes for the Tic-Tac-Toe game.

This is a self-contained Flask Blueprint so it can be registered onto the
existing `app.py` with a single line, without touching any of the original
Minimax-demo routes. Responses carry concise search statistics (value,
chosen move, node counts, pruning count, timing) but never a full
step-by-step event trace or board-snapshot history - the page only ever
displays the board and the final numbers, never an animated search-tree
graph or event log, so there is nothing on the frontend that needs them.

Game state (board, symbols, whose turn it is, chosen algorithm, game-over
flag) lives in the browser's Flask *session* cookie under the single key
"ttt_state" - never in a module-level/global variable. That is what keeps
one player's game completely isolated from another's: every browser gets
its own signed session cookie, so two tabs (or two students in the same
classroom hitting the same server) never see or mutate each other's board.
"""

from flask import Blueprint, jsonify, render_template, request, session

import tic_tac_toe as ttt

ttt_bp = Blueprint("tic_tac_toe", __name__)

SESSION_KEY = "ttt_state"
VALID_SYMBOLS = (ttt.PLAYER_X, ttt.PLAYER_O)
VALID_ALGORITHMS = ("minimax", "alphabeta")
VALID_FIRST_PLAYERS = ("human", "ai")


def _new_game_state(human_symbol, first_player, algorithm, use_move_ordering=True):
    ai_symbol = ttt.other_player(human_symbol)
    return {
        "board": ttt.create_empty_board(),
        "human_symbol": human_symbol,
        "ai_symbol": ai_symbol,
        "algorithm": algorithm,
        "use_move_ordering": use_move_ordering,
        "turn": first_player,       # whose move it is right now: "human" or "ai"
        "game_over": False,
        "winner": None,             # "X", "O", or "draw" once decided
    }


def _get_state():
    return session.get(SESSION_KEY)


def _save_state(state):
    session[SESSION_KEY] = state


def _public_search(result):
    """Trim a `search_best_move` result down to the concise stats the page
    actually displays (algorithm, final value, chosen move, node counts,
    pruning count, timing). Deliberately drops the `events` list - the
    page no longer renders a search-tree graph or a step-by-step event
    log, so there is no reason to ship that payload to the browser. (With
    `collect_events` defaulting to False, `events` is normally already
    empty by the time it gets here; this also protects against ever
    leaking it if that default is changed in the future.)"""
    return {
        "algorithm": result["algorithm"],
        "value": result["value"],
        "move": result["move"],
        "nodes_visited": result["nodes_visited"],
        "terminal_count": result["terminal_count"],
        "pruned_branches": result["pruned_branches"],
        "time_ms": result["time_ms"],
    }


def _public_state(state, last_search=None):
    """The subset of state the frontend needs, plus the latest AI search
    stats (no event trace) if an AI move was just computed on this request."""
    out = {
        "board": state["board"],
        "human_symbol": state["human_symbol"],
        "ai_symbol": state["ai_symbol"],
        "algorithm": state["algorithm"],
        "use_move_ordering": state["use_move_ordering"],
        "turn": state["turn"],
        "game_over": state["game_over"],
        "winner": state["winner"],
    }
    if last_search is not None:
        out["search"] = _public_search(last_search)
    return out


def _finish_if_terminal(state):
    """Check the board for a win/draw and update state in place."""
    winner = ttt.get_winner(state["board"])
    if winner is not None:
        state["game_over"] = True
        state["winner"] = winner
    elif ttt.is_board_full(state["board"]):
        state["game_over"] = True
        state["winner"] = "draw"


def _run_ai_move(state):
    """Let the AI compute and play its move with the real search. Returns
    the search-result dict (value, move, stats, events) for the frontend."""
    result = ttt.search_best_move(
        state["board"], state["ai_symbol"], state["algorithm"],
        use_move_ordering=state["use_move_ordering"],
    )
    move = result["move"]
    if move is not None:
        state["board"] = ttt.apply_move(state["board"], move, state["ai_symbol"])
        state["turn"] = "human"
    _finish_if_terminal(state)
    return result


@ttt_bp.route("/tic-tac-toe")
def tic_tac_toe_page():
    return render_template("tic_tac_toe.html")


@ttt_bp.route("/api/ttt/new", methods=["POST"])
def api_ttt_new():
    data = request.get_json(silent=True) or {}
    human_symbol = data.get("human_symbol", ttt.PLAYER_X)
    first_player = data.get("first_player", "human")
    algorithm = data.get("algorithm", "alphabeta")
    use_move_ordering = bool(data.get("use_move_ordering", True))

    if human_symbol not in VALID_SYMBOLS:
        return jsonify({"error": f"human_symbol must be one of {VALID_SYMBOLS}"}), 400
    if first_player not in VALID_FIRST_PLAYERS:
        return jsonify({"error": f"first_player must be one of {VALID_FIRST_PLAYERS}"}), 400
    if algorithm not in VALID_ALGORITHMS:
        return jsonify({"error": f"algorithm must be one of {VALID_ALGORITHMS}"}), 400

    state = _new_game_state(human_symbol, first_player, algorithm, use_move_ordering)

    search_result = None
    if state["turn"] == "ai":
        search_result = _run_ai_move(state)

    _save_state(state)
    return jsonify(_public_state(state, search_result))


@ttt_bp.route("/api/ttt/move", methods=["POST"])
def api_ttt_move():
    state = _get_state()
    if state is None:
        return jsonify({"error": "No game in progress. Start a new game first."}), 400
    if state["game_over"]:
        return jsonify({"error": "The game is already over. Start a new game."}), 400
    if state["turn"] != "human":
        return jsonify({"error": "It is not the human player's turn."}), 400

    data = request.get_json(silent=True) or {}
    position = data.get("position")
    if not isinstance(position, int) or not (0 <= position <= 8):
        return jsonify({"error": "position must be an integer from 0 to 8."}), 400
    if state["board"][position] != ttt.EMPTY:
        return jsonify({"error": f"Cell {position} is already occupied."}), 400

    state["board"] = ttt.apply_move(state["board"], position, state["human_symbol"])
    state["turn"] = "ai"
    _finish_if_terminal(state)

    search_result = None
    if not state["game_over"]:
        search_result = _run_ai_move(state)

    _save_state(state)
    return jsonify(_public_state(state, search_result))


@ttt_bp.route("/api/ttt/reset", methods=["POST"])
def api_ttt_reset():
    # A reset is just a fresh "new game" using whatever settings the
    # request supplies (or sensible defaults if the board is reset without
    # changing settings).
    data = request.get_json(silent=True) or {}
    previous = _get_state()
    human_symbol = data.get("human_symbol", previous["human_symbol"] if previous else ttt.PLAYER_X)
    first_player = data.get("first_player", "human")
    algorithm = data.get("algorithm", previous["algorithm"] if previous else "alphabeta")
    use_move_ordering = bool(data.get(
        "use_move_ordering", previous["use_move_ordering"] if previous else True
    ))

    if first_player not in VALID_FIRST_PLAYERS:
        first_player = "human"
    if human_symbol not in VALID_SYMBOLS:
        human_symbol = ttt.PLAYER_X
    if algorithm not in VALID_ALGORITHMS:
        algorithm = "alphabeta"

    state = _new_game_state(human_symbol, first_player, algorithm, use_move_ordering)

    search_result = None
    if state["turn"] == "ai":
        search_result = _run_ai_move(state)

    _save_state(state)
    return jsonify(_public_state(state, search_result))


@ttt_bp.route("/api/ttt/algorithm", methods=["POST"])
def api_ttt_set_algorithm():
    """Change the AI's algorithm (and move-ordering) without touching the
    board - useful for comparing algorithms mid-game."""
    state = _get_state()
    if state is None:
        return jsonify({"error": "No game in progress. Start a new game first."}), 400

    data = request.get_json(silent=True) or {}
    algorithm = data.get("algorithm")
    if algorithm not in VALID_ALGORITHMS:
        return jsonify({"error": f"algorithm must be one of {VALID_ALGORITHMS}"}), 400
    if "use_move_ordering" in data:
        state["use_move_ordering"] = bool(data["use_move_ordering"])

    state["algorithm"] = algorithm
    _save_state(state)
    return jsonify(_public_state(state))


@ttt_bp.route("/api/ttt/state")
def api_ttt_state():
    state = _get_state()
    if state is None:
        return jsonify({"error": "No game in progress."}), 404
    return jsonify(_public_state(state))


@ttt_bp.route("/api/ttt/compare", methods=["POST"])
def api_ttt_compare():
    """Run Minimax, Alpha-Beta (with move ordering), and Alpha-Beta
    (without move ordering) on the *current* board without changing the
    actual game - lets the UI show a side-by-side efficiency comparison."""
    state = _get_state()
    if state is None:
        return jsonify({"error": "No game in progress. Start a new game first."}), 400

    board = state["board"]
    ai_symbol = state["ai_symbol"]

    # collect_events is left at its default (False): the comparison panel
    # only ever displays the final stats below, never a tree or event log,
    # so there is no reason to pay for building thousands of event dicts
    # (each copying the board) just to throw them away.
    minimax_result = ttt.search_best_move(board, ai_symbol, "minimax")
    alphabeta_ordered = ttt.search_best_move(board, ai_symbol, "alphabeta", use_move_ordering=True)
    alphabeta_unordered = ttt.search_best_move(board, ai_symbol, "alphabeta", use_move_ordering=False)

    return jsonify({
        "board": board,
        "ai_symbol": ai_symbol,
        "minimax": _public_search(minimax_result),
        "alphabeta_ordered": _public_search(alphabeta_ordered),
        "alphabeta_unordered": _public_search(alphabeta_unordered),
        "nodes_saved_by_pruning": minimax_result["nodes_visited"] - alphabeta_ordered["nodes_visited"],
        "nodes_saved_by_move_ordering": alphabeta_unordered["nodes_visited"] - alphabeta_ordered["nodes_visited"],
        "values_agree": (
            minimax_result["value"] == alphabeta_ordered["value"] == alphabeta_unordered["value"]
        ),
    })
