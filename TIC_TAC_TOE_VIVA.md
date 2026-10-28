# Tic-Tac-Toe Minimax / Alpha-Beta — Viva Preparation

This document explains the Tic-Tac-Toe feature added to the Minimax &
Alpha-Beta Pruning Visualizer project, so you can walk an examiner through
it confidently. Every claim here matches the actual code in `tic_tac_toe.py`
and `tic_tac_toe_routes.py` — nothing below is invented or aspirational.

## 1. Problem statement and objectives

**Problem:** Tic-Tac-Toe is a two-player, zero-sum, perfect-information
game. "Zero-sum" means one player's gain is exactly the other's loss;
"perfect information" means both players can see the whole board at all
times — there is nothing hidden. For such games, game theory guarantees
that an **optimal strategy** exists: a way of playing that is never beaten
by any possible opponent strategy. The objective of this feature is to:

1. Implement that optimal strategy using **Minimax**, a recursive
   algorithm that explores every possible way the game could continue.
2. Implement **Alpha-Beta Pruning**, an optimization of Minimax that
   reaches the *same* decision while examining *fewer* positions.
3. Make the search's internal behaviour visible step by step, so the
   abstract algorithm from the textbook can be seen operating on a
   concrete, familiar game.

## 2. How the game is represented in Python

The board is a flat Python list of 9 characters:

```
 0 | 1 | 2
---+---+---
 3 | 4 | 5
---+---+---
 6 | 7 | 8
```

Each entry is `"X"`, `"O"`, or `" "` (a space, meaning empty). There are
eight ways to win, stored as `WIN_LINES` — three rows, three columns, and
two diagonals, each a tuple of three board indexes.

Two design choices matter and are worth explaining if asked:

- **`apply_move` never mutates the board it's given — it returns a new
  list.** Minimax explores many hypothetical futures branching off the
  same board. If moves mutated a shared list in place, one branch's
  exploration would corrupt the board another branch still needs. Copying
  keeps every recursive call's view of the world independent — this is
  what makes the recursion safe.
- **No module-level global state.** The original `minimax.py` example uses
  a global `nodes_visited` counter, which is fine for a single, one-shot
  script. The Tic-Tac-Toe module instead threads a small `stats` dictionary
  through every recursive call as an argument. That dictionary belongs to
  one search and nobody else's — so two games (two browser tabs, two
  students on the same server) can never corrupt each other's counts. The
  Flask layer goes one step further and keeps each *game's* state in a
  signed session cookie rather than a server-side variable, for the same
  reason.

## 3. The evaluation function (shared by both algorithms)

```python
def evaluate_terminal(board, ai_player):
    winner = get_winner(board)
    if winner == ai_player:
        return 1
    if winner is not None:
        return -1
    return 0
```

This is called **only on terminal boards** (a board where someone has won,
or every cell is full). It is the single source of truth for "how good is
this outcome for the AI," and both Minimax and Alpha-Beta call the exact
same function — which is exactly why they are guaranteed to agree on the
value of any position (see the tests
`test_minimax_and_alphabeta_agree_on_empty_board_value`,
`test_forced_win_is_found`, `test_forced_block_is_found`).

## 4. MAX, MIN, and whose turn it is

- `ai_player` is fixed for an entire search — it's always the symbol the
  AI is playing (`"X"` or `"O"`), decided once per game.
- `current_player` changes every recursive call — it's whoever is about to
  move *at this node*.
- `is_max` is `True` exactly when `current_player == ai_player`.

So **MAX is always the AI**, trying to steer the game toward `+1`, and
**MIN is always the human opponent**, trying to steer it toward `-1`. The
two roles strictly alternate on every ply (every single move), because
`current_player` flips (`other_player`) on every recursive call.

## 5. Step-by-step: how Minimax decides a move

