# cys-harness-creator — STRATEGY + DESIGN (Integrated)

> **DESIGN-ONLY deliverable** (locked decision 1). No code is written this pass. This document
> assembles the five design components (D1 integrated workflow, D2 all-primitive composition,
> D3 memory+QA DNA, D4 eval+parity, D5 strengths+backlog) into one coherent, non-redundant
> strategy + design. Every change below is implementable against files that were read first-hand.
> All paths absolute. Conforms to all 7 locked decisions and requirements R1–R4.

## 0. Canonical naming (read first — resolves cross-component aliasing)

The five components independently coined overlapping names for the same concept. This document uses
ONE canonical name per concept; the aliases are listed once here and never used again below.

| Concept | **CANONICAL** name used in this doc | Aliases seen in components (do not use) |
|---|---|---|
| Per-node author-vs-inline decision field | `node.skill_authoring` `{mode, reason, shared_by?}` | `domain_skill` (D2), `authoring_decision` (D4) |
| Validate: team-mode emit actually contains team primitives | `TEAM_EMIT_PRESENT` | `PRIMITIVE_VERB_PRESENT` (D5) |
| Validate: cross-run memory store is first-class | `MEMORY_FIRST_CLASS` | `RLM_STORE_PRESENT` / `MEMORY_STORE_INIT` (D3/D5) |
| Validate: L0–L2 gates wired as hooks | `QA_HOOKS_WIRED` (umbrella) | `L0_ANTISKIP_WIRED`/`L1_VERIFICATION_WIRED`/`PACS_GATE_WIRED`/`QA_LAYER_WIRED` (D5, kept as sub-codes) |
| Validate: workflow.js retired from product | `WORKFLOW_RETIRED` | (D5 only — adopted) |
| Cross-run domain memory directory | `.harness/memory/` | `domain-memory/` (D1) |
| PostToolUse spawn-count hook | `spawn_counter.py` | (D2/D3/D5 agree) |
| SessionStart SOT-instantiation hook | `sot_init.py` | `sot_state_init.py`/`init_sot.py` (D3/D1) |
| PostToolUse L0–L2 runner hook | `qa_gate_runner.py` | (D3 only — adopted) |

**Ground-truth corrections applied** (verified by file read this session — these override any
component sentence that disagrees):

- `validate_harness.py:253` defaults `execution_mode` to `"workflow"`. The retired mode is the
  validator's de-facto canonical. (D5 correct; must flip.)
- **CORRECTED (was wrong in an earlier draft):** `gate_or_block.py` + `budget_block.py` live in
  `templates/hooks/` and **ARE transplanted into every child** by `inherit_genome._CYS_HOOKS` (line 45,
  copied to the child's `.claude/hooks/scripts/` at lines 160–163); `_merge_settings` (lines 118–121)
  **ALREADY wires `budget_block.py`** as `PreToolUse(Agent|Task|TeamCreate)`. Verified on
  `_workspace/dogfood`: both scripts present in the child, `budget_block` wired=True. The genome-DIR not
  containing them is irrelevant — inherit's *source* is `templates/`, and the child gets them. So the
  REAL gaps are NOT "transplant gate/budget" (a no-op): (a) `gate_or_block.py` reaches the child but
  **nothing INVOKES it on `PostToolUse`** → L0–L2 stay advisory; (b) `budget_block` is wired but
  `budget.spawns_used` is **never incremented** (no counter hook) and `state.yaml` is **never
  instantiated** (no init hook) → the ceiling can't fire. Fix = THREE NEW hooks
  (`qa_gate_runner.py`, `spawn_counter.py`, `sot_init.py`) + wiring. The genome still ships the
  *validators* (`validate_{pacs,review,verification,domain_knowledge}.py`, `context_guard.py`,
  `query_workflow.py`).
- `emit_orchestrator.py:113` is literally `sch = ("schemas/%s.json" % nid)` — derives schema path from
  node **id**, not `output_schema`. The bug is real.
- `graph.schema.json`: `topology` enum has only 3 values (`pipeline|dispatch|producer-reviewer`);
  `execution_mode` enum still includes `"workflow"`.
- `warrant.py` cost band is already team-aware (`TEAM_COORD_TOKENS × len(nodes)`, line 152).

---

## 1. EXECUTIVE THESIS — what we are building and how it coheres

**cys-harness-creator is a META-SKILL (a factory).** It turns a one-sentence domain request into a
**produced harness**: a live Claude Code session that does the domain work. There are two layers, and
keeping them distinct is the load-bearing idea of the whole product:

- **Layer 1 — FACTORY (build time).** A Claude Code skill (`harness-creator`) plus Python
  emitters/validators (`warrant.py`, `emit_orchestrator.py`, `validate_harness.py`,
  `inherit_genome.py`, new `audit_harness.py`, new `emit_domain_skill.py`). The factory may be Python;
  it runs once, at creation time, to *author* a harness.
- **Layer 2 — PRODUCED HARNESS (run time).** The emitted artifacts (orchestrator skill +
  `.claude/agents/` + `.claude/skills/` + `.claude/settings.json` hooks + `.harness/` contract/state).
  **The ABSOLUTE RULE applies to Layer 2 only: 100% of produced-harness EXECUTION is delegated to
  Claude Code primitives** — Agent (sub-agents), TeamCreate / SendMessage / TaskCreate (Agent Teams).
  No non-primitive runtime ever spawns or coordinates the work.

**The ABSOLUTE RULE, defined precisely (locked decision A1).** "100% primitive" governs the *domain
WORK* — all reasoning, judgment, and generation runs on Agent / TeamCreate / SendMessage / TaskCreate.
It does NOT forbid Python in the produced harness: deterministic Python (lifecycle hooks, validators,
memory save/restore, counters, parsers) is the harness's **non-execution guardrail layer** — it GATES,
SAVES, and REMEMBERS *around* the primitives but never performs domain reasoning. The boundary is
**deterministic mechanics (Python allowed) vs judgment/generation (primitives only)** — exactly AWF's
P1 principle ("code-computable work is pre-processed; the AI focuses on judgment"). This is the
*enabling* reconciliation, not a loophole: R4 (Context Preservation, the 4-layer QA stack, RLM memory)
are inherently deterministic and can only FIRE as Python guardrails — so this definition is precisely
what makes the genome actually fire instead of lie dormant, and it is exactly where CYS exceeds
idoforgod's pure-prose (unenforced) gates. **Litmus test for any emitted Python:** if removing it could
change a domain ANSWER, it is illegal (must be a primitive); if it only blocks/saves/measures/parses, it
is a legal guardrail.

Five strategic commitments cohere into one design:

1. **The ABSOLUTE RULE (100% primitive delegation) is the runtime substrate that lets everything
   else FIRE.** Under the retired Mode-A `workflow.js`, the Agent tool downgraded all agents to a
   generic runtime, so tier policy, custom `model:`/`tools:` frontmatter, and the lifecycle hooks were
   advisory. Under the primitive substrate, the Agent tool **honors `model:` and `tools:` frontmatter**
   and the harness's own `settings.json` hooks fire. So choosing primitives is not a constraint we pay
   for — it is the *enabling condition* for tier policy, least-privilege tools, and all inherited DNA to
   become runtime-binding rather than narrated. **`workflow.js` is RETIRED from the product** (locked 3):
   no child ever gets it; `emit_workflow.py` + the generic Workflow tool survive only as
   **factory-internal measurement tooling** (h2h), never emitted to a child.

2. **The benchmark is FEATURE PARITY with idoforgod/harness, not performance superiority** (locked 4).
   Parity = *capability* parity. But where idoforgod's FORM *is* the Claude-native mechanism — above
   all, generating per-node domain skills under `.claude/skills/` and real Agent Teams — we adopt that
   form wholesale. The eval bar is concrete: **all 8 idoforgod README use cases must pass** (R2), each
   exercising a specific topology/primitive mix. Winning an h2h is explicitly NOT required; honesty
   about losing IS (the `MEASUREMENT_DRIFT` honesty gate, the institutional memory of the fictional
   "+37.5pp" lesson, is preserved and extended).

3. **AWF good-harness DNA is transplanted for FUNCTIONAL COMPLETENESS** (locked 6): every functional
   DNA mechanism must actually FIRE in produced harnesses, not lie dormant. The four-layer QA stack
   (L0 Anti-Skip → L1 Verification → L1.5 pACS → L2 Adversarial Review), the budget interlock, and the
   SOT are wired as `settings.json` hooks — converting "fire by orchestrator prose" into deterministic
   exit-2 interlocks. **Exception:** prompt-runner (a `claude -p` subprocess supervisor = a
   non-primitive parallel runtime) is EXCLUDED — vendored-but-inert, never wired into child execution;
   only its reusable PROMPT assets are harvested into sub-agent bodies.

4. **Long-term memory is OPTION B, implemented via the RLM mechanism** (locked 7, R4). Every produced
   harness gets (a) AWF's Context Preservation System made FIRST-CLASS + machine-verified (Tier I:
   survives token-overflow / `/clear` / compaction within a run), AND (b) HARNESS-LEVEL cross-run
   domain memory (Tier II: remembers prior outputs, sources, decisions, domain facts across repeated
   RUNS, and feeds the evolution loop). Both tiers obey the **RLM principle**: memory is an EXTERNAL
   STORE queried PROGRAMMATICALLY (Grep/Read/code over the store), with recursive sub-agent
   decomposition over snippets, **never bulk-loaded into context** — beating compaction (no forgetting
   of early detail) and beating the context window (scales orders of magnitude past it).

5. **All CYS verified strengths are preserved as a strict superset over idoforgod** (locked 8): the
   machine-checked graph.json contract (draft 2020-12), the ~20-code static build gate, role→tier
   model policy with the JS↔Py mirror-drift guard, the team-aware warrant cost band + approval gate,
   genome inheritance with functional load-verify, and the measurement infra (blind-grader lift gate,
   h2h aggregate, MEASUREMENT_DRIFT honesty gate). Adopting idoforgod's FORM does not dilute the
   contract: every emitted artifact remains a **projection of graph.json** that `validate_harness.py`
   can re-derive, so prose can never silently drift from the contract.

**How the pieces lock together in one sentence:** the **integrated workflow** (§2) authors a
machine-checked `graph.json` contract, which the emitter **projects** into an **all-primitive
composition** (§3) whose runtime is governed by **mandatory DNA hooks** (§4 — QA + budget + SOT +
two-tier RLM memory), proven by the **8-use-case parity eval** (§5), built on **preserved CYS
strengths** (§6), and delivered by a **sequenced backlog with new validate codes and a risk register**
(§7).

---

## 2. THE INTEGRATED WORKFLOW (the new SKILL.md + references map) — R1

### 2.1 Frame: AWF 3-stage ⊃ idoforgod 8 phases ⊃ CYS machine-check gates

