# Minimax & Alpha-Beta Pruning Visualizer

**Author:** Harsh Kumar Singh

A beginner-friendly Flask project demonstrating the **Minimax** and
**Alpha-Beta Pruning** algorithms in two ways:

1. On a small, fixed example game tree (the original demo).
2. On a full, playable game of **Tic-Tac-Toe**, where the same two
   algorithms make every one of the AI's moves in real time.

Everything you see is driven by real, recursive Python search code — there
is no hardcoded demo data, no mocked AI, and no separate JavaScript
re-implementation of the algorithms. The backend runs the actual search and
reports real statistics (nodes visited, terminal states evaluated, branches
pruned, timing); the frontend only displays what the backend computed.

## Problem statement and objectives

Two-player, zero-sum, perfect-information games (where both players see
the whole board and one player's gain is exactly the other's loss) have a
provably optimal strategy. This project's objective is to:

1. Implement that optimal strategy with **Minimax**, a recursive algorithm
   that explores every way a game could continue.
2. Implement **Alpha-Beta Pruning**, an optimization of Minimax that
   reaches the *same* decision while visiting *fewer* positions.
3. Demonstrate both concretely: first on a small textbook game tree, then
   on a real, playable game (Tic-Tac-Toe) with accurate, reproducible
   search statistics.

## How Minimax works

Minimax alternates between two roles on every move: **MAX** (trying to
maximize the outcome — the AI) and **MIN** (trying to minimize it — the
opponent). The algorithm:

1. Checks whether the current position is terminal (a finished game, or a
   leaf of the example tree). If so, it returns that position's value
   immediately.
2. Otherwise, it recursively evaluates every legal move, flipping between
   MAX and MIN at each level.
3. A MAX node takes the **largest** value among its children (the AI picks
   whichever continuation is best for itself). A MIN node takes the
   **smallest** value among its children (a rational opponent picks
   whichever continuation is worst for the AI).

Minimax is exhaustive — it visits every reachable position exactly once.

## How Alpha-Beta Pruning works

Alpha-Beta Pruning computes the **same value as Minimax**, but skips
branches that are provably irrelevant to the final answer. It carries two
extra bounds through the recursion:

- **alpha** — the best value MAX can already guarantee from elsewhere in
  the tree (starts at −∞).
- **beta** — the best value MIN can already guarantee from elsewhere in
  the tree (starts at +∞).

### The pruning condition: `alpha >= beta`

After evaluating a child, a MAX node updates `alpha = max(alpha, value)`
and a MIN node updates `beta = min(beta, value)`. Once `alpha >= beta`, the
remaining children at that node are skipped (`break`), because:

> MAX already has a way to force at least `alpha` somewhere else, **and**
> MIN already has a way to hold this branch to at most `beta`. Since
> `alpha >= beta`, neither player can do better by continuing to explore
> this node's remaining children, so those children can never change the
> final decision.

This is a mathematical proof that a branch is irrelevant, not a heuristic
guess — which is why Alpha-Beta always returns the same value as plain
Minimax while visiting fewer nodes. See `TIC_TAC_TOE_VIVA.md` for a fully
worked example and twenty-plus explained viva questions.

## How the Tic-Tac-Toe game demonstrates these algorithms

- The AI's symbol is always the **MAX** player; the opponent is always
  **MIN**. Both algorithms share a single evaluation function
  (`evaluate_terminal` in `tic_tac_toe.py`): AI win = `+1`, draw = `0`, AI
  loss = `-1`.
- You can choose **Minimax** or **Alpha-Beta Pruning** as the AI's search
  algorithm, with or without move ordering (center → corners → edges),
  before or during a game.
- A **Compare Algorithms Now** button runs Minimax, Alpha-Beta (ordered),
  and Alpha-Beta (unordered) on the *current* board and reports the value
  and node counts for all three — proving pruning and move ordering both
  reduce the work done without changing the answer.
- Node counts, terminal-state counts, and pruned-branch counts are
  computed by counters updated inside the real recursive search (see
  `tic_tac_toe.py`), never hardcoded or estimated.
- **Note on the UI:** an earlier version of this page animated a
  search-tree graph and a step-by-step event log. That was removed because
  building and rendering a snapshot for every node visited (up to hundreds
  of thousands of nodes from an early board) was the actual source of
  browser lag. The backend now skips building that event trace by default
  (`collect_events=False`), and the page shows only the final, real
  statistics for each search — no loss of correctness, much less data to
  compute or render.

## Technology stack