```python
def minimax(board, ai_player, current_player, is_max, depth, stats,
            on_event=None, label="Root"):
    stats["nodes_visited"] += 1
    if is_terminal(board):
        return evaluate_terminal(board, ai_player), None
    best_value = -inf if is_max else inf
    for move in ordered_moves(board):
        child_board = apply_move(board, move, current_player)
        child_value, _ = minimax(child_board, ai_player,
                                  other_player(current_player),
                                  not is_max, depth + 1, stats, ...)
        if is_max:
            if child_value > best_value: best_value, best_move = child_value, move
        else:
            if child_value < best_value: best_value, best_move = child_value, move
    return best_value, best_move
```

In plain English:

1. **Terminal check first.** The very first thing every call does is ask
   "is this game already over?" If so, there is nothing to search — just
   score the board and return. This is what stops the recursion from ever
   trying to play a 10th move on a full board.
2. **Recursion.** If the game isn't over, try every legal move, recursively
   asking "what is the value of the position *after* this move?" — with
   the MAX/MIN role flipped, because it's now the other player's turn.
3. **Combine.** MAX keeps the *largest* value seen among its children
   (because the AI picks whichever move leads to the best outcome for
   itself). MIN keeps the *smallest* value seen among its children
   (because the opponent, playing optimally, picks whichever move is worst
   for the AI).
4. **Propagate up.** The chosen value travels back up to the parent call,
   which is itself in the middle of a `max(...)`/`min(...)` comparison one
   level up. This is why it's called recursive — the same function calls
   itself to solve smaller sub-problems, and the final answer is built
   from the answers to those sub-problems.

Minimax is *exhaustive*: it visits every reachable position exactly once.
From an empty board that is **549,946 nodes** (measured directly by
`test_alphabeta_visits_fewer_nodes_than_minimax_on_empty_board`) — large,
but small enough that Python finishes in a couple of seconds.

## 6. Step-by-step: how Alpha-Beta Pruning does less work for the same answer

Alpha-Beta carries two extra numbers through the recursion:

- **alpha** — the best value the MAX player can *already* guarantee
  somewhere above the current node (starts at −∞).
- **beta** — the best value the MIN player can *already* guarantee
  somewhere above the current node (starts at +∞).

After evaluating each child, a MAX node updates `alpha = max(alpha, value)`
and a MIN node updates `beta = min(beta, value)`. Then comes the key line:

```python
if alpha >= beta:
    break  # prune: skip the remaining children
```

**What this condition means:** by the time `alpha >= beta`, the MAX player
already has a way to force an outcome of at least `alpha` somewhere else in
the tree, *and* the MIN player already has a way to hold this branch down
to at most `beta`. Since `alpha >= beta`, neither player can do any better
by continuing to explore this node's remaining children — whoever is
"in control" one level up will simply steer play toward the option they
already know about instead. The remaining children are therefore
**mathematically irrelevant to the final answer**, so they are never
visited. That is what "pruning" means here: not an approximation, not a
heuristic — a proof that those branches cannot change the result.

Because Alpha-Beta skips branches that provably cannot matter, it always
returns the **same value** as plain Minimax (verified directly by
`test_minimax_and_alphabeta_agree_on_empty_board_value`,
`test_forced_win_is_found`, `test_forced_block_is_found`) while visiting
**far fewer nodes** (7,275 instead of 549,946 from an empty board, in the
default configuration — see §9).

## 7. A small worked example

Take this position, with X to move:

```
 X | X | .        X has two in a row (0, 1) and an open
-----------       third cell (2). O has replied at 4 and 5.
 . | O | O
-----------
 . | . | .
```

- Trying move **2** completes X's row → terminal, evaluates to `+1`
  immediately. MAX sees a child worth `+1`, which is the best possible
  value, so `alpha` becomes `1`.
- Any *other* move keeps the game going into O's turn, and because O then
  plays optimally to avoid losing, those branches are worth at most `0` or
  `-1` for X once fully explored.
- Once MAX has already found a `+1` child, `alpha = 1`. If the search is
  still exploring an unfinished MIN child whose `beta` has already dropped
  to `1` or below while a sibling move is still untried, the condition
  `alpha >= beta` fires and the remaining untried moves at that MIN node
  are skipped — they cannot change the fact that X's best is `+1` via move
  `2`.

