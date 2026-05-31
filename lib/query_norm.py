#!/usr/bin/env python3
"""Deterministic recall-key normalizer — the SINGLE source of the Tier-II memory query key.

WHY (3-tier memory / "recall is wiring, not presence"): the Phase-0 recall greps the runs index for a
prior run, and the run-START write stores `query_norm`. If the read token (LLM-derived prose) and the
write token (a different rule) disagree, recall silently misses — the recall step is PRESENT but never
WIRED to a hit. This module makes BOTH halves use ONE deterministic rule, and emit BAKES its output as a
literal into the orchestrator prose (like sot_init.estimate_max_spawns), so the LLM never re-derives it.

Pure, no clock/RNG, resume-safe. Imported by bootstrap_factory_memory (write side) and emit_orchestrator
(bakes the literal grep token + query_norm into the produced orchestrator).
"""
import re


def query_norm(text):
    """Canonical recall key: lowercase, non-alphanumeric -> space, collapse. Deterministic + idempotent
    (query_norm(query_norm(x)) == query_norm(x)). 'deep-research' -> 'deep research'; 'Competitor_Watch!'
    -> 'competitor watch'. Substring-grep-safe: the same input always yields the same token string, so a
    reader grepping query_norm(name) hits a writer that stored query_norm(name)."""
    return " ".join(re.findall(r"[a-z0-9]+", str(text).lower()))


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        cases = [("deep-research", "deep research"), ("Competitor_Watch!", "competitor watch"),
                 ("ticket triage", "ticket triage"), ("  A--B  ", "a b"), ("deep research", "deep research")]
        bad = [(i, query_norm(i), o) for i, o in cases if query_norm(i) != o]
        # idempotency
        bad += [(i, query_norm(query_norm(i)), query_norm(i)) for i, _ in cases
                if query_norm(query_norm(i)) != query_norm(i)]
        print("FAIL %r" % (bad,) if bad else "ok %d cases + idempotent" % len(cases))
        sys.exit(1 if bad else 0)
    print(query_norm(" ".join(sys.argv[1:])))