The BIG FRAME is AWF's **Research → Planning → Implementation**, plus a named **post-Implementation
Evolution loop** (AWF treats Impl as final; idoforgod Phase 7 + CYS h2h/measurement need a home).
idoforgod's 8 phases nest inside the appropriate stage. CYS machine-gates interleave as the
*enforcement* layer. **The single human review/approval point lives at the end of Planning** (AWF's
mandatory human-intervention point fused with CYS's `approval_required` cost gate).

Notation: `[ido Pn]` = idoforgod phase; `[CYS]` = CYS machine-check gate; `[AWF]` = AWF DNA mechanism.

#### PRE-STAGE — Warrant Gate (CYS Phase −1) — *gating, before Research*
- **W1** `[CYS]` Extract 5 predicates `{distinct_expertise_domains, has_dependent_or_parallel_stages,
  will_be_rerun, output_objective, noisy}` → `python3 warrant.py --predicates`.
- **W2** Branch: `answer-directly` → answer, STOP. `single-agent` → one agent, STOP.
  `build-harness(topology, decision_mechanism, n_agents)` → enter Research.
- *Why before Research:* warrant decides whether a harness should exist at all. idoforgod always
  builds; this is a CYS superset kept verbatim.

#### STAGE 1 — RESEARCH (gather + analyze; no authoring, no human gate)
Maps **ido P0 (Status Audit)** + **ido P1 (Domain Analysis)** + the *analysis half* of **ido P2 (topology selection)**.
- **R1. Status Audit `[ido P0]`** — new factory tool `audit_harness.py <TARGET>` (build-time Python,
  Layer 1 — permitted). Inventories three sources: (a) `<TARGET>/.harness/graph.json` →
  `{node.agent, write_paths, output_schema, skill_authoring}`; (b) on-disk `.claude/agents/*.md` and
  `.claude/skills/*/SKILL.md`; (c) the `CLAUDE.md` harness-pointer change-history table. Computes three
  set-diffs (`agents_on_disk △ agents_in_graph`, `skills_on_disk △ skills_implied_by_skill_authoring`,
  `history △ files_present`) → emits `audit-report.json {branch ∈ {new,extend,maintain}, drift:[...]}`.
  *CYS upgrade over ido:* ido P0 does this by prose; CYS makes drift a deterministic JSON artifact, so
  "drift" is a checkable fact. Unremediated drift surfaces as a `validate_harness.py` warning.
- **R2. Domain Decomposition `[ido P1]`** — decompose request into nodes
  `{id, role-name, inputs/outputs, write_paths}`; detect user proficiency; explore any existing
  codebase; cross-check decomposed nodes against R1's existing-agent inventory for overlap dedup
  (ido P3-0/P4-0 pulled forward into analysis).
- **R3. Topology + Mode Analysis `[ido P2 analysis]`** — per node-cluster pick among the **6 idoforgod
  topologies** (pipeline, fan-out/fan-in, expert-pool, producer-reviewer, supervisor,
  hierarchical-delegation) and the `execution_mode` (agent/team/hybrid). *Analysis only* — recorded,
  not yet written to graph.json. The 6→(3 schema `topology` enums after widening, see §3) mapping lives
  in `architecture-patterns.md`.
- **R4. Model-tier resolution `[CYS]`** — map each role-name → `model-tier-policy.js` role-class →
  `resolveModel()` → tier; enforce `n_agents ≤ MAX_FANOUT(5)`.
- **Output:** `audit-report.json` + a decomposition table (nodes, roles, tiers, chosen topology/mode
  per cluster, author-or-inline pre-decision per node). **No human gate yet.**

#### STAGE 2 — PLANNING (author the contract + the single human gate)
Finalizes **ido P2 (decision half)**; the *authoring* of `graph.json` + schemas happens here because
they ARE the plan.
- **P1. graph.json authoring `[CYS, single-writer]`** — **this skill is the only writer of graph.json.**
  Conforms to `graph.schema.json`. Per node: `id, agent, model, decision_mechanism, mechanism_params,
  inputs, outputs, write_paths, output_schema, retries, on_exhaust, max_rounds` + the new
  machine-checkable fields **`skill_authoring`** (§3.3, locked 5), **`stage_id`**, **`team_role`**.
  Top-level: `execution_mode`, widened `topology`, `budget`, plus new **`stages`**, **`team_block`**,
  **`hooks_manifest`**, **`memory_config`** (§3). `budget.total_tokens` = warrant estimate + headroom;
  `budget.approval_required = true`.
- **P2. output_schema authoring `[CYS]`** — each `node.output_schema` → `schemas/<name>.json`
  (draft 2020-12, bare-filename `$id`, `additionalProperties:false`); reflect-then-revise nodes also get
  `schemas/critique.json`. **Fixes `emit_orchestrator.py:113`** — schema path comes from the
  `output_schema` field, never derived from node id.
- **P3. Team-architecture finalization `[ido P2 decision]`** — lock topology + `execution_mode` + team
  membership/roles into the `stages`/`team_block` blocks; apply the 6→3 topology map and the
  team-vs-subagent-vs-hybrid decision tree (§3.1), recorded as graph metadata.
- **P4. Cost-band computation `[CYS]`** — `python3 warrant.py --graph <TARGET>/.harness/graph.json` →
  token/USD band, team-aware (multiplies by team fan-out; already implemented).
- **P5. ⛔ HUMAN REVIEW / APPROVAL POINT `[AWF + CYS — THE single gate]`** — present to the human:
  (a) the plan (topology, agents, modes, per-node `skill_authoring` decisions, drift remediation from
  R1); (b) the cost band. Human approves or revises. Nothing in Implementation runs before approval
  returns. Autopilot may auto-approve only if explicitly configured, never silently skipping the display.

#### STAGE 3 — IMPLEMENTATION (emit the real, firing harness)
Maps **ido P3 (agents)**, **P4 (skills)**, **P5 (orchestration)**, **P6 (validation/testing)**. Where
idoforgod's `.claude/agents/` + `.claude/skills/` FORM is adopted (locked 4) and every CYS gate + AWF
DNA mechanism is made to actually fire.
- **I1. Agent-definition generation `[ido P3]`** — per node → `.claude/agents/<agent>.md`: frontmatter
  `name/description/model/model_rationale/tools` (least-privilege) + body `{core role, work principles,
  I/O protocol with exact `_workspace` paths + emitted schema, error handling, team-comms protocol when
  team-mode}`. ido's "write the agent FILE even for builtins" rule is kept. **CYS difference vs ido:**
  model is **tier-resolved per role**, NOT hard-coded opus (ido P3 says all-opus; CYS keeps tier policy —
  a kept strength; `TIER_OVERSPEND` enforces it).
- **I2. Domain-skill generation `[ido P4]` (HYBRID, new emitter) `[CYS]`** — new `emit_domain_skill.py`.
  For each node where `skill_authoring.mode == "skill"`, author `.claude/skills/<skill_name>/SKILL.md`
  (+ its own `references/` if large). For `mode == "inline"`, the "how" is inlined into the agent body
  (I1). `validate_harness.py` enforces on-disk reality matches the field (`SKILL_AUTHORING_CONSISTENCY`).
  Adopts ido's `.claude/skills/` form as the Claude-native mechanism while making the author-vs-inline
  choice machine-checked (locked 5).
- **I3. Orchestration + emit `[ido P5]` `[CYS emit_orchestrator]`** —
  - `.claude/skills/<domain>-orchestrator/SKILL.md` (human view; phase-count must equal README →
    `DOC_DRIFT`).
  - `python3 emit_orchestrator.py <TARGET>` emits orchestrator SKILL + agent stamps + **auto-runs
    `inherit_genome.py`** (genome transplant). Branches per `execution_mode` (the real per-stage
    dispatch of §3.2): `agent` → sequential sub-spawn via **Agent** (`run_in_background` for parallel
    fan-out); `team` → **real team emit** (TeamCreate / TaskCreate(with deps) / SendMessage / TeamDelete
    from `team_role`/`team_block`); `hybrid` → per-stage mode tags with team↔sub handoff via
    `_workspace/` files.
  - **`workflow.js` / `emit_workflow.py` RETIRED from the product** (locked 3): no
    `execution_mode:'workflow'` branch is emitted to a child; the Workflow tool survives factory-internal
    only for h2h.
  - Data-passing (ido P5-1): team → message+task+file; sub → return+file; `_workspace/{phase}_{agent}_{artifact}`.
  - `.harness/harness.lock` (write_paths→node map) + `MANIFEST.json` (provenance) + `RUNTIME.json`
    (`canonical_runtime` matches `execution_mode`; `RUNTIME_DECLARED`).
  - **CLAUDE.md harness-pointer registration `[ido P5-4]`** — write the minimal pointer block (trigger
    rule + change-history table) into `<TARGET>/CLAUDE.md`. Substrate that Phase-7 evolution writes to.
- **I4. Genome transplant FIRES `[AWF DNA, CYS inherit_genome]`** — `inherit_genome.py` copies the 9
  inherited-DNA components into `<TARGET>/.claude/` and **WIRES them as hooks in the produced
  `settings.json`** (full detail in §4):
  - **Context Preservation `[AWF + R4 + locked 7]`** — already wired in genome settings
    (`Stop/PreCompact/SessionStart→context_guard.py`, `SessionEnd→save_context.py`,
    `PostToolUse→context_guard.py`); kept. Made FIRST-CLASS (§4.2).
  - **4-layer QA WIRED as hooks** — `qa_gate_runner.py` (new) on `PostToolUse(Agent|Task)` runs
    L0→L1→L1.5→L2 through `gate_or_block.py` as exit-2 interlocks (§4.3). *Requires transplanting
    `gate_or_block.py` + `budget_block.py` from `templates/hooks/` into the genome — they are NOT there
    today.*
  - **Budget interlock WIRED** — `budget_block.py` on `PreToolUse(Agent|Task|TeamCreate)` blocks at the
    ceiling; new `spawn_counter.py` on `PostToolUse` increments `spawns_used` **via hook, not prose**
    (fixes "stuck at 0").
  - **SOT instantiation FIRES** — new `sot_init.py` on `SessionStart` writes `.harness/state.yaml`
    (orchestrator single-writer) if absent.
  - **prompt-runner EXCLUDED `[locked 6]`** — vendored under `genome/prompt-runner/` but inert; only its
    reusable PROMPT assets are harvested into sub-agent bodies.
  - **RLM long-term memory FIRES `[R4 + locked 7]`** — external store (`context-snapshots/` Tier I +
    new `.harness/memory/` Tier II) queried programmatically via `query_workflow.py` (§4.1).
- **I5. validate_harness build gate `[CYS, ~20→~40 codes]`** — `python3 validate_harness.py <TARGET>` →
  error ⇒ generation halts & reports. Existing codes kept; new codes in §7.2.
- **I6. Validation & Testing `[ido P6]`** — structure check (I5), with-skill vs without-skill **lift**
  (`lift_gate.py` blind grader), **trigger near-miss** (8–10 should-trigger + 8–10 should-NOT per skill),
  **dry-run** (phase order logical, no dead data-links, every input matches a prior output). ido P6's 5
  sub-checks map onto CYS `lift_gate` + trigger-verification + dry-run.

#### STAGE 4 — EVOLUTION LOOP (post-Implementation; home for ido P7 + CYS measurement)
- **E1. git + ship `[CYS]`** — `git init && git add -A && git commit` (rollback substrate).
- **E2. Head-to-head measurement `[CYS]`** — `evals/<domain>.scorecard.json`: C2 (CYS-harness) vs C3
  (no-harness) blind h2h → `h2h_aggregate.py`; honesty gate `MEASUREMENT_DRIFT` blocks any "CYS-WINS"
  doc claim without a matching `evals/*.verdict.json`.
- **E3. Feedback routing `[ido P7-1/7-2]`** — after each RUN, route by type: result-quality → domain
  skill; agent-role → agent `.md`; workflow-order → orchestrator; team-comp → orchestrator+agents;
  trigger-miss → description. The routed edit re-enters at the matching Implementation sub-step
  (I1/I2/I3) and MUST re-pass `validate_harness.py` — evolution cannot regress the contract.
- **E4. CLAUDE.md change-history `[ido P7-3]`** — every edit appends `{date, change, target, reason}` to
  the table seeded at I3. Also read by `audit_harness.py` (history↔disk drift detection).
- **E5. Proactive triggers `[ido P7-4]` — machine-detected via RLM, not prose.** `query_workflow.py`
  (Grep/Read over `knowledge-index.jsonl`, never bulk-load) detects: same feedback type ≥2×; an agent
  failing repeatedly (group error-patterns by agent); user bypassing the orchestrator. On a hit, the
  harness proactively proposes the matching E3 edit. RLM doing double duty: cross-run memory AND
  evolution-trigger detection.
- **E6. Maintenance loop `[ido P7-5]`** — the `maintain` branch from R1: re-audit → present drift →
  apply one change at a time → re-run relevant validate/trigger checks → sync CLAUDE.md. Large changes
  (arch, ≥3 agents) additionally re-run `lift_gate` + dry-run.

### 2.2 Full ido-phase → stage coverage map

| ido phase | Lands in | CYS gate co-located |
|---|---|---|
| P0 Status Audit | Research R1 | (new) `audit_harness.py` |
| P1 Domain Analysis | Research R2 | model-tier R4 |
| P2 Team Architecture | Research R3 (analysis) + Planning P1/P3 (decision) | warrant topology suggestion |
| P3 Agent Definition | Implementation I1 | `TIER_MISMATCH`, `AGENT_FRONTMATTER` |
| P4 Skill Generation | Implementation I2 | `SKILL_AUTHORING_CONSISTENCY` (new) |
| P5 Integration/Orchestration | Implementation I3 | `emit_orchestrator` + `GRAPH_SKILL_CONSISTENCY` + `TEAM_EMIT_PRESENT` (new) |
| P6 Validation/Testing | Implementation I5/I6 | `validate_harness` (~40) + `lift_gate` |
| P7 Harness Evolution | Evolution E3–E6 | `h2h` + `MEASUREMENT_DRIFT` |
| — warrant (Phase −1 + cost band) | Pre-stage W + Planning P4/P5 | `warrant.py` (both invocations) |
| — graph.json authoring | Planning P1 | single-writer + `GRAPH_SCHEMA` |
| — genome transplant | Implementation I4 | `inherit_genome` + `GENOME_PRESENT`/`HOOK_REGISTERED` |
| — validate_harness | Implementation I5 | (the gate itself) |

### 2.3 The new SKILL.md outline (target ≈ 260–300 lines, < 500; current is 111)

Pushy description with follow-up keywords; progressive disclosure (body lean, detail in references).

```
---
name: harness-creator
description: "도메인 한 문장을 검증된·비용통제된·재개가능한 풀스택 Claude 프리미티브 하네스
  (orchestrator skill + .claude/agents + Sub-agents + Agent Teams + Hooks + .claude/skills + memory)로
  변환하는 메타스킬. '하네스 만들어줘/구성/설계', '에이전트 팀 설계', '이 도메인 자동화',
  '하네스 점검·감사·확장·진화·동기화' 시 사용. 후속: 재실행·수정·보완·부분재생성·
  이전결과개선·드리프트수정·유지보수 요청 시에도 반드시 이 스킬을 사용."
---
```
1. **# Harness Creator (CYS) — 메타스킬** — what-it-is + 4 core principles (primitive-delegation default;
   every rule machine-enforced; cost pre-approval + ceiling; produced harness = git repo with SOT).
