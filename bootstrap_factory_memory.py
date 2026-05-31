#!/usr/bin/env python3
"""bootstrap_factory_memory — seed the FACTORY's own Tier-II BUILD memory (layer 1 of the 3-tier
self-hosting memory). See design/adr-3tier-memory-self-hosting.md and the `three-tier-memory-self-hosting`
project memory.

The factory dogfoods the same `.harness/memory/` store it transplants into emitted harnesses, but
kind="build": one append-only line per harness BUILD. Existing examples/ are imported as build history
so the build-recall (layer 2, in harness-creator SKILL) is not cold on the next build.

A1: this only seeds + indexes (deterministic). Recalling/using the build memory when authoring a new
graph is the primitive's (Claude's) job, wired in the harness-creator SKILL workflow.

Run: python3 bootstrap_factory_memory.py   (idempotent — never duplicates an already-imported build)
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import inherit_genome  # noqa: E402


def _build_record(graph, name, source=None, ts="seed-import"):
    """One build-history line from an emitted harness's graph.json."""
    nodes = graph.get("nodes") or []
    return {
        "build_id": graph.get("harness_name") or name,
        "query_norm": (graph.get("harness_name") or name).replace("-", " "),
        "topology": graph.get("topology"),
        "execution_mode": graph.get("execution_mode"),
        "n_nodes": len(nodes),
        "agents": [n.get("agent") for n in nodes],
        "final_status": "validated",
        "source": source or ("examples/%s" % name),
        "ts": ts,
    }


def _existing_build_ids(index_path):
    ids = set()
    if os.path.isfile(index_path):
        for line in open(index_path, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                ids.add(json.loads(line).get("build_id"))
            except ValueError:
                pass
    return ids


def import_examples(root=ROOT):
    """Seed the factory build store and append a build record per examples/*/.harness/graph.json.
    IDEMPOTENT: skips a build_id already present. Returns the list of newly-imported build_ids."""
    inherit_genome._init_memory_store(root, kind="build")
    index_path = os.path.join(root, ".harness", "memory", "runs", "index.jsonl")
    seen = _existing_build_ids(index_path)
    examples_dir = os.path.join(root, "examples")
    added = []
    names = sorted(os.listdir(examples_dir)) if os.path.isdir(examples_dir) else []
    for name in names:
        gpath = os.path.join(examples_dir, name, ".harness", "graph.json")
        if not os.path.isfile(gpath):
            continue
        try:
            graph = json.load(open(gpath, encoding="utf-8"))
        except ValueError:
            continue
        rec = _build_record(graph, name)
        if rec["build_id"] in seen:
            continue
        with open(index_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        seen.add(rec["build_id"])
        added.append(rec["build_id"])
    return added


def record_build(graph, root=ROOT, status="validated", source=None):
    """Append ONE build record (any emitted harness, not just examples/) to the factory build memory.
    Called by the harness-creator EVOLUTION step (layer 2 build-record). IDEMPOTENT on build_id —
    returns True iff newly recorded."""
    inherit_genome._init_memory_store(root, kind="build")
    index_path = os.path.join(root, ".harness", "memory", "runs", "index.jsonl")
    name = graph.get("harness_name") or "?"
    rec = _build_record(graph, name, source=source or name, ts="recorded")
    rec["final_status"] = status
    if rec["build_id"] in _existing_build_ids(index_path):
        return False
    with open(index_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return True


if __name__ == "__main__":
    new = import_examples()
    print("factory build memory at .harness/memory/ (kind=build); imported builds: %s" % (new or "(none new)"))
