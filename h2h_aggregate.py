#!/usr/bin/env python3
"""CYS Harness Creator M1 — head-to-head aggregator (n-run median + provenance).

Pure stdlib, deterministic, NO agent calls, NO wall-clock/RNG. Upgrades the M0
single-scorecard check into the full suite: given per-run scorecards (one entry
per blind grading run), compute the MEDIAN pass_rate per condition (robust to a
single bad run), the per-condition variance (run-to-run instability signal), the
delta on MEDIANS, and the win/lose verdict vs HEAD_TO_HEAD_WIN_MARGIN_PP (15pp).

A scorecard is one grading of one run: {"c2_pass_rate": float, "c3_pass_rate":
float, ...}. Extra assertion-level keys (cN_pass_rate for any condition N) are
aggregated too, but C2 (CYS harness) vs C3 (no-harness baseline) drives verdict.

Provenance is stamped from values the caller passes in (model_id, git_sha) plus
what we can read locally (schema_version, harness_version, n_runs) so the result
is reproducible and auditable. The .js suite produces runs.json; this turns it
into the head-to-head verdict.

CLI:  h2h_aggregate.py <runs.json> [--model-id ID] [--git-sha SHA]
                       [--harness-version V] [--margin-pp PP]
runs.json: {"runs":[{...scorecard...}, ...], "model_id"?, "git_sha"?,
            "harness_version"?}  (CLI flags override file fields)
"""
import argparse
import json
import os
import sys

SCHEMA_VERSION = "0.1"

# Single source of truth is constants.json (next to this file); fall back if absent
# so the aggregator stays resume-safe with no hard dependency.
_DEFAULTS = {"HEAD_TO_HEAD_WIN_MARGIN_PP": 15}


def _load_constants():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "constants.json")
    cfg = dict(_DEFAULTS)
    try:
        with open(path) as f:
            loaded = json.load(f)
        for k in _DEFAULTS:
            if k in loaded:
                cfg[k] = loaded[k]
    except (OSError, ValueError):
        pass
    return cfg


HEAD_TO_HEAD_WIN_MARGIN_PP = _load_constants()["HEAD_TO_HEAD_WIN_MARGIN_PP"]


def median(xs):
    """Deterministic median of a non-empty numeric list (no statistics import needed)."""
    s = sorted(xs)
    n = len(s)
    mid = n // 2
    if n % 2:
        return float(s[mid])
    return (s[mid - 1] + s[mid]) / 2.0


def variance(xs):
    """Population variance (n divisor). 0.0 for a single run. Run-to-run instability signal."""
    n = len(xs)
    if n < 2:
        return 0.0
    m = sum(xs) / n
    return sum((x - m) ** 2 for x in xs) / n


def _condition_keys(runs):
    """Discover every 'cN_pass_rate' key present across runs, in stable sorted order."""
    keys = set()
    for r in runs:
        for k in r:
            if k.endswith("_pass_rate"):
                keys.add(k)
    return sorted(keys)


def aggregate(runs, *, model_id, git_sha, harness_version,
              margin_pp=HEAD_TO_HEAD_WIN_MARGIN_PP):
    """Aggregate per-run scorecards into the head-to-head verdict + provenance.

    runs: list of {"cN_pass_rate": float, ...}. Requires c2_pass_rate & c3_pass_rate.
    Returns the load-bearing report dict (median/variance per condition, median delta,
    verdict vs margin, provenance). pass_rates are fractions 0..1; delta is in pp.
    """
    if not runs:
        raise ValueError("runs is empty: need >=1 per-run scorecard to aggregate.")
    for k in ("c2_pass_rate", "c3_pass_rate"):
        for i, r in enumerate(runs):
            if k not in r:
                raise ValueError(f"run[{i}] missing required key {k!r}")

    conditions = {}
    for key in _condition_keys(runs):
        vals = [float(r[key]) for r in runs if key in r]
        cond = key[: -len("_pass_rate")].upper()  # c2_pass_rate -> C2
        conditions[cond] = {
            "median": round(median(vals), 4),
            "variance": round(variance(vals), 6),
            "n": len(vals),
            "runs": vals,
        }

    c2_med = conditions["C2"]["median"]
    c3_med = conditions["C3"]["median"]
    delta_pp = round((c2_med - c3_med) * 100.0, 2)  # medians are fractions -> pp
    if delta_pp >= margin_pp:
        verdict = "CYS-WINS"
    elif delta_pp <= -margin_pp:
        verdict = "BASELINE-WINS"
    else:
        verdict = "INCONCLUSIVE"

    return {
        "conditions": conditions,
        "delta_pp": delta_pp,
        "margin_pp": margin_pp,
        "verdict": verdict,
        "verdict_basis": "median(C2) - median(C3) vs +/-HEAD_TO_HEAD_WIN_MARGIN_PP",
        "provenance": {
            "schema_version": SCHEMA_VERSION,
            "model_id": model_id,
            "harness_version": harness_version,
            "git_sha": git_sha,
            "n_runs": len(runs),
        },
        "note": "INCONCLUSIVE => margin not cleared either way; high variance => "
                "increase n. Report domains where CYS does NOT win honestly.",
    }


def main():
    ap = argparse.ArgumentParser(description="M1 head-to-head aggregator (n-run median)")
    ap.add_argument("runs", help="runs.json: {runs:[{c2_pass_rate,c3_pass_rate,...},...], ...}")
    ap.add_argument("--model-id", help="model id under test (provenance); overrides file")
    ap.add_argument("--git-sha", help="git sha of the harness (provenance); overrides file")
    ap.add_argument("--harness-version", help="harness_version (provenance); overrides file")
    ap.add_argument("--margin-pp", type=float, default=HEAD_TO_HEAD_WIN_MARGIN_PP,
                    help=f"win margin in pp (default {HEAD_TO_HEAD_WIN_MARGIN_PP})")
    a = ap.parse_args()

    with open(a.runs) as f:
        doc = json.load(f)
    runs = doc.get("runs", doc) if isinstance(doc, dict) else doc

    out = aggregate(
        runs,
        model_id=a.model_id or (doc.get("model_id") if isinstance(doc, dict) else None),
        git_sha=a.git_sha or (doc.get("git_sha") if isinstance(doc, dict) else None),
        harness_version=a.harness_version
        or (doc.get("harness_version") if isinstance(doc, dict) else None),
        margin_pp=a.margin_pp,
    )
    json.dump(out, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
