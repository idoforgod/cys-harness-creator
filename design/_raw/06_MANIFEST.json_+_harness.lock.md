# MANIFEST.json + harness.lock (provenance/drift/evolve ledger + write-ownership lock)

## PURPOSE
Two deterministic, content-addressed artifacts that turn the graph.json spine into (1) a provenance ledger that makes Phase-0 drift detection and `evolve` minimal-re-run computable by a plain shell/JS script with NO LLM in the loop, and (2) a write-ownership lock consumed by the PreToolUse hook to enforce per-node path isolation.

MANIFEST.json answers "what produced this artifact, from what inputs, and has anything changed since?" — one record per declared `node.outputs` path. It is the cache key for evolve: re-run a node iff its input hashes changed OR its agent/spec definition changed OR an upstream output (that is one of its inputs) changed. This is the deterministic analogue of Workflow's own agent()-prefix caching, lifted to the harness/graph level so it survives across separate runs (Workflow's cache is per-run/resume only — constraint #5: checkpoints are best-effort artifacts the NEXT run re-reads).

harness.lock answers "which node exclusively owns each write path?" — derived purely from `node.write_paths`. The validator rejects any overlap at build time; the PreToolUse hook enforces it at run time, giving the only feasible write-isolation guarantee (constraint #3: a hook fires at tool-call boundaries and CAN deterministically allow/deny a single Write/Edit by path; it CANNOT aggregate tokens, so we use it for what it can do — path gating).

## CONTRACT
================================================================
A) MANIFEST.json  (path: <harness_root>/MANIFEST.json)
   One entry per artifact = per graph.json node.outputs[] path.
================================================================
JSON Schema (draft 2020-12):
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["schema_version","harness_name","harness_version","manifest_algo","graph_hash","artifacts"],
  "properties": {
    "schema_version": { "const": "0.1" },          // tracks MANIFEST format, NOT graph
    "harness_name":   { "type": "string" },         // mirrors graph.json.harness_name
    "harness_version":{ "type": "string" },         // mirrors graph.json.harness_version at gen time
    "manifest_algo":  { "const": "sha256" },        // hash algo for all *_hash fields
    "graph_hash":     { "type": "string" },         // sha256 of canonical graph.json (global invalidation)
    "generated_at":   { "type": "string" },         // ISO8601 stamped AFTER run (never used in a hash; constraint: no wall-clock inside workflow.js)
    "artifacts": {
      "type": "object",
      "additionalProperties": {                     // KEY = the output path, verbatim from node.outputs[]
        "type": "object",
        "required": ["producing_node","producing_agent","model","decision_mechanism",
                     "input_hashes","def_hash","content_hash","harness_version","generated_at"],
        "properties": {
          "producing_node":  { "type": "string" },  // graph.json node.id
          "producing_agent": { "type": "string" },  // graph.json node.agent (-> .claude/agents/<agent>.md)
          "model":           { "type": "string" },  // graph.json node.model  (def_hash input)
          "decision_mechanism": { "type": "string" },// graph.json node.decision_mechanism (def_hash input)
          "input_hashes": {                          // EXACTLY node.inputs[] (no globbing), each hashed
            "type": "array",
            "items": {
              "type": "object",
              "required": ["path","sha256"],
              "properties": {
                "path":   { "type": "string" },
                "sha256": { "type": "string", "pattern": "^[0-9a-f]{64}$|^MISSING$" }
              }
            }
          },
          "def_hash":     { "type": "string" },      // sha256 of the NODE DEFINITION fingerprint (see C)
          "content_hash": { "type": "string" },      // sha256 of the produced artifact bytes
          "harness_version": { "type": "string" },
          "generated_at": { "type": "string" }       // per-artifact stamp, post-run
        }
      }
    }
  }
}

================================================================
B) harness.lock  (path: <harness_root>/harness.lock)
   Pure function of graph.json node.write_paths. No hashes.