2. **## 산출물 = 풀스택 프리미티브 합성** — 1-line list (orchestrator skill + agents + Sub-agents + Teams
   + Hooks + skills + memory) — establishes R3.
3. **## 호출 & 경로** — trigger phrases; `TOOLS_ROOT` (absolute) + `<TARGET>`; canonical command block;
   execution-handoff note (run child in a NEW `cd <TARGET> && claude` session so its hooks fire).
4. **## 워크플로우 — 4 스테이지 (Research→Planning→Implementation→Evolution)** — one-sentence frame.
5. **### PRE: Warrant 게이트 (Phase −1)** — 5-predicate branch.
6. **### STAGE 1 — RESEARCH** — R1 Status Audit (new/extend/maintain + drift), R2 Decomposition, R3
   Topology+Mode (6→3 pointer), R4 model-tier. → `architecture-patterns.md`.
7. **### STAGE 2 — PLANNING (+ 사람 승인 게이트)** — P1 graph.json (single-writer; new fields), P2 schemas,
   P3 team-arch finalize, P4 cost band, **P5 HUMAN APPROVAL** (bold callout). → `graph-and-orchestration.md`.
8. **### STAGE 3 — IMPLEMENTATION** — I1 agents, I2 domain-skill hybrid, I3 orchestrator+emit
   (agent/team/hybrid; workflow.js RETIRED note), I4 genome transplant FIRES (memory + L0–L2 + budget +
   SOT wired), I5 validate, I6 lift+trigger+dry-run. → `skill-and-agent-authoring.md`,
   `genome-and-runtime.md`, `testing-and-measurement.md`.
9. **### STAGE 4 — EVOLUTION 루프** — E1 git, E2 h2h, E3 routing, E4 change-history, E5 proactive triggers,
   E6 maintenance. → `evolution-and-memory.md`.
10. **## 실행 명령 (복붙용)** — literal bash (warrant×2, emit_orchestrator, validate_harness) — **no
    `emit_workflow`**.
11. **## 산출 체크리스트** — produced-harness checklist (graph schema-pass; agents w/ tier+rationale+
    least-priv tools; schemas; orchestrator+README phase-match; validate PASS; QA-hooks+budget+SOT+memory
    wired; cost approved; git init; **NO workflow.js**, NO global opus, NO absolute paths).
12. **## 도구 (cys-harness-creator/)** — 1-line each: warrant, model-tier-policy, graph.schema,
    emit_orchestrator, emit_domain_skill (new), inherit_genome, validate_harness, audit_harness (new),
    lift_gate, h2h_aggregate, query_workflow (RLM), constants, lib/toposort. Note: emit_workflow =
    factory-internal-only.
13. **## 참고 — references/** — the 8-file map (§2.4); lead line: "구현 현황은 `IMPLEMENTATION-STATUS.md`가
    모든 서술에 우선."

### 2.4 references/ file map (8 files; current 7 + idoforgod's 6 + AWF protocols, folded)

| # | Reference file | Covers | Adapts from |
|---|---|---|---|
| 1 | **IMPLEMENTATION-STATUS.md** | **Read first.** Real vs deferred vs retired (workflow.js retired; M-deferred list); overrides every aspirational sentence elsewhere. | CYS (extend) |
| 2 | **architecture-patterns.md** | Research R3 + Planning P3: 6 ido topologies ↔ widened `topology` enum + agent/team/hybrid `execution_mode` mapping; agent-separation 4-axis; team-vs-subagent-vs-hybrid decision tree; 8-use-case→topology assignment (folds old `examples.md`). | CYS + ido `agent-design-patterns.md` |
| 3 | **graph-and-orchestration.md** | Planning P1/P2 + Impl I3: graph.json template, new `skill_authoring`/`team_role`/`stages`/`team_block` spec, schema authoring, real-team emit, data-passing, on_exhaust, CLAUDE.md pointer template; `node.memory` read/write contract. | CYS + ido `orchestrator-template.md` + `team-examples.md` |
| 4 | **skill-and-agent-authoring.md** | Impl I1/I2: agent `.md` + team-comms section; hybrid author-or-inline rule; pushy-description + Why-not-ALWAYS + progressive disclosure; output_schema design; reuse-dedup. | CYS `skill-writing-guide.md` + ido `skill-writing-guide.md` |
| 5 | **genome-and-runtime.md** | Impl I4: the 9 inherited-DNA components + **how each is WIRED as a hook** (Context Preservation cycle; L0–L2 via gate_or_block; budget_block; spawn_counter; sot_init); prompt-runner EXCLUSION; RUNTIME.json; primitive-substrate enforcement. | NEW (AWF `AGENTS.md` distilled) |
| 6 | **evolution-and-memory.md** | Stage 4 + R4 memory: ido P7 routing table + change-history + proactive triggers + maintenance; RLM two-tier store (external, programmatic, recursive, cross-run feeding evolution). | NEW (ido P7 + RLM + AWF Knowledge Archive) |
| 7 | **testing-and-measurement.md** | Impl I6 + E2: validate-code catalogue, lift_gate, h2h + MEASUREMENT_DRIFT, trigger near-miss, dry-run; **8-use-case eval harness (R2)**. | CYS + ido `skill-testing-guide.md` |
| 8 | **qa-guide.md** | QA-agent integration: interface cross-comparison (not existence-check), incremental QA, 7 boundary bug patterns, verify-before-assert, finding triage; how QA maps to L1/L2 gate hooks. | CYS + ido `qa-agent-guide.md` |

Folds: CYS `examples.md` → into `architecture-patterns.md` (the 8 README use cases ARE the examples);
ido `team-examples.md` → into `graph-and-orchestration.md` + `architecture-patterns.md`.

---

## 3. PRODUCED-HARNESS ALL-PRIMITIVE COMPOSITION + graph.json contract extensions — R3, D2

### 3.1 Primitive-selection model (data-driven, encoded in graph.json)

Three inherited positions, reconciled into ONE deterministic, authoring-time selector:

| Source | Stated rule | What we keep |
|---|---|---|
| idoforgod | "Agent Teams = default; ask 'is inter-agent comms really unneeded?'" | DEFAULT BIAS toward team when ≥2 agents share a stage AND need cross-talk |
| AWF | fork/fresh/team_decision categorization; adversarial reviewer MUST be isolated read-only | QUALITY OVERRIDE: adversarial/independent-verification stages MUST be isolated sub-agents, never teammates |
| CYS warrant | every primitive choice must be cost-warranted + machine-checkable | The selection is a FIELD in graph.json, not a runtime guess; validate enforces it; warrant prices it |

A **stage** = a maximal set of nodes mutually concurrent under `edges` (same toposort rank) OR grouped
by `stage_id`. The selector runs per stage:

```
select_primitive(stage):
  members = nodes in stage
  if len(members) == 1:                  -> SUBAGENT          (single Agent() call)
  elif stage.requires_isolation:         -> SUBAGENT (fan)    # adversarial/independent verify: NO cross-talk
  elif stage.cross_talk:                 -> TEAM              # peers share/challenge mid-flight
  elif stage.dynamic_dispatch:           -> TEAM (supervisor) # runtime work allocation via shared task list
  else:                                  -> SUBAGENT (fan)    # parallel-independent, results returned to orchestrator
  # HYBRID is a HARNESS-level property: it emerges when stages resolve to different primitives.
```

