# cys-harness-creator/lib/toposort.py
# Shared, deterministic topological sort over graph.json edges.
# Used by: emit_workflow.py (stage order) and validate_harness.py (GRAPH_NO_CYCLE).
# Determinism contract: ties are broken by node ARRAY INDEX, never by clock/RNG,
# so the emitter's agent() call order is stable across re-emits (resume cache safety).
# stdlib only; no wall-clock, no random.


class CycleError(ValueError):
    """Raised when edges contain a cycle. .cycle is the offending node id list."""

    def __init__(self, cycle):
        self.cycle = cycle
        super().__init__("edge cycle detected: " + " -> ".join(cycle))


def toposort(nodes, edges):
    """Return node ids in stable topological order (Kahn, ties by array index).

    nodes: list of dicts each with an 'id'.
    edges: list of dicts each with 'from' and 'to' (ordering only, not depends_on).
    Raises CycleError if the edge set is not a DAG.
    """
    order = [n["id"] for n in nodes]          # array-index tie-break key
    rank = {nid: i for i, nid in enumerate(order)}
    indeg = {nid: 0 for nid in order}
    succ = {nid: [] for nid in order}
    for e in edges:
        f, t = e["from"], e["to"]
        if f not in indeg or t not in indeg:
            raise ValueError("edge " + str(f) + "->" + str(t) + " references unknown node")
        succ[f].append(t)
        indeg[t] += 1

    ready = sorted((nid for nid in order if indeg[nid] == 0), key=rank.get)
    out = []
    while ready:
        nid = ready.pop(0)
        out.append(nid)
        newly = []
        for s in succ[nid]:
            indeg[s] -= 1
            if indeg[s] == 0:
                newly.append(s)
        if newly:                              # keep array-index ordering stable
            ready = sorted(ready + newly, key=rank.get)

    if len(out) != len(order):
        stuck = [nid for nid in order if nid not in out]
        raise CycleError(stuck)
    return out


def has_cycle(nodes, edges):
    """Bool convenience for the validator's GRAPH_NO_CYCLE check."""
    try:
        toposort(nodes, edges)
        return False
    except CycleError:
        return True
