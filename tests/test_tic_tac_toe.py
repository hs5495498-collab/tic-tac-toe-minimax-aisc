import math
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import tic_tac_toe as ttt
from app import app as flask_app


# --- Board / rules ---------------------------------------------------------

def test_empty_board_has_nine_blank_cells():
    board = ttt.create_empty_board()
    assert len(board) == 9
    assert all(cell == ttt.EMPTY for cell in board)


def test_apply_move_returns_new_board_without_mutating_original():
    board = ttt.create_empty_board()
    new_board = ttt.apply_move(board, 4, ttt.PLAYER_X)
    assert new_board[4] == ttt.PLAYER_X
    assert board[4] == ttt.EMPTY  # original untouched


def test_apply_move_rejects_occupied_cell():
    board = ttt.apply_move(ttt.create_empty_board(), 0, ttt.PLAYER_X)
    try:
        ttt.apply_move(board, 0, ttt.PLAYER_O)
        assert False, "expected ValueError for occupied cell"
    except ValueError:
        pass


def test_all_eight_winning_lines_detected_for_x_and_o():
    for line in ttt.WIN_LINES:
        for player in (ttt.PLAYER_X, ttt.PLAYER_O):
            board = ttt.create_empty_board()
            for pos in line:
                board[pos] = player
            assert ttt.get_winner(board) == player, f"line {line} failed for {player}"


def test_no_winner_on_empty_board():
    assert ttt.get_winner(ttt.create_empty_board()) is None


def test_draw_detection_full_board_no_winner():
    # A known drawn board.
    board = list("XOXXOOOXX")
    assert ttt.get_winner(board) is None
    assert ttt.is_board_full(board)
    assert ttt.is_terminal(board)


def test_terminal_true_on_win_and_on_draw_and_false_otherwise():
    win_board = list("XX_______".replace("_", ttt.EMPTY))
    win_board[2] = ttt.PLAYER_X
    assert ttt.is_terminal(win_board)

    mid_board = ttt.create_empty_board()
    mid_board[0] = ttt.PLAYER_X
    assert not ttt.is_terminal(mid_board)

    draw_board = list("XOXXOOOXX")
    assert ttt.is_terminal(draw_board)


def test_available_moves_lists_only_empty_cells():
    board = ttt.create_empty_board()
    board[0] = ttt.PLAYER_X
    board[4] = ttt.PLAYER_O
    assert ttt.available_moves(board) == [1, 2, 3, 5, 6, 7, 8]


# --- Algorithm correctness --------------------------------------------------

def test_minimax_and_alphabeta_agree_on_empty_board_value():
    board = ttt.create_empty_board()
    mm_result = ttt.search_best_move(board, ttt.PLAYER_X, "minimax")
    ab_result = ttt.search_best_move(board, ttt.PLAYER_X, "alphabeta")
    # Perfect play from an empty Tic-Tac-Toe board is a known draw.
    assert mm_result["value"] == 0
    assert ab_result["value"] == 0
    assert mm_result["value"] == ab_result["value"]


def test_alphabeta_visits_fewer_nodes_than_minimax_on_empty_board():
    board = ttt.create_empty_board()
    mm_result = ttt.search_best_move(board, ttt.PLAYER_X, "minimax")
    ab_result = ttt.search_best_move(board, ttt.PLAYER_X, "alphabeta")
    assert mm_result["nodes_visited"] == 549946  # full unpruned game tree
    assert ab_result["nodes_visited"] < mm_result["nodes_visited"]


def test_move_ordering_improves_pruning_efficiency():
    board = ttt.create_empty_board()
    ordered = ttt.search_best_move(board, ttt.PLAYER_X, "alphabeta", use_move_ordering=True)
    unordered = ttt.search_best_move(board, ttt.PLAYER_X, "alphabeta", use_move_ordering=False)
    # Same algorithm, same evaluation function -> same value regardless of
    # the order moves are tried in.
    assert ordered["value"] == unordered["value"]
    # But trying the strongest-looking move first prunes more.
    assert ordered["nodes_visited"] < unordered["nodes_visited"]