================================================================
JSON Schema (draft 2020-12):
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["schema_version","harness_name","workspace_root","ownership","policy"],
  "properties": {
    "schema_version": { "const": "0.1" },
    "harness_name":   { "type": "string" },
    "workspace_root": { "type": "string" },          // e.g. "_workspace/" — all owned paths must be under it
    "ownership": {                                    // normalized, dir-prefix -> single owner node
      "type": "array",
      "items": {
        "type": "object",
        "required": ["path","owner_node","owner_agent"],
        "properties": {
          "path":        { "type": "string" },        // normalized write_path (trailing "/" => dir prefix; else exact file)
          "owner_node":  { "type": "string" },         // graph.json node.id
          "owner_agent": { "type": "string" }          // graph.json node.agent
        }
      }
    },
    "policy": {
      "type": "object",
      "required": ["on_violation","unowned_path"],
      "properties": {
        "on_violation": { "enum": ["deny","warn"] },   // M0 default "deny"
        "unowned_path": { "enum": ["deny","allow"] }   // writes outside any owned prefix; M0 default "allow"
                                                        // (so agents can scribble scratch under their own tmp);
                                                        // set "deny" to lock the workspace fully.
      }
    }
  }
}

================================================================
C) def_hash — the node-definition fingerprint (load-bearing for evolve)
================================================================
def_hash = sha256( canonical_json({
  "agent":             node.agent,
  "agent_md_sha256":   sha256(.claude/agents/<node.agent>.md),   // <-- the "researcher edited" trigger
  "model":             node.model,
  "decision_mechanism":node.decision_mechanism,
  "mechanism_params":  node.mechanism_params,
  "output_schema":     node.output_schema,
  "output_schema_sha256": node.output_schema ? sha256(<output_schema file>) : "",
  "retries":           node.retries,
  "on_exhaust":        node.on_exhaust,
  "max_rounds":        node.max_rounds
}) )
Rationale: editing .claude/agents/researcher.md changes agent_md_sha256 -> def_hash -> the gather node is dirty even though its inputs (query.md) are byte-identical. This is the exact dogfood case.

canonical_json(x): `jq -S -c .`  (verified order-stable; key-sorted, no whitespace).
file hash:        `shasum -a 256 <f> | cut -c1-64`  (or sha256sum). Missing file -> "MISSING".

================================================================
D) DRIFT (Phase-0) — recompute & diff, deterministic, no LLM
   Run at the START of every harness invocation, before any agent().
================================================================
phase0_drift(harness_root):
  manifest = read MANIFEST.json   # if absent -> COLD: every node dirty, skip rest
  graph    = read graph.json
  # 1. global guard
  if sha256(canonical(graph)) != manifest.graph_hash: return ALL_DIRTY("graph changed")
  drift = []
  for art_path, rec in manifest.artifacts:
     # a) output tamper check
     if not exists(art_path):                 drift += {art_path, "output-missing"}; continue
     if sha256(art_path) != rec.content_hash: drift += {art_path, "output-modified-out-of-band"}
     # b) input drift
     for ih in rec.input_hashes:
        cur = exists(ih.path) ? sha256(ih.path) : "MISSING"
        if cur != ih.sha256:                  drift += {art_path, "input-changed", ih.path}
     # c) definition drift
     if recompute_def_hash(node_of(rec.producing_node)) != rec.def_hash:
                                              drift += {art_path, "def-changed"}
  return drift   # [] == clean. Each entry names the dirty artifact + reason.

================================================================
E) EVOLVE — minimal re-run set (transitive closure over edges)
================================================================
evolve(harness_root):
  drift = phase0_drift(harness_root)
  dirty_nodes = { producing_node(d.art_path) for d in drift if reason in
                  {input-changed, def-changed, graph-changed, output-missing} }
                  # NOTE: "output-modified-out-of-band" => warn only, do NOT auto-rerun (user may have hand-edited);
                  #       surface and require --force.
  # transitive downstream closure over graph.edges (edges = ordering, NOT TaskCreate depends_on)
  rerun = dirty_nodes
  changed = true
  while changed:
     changed = false
     for e in graph.edges:
        if e.from in rerun and e.to not in rerun: rerun.add(e.to); changed = true
  clean = all_nodes - rerun
  # emit a SCOPED workflow.js: clean nodes are replaced by `loadCached(<output path>)`
  # (read the artifact straight off disk); only `rerun` nodes emit live agent() calls.
  return { rerun: topo_order(rerun, graph.edges), reuse: clean }

This is the cross-run analogue of Workflow's agent()-prefix cache (constraint #6 gives per-run caching only; evolve provides the persistent layer the NEXT run reads — constraint #5).

================================================================
F) PreToolUse write-lock hook  (.claude/hooks/write_lock.sh)
   Wired in settings.json: hooks.PreToolUse[matcher: "Write|Edit|MultiEdit|NotebookEdit"]
