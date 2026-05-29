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

# ---- tier policy MIRROR of model-tier-policy.js (keep in sync; M0 avoids cross-lang shelling) ----
VALID_TIERS = ["haiku", "sonnet", "opus"]
TIER_BY_ROLE_CLASS = {
    "gather": "haiku", "extract": "haiku", "format": "haiku", "qa-scan": "haiku",
    "voter": "sonnet", "debater": "sonnet", "reviser": "sonnet",
    "synthesis": "opus", "judge": "opus", "critic": "opus", "architecture": "opus",
}
PURE_RETRIEVAL = ["gather", "extract", "format", "qa-scan"]


def _base_role_class(id_, agent):
    s = (str(id_) + " " + str(agent)).lower()
    for rx, rc in [(r"gather|fetch|search|retriev|collect|scan-src", "gather"),
                   (r"extract|parse|pull", "extract"),
                   (r"format|render|serialize|report|writer|publish", "format"),
                   (r"qa|lint|check|verify|valid", "qa-scan"),
                   (r"synth|aggregate|merge|conclude", "synthesis"),
                   (r"judge|arbiter", "judge"), (r"critic|review", "critic"),
                   (r"architect|plan|design", "architecture")]:
        if re.search(rx, s):
            return rc
    return "synthesis"


def _role_class_of(node):
    return {"majority-vote": "voter", "debate-with-judge": "debater",
            "reflect-then-revise": "reviser"}.get(
        node["decision_mechanism"], _base_role_class(node["id"], node["agent"]))


def _load_const(key, default):
    try:
        with open(os.path.join(HERE, "constants.json")) as f:
            return json.load(f).get(key, default)
    except (OSError, ValueError):
        return default


def _parse_frontmatter(md_path):
    """Minimal YAML frontmatter line-scan: returns dict of top-level scalar keys."""
    fm = {}
    try:
        with open(md_path) as f:
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
    graph = json.load(open(gpath))

    # GRAPH_SCHEMA
    try:
        import jsonschema
        schema = json.load(open(os.path.join(HERE, "graph.schema.json")))
        try:
            jsonschema.validate(graph, schema)
        except jsonschema.ValidationError as e:
            r.err("GRAPH_SCHEMA", "graph.json invalid: %s" % e.message, "/".join(str(p) for p in e.path))
    except ImportError:
        if graph.get("schema_version") != "0.1" or not graph.get("nodes"):
            r.err("GRAPH_SCHEMA", "structural check failed (jsonschema not installed)", gpath)

    nodes = graph.get("nodes", [])
    node_ids = {n["id"] for n in nodes}

    # EDGE_INTEGRITY + cycle (pipeline must be acyclic)
    for e in graph.get("edges", []):
        if e["from"] not in node_ids or e["to"] not in node_ids:
            r.err("EDGE_INTEGRITY", "edge references unknown node: %s->%s" % (e["from"], e["to"]))
    if graph.get("topology") in ("pipeline", "dispatch"):
        try:
            toposort(nodes, graph.get("edges", []))
        except CycleError as ce:
            r.err("GRAPH_CYCLE", str(ce))
        except ValueError as ve:
            r.err("EDGE_INTEGRITY", str(ve))

    # per-node: AGENT_EXISTS, AGENT_FRONTMATTER, tier V1/V2/V3, SCHEMA_FILE_EXISTS, ABSOLUTE_PATHS, conditional params
    lock_owners = {}
    for n in nodes:
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
        # V1 model present/valid
        if not n.get("model") or n["model"] not in VALID_TIERS:
            r.err("TIER_MISSING", "node '%s'.model empty/invalid (default would be %s)"
                  % (nid, TIER_BY_ROLE_CLASS[_role_class_of(n)]), nid)
        # V2 opus on pure-retrieval
        if n.get("model") == "opus" and _role_class_of(n) in PURE_RETRIEVAL:
            lvl = "warn" if n.get("tier_override_reason") else "error"
            r.add("TIER_OVERSPEND", lvl, "node '%s' role-class %s (pure retrieval) is opus"
                  % (nid, _role_class_of(n)), nid)
        # SCHEMA_FILE_EXISTS
        if n.get("output_schema"):
            sp = os.path.join(harness_dir, n["output_schema"])
            if not os.path.isfile(sp):
                r.err("SCHEMA_FILE_EXISTS", "node '%s' output_schema missing: %s" % (nid, n["output_schema"]), nid)
            else:
                try:
                    s = json.load(open(sp))
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
    _doc_drift(harness_dir, r)

    # GENOME (AWF DNA graft, D0+D1): inherited-DNA section + L0 security hooks
    _genome_checks(harness_dir, r)

    return r