def test_forced_win_is_found():
    # X has two in a row (0, 1) with O having replied elsewhere (4, 5);
    # it is X's turn and cell 2 completes the line.
    board = ttt.create_empty_board()
    board[0] = ttt.PLAYER_X
    board[1] = ttt.PLAYER_X
    board[4] = ttt.PLAYER_O
    board[5] = ttt.PLAYER_O

    mm_result = ttt.search_best_move(board, ttt.PLAYER_X, "minimax")
    ab_result = ttt.search_best_move(board, ttt.PLAYER_X, "alphabeta")
    assert mm_result["move"] == 2
    assert mm_result["value"] == 1
    assert ab_result["move"] == 2
    assert ab_result["value"] == 1


def test_forced_block_is_found():
    # O has two in a row (0, 1) and it is X's turn; X must block at 2 or
    # lose on O's next move. Blocking leads to a draw with perfect play.
    board = ttt.create_empty_board()
    board[0] = ttt.PLAYER_O
    board[1] = ttt.PLAYER_O
    board[4] = ttt.PLAYER_X

    mm_result = ttt.search_best_move(board, ttt.PLAYER_X, "minimax")
    ab_result = ttt.search_best_move(board, ttt.PLAYER_X, "alphabeta")
    assert mm_result["move"] == 2
    assert mm_result["value"] == 0
    assert ab_result["move"] == 2
    assert ab_result["value"] == 0


def test_evaluate_terminal_uses_single_consistent_scale():
    win_for_ai = list("XX_______".replace("_", ttt.EMPTY))
    win_for_ai[2] = ttt.PLAYER_X
    assert ttt.evaluate_terminal(win_for_ai, ttt.PLAYER_X) == 1
    assert ttt.evaluate_terminal(win_for_ai, ttt.PLAYER_O) == -1

    draw_board = list("XOXXOOOXX")
    assert ttt.evaluate_terminal(draw_board, ttt.PLAYER_X) == 0
    assert ttt.evaluate_terminal(draw_board, ttt.PLAYER_O) == 0


# --- Alpha-beta pruning events ---------------------------------------------

def test_prune_events_never_double_as_enter_events():
    # The live Tic-Tac-Toe page no longer renders a search-tree graph, so
    # search_best_move() defaults to collect_events=False and skips
    # building event dicts entirely. This test specifically checks the
    # *event trace's* correctness (still exercised by anything that opts
    # in, and worth keeping correct), so it must explicitly ask for events.
    board = ttt.create_empty_board()
    board[4] = ttt.PLAYER_X  # mid-game-ish position keeps the tree smaller
    board[0] = ttt.PLAYER_O
    result = ttt.search_best_move(board, ttt.PLAYER_X, "alphabeta", collect_events=True)

    entered_labels = {e["label"] for e in result["events"] if e["type"] == "enter"}
    pruned_labels = set()
    for e in result["events"]:
        if e["type"] == "prune":
            for move in e["skipped_moves"]:
                pruned_labels.add(f"{e['label']}.{move}")

    assert entered_labels.isdisjoint(pruned_labels)


def test_pruned_branches_counted_as_skipped_immediate_moves():
    board = ttt.create_empty_board()
    board[4] = ttt.PLAYER_X
    board[0] = ttt.PLAYER_O
    result = ttt.search_best_move(board, ttt.PLAYER_X, "alphabeta", collect_events=True)

    total_skipped = sum(
        len(e["skipped_moves"]) for e in result["events"] if e["type"] == "prune"
    )
    # Our counting methodology: every skipped immediate move at a prune
    # point counts as one pruned branch - nothing inside it is counted
    # again, since it was genuinely never visited.
    assert total_skipped <= result["pruned_branches"]
    assert result["pruned_branches"] > 0


def test_collect_events_defaults_to_off_but_stats_stay_accurate():
    # This is the optimization at the heart of the lag fix: by default,
    # search_best_move() must not build the per-node event trace at all
    # (the UI no longer draws a search-tree graph or event log), while the
    # node-count statistics - which ARE still displayed - must remain
    # exactly as accurate as when events were collected.
    board = ttt.create_empty_board()
    board[4] = ttt.PLAYER_X
    board[0] = ttt.PLAYER_O

    without_events = ttt.search_best_move(board, ttt.PLAYER_X, "alphabeta")
    with_events = ttt.search_best_move(board, ttt.PLAYER_X, "alphabeta", collect_events=True)

    assert without_events["events"] == []
    assert without_events["total_events_seen"] == 0
    assert with_events["events"] != []

    assert without_events["value"] == with_events["value"]
    assert without_events["move"] == with_events["move"]
    assert without_events["nodes_visited"] == with_events["nodes_visited"]
    assert without_events["terminal_count"] == with_events["terminal_count"]
    assert without_events["pruned_branches"] == with_events["pruned_branches"]