This matches `test_forced_win_is_found`: both algorithms return
`move == 2, value == 1`.

## 8. Node-counting methodology (how to reproduce every number shown)

Every search call carries one `stats` dictionary with exactly three
counters, updated at exactly one place each in the code:

| Counter | Incremented... | Meaning |
|---|---|---|
| `nodes_visited` | once at the top of *every* recursive call (`minimax`/`alphabeta`) | Every board position the algorithm actually looked at, terminal or not. |
| `terminal_count` | once whenever `is_terminal(board)` is true | How many of those visited positions were finished games (needed an evaluation). |
| `pruned_branches` | by `len(skipped)` whenever `alpha >= beta` fires | How many **immediate child moves** were skipped at a cutoff — not the nodes *inside* those children, since those were genuinely never visited and so are correctly never counted as visited either. |

This means `nodes_visited` is always exactly equal to the number of
distinct "enter" events recorded (checked by
`test_nodes_visited_equals_number_of_distinct_entered_labels`), and a
pruned branch's descendants never also show up as "visited" (checked by
`test_prune_events_never_double_as_enter_events`). Because nothing here
depends on random numbers or wall-clock time, running the same search
twice always produces identical counts
(`test_node_counts_are_deterministic_and_reproducible`).

**Why the on-screen tree diagram can show fewer nodes than the stats bar.**
The backend always computes the complete, correct search and the stats
above are always exact. But from an empty board that search produces
*hundreds of thousands* of recorded steps — far too many to draw as
on-screen elements without freezing the browser. So the list of steps sent
to the browser for drawing is capped at the first 3,000 (`MAX_VISUAL_EVENTS`
in `tic_tac_toe.py`), in true execution order — it is a real prefix of the
actual run, never a fabricated summary. A banner appears on the page saying
exactly how many of the real events were drawn. This only affects what is
*drawn*; it never affects what is *counted*.

## 9. Move ordering: why it changes pruning efficiency but not the answer

`ordered_moves(board, use_move_ordering)` decides which legal move the
search tries *first* at each node: center → corners → edges when ordering
is on, or plain ascending order when it's off. This can only affect
**Alpha-Beta**, and only affects *how quickly* `alpha`/`beta` tighten, not
*what* the final value is — Minimax visits every child regardless of order,
and Alpha-Beta's final returned value doesn't depend on the order moves are
tried in either (only on which values exist among the children).

Measured directly on an empty board (`python tic_tac_toe.py`, and
`test_move_ordering_improves_pruning_efficiency`):

| Search | Nodes visited | Pruned branches |
|---|---:|---:|
| Minimax (no pruning) | 549,946 | 0 |
| Alpha-Beta, natural order (0,1,2,…) | 18,297 | 6,930 |
| Alpha-Beta, center-first order | 7,275 | 3,668 |

Trying the strongest-looking move first means `alpha` (or `beta`) reaches
its final, tight value sooner, which means later, weaker-looking siblings
are more likely to trigger the `alpha >= beta` cutoff before being
searched at all. Weaker move ordering still reaches the identical answer —
it just has to look at more of the tree to prove it.

## 10. Time and space complexity

- **Minimax:** time is `O(b^d)`, where `b` is the branching factor (at most
  9, shrinking by one each ply) and `d` is the remaining depth (at most 9).
  Space is `O(d)` — only the current path down the tree needs to be kept
  on the call stack at once; siblings are discarded as soon as they return.
- **Alpha-Beta:** same `O(d)` space. Time is still `O(b^d)` in the worst
  case (no cutoffs), but with good move ordering it approaches `O(b^(d/2))`
  — intuitively, good ordering lets it search to roughly *half the depth*
  for the same effective effort, because early strong moves prune large
  portions of later siblings' subtrees. The measured numbers in §9 show
  this concretely: 7,275 nodes instead of 549,946 is roughly `b^(d/2)`-like
  behaviour, not a coincidence.

## 11. 20+ viva questions and answers