The three booleans (`cross_talk`, `requires_isolation`, `dynamic_dispatch`) are the **machine-encoded
warrant** for each choice — the same "machine-checkable field" pattern locked decision 5 mandates for
domain skills, reused for primitive selection. Validate checks mutual exclusivity + topology
consistency. **The critical reconciliation:** idoforgod would make a webtoon producer-reviewer a team;
AWF forbids it (a teammate-reviewer who read the producer's chain-of-thought via SendMessage
rubber-stamps); CYS resolves by `requires_isolation:true` → isolated fresh read-only sub-agent.

**All-6 composition FLOOR (locked decision A2).** The per-stage selector above chooses *which* primitive
each stage uses; on top of it, **EVERY built harness must instantiate all six primitive types as a
floor**: orchestrator skill + agent definitions + Sub-agents (Agent) + Agent Teams (TeamCreate/
SendMessage/TaskCreate) + Hooks (settings.json) + Skills (`.claude/skills/`) — plus memory. Concretely a
built harness MUST contain **≥1 team stage** (so Agent Teams are exercised, per idoforgod's team-default)
AND **≥1 sub-agent stage** AND the wired hooks AND **≥1 skill** (≥ the orchestrator skill). If a domain
has no natural team stage, the primary multi-agent work is emitted as a team (idoforgod's default — e.g.,
a "pipeline" domain runs its integration/review stage as a team). Three locked caveats bound this:
**(A2-i)** all-6 is a *floor*, not a *size* — team membership and sub-agent counts scale to the domain
(a 2-member team is fine; "3 focused > 5 scattered"); **(A2-ii)** the warrant `answer-directly` /
`single-agent` verdicts are EXEMPT — they build no harness, so the floor applies only to `build-harness`
(this preserves the off-ramp upstream, dissolving the simplicity-vs-all-6 tension); **(A2-iii)** Agent
Teams are an experimental Claude Code feature, so the emitted harness declares the dependency and
**gracefully degrades to Sub-agents** if the flag is absent (the team stage's TaskCreate-sequenced work
re-expresses as `Agent()` fan + `_workspace/` handoff). New codes: `ALL_PRIMITIVES_PRESENT` enforces the
floor; `TEAM_GRACEFUL_DEGRADE` enforces the documented fallback path exists.

### 3.2 Real team-emit (closes the vaporware gap)

**Verified gap:** `emit_orchestrator._orchestrator_skill()` is byte-identical for agent/team/hybrid —
it always emits `**실행 모드: agent**` and only ever renders `_spawn_recipe()` (line 109, `Agent(...)`
prose). `TeamCreate/SendMessage/TaskCreate/TeamDelete` are **never generated**; `mode` is interpolated
into the header text but drives no branch.

The emitter gains `_team_stage_recipe(stage)` alongside `_spawn_recipe()`; Phase 2 becomes a per-stage
loop dispatching on `selected_primitive`. The orchestrator (= the live session = Team Lead, locked 2)
**literally calls the primitives**. A `team` stage emits exactly five parameterized recipes:

1. **TeamCreate** — members from stage nodes; each member prompt = a *summary harvested from the agent
   `.md` body* (role + I/O + team-comms protocol) so the teammate needs no second file read (the one
   place ido's FORM is adopted wholesale). Team Lead = the orchestrator session (L2-tier, fixed).
   `spawns_used += len(members)` (hook-backed, not prose).
2. **TaskCreate** — shared task list; `depends_on` = **intra-stage edges only** (inter-stage edges stay
   orchestrator-sequencing via toposort; the emitter partitions edges into the two classes).
3. **SendMessage** peer routing — from `team_block.routes` (leader-bypass peer-to-peer); default route
   "share findings on conflict" across all intra-stage pairs if `routes` empty; broadcast only for
   `team_block.broadcast_nodes` (cost-warned).
4. **Team Lead monitoring (L2 coordination)** — idle alerts → `TaskGet` progress → `SendMessage`
   directive or `TaskUpdate` reassign; `state.yaml` single-writer = lead.
5. **TeamDelete** (teardown, mandatory) — flush member outputs to `_workspace/<stage_id>/`; the next
   team stage requires this TeamDelete first (one team per session; nesting forbidden).

A `hybrid` harness is just one whose stages resolve to a mix — exactly idoforgod Template C, now
MACHINE-DRIVEN from `selected_primitive` instead of hand-written.

### 3.3 graph.json schema extensions (additive, backward-compatible)

All new fields are optional (`additionalProperties:false`-compatible); existing
`execution_mode:agent`/single-stage harnesses still validate.

**New top-level fields:**

| Field | Type | Purpose |
|---|---|---|
| `topology` (widen enum) | add `fan-out-fan-in`, `supervisor`, `expert-pool`, `hierarchical` to the existing `pipeline`/`dispatch`/`producer-reviewer` | the 6 first-class topologies (was 3) |
| `stages` | array `{stage_id, node_ids[], selected_primitive, cross_talk, requires_isolation, dynamic_dispatch}` | the unit the selector operates on; absent → one implicit stage per toposort rank |
| `team_block` | `{team_name, lead, routes[], broadcast_nodes[], teardown:"per-stage"}` | drives TeamCreate/SendMessage/TeamDelete |
| `hooks_manifest` | `{l0_anti_skip, l1_verify, l1_5_pacs, l2_review, budget_block, spawn_counter}` each → `{event, script, blocking:bool}` | declares which AWF gate fires as which hook event |
| `memory_config` | `{context_preservation:bool, tier1_snapshots:true, tier2_domain_store:".harness/memory/", rlm_query_mode:"grep-read-recurse", immortal:[...]}` | locked 7 / R4 memory, first-class machine contract |

**New per-node fields:**

| Field | Type | Purpose |
|---|---|---|
| `stage_id` | string | selector grouping |
| `skill_authoring` | `{mode:"inline"\|"skill", reason:"reuse"\|"complex"\|"conditional", shared_by?:[node_ids]}` | locked-5 machine-checkable author-or-inline decision |
| `team_role` | enum `["lead","member","reviewer-isolated"]` | maps node to its primitive slot |
| `memory` | `{reads:[...], writes:[...]}` | cross-run store read/write contract (Tier II) |

`execution_mode` enum: **drop `"workflow"` from the product enum** (constrain to factory-measurement
graphs only); `validate_harness.py:253` default flips from `"workflow"` → `"agent"`.

### 3.4 The 6 topologies as first-class emit targets → primitives

| Topology | Primitive mapping | Status |
|---|---|---|
| **pipeline** | Sequential stages, each `subagent` (single); orchestrator chains by toposort; output of N = Read-input of N+1. No team. | exists |
| **fan-out/fan-in** | One `team` stage, `cross_talk=true`: TeamCreate(fan workers) + TaskCreate(independent) + SendMessage peer routes → Lead Reads `_workspace/<stage>/*` → synthesis subagent. | exists (team-emit was vaporware → fixed §3.2) |
| **producer-reviewer** | Sub-agent pair, `requires_isolation=true`: producer Agent() → fresh read-only reviewer Agent() (NOT teammate — AWF override) → loop `max_rounds`. Maps to `node.review` + L2 gate. | exists |
| **supervisor** (dynamic shared task-list) | `team` stage, `dynamic_dispatch=true`: Lead=supervisor; TeamCreate(workers) + TaskCreate(batch w/ deps); workers self-claim; on `TaskUpdate(done)` Lead emits next-batch `TaskCreate` **at runtime**. Differs from fan-out: tasks added dynamically. | **NEW emit target** |
| **expert-pool** | Sub-agent dispatch with a ROUTER node (`single`, haiku/sonnet) classifying input → orchestrator conditionally spawns ONLY the matched expert Agent(). `topology=expert-pool` + a router node whose `outputs` name candidate expert ids. Sub-agent, not team. | **NEW emit target** |
| **hierarchical-delegation** | 2-level (depth > 2 forbidden): level-1 = team of sub-coordinators; level-2 = each member spawns its own sub-agents via Agent() (teammates CAN spawn sub-agents; teams cannot nest). Validate caps depth at 2. | **NEW emit target** |

The three missing topologies become emittable via (1) the widened enum, (2) the `stages`/`team_block`
blocks, (3) new emit recipes `_team_stage_recipe` + `_router_dispatch_recipe` + `_hierarchy_recipe`
alongside `_spawn_recipe`.

### 3.5 8-use-case → topology → primitive-mix coverage proof (consolidated)

This is the single coverage table reconciling D2's and D4's mappings. (D2 and D4 differed only on
case 5 exec-mode — D4 deliberately models it as `agent` to stay honest about M-deferred dynamic
dispatch. We keep D4's conservative call but note D2's team-variant as the post-M2 upgrade.)

| # | Use case (R2) | `topology` | `exec_mode` | mechanism | primitive highlight | key flags |
|---|---|---|---|---|---|---|
| 1 | Deep Research | fan-out/fan-in | team | reflect-then-revise / cross-validate | TeamCreate fan-out + SendMessage findings-share → synth subagent | `cross_talk` |
| 2 | Website Dev | pipeline | hybrid | reflect-then-revise@QA | pipeline + team@integration + isolated QA agent | per-stage subagent; QA isolated |
| 3 | Webtoon | producer-reviewer | team→**isolated pair** | debate-with-judge | producer → isolated reviewer loop (AWF override, NOT teammate) | `requires_isolation` |
| 4 | YouTube | supervisor | team | single+synth | TaskCreate shared list, dynamic re-dispatch | `dynamic_dispatch` |
| 5 | Code Review | dispatch / fan-out-fan-in | agent (M-now) → team (post-M2) | single fan-out | parallel Agent(run_in_background) + merge — deliberate sub-agent-only today | (cross_talk post-M2) |
| 6 | Tech Docs | pipeline | agent | reflect-then-revise@review | sequential subagents + isolated reviewer | review `requires_isolation` |
| 7 | Data Pipeline | hierarchical | hybrid | debate-with-judge@schema | level-1 team → each spawns subagents (depth ≤ 2) | 2-level team+subagent |
| 8 | Marketing | producer-reviewer / fan-out-fan-in | team | reflect-then-revise (iterative) | team generate→critique→revise loop, isolated reviewer per round | `cross_talk` + producer-reviewer sub-stage |

**Coverage proof:** all 6 topologies exercised (pipeline ×2, fan-out/fan-in ×3, producer-reviewer
×2+embedded, supervisor ×1, expert-pool via the router variant / Code-Review-scoped-to-one-domain,
hierarchical ×1); every primitive class fires across the set (TeamCreate/SendMessage/TaskCreate/
TeamDelete in 1,4,5,7,8; isolated Agent() sub-agents in 2,3,6,7; router dispatch in expert-pool; L0–L2
hook gates in all 8). No case needs a 7th topology or a non-primitive runtime — confirming R3 covers R2
in full.

---

## 4. MANDATORY DNA: Context Preservation + 4-layer QA + RLM long-term memory — R4, D3

### 4.1 Long-term memory — two tiers, RLM as the mechanism (locked 7 option B)

The store is an **external environment**, never loaded whole into context. The orchestrator/agents
treat the memory directory as the RLM "variable in the REPL": they write code (Grep/Read/jq/head) to
peek, decompose, and recursively spawn sub-agents over snippets, fetching only matched slices on
demand. This generalizes the pattern `restore_context.py` already prints as RLM query hints, from
*session restore* to *full domain memory*.

| | **Tier I — SESSION CONTINUITY** | **Tier II — CROSS-RUN DOMAIN MEMORY** |
|---|---|---|
| Survives | token-overflow / `/clear` / compaction / resume (within or across sessions of ONE run) | repeated RUNS of the harness (months apart) |
| Owner | AWF Context Preservation System (already transplanted + wired) | NEW harness-level domain archive (this design) |
| Store | `.claude/context-snapshots/` (latest.md, knowledge-index.jsonl, sessions/, risk-scores.json, work_log.jsonl) + `agent-memory/` | **`.harness/memory/`** (NEW) |
| Status today | wired but "dormant-as-feature" (1 line in emit) | does not exist |
| Consumed by | `restore_context.py` at SessionStart | NEW: orchestrator Phase-0 recall + Phase-7 evolution |

**Tier II store layout — `.harness/memory/`** (the "environment"):
```
.harness/memory/
  domain-knowledge.yaml      # IMMORTAL. DKS entities/relations/constraints (validate_domain_knowledge.py DK1–DK7).
  runs/
    index.jsonl              # APPEND-ONLY thin probe surface: one line/run
                             #   {run_id, ts, query, query_norm, topology, nodes_used, final_status,
                             #    outputs:[paths+sha256], sources:[...], pacs_final, h2h_verdict,
                             #    decisions:[ids], errors_resolved:[{taxonomy,resolution}], tags[]}
    <run_id>/output.<ext>    # heavy payload, content-addressed, fetched only on probe match
    <run_id>/sources.jsonl
    <run_id>/decisions.jsonl
  risk/decisions.jsonl       # IMMORTAL cross-run risk register + standing decisions ("never use X")
  archive.manifest.json      # IMMORTAL RLM index card: section list + their query recipes
```
*Why this shape, not one big file:* RLM out-of-core beats compaction (early detail never forgotten) and
scales 2 orders of magnitude past the window. `runs/index.jsonl` is the thin grep-able probe; heavy
`runs/<run_id>/` is fetched only on a match. Mirrors the genome's existing
`knowledge-index.jsonl` (thin) + `sessions/` (heavy) split.

**WRITE path (Phase 7, single-writer = orchestrator, append-only):** append one `runs/index.jsonl`
line + `runs/<run_id>/{output,sources,decisions}`; **merge** new facts into `domain-knowledge.yaml`
(dedup by entity id); append standing risks to `risk/decisions.jsonl`. `write_paths` for the memory dir
are owned by the orchestrator node only (`WRITE_PATH_OVERLAP` enforces single-owner).

**READ/QUERY path (RLM-style, programmatic, on-demand):** peek the index
(`Grep "<query_norm tokens>" runs/index.jsonl` → matched lines only); decompose (per hit,
`Read runs/<id>/sources.jsonl`, bounded); **recursive sub-agent decomposition** — when a probe returns
many slices, spawn a `@memory-probe` sub-agent **per slice batch via the Agent primitive** (max
recursion depth 1), each returning a distilled finding the orchestrator stitches into a variable;
out-of-core fetch of full `runs/<run_id>/output.*` ONLY when a probe proves it relevant. **No
`claude -p` subprocess** — recursion is delegated to sub-agents (locked-6 prompt-runner exclusion).

### 4.2 Context Preservation made FIRST-CLASS + machine-verified

Closes the "inherited-but-dormant" gap with three coordinated changes:

- **b1. Orchestrator SKILL gets a mandatory `## 메모리 운영 (Memory Operating Cycle)` section** emitted
  verbatim, declaring both tiers + exact RLM recipes (Tier I: rely on genome auto-save/restore, don't
  hand-roll; Tier II: `Phase 0 recall: Grep "<query>" .harness/memory/runs/index.jsonl`; dedup → Read
  sources.jsonl + spawn `@memory-probe`; domain reuse → Read domain-knowledge.yaml; risk → Grep
  risk/decisions.jsonl; Phase 7 write recipe). Its ABSENCE today IS the dormancy gap.
- **b2. `emit_orchestrator.py` + `inherit_genome.py` INITIALIZE the store** — `inherit_genome` runtime
  dirs gain `.harness/memory/{runs,risk}`; a new `_init_memory_store()` writes the three IMMORTAL seed
  files (`archive.manifest.json`, empty `runs/index.jsonl`, seed `domain-knowledge.yaml` passing
  DK1–DK2). This is the byte that flips memory from inherited → initialized.
- **b3. validate codes** assert the wiring (§7.2).

### 4.3 4-layer QA stack made to FIRE — wired as hooks

Today L0/L1/L1.5/L2 fire **only by orchestrator prose** — because although `gate_or_block.py` AND the
validators (`validate_{pacs,verification,review,domain_knowledge}.py`) both **already reach the child**
(validators via the genome; `gate_or_block.py` via `inherit_genome._CYS_HOOKS`), **nothing invokes
`gate_or_block.py` on a hook event**. The work is **wiring + one new runner hook**, not authoring logic
and not a genome transplant of gate/budget. Mechanism: validators take `--step N --project-dir .` and
emit `{"valid":bool}`; `gate_or_block.py` converts `valid:false` → exit 2 (the one signal the host
honors at PostToolUse/PreToolUse).

**The firing hook `qa_gate_runner.py` (new template hook)** — wired `PostToolUse` matcher
`Agent|Task|TaskUpdate` (spawn-return signal). On each Agent return it reads `.harness/state.yaml`
`current_step`, then runs the chain through `gate_or_block.py`, stopping at first block:
L0 `validate_pacs.py --check-l0` (file exists + ≥100B) → L1 `validate_verification.py` (functional goal
100%) → L1.5 `validate_pacs.py` (pre-mortem + min(F,C,L), RED→block) → L2 `validate_review.py` (R1–R5,
**only if** the node has a `review:` attr). Any block → exit 2 → deterministic halt.

**SOT instantiated + single-writer + spawn counting (fixes budget_block):** two new template hooks —
- `sot_init.py` (SessionStart, matcher `startup|clear|resume`): if `.harness/state.yaml` absent, writes
  the seed SOT `{current_step:0, outputs:{}, budget:{spawns_used:0, max_spawns:<from graph>}, pacs:{},
  audit_log:[]}`. Closes the prose-only-SOT gap. Single-writer preserved (only this init + orchestrator
  write; sub-agents never write).
- `spawn_counter.py` (PostToolUse, matcher `Agent|Task|TeamCreate`): increments `budget.spawns_used`
  by 1 per spawn-return. **The missing half** of the budget interlock — `budget_block.py` (PreToolUse)
  reads the count and blocks at `max_spawns − margin`. So the counter (PostToolUse) ↑ → ceiling
  (PreToolUse) blocks. Writes ONLY the reserved integer key `budget.spawns_used` under file lock
  (`append_with_lock`) — the one sanctioned non-orchestrator SOT write, documented in CONSTITUTION
  AC-2 and `memory_config`.

**Review nodes emitted + R5 min-1-issue enforced:** `node.review:{agent}` already exists and
`_spawn_recipe` already emits the L2 recipe; the design adds emitting dedicated
`.claude/agents/{reviewer,fact-checker}.md` (reviewer = Read/Glob/Grep read-only opus; fact-checker =
+WebSearch/WebFetch opus) with the 4-defense rubber-stamp guard embedded, whenever ANY node has
`review:`. R5 (≥1 issue) is enforced by `validate_review.py` wrapped in `gate_or_block` → a 0-issue
review = exit 2.

**Layer → hook → validator → artifact:**

| Layer | Fires via | Validator (via gate_or_block) | Artifact |
|---|---|---|---|
| **L0** Anti-Skip | PostToolUse `qa_gate_runner.py` | `validate_pacs.py --check-l0 --step N` | node output file (≥100B) |
| **L1** Verification | PostToolUse `qa_gate_runner.py` | `validate_verification.py --step N` | `verification-logs/step-N-verify.md` |
| **L1.5** pACS | PostToolUse `qa_gate_runner.py` | `validate_pacs.py --step N` | `pacs-logs/step-N-pacs.md` |
| **L2** Adversarial | PostToolUse `qa_gate_runner.py` (if `review:`) | `validate_review.py --step N` (R1–R5) | `review-logs/step-N-review.md` |
| **Budget** | PreToolUse `budget_block.py` + PostToolUse `spawn_counter.py` | (reads SOT `budget`) | `.harness/state.yaml` `spawns_used` |
| **SOT init** | SessionStart `sot_init.py` | (seeds SOT) | `.harness/state.yaml` |
| **Tier I memory** | Stop/PreCompact/SessionStart `context_guard.py` (already wired) | — | `context-snapshots/{latest.md, knowledge-index.jsonl}` |

The three new hooks land in `templates/hooks/` and are appended to `inherit_genome._CYS_HOOKS`
(currently `[cys_log_tokens, gate_or_block, budget_block]` — `gate_or_block`/`budget_block` are ALREADY
there and ALREADY reach the child; the list is simply **extended** with `qa_gate_runner, sot_init,
spawn_counter`), then wired in `_merge_settings()`. **No genome-DIR transplant of gate/budget is
needed** (correcting an earlier draft).

### 4.4 How memory FEEDS evolution (Phase 7) and improves subsequent runs

1. **Error→resolution recall.** Tier I `knowledge-index.jsonl` records the 12-pattern Error Taxonomy +
   `resolution`; Phase 7 **promotes** repeated cross-run errors into `risk/decisions.jsonl`; next run's
   Phase 0 greps the register → `predictive_debug_guard.py` warns before the known-risky edit. The
   harness stops repeating a past failure.
2. **Prior-output dedup.** Phase 0 greps `runs/index.jsonl` for the normalized query; on a hit, spawns
   `@memory-probe` sub-agents over matched `sources.jsonl` to find already-answered sub-questions →
   **skips or shrinks** those nodes (lower fan-out → lower `max_spawns` → cheaper run).
3. **Domain-knowledge reuse.** `domain-knowledge.yaml` (validated DK1–DK7) is read at Phase 0 and
   injected as **L1 verification criteria**; each run refines it → domain reasoning measurably improves
   run over run.

**Evolution feedback into the contract:** Phase 7 routes accumulated signal (recurring near-misses,
dedup hit-rate, pACS trends) into a **proposed `graph.json` revision** (drop an always-deduped node,
raise an always-RED tier). Because graph.json is the machine-checked contract, every proposal re-passes
`validate_harness.py` before adoption — evolution cannot corrupt the contract. **The loop:**
memory → Phase 7 analysis → graph.json proposal → validate gate → next run reads improved memory.

---

## 5. THE 8-USE-CASE PARITY EVAL + FEATURE-PARITY MATRIX — R2, D4

### 5.1 Foundational split (governs the whole eval)

Two eval layers, never conflated:
- **L-factory** (build correctness): did the factory EMIT the right harness? Pure Python,
  byte-deterministic, runs free in CI every commit.
- **L-runtime** (effectiveness): does the emitted harness beat no-harness? Live session, statistical
  n-run median, quota-gated.

The 8 cases are graded **primarily at L-factory** (the CI gate) and **conditionally at L-runtime** (the
expensive h2h — the quota lesson forces this).

### 5.2 Per-case PASS criterion (machine-checkable acceptance tests C1–C8)

Each case = a golden `expected.json` spec; a new pure matcher `eval_topology.py` compares emitted
artifacts against it. (Topology/exec-mode/mechanism mix per case = §3.5.)
- **C1** warrant verdict matches; **C2** topology matches; **C3** exec_mode matches; **C4**
  `validate_harness --json` exit 0 (all codes green); **C5** primitive_mix all true (orchestrator skill +
  ≥N agents + team primitives present for team cases + `Agent(` for agent cases + hooks wired +
  authored-skill count); **C6** DNA all true (memory first-class + `qa_stack_wired==[L0,L1,L1.5,L2]` +
  cross-run store); **C7** lift register per authored skill; **C8** (quota lane) h2h verdict.

C1–C6 free; C7 one cheap probe per skill; C8 the expensive live h2h.

### 5.3 PASS/FAIL for "cys-harness-creator works"

- **Self-test** extends `tests/test_factory.py` with a data-driven `TestEightUseCases` iterating
  `tests/golden/usecases/*.expected.json`.
- **CI-safety choice:** no agent spawn, no genome transplant in the suite. Each case ships a **frozen
  golden harness** (committed graph.json + SKILL.md + settings excerpt + frozen `lift_results.json` VCR
  cassette) — same pattern as the existing `tests/golden/*.workflow.js`. Tripwire: a cassette that no
  longer reproduces its frozen verdict fails the test.
- **Three lanes:** per-commit free/blocking (`make test`, C1–C7 over cassettes, sub-second, red blocks
  merge); golden-refresh manual (`make refresh-goldens` on intentional emitter change); quota-gated h2h
  non-blocking (`make h2h CASE=...` via the resumable `run_h2h.py`).
- **Crisp definition:** *works ⟺ C1–C6 PASS for all 8 AND C7 PASS for every authored skill.* **C8
  (≥+15pp) is explicitly NOT part of "works"** — per locked 4 the benchmark is feature parity, not
  superiority. A BASELINE-WINS verdict is recorded honestly, never hidden/fabricated (enforced by
  `MEASUREMENT_DRIFT`).

### 5.4 Feature-parity matrix (16 features → status)

4 has-equivalent, 4 form-adopted, 2 capability-via-CYS-superset, **6 to-build**:
- **has-equivalent:** agent-separation 4 axes; with/without lift (`lift_gate`, stronger via blind
  grader); trigger near-miss doctrine; progressive-disclosure doctrine.
- **form-adopted:** agent-def generation; pushy descriptions + follow-up keywords; orchestrator +
  data-passing; QA agent — CYS adopts `.claude/agents`/`.claude/skills`/TeamCreate because the form IS
  the native mechanism.
- **capability-via-CYS-superset:** 6 topologies → (widened enum × 3 exec-modes × 4 mechanisms)
  orthogonal algebra (strictly more expressive); "all-opus" → role→tier `TIER_OVERSPEND` (deliberate
  improvement, not a gap).
- **6 to-build (= the named gaps):** #2 domain-skill emitter (+`skill_authoring` field); #3 real team
  emit (today byte-identical to agent emit — the headline bug); #4 dynamic-dispatch/expert-pool; #9
  trigger-eval runner; #11 Phase-0 audit; #12/#13 Phase-7 evolution + CLAUDE.md pointer/change-history.
- **team-default divergence:** CYS deliberately diverges (agent default, team after P5 proof) — a
  locked-decision divergence, not a gap; team capability is fully present.

### 5.5 Wiring lift_gate + h2h into the build (currently orphaned — zero call sites)

Both tools are correct/tested but never invoked by emit/validate — a harness can ship unmeasured. The
fix makes measurement a build/claim precondition:
- **Gate 2 (lift) at skill-authoring (Stage 3 / ido P4):** new `LIFT_UNMEASURED` validate error —
  every `skill_authoring.mode=="skill"` node must have a committed `lift_verdict.json` with
  `decision:"register"`, else build fails ("inline it or strengthen it"). Makes locked-5 hybrid
  authoring enforced by lift.
- **Gate 3 (h2h) at harness-completion (Stage 4 / ido P7):** emitter writes per-harness
  `scorecard.json`; `make h2h` drives the resumable runner → `h2h_aggregate` → `verdict.json`.
  `MEASUREMENT_DRIFT` enforces it, EXTENDED to also block any doc citing a `delta_pp` that disagrees
  with the on-disk verdict (the precise "+37.5pp" regression class). Winning is not required; honesty is.

**Findings that anchor the honesty design:** the team-emit gap is confirmed real (cases 1/3/4/8 fail C5
`uses_team_primitive` today); `lift_gate`/`h2h` have zero call sites in emit/validate; the only stamped
h2h on disk is n=1 BASELINE-WINS −16.67pp (`deep-research.verdict.json`); `dispatch(dynamic)`/
supervisor/expert-pool are deferred, so cases 4/5 are modeled as static dispatch to stay honest.

---

## 6. PRESERVED STRENGTHS — D5

Format: **strength → survives? → how it extends.**

- **P1. graph.json machine contract (draft 2020-12, single-writer).** *Survives unchanged as the
  build-time contract* — the load-bearing invariant of the pivot. graph.json stays the only
  machine-checkable spine, authored once (Planning P1, single-writer). 100% primitive execution does
  NOT weaken it because **the contract is consumed at BUILD time, not runtime**: `emit_orchestrator.py`
  *reads* graph.json and *renders* it into prose (orchestrator SKILL + agent bodies + frontmatter) — the
  prose is a **projection** of the contract, not an alternative source of truth.
  `GRAPH_SKILL_CONSISTENCY` keeps prose↔contract coherent and the new codes extend that guard so every
  new prose obligation (topology verbs, hooks, skills, memory) is re-derivable. *Extends* additively
  (new optional fields; `additionalProperties:false` stays).
- **P2. ~20-code static build gate (`validate_harness.py`).** *Survives unchanged in structure*
  (Report/err/warn, exit 0/1/2, `--json`, per-node loop); every existing code kept. *Extends by ADDING
  codes, never relaxing.* The one behavioral edit (not a relaxation): flip the `RUNTIME_DECLARED`/
  `execution_mode` default off `"workflow"` (locked 3) and error on any emitted `workflow.js` in a
  product harness.
- **P3. role→tier model policy + JS↔Py mirror guard.** *Survives unchanged and is UPGRADED to
  runtime-enforced* — the pivot's single biggest free win. `model-tier-policy.js` untouched; the
  Python `TIER_BY_ROLE_CLASS` mirror + `TIER_*` codes untouched. Under Mode A the tier was advisory
  (Workflow downgraded all agents); under the primitive substrate the Agent tool honors `model:`
  frontmatter, so the same policy binds at runtime. The `MIRROR_DRIFT` guard (landed `5f08407`/C16)
  stays; any new role-class for the 8 use-cases must be added to both sides or it fires.
- **P4. team-aware cost band (`warrant.py cost_band`).** *Survives unchanged* — already adds
  `TEAM_COORD_TOKENS × len(nodes)` for `team|hybrid` (verified line 152); off-ramp + LOW/MED/HIGH +
  `approval_required` untouched. *Extends:* the coordination term becomes topology-aware
  (supervisor/hierarchical cost more SendMessage rounds) via a `rounds`/`member_count` multiplier driven
  by the new `topology`/`stages` fields — additive, still display-only; hard ceiling stays
  `budget.total_tokens` + runtime `budget_block`.
- **P5. genome inheritance with functional load-verify.** *Survives unchanged* — `inherit_genome.py`
  rsync + `GENOME_PRESENT` (load-bearing files) + `HOOK_REGISTERED` + py_compile/import-spine verify
  kept; security + context-preservation hooks already FIRE. *Extends:* `inherit_genome._CYS_HOOKS` gains the
  three NEW hooks (`qa_gate_runner`, `spawn_counter`, `sot_init`) — `gate_or_block`/`budget_block` are
  already in `_CYS_HOOKS` and already reach the child, so only the QA *runner* + counters are new;
  `GENOME_PRESENT`'s `must_exist` list and `HOOK_REGISTERED`'s `needed_hooks` grow so the gate errors if
  the new hooks aren't wired. This is how AWF DNA goes from "vendored/advisory" to "fires" (locked 6)
  without weakening the verify.
- **P6. measurement infra (lift_gate blind grader + h2h_aggregate + MEASUREMENT_DRIFT honesty gate).**
  *Survives unchanged* — `lift_gate.py` (threshold 0.2, blind grader, register/refuse),
  `h2h_aggregate.py` (15pp margin, C2 vs C3), `MEASUREMENT_DRIFT` build-check all kept verbatim; the
  honesty gate is the institutional memory of the +37.5pp lesson, explicitly preserved. *Extends:* the
  8-use-case suite plugs into `h2h_aggregate` unchanged (new scorecard fixtures); `MEASUREMENT_DRIFT`
  extended to catch stale numeric drift (`STALE_BENCHMARK`) and scope-extended to scan `design/`.

---

## 7. SEQUENCED BACKLOG + NEW VALIDATE CODES + RISK REGISTER — D5 + D1/D2/D3/D4 net-changes

### 7.1 Sequenced backlog (design-only milestones, ordered by dependency)

Dependency spine: the primitive-delegation contradiction (M0) closes first — every later milestone
assumes primitive is the only product runtime. Then the substrate that makes DNA fire (M1), then emit
features (M2–M3), then phases (M4–M5), then memory (M6), then eval (M7), then honesty-doc fixes (M8,
parallel after M0). Each: **goal · files · machine-check that proves done.**

- **M0 — Close the primitive-delegation contradiction (FOUNDATION; blocks all).** (1) flip
  `validate_harness.py:253` default `"workflow"`→`"agent"`, add `WORKFLOW_RETIRED`; (2) drop `"workflow"`
  from the product `execution_mode` enum in `graph.schema.json`; demote `emit_workflow.py` +
  `h2h_suite.workflow.js` to factory-internal `_measurement/`; rewire SKILL.md Phase-4 line 63
  (`emit_workflow.py`→`emit_orchestrator.py`) and delete the workflow product-command lines; (3) fix
  `emit_orchestrator.py:113` (`sch = n.get("output_schema") or "(none)"`); (4) **add
  `qa_gate_runner.py` + `spawn_counter.py` + `sot_init.py` to `templates/hooks/` and
  `inherit_genome._CYS_HOOKS`** (`gate_or_block`/`budget_block` are ALREADY in `_CYS_HOOKS` and reach
  the child — no transplant needed), and wire all in `genome/.claude/settings.json` +
  `inherit_genome._merge_settings()`; (5) `_spawn_recipe`/`_orchestrator_skill` branch on
  `execution_mode` (real team emit); **(6) SCRUB the retired-runtime advertising that ships into EVERY
  child** (verified leak) — `emit_orchestrator._runtime_manifest()` must stop listing
  `cys-mode-a-workflow`/`awf-prompt-runner` in the child's `.harness/RUNTIME.json` (orchestrator-canonical
  ONLY), and `inherit_genome._CLAUDE_PTR` + its default `_RUNTIME_MANIFEST` must stop declaring
  `.harness/workflow.js` as the child's "canonical runtime". *Proves done:* `WORKFLOW_RETIRED`,
  `RUNTIME_MANIFEST_CLEAN` (new — no child RUNTIME.json/CLAUDE.md names `workflow.js`/`prompt-runner` as
  an execution runtime), `HOOK_REGISTERED` (extended), `SPAWN_COUNTER_WIRED`, `SOT_INIT_WIRED`,
  `TEAM_EMIT_PRESENT`, `SCHEMA_REF_VALID` all pass; factory tests + a team-mode example validate 0/0.
- **M1 — 4-layer QA + Context Preservation FIRST-CLASS (R4).** Wire L0→L1→L1.5→L2 via
  `qa_gate_runner.py` (PostToolUse) fronted by `gate_or_block`; emit `review:` nodes as real L2 spawns +
  `.claude/agents/{reviewer,fact-checker}.md`; verify Context Preservation first-class. *Proves done:*
  `QA_HOOKS_WIRED` (umbrella) + `L0_ANTISKIP_WIRED`/`L1_VERIFICATION_WIRED`/`PACS_GATE_WIRED`/
  `QA_LAYER_WIRED`/`GATE_UNWRAPPED`/`CONTEXT_PRESERVATION_FIRSTCLASS`.
- **M2 — Real team/hybrid emit + 6 topologies (R3, locked 4).** Widen `topology` enum 3→6; add
  `stages`/`team_block`/`team_role`/`stage_id`; `_team_stage_recipe`/`_router_dispatch_recipe`/
  `_hierarchy_recipe`; warrant `classify` maps domain shape → one of 6. *Proves done:*
  `TOPOLOGY_PRIMITIVE_CONSISTENCY`, `PRIMITIVE_SELECTOR_WELLFORMED`, `TEAM_TEARDOWN`. (Gate the
  supervisor/hierarchical sub-milestone behind a live probe; ship pipeline/fan-out/producer-reviewer
  first → 6/8 use-cases.)
- **M3 — Domain-skill emitter (hybrid author-or-inline, locked 5).** Add `node.skill_authoring`;
  `emit_domain_skill.py` writes `.claude/skills/<skill>/SKILL.md` for `mode:"skill"`, inlines otherwise.
  *Proves done:* `SKILL_AUTHORING_CONSISTENCY` (umbrella) + `SKILL_AUTHORING_DECLARED`/
  `SKILL_AUTHORING_JUSTIFIED`/`INLINE_NO_ORPHAN_SKILL`/`LIFT_UNMEASURED`.
- **M4 — Phase 0 Status Audit.** New `audit_harness.py` (3-source inventory + 3 set-diffs +
  new/extend/maintain branch); expand SKILL.md Phase 0. *Proves done:* `AUDIT_VERDICT_PRESENT`,
  `AUDIT_NONDESTRUCTIVE`.
- **M5 — Phase 7 Evolution loop.** New `evolve_harness.py` + SessionEnd outcome hook; SKILL.md Phase 7
  routing. *Proves done:* `EVOLUTION_LOG_PRESENT`, `EVOLUTION_WIRED`, `FEEDBACK_ROUTED`. (Phase 7 only
  *proposes* graph.json edits → single-writer + approval preserved.)
- **M6 — RLM cross-run memory store (locked 7, R4).** `.harness/memory/` layout; `_init_memory_store()`;
  `## 메모리 운영` SKILL section; `node.memory` + `memory_config`; `query_workflow.py` programmatic
  accessor. *Proves done:* `MEMORY_FIRST_CLASS` (umbrella) + `MEMORY_CONFIG`/`MEMORY_STORE_INIT`/
  `MEMORY_SKILL_SECTION`/`MEMORY_HOOKS_WIRED`/`DOMAIN_KNOWLEDGE_VALID`/`RLM_PROGRAMMATIC_ONLY`/
  `CROSS_RUN_MEMORY_CONSUMED`.
- **M7 — 8-use-case eval suite (R2 bar).** `eval_topology.py` + 8 `expected.json` + cassettes + 8
  `evals/<usecase>.scorecard.json`; `TestEightUseCases`. *Proves done:* `USECASE_COVERAGE`; each example
  validates 0/0; lift register/refuse per case; `MEASUREMENT_DRIFT` clean. (Items M7.1–M7.4 — matcher,
  field, emitter, lift wiring — are the minimum to make the eval a real CI gate.)
- **M8 — Honesty-drift doc fixes (parallel after M0).** Correct stale `+38pp`/`+37.5pp` literals to the
  stamped −16.67pp n=1 (or remove); reconcile `IMPLEMENTATION-STATUS.md` "P1 built" with genome
  ground-truth (gate/budget hooks were in `templates/`, not wired); extend `MEASUREMENT_DRIFT` scope to
  `design/` + token-normalization. *Proves done:* `STALE_BENCHMARK`, `TOKEN_NORMALIZED`,
  `MEASUREMENT_DRIFT` (scope-extended).

### 7.2 New validate_harness check codes (grouped by milestone)

Existing ~20 codes kept verbatim. New codes (canonical names per §0; component-specific sub-codes
retained where they assert distinct facts):

**Primitive-delegation (M0):** `WORKFLOW_RETIRED` (no product `workflow.js`/`execution_mode:"workflow"`);
`TEAM_EMIT_PRESENT` (team-mode orchestrator SKILL literally contains `TeamCreate`+`TaskCreate`+
`TeamDelete`, and `SendMessage` if `routes` non-empty); `TEAM_TEARDOWN` (every `TeamCreate` has a
matching `TeamDelete` before the next); `SPAWN_COUNTER_WIRED`; `SOT_INIT_WIRED`; `SCHEMA_REF_VALID`
(emitted schema path uses `node.output_schema`, not node id); `RUNTIME_MANIFEST_CLEAN` (no emitted
child `RUNTIME.json`/`CLAUDE.md` advertises `workflow.js` or `prompt-runner` as an execution runtime —
closes the verified leak in `emit_orchestrator._runtime_manifest` + `inherit_genome._CLAUDE_PTR`).

**DNA-fires (M1):** `QA_HOOKS_WIRED` (umbrella) with sub-codes `L0_ANTISKIP_WIRED`,
`L1_VERIFICATION_WIRED`, `PACS_GATE_WIRED`, `QA_LAYER_WIRED` (every `review` node's L2 gate is BOTH in
prose AND wired); `GATE_UNWRAPPED` (negative: a `valid:false`-emitting validator must be fronted by
`gate_or_block`, never wired raw); `CONTEXT_PRESERVATION_FIRSTCLASS`; `HOOK_MANIFEST_WIRED` (every
`hooks_manifest` entry with `blocking:true` is present in settings for its declared event — extends the
existing `HOOK_REGISTERED`).

**Topology/primitive coherence (M2):** `TOPOLOGY_PRIMITIVE_CONSISTENCY` (declared topology matches
emitted primitives: `fan-out-fan-in`/`supervisor` ⇒ a team stage; `producer-reviewer`/`expert-pool` ⇒
isolated sub-agent stages); `PRIMITIVE_SELECTOR_WELLFORMED` (per stage: `cross_talk` ⊕
`requires_isolation` mutually exclusive; `dynamic_dispatch` ⇒ team; `len==1` ⇒ subagent; hierarchy
depth ≤ 2); `ALL_PRIMITIVES_PRESENT` (locked A2: every `build-harness` instantiates all 6 primitive
types — orchestrator + agents + sub-agents + **≥1 team stage** + hooks + **≥1 skill** — exempt only for
warrant `single-agent`/`answer-directly`); `TEAM_GRACEFUL_DEGRADE` (each team stage ships a documented
Sub-agent fallback for when the experimental Agent-Teams flag is absent).

**Hybrid domain-skill (M3):** `SKILL_AUTHORING_CONSISTENCY` (umbrella) with `SKILL_AUTHORING_DECLARED`
(every node has a valid field), `SKILL_AUTHORING_JUSTIFIED` (`mode:"skill"` reason is checkable:
`reuse`→`shared_by`≥2, `complex`→body-length, `conditional`→branching present), `INLINE_NO_ORPHAN_SKILL`
(`mode:"inline"` has no domain SKILL.md; `mode:"skill"` has one), `LIFT_UNMEASURED` (every `skill` node
has a committed `lift_verdict.json` `decision:"register"`).

**Phase 0 audit (M4):** `AUDIT_VERDICT_PRESENT` (`.harness/audit.json` with `{new|extend|maintain}` +
drift list on regeneration over an existing dir); `AUDIT_NONDESTRUCTIVE` (extend/maintain did not
clobber non-emit-owned files per `harness.lock`).

**Phase 7 evolution (M5):** `EVOLUTION_LOG_PRESENT` (`.harness/change-history.jsonl` append-only,
schema-valid); `EVOLUTION_WIRED` (SessionEnd feedback hook registered); `FEEDBACK_ROUTED`.

**RLM memory (M6):** `MEMORY_FIRST_CLASS` (umbrella) with `MEMORY_CONFIG` (top-level `memory_config`
object present), `MEMORY_STORE_INIT` (`.harness/memory/` with `archive.manifest.json` +
`runs/index.jsonl` + `domain-knowledge.yaml`), `MEMORY_SKILL_SECTION` (`## 메모리 운영` heading + 4 RLM
recipe lines), `MEMORY_HOOKS_WIRED`, `DOMAIN_KNOWLEDGE_VALID` (DK1–DK7 via `validate_domain_knowledge.py`),
`RLM_PROGRAMMATIC_ONLY` (orchestrator/agents query via Grep/Read/code; no full-store dump inlined),
`CROSS_RUN_MEMORY_CONSUMED` (≥1 node declares `memory.reads`).

**8-use-case parity (M7):** `USECASE_COVERAGE` (all 8 scorecards exist, each mapped to its implied
topology).

**Honesty-drift (M8):** `STALE_BENCHMARK` (no doc asserts a current head-to-head margin contradicting
the latest `evals/*.verdict.json`); `TOKEN_NORMALIZED` (a CYS-WINS claim cites a token-normalized
comparison); `MEASUREMENT_DRIFT` scope-extended to `design/`.

### 7.3 Risk register (where the design could fail the ABSOLUTE RULE or the parity bar)

| # | Risk | Hits | Mitigation |
|---|---|---|---|
| **RR1** | **Hooks/gates are factory Python running at the child's runtime** — is a PostToolUse `gate_or_block.py` subprocess a violation of "100% primitive execution"? | ABSOLUTE RULE | The rule governs *execution/orchestration* (who spawns/coordinates work = Agent/TeamCreate/SendMessage/TaskCreate). Hooks are the harness's **governance substrate** (settings.json lifecycle), the same mechanism AWF + idoforgod use — they GATE work, don't DO it. State in CONSTITUTION: **primitives do the work; hooks gate the work; no non-primitive runtime spawns or coordinates agents** (exactly why prompt-runner stays inert). |
| **RR2** | **prompt-runner / `claude -p` subprocess leaks into child execution** — RLM recursion (M6) is tempting to implement as a subprocess supervisor. | ABSOLUTE RULE | Locked 6 excludes prompt-runner from child execution. M6 recursion MUST be delegated to **sub-agents** (Agent tool). `RLM_PROGRAMMATIC_ONLY` + a check that no emitted child wires prompt-runner into execution. |
| **RR3** | **Gate is narrated, not fired** — validators exit 0 even on `valid:false` (verified); the "DNA fires" claim collapses if they stay advisory. | locked 6 intent | `GATE_UNWRAPPED` + `QA_HOOKS_WIRED` make "fronted by gate_or_block AND wired as a hook" a build-time error if absent. Converts locked-6 "must FIRE" from prose to interlock. |
| **RR4** | **The contradiction reappears** — if `workflow.js` survives reachable from product emit, graph.json has two consumers again. | locked 3 | `WORKFLOW_RETIRED` errors; emit_workflow demoted to `_measurement/`; enum drops `workflow`; SKILL.md Phase-4 rewired. M0 gates everything. |
| **RR5** | **spawns_used stays 0 → cost ceiling is fiction** — `budget_block` IS already wired (PreToolUse) but reads a `spawns_used` counter that **nothing increments**, and `state.yaml` is **never instantiated** — so the ceiling can't fire. (NOT a budget_block-wiring gap.) | P4/P5 | M0 ships the two missing halves `spawn_counter.py` (PostToolUse ↑) + `sot_init.py` (SessionStart seed); `SPAWN_COUNTER_WIRED`/`SOT_INIT_WIRED` prove wiring. Single-writer race mitigated by reserving `budget.spawns_used` as the counter's disjoint key (CONSTITUTION AC-2 amendment, file-locked). |
| **RR10** | **Retired-runtime advertising ships into every child** (verified leak) — `emit_orchestrator._runtime_manifest()` writes `.harness/RUNTIME.json` listing `workflow.js`+`prompt-runner` as runtimes, and `inherit_genome._CLAUDE_PTR` declares `workflow.js` canonical, in EVERY child — a direct locked-3 contradiction the draft first missed. | locked 3 | M0 step (6) scrubs both; `RUNTIME_MANIFEST_CLEAN` errors if any child artifact names `workflow.js`/`prompt-runner` as an execution runtime. |
| **RR11** | **All-6 floor (A2) collides with the experimental Agent-Teams flag** — forcing a team stage everywhere hard-depends every harness on `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`. | A2 / robustness | `TEAM_GRACEFUL_DEGRADE`: each team stage emits a documented Sub-agent fallback (`Agent()` fan + `_workspace` handoff); the harness declares the dependency in RUNTIME.json and degrades, never breaks. |
| **RR6** | **Parity unmet on supervisor/hierarchical cases (YouTube, Data Pipeline)** — those topologies are deferred (dynamic dispatch unimplemented). | parity (R2) | Sequence the 6th-topology emit behind a live probe (M2 sub-milestone); 6/8 cases land on pipeline/fan-out/producer-reviewer; deferred 2 approximated by 2-stage pipeline with documented fallback, then upgraded. Don't fake n≥5 or fake topology coverage. |
| **RR7** | **Adopting idoforgod's FORM dilutes CYS's machine-contract** — their `.claude/skills/` form is schemaless prose; CYS's edge is the graph.json contract. | parity vs P1 | The form is an **emit target** (we generate `.claude/skills/` like they do) but remains a **projection of graph.json** — `GRAPH_SKILL_CONSISTENCY` + `SKILL_AUTHORING_*` keep prose machine-derivable. We get their form AND our contract. |
| **RR8** | **Honesty drift persists in shipped docs** (stale +38pp, un-normalized win claims). | P6 / honesty | M8 `STALE_BENCHMARK` + `TOKEN_NORMALIZED` + `MEASUREMENT_DRIFT` scope-extension make superiority claims build-time-falsifiable against `evals/*.verdict.json`. Reconcile IMPLEMENTATION-STATUS "P1 built" against genome ground-truth. |
| **RR9** | **Session-boundary handoff (R4) silently breaks DNA** — if the harness is spawned from the *factory* session, the factory's hooks fire, not the child's (dormancy reappears). | locked 6 / R4 | RUNTIME.json `launch` field + SKILL.md R4 note (`cd <TARGET> && claude`); new `LAUNCH_DECLARED` check; the eval suite (M7) runs each use-case from a fresh child session, not the factory. |

### 7.4 Net file-touch summary (design targets, no code this pass)

- `/Users/cys/Desktop/CYSjavis/cys-harness-creator/skills/harness-creator/SKILL.md` — rewrite to the
  4-stage structure (§2.3); remove `emit_workflow` product lines; Phase-0→audit, Phase-7→evolution.
- `/Users/cys/Desktop/CYSjavis/cys-harness-creator/skills/harness-creator/references/` — restructure to
  the 8-file map (§2.4); fold `examples.md`→`architecture-patterns.md`; add `genome-and-runtime.md`,
  `evolution-and-memory.md`, `skill-and-agent-authoring.md`.
- `/Users/cys/Desktop/CYSjavis/cys-harness-creator/graph.schema.json` — widen `topology` enum (+3); drop
  `workflow` from product `execution_mode`; add `stages`, `team_block`, `hooks_manifest`,
  `memory_config`; node `stage_id`, `skill_authoring`, `team_role`, `memory`.
- `/Users/cys/Desktop/CYSjavis/cys-harness-creator/validate_harness.py` — flip line-253 default; add the
  ~20 new codes (§7.2).
- `/Users/cys/Desktop/CYSjavis/cys-harness-creator/emit_orchestrator.py` — fix line-113 schema-ref bug;
  add `_team_stage_recipe`/`_router_dispatch_recipe`/`_hierarchy_recipe` + per-stage Phase-2 dispatch;
  `_init_memory_store()`; emit reviewer/fact-checker agents + `## 메모리 운영` section; **scrub
  `_runtime_manifest()` of `workflow.js`/`prompt-runner` runtimes** (orchestrator-canonical only — RR10).
- `/Users/cys/Desktop/CYSjavis/cys-harness-creator/emit_workflow.py` +
  `/Users/cys/Desktop/CYSjavis/cys-harness-creator/h2h_suite.workflow.js` — demote to factory-internal
  `_measurement/` (locked 3).
- `/Users/cys/Desktop/CYSjavis/cys-harness-creator/warrant.py` — topology-aware coordination multiplier
  (additive to the existing team term).
- `/Users/cys/Desktop/CYSjavis/cys-harness-creator/genome/.claude/settings.json` — wire `gate_or_block`-
  fronted L0–L2, `budget_block` (PreToolUse), `spawn_counter` + `sot_init`, `qa_gate_runner`.
- `/Users/cys/Desktop/CYSjavis/cys-harness-creator/templates/hooks/` — add `qa_gate_runner.py`,
  `spawn_counter.py`, `sot_init.py` (each with `--selftest`). **`gate_or_block.py`+`budget_block.py` are
  already here and already in `_CYS_HOOKS` → NOT re-transplanted** (correcting an earlier draft that
  pointed at `genome/.claude/hooks/scripts/`).
- `/Users/cys/Desktop/CYSjavis/cys-harness-creator/inherit_genome.py` — extend `_CYS_HOOKS` (+3 new
  hooks) + `_RUNTIME_DIRS` (+`.harness/memory/{runs,risk}`) + `GENOME_PRESENT` must_exist + wire in
  `_merge_settings()`; **scrub `_CLAUDE_PTR` + default `_RUNTIME_MANIFEST` of all `workflow.js`-canonical
  declarations** (RR10 / locked 3).
- `/Users/cys/Desktop/CYSjavis/cys-harness-creator/constants.json` — add `MEMORY_IMMORTAL_SECTIONS`.
- NEW factory tools: `audit_harness.py` (Phase 0), `emit_domain_skill.py` (Phase 4 hybrid),
  `evolve_harness.py` (Phase 7), `eval_topology.py` (M7 matcher). All build-time Python (Layer 1 —
  permitted).
- `/Users/cys/Desktop/CYSjavis/cys-harness-creator/tests/test_factory.py` — add `TestEightUseCases`
  over `tests/golden/usecases/*.expected.json` + cassettes.

---

## 8. SCOPING DEFAULTS (B1/B2) + TECHNICAL-GAP HANDLING (C) — from the pre-design review

### 8.1 Scoping defaults (locked as defaults unless overridden)
- **B1 — what "pass the 8 use cases" means.** PASS = **build-level (L-factory) for all 8** (C1–C6:
  warrant/topology/exec-mode match, validate 0/0, all-6 primitive composition present, DNA present) +
  **run-level (L-runtime, C8 h2h) for a self-contained representative subset** (Deep Research first).
  Running Website-Dev (real deploy) / Webtoon (image gen) end-to-end on every commit is impractical as a
  regression gate; build-level is the CI bar, run-level is quota-gated + non-blocking (matches §5.3).
- **B2 — install model.** Default = **self-contained `<harness>/` dir** (`cd <TARGET> && claude` so the
  child's own hooks fire — RR9). Also support an **idoforgod-style in-project install** (harness merges
  into an existing project's `.claude/` + `CLAUDE.md`), which REQUIRES the Phase-0 audit's safe
  settings/hook merge (C3). The two modes differ only in TARGET + the merge step.

### 8.2 Technical gaps handled in the design
- **C1 (Teams experimental flag).** Graceful-degrade to Sub-agents — `TEAM_GRACEFUL_DEGRADE` (§3.1
  A2-iii, RR11).
- **C2 (domain-memory hygiene).** `.harness/memory/` entries carry provenance (`run_id`, ts, sha256) +
  recency-decay (reuse Tier-I `risk-scores` weighting) + a **verify-before-reuse** rule: a recalled prior
  output is re-validated against current `domain-knowledge.yaml` before reuse, never trusted blind —
  prevents stale/contaminated memory from poisoning new runs.
- **C3 (hook/settings merge on in-project install).** Phase-0 audit safe-merge: union the genome's
  `settings.json` hooks with the host's existing hooks (no clobber); a collision surfaces as drift, never
  a silent overwrite.
- **C4 (tier ↔ parity quality floor).** Tier policy keeps opus on quality-critical nodes; `lift_gate`
  measures each authored skill so a cheaper tier can never silently drop a use-case below the parity
  floor (`LIFT_UNMEASURED` blocks unmeasured skills).
- **C5 (RLM recursion cost).** Memory-probe sub-agent spawns are counted by `spawn_counter.py` into
  `budget.spawns_used`, so RLM recursion is priced by warrant + capped by `budget_block` like any spawn.
- **C6 (harness-version ↔ memory-version).** Each `runs/index.jsonl` entry stamps the harness
  `git_sha`/`harness_version`; Phase-7 evolution that changes the contract bumps the version, and recall
  down-weights/filters memory from incompatible prior versions (no cross-version mis-application).

### 8.3 Consistency nits from the critic (folded)
- **DOC_DRIFT direction.** The new SKILL.md is 4-stage; `_count_phases`/`DOC_DRIFT` must declare the
  **orchestrator SKILL's stage count as canonical** and compare the child README to it (NOT to
  idoforgod's 8-phase count) — else false positives. Spelled out in `genome-and-runtime.md`.
- **Phase-0 / SOT "prose-already-exists" nuance.** The current emitted orchestrator already has a `{p0}`
  context branch + prose SOT-write; M0/M4 **REPLACE** that prose with machine artifacts
  (`audit_harness.py`, `sot_init.py`) — they do not add net-new double-emitted phases.

> **Status of this document:** corrected against first-hand file reads + the consistency critic + locked
> decisions A1 (deterministic-guardrail boundary) and A2 (all-6 floor). The earlier-draft errors
> (gate_or_block/budget_block "not transplanted"; the `_runtime_manifest`/`_CLAUDE_PTR` retired-runtime
> leak) are fixed inline above. DESIGN-ONLY — no product code changed this pass.