def test_node_counts_are_deterministic_and_reproducible():
    board = ttt.create_empty_board()
    board[4] = ttt.PLAYER_X
    r1 = ttt.search_best_move(board, ttt.PLAYER_X, "alphabeta")
    r2 = ttt.search_best_move(board, ttt.PLAYER_X, "alphabeta")
    assert r1["nodes_visited"] == r2["nodes_visited"]
    assert r1["terminal_count"] == r2["terminal_count"]
    assert r1["pruned_branches"] == r2["pruned_branches"]
    assert r1["value"] == r2["value"]


def test_nodes_visited_equals_number_of_distinct_entered_labels():
    # Few empty cells -> small enough tree to stay under the visual event
    # cap, so every "enter" event is guaranteed to make it into the list.
    board = ttt.create_empty_board()
    board[0] = ttt.PLAYER_X
    board[1] = ttt.PLAYER_X
    board[4] = ttt.PLAYER_O
    board[5] = ttt.PLAYER_O
    result = ttt.search_best_move(board, ttt.PLAYER_X, "alphabeta", collect_events=True)
    entered_labels = {e["label"] for e in result["events"] if e["type"] == "enter"}
    # Only true while events aren't truncated - this position's tree is
    # well under the visual cap, so every "enter" event made it through.
    assert not result["events_truncated"]
    assert len(entered_labels) == result["nodes_visited"]


# --- Flask routes ------------------------------------------------------------

def test_tic_tac_toe_page_loads():
    client = flask_app.test_client()
    res = client.get("/tic-tac-toe")
    assert res.status_code == 200
    assert b"Tic-Tac-Toe" in res.data


def test_new_game_human_first():
    client = flask_app.test_client()
    res = client.post("/api/ttt/new", json={
        "human_symbol": "X", "first_player": "human", "algorithm": "alphabeta",
    })
    data = res.get_json()
    assert res.status_code == 200
    assert data["board"] == [" "] * 9
    assert data["turn"] == "human"
    assert data["human_symbol"] == "X"
    assert data["ai_symbol"] == "O"
    assert "search" not in data  # AI has not moved yet


def test_new_game_ai_first_makes_an_immediate_ai_move():
    client = flask_app.test_client()
    res = client.post("/api/ttt/new", json={
        "human_symbol": "O", "first_player": "ai", "algorithm": "alphabeta",
    })
    data = res.get_json()
    assert res.status_code == 200
    assert data["turn"] == "human"
    assert data["board"].count("X") == 1  # AI plays X here
    assert "search" in data
    assert data["search"]["nodes_visited"] > 0
    assert "time_ms" in data["search"]
    # The API must never ship the per-node event trace to the browser -
    # that payload (and the DOM work it used to drive) was the source of
    # the reported lag, and nothing in the current frontend reads it.
    assert "events" not in data["search"]
    assert "events_truncated" not in data["search"]


def test_new_game_rejects_invalid_settings():
    client = flask_app.test_client()
    res = client.post("/api/ttt/new", json={"human_symbol": "Z"})
    assert res.status_code == 400

    res = client.post("/api/ttt/new", json={"first_player": "robot"})
    assert res.status_code == 400

    res = client.post("/api/ttt/new", json={"algorithm": "greedy"})
    assert res.status_code == 400


def test_move_requires_an_active_game():
    client = flask_app.test_client()
    res = client.post("/api/ttt/move", json={"position": 0})
    assert res.status_code == 400


def test_move_rejects_out_of_range_and_occupied_positions():
    client = flask_app.test_client()
    client.post("/api/ttt/new", json={"human_symbol": "X", "first_player": "human"})

    res = client.post("/api/ttt/move", json={"position": 99})
    assert res.status_code == 400

    res = client.post("/api/ttt/move", json={"position": "a"})
    assert res.status_code == 400

    res = client.post("/api/ttt/move", json={"position": 4})
    assert res.status_code == 200

    res = client.post("/api/ttt/move", json={"position": 4})
    assert res.status_code == 400  # already occupied


