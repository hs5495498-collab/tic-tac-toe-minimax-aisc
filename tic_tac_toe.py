"""Tic-Tac-Toe game rules plus a *real* recursive Minimax and Alpha-Beta
Pruning implementation that plays it optimally.

This file is pure Python with **no Flask import and no module-level mutable
state** (no globals like the `nodes_visited` counter in minimax.py). Every
function either takes the data it needs as an argument or returns new data,
so two games running at the same time (e.g. two browser tabs) can never
leak state into each other. The Flask layer in `tic_tac_toe_routes.py` is
the only place that remembers "whose game is this" (via a per-browser
session), and it does that by passing a `stats` dict into the search
functions below rather than touching a global.

Board representation
---------------------
A board is a list of 9 characters, read left-to-right / top-to-bottom:

    0 | 1 | 2
    3 | 4 | 5
    6 | 7 | 8

Each cell holds "X", "O", or " " (a single space) for empty.

Search events
-------------
Both `minimax` and `alphabeta` accept an optional `on_event(event_dict)`
callback. Every time the recursion enters a node, evaluates a leaf, updates
a MAX/MIN node's running best value, prunes a branch, or returns a value,
it calls `on_event` with a small dictionary describing exactly what just
happened (including a snapshot of the board at that node). The Flask layer
collects these into an ordered list and ships them to the browser as JSON,
so the animation you see is a direct recording of the real recursion -
never a separate re-implementation in JavaScript.
"""

import math
import time

EMPTY = " "
PLAYER_X = "X"
PLAYER_O = "O"

# The eight ways to win: three rows, three columns, two diagonals.
WIN_LINES = [
    (0, 1, 2), (3, 4, 5), (6, 7, 8),   # rows
    (0, 3, 6), (1, 4, 7), (2, 5, 8),   # columns
    (0, 4, 8), (2, 4, 6),              # diagonals
]

# Move ordering used by Alpha-Beta: try the center first, then corners,
# then edges. Trying the strongest-looking moves first does not change
# *what* Alpha-Beta returns (the final value is always the same - see
# `test_minimax_and_alphabeta_agree_on_value` in the tests), but it changes
# *how many nodes it has to look at* before alpha/beta cross and it can
# prune, because a better move found early tightens alpha/beta sooner.
CENTER_FIRST_ORDER = [4, 0, 2, 6, 8, 1, 3, 5, 7]
NATURAL_ORDER = [0, 1, 2, 3, 4, 5, 6, 7, 8]


def create_empty_board():
    """A brand-new, empty 3x3 board as a flat list of 9 spaces."""
    return [EMPTY] * 9


def other_player(player):
    """The opponent of X is O, and the opponent of O is X."""
    return PLAYER_O if player == PLAYER_X else PLAYER_X


def get_winner(board):
    """Return 'X' or 'O' if that player has completed a line, else None."""
    for a, b, c in WIN_LINES:
        if board[a] != EMPTY and board[a] == board[b] == board[c]:
            return board[a]
    return None


def is_board_full(board):
    """True once every cell has a mark (no more legal moves)."""
    return EMPTY not in board


def is_terminal(board):
    """A game is over once somebody has won or the board is full (a draw)."""
    return get_winner(board) is not None or is_board_full(board)


def available_moves(board):
    """List of empty cell indexes, in natural (ascending) order."""
    return [i for i in range(9) if board[i] == EMPTY]


def ordered_moves(board, use_move_ordering=True):
    """Available moves, optionally reordered center-first/corners/edges.

    `use_move_ordering=False` falls back to plain ascending order. Both
    orderings are used purely to decide *which move to look at next*; they
    never change which moves exist, so they cannot change the final
    Minimax/Alpha-Beta value - only how quickly Alpha-Beta can prune.
    """
    priority = CENTER_FIRST_ORDER if use_move_ordering else NATURAL_ORDER
    empties = set(available_moves(board))
    return [pos for pos in priority if pos in empties]


def apply_move(board, position, player):
    """Return a *new* board with `player` placed at `position`.

    We never mutate the caller's board in place. Minimax/Alpha-Beta explore
    many hypothetical futures from the same board, and if we mutated the
    shared list instead of copying it, one branch's moves would corrupt the
    board another branch is still exploring. Returning a fresh copy keeps
    every recursive call fully isolated, which is what makes recursion
    safe here.
    """
    if board[position] != EMPTY:
        raise ValueError(f"Cell {position} is already occupied.")
    new_board = list(board)
    new_board[position] = player
    return new_board


def evaluate_terminal(board, ai_player):
    """The single evaluation function shared by Minimax and Alpha-Beta.

    This is the only place "what counts as good for the AI" is defined, so
    both algorithms are guaranteed to agree on the value of any finished
    game:
        +1  -> the AI ("ai_player") has won
        -1  -> the opponent has won
         0  -> draw
    Only call this once `is_terminal(board)` is True.
    """
    winner = get_winner(board)
    if winner == ai_player:
        return 1
    if winner is not None:
        return -1
    return 0


