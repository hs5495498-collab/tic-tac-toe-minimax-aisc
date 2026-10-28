import math
import sys

GAME_TREE = [
    [[3, 5], [6, 9]],
    [[1, 2], [0, -1]],
]

nodes_visited = 0


def minimax(node, depth, is_max, trace=False, label="Root", on_event=None):
    global nodes_visited
    nodes_visited += 1

    if on_event:
        on_event({"type": "enter", "label": label, "depth": depth, "is_max": is_max})

    if not isinstance(node, list):
        if trace:
            print("  " * depth + f"{label}: leaf = {node}")
        if on_event:
            on_event({"type": "leaf", "label": label, "depth": depth, "value": node})
        return node

    if is_max:
        best = -math.inf
        for i, child in enumerate(node):
            val = minimax(child, depth + 1, False, trace, f"{label}.{i}", on_event)
            best = max(best, val)
            if on_event:
                on_event({
                    "type": "update", "label": label, "depth": depth, "is_max": is_max,
                    "value": best, "child_index": i,
                })
    else:
        best = math.inf
        for i, child in enumerate(node):
            val = minimax(child, depth + 1, True, trace, f"{label}.{i}", on_event)
            best = min(best, val)
            if on_event:
                on_event({
                    "type": "update", "label": label, "depth": depth, "is_max": is_max,
                    "value": best, "child_index": i,
                })

    if trace:
        who = "MAX" if is_max else "MIN"
        print("  " * depth + f"{label} ({who}) = {best}")
    if on_event:
        on_event({"type": "return", "label": label, "depth": depth, "is_max": is_max, "value": best})
    return best


def alphabeta(node, depth, alpha, beta, is_max, trace=False, label="Root", on_event=None):
    global nodes_visited
    nodes_visited += 1

    if on_event:
        on_event({
            "type": "enter", "label": label, "depth": depth, "is_max": is_max,
            "alpha": alpha, "beta": beta,
        })

    if not isinstance(node, list):
        if trace:
            print("  " * depth + f"{label}: leaf = {node}")
        if on_event:
            on_event({"type": "leaf", "label": label, "depth": depth, "value": node})
        return node

    if is_max:
        value = -math.inf
        for i, child in enumerate(node):
            value = max(value, alphabeta(
                child, depth + 1, alpha, beta, False,
                trace, f"{label}.{i}", on_event
            ))
            alpha = max(alpha, value)
            if on_event:
                on_event({
                    "type": "update", "label": label, "depth": depth, "is_max": is_max,
                    "value": value, "alpha": alpha, "beta": beta, "child_index": i,
                })
            if alpha >= beta:
                if trace:
                    print("  " * depth + f"{label}: PRUNE remaining children "
                          f"(alpha={alpha} >= beta={beta})")
                if on_event:
                    pruned = [
                        {"label": f"{label}.{j}", "node": node[j]}
                        for j in range(i + 1, len(node))
                    ]
                    on_event({
                        "type": "prune", "label": label, "depth": depth,
                        "alpha": alpha, "beta": beta, "pruned": pruned,
                    })
                break
    else:
        value = math.inf
        for i, child in enumerate(node):
            value = min(value, alphabeta(
                child, depth + 1, alpha, beta, True,
                trace, f"{label}.{i}", on_event
            ))
            beta = min(beta, value)
            if on_event:
                on_event({
                    "type": "update", "label": label, "depth": depth, "is_max": is_max,
                    "value": value, "alpha": alpha, "beta": beta, "child_index": i,
                })
            if alpha >= beta:
                if trace:
                    print("  " * depth + f"{label}: PRUNE remaining children "
                          f"(alpha={alpha} >= beta={beta})")
                if on_event:
                    pruned = [
                        {"label": f"{label}.{j}", "node": node[j]}
                        for j in range(i + 1, len(node))
                    ]
                    on_event({
                        "type": "prune", "label": label, "depth": depth,
                        "alpha": alpha, "beta": beta, "pruned": pruned,
                    })
                break

    if trace:
        who = "MAX" if is_max else "MIN"
        print("  " * depth + f"{label} ({who}) = {value}")
    if on_event:
        on_event({"type": "return", "label": label, "depth": depth, "is_max": is_max, "value": value})
    return value


if __name__ == "__main__":
    print("=" * 60)
    print("PART 1: MINIMAX on tree", GAME_TREE)
    print("=" * 60)
    nodes_visited = 0
    v = minimax(GAME_TREE, 0, True, trace=True)
    mm_nodes = nodes_visited
    print(f"\nMinimax value of root = {v}, nodes visited = {mm_nodes}\n")

    print("=" * 60)
    print("PART 2: ALPHA-BETA on the same tree")
    print("=" * 60)
    nodes_visited = 0
    v = alphabeta(GAME_TREE, 0, -math.inf, math.inf, True, trace=True)
    print(f"\nAlpha-Beta value of root = {v}, nodes visited = {nodes_visited} "
          f"(saved {mm_nodes - nodes_visited} of {mm_nodes})\n")

    print("=" * 60)
