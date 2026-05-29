# validate_harness.py — static harness linter / build gate

## PURPOSE
Convert the harness factory's "rules-as-essays" into "rules-as-assertions" (strategy D-2 bet #1). It is a pure-Python, dependency-light static linter that reads a generated harness directory and asserts every structural invariant the spine (graph.json) and the strategy doc promise: every node.agent has a real agent file with legal frontmatter and a tier-legal model; opus is not wasted on pure-retrieval roles; orchestrator SKILL.md carries the mandatory error-scenario + follow-up-keyword sections (the W2/anti-dead-code rules); all paths are absolute; NOTHING lives under .claude/commands/; graph.json validates against its JSON Schema; every output_schema and input/output file referenced exists; write_paths declared per node have unique owners in harness.lock (pre-flight write-concurrency lock, fixing W8); there are no dead doc/tool references; and README phase-count == SKILL phase-count (fixing the W11 6-vs-8 documentation drift). It exits non-zero so it can be wired as a generation gate and a CI gate (.github/workflows/validate.yml). It runs at AUTHOR/BUILD time only — it never touches a live agent session, so it sidesteps every Claude Code runtime primitive limitation and is 100% deterministic and effectively free.

## CONTRACT
CLI
====
  validate_harness.py [HARNESS_DIR] [--json] [--report PATH] [--strict] [--only IDS] [--schema-dir DIR]

  HARNESS_DIR   Positional. Root of one generated harness (the dir that contains
                .claude/ and .harness/). Default: "." (cwd). MUST be an absolute
                path OR is resolved to absolute via os.path.realpath before any check.
  --json        Emit the machine-readable report (see schema below) to stdout
                INSTEAD of the human table. Exit code semantics unchanged.
  --report PATH Also write the JSON report to PATH (absolute). Independent of --json.
  --strict      Treat every `warn` as an `error` for exit-code purposes (CI gate mode).
  --only IDS    Comma list of check ids to run (e.g. "AGENT_FILE_EXISTS,LOCK_UNIQUE_OWNER");
                others are skipped (status "skipped"). For targeted re-checks.
  --schema-dir  Dir holding the bundled JSON Schemas (graph.schema.json, agent.schema.json,
                lock.schema.json). Default: <dir of this script>/schemas.

EXIT CODES (only three; deterministic)
  0  PASS  — zero errors. (warns may exist unless --strict.)
  1  FAIL  — >=1 error (or, with --strict, >=1 warn). This is the build/CI gate trip.
  2  ABORT — validator could not run the check suite at all: HARNESS_DIR missing,
            .harness/graph.json missing or not parseable as JSON, bundled schema
            files missing, or an unhandled internal exception. Distinct from 1 so
            CI can tell "harness is broken" from "validator is broken / misinvoked".

