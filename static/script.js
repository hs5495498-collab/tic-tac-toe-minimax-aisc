// Minimax / Alpha-Beta visualizer.
// All algorithm logic runs in Python (minimax.py via app.py). This file only
// requests the ordered event list the real execution produced and animates it.

const els = {
  tree: document.getElementById("tree"),
  edges: document.getElementById("edges"),
  log: document.getElementById("log"),
  statusPill: document.getElementById("status-pill"),
  statAlgo: document.getElementById("stat-algo"),
  statCurrent: document.getElementById("stat-current"),
  statValue: document.getElementById("stat-value"),
  statNodes: document.getElementById("stat-nodes"),
  statRoot: document.getElementById("stat-root"),
  statSaved: document.getElementById("stat-saved"),
  btnMinimax: document.getElementById("btn-minimax"),
  btnAlphaBeta: document.getElementById("btn-alphabeta"),
  btnStep: document.getElementById("btn-step"),
  btnPlay: document.getElementById("btn-play"),
  btnReset: document.getElementById("btn-reset"),
  speed: document.getElementById("speed"),
};

let layout = null;          // { nodes: [...], leafCount, maxDepth }
let nodeEls = {};           // label -> DOM element
let edgeEls = {};           // childLabel -> SVG line element
let activeRequestId = 0;    // guards against a stale fetch response overwriting a newer run
let state = {
  events: [],
  idx: 0,
  algo: null,
  rootValue: null,
  nodesSaved: 0,
  mmNodes: 0,
  playing: false,
  timer: null,
  visitedCount: 0,
};

function parentLabelOf(label) {
  const i = label.lastIndexOf(".");
  return i === -1 ? null : label.slice(0, i);
}

function layoutTree(tree) {
  let leafCounter = 0;
  const nodes = [];
  let maxDepth = 0;

  function visit(node, depth) {
    maxDepth = Math.max(maxDepth, depth);
    if (node.leaf) {
      const x = leafCounter++;
      nodes.push({ label: node.label, depth, x, leaf: true, value: node.value });
      return x;
    }
    const childXs = node.children.map((c) => visit(c, depth + 1));
    const x = childXs.reduce((a, b) => a + b, 0) / childXs.length;
    nodes.push({ label: node.label, depth, x, leaf: false });
    return x;
  }
  visit(tree, 0);
  return { nodes, leafCount: leafCounter, maxDepth };
}

function renderTree() {
  els.tree.innerHTML = "";
  els.edges.innerHTML = "";
  nodeEls = {};
  edgeEls = {};

  const width = els.tree.clientWidth;
  const height = els.tree.clientHeight;
  const pad = 40;

  const pixelPos = {};
  layout.nodes.forEach((n) => {
    const xPct = (n.x + 0.5) / layout.leafCount;
    const yPct = (n.depth + 0.5) / (layout.maxDepth + 1);
    const px = pad + xPct * (width - pad * 2);
    const py = pad * 0.6 + yPct * (height - pad * 1.2);
    pixelPos[n.label] = { x: px, y: py };
  });

  // Edges first (so nodes render on top)
  layout.nodes.forEach((n) => {
    const parent = parentLabelOf(n.label);
    if (parent === null) return;
    const p1 = pixelPos[parent];
    const p2 = pixelPos[n.label];
    const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
    line.setAttribute("x1", p1.x);
    line.setAttribute("y1", p1.y);
    line.setAttribute("x2", p2.x);
    line.setAttribute("y2", p2.y);
    els.edges.appendChild(line);
    edgeEls[n.label] = line;
  });

  layout.nodes.forEach((n) => {
    const div = document.createElement("div");
    let cls = "node";
    if (n.leaf) cls += " leaf";
    else cls += n.depth % 2 === 0 ? " max" : " min";
    div.className = cls;
    div.style.left = pixelPos[n.label].x + "px";
    div.style.top = pixelPos[n.label].y + "px";

    const labelEl = document.createElement("div");
    labelEl.className = "node-label";
    labelEl.textContent = n.leaf
      ? n.label
      : `${n.label} (${n.depth % 2 === 0 ? "MAX" : "MIN"})`;

    const valueEl = document.createElement("div");
    valueEl.className = "node-value";
    valueEl.textContent = n.leaf ? n.value : "?";

    const abEl = document.createElement("div");
    abEl.className = "node-ab";
    abEl.textContent = "";

    div.appendChild(labelEl);
    div.appendChild(valueEl);
    div.appendChild(abEl);
    els.tree.appendChild(div);
    nodeEls[n.label] = div;
  });
}

