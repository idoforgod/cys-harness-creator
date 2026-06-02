// CYS Harness Creator M0 — model-tier policy (single source of truth for role->tier).
// Pure functions of graph.json; no clock/RNG, resume-safe. Consumed by:
//   - the harness-creator meta-skill (fills node.model via resolveModel)
//   - emit_workflow.py (reads node.model -> agent({model}))   [JS values mirror these]
//   - validate_harness.py (V1/V2/V3 tier rules; reads the same role classes)
// Tunable weights/levels live in constants.json (the SoT); structural role maps live here.

const fs = require("fs");
const path = require("path");

function loadConstants() {
  const defaults = {
    TIER_COST_WEIGHT: { haiku: 1, sonnet: 3, opus: 5 },
    MODEL_RATIONALE_MISSING: "warn", // M0: warn (reduce first-dogfood friction); model missing is still error
  };
  try {
    const raw = JSON.parse(fs.readFileSync(path.join(__dirname, "constants.json"), "utf8"));
    return Object.assign({}, defaults, {
      TIER_COST_WEIGHT: raw.TIER_COST_WEIGHT || defaults.TIER_COST_WEIGHT,
      MODEL_RATIONALE_MISSING: raw.MODEL_RATIONALE_MISSING || defaults.MODEL_RATIONALE_MISSING,
    });
  } catch (e) {
    return defaults; // resume-safe fallback
  }
}
const C = loadConstants();

// role-class POLICY — single source of truth shared with validate_harness.py (role-class-policy.json).
// This file no longer hand-copies the regex/dict tables; both consumers load the SAME JSON so they can
// never drift. resume-safe fallback keeps the prior literals if the file is missing.
function loadRoleClassPolicy() {
  const fallback = {
    tier_by_role_class: {
      gather: "haiku", extract: "haiku", format: "haiku", "qa-scan": "haiku",
      voter: "sonnet", debater: "sonnet", reviser: "sonnet",
      synthesis: "opus", judge: "opus", critic: "opus", architecture: "opus",
    },
    pure_retrieval_role_classes: ["gather", "extract", "format", "qa-scan"],
    base_role_class_patterns: [
      ["gather|fetch|\\bsearch|retriev|collect|scan-src", "gather"],
      ["extract|parse|pull", "extract"],
      ["format|render|serialize|writer|publish", "format"],
      ["qa|lint|check|verify|valid", "qa-scan"],
      ["synth|aggregate|merge|conclude", "synthesis"],
      ["judge|arbiter", "judge"], ["critic|review", "critic"],
      ["architect|plan|design", "architecture"],
    ],
    base_role_class_default: "synthesis",
    mechanism_role_class: {
      "majority-vote": "voter", "debate-with-judge": "debater", "reflect-then-revise": "reviser",
    },
  };
  try {
    return JSON.parse(fs.readFileSync(path.join(__dirname, "role-class-policy.json"), "utf8"));
  } catch (e) {
    return fallback; // resume-safe
  }
}
const P = loadRoleClassPolicy();

const VALID_TIERS = ["haiku", "sonnet", "opus"];

// Tier per ROLE-CLASS. role-class is derived from a node (not a free string).
const TIER_BY_ROLE_CLASS = P.tier_by_role_class;
const PURE_RETRIEVAL_ROLE_CLASSES = P.pure_retrieval_role_classes;
const _BASE_PATTERNS = P.base_role_class_patterns.map(([rx, rc]) => [new RegExp(rx), rc]);

// keyword-match node.id+agent to a role-class; unmapped -> default (fail-safe-expensive:
// never silently cheap-and-wrong; the validator then forces an explicit model:).
function baseRoleClass(id, agent) {
  const s = (String(id) + " " + String(agent)).toLowerCase();
  for (const [rx, rc] of _BASE_PATTERNS) {
    if (rx.test(s)) return rc;
  }
  return P.base_role_class_default;
}

// decision_mechanism overrides the base role for the spawned sub-roles.
// (judge/critic come from mechanism_params and are tiered separately by the emitter.)
function roleClassOf(node) {
  const m = P.mechanism_role_class[node.decision_mechanism];
  return m !== undefined ? m : baseRoleClass(node.id, node.agent);
}

// FILL: applied at generation time to any node with empty/invalid model. explicit wins.
function resolveModel(node) {
  if (node.model && VALID_TIERS.includes(node.model)) return node.model;
  return TIER_BY_ROLE_CLASS[roleClassOf(node)];
}

// ---- validator rules owned by this component (returned to validate_harness via a sidecar) ----
// V1 missing/invalid model (error) + missing model_rationale (level from constants: M0=warn).
function v1_modelFields(node, agentFile) {
  const errs = [];
  if (!node.model || !VALID_TIERS.includes(node.model))
    errs.push({ code: "TIER_MISSING", level: "error",
      msg: `node "${node.id}".model empty/invalid; resolveModel default="${TIER_BY_ROLE_CLASS[roleClassOf(node)]}" — set explicitly.` });
  if (agentFile && (!agentFile.model || !VALID_TIERS.includes(agentFile.model)))
    errs.push({ code: "AGENT_TIER_MISSING", level: "error", msg: `agent "${node.agent}" frontmatter missing/invalid model:` });
  if (agentFile && !agentFile.model_rationale)
    errs.push({ code: "RATIONALE_MISSING", level: C.MODEL_RATIONALE_MISSING, msg: `agent "${node.agent}" missing model_rationale:` });
  return errs;
}
// V2 opus on a pure-retrieval role (warn if node.tier_override_reason set, else error).
function v2_opusOnRetrieval(node) {
  if (node.model === "opus" && PURE_RETRIEVAL_ROLE_CLASSES.includes(roleClassOf(node))) {
    const level = node.tier_override_reason ? "warn" : "error";
    return [{ code: "TIER_OVERSPEND", level,
      msg: `node "${node.id}" role-class "${roleClassOf(node)}" (pure retrieval) is opus. Downgrade to haiku or set tier_override_reason.` }];
  }
  return [];
}
// V3 node.model must equal agentFile.model.
function v3_consistency(node, agentFile) {
  if (agentFile && agentFile.model && node.model && node.model !== agentFile.model)
    return [{ code: "TIER_MISMATCH", level: "error",
      msg: `node "${node.id}".model="${node.model}" != agent "${node.agent}" frontmatter model="${agentFile.model}".` }];
  return [];
}

module.exports = {
  VALID_TIERS, TIER_BY_ROLE_CLASS, PURE_RETRIEVAL_ROLE_CLASSES, TIER_COST_WEIGHT: C.TIER_COST_WEIGHT,
  baseRoleClass, roleClassOf, resolveModel, v1_modelFields, v2_opusOnRetrieval, v3_consistency,
};

// CLI self-check: `node model-tier-policy.js <graph.json>` prints resolved tiers + V2 flags.
if (require.main === module) {
  const gp = process.argv[2];
  if (!gp) { console.error("usage: node model-tier-policy.js <graph.json>"); process.exit(2); }
  const g = JSON.parse(fs.readFileSync(gp, "utf8"));
  for (const n of g.nodes) {
    const rc = roleClassOf(n), rm = resolveModel(n), v2 = v2_opusOnRetrieval(n);
    console.log(`${n.id.padEnd(12)} agent=${String(n.agent).padEnd(13)} role=${rc.padEnd(12)} model=${rm}` +
      (v2.length ? `  [${v2[0].level.toUpperCase()}: ${v2[0].code}]` : ""));
  }
}