WHAT IT READS (all read-only; no writes except --report / --json stdout)
  <HARNESS_DIR>/.harness/graph.json            (REQUIRED; absence => exit 2)
  <HARNESS_DIR>/.harness/harness.lock          (REQUIRED for LOCK_* checks)
  <HARNESS_DIR>/.claude/agents/<agent>.md      (one per distinct node.agent)
  <HARNESS_DIR>/.claude/skills/*/SKILL.md      (orchestrator skill(s))
  <HARNESS_DIR>/schemas/<file>.json            (each node.output_schema target)
  <HARNESS_DIR>/README*.md                      (phase-count source)
  <HARNESS_DIR>/.claude/commands/              (must NOT exist / be empty)
  <script_dir>/schemas/graph.schema.json       (bundled meta-schema for graph.json)
  Resolution rule: graph.json paths are interpreted RELATIVE TO HARNESS_DIR only for
  the spine's documented workspace fields (inputs/outputs/write_paths/output_schema use
  the _workspace/, schemas/ project-relative form per the spine example); ANY path that
  is itself absolute on disk is checked as-is. The ABSOLUTE_PATHS check below governs
  which fields are *required* to be absolute (orchestrator prose) vs which are allowed
  to be the project-relative spine form (graph.json node io).

DEPENDENCIES
  python3 >=3.9 (verified 3.14.4 present). stdlib: json, os, sys, re, argparse, pathlib,
  dataclasses, hashlib. Third-party: jsonschema (verified importable), PyYAML (verified
  importable) for agent/SKILL frontmatter. Both degrade: if jsonschema is missing,
  GRAPH_SCHEMA_VALID emits status "skipped" with severity downgraded and a NOTE, rather
  than crashing (so the linter still catches the cheap structural bugs).

=====================================================================================
COMPLETE CHECK REGISTRY — every check is {id, severity, asserts, fail_message}
Severity is the DEFAULT; --strict promotes warn->error for exit purposes.
=====================================================================================

[G] GRAPH-LEVEL
  GRAPH_PARSEABLE            error
    asserts: .harness/graph.json exists and json.load succeeds.
    fail: "graph.json missing or not valid JSON at {path}: {jsonerr}"  (=> exit 2)
  GRAPH_SCHEMA_VALID         error
    asserts: graph.json validates against bundled graph.schema.json (Draft 2020-12).
             Requires schema_version, harness_name, harness_version, execution_mode in
             {workflow,team}, topology in {pipeline,dispatch,producer-reviewer},
             budget.total_tokens:int>0, budget.approval_required:bool, nodes:non-empty
             array, each node requires id/agent/model/decision_mechanism/inputs/outputs/
             write_paths/output_schema/retries/on_exhaust/max_rounds; edges:array of
             {from,to}. (Designers may ADD fields; additionalProperties:true.)
    fail: "graph.json schema violation at {json_pointer}: {validator_msg}"
  GRAPH_NODE_IDS_UNIQUE      error
    asserts: node.id values are unique.
    fail: "duplicate node id '{id}' (nodes must have unique ids)"
  GRAPH_EDGES_RESOLVE        error
    asserts: every edge.from and edge.to names an existing node.id.
    fail: "edge {from}->{to} references unknown node '{missing}'"
  GRAPH_NO_CYCLE             warn
    asserts: for execution_mode=workflow + topology=pipeline, the edge set is a DAG
             (pipeline()/parallel() cannot express a cycle; producer-reviewer loops are
             allowed and skip this check).
    fail: "edge cycle detected ({cycle}); pipeline topology must be acyclic — use topology=producer-reviewer for loops"
  GRAPH_MODE_TOPOLOGY_OK     warn
    asserts: execution_mode/topology pairing is one the emitter supports
             (workflow+{pipeline,dispatch,producer-reviewer}; team+any).
    fail: "execution_mode '{mode}' + topology '{topo}' is not a shipped combination"

[A] AGENT / NODE
  AGENT_FILE_EXISTS          error
    asserts: for every node.agent X, .claude/agents/X.md exists (regular file).
    fail: "node '{node_id}' references agent '{agent}' but .claude/agents/{agent}.md does not exist"
  AGENT_FRONTMATTER_PRESENT  error
    asserts: each referenced agent .md opens with a YAML frontmatter block (--- ... ---)
             that PyYAML parses to a mapping.
    fail: "agent '{agent}': missing or unparseable YAML frontmatter (--- block) at top of file"
  AGENT_FRONTMATTER_FIELDS   error
    asserts: agent frontmatter contains non-empty name, description, model.
    fail: "agent '{agent}': frontmatter missing required field(s): {missing_list}"
  AGENT_NAME_MATCHES         warn
    asserts: frontmatter.name == the agent filename stem (and == the node.agent string).
    fail: "agent '{agent}': frontmatter name '{fm_name}' != filename/reference '{agent}'"
  NODE_MODEL_PRESENT         error
    asserts: node.model is present and non-empty for every node.
    fail: "node '{node_id}': required field 'model' is missing/empty"
  NODE_MODEL_TIER_LEGAL      error
    asserts: node.model in {haiku, sonnet, opus} (the agent({model}) legal tiers).
    fail: "node '{node_id}': model '{model}' is not a legal tier (haiku|sonnet|opus)"
  AGENT_MODEL_MATCHES_NODE   warn
    asserts: agent frontmatter.model tier == node.model tier (single source of truth;
             the workflow emitter uses node.model, so a divergent agent file is a latent bug).
    fail: "agent '{agent}': frontmatter model '{fm_model}' != graph node model '{node_model}' for node '{node_id}'"
  MODEL_OPUS_ON_RETRIEVAL    warn
    asserts: a node whose role is pure-retrieval is NOT on opus. "pure-retrieval" is
             decided by: node.agent stem OR frontmatter.name matching the configurable
             RETRIEVAL_ROLE_RX = ^(gather|fetch|retriev|search|extract|scan|crawl|collect|format)
             AND node.decision_mechanism == "single". (Mirrors D-3 tier defaults:
             gather/extract/format/QA-scan -> haiku.)
    fail: "node '{node_id}' (agent '{agent}') is a pure-retrieval role on model 'opus'; downgrade to haiku per tier policy (D-3)"

[O] ORCHESTRATOR SKILL  (the .claude/skills/*/SKILL.md that drives the harness)
  ORCH_SKILL_EXISTS          error
    asserts: at least one .claude/skills/*/SKILL.md exists.
    fail: "no orchestrator SKILL.md found under .claude/skills/*/"
  ORCH_FRONTMATTER_FIELDS    error
    asserts: the orchestrator SKILL.md frontmatter has non-empty name + description.
    fail: "orchestrator '{skill}': frontmatter missing name/description"
  ORCH_ERROR_SCENARIO        error
    asserts: SKILL.md body contains an error-handling section. Detected by heading regex
             ERROR_SECTION_RX = (?im)^#{1,6}\s*(error|failure|on[- ]exhaust|error scenario|error handling)\b
    fail: "orchestrator '{skill}': missing required 'Error scenario / handling' section (anti-W2)"
  ORCH_FOLLOWUP_KEYWORDS     error
    asserts: SKILL.md frontmatter.description OR body contains follow-up/re-run keywords
             (anti-dead-code rule, strategy A-6 #2): FOLLOWUP_RX matches >=2 of
             {재실행|수정|보완|re-?run|revise|update|continue|refine|follow[- ]?up}.
    fail: "orchestrator '{skill}': description/body lacks follow-up keywords (재실행/수정/보완|re-run/revise); skill becomes dead code after first run"
  README_SKILL_PHASE_MATCH   error
    asserts: phase count parsed from README*.md == phase count in the orchestrator
             surface. SKILL-side source order: (1) if a sibling .harness file or SKILL
             frontmatter exposes phases, use its length; (2) else count body headings
             matching PHASE_RX=(?im)^#{1,6}\s*phase\s*\d+\b. README-side: count distinct
             "Phase N" tokens. Both must be equal. (Directly kills the W11 README-6 vs
             SKILL-8 drift.)
    fail: "phase-count drift: README declares {n_readme} phases but orchestrator declares {n_skill}"

[P] PATHS / FS HYGIENE
  NO_COMMANDS_DIR            error
    asserts: <HARNESS_DIR>/.claude/commands/ does not exist, OR exists but contains no
             *.md files. (Harnesses ship skills+agents, never slash-commands.)
    fail: "forbidden directory .claude/commands/ present with command file(s): {files}"
  ABSOLUTE_PATHS_IN_PROSE    error
    asserts: any filesystem path embedded in orchestrator/agent PROSE that points outside
             the spine's project-relative workspace form must be absolute. Concretely:
             flag a path token that starts with "./" or "../" or "~" appearing in
             SKILL.md / agent .md body (PATH_TOKEN_RX). The spine io fields in graph.json
             (_workspace/..., schemas/...) are EXEMPT — they are the documented relative
             contract resolved by the emitter, not prose.
    fail: "{file}:{line}: relative path '{token}' in prose; use an absolute path (./, ../, ~ not allowed in instructions)"
  GRAPH_IO_PATHS_SHAPE       warn
    asserts: every node.inputs/outputs/output_schema/write_paths entry is either absolute
             OR matches the spine workspace prefix RX ^(_workspace/|schemas/). No bare
             ambiguous relatives.
    fail: "node '{node_id}': io path '{p}' is neither absolute nor a _workspace//schemas/ path"

[F] FILE-REFERENCE INTEGRITY  (no dead references)
  OUTPUT_SCHEMA_EXISTS       error
    asserts: for every node with non-empty output_schema, the file exists under HARNESS_DIR.
             (output_schema "" => StructuredOutput not forced => skipped, status "ok".)
    fail: "node '{node_id}': output_schema '{path}' does not exist on disk"
  OUTPUT_SCHEMA_VALID_JSON   error
    asserts: each existing output_schema file parses as JSON and has a top-level "type"
             or "$schema" (a usable JSON Schema for agent({schema})).
    fail: "node '{node_id}': output_schema '{path}' is not a usable JSON Schema: {err}"
  NODE_INPUTS_EXIST          warn
    asserts: each node.inputs entry exists on disk EXCEPT those produced upstream
             (an input that equals some other node's outputs entry is exempt — it is
             produced at runtime). Pure seed inputs (e.g. _workspace/00_input/query.md)
             must exist or be a documented placeholder.
    fail: "node '{node_id}': input '{path}' not found and is not produced by any upstream node"
  DEAD_DOC_REFERENCE         warn
    asserts: in SKILL.md/agent .md, any markdown link or backtick path to a *.md/*.json/
             *.py/*.js file inside the harness resolves to an existing file.
    fail: "{file}:{line}: dead reference '{target}' (file not found in harness)"
  DEAD_TOOL_REFERENCE        warn
    asserts: tool/skill names invoked in orchestrator prose (Skill(name=...), agent(...,
             agentType=...), referenced .claude/skills/<x>) resolve to a present skill dir
             or a known builtin tool list (bundled TOOL_ALLOWLIST). Unknown => warn.
    fail: "{file}:{line}: reference to '{name}' which is not a present skill nor a known tool"

[L] LOCK / WRITE-OWNERSHIP  (pre-flight concurrency, fixes W8)
  LOCK_FILE_EXISTS           error
    asserts: .harness/harness.lock exists and parses (JSON). (Required because Mode B
             teams and Mode A parallel() both rely on it for write isolation.)
    fail: "harness.lock missing or unparseable at {path}"
  LOCK_COVERS_WRITE_PATHS    error
    asserts: every distinct node.write_paths entry appears as an owned path in harness.lock.
    fail: "node '{node_id}': write_path '{p}' is not registered in harness.lock"
  LOCK_UNIQUE_OWNER          error
    asserts: no two DISTINCT node owners claim overlapping write_paths. Overlap =
             path-prefix containment after normalization (a owns _workspace/01_gather/,
             b owns _workspace/01_gather/sub/ => overlap => fail). Identical path with two
             owners also fails.
    fail: "write-path conflict: '{p1}' (owner {n1}) overlaps '{p2}' (owner {n2}); each write_path needs exactly one owner"
  LOCK_NO_ORPHAN_OWNER       warn
    asserts: every owner named in harness.lock corresponds to an existing node.id.
    fail: "harness.lock owner '{owner}' has no matching node in graph.json (stale lock entry)"

=====================================================================================
MACHINE-READABLE REPORT (stdout with --json, and/or written to --report PATH)
=====================================================================================
{
  "report_version": "1.0",
  "tool": "validate_harness.py",
  "harness_dir": "/abs/path/deep-research",
  "harness_name": "deep-research",          // echoed from graph.json
  "harness_version": "0.1.0",
  "summary": { "errors": 0, "warnings": 1, "skipped": 1, "passed": 22, "total": 24 },
  "exit_code": 0,
  "strict": false,
  "results": [
    {
      "id": "MODEL_OPUS_ON_RETRIEVAL",
      "severity": "warn",                    // default severity
      "status": "warn",                      // ok|warn|error|skipped
      "node_id": "gather",                   // null if not node-scoped
      "file": ".claude/agents/researcher.md",// harness-relative; null if N/A
      "line": null,
      "message": "node 'gather' (agent 'researcher') is a pure-retrieval role on model 'opus'; downgrade to haiku per tier policy (D-3)",
      "remediation": "set node.model='haiku' in graph.json for node 'gather'"
    }
    // ... one object per (check x scope) evaluated
  ]
}
NOTE: status "ok" results ARE included so consumers can render full coverage; --json
consumers filter by status. exit_code in the body mirrors the process exit code.

=====================================================================================
REFERENCE IMPLEMENTATION SKELETON (the file someone codes from, abridged but runnable)
=====================================================================================
#!/usr/bin/env python3
import argparse, json, os, re, sys
from pathlib import Path
try:
    import yaml
except ImportError:
    yaml = None
try:
    from jsonschema import Draft202012Validator
except ImportError:
    Draft202012Validator = None

RETRIEVAL_ROLE_RX = re.compile(r'^(gather|fetch|retriev|search|extract|scan|crawl|collect|format)', re.I)
PHASE_RX          = re.compile(r'(?im)^#{1,6}\s*phase\s*\d+\b')
README_PHASE_RX   = re.compile(r'(?i)\bphase\s*\d+\b')
ERROR_SECTION_RX  = re.compile(r'(?im)^#{1,6}\s*(error|failure|on[- ]exhaust|error scenario|error handling)\b')
FOLLOWUP_RX       = re.compile(r'(?i)(재실행|수정|보완|re-?run|revise|update|continue|refine|follow[- ]?up)')
PATH_TOKEN_RX     = re.compile(r'(?<![\w/])(\.{1,2}/[^\s`")\]]+|~/[^\s`")\]]+)')
LEGAL_TIERS       = {"haiku", "sonnet", "opus"}
WS_PREFIX_RX      = re.compile(r'^(_workspace/|schemas/)')

class R:  # result accumulator
    def __init__(self): self.items=[]
    def add(self, id, sev, status, msg, node=None, file=None, line=None, rem=None):
        self.items.append(dict(id=id, severity=sev, status=status, node_id=node,
                               file=file, line=line, message=msg, remediation=rem))
    def ok(self, id, **k): self.add(id, k.pop('sev','error'), 'ok', k.pop('msg',''), **k)

def load_frontmatter(path):
    txt = Path(path).read_text(encoding='utf-8')
    m = re.match(r'^---\n(.*?)\n---\n', txt, re.S)
    if not m: return None, txt
    if yaml is None: return {}, txt   # degrade
    try: return (yaml.safe_load(m.group(1)) or {}), txt
    except Exception: return None, txt

def norm(p):  # path-prefix normalization for overlap detection
    p = p.rstrip('/'); return p + '/'

def overlaps(a, b):
    a, b = norm(a), norm(b)
    return a == b or a.startswith(b) or b.startswith(a)

def check(harness_dir, schema_dir, only, strict):
    H = Path(harness_dir); r = R()
    gpath = H/'.harness'/'graph.json'
    if not gpath.exists():
        r.add('GRAPH_PARSEABLE','error','error',f'graph.json missing at {gpath}')
        return r, 2
    try: graph = json.loads(gpath.read_text())
    except Exception as e:
        r.add('GRAPH_PARSEABLE','error','error',f'graph.json not valid JSON: {e}')
        return r, 2
    r.ok('GRAPH_PARSEABLE')
    # GRAPH_SCHEMA_VALID
    sf = Path(schema_dir)/'graph.schema.json'
    if Draft202012Validator is None or not sf.exists():
        r.add('GRAPH_SCHEMA_VALID','error','skipped',
              'jsonschema or graph.schema.json unavailable; structural checks still ran')
    else:
        v = Draft202012Validator(json.loads(sf.read_text()))
        errs = sorted(v.iter_errors(graph), key=lambda e: e.path)
        if errs:
            for e in errs:
                ptr = '/'+'/'.join(map(str,e.path))
                r.add('GRAPH_SCHEMA_VALID','error','error',
                      f'graph.json schema violation at {ptr}: {e.message}')
        else: r.ok('GRAPH_SCHEMA_VALID')
    nodes = graph.get('nodes', [])
    ids = [n.get('id') for n in nodes]
    # ... GRAPH_NODE_IDS_UNIQUE, GRAPH_EDGES_RESOLVE, GRAPH_NO_CYCLE,
    #     AGENT_FILE_EXISTS, AGENT_FRONTMATTER_*, NODE_MODEL_*, MODEL_OPUS_ON_RETRIEVAL,
    #     ORCH_*, NO_COMMANDS_DIR, ABSOLUTE_PATHS_IN_PROSE, OUTPUT_SCHEMA_*,
    #     NODE_INPUTS_EXIST, DEAD_*, LOCK_* ... (one block each, per registry above)
    return r, None  # exit computed by caller

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('harness_dir', nargs='?', default='.')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--report')
    ap.add_argument('--strict', action='store_true')
    ap.add_argument('--only')
    ap.add_argument('--schema-dir', default=str(Path(__file__).parent/'schemas'))
    a = ap.parse_args()
    hd = os.path.realpath(a.harness_dir)
    only = set(a.only.split(',')) if a.only else None
    try:
        r, forced = check(hd, a.schema_dir, only, a.strict)
    except SystemExit: raise
    except Exception as e:
        print(f'ABORT: validator internal error: {e}', file=sys.stderr); sys.exit(2)
    errs = sum(1 for i in r.items if i['status']=='error')
    warns = sum(1 for i in r.items if i['status']=='warn')
    skip = sum(1 for i in r.items if i['status']=='skipped')
    passed = sum(1 for i in r.items if i['status']=='ok')
    code = forced if forced is not None else (1 if errs or (a.strict and warns) else 0)
    report = dict(report_version='1.0', tool='validate_harness.py', harness_dir=hd,
                  harness_name=None, harness_version=None,
                  summary=dict(errors=errs,warnings=warns,skipped=skip,passed=passed,total=len(r.items)),
                  exit_code=code, strict=a.strict, results=r.items)
    if a.report: Path(a.report).write_text(json.dumps(report, indent=2, ensure_ascii=False))
    if a.json: print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        for i in r.items:
            if i['status']=='ok': continue
            print(f"[{i['status'].upper():5}] {i['id']:26} {i['message']}")
        print(f"\n{errs} error(s), {warns} warning(s), {skip} skipped, {passed} ok -> exit {code}")
    sys.exit(code)

if __name__ == '__main__':
    main()

=====================================================================================
BUNDLED graph.schema.json (the meta-schema GRAPH_SCHEMA_VALID enforces) — abridged
=====================================================================================
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "additionalProperties": true,
  "required": ["schema_version","harness_name","harness_version","execution_mode",
               "topology","budget","nodes","edges"],
  "properties": {
    "schema_version": {"type":"string"},
    "harness_name":   {"type":"string","minLength":1},
    "harness_version":{"type":"string"},
    "execution_mode": {"enum":["workflow","team"]},
    "topology":       {"enum":["pipeline","dispatch","producer-reviewer"]},
    "budget": {"type":"object","required":["total_tokens","approval_required"],
      "properties":{"total_tokens":{"type":"integer","exclusiveMinimum":0},
                    "approval_required":{"type":"boolean"}}},
    "nodes": {"type":"array","minItems":1,"items":{
      "type":"object","additionalProperties":true,
      "required":["id","agent","model","decision_mechanism","inputs","outputs",
                  "write_paths","output_schema","retries","on_exhaust","max_rounds"],
      "properties":{
        "id":{"type":"string","minLength":1},
        "agent":{"type":"string","minLength":1},
        "model":{"enum":["haiku","sonnet","opus"]},
        "decision_mechanism":{"enum":["single","majority-vote","debate-with-judge","reflect-then-revise"]},
        "mechanism_params":{"type":"object"},
        "inputs":{"type":"array","items":{"type":"string"}},
        "outputs":{"type":"array","items":{"type":"string"}},
        "write_paths":{"type":"array","items":{"type":"string"}},
        "output_schema":{"type":"string"},
        "retries":{"type":"integer","minimum":0},
        "on_exhaust":{"enum":["proceed-with-gap","force-pass","escalate"]},
        "max_rounds":{"type":"integer","minimum":1}}}},
    "edges":{"type":"array","items":{"type":"object","required":["from","to"],
      "properties":{"from":{"type":"string"},"to":{"type":"string"}}}}
  }
}

=====================================================================================
CI WIRING (.github/workflows/validate.yml — the gate, per D-6) — for reference
=====================================================================================
# - run: python3 validate_harness.py "$GITHUB_WORKSPACE" --strict --json --report report.json
#   (exit 1 fails the job; exit 2 fails the job AND signals "validator/harness broken")
# Also invoked at GENERATION time by the creator skill before it declares the harness done.

## DEEP-RESEARCH INSTANCE
Concrete run against the deep-research dogfood harness (the D-6 layout):

DIRECTORY UNDER TEST (canonical M0 dogfood — defined by this spec from spine + strategy):
  /Users/cys/Desktop/CYSjavis/cys-harness-creartor/harnesses/deep-research/
  ├── .claude/
  │   ├── agents/researcher.md   (name: researcher,  model: haiku)
  │   ├── agents/verifier.md     (name: verifier,    model: sonnet)
  │   ├── agents/synthesizer.md  (name: synthesizer, model: opus)
  │   └── skills/deep-research-orchestrator/SKILL.md
  ├── .harness/
  │   ├── workflow.js     (Mode A; execution_mode=workflow)
  │   ├── graph.json      (the spine instance below)
  │   └── harness.lock
  ├── schemas/findings.json, schemas/verification.json, schemas/report.json
  ├── README.md
  └── _workspace/00_input/query.md

graph.json instance (3-node pipeline, the topology=pipeline reflect-then-revise case from D-4 combo #1):
  nodes:
    gather   -> agent researcher,  model haiku,  decision_mechanism single,
                inputs [_workspace/00_input/query.md], outputs [_workspace/01_gather/findings.json],
                write_paths [_workspace/01_gather/], output_schema schemas/findings.json
    verify   -> agent verifier,    model sonnet, decision_mechanism single,
                inputs [_workspace/01_gather/findings.json], outputs [_workspace/02_verify/verification.json],
                write_paths [_workspace/02_verify/], output_schema schemas/verification.json
    synthesize -> agent synthesizer, model opus, decision_mechanism reflect-then-revise,
                mechanism_params {max_rounds:2, critic:opus},
                inputs [_workspace/02_verify/verification.json], outputs [_workspace/03_report/report.md],
                write_paths [_workspace/03_report/], output_schema schemas/report.json
  edges: gather->verify, verify->synthesize
  budget: {total_tokens:600000, approval_required:true}

INVOCATION:
  python3 validate_harness.py /Users/cys/Desktop/CYSjavis/cys-harness-creartor/harnesses/deep-research --json

EXPECTED HUMAN OUTPUT (the PASS-with-one-warn case — opus is justified on synthesize because
decision_mechanism != single, so MODEL_OPUS_ON_RETRIEVAL does NOT fire there; the one warn shown
is the intentionally-seeded drift demo):

  [WARN ] README_SKILL_PHASE_MATCH   phase-count drift: README declares 3 phases but orchestrator declares 4
  [SKIP ] GRAPH_SCHEMA_VALID         jsonschema present -> (this line only if dep missing; normally OK)

  0 error(s), 1 warning(s), 0 skipped, 23 ok -> exit 0

EXPECTED JSON (abridged):
  {"report_version":"1.0","harness_name":"deep-research","harness_version":"0.1.0",
   "summary":{"errors":0,"warnings":1,"skipped":0,"passed":23,"total":24},"exit_code":0,
   "results":[
     {"id":"GRAPH_PARSEABLE","status":"ok",...},
     {"id":"AGENT_FILE_EXISTS","status":"ok","node_id":"gather",...},
     {"id":"NODE_MODEL_TIER_LEGAL","status":"ok","node_id":"synthesize",...},
     {"id":"MODEL_OPUS_ON_RETRIEVAL","status":"ok","node_id":"synthesize",
      "message":"opus permitted: decision_mechanism 'reflect-then-revise' is not pure-retrieval"},
     {"id":"LOCK_UNIQUE_OWNER","status":"ok",...},
     {"id":"README_SKILL_PHASE_MATCH","status":"warn",
      "message":"phase-count drift: README declares 3 phases but orchestrator declares 4",
      "remediation":"reconcile README 'Phase N' headings with SKILL.md phase headings"}
   ]}

NEGATIVE/GATE DEMO (M0 success criterion #2 "망가뜨린 agent참조에서 validate 빌드실패"):
  Rename .claude/agents/researcher.md -> researcher.bak, re-run:
  [ERROR] AGENT_FILE_EXISTS          node 'gather' references agent 'researcher' but .claude/agents/researcher.md does not exist
  1 error(s), 0 warning(s), 0 skipped, 23 ok -> exit 1     # build/CI gate trips

WRITE-LOCK CONFLICT DEMO (W8 pre-flight): if graph.json gave both gather and verify
write_paths "_workspace/01_gather/":
  [ERROR] LOCK_UNIQUE_OWNER  write-path conflict: '_workspace/01_gather/' (owner gather) overlaps '_workspace/01_gather/' (owner verify); each write_path needs exactly one owner
  -> exit 1

## READS
['<HARNESS_DIR>/.harness/graph.json', '<HARNESS_DIR>/.harness/harness.lock', '<HARNESS_DIR>/.claude/agents/*.md', '<HARNESS_DIR>/.claude/skills/*/SKILL.md', '<HARNESS_DIR>/schemas/*.json', '<HARNESS_DIR>/README*.md', '<HARNESS_DIR>/_workspace/** (declared inputs)', '<HARNESS_DIR>/.claude/commands/ (asserted absent)', '<script_dir>/schemas/graph.schema.json']

## WRITES
['stdout (human table or --json report)', '--report PATH (JSON report)', 'process exit code 0|1|2']

## EDGE CASES
- output_schema == "" (free-text node): OUTPUT_SCHEMA_EXISTS/VALID_JSON are skipped with status ok, never error — empty schema is the spine's documented 'no StructuredOutput' signal.
- A node.input that is produced by an upstream node's outputs must NOT be flagged missing (it does not exist until runtime); NODE_INPUTS_EXIST cross-references all nodes' outputs before flagging.
- jsonschema or PyYAML not installed: degrade — GRAPH_SCHEMA_VALID and frontmatter checks emit status 'skipped' with a NOTE rather than crashing; cheap structural checks still run so the linter is never a hard dep wall.
- execution_mode=team (Mode B fallback): workflow-specific checks (GRAPH_NO_CYCLE for pipeline) are scoped out; LOCK_* checks become MORE important (teams have no budget ceiling, only the lock + hooks enforce write isolation) and stay error-severity.
- topology=producer-reviewer: GRAPH_NO_CYCLE is intentionally skipped because the loop is legal; do not false-positive on the reviewer->producer back-edge.
- Path overlap normalization: '_workspace/01_gather' vs '_workspace/01_gather/' must be treated identical; and parent/child containment ('/a/' vs '/a/b/') must count as overlap, not just exact equality.
- opus legitimacy: opus on a node is only WARNed when role matches retrieval RX AND decision_mechanism=='single'. opus on synthesize/judge/critic or any multi-call mechanism is correct per D-3 and must pass silently.
- Korean keywords (재실행/수정/보완) and English follow-up keywords are both accepted by FOLLOWUP_RX — harnesses in this codebase are bilingual.
- Absolute-path resolution: HARNESS_DIR itself is realpath'd first so a relative invocation ('.') still yields absolute file paths in messages; relative-path detection in PROSE must not flag the spine's _workspace//schemas/ io fields inside graph.json.
- Symlinked .claude/skills entries (this repo uses symlinks heavily): resolve via Path.exists() which follows symlinks, so a valid symlinked skill is NOT a dead reference.
- Empty .claude/commands/ directory exists but holds no *.md: treated as PASS (NO_COMMANDS_DIR only errors on actual command files), tolerating an accidentally-created empty dir.
- Multiple SKILL.md under .claude/skills/*: the ORCHESTRATOR is identified as the skill whose frontmatter name matches harness_name + '-orchestrator' or, failing that, the only one referencing the graph nodes; ambiguity => ORCH_SKILL_EXISTS passes but a NOTE flags which was chosen.

## FEASIBILITY
FULLY FEASIBLE with zero Claude Code runtime primitives. This is the cleanest M0 component precisely BECAUSE it is static: it runs at author/build/CI time as a plain `python3` process and never invokes TeamCreate/Agent/TaskCreate/Workflow/hooks. Therefore none of the six verified platform constraints apply to it: it does not need an LLM turn (constraint 1), does not express depends_on (it READS graph.json's edges, which the spine explicitly says are ordering-only, not TaskCreate deps — constraint 2), does not rely on hooks for aggregation (constraint 3), needs no wall-clock (constraint 4 — and note the Workflow tool itself bans the time/RNG builtins; this validator is NOT a workflow script so it may use the clock, but it deliberately does not, keeping output deterministic for golden-file testing), and needs no resume token (constraint 5). It is the deterministic complement to the Workflow runtime (constraint 6): the Workflow budget ceiling guards runtime cost, while this linter guards STRUCTURE before any token is spent. Environment verified on this machine: python3 3.14.4 at /opt/homebrew/bin/python3, jsonschema importable, PyYAML importable. CONSTRAINT IT MUST RESPECT: it can only assert what is statically checkable — it CANNOT verify that workflow.js actually honors graph.json semantics at runtime (e.g. that pipeline() truly follows edges, or that agent({model}) really uses node.model). Best feasible approximation: cross-check the DECLARED contract (graph.json <-> agent files <-> harness.lock <-> SKILL/README) for internal consistency, and leave behavioral verification to the runtime budget ceiling + the head-to-head benchmark (M0 success criterion #5). A second honest limit: ABSOLUTE_PATHS_IN_PROSE and DEAD_*_REFERENCE are regex/heuristic over prose, so they can miss obfuscated paths or false-positive on documentation examples; they are therefore WARN (not error) except where the spine makes the rule hard (NO_COMMANDS_DIR, AGENT_FILE_EXISTS, GRAPH_SCHEMA_VALID, LOCK_UNIQUE_OWNER are error). The validator references the spine's EXACT field names (execution_mode, topology, budget.total_tokens, budget.approval_required, nodes[].id/agent/model/decision_mechanism/mechanism_params/inputs/outputs/write_paths/output_schema/retries/on_exhaust/max_rounds, edges[].from/to) so it stays coherent with the workflow-emitter and harness.lock components that consume the same spine.

## OPEN QUESTIONS
- Phase-count source of truth: should the SKILL-side count come from a structured field (e.g. meta.phases length in a sibling workflow.js, mirroring the Workflow tool's `export const meta = {phases:[...]}`) rather than counting '# Phase N' headings? Using meta.phases would make README_SKILL_PHASE_MATCH exact instead of regex-heuristic — recommend wiring it to meta.phases.length once the workflow.js emitter component fixes that field's location.
- harness.lock concrete schema is owned by a sibling component; this spec assumes shape {"owners":[{"node":"gather","write_paths":["_workspace/01_gather/"]}, ...]}. The LOCK_* checks must be re-pinned to that component's final field names (the spine says write_paths -> harness.lock ownership but does not fix the lock's internal keys).
- Should ABSOLUTE_PATHS_IN_PROSE be error or warn? The strategy lists 'absolute paths only' as a hard rule, but prose regex has false-positive risk on doc examples. Recommend: error for paths in AGENT instruction frontmatter/agent body, warn for paths inside fenced code blocks (likely examples). Needs master sign-off on strictness.
- Is opus-on-retrieval truly only a warn, or should --strict + a release gate make it an error? D-3 says 'model:opus 전역 금지' (global ban) which sounds like error, but per-node justification (multi-call mechanisms) exists — current design: warn by default, promotable via --strict. Confirm this matches the cost-governance bet's intended teeth.
- Cross-harness uniqueness: M2 migrates ~30 harnesses; should there be a fleet-level check that two harnesses don't claim the same absolute _workspace path? Out of scope for M0 (per-harness only) but flag for M2 harness import adapter.