function clearVisualState() {
  Object.values(nodeEls).forEach((el) => {
    el.classList.remove("current", "visited", "pruned");
    const valueEl = el.querySelector(".node-value");
    const abEl = el.querySelector(".node-ab");
    const isLeaf = el.classList.contains("leaf");
    if (!isLeaf) valueEl.textContent = "?";
    abEl.textContent = "";
  });
  Object.values(edgeEls).forEach((el) => {
    el.classList.remove("active", "pruned");
  });
  els.log.innerHTML = "";
}

function log(type, text) {
  const div = document.createElement("div");
  div.className = "log-entry " + type;
  div.textContent = text;
  els.log.appendChild(div);
  els.log.scrollTop = els.log.scrollHeight;
}

function setCurrent(label) {
  Object.values(nodeEls).forEach((el) => el.classList.remove("current"));
  Object.values(edgeEls).forEach((el) => el.classList.remove("active"));
  const el = nodeEls[label];
  if (el) {
    el.classList.add("current", "visited");
    els.statCurrent.textContent = label;
  }
  const edge = edgeEls[label];
  if (edge) edge.classList.add("active");
}

function who(isMax) {
  return isMax ? "MAX" : "MIN";
}

function applyEvent(ev) {
  const el = nodeEls[ev.label];

  if (ev.type === "enter") {
    setCurrent(ev.label);
    state.visitedCount += 1;
    els.statNodes.textContent = state.visitedCount;
    if (ev.alpha !== undefined) {
      els.statValue.textContent = `α=${fmt(ev.alpha)}, β=${fmt(ev.beta)}`;
      log("enter", `Entering ${ev.label} (${who(ev.is_max)}), α=${fmt(ev.alpha)}, β=${fmt(ev.beta)}`);
    } else {
      log("enter", `Entering ${ev.label} (${ev.is_max === undefined ? "leaf" : who(ev.is_max)})`);
    }
    return;
  }

  if (ev.type === "leaf") {
    if (el) {
      el.classList.add("visited");
      el.querySelector(".node-value").textContent = ev.value;
    }
    els.statValue.textContent = String(ev.value);
    log("leaf", `${ev.label}: leaf value = ${ev.value}`);
    return;
  }

  if (ev.type === "update") {
    if (el) {
      el.querySelector(".node-value").textContent = fmt(ev.value);
      if (ev.alpha !== undefined) {
        el.querySelector(".node-ab").textContent = `α=${fmt(ev.alpha)} β=${fmt(ev.beta)}`;
      }
    }
    if (ev.alpha !== undefined) {
      els.statValue.textContent = `best=${fmt(ev.value)} (α=${fmt(ev.alpha)}, β=${fmt(ev.beta)})`;
      log("update", `${ev.label}: best so far = ${fmt(ev.value)}, α=${fmt(ev.alpha)}, β=${fmt(ev.beta)}`);
    } else {
      els.statValue.textContent = `best=${fmt(ev.value)}`;
      log("update", `${ev.label}: best so far = ${fmt(ev.value)}`);
    }
    return;
  }

  if (ev.type === "prune") {
    ev.pruned_labels.forEach((plabel) => {
      const pel = nodeEls[plabel];
      if (pel) pel.classList.add("pruned");
      const pedge = edgeEls[plabel];
      if (pedge) pedge.classList.add("pruned");
    });
    els.statusPill.textContent = "Pruned a branch!";
    els.statusPill.className = "status-pill pruned-flash";
    log("prune", `Pruning at ${ev.label}: α=${fmt(ev.alpha)} ≥ β=${fmt(ev.beta)} — skipping ${ev.pruned_labels.length} node(s)`);
    return;
  }

  if (ev.type === "return") {
    if (el) {
      el.classList.remove("current");
      el.classList.add("visited");
      if (!el.classList.contains("leaf")) {
        el.querySelector(".node-value").textContent = fmt(ev.value);
      }
    }
    els.statValue.textContent = fmt(ev.value);
    log("return", `${ev.label} (${ev.is_max === undefined ? "" : who(ev.is_max)}) returns ${fmt(ev.value)}`);
    return;
  }
}