- **Backend:** Python 3, Flask (routing, JSON APIs, server-side session
  cookies for per-browser Tic-Tac-Toe game state)
- **Frontend:** plain HTML, CSS, and vanilla JavaScript (`fetch()` calls
  only — no frontend framework, no build step)
- **Testing:** pytest (unit tests for the algorithms and Flask route tests
  using Flask's built-in test client)

## Project structure

```
minmax_aisc/
├── app.py                     # Flask app: original routes + registers the Tic-Tac-Toe blueprint
├── minimax.py                 # Original algorithm code (Minimax + Alpha-Beta on a fixed example tree)
├── tic_tac_toe.py             # Tic-Tac-Toe rules + real Minimax/Alpha-Beta search, isolated module
├── tic_tac_toe_routes.py      # Flask Blueprint: Tic-Tac-Toe page + JSON API routes
├── requirements.txt           # Exact pinned runtime + test dependencies
├── .gitignore                 # Excludes venv, caches, secrets, IDE/OS junk
├── README.md                  # This file
├── PROMPTS.md                 # Build log of the prompts used to develop this project
├── TIC_TAC_TOE_VIVA.md         # Theory, worked example, 20+ Q&A, demo script for a viva
├── templates/
│   ├── index.html             # Original demo page
│   └── tic_tac_toe.html       # Tic-Tac-Toe + stats page
├── static/
│   ├── style.css              # Original demo styling
│   ├── script.js              # Original demo logic (fetches and animates real search events)
│   ├── tic_tac_toe.css        # Tic-Tac-Toe page styling
│   └── tic_tac_toe.js         # Tic-Tac-Toe page logic (board, moves, stats panel, compare table)
└── tests/
    ├── test_minimax.py        # 14 tests: original algorithm + Flask route tests
    └── test_tic_tac_toe.py    # 33 tests: game rules, algorithm agreement, pruning, Flask routes
```

## Prerequisites

- **Windows** with **Python 3.12** (this is the version this project was
  built and tested against: `Python 3.12.5`). Flask 3.0.3 supports
  Python 3.8+, so other 3.x versions may work, but only 3.12 has been
  verified for this project.
- The Python **"py" launcher** (installed automatically by the official
  Windows Python installer from python.org) so `py -3.12` works. If you
  don't have it, substitute `python` for `py -3.12` in the commands below,
  as long as that `python` is already a 3.12.x interpreter.
- Git, to clone the repository.
- No database, no external API keys, and no account credentials are
  required to run this project.

## Fresh-clone installation (Windows PowerShell)

Starting from nothing but a clean clone — no local virtual environment or
uncommitted files required:

```powershell
# 1. Clone the repository and enter it
git clone <repository-url>
cd <repository-folder>

# 2. Create a virtual environment (Python 3.12)
py -3.12 -m venv .venv

# 3. Activate it
.venv\Scripts\Activate.ps1

# 4. Upgrade pip, then install the exact pinned dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

# 5. Run the full test suite (47 tests; see "Test results" below)
python -m pytest tests -v

# 6. Start the Flask app (serves both pages)
python app.py
```

Replace `<repository-url>` and `<repository-folder>` with this project's
actual GitHub URL and the folder Git creates when you clone it.

If PowerShell blocks the activation script with an execution-policy error,
run this once in an **administrator** PowerShell window, then retry step 3:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### Virtual environment notes

- `.venv/` is excluded from version control by `.gitignore` — it is never
  committed, and a fresh clone will not contain one. You must create it
  yourself with the commands above.
- Any name works for the virtual environment folder (`.venv`, `venv`, …);
  `.gitignore` excludes both `.venv/` and `venv/` so either choice is safe.

## Running the tests

```powershell
# All tests (both the original simulation and Tic-Tac-Toe)
python -m pytest tests -v

# Just the original Minimax/Alpha-Beta demo
python -m pytest tests\test_minimax.py -v

# Just the Tic-Tac-Toe feature
python -m pytest tests\test_tic_tac_toe.py -v
```

## Starting the app

```powershell
python app.py
```

Flask starts in debug mode on `127.0.0.1:5000`. Press `Ctrl+C` in that
PowerShell window to stop it.

### URLs

- **Original Minimax demo:** http://127.0.0.1:5000/
- **Tic-Tac-Toe:** http://127.0.0.1:5000/tic-tac-toe

Both pages link to each other.

On the original demo, use **Run Minimax** or **Run Alpha-Beta** to fetch
the real execution trace from the backend and watch it animate
(**Step Forward**, **Play/Pause**, speed control, **Reset**).

On the Tic-Tac-Toe page: pick your symbol, who starts, and an algorithm,
then click **New Game**. Click a cell to play; the AI replies immediately
and the stats panel shows the real search's value, node counts, and
timing. Use **Compare Algorithms Now** to run all three search variants on
the current board and compare their node counts side by side.

## Configuration

- `FLASK_SECRET_KEY` (optional environment variable): used to sign the
  Tic-Tac-Toe page's per-browser session cookie (board, symbols, whose
  turn, chosen algorithm). If unset, `app.py` falls back to a clearly
  labeled, **development-only** value (`"dev-secret-key-for-local-demo"`).
  That fallback is fine for running this project locally, but is **not** a
  production-grade secret — for any shared or deployed use, set a real
  random value:
  ```powershell
  $env:FLASK_SECRET_KEY = "<your own random value>"
  python app.py
  ```
