// Tic-Tac-Toe + Minimax/Alpha-Beta.
// All search logic runs in Python (tic_tac_toe.py via tic_tac_toe_routes.py).
// This file renders the board, sends moves to the backend, and displays the
// concise final search statistics the backend returns (nodes visited,
// terminal states, pruned branches, chosen move, value, timing).
//
// There is deliberately no search-tree graph and no step-by-step event log
// here. An earlier version animated every recorded search step as its own
// DOM node; that meant building and rendering up to thousands of elements
// per move (worse the earlier in the game the AI was asked to move), which
// is what caused the reported lag. The backend now skips building that
// event trace entirely by default (see `collect_events` in
// tic_tac_toe.py), so the fix is on both ends: nothing wasteful is computed
// server-side, and nothing wasteful is rendered client-side.

const els = {
  cells: Array.from(document.querySelectorAll(".ttt-cell")),
  status: document.getElementById("ttt-status"),
  newGameBtn: document.getElementById("ttt-new-game"),
  restartBtn: document.getElementById("ttt-restart"),
  moveOrdering: document.getElementById("ttt-move-ordering"),

  statAlgo: document.getElementById("ttt-stat-algo"),
  statValue: document.getElementById("ttt-stat-value"),
  statNodes: document.getElementById("ttt-stat-nodes"),
  statTerminal: document.getElementById("ttt-stat-terminal"),
  statPruned: document.getElementById("ttt-stat-pruned"),
  statMove: document.getElementById("ttt-stat-move"),
  statTime: document.getElementById("ttt-stat-time"),

  compareBtn: document.getElementById("ttt-compare"),
  compareResults: document.getElementById("ttt-compare-results"),
};

// activeRequestId guards against a slow/stale fetch response (e.g. the
// user clicked twice) overwriting a newer game state - same pattern used
// in the original Minimax demo's script.js.
let activeRequestId = 0;

let game = {
  board: Array(9).fill(" "),
  humanSymbol: "X",
  aiSymbol: "O",
  algorithm: "alphabeta",
  turn: null,
  gameOver: false,
  winner: null,
  started: false,
};

function fmt(v) {
  if (v === undefined || v === null) return "—";
  return String(v);
}

// --- Board rendering --------------------------------------------------

function renderBoard() {
  els.cells.forEach((cell, i) => {
    const mark = game.board[i];
    cell.textContent = mark === " " ? "" : mark;
    cell.classList.toggle("mark-o", mark === "O");
    const canClick = game.started && !game.gameOver && game.turn === "human" && mark === " ";
    cell.disabled = !canClick;
  });
}

function updateStatusPill() {
  if (!game.started) {
    els.status.textContent = "Set up a game to begin";
    els.status.className = "status-pill";
    return;
  }
  if (game.gameOver) {
    if (game.winner === "draw") {
      els.status.textContent = "Draw!";
      els.status.className = "status-pill draw";
    } else if (game.winner === game.humanSymbol) {
      els.status.textContent = "You win!";
      els.status.className = "status-pill win";
    } else {
      els.status.textContent = "AI wins!";
      els.status.className = "status-pill lose";
    }
    return;
  }
  if (game.turn === "human") {
    els.status.textContent = `Your turn (${game.humanSymbol})`;
    els.status.className = "status-pill turn-human";
  } else {
    els.status.textContent = "AI is thinking...";
    els.status.className = "status-pill turn-ai";
  }
}

// Shows the concise stats from the AI's most recent search, or clears the
// panel back to placeholders when no search has happened yet (e.g. right
// after starting a game where the human moves first).
function updateSearchStats(search) {
  if (!search) {
    els.statAlgo.textContent = "—";
    els.statValue.textContent = "—";
    els.statNodes.textContent = "—";
    els.statTerminal.textContent = "—";
    els.statPruned.textContent = "—";
    els.statMove.textContent = "—";
    els.statTime.textContent = "—";
    return;
  }
  els.statAlgo.textContent = search.algorithm === "alphabeta" ? "Alpha-Beta Pruning" : "Minimax";
  els.statValue.textContent = fmt(search.value);
  els.statNodes.textContent = fmt(search.nodes_visited);
  els.statTerminal.textContent = fmt(search.terminal_count);
  els.statPruned.textContent = fmt(search.pruned_branches);
  els.statMove.textContent = fmt(search.move);
  els.statTime.textContent = `${search.time_ms} ms`;
}

