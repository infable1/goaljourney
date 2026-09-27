"""Near-duplicate detection for diversity (within train) and leakage (train vs eval/validation).

Signature text = goal title + description + user messages + evidence/event text: the parts that
define *the situation*. Character-shingle Jaccard is language-agnostic and good enough at the
current scale (O(n^2)); swap in MinHash/LSH before the pool exceeds ~20k items.
"""
import re


def signature_text(input_ctx: dict) -> str:
    parts = []
    goal = input_ctx.get("goal") or {}
    parts += [goal.get("title", ""), goal.get("description", ""), goal.get("desired_outcome", "")]
    for m in input_ctx.get("conversation") or []:
        if m.get("role") == "user":
            parts.append(m.get("content", ""))
    for e in input_ctx.get("evidence") or []:
        parts += [e.get("description", ""), e.get("content", "")]
    for ev in input_ctx.get("events") or []:
        parts.append(ev.get("description", ""))
    task = input_ctx.get("task") or {}
    parts.append(task.get("title", ""))
    return " ".join(p for p in parts if p)


def _normalise(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def shingles(text: str, k: int = 5) -> frozenset:
    t = _normalise(text)
    if len(t) <= k:
        return frozenset([t]) if t else frozenset()
    return frozenset(t[i:i + k] for i in range(len(t) - k + 1))


def jaccard(a: frozenset, b: frozenset) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def pairwise_near_duplicates(items, threshold: float, k: int = 5):
    """items: [(id, text)]. Returns [(id_a, id_b, similarity)] above threshold."""
    sh = [(i, shingles(t, k)) for i, t in items]
    out = []
    for x in range(len(sh)):
        for y in range(x + 1, len(sh)):
            s = jaccard(sh[x][1], sh[y][1])
            if s >= threshold:
                out.append((sh[x][0], sh[y][0], round(s, 3)))
    return out


def cross_near_duplicates(left, right, threshold: float, k: int = 5):
    """left/right: [(id, text)]. Pairs across the two sets above threshold."""
    rsh = [(i, shingles(t, k)) for i, t in right]
    out = []
    for li, lt in left:
        ls = shingles(lt, k)
        for ri, rs in rsh:
            s = jaccard(ls, rs)
            if s >= threshold:
                out.append((li, ri, round(s, 3)))
    return out