================================================================
#!/usr/bin/env bash
# stdin = PreToolUse event JSON. Decide allow/deny for THIS single write by path.
# Feasible because the hook fires at the tool-call boundary and sees tool_input.file_path
# (constraint #3: path gating is exactly what a PreToolUse hook CAN do deterministically).
set -euo pipefail
LOCK="${HARNESS_ROOT:?}/harness.lock"
ev=$(cat)
fp=$(jq -r '.tool_input.file_path // .tool_input.path // empty' <<<"$ev")
# Owning node identity comes from env stamped by workflow.js per agent() call:
me="${HARNESS_NODE_ID:-}"        # see G; "" for the leader/un-scoped calls
[ -z "$fp" ] && exit 0
fp=$(python3 -c 'import os,sys;print(os.path.realpath(sys.argv[1]))' "$fp")
# find the owning record whose normalized path is a prefix (dir) or exact (file) of fp
owner=$(jq -r --arg fp "$fp" --arg root "$(dirname "$LOCK")" '
  .ownership[] as $o
  | ($root + "/" + ($o.path|sub("/$";""))) as $owned
  | select( ($o.path|test("/$")) and (($fp|startswith($owned+"/")) or $fp==$owned)
            or ((($o.path|test("/$"))|not) and $fp==$owned) )
  | .owner_node' "$LOCK" | head -1)
pol_unowned=$(jq -r '.policy.unowned_path' "$LOCK")
pol_viol=$(jq -r '.policy.on_violation' "$LOCK")
if [ -z "$owner" ]; then
  [ "$pol_unowned" = "deny" ] && { jq -n '{decision:"block",reason:"write outside any owned path"}'; exit 0; }
  exit 0
fi
if [ -n "$me" ] && [ "$owner" != "$me" ]; then
  if [ "$pol_viol" = "deny" ]; then
    jq -n --arg o "$owner" --arg m "$me" --arg p "$fp" \
      '{decision:"block",reason:("write-lock: "+$p+" owned by "+$o+", caller is "+$m)}'
    exit 0
  fi
fi
exit 0   # allow

================================================================
G) How the owner identity reaches the hook (the one integration seam)
================================================================
A PreToolUse hook only knows env + event JSON; it cannot read "which subagent am I."
workflow.js stamps the owner before each node's agent() call by prefixing the prompt
with a fenced directive AND relying on the runner to export HARNESS_NODE_ID for the
spawned session. Concrete, no-magic version for M0:
  - workflow.js writes the owner into the agent prompt header:  "[HARNESS_NODE_ID=gather]"
  - the SessionStart hook (.claude/hooks/stamp_node.sh) greps the latest prompt for that
    token and writes it to $HARNESS_ROOT/.run/<session_id>.node ; write_lock.sh reads it.
  - If neither env nor stamp file resolves (leader turn), me="" => path-ownership still
    enforced via unowned_path policy, but cross-owner blocking is skipped (fail-open for leader).