def new_stats():
    """A fresh, isolated counters dict to pass into a search.

    Using a plain dict that the caller owns (instead of a module-level
    global like `nodes_visited` in minimax.py) means two searches - even
    two running "at the same time" for two different browser tabs - can
    never stomp on each other's counts.
    """
    return {"nodes_visited": 0, "terminal_count": 0, "pruned_branches": 0}


def _board_label(label, move):
    return label if move is None else f"{label}.{move}"


def minimax(board, ai_player, current_player, is_max, depth, stats,
            on_event=None, label="Root"):
    """Plain recursive Minimax for Tic-Tac-Toe.

    - `ai_player` never changes across the recursion: it is always the
      player the AI is trying to win as.
    - `current_player` is whoever is about to move *at this node*.
    - `is_max` is True exactly when `current_player == ai_player`: the AI
      is the MAX player (trying to maximize the evaluation), and the human
      opponent is the MIN player (trying to minimize it). This is the
      "alternating MAX and MIN turns" the algorithm relies on.
    - Returns (value, best_move): `value` is the Minimax value of this
      board, and `best_move` is the move that achieves it (None for a
      terminal node, where no move is made).
    """
    stats["nodes_visited"] += 1
    if on_event:
        on_event({"type": "enter", "label": label, "depth": depth,
                  "is_max": is_max, "board": list(board)})

    # Terminal-state check: stop recursing the instant the game is decided,
    # instead of still trying to place marks on a finished board.
    if is_terminal(board):
        stats["terminal_count"] += 1
        value = evaluate_terminal(board, ai_player)
        if on_event:
            on_event({"type": "leaf", "label": label, "depth": depth,
                      "value": value, "board": list(board),
                      "winner": get_winner(board)})
        return value, None

    best_value = -math.inf if is_max else math.inf
    best_move = None
    next_player = other_player(current_player)

    for move in ordered_moves(board):
        child_board = apply_move(board, move, current_player)
        child_value, _ = minimax(
            child_board, ai_player, next_player, not is_max, depth + 1,
            stats, on_event, _board_label(label, move),
        )

        if is_max:
            if child_value > best_value:
                best_value, best_move = child_value, move
        else:
            if child_value < best_value:
                best_value, best_move = child_value, move

        if on_event:
            on_event({"type": "update", "label": label, "depth": depth,
                      "is_max": is_max, "value": best_value,
                      "move": move, "board": list(board)})

    if on_event:
        on_event({"type": "return", "label": label, "depth": depth,
                  "is_max": is_max, "value": best_value, "board": list(board)})
    return best_value, best_move


def alphabeta(board, ai_player, current_player, alpha, beta, is_max, depth,
              stats, on_event=None, label="Root", use_move_ordering=True):
    """Recursive Alpha-Beta Pruning for Tic-Tac-Toe.

    Same MAX/MIN structure as `minimax` above, plus two running bounds:
      - `alpha` = the best (highest) value the MAX player can already
        guarantee somewhere above this node.
      - `beta`  = the best (lowest) value the MIN player can already
        guarantee somewhere above this node.

    The pruning condition `alpha >= beta` means: "the MAX player already
    has a way to force at least `alpha`, but the MIN player already has a
    way to force the result down to at most `beta`. Since alpha >= beta,
    whichever of them is in control at this node can never do better than
    they already can elsewhere, so there is no point in looking at this
    node's remaining children - they cannot change the outcome." Skipping
    those children is what "pruning" means; we never visit them, and they
    are never counted as visited.
    """
    stats["nodes_visited"] += 1
    if on_event:
        on_event({"type": "enter", "label": label, "depth": depth,
                  "is_max": is_max, "alpha": alpha, "beta": beta,
                  "board": list(board)})

    if is_terminal(board):
        stats["terminal_count"] += 1
        value = evaluate_terminal(board, ai_player)
        if on_event:
            on_event({"type": "leaf", "label": label, "depth": depth,
                      "value": value, "board": list(board),
                      "winner": get_winner(board)})
        return value, None

    best_move = None
    next_player = other_player(current_player)
    moves = ordered_moves(board, use_move_ordering)

    if is_max:
        value = -math.inf
        for i, move in enumerate(moves):
            child_board = apply_move(board, move, current_player)
            child_value, _ = alphabeta(
                child_board, ai_player, next_player, alpha, beta, False,
                depth + 1, stats, on_event, _board_label(label, move),
                use_move_ordering,
            )
            if child_value > value:
                value, best_move = child_value, move
            alpha = max(alpha, value)
            if on_event:
                on_event({"type": "update", "label": label, "depth": depth,
                          "is_max": is_max, "value": value, "alpha": alpha,
                          "beta": beta, "move": move, "board": list(board)})
            # Pruning condition: MAX already has >= alpha elsewhere, and
            # MIN can already hold this branch to <= beta, so once
            # alpha >= beta the remaining untried moves cannot matter.
            if alpha >= beta:
                skipped = moves[i + 1:]
                stats["pruned_branches"] += len(skipped)
                if on_event and skipped:
                    on_event({"type": "prune", "label": label, "depth": depth,
                              "alpha": alpha, "beta": beta,
                              "skipped_moves": skipped, "board": list(board)})
                break
    else:
        value = math.inf
        for i, move in enumerate(moves):
            child_board = apply_move(board, move, current_player)
            child_value, _ = alphabeta(
                child_board, ai_player, next_player, alpha, beta, True,
                depth + 1, stats, on_event, _board_label(label, move),
                use_move_ordering,
            )
            if child_value < value:
                value, best_move = child_value, move
            beta = min(beta, value)
            if on_event:
                on_event({"type": "update", "label": label, "depth": depth,
                          "is_max": is_max, "value": value, "alpha": alpha,
                          "beta": beta, "move": move, "board": list(board)})
            if alpha >= beta:
                skipped = moves[i + 1:]
                stats["pruned_branches"] += len(skipped)
                if on_event and skipped:
                    on_event({"type": "prune", "label": label, "depth": depth,
                              "alpha": alpha, "beta": beta,
                              "skipped_moves": skipped, "board": list(board)})
                break

    if on_event:
        on_event({"type": "return", "label": label, "depth": depth,
                  "is_max": is_max, "value": value, "board": list(board)})
    return value, best_move