def test_move_rejected_when_not_humans_turn():
    client = flask_app.test_client()
    client.post("/api/ttt/new", json={
        "human_symbol": "X", "first_player": "human", "algorithm": "alphabeta",
    })
    # Force the session into a state where it is the AI's turn, the way
    # a tampered or racing request might, and confirm the route still
    # defends against it rather than trusting the client.
    with client.session_transaction() as sess:
        sess["ttt_state"]["turn"] = "ai"
        sess.modified = True

    res = client.post("/api/ttt/move", json={"position": 1})
    assert res.status_code == 400


def test_moves_are_rejected_after_game_is_over():
    client = flask_app.test_client()
    client.post("/api/ttt/new", json={
        "human_symbol": "X", "first_player": "human", "algorithm": "alphabeta",
    })

    # Play until the game ends. The AI is unbeatable, so repeatedly taking
    # whatever cell is still open is enough to drive the game to a
    # terminal state (a loss or draw for the human) within at most 9 moves.
    game_over = False
    for _ in range(9):
        board = client.get("/api/ttt/state").get_json()["board"]
        empties = [i for i, cell in enumerate(board) if cell == " "]
        if not empties:
            break
        move_data = client.post("/api/ttt/move", json={"position": empties[0]}).get_json()
        if move_data.get("game_over"):
            game_over = True
            break
    assert game_over

    res = client.post("/api/ttt/move", json={"position": 0})
    assert res.status_code == 400


def test_reset_clears_board_but_keeps_valid_settings():
    client = flask_app.test_client()
    client.post("/api/ttt/new", json={
        "human_symbol": "X", "first_player": "human", "algorithm": "alphabeta",
    })
    client.post("/api/ttt/move", json={"position": 4})
    res = client.post("/api/ttt/reset", json={"first_player": "human"})
    data = res.get_json()
    assert res.status_code == 200
    assert data["board"] == [" "] * 9
    assert data["game_over"] is False


def test_set_algorithm_without_resetting_board():
    client = flask_app.test_client()
    client.post("/api/ttt/new", json={
        "human_symbol": "X", "first_player": "human", "algorithm": "minimax",
    })
    client.post("/api/ttt/move", json={"position": 4})
    res = client.post("/api/ttt/algorithm", json={"algorithm": "alphabeta"})
    data = res.get_json()
    assert res.status_code == 200
    assert data["algorithm"] == "alphabeta"
    assert data["board"][4] != " "  # board untouched by the algorithm switch


def test_compare_endpoint_agrees_across_algorithms():
    client = flask_app.test_client()
    client.post("/api/ttt/new", json={
        "human_symbol": "X", "first_player": "human", "algorithm": "alphabeta",
    })
    client.post("/api/ttt/move", json={"position": 4})
    res = client.post("/api/ttt/compare", json={})
    data = res.get_json()
    assert res.status_code == 200
    assert data["values_agree"] is True
    assert data["minimax"]["value"] == data["alphabeta_ordered"]["value"]
    assert data["nodes_saved_by_pruning"] >= 0
    # Compare mode only ever displays final stats, never a tree or log, so
    # none of its three results should carry an event trace either.
    for key in ("minimax", "alphabeta_ordered", "alphabeta_unordered"):
        assert "events" not in data[key]
        assert "time_ms" in data[key]


def test_two_sessions_do_not_share_game_state():
    client_a = flask_app.test_client()
    client_b = flask_app.test_client()
    client_a.post("/api/ttt/new", json={
        "human_symbol": "X", "first_player": "human", "algorithm": "alphabeta",
    })
    client_a.post("/api/ttt/move", json={"position": 0})

    # client_b never started a game, so it must not see client_a's board.
    res_b = client_b.get("/api/ttt/state")
    assert res_b.status_code == 404

    res_a = client_a.get("/api/ttt/state")
    assert res_a.status_code == 200
    assert res_a.get_json()["board"][0] == "X"


# --- Separation from the original Minimax simulation ------------------------

def test_original_minimax_routes_are_unaffected_by_the_new_blueprint():
    client = flask_app.test_client()
    tree_res = client.get("/api/tree")
    assert tree_res.status_code == 200
    assert tree_res.get_json()["label"] == "Root"

    run_res = client.get("/api/run?algo=alphabeta")
    run_data = run_res.get_json()
    assert run_res.status_code == 200
    assert run_data["root_value"] == 5
    assert run_data["nodes_visited"] == 11


def test_original_game_tree_object_is_never_touched_by_ttt_module():
    import minimax as mm
    assert mm.GAME_TREE == [[[3, 5], [6, 9]], [[1, 2], [0, -1]]]