1. **Q: Why does the AI never lose at Tic-Tac-Toe?**
   A: Because Minimax searches the entire remaining game tree and always
   picks the move with the best guaranteed outcome against an opponent who
   also plays optimally. Tic-Tac-Toe is a known draw with perfect play, so
   the AI can only win if the human makes a mistake, and can never do
   worse than a draw.

2. **Q: What does "MAX" mean here, concretely?**
   A: The player whose turn it currently is, exactly when that player is
   the AI. At a MAX node the algorithm takes the largest value among its
   children, because the AI wants the best outcome for itself.

3. **Q: What does "MIN" mean here?**
   A: The player whose turn it currently is, exactly when that player is
   the human opponent. At a MIN node the algorithm takes the smallest
   value, modelling a worst-case, fully rational opponent.

4. **Q: What are alpha and beta, in one sentence each?**
   A: Alpha is the best value MAX can already guarantee from elsewhere in
   the tree; beta is the best value MIN can already guarantee from
   elsewhere in the tree.

5. **Q: What exactly triggers a prune, and why is that condition correct?**
   A: `alpha >= beta`. It's correct because once it holds, neither player
   benefits from exploring this node further — whichever of them is in
   control one level up already has an equal-or-better option elsewhere,
   so the remaining children cannot change the final decision.

6. **Q: Does Alpha-Beta ever return a different move than Minimax?**
   A: It can choose a *different but equally optimal* move when several
   moves tie in value (the spec explicitly allows this); it never returns
   a different *value*. See `test_forced_win_is_found` for a case where
   both agree on both the move and the value.

7. **Q: Why is the evaluation function only `+1`/`0`/`-1`, with no bonus
   for winning faster?**
   A: To keep the textbook Minimax model simple: it only measures the
   final outcome of optimal play, not how many moves it takes to reach it.
   A consequence worth knowing: against an imperfect opponent, the AI may
   not always choose the fastest available win, because every winning
   move is valued identically.

8. **Q: Why does `apply_move` return a new board instead of modifying the
   one it's given?**
   A: Because Minimax explores many branches from the same board. Mutating
   a shared list in place would let one branch's trial moves leak into
   another branch still being explored. Returning a fresh copy keeps every
   recursive call's exploration independent.

9. **Q: Why is there no global `nodes_visited` variable like in
   `minimax.py`?**
   A: Because this module must support multiple independent games running
   at once (different browser sessions). A module-level global would be
   shared and corrupted by concurrent searches; a `stats` dict passed into
   each call belongs only to that call's search.

10. **Q: Where does the actual game state live between HTTP requests?**
    A: In the browser's signed Flask session cookie, under the key
    `"ttt_state"` — never in a Python global or module-level dict. That is
    what keeps two browser tabs' games from mixing.

11. **Q: What happens if a move request names an already-occupied cell?**
    A: `/api/ttt/move` checks `state["board"][position] != EMPTY` and
    returns HTTP 400 with an error message before touching the algorithm.

12. **Q: What happens if a move is sent after the game is already over?**
    A: Rejected with HTTP 400 — checked via `state["game_over"]` before
    any board mutation.

13. **Q: Why does the tree diagram not show every node the algorithm
    visited?**
    A: Because the real tree can have over half a million nodes from an
    early board; rendering that many DOM elements would freeze the
    browser. The diagram draws the first 3,000 real recorded steps (a true
    prefix of the actual execution, never a fabrication); the statistics
    panel above it always reflects the complete search.

14. **Q: How do you know the node counts shown are accurate and not
    estimated?**
    A: `stats["nodes_visited"]` is incremented once per recursive call,
    unconditionally, regardless of whether that call's event made it into
    the (possibly truncated) list sent to the browser. The test
    `test_nodes_visited_equals_number_of_distinct_entered_labels` checks
    this count equals the number of distinct positions actually entered,
    for a case small enough to stay under the truncation limit.

15. **Q: What counts as "one pruned branch"?**
    A: One immediate child move skipped at a cutoff point. If three
    remaining moves are skipped at once, that's three pruned branches —
    not the (possibly much larger) number of positions that exist deeper
    inside those unexplored moves, since none of those deeper positions
    were ever visited.

