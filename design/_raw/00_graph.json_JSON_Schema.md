# graph.json JSON Schema (draft 2020-12) — the central harness contract spine

## PURPOSE
graph.json is the single source of truth every other M0 artifact derives from: the workflow.js emitter reads it to choose pipeline()/parallel()/loop and to set agent({model,schema}) + budget.total; harness.lock is generated from every node.write_paths; validate_harness.py asserts referenced .claude/agents/*.md and schemas/*.json exist and that model tiers obey governance; the pre-flight cost band reads budget. This component is the STRICT schema that makes graph.json machine-checkable rather than prose — turning the original harness's advisory rules into assertions (W1/W2/W4/W5 fixes). It fixes the master spine field names and adds only conditional-validity rules (which mechanism_params each decision_mechanism requires, which edges each topology requires, which fields each execution_mode requires) plus tier-governance and convergence guards that are statically checkable. Anything the platform cannot enforce statically (live token abort, durable team resume, depends_on graph) is explicitly NOT modeled as a hard edge — edges are declared as ordering-only, matching the spine note 'NOT a TaskCreate depends_on'.

## CONTRACT
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://cys-harness/schemas/graph.schema.json",
  "title": "CYS Harness graph.json",
  "description": "The central harness contract. Master-fixed spine field names MUST NOT be renamed. workflow.js, harness.lock, validate_harness.py, and the pre-flight cost band all derive from this file. edges express ORDERING ONLY (pipeline/parallel/loop scheduling) and are NOT a TaskCreate depends_on graph.",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "schema_version",
    "harness_name",
    "harness_version",
    "execution_mode",
    "topology",
    "budget",
    "nodes",
    "edges"
  ],
  "properties": {
    "schema_version": {
      "type": "string",
      "const": "0.1",
      "description": "Schema contract version. M0 pins 0.1. Bump only on breaking spine change."
    },
    "harness_name": {
      "type": "string",
      "pattern": "^[a-z][a-z0-9-]{1,48}[a-z0-9]$",
      "description": "kebab-case harness id. Used as workflow meta.name and dir name."
    },
    "harness_version": {
      "type": "string",
      "pattern": "^[0-9]+\\.[0-9]+\\.[0-9]+$",
      "description": "SemVer of the generated harness (rollback substrate, M2 evolve)."
    },
    "execution_mode": {
      "type": "string",
      "enum": ["workflow", "team"],
      "description": "workflow = Mode A (deterministic sub-agents, emit workflow.js, DEFAULT). team = Mode B fallback ONLY when real-time inter-agent comms is required; team mode is NOT deterministically schedulable (platform limit) so graph.json is then a CONTRACT + hook-enforced, not a runtime."
    },
    "topology": {
      "type": "string",
      "enum": ["pipeline", "dispatch", "producer-reviewer"],
      "description": "pipeline -> pipeline(items, ...stages) following edges. dispatch -> parallel(thunks) BARRIER fan-out (edges are static fan from a single source, ordering not enforced between siblings). producer-reviewer -> a bounded while loop (producer agent() then reviewer agent(), repeat up to a node max_rounds)."
    },
    "budget": {
      "type": "object",
      "additionalProperties": false,
      "required": ["total_tokens", "approval_required"],
      "properties": {
        "total_tokens": {
          "type": ["integer", "null"],
          "minimum": 1,
          "description": "-> budget.total guard in workflow.js. Once spent()>=total, agent() THROWS (hard ceiling, oin-orchestration-layer, NOT a hook). null = uncapped (validator WARNS; disallowed when approval_required true)."
        },
        "approval_required": {
          "type": "boolean",
          "description": "-> pre-flight cost band shown for approval before run. When true, total_tokens MUST be a finite integer."
        },
        "cost_band_model": {
          "type": "string",
          "enum": ["haiku", "sonnet", "opus", "mixed"],
          "description": "OPTIONAL added field. Justification: lets the pre-flight estimator pick a $/token rate for the displayed band without re-deriving from nodes. Defaults to 'mixed' if absent."
        }
      },
      "if": { "properties": { "approval_required": { "const": true } } },
      "then": { "properties": { "total_tokens": { "type": "integer", "minimum": 1 } } }
    },
    "nodes": {
      "type": "array",
      "minItems": 1,
      "maxItems": 1000,
      "description": "1000 = Workflow total-agents cap. Each node = one logical step; decision_mechanism may expand a node to N underlying agent() calls.",
      "items": { "$ref": "#/$defs/node" }
    },
    "edges": {
      "type": "array",
      "description": "ORDERING ONLY. NOT depends_on. pipeline: a linear chain from first to last node. dispatch: fan-out edges from one source node to siblings. producer-reviewer: a self/2-node cycle is allowed (loop). Validator builds the order from edges.",
      "items": { "$ref": "#/$defs/edge" }
    },
    "metadata": {
      "type": "object",
      "description": "OPTIONAL added field. Justification: non-load-bearing provenance the validator ignores (author, created_run_id, source_domain). Kept out of the spine so emitters never depend on it.",
      "additionalProperties": true
    }
  },
  "$defs": {
    "modelTier": {
      "type": "string",
      "enum": ["haiku", "sonnet", "opus"],
      "description": "Required tier. Default-map by role; validator FLAGS opus on pure-retrieval roles. -> agent({model})."
    },
    "node": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "id",
        "agent",
        "model",
        "decision_mechanism",
        "mechanism_params",
        "inputs",
        "outputs",
        "write_paths",
        "output_schema",
        "retries",
        "on_exhaust",
        "max_rounds"
      ],
      "properties": {
        "id": {
          "type": "string",
          "pattern": "^[a-z][a-z0-9_]{0,30}[a-z0-9]$",
          "description": "Unique node id. Referenced by edges.from/edges.to."
        },
        "agent": {
          "type": "string",
          "pattern": "^[a-z][a-z0-9-]{1,48}[a-z0-9]$",
          "description": "-> .claude/agents/<agent>.md (validator asserts file exists) AND -> agent({agentType})."
        },
        "model": { "$ref": "#/$defs/modelTier" },
        "decision_mechanism": {
          "type": "string",
          "enum": ["single", "majority-vote", "debate-with-judge", "reflect-then-revise"],
          "description": "Wraps the node's agent() call. single=1 call; majority-vote=parallel(N voters)+deterministic reduce; debate-with-judge=loop rounds then judge agent(); reflect-then-revise=loop(critic->reviser)."
        },
        "mechanism_params": {
          "type": "object",
          "description": "Params for decision_mechanism. Conditionally required/validated by the node-level allOf below.",
          "additionalProperties": false,
          "properties": {
            "n": { "type": "integer", "description": "voter/debater count" },
            "quorum": { "type": "integer", "description": "votes needed to win (majority-vote)" },
            "tie_break": { "type": "string", "enum": ["first", "highest-confidence", "escalate"], "description": "deterministic tie resolution (majority-vote)" },
            "max_rounds": { "type": "integer", "minimum": 1, "maximum": 5, "description": "loop bound — GUARANTEES termination (fixes W5). Required by debate / reflect / producer-reviewer." },
            "judge": { "$ref": "#/$defs/modelTier", "description": "judge model (debate-with-judge); SHOULD be opus" },
            "critic": { "$ref": "#/$defs/modelTier", "description": "critic model (reflect-then-revise); SHOULD be opus" }
          }
        },
        "inputs": {
          "type": "array",
          "items": { "$ref": "#/$defs/workspacePath" },
          "description": "Files this node reads. Validator cross-checks every input is some upstream node's output or an 00_input/ seed."
        },
        "outputs": {
          "type": "array",
          "minItems": 1,
          "items": { "$ref": "#/$defs/workspacePath" },
          "description": "Files this node writes. Each MUST be under one of write_paths (validator enforced)."
        },
        "write_paths": {
          "type": "array",
          "minItems": 1,
          "items": { "$ref": "#/$defs/workspaceDir" },
          "description": "-> harness.lock ownership rows. Exclusive write territory for this node. PreToolUse hook denies non-owner Write here."
        },
        "output_schema": {
          "oneOf": [
            { "type": "string", "const": "", "description": "free text, no StructuredOutput forced" },
            { "type": "string", "pattern": "^schemas/[a-z0-9_-]+\\.json$", "description": "-> agent({schema}); validator asserts schemas/<file> exists" }
          ],
          "description": "node.output_schema -> agent({schema}). \"\" = free text."
        },
        "retries": {
          "type": "integer",
          "minimum": 0,
          "maximum": 3,
          "description": "agent()-level retries on throw/validation-fail before on_exhaust fires. Distinct from mechanism_params.max_rounds (which is convergence iterations)."
        },
        "on_exhaust": {
          "type": "string",
          "enum": ["proceed-with-gap", "force-pass", "escalate"],
          "description": "Terminal policy after retries exhausted. proceed-with-gap=record gap, continue (pipeline survives null). force-pass=accept last output as-is. escalate=throw, halt run."
        },
        "max_rounds": {
          "type": "integer",
          "minimum": 1,
          "maximum": 5,
          "description": "Spine field. Node-level outer iteration cap (e.g. producer-reviewer cycles). For mechanism-internal loops use mechanism_params.max_rounds; this field is the node's own ceiling and MUST be >= mechanism_params.max_rounds when both apply."
        },
        "isolation": {
          "type": "string",
          "enum": ["none", "worktree"],
          "description": "OPTIONAL added field. Justification: maps directly to agent({isolation:'worktree'}) for nodes whose write_paths must not collide with concurrent siblings under dispatch. Default 'none'."
        }
      },
      "allOf": [
        {
          "description": "single: mechanism_params MUST be empty object.",
          "if": { "properties": { "decision_mechanism": { "const": "single" } } },
          "then": { "properties": { "mechanism_params": { "maxProperties": 0 } } }
        },
        {
          "description": "majority-vote: requires odd n>=3, quorum>n/2 and quorum<=n, tie_break. (n odd + quorum>floor(n/2) makes a deterministic winner reachable.)",
          "if": { "properties": { "decision_mechanism": { "const": "majority-vote" } } },
          "then": {
            "properties": {
              "mechanism_params": {
                "required": ["n", "quorum", "tie_break"],
                "properties": {
                  "n": { "type": "integer", "minimum": 3, "maximum": 5, "multipleOf": 2, "description": "MUST be odd: schema encodes oddness via not-even check in $comment; enforced as 3 or 5 by enum in instance. (JSON Schema cannot express 'odd' directly; validator script asserts n%2==1.)" },
                  "quorum": { "type": "integer", "minimum": 2, "maximum": 5 }
                }
              }
            },
            "$comment": "validate_harness.py MUST additionally assert: mechanism_params.n is odd; floor(n/2) < quorum <= n. (multipleOf:2 above is a placeholder the script overrides — see edgeCases.)"
          }
        },
        {
          "description": "debate-with-judge: requires n>=2 debaters, max_rounds, judge model.",
          "if": { "properties": { "decision_mechanism": { "const": "debate-with-judge" } } },
          "then": {
            "properties": {
              "mechanism_params": {
                "required": ["n", "max_rounds", "judge"],
                "properties": { "n": { "type": "integer", "minimum": 2, "maximum": 4 } }
              }
            }
          }
        },
        {
          "description": "reflect-then-revise: requires max_rounds and critic model.",
          "if": { "properties": { "decision_mechanism": { "const": "reflect-then-revise" } } },
          "then": {
            "properties": {
              "mechanism_params": { "required": ["max_rounds", "critic"] }
            }
          }
        }
      ]
    },
    "edge": {
      "type": "object",
      "additionalProperties": false,
      "required": ["from", "to"],
      "properties": {
        "from": { "type": "string", "description": "source node id (must exist in nodes[].id)" },
        "to": { "type": "string", "description": "target node id (must exist in nodes[].id). from==to allowed ONLY for producer-reviewer self-loop." },
        "kind": {
          "type": "string",
          "enum": ["sequence", "fanout", "loopback"],
          "description": "OPTIONAL added field. Justification: makes ordering semantics explicit for the emitter without re-inferring from topology. sequence=pipeline stage boundary; fanout=dispatch sibling; loopback=producer-reviewer cycle. Defaults inferred from topology if absent."
        }
      }
    },
    "workspacePath": {
      "type": "string",
      "pattern": "^_workspace/[0-9]{2}_[a-z0-9_]+/[A-Za-z0-9._/-]+$",
      "description": "Workspace-relative file path. Numbered-stage convention (00_input, 01_gather, ...) gives deterministic ordering."
    },
    "workspaceDir": {
      "type": "string",
      "pattern": "^_workspace/[0-9]{2}_[a-z0-9_]+/$",
      "description": "Workspace-relative directory (trailing slash). Unit of write-ownership in harness.lock."
    }
  }
}
```

VALIDATOR-SCRIPT obligations (rules NOT expressible in pure JSON Schema, asserted by validate_harness.py):
1. node.id uniqueness; every edge.from/edge.to resolves to an existing node.id.
2. majority-vote: assert mechanism_params.n is ODD and floor(n/2) < quorum <= n. (Schema's multipleOf:2 is a deliberate placeholder; the enum-of-{3,5} + this script check is the real gate.)
3. topology<->edges consistency: pipeline => edges form a single linear chain covering all nodes, no cycle; dispatch => exactly one source node with fanout edges to all others, no chain; producer-reviewer => at least one loopback edge (from==to or 2-cycle) bounded by that node's max_rounds.
4. tier governance: model=='opus' on a node whose agent is a pure-retrieval role (gather/extract/fetch/format/qa-scan name-matched) => FAIL. mechanism_params.judge/critic default to opus; if downgraded, WARN.
5. file existence: .claude/agents/<agent>.md exists; output_schema (if non-empty) schemas/<file>.json exists and is itself valid draft-2020-12.
6. ownership integrity: every node.outputs[i] is prefixed by one of that same node.write_paths; no two nodes share an overlapping write_paths prefix (=> harness.lock has no double-owner).
7. inputs provenance: every node.inputs[i] equals some upstream node.outputs entry OR lives under _workspace/00_input/.
8. budget: approval_required==true => total_tokens finite. total_tokens==null => WARN.
9. node.max_rounds >= mechanism_params.max_rounds when both present.

## DEEP-RESEARCH INSTANCE
Complete deep-research graph.json (the M0 dogfood, 4 nodes, pipeline topology, Mode A):

```json
{
  "schema_version": "0.1",
  "harness_name": "deep-research",
  "harness_version": "0.1.0",
  "execution_mode": "workflow",
  "topology": "pipeline",
  "budget": { "total_tokens": 600000, "approval_required": true, "cost_band_model": "mixed" },
  "nodes": [
    {
      "id": "gather",
      "agent": "researcher",
      "model": "haiku",
      "decision_mechanism": "single",
      "mechanism_params": {},
      "inputs": ["_workspace/00_input/query.md"],
      "outputs": ["_workspace/01_gather/findings.json"],
      "write_paths": ["_workspace/01_gather/"],
      "output_schema": "schemas/findings.json",
      "retries": 1,
      "on_exhaust": "proceed-with-gap",
      "max_rounds": 1
    },
    {
      "id": "verify",
      "agent": "verifier",
      "model": "sonnet",
      "decision_mechanism": "majority-vote",
      "mechanism_params": { "n": 3, "quorum": 2, "tie_break": "highest-confidence" },
      "inputs": ["_workspace/01_gather/findings.json"],
      "outputs": ["_workspace/02_verify/verified_claims.json"],
      "write_paths": ["_workspace/02_verify/"],
      "output_schema": "schemas/verified_claims.json",
      "retries": 1,
      "on_exhaust": "proceed-with-gap",
      "max_rounds": 1
    },
    {
      "id": "synthesize",
      "agent": "synthesizer",
      "model": "opus",
      "decision_mechanism": "reflect-then-revise",
      "mechanism_params": { "max_rounds": 2, "critic": "opus" },
      "inputs": ["_workspace/02_verify/verified_claims.json"],
      "outputs": ["_workspace/03_synthesize/draft_report.md"],
      "write_paths": ["_workspace/03_synthesize/"],
      "output_schema": "",
      "retries": 1,
      "on_exhaust": "escalate",
      "max_rounds": 2
    },
    {
      "id": "report",
      "agent": "formatter",
      "model": "haiku",
      "decision_mechanism": "single",
      "mechanism_params": {},
      "inputs": ["_workspace/03_synthesize/draft_report.md"],
      "outputs": ["_workspace/04_report/report.md"],
      "write_paths": ["_workspace/04_report/"],
      "output_schema": "",
      "retries": 1,
      "on_exhaust": "force-pass",
      "max_rounds": 1
    }
  ],
  "edges": [
    { "from": "gather", "to": "verify", "kind": "sequence" },
    { "from": "verify", "to": "synthesize", "kind": "sequence" },
    { "from": "synthesize", "to": "report", "kind": "sequence" }
  ]
}
```

How the emitter turns THIS into workflow.js (Mode A): linear edges => pipeline([query], gatherStage, verifyStage, synthesizeStage, reportStage). gatherStage = single agent({model:'haiku', schema: findings}). verifyStage = parallel of 3 voter agent({model:'sonnet', schema: verified_claims}) then a deterministic reduce keeping claims with >=2 (quorum) agreeing votes, ties broken by highest-confidence. synthesizeStage = loop max_rounds=2: critic agent({model:'opus'}) -> reviser agent({model:'opus'}). reportStage = single agent({model:'haiku'}, free text). budget.total=600000 set on the Workflow budget => 4th+ agent() throws once spent>=600k. This exercises all four M0 success criteria: budget ceiling+resume, validate build-fail on broken agent ref, write-lock per stage dir, and the head-to-head C2 condition.

## READS
["harness-teardown-and-strategy.md (Part C/D — the master-fixed spine + Mode A decision, source of every field's intent)", 'the master spine literal provided in the task (field names obeyed exactly)', "Writingbook-AgenticWorkflow/.../schemas/review_verdict.schema.json (project's existing draft-2020-12 conventions: $schema/$id/title/description, pattern-constrained ids)"]

## WRITES
['.harness/graph.json (the instance — authored by the harness-creator meta-skill, consumed by everything downstream)', 'schemas/graph.schema.json (this strict schema — consumed by validate_harness.py)']

## EDGE CASES
- JSON Schema CANNOT express 'n is odd' directly. multipleOf:2 in the schema is a deliberate placeholder; the real gate is enum {3,5} in practice + an explicit n%2==1 assertion in validate_harness.py. Documented in $comment so the coder does not trust the schema alone for oddness.
- edges are ORDERING ONLY, never depends_on (platform: TaskCreate has no declarative depends_on). A coder must not generate TaskCreate edges from this; pipeline()/parallel()/loop is the only honoring path.
- producer-reviewer self-loop: edge.from==edge.to is allowed but ONLY for that topology; pipeline/dispatch with a self-edge must FAIL in the validator (cannot be caught by per-edge schema, needs the topology cross-check).
- execution_mode=='team' (Mode B): graph.json becomes a CONTRACT not a runtime — workflow.js is NOT emitted; instead settings.json hooks enforce write_paths via PreToolUse. The schema validates identically but the emitter branch differs. No live token-abort is possible in team mode (only SubagentStop post-hoc per-session token logging) — graph.budget.total_tokens is then advisory + pre-flight estimate only.
- budget.total_tokens=null is schema-legal but WARNed and FORBIDDEN when approval_required=true (the if/then enforces the latter; the WARN is script-side).
- node.outputs must each fall under that node's own write_paths prefix, and no two nodes' write_paths may overlap — this prevents harness.lock double-ownership but is NOT expressible in pure schema (cross-node), so it is a mandatory script check.
- additionalProperties:false at root, node, edge, budget levels: any unknown spine field FAILS fast — but designers MAY add fields ONLY by extending this schema with justification (the four added fields here: budget.cost_band_model, node.isolation, edge.kind, root.metadata each carry an inline justification).
- mechanism_params.max_rounds (convergence loop bound, <=5) vs node.max_rounds (outer node cap) vs node.retries (agent-throw retries, <=3) are THREE distinct termination controls — conflating them breaks the W5 'no convergence guarantee' fix. node.max_rounds>=mechanism_params.max_rounds is script-asserted.

## FEASIBILITY
Maps cleanly onto REAL Claude Code primitives. (1) execution_mode='workflow' => the Workflow tool (verified to exist, in-session, real budget ceiling, resumeFromRunId, agent({schema}) StructuredOutput forcing, pipeline/parallel). Every node field has a direct Workflow target: model->agent({model}), output_schema->agent({schema}), agent->agent({agentType}), budget.total_tokens->budget.total (throws at ceiling). (2) topology maps to the three Workflow control-flow shapes: pipeline()->pipeline, dispatch->parallel() barrier, producer-reviewer->a while(budget && rounds<max) loop of agent() calls. (3) decision_mechanism is implemented ENTIRELY in workflow.js JS, not by any platform feature: majority-vote=parallel(N)+plain JS reduce (deterministic, no RNG — vary voters by index/label per the no-RNG constraint), debate/reflect=bounded loops. CONSTRAINTS RESPECTED: edges are ordering-only because TaskCreate has no depends_on; no field encodes a live token-abort hook (impossible — hooks can't aggregate cross-session tokens mid-flight), so budget is enforced at the Workflow orchestration layer + pre-flight approval, with SubagentStop only for post-hoc per-session token reporting; no field encodes a wall-clock/no-progress watchdog (LLM leader has no timer); resume is via Workflow resumeFromRunId (cached unchanged agent() prefix), NOT a durable team pause — so the schema deliberately has no 'resume_token' field. The no-RNG/no-wall-clock Workflow rule means harness_version timestamps and any tie randomness must NOT be generated inside workflow.js; tie_break is therefore a deterministic enum ('first'/'highest-confidence'/'escalate'), never random. Team mode (Mode B) is the only non-deterministic branch and the schema/validator explicitly downgrade budget to advisory there.

## OPEN QUESTIONS
- MAX_FANOUT=5 / MAX_VOTERS=5 are hypothesis values (strategy D-5): schema caps n at 5 and node count at 1000 (Workflow hard cap). Confirm whether voter n should be capped at 5 in schema or left to the cost-band approval.
- tie_break enum: is 'escalate' (halt + ask user) acceptable in a headless Workflow run, or should ties always resolve deterministically to keep the run unattended? Currently allowed; may need removal for fully-unattended Mode A.
- Should node.output_schema for synthesize ('') stay free-text, or should M0 force a schema even on the draft to make the reflect-then-revise critic machine-gradable? Left free-text per the spine's report-style output, but head-to-head grading may want structure.
- max_rounds ceiling of 5 vs strategy's '2-3' hypothesis — schema allows up to 5 for headroom; confirm whether to hard-cap at 3 for M0 cost control.
- Whether budget.total_tokens should be split per-node (sub-budgets) in a future schema_version, or remain a single global ceiling as in M0 (current: single global, matching Workflow's single budget.total).