function applyServerState(data) {
  game.board = data.board;
  game.humanSymbol = data.human_symbol;
  game.aiSymbol = data.ai_symbol;
  game.algorithm = data.algorithm;
  game.turn = data.turn;
  game.gameOver = data.game_over;
  game.winner = data.winner;
  game.started = true;

  renderBoard();
  updateStatusPill();
  updateSearchStats(data.search);
}

// The backend no longer sends any field that can be +/-Infinity (that only
// ever happened inside the now-removed per-node event trace), so a plain
// res.json() is safe here - no tolerant parsing needed.
async function postJson(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.error || "Request failed");
  }
  return data;
}

function currentSetup() {
  const symbol = document.querySelector('input[name="ttt-symbol"]:checked').value;
  const first = document.querySelector('input[name="ttt-first"]:checked').value;
  const algorithm = document.querySelector('input[name="ttt-algo"]:checked').value;
  const useMoveOrdering = els.moveOrdering.checked;
  return { human_symbol: symbol, first_player: first, algorithm, use_move_ordering: useMoveOrdering };
}

async function startNewGame() {
  const requestId = ++activeRequestId;
  els.status.textContent = "Starting...";
  els.status.className = "status-pill";
  try {
    const data = await postJson("/api/ttt/new", currentSetup());
    if (requestId !== activeRequestId) return;
    applyServerState(data);
  } catch (err) {
    if (requestId !== activeRequestId) return;
    els.status.textContent = `Error: ${err.message}`;
    els.status.className = "status-pill lose";
  }
}

async function restartBoard() {
  const requestId = ++activeRequestId;
  try {
    const data = await postJson("/api/ttt/reset", currentSetup());
    if (requestId !== activeRequestId) return;
    applyServerState(data);
  } catch (err) {
    if (requestId !== activeRequestId) return;
    els.status.textContent = `Error: ${err.message}`;
    els.status.className = "status-pill lose";
  }
}

async function playCell(position) {
  if (!game.started || game.gameOver || game.turn !== "human") return;
  if (game.board[position] !== " ") return;

  const requestId = ++activeRequestId;
  els.status.textContent = "AI is thinking...";
  els.status.className = "status-pill turn-ai";
  try {
    const data = await postJson("/api/ttt/move", { position });
    if (requestId !== activeRequestId) return;
    applyServerState(data);
  } catch (err) {
    if (requestId !== activeRequestId) return;
    els.status.textContent = `Error: ${err.message}`;
    els.status.className = "status-pill lose";
    renderBoard();
  }
}

async function compareAlgorithms() {
  els.compareBtn.disabled = true;
  els.compareResults.classList.add("hidden");
  try {
    const data = await postJson("/api/ttt/compare", {});
    renderCompare(data);
  } catch (err) {
    els.compareResults.classList.remove("hidden");
    els.compareResults.innerHTML = `<p>Error: ${err.message}</p>`;
  } finally {
    els.compareBtn.disabled = false;
  }
}

function renderCompare(data) {
  const row = (title, r) => `
    <tr>
      <td>${title}</td>
      <td>${fmt(r.value)}</td>
      <td>${r.nodes_visited}</td>
      <td>${r.terminal_count}</td>
      <td>${r.pruned_branches}</td>
      <td>${r.time_ms} ms</td>
    </tr>`;

  els.compareResults.innerHTML = `
    <table>
      <thead>
        <tr><th>Algorithm</th><th>Value</th><th>Nodes Visited</th><th>Terminal States</th><th>Pruned Branches</th><th>Time</th></tr>
      </thead>
      <tbody>
        ${row("Minimax", data.minimax)}
        ${row("Alpha-Beta (ordered)", data.alphabeta_ordered)}
        ${row("Alpha-Beta (no ordering)", data.alphabeta_unordered)}
      </tbody>
    </table>
    <p>
      Values agree across all three: <strong class="${data.values_agree ? "highlight" : ""}">${data.values_agree}</strong>.
      Alpha-Beta saved <strong class="highlight">${data.nodes_saved_by_pruning}</strong> node visits versus plain Minimax.
      Move ordering alone saved a further <strong class="highlight">${data.nodes_saved_by_move_ordering}</strong> node visits
      (ordered vs. unordered Alpha-Beta on the identical position).
    </p>`;
  els.compareResults.classList.remove("hidden");
}

// --- Wiring --------------------------------------------------------------

els.cells.forEach((cell) => {
  cell.addEventListener("click", () => playCell(parseInt(cell.dataset.pos, 10)));
});
els.newGameBtn.addEventListener("click", startNewGame);
els.restartBtn.addEventListener("click", restartBoard);
els.compareBtn.addEventListener("click", compareAlgorithms);

renderBoard();
updateStatusPill();
updateSearchStats(null);