16. **Q: Why does move ordering help Alpha-Beta but not Minimax?**
    A: Minimax has no cutoff condition — it visits every child regardless
    of order, so reordering changes nothing about its node count. Alpha-
    Beta's cutoff depends on how tight `alpha`/`beta` are *when* a sibling
    is about to be tried; trying stronger moves first tightens the bounds
    sooner, so later siblings are more likely to be prunable.

17. **Q: Is there a transposition table or caching of repeated positions?**
    A: No — deliberately left out, so that the recorded events are always
    a faithful, literal trace of the real recursive calls, with nothing
    hidden behind a cache lookup. This keeps the visualization's claim
    ("you are watching the real algorithm run") strictly true.

18. **Q: What's the time complexity of Minimax here, and why is the space
    complexity so much smaller?**
    A: Time is `O(b^d)` (exponential in the remaining depth). Space is only
    `O(d)`, because recursion only needs to remember the single path from
    the root down to the current node — completed siblings are discarded
    once they return their value.

19. **Q: How is a draw detected?**
    A: `is_board_full(board)` is true (no `" "` cells left) and
    `get_winner(board)` is `None` — checked by `is_terminal`, and scored as
    `0` by `evaluate_terminal`.

20. **Q: How does the Flask layer guarantee the original Minimax demo
    still works unchanged?**
    A: The only two edits to `app.py` are a `secret_key` assignment and one
    `app.register_blueprint(ttt_bp)` call — none of the original routes,
    functions, or `minimax.py` were touched. `test_original_minimax_routes_are_unaffected_by_the_new_blueprint`
    and `test_original_game_tree_object_is_never_touched_by_ttt_module`
    check this directly, and the full original `tests/test_minimax.py`
    suite (14 tests) still passes unmodified.

21. **Q: Why is the AI's symbol allowed to be either X or O?**
    A: `ai_player` is just a parameter — `evaluate_terminal` compares the
    winner against whichever symbol was passed in, so the same code works
    identically regardless of which symbol the AI happens to be playing
    this game.

22. **Q: What would need to change to adapt this Minimax implementation to
    a bigger game, like Connect Four?**
    A: The board representation, `get_winner`, `available_moves`, and
    `apply_move` would need to change for the new rules, but the recursive
    MAX/MIN structure, the alpha-beta pruning condition, and the general
    approach (search to a terminal state or a depth limit, then back values
    up) stay the same. In practice, a game that large would also need a
    depth limit and a heuristic (non-terminal) evaluation function, since
    searching to the end of the game would be computationally infeasible.

## 12. 3–5 minute demonstration script

1. **(30s) Open both pages.** Show the original demo at `/` running
   Alpha-Beta on the small fixed tree, pointing out the Nodes Visited vs.
   Nodes Saved stats. Say: "This is the original project; it's untouched."
2. **(30s) Navigate to `/tic-tac-toe`.** Say: "This is the new feature —
   same two algorithms, now deciding real Tic-Tac-Toe moves."
3. **(60s) Play a quick game.** Pick X, human-first, Alpha-Beta. Make an
   obviously bad move (e.g. a corner instead of the center) and show the
   AI immediately punishing it, or make good moves and show the game end
   in a draw. While the AI "thinks," point at the search-tree panel
   animating and read one or two lines from the plain-English explanation
   panel out loud.
4. **(45s) Point at a prune event.** Pause the animation on a node styled
   as pruned, and explain: "alpha was already ≥ beta here, so the
   remaining moves at this node were skipped — they're proven not to
   matter, not just assumed unlikely."
5. **(45s) Click "Compare Algorithms Now."** Show the three rows (Minimax,
   Alpha-Beta ordered, Alpha-Beta unordered): same value in all three,
   very different node counts. Say: "This proves pruning doesn't change
   the answer, only the amount of work — and move ordering makes pruning
   even more effective."
6. **(30s) Mention the tests.** "`pytest tests -v` — 46 tests, including
   forced-win and forced-block positions, and a check that the original
   14 tests still pass unmodified."

Total: ~4 minutes, with room to answer a question or two from the sections
above.