- No other environment variables, config files, or external services are
  required.

## Troubleshooting

- **`'py' is not recognized...`** — the Python launcher isn't installed or
  isn't on your PATH. Use `python -m venv .venv` instead, provided that
  `python --version` already reports 3.12.x.
- **`.venv\Scripts\Activate.ps1` fails with an execution-policy error** —
  see the `Set-ExecutionPolicy` command above.
- **`ModuleNotFoundError: No module named 'flask'`** — your virtual
  environment isn't activated, or `pip install -r requirements.txt` was
  not run inside it. Re-activate with `.venv\Scripts\Activate.ps1` and
  reinstall.
- **Port 5000 already in use** — stop whatever else is using it, or edit
  the `port=5000` argument in `app.run(...)` at the bottom of `app.py`.
- **Browser shows stale results after code changes** — Flask's debug
  reloader should restart automatically; if not, stop (`Ctrl+C`) and
  rerun `python app.py`.

## Known limitations

- The Tic-Tac-Toe page no longer renders a search-tree graph or a
  step-by-step event log (removed deliberately to fix a real performance
  problem — see the note above). The original demo's search-tree
  animation on `/` is unaffected and still works as before.
- Comparing algorithms from a **near-empty** Tic-Tac-Toe board is
  genuinely slow for the plain-Minimax leg of the comparison (observed
  ~2–3 seconds from an empty board on the development machine), because
  it is really enumerating the full, unpruned game tree (549,946 nodes) —
  this is an inherent cost of running the real, un-optimized algorithm,
  not a bug.
- This project has only been run and verified on Windows with Python
  3.12.5. It has not been tested on macOS or Linux, or with other Python
  3.x versions, so no claim is made about compatibility there.
- Automated verification in this repository is backend/API-level (pytest,
  plus direct HTTP requests against the running server). No automated
  browser UI test (e.g. Selenium/Playwright) is included; manual
  browser testing is still recommended before relying on the UI.

## Test results (actually verified)

Running `python -m pytest tests -v` on this project, on Windows with
Python 3.12.5, produces:

```
47 passed
```

- `tests/test_minimax.py` — **14 tests** covering the original Minimax and
  Alpha-Beta implementation on its fixed example tree
  (`[[[3, 5], [6, 9]], [[1, 2], [0, -1]]]`): Minimax returns `5` visiting
  `15` nodes, Alpha-Beta returns `5` visiting `11` nodes (saving `4`), and
  the original Flask routes (`/api/tree`, `/api/run`).
- `tests/test_tic_tac_toe.py` — **33 tests** covering board rules, win/draw
  detection, forced-win and forced-block positions, Minimax/Alpha-Beta
  value agreement, pruning/event correctness, move-ordering efficiency,
  and the Tic-Tac-Toe Flask routes (new game, move, reset, algorithm
  switch, compare, and session isolation between two separate games).

Separately verified by issuing real HTTP requests against the running
server (not just the test suite): a Tic-Tac-Toe move from a near-empty
board returns in well under 100ms with a response of a few hundred bytes
(no event trace attached), and Minimax/Alpha-Beta/Alpha-Beta-without-
ordering agree on the same value for the same position while visiting very
different numbers of nodes (e.g. 549,946 vs. 7,275 vs. 18,297 from an
empty board) — demonstrating that pruning and move ordering are real
optimizations, not relabeled or fabricated numbers.

## Acknowledgments and third-party licenses

This project depends on the following open-source packages (see
`requirements.txt` for exact pinned versions):

- **[Flask](https://flask.palletsprojects.com/)** — BSD-3-Clause License.
- **[pytest](https://pytest.org/)** — MIT License.

Their respective licenses apply to those packages only, not to the
original code in this repository.