LIMIT (state explicitly): there is no API to bind a hook to a specific teammate identity in
team mode (constraint #1/#3). In Mode A (workflow) sub-agents are spawned by the in-session
runner, so the prompt-stamp seam is reliable; in Mode B (team) the lock degrades to
path-ownership + unowned_path policy only (no cross-owner attribution). Document as Mode B caveat.

## DEEP-RESEARCH INSTANCE
CONCRETE deep-research harness (topology=pipeline; gather -> verify -> synthesize), built to the spine field names.

graph.json (relevant slice) has nodes: gather(researcher/haiku), verify(verifier/sonnet, majority-vote n=3), synthesize(writer/opus); edges gather->verify, verify->synthesize.

----- harness.lock -----
{
  "schema_version": "0.1",
  "harness_name": "deep-research",
  "workspace_root": "_workspace/",
  "ownership": [
    { "path": "_workspace/01_gather/",    "owner_node": "gather",     "owner_agent": "researcher" },
    { "path": "_workspace/02_verify/",    "owner_node": "verify",     "owner_agent": "verifier"   },
    { "path": "_workspace/03_synth/",     "owner_node": "synthesize", "owner_agent": "writer"     }
  ],
  "policy": { "on_violation": "deny", "unowned_path": "allow" }
}
Validator note: gather.write_paths=["_workspace/01_gather/"], verify=["_workspace/02_verify/"],
synthesize=["_workspace/03_synth/"]. No prefix of one is a prefix of another -> no overlap -> PASS.
(If verify had also declared "_workspace/01_gather/" the validator emits:
 ERROR overlap: "_workspace/01_gather/" owned by both gather and verify.)

----- MANIFEST.json (after a clean cold run) -----
{
  "schema_version": "0.1",
  "harness_name": "deep-research",
  "harness_version": "0.1.0",
  "manifest_algo": "sha256",
  "graph_hash": "9f2c...e10",
  "generated_at": "2026-05-29T11:02:14Z",
  "artifacts": {
    "_workspace/01_gather/findings.json": {
      "producing_node": "gather", "producing_agent": "researcher",
      "model": "haiku", "decision_mechanism": "single",
      "input_hashes": [
        { "path": "_workspace/00_input/query.md", "sha256": "aa11...001" }
      ],
      "def_hash": "d1f0...aaa",          // includes sha256(.claude/agents/researcher.md)=R0
      "content_hash": "c0ff...e01",
      "harness_version": "0.1.0", "generated_at": "2026-05-29T11:00:51Z"
    },
    "_workspace/02_verify/verified.json": {
      "producing_node": "verify", "producing_agent": "verifier",
      "model": "sonnet", "decision_mechanism": "majority-vote",
      "input_hashes": [
        { "path": "_workspace/01_gather/findings.json", "sha256": "c0ff...e01" }  // == gather's content_hash
      ],
      "def_hash": "e22b...bbb",
      "content_hash": "ba5e...e02",
      "harness_version": "0.1.0", "generated_at": "2026-05-29T11:01:40Z"
    },
    "_workspace/03_synth/report.md": {
      "producing_node": "synthesize", "producing_agent": "writer",
      "model": "opus", "decision_mechanism": "single",
      "input_hashes": [
        { "path": "_workspace/02_verify/verified.json", "sha256": "ba5e...e02" }  // == verify's content_hash
      ],
      "def_hash": "f33c...ccc",
      "content_hash": "dec0...e03",
      "harness_version": "0.1.0", "generated_at": "2026-05-29T11:02:12Z"
    }
  }
}
The input_hash chaining (gather.content_hash == verify.input_hashes[0].sha256, etc.) is what
makes downstream invalidation fall out automatically: if gather re-runs and produces a new
content_hash, verify's recorded input_hash no longer matches -> verify is dirty -> synthesize dirty.

================================================================
WORKED EXAMPLE: "researcher agent edited -> evolve re-runs only gather + downstream"
================================================================
Action: user edits .claude/agents/researcher.md (tightens the search prompt). Nothing else changes.

phase0_drift:
  graph_hash unchanged -> no global invalidation.
  _workspace/01_gather/findings.json:
     output exists, content_hash matches (file untouched on disk) -> no output drift
     input query.md sha256 unchanged -> no input drift
     recompute def_hash(gather): sha256(researcher.md) is now R1 != R0
        -> def_hash d1f0... -> d9NEW...  MISMATCH  => drift {gather, "def-changed"}
  _workspace/02_verify/verified.json:
     def_hash(verify) unchanged; input findings.json on disk still hashes to c0ff...e01
        (gather hasn't re-run YET) -> at drift time verify looks CLEAN.
  _workspace/03_synth/report.md: also clean at drift time.

evolve:
  dirty_nodes = { gather }  (reason def-changed)
  transitive closure over edges gather->verify->synthesize:
     gather in rerun => add verify; verify in rerun => add synthesize.
  rerun = [gather, verify, synthesize]   (topo order)
  reuse = []   (nothing upstream of gather)
  Emitted scoped workflow.js: all three nodes emit live agent() calls;
  if instead only synthesize.agent had been edited, rerun would be [synthesize] and
  gather+verify would be loadCached('_workspace/01_gather/findings.json' / '..verified.json').

Counter-case proving minimality: user edits ONLY .claude/agents/writer.md (synthesize):
  def_hash(synthesize) mismatches; gather & verify def_hash + inputs unchanged.
  dirty_nodes={synthesize}; no outgoing edges from synthesize -> rerun=[synthesize],
  reuse=[gather,verify]. gather/verify outputs are read off disk via loadCached; the
  600k token budget is only spent on the opus synthesize node. This is the payoff of the
  ledger: evolve never re-pays for unchanged upstream work.

Post-run: after rerun completes, the manifest entries for gather/verify/synthesize are
rewritten with new content_hash + def_hash + post-run generated_at; graph_hash refreshed.

## READS
['graph.json (nodes[].id, .agent, .model, .decision_mechanism, .mechanism_params, .inputs, .outputs, .write_paths, .output_schema, .retries, .on_exhaust, .max_rounds; edges[].from/.to; harness_name; harness_version)', '.claude/agents/<agent>.md (hashed into def_hash)', 'schemas/*.json referenced by node.output_schema (hashed into def_hash)', '_workspace/** produced artifacts (content_hash recompute) and declared node.inputs (input_hash recompute)', 'settings.json (PreToolUse hook registration)']

## WRITES
['MANIFEST.json (written post-run by workflow.js wrapper / build step; rewritten per evolve for re-run nodes only)', 'harness.lock (written by the build/validate step purely from node.write_paths; static between graph edits)', '.claude/hooks/write_lock.sh (the PreToolUse consumer)', '.claude/hooks/stamp_node.sh (SessionStart owner-id stamp)', '$HARNESS_ROOT/.run/<session_id>.node (transient owner-id resolution file)']

## EDGE CASES
- Cold start: MANIFEST.json absent -> all nodes dirty, full pipeline runs (no spurious cache).
- graph.json edited (topology/budget/any field) -> graph_hash mismatch -> ALL_DIRTY, ignore per-node cache (prevents stale reuse after structural change).
- Out-of-band artifact edit (user hand-edits _workspace/03_synth/report.md): content_hash mismatch detected but reason=output-modified-out-of-band => WARN only, NOT auto-rerun; require --force to overwrite user edits.
- Missing declared input at drift time -> sha256='MISSING', counts as input-changed -> node dirty (don't crash).
- Two nodes declaring the same write_path (or one a prefix of the other) -> harness.lock validator ERROR before any run; build blocked.
- write_path not under workspace_root -> validator ERROR (keeps lock enforceable and prevents escaping the sandbox).
- PreToolUse hook cannot resolve owner identity (leader turn / Mode B team) -> fail-open on cross-owner check but still enforce unowned_path policy; documented Mode B degradation (constraint #1/#3).
- Hashing must be canonical: JSON inputs/defs hashed via `jq -S -c` BEFORE sha256, else key-reorder produces false drift (verified order-stable).
- No wall-clock inside workflow.js: generated_at is stamped by the post-run wrapper, never read into any hash, so resume/replay stays deterministic (Workflow API forbids current-time/RNG).
- decision_mechanism=majority-vote/debate: the node still has ONE outputs[] artifact (the reduced result); voters are internal and not separately manifested in M0 (keeps the ledger 1:1 with node.outputs).
- Concurrent writes within one node (parallel voters writing scratch under the node's own owned prefix) are allowed because they share owner_node; no false lock conflict.

## FEASIBILITY
Maps cleanly to real primitives. (1) Hashing + diff is plain shell (`shasum -a 256`, `jq -S -c` — both verified present in this env, Node 25 / Python 3.14 available as fallbacks); no LLM, so drift/evolve are fully deterministic and run BEFORE any agent() call. (2) The PreToolUse write-lock hook uses exactly the one thing a hook can do per constraint #3: inspect a single tool-call's file_path at the boundary and emit {decision:'block'}; it does NOT attempt token aggregation (infeasible) or time-based watchdog (infeasible, constraint #4). (3) evolve's cache layer is the explicit, persistent complement to Workflow's per-run agent()-prefix cache (constraint #6) — Workflow only caches within a run/resume (constraint #5), so MANIFEST is the cross-invocation memory the next run re-reads; the emitted scoped workflow.js feeds clean nodes via loadCached(diskpath) and only emits live agent() for the rerun set, so the budget.total guard is spent only on changed work. (4) graph.edges are honored as ordering for the transitive closure ONLY — never treated as TaskCreate depends_on (constraint #2). (5) Owner-identity seam: reliable in Mode A (in-session runner stamps HARNESS_NODE_ID via prompt token + SessionStart hook); in Mode B (team) it degrades to path-ownership + unowned_path policy because no hook-to-teammate identity binding exists (constraint #1). All limits stated inline rather than hidden.

## OPEN QUESTIONS