# If a caller opts into event collection (`collect_events=True`), events are
# still capped here, because the full Tic-Tac-Toe search tree from an early
# board can contain hundreds of thousands of nodes - more than any browser
# should try to draw as DOM elements. The cap only limits what would be
# *drawn*; `stats` below is always updated for every node the real
# algorithm visits, so the node counts are always the true, complete
# totals, never an estimate based on the trimmed event list.
#
# `collect_events` defaults to False: the live Tic-Tac-Toe page no longer
# animates a search-tree graph or a step-by-step event log (that UI was
# removed because building and rendering those events - a board-state
# snapshot for every single node visited - was the main source of lag,
# especially from an early/empty board). Building the event dicts (each
# one copies the board) has a real, measurable cost even when most of them
# are immediately discarded, so skipping it entirely when nobody asked for
# it is a genuine speedup, not just a smaller HTTP response - see the
# timing comparison in the project's optimization notes. The event
# machinery itself is kept (and still exercised by
# tests/test_tic_tac_toe.py) because it is harmless, already correct, and
# may be useful again later (e.g. a lightweight debugging dump); it is
# simply no longer switched on by default.
MAX_VISUAL_EVENTS = 3000


def search_best_move(board, ai_player, algorithm, use_move_ordering=True,
                      collect_events=False):
    """Run the real search and return the move, value, and node-count stats.

    `algorithm` is "minimax" or "alphabeta". Pass `collect_events=True` to
    additionally get back a (possibly truncated) ordered list of search
    events describing every node entered/evaluated/updated/pruned/returned
    - off by default because nothing in the current UI draws them, and
    constructing them (a board-state copy per event) is not free.
    """
    if algorithm not in ("minimax", "alphabeta"):
        raise ValueError(f"Unknown algorithm: {algorithm!r}")

    stats = new_stats()
    events = []
    total_events_seen = 0
    on_event = None

    if collect_events:
        def collect(event):
            nonlocal total_events_seen
            total_events_seen += 1
            if len(events) < MAX_VISUAL_EVENTS:
                events.append(event)
        on_event = collect

    start_time = time.perf_counter()
    if algorithm == "minimax":
        value, move = minimax(board, ai_player, ai_player, True, 0, stats, on_event)
    else:
        value, move = alphabeta(
            board, ai_player, ai_player, -math.inf, math.inf, True, 0,
            stats, on_event, use_move_ordering=use_move_ordering,
        )
    elapsed_ms = (time.perf_counter() - start_time) * 1000

    return {
        "algorithm": algorithm,
        "value": value,
        "move": move,
        "nodes_visited": stats["nodes_visited"],
        "terminal_count": stats["terminal_count"],
        "pruned_branches": stats["pruned_branches"],
        "time_ms": round(elapsed_ms, 2),
        "events": events,
        "events_truncated": total_events_seen > len(events),
        "total_events_seen": total_events_seen,
    }


if __name__ == "__main__":
    board = create_empty_board()
    print("Searching the best opening move for X with Alpha-Beta Pruning...")
    result = search_best_move(board, PLAYER_X, "alphabeta")
    print(f"Best move: {result['move']}  value: {result['value']}  "
          f"nodes visited: {result['nodes_visited']}  "
          f"terminal states: {result['terminal_count']}  "
          f"pruned branches: {result['pruned_branches']}  "
          f"({result['time_ms']:.2f}ms)")