def _genome_checks(harness_dir, r):
    """Verify the FULL AgenticWorkflow genome was inherited (전수/유전), not a subset.
    W1_GENOME: harness.md embeds inherited DNA. GENOME_PRESENT: the load-bearing
    machinery files transplanted. HOOK_REGISTERED: settings.json wires the AWF hooks."""
    hm = os.path.join(harness_dir, "harness.md")
    if not os.path.isfile(hm):
        r.warn("W1_GENOME", "no harness.md (run emit_workflow.py to inject inherited DNA)", hm)
    else:
        text = open(hm, encoding="utf-8").read()
        missing = [m for m in ("Inherited DNA", "AC-1", "AC-2", "AC-3") if m not in text]
        if missing:
            r.err("W1_GENOME", "harness.md missing inherited-DNA markers: %s" % ", ".join(missing), hm)
    # GENOME_PRESENT: the machinery a long harness needs must be transplanted (self-contained)
    must_exist = [
        ".claude/hooks/scripts/_context_lib.py",        # shared spine the hooks depend on
        ".claude/hooks/scripts/context_guard.py",       # context-preservation dispatcher
        ".claude/hooks/scripts/block_destructive_commands.py",
        ".claude/hooks/scripts/output_secret_filter.py",
        ".claude/hooks/scripts/security_sensitive_file_guard.py",
        "soul.md", "AGENTS.md", "CLAUDE.md", ".harness/GENOME.json",
    ]
    for rel in must_exist:
        if not os.path.isfile(os.path.join(harness_dir, rel)):
            r.err("GENOME_PRESENT", "genome machinery missing (run emit/inherit_genome): %s" % rel, rel)
    # RUNTIME_DECLARED: the two inherited runtimes must be disambiguated (canonical = workflow.js)
    rp = os.path.join(harness_dir, ".harness", "RUNTIME.json")
    if not os.path.isfile(rp):
        r.err("RUNTIME_DECLARED", "no .harness/RUNTIME.json — two-runtime ambiguity unresolved (run inherit_genome)", rp)
    else:
        try:
            rt = json.load(open(rp))
            if rt.get("canonical_runtime") != "cys-mode-a":
                r.err("RUNTIME_DECLARED", "RUNTIME.json canonical_runtime must be 'cys-mode-a'", rp)
            names = {x.get("name") for x in rt.get("runtimes", [])}
            if "awf-prompt-runner" not in names:
                r.warn("RUNTIME_DECLARED", "RUNTIME.json should declare the inherited 'awf-prompt-runner' alternative", rp)
        except ValueError:
            r.err("RUNTIME_DECLARED", "RUNTIME.json is not valid JSON", rp)
    # HOOK_REGISTERED: AWF hook wiring present in settings.json
    sp = os.path.join(harness_dir, ".claude", "settings.json")
    if os.path.isfile(sp):
        try:
            cmds = json.dumps(json.load(open(sp)).get("hooks", {}))
            for needed in ("block_destructive_commands.py", "output_secret_filter.py",
                           "security_sensitive_file_guard.py", "context_guard.py"):
                if needed not in cmds:
                    r.err("HOOK_REGISTERED", "settings.json does not wire %s" % needed, sp)
        except ValueError:
            r.err("HOOK_REGISTERED", "settings.json is not valid JSON", sp)
    else:
        r.err("HOOK_REGISTERED", "no .claude/settings.json (genome not inherited)", sp)


def _count_phases(text):
    # count distinct "Phase N" headings or numbered workflow steps; M0 heuristic
    nums = set(int(m) for m in re.findall(r"[Pp]hase\s*(\d+)", text))
    return len(nums) if nums else None


def _doc_drift(harness_dir, r):
    readme = os.path.join(harness_dir, "README.md")
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
    rc = _count_phases(open(readme).read())
    sc = _count_phases(open(skill_md).read())
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
