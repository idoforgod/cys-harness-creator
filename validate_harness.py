#!/usr/bin/env python3
"""CYS Harness Creator M0 — static harness linter / build gate.

Turns the original harness's advisory authoring principles into ASSERTIONS.
Pure static (no runtime Claude primitives). Exit: 0 pass, 1 error(s), 2 warn-only.
Usage: validate_harness.py <harness_dir> [--json]

Reads: <harness_dir>/.harness/graph.json, graph.schema.json (next to this file),
       .claude/agents/*.md, schemas/*.json, .harness/harness.lock,
       README.md + .claude/skills/*/SKILL.md (phase-count drift).
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "lib"))
from toposort import toposort, CycleError  # noqa: E402

# ---- tier policy: loaded from role-class-policy.json, the SINGLE SoT shared with model-tier-policy.js ----
# (replaces the former hand-copied mirror so the two can never drift; resume-safe fallback below.)
VALID_TIERS = ["haiku", "sonnet", "opus"]
_RC_FALLBACK = {
    "tier_by_role_class": {
        "gather": "haiku", "extract": "haiku", "format": "haiku", "qa-scan": "haiku",
        "voter": "sonnet", "debater": "sonnet", "reviser": "sonnet",
        "synthesis": "opus", "judge": "opus", "critic": "opus", "architecture": "opus",
    },
    "pure_retrieval_role_classes": ["gather", "extract", "format", "qa-scan"],
    "base_role_class_patterns": [
        ["gather|fetch|\\bsearch|retriev|collect|scan-src", "gather"],
        ["extract|parse|pull", "extract"],
        ["format|render|serialize|writer|publish", "format"],
        ["qa|lint|check|verify|valid", "qa-scan"],
        ["synth|aggregate|merge|conclude", "synthesis"],
        ["judge|arbiter", "judge"], ["critic|review", "critic"],
        ["architect|plan|design", "architecture"],
    ],
    "base_role_class_default": "synthesis",
    "mechanism_role_class": {
        "majority-vote": "voter", "debate-with-judge": "debater", "reflect-then-revise": "reviser",
    },
}


def _load_role_class_policy():
    try:
        with open(os.path.join(HERE, "role-class-policy.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return _RC_FALLBACK


_RC = _load_role_class_policy()
TIER_BY_ROLE_CLASS = _RC["tier_by_role_class"]
PURE_RETRIEVAL = _RC["pure_retrieval_role_classes"]
_BASE_PATTERNS = [(re.compile(rx), rc) for rx, rc in _RC["base_role_class_patterns"]]
_MECHANISM_ROLE_CLASS = _RC["mechanism_role_class"]
_BASE_DEFAULT = _RC["base_role_class_default"]


def _base_role_class(id_, agent):
    s = (str(id_) + " " + str(agent)).lower()
    for rx, rc in _BASE_PATTERNS:
        if rx.search(s):
            return rc
    return _BASE_DEFAULT


def _role_class_of(node):
    # .get() (not node["..."]) so a node missing decision_mechanism/id/agent never raises a raw KeyError —
    # the validate gate flags malformed nodes via GRAPH_SCHEMA and must not crash (callers in both validate
    # and emit pass schema-valid nodes; this only hardens the malformed-input path).
    return _MECHANISM_ROLE_CLASS.get(
        node.get("decision_mechanism"), _base_role_class(node.get("id", ""), node.get("agent", "")))


def _load_const(key, default):
    try:
        with open(os.path.join(HERE, "constants.json"), encoding="utf-8") as f:
            return json.load(f).get(key, default)
    except (OSError, ValueError):
        return default


def _parse_frontmatter(md_path):
    """Minimal YAML frontmatter line-scan: returns dict of top-level scalar keys."""
    fm = {}
    try:
        with open(md_path, encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return None
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not m:
        return fm
    for line in m.group(1).splitlines():
        mm = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if mm:
            fm[mm.group(1)] = mm.group(2).strip().strip('"').strip("'")
    return fm


class Report:
    def __init__(self):
        self.items = []

    def add(self, code, level, msg, where=""):
        self.items.append({"code": code, "level": level, "msg": msg, "where": where})

    def error(self, *a):
        self.add(*a) if len(a) == 3 else self.add(a[0], "error", a[1], a[2] if len(a) > 2 else "")

    def err(self, code, msg, where=""):
        self.add(code, "error", msg, where)

    def warn(self, code, msg, where=""):
        self.add(code, "warn", msg, where)


def validate(harness_dir):
    r = Report()
    rationale_level = _load_const("MODEL_RATIONALE_MISSING", "warn")
    gpath = os.path.join(harness_dir, ".harness", "graph.json")
    if not os.path.isfile(gpath):
        r.err("GRAPH_MISSING", "no .harness/graph.json", gpath)
        return r
    try:                                              # audit: a malformed/empty graph.json must FAIL the gate,
        graph = json.load(open(gpath, encoding="utf-8"))   # not crash it with an uncaught traceback
        if not isinstance(graph, dict):
            raise ValueError("graph.json is not a JSON object")
    except (ValueError, OSError) as e:
        r.err("GRAPH_SCHEMA", "graph.json is not readable/valid JSON: %s" % e, gpath)
        return r

    # install_mode marker (P1.2/B2): in-project installs preserve the HOST's root files and relocate the
    # genome constitution + the harness README/harness.md under .harness/, so the root-ownership checks
    # (GENOME_PRESENT root docs, W1_GENOME, doc/measurement drift) must follow the relocated paths.
    in_project = False
    gj = os.path.join(harness_dir, ".harness", "GENOME.json")
    _relocated = os.path.isfile(os.path.join(harness_dir, ".harness", "genome", "CLAUDE.md"))
    if os.path.isfile(gj):
        try:
            mode = json.load(open(gj, encoding="utf-8")).get("install_mode")
            # corrupt or keyless GENOME.json must NOT silently fall back to self-contained checks against an
            # in-project layout — detect in-project structurally (relocated constitution) before defaulting.
            in_project = (mode == "in-project") or (mode is None and _relocated)
        except ValueError:
            in_project = _relocated

    # GRAPH_SCHEMA
    try:
        import jsonschema
        schema = json.load(open(os.path.join(HERE, "graph.schema.json"), encoding="utf-8"))
        try:
            jsonschema.validate(graph, schema)
        except jsonschema.ValidationError as e:
            r.err("GRAPH_SCHEMA", "graph.json invalid: %s" % e.message, "/".join(str(p) for p in e.path))
    except ImportError:
        # audit: don't SILENTLY degrade to a 2-field check — warn that full schema enforcement is off.
        r.warn("GRAPH_SCHEMA_DEGRADED",
               "jsonschema not installed — full graph.schema.json validation skipped (structural check only); "
               "pip install jsonschema to restore the full contract gate", gpath)
        if graph.get("schema_version") != "0.1" or not graph.get("nodes"):
            r.err("GRAPH_SCHEMA", "structural check failed (jsonschema not installed)", gpath)

    nodes = graph.get("nodes", [])
    # A node that is not an object, or lacks id/agent, is FUNDAMENTALLY malformed — every downstream check
    # (node_ids, EDGE_INTEGRITY, the per-node loop, QA_TOKEN_TRAP, GRAPH_SKILL_CONSISTENCY) raw-dereferences
    # n["id"]/n["agent"]. Flag it via GRAPH_SCHEMA and RETURN here so the gate FAILS cleanly instead of
    # crashing with a KeyError/TypeError traceback (the gate's stated contract). Nodes that merely miss an
    # OPTIONAL field still flow through the collect-all checks below (they keep id+agent).
    malformed_nodes = [n for n in nodes if not isinstance(n, dict) or not n.get("id") or not n.get("agent")]
    if malformed_nodes:
        for n in malformed_nodes:
            r.err("GRAPH_SCHEMA", "malformed node (not an object / missing id/agent): %r" % (n,), gpath)
        return r
    node_ids = {n["id"] for n in nodes}

    # EDGE_INTEGRITY + cycle (pipeline must be acyclic). Derefs are .get()-guarded so a structurally
    # malformed edge (missing from/to — already flagged by GRAPH_SCHEMA above) yields a clean EDGE_INTEGRITY
    # message instead of a raw KeyError traceback (the gate's stated contract: FAIL malformed, never crash).
    for e in graph.get("edges", []):
        if not isinstance(e, dict) or e.get("from") not in node_ids or e.get("to") not in node_ids:
            r.err("EDGE_INTEGRITY", "edge references unknown/missing node: %s->%s"
                  % (e.get("from") if isinstance(e, dict) else e, e.get("to") if isinstance(e, dict) else "?"))
    # GRAPH_CYCLE: emit toposorts the graph for EVERY topology (emit_orchestrator), so any cycle it can't
    # schedule must be caught HERE, before emit — for all topologies EXCEPT producer-reviewer, whose
    # reviewer->producer back-edge is intentional (qa-guide §6-2: the loop is driven by topology semantics
    # + max_rounds, not a schedulable edge). Previously only pipeline/dispatch were checked, so an accidental
    # cycle in hierarchical/supervisor/expert-pool/fan-out-fan-in passed the gate then failed at emit.
    if graph.get("topology") != "producer-reviewer":
        try:
            toposort(nodes, graph.get("edges", []))
        except CycleError as ce:
            r.err("GRAPH_CYCLE", str(ce))
        except (ValueError, KeyError, TypeError) as ve:
            r.err("EDGE_INTEGRITY", str(ve))

    # PRODUCER_REVIEWER_REVIEW (audit P1-2): a producer-reviewer harness exists to REVIEW, so it must wire
    # >=1 L2 review node — else the genome's reviewer/fact-checker ships but the adversarial layer never fires
    # (all 4 shipped examples had zero review nodes, incl. the producer-reviewer one).
    if graph.get("topology") == "producer-reviewer" and not any(n.get("review") for n in nodes):
        r.err("PRODUCER_REVIEWER_REVIEW",
              "topology='producer-reviewer' but no node has a 'review' block — the L2 adversarial reviewer "
              "never fires; add review:{agent:'reviewer'} to the reviewed node", gpath)

    # TOPOLOGY_STRUCTURE (audit P2-A): a declared topology must match the NODE STRUCTURE, not just emit a
    # prose marker — else a trivial 1-node graph 'conforms' to fan-out-fan-in and hierarchical alike. fan-out-
    # fan-in needs >=2 parallel producers converging to a sink (a node with >=2 incoming edges); hierarchical
    # needs >=2 delegation levels (>=3 nodes). pipeline/dispatch/supervisor/expert-pool have no extra structural
    # floor here (supervisor/expert-pool are runtime-dynamic).
    _topo, _edges = graph.get("topology"), graph.get("edges", [])
    if _topo == "fan-out-fan-in":
        _indeg = {}
        for _e in _edges:
            _to = _e.get("to") if isinstance(_e, dict) else None
            if _to is not None:
                _indeg[_to] = _indeg.get(_to, 0) + 1
        if len(nodes) < 3 or not any(v >= 2 for v in _indeg.values()):
            r.err("TOPOLOGY_STRUCTURE",
                  "topology='fan-out-fan-in' needs >=2 parallel producers converging to a sink (a node with "
                  ">=2 incoming edges) over >=3 nodes — got %d node(s), max fan-in %d"
                  % (len(nodes), max(_indeg.values()) if _indeg else 0), gpath)
    elif _topo == "hierarchical" and len(nodes) < 3:
        r.err("TOPOLOGY_STRUCTURE",
              "topology='hierarchical' needs >=2 delegation levels (>=3 nodes) — got %d" % len(nodes), gpath)

    # per-node: AGENT_EXISTS, AGENT_FRONTMATTER, tier V1/V2/V3, SCHEMA_FILE_EXISTS, ABSOLUTE_PATHS, conditional params
    lock_owners = {}
    for n in nodes:                                 # every node here has id+agent (early-returned above otherwise)
        nid = n["id"]
        ap = os.path.join(harness_dir, ".claude", "agents", n["agent"] + ".md")
        fm = _parse_frontmatter(ap)
        if fm is None:
            r.err("AGENT_EXISTS", "missing agent file for node '%s': %s" % (nid, ap), nid)
        else:
            for k in ("name", "description", "model"):
                if not fm.get(k):
                    r.err("AGENT_FRONTMATTER", "agent '%s' missing frontmatter '%s:'" % (n["agent"], k), nid)
            if not fm.get("model_rationale"):
                r.add("RATIONALE_MISSING", rationale_level, "agent '%s' missing model_rationale:" % n["agent"], nid)
            if fm.get("model") and n.get("model") and fm["model"] != n["model"]:
                r.err("TIER_MISMATCH", "node '%s'.model=%s != agent frontmatter model=%s"
                      % (nid, n["model"], fm["model"]), nid)
            # AGENT_MEMORY_CONTRACT (3-tier P1): the agent must READ the Phase-0 recall relay
            # (_workspace/_recall.json) so recall is actually CONSUMED, not vestigial — closes the
            # field-observed 'agents are memory-blind' gap (presence of Read perm is not consumption).
            if "_recall.json" not in open(ap, encoding="utf-8").read():
                r.err("AGENT_MEMORY_CONTRACT",
                      "agent '%s' lacks the memory-input contract (does not Read _workspace/_recall.json "
                      "— recall is never consumed)" % n["agent"], nid)
        # REVIEW_AGENT_PRESENT (M1): a review node's adversarial agent must have a definition file so
        # the L2 layer can actually spawn it (genome ships reviewer/fact-checker; this enforces it).
        rv = n.get("review")
        if rv and rv.get("agent"):
            rap = os.path.join(harness_dir, ".claude", "agents", rv["agent"] + ".md")
            if not os.path.isfile(rap):
                r.err("REVIEW_AGENT_PRESENT",
                      "node '%s' review.agent '%s' has no .claude/agents/%s.md (L2 review can't fire)"
                      % (nid, rv["agent"], rv["agent"]), nid)
        # SKILL_AUTHORING_CONSISTENCY (M3/locked-5): the hybrid author-or-inline decision is machine-checked.
        sa = n.get("skill_authoring") or {}
        if sa.get("mode") == "skill":
            reason = sa.get("reason")
            if reason not in ("reuse", "complex", "conditional"):
                r.err("SKILL_AUTHORING_JUSTIFIED",
                      "node '%s' skill_authoring.mode='skill' needs reason in {reuse,complex,conditional}" % nid, nid)
            elif reason == "reuse" and len(sa.get("shared_by") or []) < 2:
                r.err("SKILL_AUTHORING_JUSTIFIED",
                      "node '%s' reason='reuse' must list shared_by with >=2 nodes that reuse the skill" % nid, nid)
            sn = "%s-%s" % ((graph or {}).get("harness_name", ""), nid)
            sk_md = os.path.join(harness_dir, ".claude", "skills", sn, "SKILL.md")
            if not os.path.isfile(sk_md):
                r.err("INLINE_NO_ORPHAN_SKILL",
                      "node '%s' authors a domain skill but .claude/skills/%s/SKILL.md is missing "
                      "(run emit_domain_skill.py)" % (nid, sn), nid)
            # LIFT gate (M3 + P1.3 wiring): an authored skill must earn its keep against the no-skill baseline.
            #   - UNMEASURED (no lift_verdict.json): policy-controlled (constants.LIFT_UNMEASURED, default 'warn';
            #     flip to 'error' to forbid shipping unmeasured skills).
            #   - MEASURED-AND-REFUSED (verdict present, decision!=register): HARD ERROR — the skill lost to the
            #     baseline, so relying on it is unjustified. Inline it or improve it. (lift_gate score --out writes
            #     the verdict to this exact path.) This is what gives the gate teeth.
            lv = os.path.join(harness_dir, ".claude", "skills", sn, "lift_verdict.json")
            if not os.path.isfile(lv):
                r.add("LIFT_UNMEASURED", _load_const("LIFT_UNMEASURED", "warn"),
                      "node '%s' authors skill '%s' but no lift_verdict.json — measure it (lift_gate.py score "
                      "--out <skill>/lift_verdict.json) or inline it" % (nid, sn), nid)
            else:
                try:
                    v = json.load(open(lv, encoding="utf-8"))
                except ValueError:
                    v = None
                if not isinstance(v, dict):
                    # corrupt / non-object verdict (truncated write, bad merge, hand-edit) — never crash on it;
                    # an unreadable verdict is not a valid registration, so the skill must not ship.
                    r.err("LIFT_REFUSED",
                          "node '%s' skill '%s' lift_verdict.json is missing a decision / not a JSON object — "
                          "re-run lift_gate.py score --out" % (nid, sn), nid)
                elif v.get("decision") != "register":
                    r.err("LIFT_REFUSED",
                          "node '%s' skill '%s' was lift-measured but REFUSED (decision=%r, lift=%s) — inline it or "
                          "improve it; do not ship a skill that does not beat the baseline"
                          % (nid, sn, v.get("decision"), v.get("lift")), nid)
                else:
                    # audit: trust the MATH, not a hand-written 'decision' label — a verdict claiming register
                    # with lift < threshold (or non-numeric lift/threshold) is inconsistent/forged and must not pass.
                    lift, thr = v.get("lift"), v.get("threshold")
                    if not isinstance(lift, (int, float)) or not isinstance(thr, (int, float)) or lift < thr:
                        r.err("LIFT_REFUSED",
                              "node '%s' skill '%s' verdict says register but lift=%s < threshold=%s "
                              "(inconsistent/hand-written) — re-run lift_gate.py score" % (nid, sn, lift, thr), nid)
        # V1 model present/valid
        if not n.get("model") or n["model"] not in VALID_TIERS:
            r.err("TIER_MISSING", "node '%s'.model empty/invalid (default would be %s)"
                  % (nid, TIER_BY_ROLE_CLASS[_role_class_of(n)]), nid)
        # V2 opus on pure-retrieval
        if n.get("model") == "opus" and _role_class_of(n) in PURE_RETRIEVAL:
            lvl = "warn" if (n.get("tier_override_reason") or "").strip() else "error"
            r.add("TIER_OVERSPEND", lvl, "node '%s' role-class %s (pure retrieval) is opus"
                  % (nid, _role_class_of(n)), nid)
        # SCHEMA_FILE_EXISTS
        if n.get("output_schema"):
            sp = os.path.join(harness_dir, n["output_schema"])
            if not os.path.isfile(sp):
                r.err("SCHEMA_FILE_EXISTS", "node '%s' output_schema missing: %s" % (nid, n["output_schema"]), nid)
            else:
                try:
                    s = json.load(open(sp, encoding="utf-8"))
                    if "type" not in s:
                        r.err("SCHEMA_FILE_EXISTS", "schema %s has no top-level 'type'" % n["output_schema"], nid)
                except ValueError:
                    r.err("SCHEMA_FILE_EXISTS", "schema %s is not valid JSON" % n["output_schema"], nid)
        # ABSOLUTE_PATHS (inputs/outputs/write_paths must be relative)
        for p in n.get("inputs", []) + n.get("outputs", []) + n.get("write_paths", []):
            if os.path.isabs(p):
                r.err("ABSOLUTE_PATHS", "node '%s' uses absolute path: %s" % (nid, p), nid)
        # WRITE_PATH_OVERLAP (static harness.lock check — no two nodes own the same write path)
        for wp in n.get("write_paths", []):
            if wp in lock_owners:
                r.err("WRITE_PATH_OVERLAP", "write_path '%s' owned by both '%s' and '%s'"
                      % (wp, lock_owners[wp], nid), nid)
            else:
                lock_owners[wp] = nid

    # NO_COMMANDS: SUPERSEDED by genome inheritance — the AWF genome legitimately ships
    # .claude/commands/ (install, maintenance, run-prompts...) as inherited machinery.
    # The original "never create commands" rule no longer applies once every harness
    # inherits the full AWF genome. (Removed per the full-inheritance decision.)

    # DOC_DRIFT: README phase-count == orchestrator SKILL phase-count
    _doc_drift(harness_dir, r, in_project)

    # GENOME (AWF DNA graft, D0+D1): inherited-DNA section + L0 security hooks
    _genome_checks(harness_dir, r, graph, in_project)

    # MEASUREMENT_DRIFT: a harness doc must not advertise CYS-WINS unless an evals verdict shows it
    _measurement_drift(harness_dir, r, in_project)

    # AUDIT_VERDICT_PRESENT (M4): if a Phase-0 audit was produced, it must be well-formed (branch in
    # {new,extend,maintain} + a drift list). Optional — a fresh 'new' build needn't run audit_harness.
    apath = os.path.join(harness_dir, ".harness", "audit.json")
    if os.path.isfile(apath):
        try:
            au = json.load(open(apath, encoding="utf-8"))
            if au.get("branch") not in ("new", "extend", "maintain"):
                r.err("AUDIT_VERDICT_PRESENT",
                      ".harness/audit.json branch must be new|extend|maintain (got %r)" % au.get("branch"), apath)
            if not isinstance(au.get("drift"), list):
                r.err("AUDIT_VERDICT_PRESENT", ".harness/audit.json must carry a 'drift' list", apath)
        except ValueError:
            r.err("AUDIT_VERDICT_PRESENT", ".harness/audit.json is not valid JSON", apath)

    # EVOLUTION_LOG_PRESENT (M5): if a change-history log exists, every entry must be a well-formed
    # routed change (feedback_type + target + change). Append-only living record.
    cpath = os.path.join(harness_dir, ".harness", "change-history.jsonl")
    if os.path.isfile(cpath):
        for i, line in enumerate(open(cpath, encoding="utf-8"), 1):
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except ValueError:
                r.err("EVOLUTION_LOG_PRESENT", "change-history.jsonl line %d is not valid JSON" % i, cpath)
                break
            if not all(k in e for k in ("feedback_type", "target", "change")):
                r.err("EVOLUTION_LOG_PRESENT",
                      "change-history.jsonl line %d missing feedback_type/target/change" % i, cpath)
                break

    # MEMORY_STORE_INIT (M6): a genome-inherited harness must have the Tier-II cross-run memory store
    # seeded (RLM external environment). Gated on settings.json (genome present) so minimal/non-inherited
    # fixtures are exempt.
    if os.path.isfile(os.path.join(harness_dir, ".claude", "settings.json")):
        mem = os.path.join(harness_dir, ".harness", "memory")
        for rel in ("archive.manifest.json", "domain-knowledge.yaml", os.path.join("runs", "index.jsonl")):
            if not os.path.isfile(os.path.join(mem, rel)):
                r.err("MEMORY_STORE_INIT",
                      ".harness/memory/%s missing (run inherit_genome / _init_memory_store)" % rel, mem)

    # BUILD_GATES_SKIPPED (P1-4/audit): the 4-stage factory workflow (warrant PRE -> R1 audit -> P5 approval
    # -> emit) is honor-system by default — emit/validate succeed even if every build-time gate was skipped.
    # This OPT-IN policy (constants.BUILD_GATES: off|warn|error, default 'off') lets a project REQUIRE the gate
    # ARTIFACTS so a build cannot silently bypass them: warrant.json (warrant --graph writes it), audit.json
    # (audit_harness writes it), APPROVED (the P5 human-approval token the orchestrator stamps on 'approve').
    # Default 'off' keeps direct/example emits at 0/0; flip to warn/error to enforce the pipeline.
    _bg = _load_const("BUILD_GATES", "off")
    if _bg in ("warn", "error"):
        for _art, _label in ((os.path.join(".harness", "warrant.json"), "warrant PRE cost gate"),
                             (os.path.join(".harness", "audit.json"), "R1 state audit"),
                             (os.path.join(".harness", "APPROVED"), "P5 human-approval token")):
            if not os.path.isfile(os.path.join(harness_dir, _art)):
                r.add("BUILD_GATES_SKIPPED", _bg,
                      "build-time gate not recorded: %s (%s) — the 4-stage workflow step did not run "
                      "(BUILD_GATES=%s)" % (_art, _label, _bg), _art)

    # GRAPH_PROVENANCE (P2-C/audit): the graph.json 'single-writer contract' was unenforced — a hand-edited
    # graph validated 0/0. If emit stamped .harness/graph.lock, WARN when graph.json changed after emit
    # (re-emit to re-bless). Warn (not error): an author may legitimately hand-tune then re-emit.
    _lock = os.path.join(harness_dir, ".harness", "graph.lock")
    if os.path.isfile(_lock):
        try:
            import hashlib
            _want = json.load(open(_lock, encoding="utf-8")).get("sha256")
            _got = hashlib.sha256(open(gpath, "rb").read()).hexdigest()
            if _want and _want != _got:
                r.warn("GRAPH_PROVENANCE",
                       "graph.json changed after emit (sha256 != .harness/graph.lock) — re-run emit_orchestrator "
                       "to re-bless the contract, or the orchestrator/agents are out of sync with the graph", gpath)
        except (ValueError, OSError):
            pass

    # QA_TOKEN_TRAP (P2-G/audit): the role-class regex tests qa|lint|check|verify|valid BEFORE critic|review, so
    # a node whose name has BOTH a qa-token AND a critic-token (e.g. 'qa-coherence-reviewer') resolves to
    # qa-scan/haiku — qa wins — silently under-tiering an intended critic. Warn precisely on that name collision
    # (a plain 'verify'/'verifier' node has no critic token and is NOT flagged).
    for n in nodes:
        _s = (str(n["id"]) + " " + str(n["agent"])).lower()
        if re.search(r"qa|lint|check|verif|valid", _s) and re.search(r"critic|review|judge|arbiter", _s):
            r.warn("QA_TOKEN_TRAP",
                   "node '%s' (agent '%s') name carries BOTH a qa-scan token and a critic token — the classifier "
                   "resolves it to qa-scan/haiku (qa wins), under-tiering an intended critic; drop the "
                   "qa/check/verify token from the name (e.g. 'integration-critic')" % (n["id"], n["agent"]), n["id"])

    return r


def _measurement_drift(harness_dir, r, in_project=False):
    """Honesty gate (the +37.5pp lesson): if the harness ships h2h verdicts and NONE is
    CYS-WINS, no in-harness doc (README / orchestrator SKILL) may advertise 'CYS-WINS'."""
    edir = os.path.join(harness_dir, "evals")
    if not os.path.isdir(edir):
        return
    verdicts = set()
    saw_file = False
    unreadable = 0
    for fn in os.listdir(edir):
        if fn.endswith(".verdict.json"):
            saw_file = True
            try:
                verdicts.add(json.load(open(os.path.join(edir, fn), encoding="utf-8")).get("verdict"))
            except (OSError, ValueError):
                unreadable += 1   # a present-but-unreadable verdict is NOT 'unmeasured' — don't let it pass a win claim
    if "CYS-WINS" in verdicts:
        return  # a genuine CYS-WINS verdict -> win claims are allowed
    if not saw_file:
        return  # no verdict files at all -> honestly unmeasured, nothing to police
    # verdict files exist but none shows CYS-WINS (includes the all-corrupt case) -> a win claim is unsupported
    # in-project: the harness readme is .harness/README.md; the host's root README is NOT a harness claim surface
    readme = os.path.join(harness_dir, ".harness", "README.md") if in_project \
        else os.path.join(harness_dir, "README.md")
    docs = [readme]
    sk = os.path.join(harness_dir, ".claude", "skills")
    if os.path.isdir(sk):
        for d in os.scandir(sk):
            cand = os.path.join(d.path, "SKILL.md")
            if d.is_dir() and os.path.isfile(cand):
                docs.append(cand)
    _corrupt = " (%d verdict file(s) unreadable)" % unreadable if unreadable else ""
    for d in docs:
        if os.path.isfile(d) and "CYS-WINS" in open(d, encoding="utf-8").read():
            r.err("MEASUREMENT_DRIFT", "doc advertises CYS-WINS but no evals/*.verdict.json shows it%s (%s)"
                  % (_corrupt, os.path.basename(d)), d)


def _genome_checks(harness_dir, r, graph=None, in_project=False):
    """Verify the FULL AgenticWorkflow genome was inherited (전수/유전), not a subset.
    W1_GENOME: harness.md embeds inherited DNA. GENOME_PRESENT: the load-bearing
    machinery files transplanted. HOOK_REGISTERED: settings.json wires the AWF hooks.

    in_project: the harness README/harness.md live under .harness/, and the genome constitution is
    relocated under .harness/genome/ (the host owns its root CLAUDE.md/AGENTS.md/soul.md) — so the
    root-ownership checks follow the relocated paths instead of requiring the genome at the host root."""
    hm = os.path.join(harness_dir, ".harness", "harness.md") if in_project \
        else os.path.join(harness_dir, "harness.md")
    if not os.path.isfile(hm):
        r.warn("W1_GENOME", "no harness.md (run emit_orchestrator to inject inherited DNA)", hm)
    else:
        text = open(hm, encoding="utf-8").read()
        missing = [m for m in ("Inherited DNA", "AC-1", "AC-2", "AC-3") if m not in text]
        if missing:
            r.err("W1_GENOME", "harness.md missing inherited-DNA markers: %s" % ", ".join(missing), hm)
    # GENOME_PRESENT: the load-bearing machinery must be transplanted. The .claude/hooks/scripts spine is
    # required in BOTH modes; the ~440KB constitution is at the root (self-contained) or relocated under
    # .harness/genome/ (in-project — never clobbering the host's own root docs).
    must_exist = [
        ".claude/hooks/scripts/_context_lib.py",        # shared spine the hooks depend on
        ".claude/hooks/scripts/context_guard.py",       # context-preservation dispatcher
        ".claude/hooks/scripts/block_destructive_commands.py",
        ".claude/hooks/scripts/output_secret_filter.py",
        ".claude/hooks/scripts/security_sensitive_file_guard.py",
        ".harness/GENOME.json",
    ]
    constitution = ["soul.md", "AGENTS.md", "CLAUDE.md"]
    must_exist += [os.path.join(".harness", "genome", c) for c in constitution] if in_project else constitution
    for rel in must_exist:
        if not os.path.isfile(os.path.join(harness_dir, rel)):
            r.err("GENOME_PRESENT", "genome machinery missing (run emit/inherit_genome): %s" % rel, rel)
    # RUNTIME_DECLARED: dual-accept by execution_mode (CD-6).
    #   execution_mode='workflow'        -> canonical 'cys-mode-a' (Mode-A workflow.js)
    #   execution_mode=agent|team|hybrid -> canonical '<harness>-orchestrator' (primitive substrate)
    mode = (graph or {}).get("execution_mode", "agent")  # M0: primitive substrate is the product default
    # WORKFLOW_RETIRED (M0/locked-3): Mode-A workflow.js is retired from the PRODUCT. A produced harness
    # must run 100% on Claude Code primitives (agent/team/hybrid). 'workflow' survives only as
    # factory-internal measurement tooling, never as a shipped harness.
    if mode == "workflow":
        r.err("WORKFLOW_RETIRED",
              "execution_mode='workflow' is retired from the product — use agent/team/hybrid "
              "(workflow.js survives only as factory-internal measurement tooling)",
              os.path.join(harness_dir, ".harness", "graph.json"))
    _wjs = os.path.join(harness_dir, ".harness", "workflow.js")
    if os.path.isfile(_wjs):
        r.err("WORKFLOW_RETIRED",
              "produced harness ships .harness/workflow.js (retired non-primitive runtime) — remove it; "
              "the orchestrator skill is the only execution runtime", _wjs)
    # PROMPT_RUNNER_ABSENT (P0-3/audit): a produced harness must not PHYSICALLY ship the prompt-runner
    # `claude -p` subprocess executor or its slash commands — a latent non-primitive execution path. This is
    # a FILESYSTEM check (symmetric to the workflow.js isfile check above); RUNTIME_MANIFEST_CLEAN below only
    # checks what RUNTIME.json *advertises*, so the binary could sit on disk while the manifest stayed 'clean'.
    if mode != "workflow":
        _pr = os.path.join(harness_dir, "prompt-runner", "run.py")
        if os.path.isfile(_pr):
            r.err("PROMPT_RUNNER_ABSENT",
                  "produced harness ships prompt-runner/run.py (a `claude -p` subprocess batch executor — a "
                  "non-primitive execution path); exclude it from the transplant (inherit_genome _NONPRIMITIVE_EXCLUDES)", _pr)
        _cmd = os.path.join(harness_dir, ".claude", "commands")
        if os.path.isdir(_cmd):
            _bad = sorted(f for f in os.listdir(_cmd) if "prompt" in f.lower() and f.endswith(".md"))
            if _bad:
                r.err("PROMPT_RUNNER_ABSENT",
                      "produced harness ships prompt-runner slash command(s): %s (non-primitive execution path)"
                      % ", ".join(_bad), _cmd)
    hname = (graph or {}).get("harness_name", "")
    expected_canonical = "cys-mode-a" if mode == "workflow" else ("%s-orchestrator" % hname)
    rp = os.path.join(harness_dir, ".harness", "RUNTIME.json")
    if not os.path.isfile(rp):
        r.err("RUNTIME_DECLARED", "no .harness/RUNTIME.json — two-runtime ambiguity unresolved (run inherit_genome)", rp)
    else:
        try:
            rt = json.load(open(rp, encoding="utf-8"))
            if rt.get("canonical_runtime") != expected_canonical:
                r.err("RUNTIME_DECLARED", "RUNTIME.json canonical_runtime='%s' but execution_mode='%s' expects '%s'"
                      % (rt.get("canonical_runtime"), mode, expected_canonical), rp)
            # RUNTIME_MANIFEST_CLEAN (M0/locked-3): a primitive harness advertises exactly ONE
            # execution runtime — the orchestrator skill. The retired workflow.js and the inherited
            # prompt-runner subprocess must NOT be listed as runnable runtimes in a produced child.
            if mode != "workflow":
                bad = [x.get("name") for x in rt.get("runtimes", [])
                       if "workflow.js" in (x.get("entrypoint") or "")
                       or "prompt-runner" in (x.get("entrypoint") or "")
                       or x.get("name") in ("cys-mode-a-workflow", "awf-prompt-runner")]
                if bad:
                    r.err("RUNTIME_MANIFEST_CLEAN",
                          "produced harness RUNTIME.json advertises a non-primitive runtime: %s "
                          "(workflow.js/prompt-runner are retired from the product)" % ", ".join(bad), rp)
        except ValueError:
            r.err("RUNTIME_DECLARED", "RUNTIME.json is not valid JSON", rp)
    # HOOK_REGISTERED: AWF security/context hooks wired; primitive substrate also wires budget_block.
    sp = os.path.join(harness_dir, ".claude", "settings.json")
    needed_hooks = ["block_destructive_commands.py", "output_secret_filter.py",
                    "security_sensitive_file_guard.py", "context_guard.py", "save_context.py"]
    if mode != "workflow":
        # M0d: the primitive substrate must wire the budget ceiling AND the halves that make it + the
        # QA gates actually fire — else DNA stays dormant (the exact gap the audit flagged).
        needed_hooks += ["budget_block.py", "spawn_counter.py", "sot_init.py", "qa_gate_runner.py"]
    if os.path.isfile(sp):
        try:
            cmds = json.dumps(json.load(open(sp, encoding="utf-8")).get("hooks", {}))
            for needed in needed_hooks:
                if needed not in cmds:
                    r.err("HOOK_REGISTERED", "settings.json does not wire %s" % needed, sp)
        except ValueError:
            r.err("HOOK_REGISTERED", "settings.json is not valid JSON", sp)
    else:
        r.err("HOOK_REGISTERED", "no .claude/settings.json (genome not inherited)", sp)
    # GRAPH_SKILL_CONSISTENCY: (primitive substrate) the orchestrator SKILL must name every node id
    # — the prose-vs-graph drift surface idoforgod cannot detect.
    if mode != "workflow" and graph:
        sk = os.path.join(harness_dir, ".claude", "skills", "%s-orchestrator" % hname, "SKILL.md")
        if not os.path.isfile(sk):
            r.err("GRAPH_SKILL_CONSISTENCY", "no orchestrator SKILL for primitive mode: %s" % sk, sk)
        else:
            # P1-1 (audit): strip HTML/markdown comments BEFORE the substring gates — else a single
            # `<!-- this orchestrator uses neither TeamCreate( nor Agent( -->` disclaimer satisfies the A2
            # floor / team-emit / graceful-degrade checks while the real calls are neutered. The emitted
            # primitive calls live in the live prose (backtick code spans), never in comments.
            txt = re.sub(r"<!--.*?-->", "", open(sk, encoding="utf-8").read(), flags=re.DOTALL)
            missing = [n["id"] for n in graph.get("nodes", []) if n["id"] not in txt]
            if missing:
                r.err("GRAPH_SKILL_CONSISTENCY", "orchestrator SKILL omits graph nodes: %s" % ", ".join(missing), sk)
            # TEAM_EMIT_PRESENT (M0d): execution_mode='team' must emit the ACTUAL team primitives, not
            # the Agent() fan of agent mode (the verified 'team emit byte-identical to agent' vaporware).
            if mode == "team":
                need = [p for p in ("TeamCreate", "TaskCreate", "TeamDelete") if p not in txt]
                if need:
                    r.err("TEAM_EMIT_PRESENT",
                          "execution_mode='team' but orchestrator SKILL never emits: %s "
                          "(team mode must drive real team primitives, not Agent() fan)" % ", ".join(need), sk)
            # CONTEXT_PRESERVATION_FIRSTCLASS (M1): long-term memory must be a declared operating cycle,
            # not the old 1-line gap — RLM knowledge-index recall + latest.md restore named explicitly.
            mem_markers = ("메모리 운영", "knowledge-index", "latest.md")
            miss = [m for m in mem_markers if m not in txt]
            if miss:
                r.err("CONTEXT_PRESERVATION_FIRSTCLASS",
                      "orchestrator SKILL lacks a first-class memory operating section (missing: %s)"
                      % ", ".join(miss), sk)
            # ALL_PRIMITIVES_PRESENT (M2/A2 floor): a built harness must instantiate ALL 6 primitive
            # types — orchestrator + agents + hooks + skills (structural, checked elsewhere) AND BOTH
            # Sub-agents (Agent) and Agent Teams (TeamCreate) in the orchestrator. agent-only (no team)
            # is not A2-compliant; use team/hybrid (with graceful degrade to sub-agents).
            # Use the CALL form `TeamCreate(` / `Agent(` — the description line always mentions the words
            # "Agent/TeamCreate", so word-presence would be vacuous; an actual spawn uses the paren form.
            prim_missing = []
            if "Agent(" not in txt:
                prim_missing.append("Sub-agents (Agent)")
            if "TeamCreate(" not in txt:
                prim_missing.append("Agent Teams (TeamCreate)")
            if prim_missing:
                r.err("ALL_PRIMITIVES_PRESENT",
                      "built harness does not instantiate all 6 primitives — orchestrator SKILL lacks: %s "
                      "(A2: use team/hybrid so both teams and sub-agents are present)" % ", ".join(prim_missing), sk)
            # TEAM_GRACEFUL_DEGRADE (M2/A2-iii): if teams are used, the orchestrator must document the
            # Sub-agent fallback for when CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS is absent (never hard-break).
            if "TeamCreate(" in txt and "degrade" not in txt.lower() and "강등" not in txt:
                r.err("TEAM_GRACEFUL_DEGRADE",
                      "harness uses Agent Teams but documents no Sub-agent fallback for when the "
                      "experimental Agent-Teams flag is absent (A2-iii)", sk)
            # TOPOLOGY_PRIMITIVE_CONSISTENCY (M2-2): a declared topology must actually emit its recipe,
            # and team-requiring topologies must emit a team. (pipeline/dispatch/producer-reviewer have
            # no addendum requirement; the 4 below are first-class emit targets.)
            topo = (graph or {}).get("topology")
            topo_hdr = {"fan-out-fan-in": "### 토폴로지: fan-out/fan-in",
                        "supervisor": "### 토폴로지: supervisor",
                        "expert-pool": "### 토폴로지: expert-pool",
                        "hierarchical": "### 토폴로지: hierarchical"}.get(topo)
            if topo_hdr and topo_hdr not in txt:
                r.err("TOPOLOGY_PRIMITIVE_CONSISTENCY",
                      "topology='%s' declared but its emit recipe is absent from the orchestrator SKILL" % topo, sk)
            if topo in ("fan-out-fan-in", "supervisor", "hierarchical") and "TeamCreate(" not in txt:
                r.err("TOPOLOGY_PRIMITIVE_CONSISTENCY",
                      "topology='%s' needs an Agent Team but execution_mode emits no TeamCreate( "
                      "(set execution_mode=team/hybrid)" % topo, sk)
            # EVOLUTION_WIRED (M5): the orchestrator must carry the Phase-7 evolution loop (feedback
            # routing + change-history) so the harness is a living system, not a one-shot artifact.
            if "진화" not in txt or "evolve_harness" not in txt:
                r.err("EVOLUTION_WIRED",
                      "orchestrator SKILL lacks the Phase-7 evolution section (진화 + evolve_harness)", sk)
            # MEMORY_SKILL_SECTION (M6): the orchestrator must declare the Tier-II cross-run memory
            # recall+write recipe (RLM — Grep the index, never bulk-load).
            if "교차-실행 도메인 메모리" not in txt or "runs/index.jsonl" not in txt:
                r.err("MEMORY_SKILL_SECTION",
                      "orchestrator SKILL lacks the Tier-II cross-run memory recipe "
                      "(교차-실행 도메인 메모리 + runs/index.jsonl)", sk)
            # MEMORY_RECALL_WIRED (3-tier P0): recall must be a Phase-0 EXECUTION step that relays into
            # _workspace/_recall.json (read by downstream agents) — not just the prose 'memory operations'
            # recipe. Guards the field-observed regression where recall stayed vestigial (presence ≠ wiring).
            if "_recall.json" not in txt:
                r.err("MEMORY_RECALL_WIRED",
                      "orchestrator Phase 0 does not WIRE Tier-II recall as an execution step "
                      "(missing the _workspace/_recall.json relay — recall stays prose and never fires)", sk)
            # RECALL_KEY_DETERMINISTIC (3-tier P0): the recall Grep token must be a BAKED literal
            # (query_norm(harness_name)), never an LLM-derived "<...정규화 토큰>"/"<query 토큰>" placeholder —
            # else read/write keys diverge and recall silently misses ('recall is wiring, not presence').
            if re.search(r'Grep\s+"<[^"]*(?:정규화|query)[^"]*토큰[^"]*>"', txt):
                r.err("RECALL_KEY_DETERMINISTIC",
                      "orchestrator recall greps an LLM-derived token placeholder instead of the baked "
                      "query_norm(harness_name) literal — re-run emit_orchestrator (read/write keys must match)", sk)
            # MEMORY_RELAY_WIRED (3-tier P2): verified facts must relay stage-to-stage THROUGH memory
            # (stage-N-facts.jsonl) so the fact spine flows through long-term memory, not only _workspace/.
            if "stage-<N>-facts" not in txt:
                r.err("MEMORY_RELAY_WIRED",
                      "orchestrator Phase 2 does not relay verified facts through memory "
                      "(missing the stage-<N>-facts.jsonl spine — data never flows through long-term memory)", sk)
            # MEMORY_INCREMENTAL_WIRED (3-tier P3): Tier-II writes must STREAM (run START status=in_progress,
            # updated stage-by-stage) so a crash/parallel run recalls partial progress — not deposit-at-end.
            if "in_progress" not in txt:
                r.err("MEMORY_INCREMENTAL_WIRED",
                      "orchestrator does not stream Tier-II writes (no run-START status=in_progress marker — "
                      "memory is deposited only at the end, so a crash/parallel run loses all progress)", sk)


def _count_phases(text):
    # count distinct "Phase N" headings or numbered workflow steps; M0 heuristic
    nums = set(int(m) for m in re.findall(r"[Pp]hase\s*(\d+)", text))
    return len(nums) if nums else None


def _doc_drift(harness_dir, r, in_project=False):
    # in-project: the harness readme is .harness/README.md (root README.md is the HOST's, not a drift surface)
    readme = os.path.join(harness_dir, ".harness", "README.md") if in_project \
        else os.path.join(harness_dir, "README.md")
    skills_dir = os.path.join(harness_dir, ".claude", "skills")
    skill_md = None
    if os.path.isdir(skills_dir):
        # target the DOMAIN orchestrator skill only — inherited genome skills
        # (workflow-generator, doctoral-writing, ...) are machinery, not the domain doc.
        for d in os.scandir(skills_dir):
            if d.is_dir() and d.name.endswith("-orchestrator"):
                cand = os.path.join(d.path, "SKILL.md")
                if os.path.isfile(cand):
                    skill_md = cand
                    break
    if not (os.path.isfile(readme) and skill_md):
        return  # no domain orchestrator skill -> nothing to drift-check
    rc = _count_phases(open(readme, encoding="utf-8").read())
    sc = _count_phases(open(skill_md, encoding="utf-8").read())
    if rc is not None and sc is not None and rc != sc:
        r.err("DOC_DRIFT", "README phase-count (%d) != SKILL phase-count (%d)" % (rc, sc), readme)


def main():
    ap = argparse.ArgumentParser(description="static harness validator / build gate")
    ap.add_argument("harness_dir")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    rep = validate(os.path.abspath(a.harness_dir))
    errs = [i for i in rep.items if i["level"] == "error"]
    warns = [i for i in rep.items if i["level"] == "warn"]
    status = "fail" if errs else ("warn" if warns else "pass")
    if a.json:
        json.dump({"status": status, "errors": errs, "warns": warns}, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        for i in rep.items:
            print("[%s] %-20s %s%s" % (i["level"].upper(), i["code"], i["msg"],
                                       (" (%s)" % i["where"]) if i["where"] else ""))
        print("\n%s: %d error(s), %d warning(s)" % (status.upper(), len(errs), len(warns)))
    sys.exit(1 if errs else (2 if warns else 0))


if __name__ == "__main__":
    main()