// The backend serializes Python's math.inf/-math.inf (used as initial
// alpha/beta bounds) as the bare tokens Infinity/-Infinity, which are
// valid Python JSON output but NOT valid per the JSON spec. The browser's
// native res.json() uses a strict parser and throws on them, so Alpha-Beta
// responses (which carry alpha/beta) must go through this tolerant parser;
// Minimax responses never contain these tokens, which is why only
// Alpha-Beta was failing.
function parseJsonWithInfinity(text) {
  const sanitized = text
    .replace(/-Infinity/g, '"__NEG_INFINITY__"')
    .replace(/\bInfinity\b/g, '"__POS_INFINITY__"');
  return JSON.parse(sanitized, (key, value) => {
    if (value === "__POS_INFINITY__") return Infinity;
    if (value === "__NEG_INFINITY__") return -Infinity;
    return value;
  });
}

function fmt(v) {
  if (v === Infinity) return "∞";
  if (v === -Infinity) return "-∞";
  return String(v);
}

function step() {
  if (state.events.length === 0) {
    log("enter", "Click “Run Minimax” or “Run Alpha-Beta” first.");
    return;
  }
  if (state.idx >= state.events.length) {
    finish();
    return;
  }
  const ev = state.events[state.idx];
  applyEvent(ev);
  state.idx += 1;

  if (state.idx >= state.events.length) {
    finish();
  }
}

function finish() {
  pause();
  els.statRoot.textContent = fmt(state.rootValue);
  els.statSaved.textContent = state.algo === "alphabeta" ? state.nodesSaved : "0";
  els.statusPill.textContent = "Done";
  els.statusPill.className = "status-pill done";
  els.statCurrent.textContent = "Root";
}

function play() {
  if (state.playing) return;
  if (state.idx >= state.events.length) return;
  state.playing = true;
  els.btnPlay.textContent = "Pause";
  els.statusPill.textContent = "Running…";
  els.statusPill.className = "status-pill running";
  const delay = parseInt(els.speed.value, 10);
  state.timer = setInterval(() => {
    step();
    if (state.idx >= state.events.length) {
      pause();
    }
  }, delay);
}

function pause() {
  state.playing = false;
  els.btnPlay.textContent = "Play";
  if (state.timer) {
    clearInterval(state.timer);
    state.timer = null;
  }
}

function resetVisualization() {
  pause();
  activeRequestId += 1; // invalidate any in-flight /api/run fetch
  state.events = [];
  state.idx = 0;
  state.visitedCount = 0;
  clearVisualState();
  els.statNodes.textContent = "0";
  els.statCurrent.textContent = "—";
  els.statValue.textContent = "—";
  els.statRoot.textContent = "—";
  els.statSaved.textContent = "—";
  els.statusPill.textContent = "Idle";
  els.statusPill.className = "status-pill";
}

async function runAlgorithm(algo) {
  pause();
  const requestId = ++activeRequestId;
  els.statAlgo.textContent = algo === "alphabeta" ? "Alpha-Beta Pruning" : "Minimax";
  els.statusPill.textContent = "Loading…";
  els.statusPill.className = "status-pill running";

  const res = await fetch(`/api/run?algo=${algo}`);
  const text = await res.text();
  const data = parseJsonWithInfinity(text);

  // A newer run (another click) started while this fetch was in flight.
  // Discard this response so it can never overwrite the newer run's state.
  if (requestId !== activeRequestId) {
    return;
  }

  state.events = data.events;
  state.idx = 0;
  state.algo = data.algorithm;
  state.rootValue = data.root_value;
  state.nodesSaved = data.nodes_saved;
  state.mmNodes = data.minimax_nodes_visited;
  state.visitedCount = 0;

  clearVisualState();
  els.statNodes.textContent = "0";
  els.statCurrent.textContent = "—";
  els.statValue.textContent = "—";
  els.statRoot.textContent = "—";
  els.statSaved.textContent = "—";

  play();
}

els.btnMinimax.addEventListener("click", () => runAlgorithm("minimax"));
els.btnAlphaBeta.addEventListener("click", () => runAlgorithm("alphabeta"));
els.btnStep.addEventListener("click", () => {
  pause();
  step();
});
els.btnPlay.addEventListener("click", () => {
  if (state.playing) pause();
  else play();
});
els.btnReset.addEventListener("click", resetVisualization);
els.speed.addEventListener("change", () => {
  if (state.playing) {
    pause();
    play();
  }
});

window.addEventListener("resize", () => {
  if (layout) renderTree();
});

async function init() {
  const res = await fetch("/api/tree");
  const tree = await res.json();
  layout = layoutTree(tree);
  renderTree();
  resetVisualization();
}

init();
