# AgenticWorkflow — Common Directive for AI Agents

> This file defines the rules that **all AI agents working on this project must follow, regardless of model or tool**.
> Whether you use Claude Code, Cursor, Copilot, Codex, or any other tool, the rules in this document apply.

---

## 1. Project Definition

An agent-based workflow automation project. Its purpose is to systematically design complex tasks as workflows and actually implement those workflows so that they run.

### Final Goal — A 2-Stage Process

| Stage | Deliverable | Nature |
|-------|-------------|--------|
| **Phase 1: Workflow Design** | `workflow.md` | Intermediate deliverable (blueprint) |
| **Phase 2: Workflow Implementation** | A system where agents, scripts, and automation actually run | **Final deliverable** |

> Creating `workflow.md` is only half the journey. **The final goal is that the content described in it actually runs.**

### Reason for Existence — DNA Inheritance

AgenticWorkflow is a **parent organism that gives birth to child agentic workflow systems**. Whatever domain the child belongs to, it structurally embeds the entire parent genome.

| Genome Component | Form Embedded in Child |
|------------------|-----------------------|
| 3 Absolute Criteria | `Inherited DNA` section of workflow.md — contextualized per domain |
| SOT pattern | `state.yaml` — single file + single write point |
| 3-stage structure | Structural constraint: Research → Planning → Implementation |
| 4-layer verification | L0 Anti-Skip → L1 Verification → L1.5 pACS → L2 Review |
| P1 containment | Python deterministic validation scripts |
| Safety Hook | Dangerous command blocking + TDD Guard |
| Adversarial Review | `@reviewer` + `@fact-checker` Generator-Critic pattern |
| Decision Log | Recording the rationale for auto-approval decisions |
| Context Preservation | Cross-session memory preservation + Knowledge Archive + RLM pattern |

> Inheritance is not optional — it is **structural**. The child does not "reference" the parent's DNA, it **embeds** it. Details: `soul.md §0`.

> **12→9 Mapping**: Of the 12 components in soul.md §0, the 9 above are structurally embedded in the child as `inherited_dna`. The remaining 3 — Design Principles P1-P4 (included in the Absolute Criteria), Sisyphus/Error→Resolution (behavioral pattern, not a structure), and RLM theory (theoretical foundation, not a structure) — are implicitly reflected in the child as internal mechanisms of the parent organism, but are not separated as distinct `inherited_dna` items. soul.md itself is a meta-document (the definition of inheritance), so it is not an inheritance target.

### Basic Workflow Structure

Every workflow consists of three stages:

1. **Research** — Information gathering and analysis
2. **Planning** — Plan formulation, structuring, human review/approval
3. **Implementation** — Actual execution and deliverable generation

Each stage specifies:
- The task performed (Task)
- The responsible agent
- Data pre-processing / post-processing
- Deliverable (Output)
- Human intervention point (if applicable)

---

## 2. Absolute Criteria

> **These are the top-level rules applied to every design, implementation, and modification decision in this project.**
> They sit above all principles, guidelines, and conventions below.
> Whatever principle it is, if it conflicts with an Absolute Criterion, the Absolute Criterion wins.

### Absolute Criterion 1: Quality of the Final Deliverable

> **Speed, token cost, workload, and length limits are completely ignored.**
> The only criterion for every decision is the **quality of the final deliverable**.
> Rather than making things fast by reducing steps, we choose the direction that raises quality even if that means adding steps.

Applied examples:
- If quality rises with more workflow stages → add stages
- If using more agents raises quality → add agents
- If repeated verification stages improve the deliverable → allow repetition

### Absolute Criterion 2: Single-File SOT + Hierarchical Memory Structure

> **Under the design of a single-file SOT (Single Source of Truth) + hierarchical memory structure, no data inconsistency occurs even when dozens of agents operate simultaneously.**

Design rules:
- **State concentration**: All shared state of a workflow is concentrated in a **single file** (e.g., `state.json`, `state.yaml`). Do not scatter state across multiple files.
- **Single write point**: Only the Orchestrator (or one designated agent) has write permission to the SOT file. Other agents access it read-only and produce their results as separate output files.
- **Conflict prevention**: Do not design structures in which multiple agents modify the same file simultaneously.

```
Bad:  Agent A → directly modifies state.json
      Agent B → directly modifies state.json  → data conflict

Good: Agent A → produces output-a.md → reports to Orchestrator
      Agent B → produces output-b.md → reports to Orchestrator
      Orchestrator → merges into state.json  → single write point
```

### Absolute Criterion 3: Code Change Protocol (CCP)

> **Before writing, modifying, adding, or deleting code, you must internally perform the 3 steps below.**
> Skipping this protocol is a violation of the Absolute Criteria.

If Absolute Criterion 1 (Quality) defines "what we optimize for," and Absolute Criterion 2 (SOT) defines "how we structure data," then Absolute Criterion 3 defines **"how we behave when changing code."** High-quality code emerges from a rigorous process that analyzes dependencies, coupling, and ripple effects of changes in advance.

#### Coding Anchor Points (CAP-1~4)

If CCP defines "what to perform" (procedure), then CAP defines **"what attitude to perform with"** (mindset). Every step of CCP is performed while internalizing the 4 anchor points below.

- **CAP-1: Think Before Coding** — Do not assume. Do not modify code before reading it; surface trade-offs when they exist; ask when unclear.
- **CAP-2: Simplicity First** — Write only the minimum code needed to satisfy the current requirement. Do not create speculative features, premature abstractions, or unnecessary helpers.
- **CAP-3: Goal-Based Execution** — Define success criteria before implementation, and verify after (e.g., tests, manual checks).
- **CAP-4: Surgical Changes** — Perform only the requested change. Do not "improve" unrelated code, and do not add comments, types, or documentation to code you did not touch.

> CAP is a subordinate set of attitude norms under CCP, so when it conflicts with Absolute Criterion 1 (Quality), quality wins. Example: when CAP-2 (Simplicity) undermines quality — complexity required for quality is allowed.

**Step 1 — Understand Intent:**
- Have you accurately understood the implementation the user requested? You should be able to explain it clearly in 1-2 sentences.
- Have you accurately understood the purpose of the change (bug fix, refactoring, performance, feature addition, etc.) and the constraints (compatibility preservation, tech stack, etc.)?

**Step 2 — Ripple Effect Analysis:**

Investigate the impact that writing new code or modifying existing code has on the entire codebase:
- **Direct dependencies**: Functions / classes / modules / files where the target is defined
- **Call relationships**: Other code that calls this code, or that this code calls
- **Structural relationships**: Inheritance / implementation (inheritance, interface), composition, association / reference
- **Data model / schema**: Types / fields / validation logic that must change together
- **Test code**: Unit tests, integration tests, snapshot tests, etc.
- **Configuration / environment / build**: config, DI settings, routing, dependency injection, etc.
- **Documentation / comments / API specs**: comments, README, API documents, type definitions, etc.

Investigate at an expert level: "Since we're changing here, how far can this change ripple?" If there are highly coupled areas (tight coupling, change coupling, possibility of shotgun surgery), you **must** flag them in advance and discuss with the user.

**Step 3 — Change Plan:**
- Before updating the actual related code, propose a step-by-step change plan:
  - Step 1: Which file / class / function to modify first
  - Step 2: What changes to propagate to downstream dependencies / callers
  - Step 3: How to align tests / docs / configuration
- If you see a refactoring opportunity toward a better structure from the perspective of reducing coupling / increasing cohesion, propose it along with the plan (execute only after user approval).

**Proportionality Rule — Always perform the protocol, but scale analysis depth to the scope of the change:**

| Scope | Criterion | Depth Applied |
|-------|-----------|---------------|
| **Minor** | Typos, comments, formatting, logic-irrelevant changes | Step 1 only — confirm "no ripple effect" in one sentence and execute immediately |
| **Standard** | Function / logic changes, file addition / deletion | Full 3 steps |
| **Large-scale** | Architecture, public API, cross-cutting changes | Full 3 steps + **mandatory** prior user approval |

Applied examples:

```
Bad:  "User requests function modification → only modifies that function → 6 callers hit runtime errors"
Good: "User requests function modification → checks 6 call sites → reports impact scope → proposes step-by-step change plan → executes after approval"
```

**Communication Rules:**
- Avoid unnecessarily verbose theoretical explanations; focus on actual code and concrete steps.
- Add brief reasons for important design choices.
- Even when parts are ambiguous, do not avoid the work — state "reasonable assumptions" explicitly and propose the best design.

### Priority Among Absolute Criteria

> **Absolute Criterion 1 (Quality) is the highest. Absolute Criterion 2 (SOT) and Absolute Criterion 3 (CCP) are co-equal means to guarantee quality.**

```
Absolute Criterion 1 (Quality) — Highest. The reason every criterion exists.
  ├── Absolute Criterion 2 (SOT) — Means of guaranteeing data integrity
  └── Absolute Criterion 3 (CCP) — Means of guaranteeing code-change quality
```

Absolute Criteria 2 (SOT) and 3 (CCP) operate on different dimensions, so direct conflict between them is unlikely. Whichever criterion it is, when it conflicts with Absolute Criterion 1 (Quality), quality wins. Both SOT and CCP are **means** of guaranteeing quality, not **ends** that constrain quality.

Conflict scenarios and resolutions:
- The SOT single write point causes an information bottleneck and agents work with stale data → **allow direct reference between agents' outputs** (adjust the SOT structure)
- State complexity of the SOT grows due to added stages for quality improvement → **accept it** (Absolute Criterion 1 > 2)
- SOT is unnecessary for fully independent parallel work (no shared state between agents) → **allow lightweight SOT** (document the rationale)
- Full CCP analysis is excessive overhead for trivial changes → **apply the Proportionality Rule** (Step 1 only for minor changes)

---

## 3. Design Principles

These are subordinate principles under the Absolute Criteria.

### P1. Data Refinement for Accuracy

Passing large data directly to AI drops accuracy through noise.

- Specify **pre-processing** at each stage: remove noise before handing off to the agent
- Specify **post-processing** at each stage: refine the deliverable before passing to the next stage
- Relationships computable in code are pre-processed → the AI focuses on judgment and analysis

```
Bad:  "Pass the entire collected HTML of the web page to the agent"
Good: "Extract only the body text via a Python script → pass only the essential text to the agent"
```

### P2. Expertise-Based Delegation Structure

Maximize quality by delegating each task to the specialized agent that can best perform it. The Orchestrator coordinates overall quality, while specialized agents focus deeply on their respective domains.

```
Orchestrator (quality coordination + flow management)
  ├→ Agent A: Specialized research (optimized for the domain)
  ├→ Agent B: In-depth analysis (focused only on analysis)
  └→ Agent C: Verification and quality gate
```

#### Orchestrator Role Definition

**Orchestrator = main Claude session**. It is not a separate agent file; the main session executing the workflow plays the Orchestrator role. In `(team)` stages, **the Orchestrator also serves as the Team Lead**.

| Role | Actor | SOT Write | Start Time |
|------|-------|-----------|------------|
| Orchestrator | Main Claude session | **Writable** (sole) | At workflow start |
| Team Lead | Orchestrator (same entity) | **Writable** | On entering a `(team)` stage |
| Sub-agent | Created via the `Task` tool | **Read-only** | When Orchestrator invokes |
| Teammate | Created via `Task` + `TeamCreate` | **Read-only** | When Team Lead assigns |

#### Sub-agent Invocation Protocol

Standard protocol for the Orchestrator to invoke a Sub-agent (`@translator`, `@reviewer`, `@fact-checker`):

**1. How to invoke**: specify the agent name via the `subagent_type` parameter of the `Task` tool
```
Task(subagent_type="translator", prompt="...", ...)
```

**2. Context that must be included in the prompt**:
- Workflow step number (step N)
- Input deliverable file paths (absolute paths)
- Verification criteria for that step (if any)
- SOT `outputs.step-N` path (where to save the deliverable)
- Reference file paths (glossary.yaml, previous step deliverables, etc.)

**3. Receiving results**: when the Sub-agent exits, the `Task` tool returns the result.
- The Orchestrator checks that the deliverable file was created on disk
- Runs the P1 validation scripts (validate_review.py, validate_translation.py, etc.)
- Records the path in SOT `outputs.step-N` (performed by the Orchestrator)

**4. `(team)` stage Task Lifecycle**:
```
Team Lead (= Orchestrator)
  1. TeamCreate → records SOT active_team
  2. TaskCreate (subject, description, owner=@teammate)
  3. Task(subagent_type, team_name, ...) → creates Teammate
  4. Teammate: performs work → L1 self-verification → L1.5 pACS self-scoring
  5. Teammate: SendMessage (report + pACS score) → TaskUpdate (completed)
  6. Team Lead: receives report → L2 comprehensive verification → updates SOT
  7. TeamDelete → SOT active_team → moves to completed_teams
```

**Dense Checkpoint Pattern (DCP)**: Insert intermediate checkpoints (CP-1/2/3) into Tasks with turn count > 10. Details: `references/claude-code-patterns.md §DCP`

### P3. Resource Accuracy

For stages that require images, files, or external resources, specify exact paths. Placeholders may not be omitted.

### P4. Question Design Rules

When asking the user questions:
- At most 4 questions
- Each question offers roughly 3 options
- If there is no ambiguity, proceed without questions

---

## 4. Project Structure

```
AgenticWorkflow/
├── CLAUDE.md          ← Claude Code-specific directive
├── AGENTS.md          ← This file (model-agnostic common directive)
├── README.md          ← Project introduction
├── AGENTICWORKFLOW-USER-MANUAL.md              ← User manual
├── AGENTICWORKFLOW-ARCHITECTURE-AND-PHILOSOPHY.md  ← Design philosophy and architecture overview
├── DECISION-LOG.md          ← Project design decision log (ADR)
├── COPYRIGHT.md          ← Copyright
├── .claude/
│   ├── settings.json          ← Hook settings (Setup + SessionEnd)
│   ├── agents/                ← Sub-agent definitions
│   │   ├── translator.md     (English→Korean translation specialist — glossary-based terminology consistency)
│   │   ├── reviewer.md       (Adversarial Review — critical analysis of code/deliverables, read-only)
│   │   └── fact-checker.md   (Adversarial Review — external fact verification, web access)
│   ├── commands/              ← Slash Commands
│   │   ├── install.md         (Setup Init validation result analysis — /install)
│   │   └── maintenance.md     (Setup Maintenance health check — /maintenance)
│   ├── hooks/scripts/         ← Context Preservation System + Setup Hooks + Safety Hooks
│   │   ├── context_guard.py   (Hook unified dispatcher — single entry point for 4 events)
│   │   ├── _context_lib.py    (shared library — parsing, generation, SOT capture, Smart Throttling, Autopilot state reading/validation, ULW detection/compliance verification, centralization of truncation constants, sot_paths() path unification, multi-stage transition detection, decision-quality tag ordering, Error Taxonomy 12 patterns + Resolution matching, Success Patterns (extracting successful Edit/Write→Bash sequences), IMMORTAL-aware compression + audit trail, E5 Guard centralization (is_rich_snapshot + update_latest_with_guard), Knowledge Archive integration (archive_and_index_session — partial failure isolation), path tag extraction (extract_path_tags), KI schema validation (_validate_session_facts — ensuring RLM-required keys), SOT schema validation (validate_sot_schema — structural integrity of workflow state.yaml verified across 8 items: S1-S6 basic + S7 pacs 5 fields (dimensions, current_step_score, weak_dimension, history, pre_mortem_flag) + S8 active_team 5 fields (name, status (partial|all_completed), tasks_completed, tasks_pending, completed_summaries)), Adversarial Review P1 validation (validate_review_output R1-R5, parse_review_verdict, calculate_pacs_delta, validate_review_sequence), Translation P1 validation (validate_translation_output T1-T7, check_glossary_freshness T8, verify_pacs_arithmetic T9 generic, validate_verification_log V1a-V1c), Predictive Debugging P1 (aggregate_risk_scores + validate_risk_scores RS1-RS6 + _RISK_WEIGHTS 13 weights + _RECENCY_DECAY_DAYS decay), pACS P1 validation (validate_pacs_output PA1-PA6 — structural integrity of pACS log: file existence, minimum size, dimension scores, Pre-mortem, min() arithmetic, Color Zone), L0 Anti-Skip Guard (validate_step_output L0a-L0c — deliverable file existence + minimum size + non-empty), Team Summaries KI archive (_extract_team_summaries — SOT active_team.completed_summaries → preserved in KI), Abductive Diagnosis Layer (diagnose_failure_context pre-evidence collection + validate_diagnosis_log AD1-AD10 post-validation + _extract_diagnosis_patterns KA archiving + Fast-Path FP1-FP3 + hypothesis priority H1/H2/H3), module-level regex compilation (9+8+8+4+5 patterns — once per process))
│   │   ├── save_context.py    (save engine)
│   │   ├── restore_context.py (restore — RLM pointer + completion/Git state + Predictive Debugging risk score cache generation)
│   │   ├── update_work_log.py (work log accumulation — tracking 9 tools)
│   │   ├── generate_context_summary.py (incremental snapshot + Knowledge Archive + E5 Guard + Autopilot Decision Log safety net + ULW Compliance safety net)
│   │   ├── setup_init.py      (Setup Init — infrastructure health verification + SOT write pattern validation (P1 hallucination containment), --init trigger)
│   │   ├── setup_maintenance.py (Setup Maintenance — periodic health check, --maintenance trigger)
│   │   ├── block_destructive_commands.py (PreToolUse Safety Hook — blocks dangerous commands (P1 hallucination containment), blocks with exit code 2 + Claude self-correction)
│   │   ├── block_test_file_edit.py  (PreToolUse TDD Guard — blocks test file modification (.tdd-guard toggle), blocks with exit code 2 + directs to implementation code modification)
│   │   ├── predictive_debug_guard.py (PreToolUse Predictive Debug — warns about risky files based on error history, exit code 0 warning only)
│   │   ├── output_secret_filter.py  (PostToolUse secret detection — 3-tier extraction (tool_response→file read→transcript), 25+ regex patterns, 2-pass scanning (raw + base64/URL), fcntl-locked audit log, exit code 0 warning only)
│   │   ├── security_sensitive_file_guard.py (PostToolUse security-sensitive file warning — .env/PEM/credentials/cloud/K8s/terraform, etc. 12 patterns, session dedup, exit code 0 warning only)
│   │   ├── diagnose_context.py  (Abductive Diagnosis pre-evidence collection — generates an evidence bundle on quality gate FAIL, manually invoked by the Orchestrator)
│   │   ├── query_workflow.py    (workflow observability — 4 modes: dashboard/weakest/retry/blocked, P1 SOT schema validation + context-aware pACS extraction)
│   │   ├── validate_pacs.py    (pACS P1 validation + L0 Anti-Skip Guard — PA1-PA7, standalone script, JSON output)
│   │   ├── validate_review.py (Adversarial Review P1 validation — R1-R5, standalone script, JSON output)
│   │   ├── validate_translation.py (Translation P1 validation — T1-T9 + glossary validation, JSON output)
│   │   ├── validate_verification.py (Verification Log P1 validation — V1a-V1c structural integrity, JSON output)
│   │   ├── validate_diagnosis.py (Abductive Diagnosis P1 post-validation — AD1-AD10, JSON output)
│   │   ├── validate_traceability.py (Cross-Step Traceability P1 validation — CT1-CT5, JSON output)
│   │   ├── validate_domain_knowledge.py (Domain Knowledge P1 validation — DK1-DK7, JSON output)
│   │   ├── validate_workflow.py (DNA inheritance P1 validation — W1-W8, JSON output)
│   │   ├── validate_retry_budget.py (Retry Budget P1 validation — RB1-RB3 retry budget decision (ULW-aware), JSON output)
│   │   ├── _test_secret_filter.py   (output_secret_filter tests — 44 cases)
│   │   ├── _test_sensitive_file_guard.py (security_sensitive_file_guard tests — 44 cases)
│   │   └── _test_block_destructive.py (block_destructive_commands tests — 43 cases)
│   ├── context-snapshots/     ← runtime snapshots (gitignored)
│   └── skills/
│       ├── workflow-generator/   ← workflow design and generation
│       │   ├── SKILL.md          (skill definition + Absolute Criteria)
│       │   └── references/       (implementation patterns, templates, document analysis guide)
│       └── doctoral-writing/     ← doctoral-level academic writing
│           ├── SKILL.md          (skill definition + Absolute Criteria)
│           └── references/       (checklists, common errors, revision examples, discipline-specific guides)
├── prompt/              ← prompt materials
│   ├── crystalize-prompt.md      (prompt compression techniques)
│   ├── distill-partner.md        (essence extraction and optimization)
│   └── crawling-skill-sample.md  (crawling skill sample)
└── coding-resource/     ← reference materials
```

### Context Preservation System

An automatic save/restore system that prevents the loss of work context when the context window is exhausted, the session is reset, or the context is compacted.

**Core principles:**
- RLM pattern applied: work history is persisted as an **external memory object** (MD file), and restored in a new session via pointers
- P1 principle followed: transcript parsing and statistics are performed deterministically by Python code. The AI focuses only on semantic interpretation
- Absolute Criterion 2 followed: the SOT file (`state.yaml`) is accessed **read-only**. Snapshots are stored in a separate directory (`context-snapshots/`)
- **Knowledge Archive**: Cross-session knowledge accumulation — session facts are deterministically extracted and accumulated in `knowledge-index.jsonl`. Recorded by both the Stop hook and SessionEnd/PreCompact, guaranteeing 100% indexing of the session. Each entry includes completion_summary (tool success/failure), git_summary (change status), session_duration_entries (session length), phase (session phase), phase_flow (multi-stage transition flow), primary_language (primary file extension), error_patterns (Error Taxonomy 12-pattern classification + resolution matching), tool_sequence (RLE-compressed tool sequence), final_status (success/incomplete/error/unknown), tags (path-based search tags — CamelCase/snake_case split + extension mapping). AI searches programmatically with Grep (RLM pattern)
- **Resume Protocol**: Snapshot includes deterministic restoration instructions — list of modified/referenced files, session metadata, completion state (tool success/failure), Git change state. **Dynamic RLM query hints**: Based on tags extracted from the modified file paths (`extract_path_tags()`) and error information, session-specific tailored Grep query examples are auto-generated. Guarantees a floor level for restoration quality
- **Autopilot runtime reinforcement**: When Autopilot is active, the snapshot includes an Autopilot state section (IMMORTAL priority), and on session restoration execution rules are injected into context. The Stop hook detects and compensates for missing Decision Logs
- **ULW mode detection / preservation**: `detect_ulw_mode()` detects the `ulw` keyword in the transcript using word-boundary regex. When active, the snapshot includes a ULW state section (IMMORTAL priority), and SessionStart injects the 3 reinforcement rules (Intensifiers) into context. `check_ulw_compliance()` deterministically verifies compliance. Tagged as `ulw_active: true` in the Knowledge Archive
- **Decision-quality tag ordering**: The "key design decisions" section of the snapshot is ordered `[explicit]` > `[decision]` > `[rationale]` > `[intent]`, so that high-signal decisions are placed first in the 15 slots. Comparison / trade-off / selection patterns are also extracted
- **IMMORTAL-aware compression**: When the snapshot exceeds size, IMMORTAL sections are preserved with priority and non-IMMORTAL content is truncated first. In extreme cases, the beginning of IMMORTAL text is still preserved. **Compression audit trail**: The number of characters removed in each compression Phase is recorded at the end of the snapshot as an HTML comment (`<!-- compression-audit: ... -->`) (per-Phase deltas for Phases 1~7 + final size)
- **Error Taxonomy**: Tool errors are classified into 12 patterns (file_not_found, permission, syntax, timeout, dependency, edit_mismatch, type_error, value_error, connection, memory, git_error, command_not_found). Negative-lookahead and qualifier matching are applied to prevent false positives. Recorded in the error_patterns field of the Knowledge Archive. **Error→Resolution matching**: Successful tool invocations within 5 entries after an error are detected via file-aware matching and recorded in the `resolution` field (tool name + file name). Cross-session exploration of resolution patterns is possible via `Grep "resolution" knowledge-index.jsonl`
- **System command filtering**: In the snapshot's "current work" section, system commands such as `/clear`, `/help` are filtered out so that only actual work intent is captured
- **Crash-safe writes**: The atomic write pattern (temp → rename) is applied to all file writes (snapshots, archives, log cleanup). Prevents partial writes on process crash
- **P1 Hallucination Prevention**: Tasks that must be 100% accurate repeatedly are enforced by Python code. (1) **KI schema validation**: `_validate_session_facts()` guarantees the presence of RLM-required keys (session_id, tags, final_status, etc. — 10 items) right before writing to knowledge-index — fills with safe defaults if missing. (2) **Partial failure isolation**: In `archive_and_index_session()`, failure to write the archive file does not block knowledge-index update — protects the core RLM asset. (3) **SOT write pattern validation**: `_check_sot_write_safety()` in `setup_init.py` detects the coexistence of SOT file names + write patterns in Hook scripts, based on AST function boundaries. (4) **SOT schema validation**: `validate_sot_schema()` validates the structural integrity of the workflow state.yaml across 8 items (S1-S6 basic + S7 pacs 5 fields + S8 active_team 5 fields). (5) **Adversarial Review P1 validation**: `validate_review_output()` R1-R5, `parse_review_verdict()`, `calculate_pacs_delta()`, `validate_review_sequence()` deterministically guarantee review quality

**Data flow:**

```
Work in progress ─→ [PostToolUse] update_work_log.py ─→ accumulates work_log.jsonl (tracking 9 tools)
                 ├→ [PostToolUse] output_secret_filter.py ─→ secret detection on Bash|Read output (3-tier extraction, 25+ patterns, standalone)
                 └→ [PostToolUse] security_sensitive_file_guard.py ─→ Edit|Write sensitive file warning (standalone)
                                                         │ (when token > 75%)
                                                         ↓
Response complete ─→ [Stop] generate_context_summary.py ─→ saves latest.md (30s throttling)
                                                         │        + accumulates knowledge-index.jsonl
                                                         │        + archives to sessions/
                                                         │        + E5 Empty Snapshot Guard
                                                         ↓
Session end/compact ─→ [SessionEnd/PreCompact] save_context.py ─→ saves latest.md
                                                         │        + accumulates knowledge-index.jsonl
                                                         │        + archives to sessions/
                                                         ↓
New session start ──→ [SessionStart] restore_context.py ───────→ emits pointer + summary + completion state + Git state
                                                         AI restores the full content via Read tool
```

---

## 5. Implementation Element Mapping

When designing a workflow, combine the implementation elements below. Tools may use different names, but the concepts are the same.

| Workflow Element | Concept | Selection Criterion |
|------------------|---------|--------------------|
| **Specialized agent** | A single agent focused on one specific domain | When keeping deep context is the key to quality |
| **Agent group** | Multiple agents working independently in parallel | When multi-perspective analysis / cross-verification raises quality |
| **Human intervention point** | User interaction for review / approval / selection | When judgment that cannot be automated is required |
| **Automated verification** | Quality gate, format check, security check | For automating repeated verifications |
| **Reusable module** | Encapsulates domain knowledge and repeated patterns | For applying validated patterns consistently |
| **External integration** | API, DB, external service integration | When external data/functionality is needed |
| **Dynamic question collection** | Collects information during execution via structured questions to the user | Applies P4 rule. When options cannot be predefined and dynamic judgment is needed |
| **Task allocation / tracking** | Task creation, allocation, dependency, progress tracking when using an agent group | Does not replace SOT. When coordinating work across agents is required |

> **The sole criterion for agent selection is "which structure best raises the quality of the final deliverable."**
> Do not choose an agent group just because parallelism is fast.
> Do not choose a specialized agent just because it uses fewer tokens.

#### Specialized Agent vs Agent Group — Quality Judgment Matrix

Decide the structure along 5 quality factors. "Because it's faster" or "because it's cheaper" is not a criterion:

| Quality Factor | Specialized Agent advantage | Agent Group advantage | Judgment Question |
|----------------|----------------------------|----------------------|------------------|
| **Context depth** | When results of prior stages must be deeply referenced | When each task requires independent expertise | "Does quality drop if nuance from the previous stage is lost?" |
| **Cross-verification** | When a single viewpoint ensures consistency | When multi-viewpoint analysis removes bias | "Does another perspective raise the credibility of the result?" |
| **Deliverable consistency** | When uniform style / tone matters | When each deliverable is independently complete | "Is tone inconsistency across deliverables a quality issue?" |
| **Error isolation** | When errors must be caught in the full context | When a failed task must not affect others | "Does one failure contaminate the whole?" |
| **Information transfer loss** | When there is high risk of nuance loss when transferred via files | When structured data transfer is sufficient | "Does contextual summarization cause information loss?" |

**Judgment rules:**
1. If specialized-agent advantage wins on 3 or more of the 5 factors → **Specialized agent**
2. If agent-group advantage wins on 3 or more factors → **Agent group**
3. Tie (2:2 + 1 undecidable) → **Context depth** acts as tiebreaker (context retention is generally safer)
4. When in doubt → **Specialized agent** (safe default — guarantees context retention)

#### Model Level Selection — Quality-Based Judgment

| Model Level | Selection Criterion | Fitting Tasks |
|-------------|---------------------|--------------|
| **Top tier** | Core tasks — directly impact final quality | Core analysis, final writing, strategic judgment, code architecture |
| **Stable tier** | Repetitive tasks — patterns are established | Data collection, format conversion, standardized classification |
| **Auxiliary tier** | Simple tasks — minimal judgment | Format validation, simple filtering, label extraction |

**Judgment procedure:**
1. How directly does this task affect the quality of the final deliverable?
2. Is the quality difference between model levels meaningful?
   - If meaningful → higher-tier model
   - If not meaningful → lower-tier model is permitted
3. When in doubt → **higher-tier model** (quality-guarantee principle — Absolute Criterion 1)

### 5.1 Autopilot Mode

A mode that enables uninterrupted workflow execution by automatically approving **human-in-the-loop** points.

**Core principles:**
- Autopilot only performs **automatic approval** of human intervention points
- Every workflow stage is **fully executed** — stage skipping is forbidden
- Every deliverable is produced at **full quality** — abbreviation is forbidden
- Automated verification (Hook exit code 2) **still blocks** under Autopilot

**Target distinction:**

| Mechanism | Autopilot Behavior | Rationale |
|-----------|--------------------|-----------|
| Human intervention point `(human)` | Auto-approve — select the quality-maximizing default | AI proxies human judgment |
| Dynamic question collection | Auto-respond — select the quality-maximizing option | AI proxies human selection |
| Automated verification `(hook)` exit code 2 | **No change — still blocks** | Deterministic verification; not a target for AI proxying |

**Anti-Pattern:**
1. Autopilot ≠ stage skipping: every stage is fully executed in sequence
2. Autopilot ≠ abbreviated output: every agent produces deliverables of the same quality and length as it would under human review

**Anti-Skip Guard (runtime verification):**

The deterministic verification performed by the Orchestrator on each stage completion:
1. Is the deliverable file recorded as a path in SOT `outputs`?
2. Does that file exist on disk?
3. Is the file size ≥ 100 bytes (ensuring meaningful content)?

> In Claude Code's Hook system, the `validate_step_output()` function of `_context_lib.py` performs this verification deterministically. In other tools, implement equivalent file validation logic.

**SOT record:**
```yaml
workflow:
  name: "my-workflow"
  current_step: 3
  status: "running"
  outputs:
    step-1: "research/raw-contents.md"
    step-2: "analysis/insights-list.md"
  autopilot:
    enabled: true
    activated_at: "ISO-8601"
    auto_approved_steps: [3, 6]
```

- `autopilot.enabled`: Boolean — whether Autopilot is active
- `autopilot.auto_approved_steps`: list of step numbers that were auto-approved
- `outputs`: per-step deliverable paths — the targets verified by Anti-Skip Guard
- Auto-approval decisions are recorded in a separate log file (`autopilot-logs/step-N-decision.md`) (transparency guarantee)
- Decision Log standard template: see Claude Code's `references/autopilot-decision-template.md`

**Runtime reinforcement (Claude Code implementation):**

| Layer | Mechanism | Reinforcement |
|-------|-----------|---------------|
| **Hook** | SessionStart context injection | On session start/restore, injects the Autopilot execution rules + previous-stage verification results into the prompt |
| **Hook** | Snapshot Autopilot section | Preserves Autopilot state at IMMORTAL priority across session boundaries |
| **Hook** | Stop Decision Log safety net | Detects auto-approval patterns → compensates for missing Decision Logs |
| **Hook** | PostToolUse progress tracking | Records step progress in work_log via the `autopilot_step` field |
| **Prompt** | Execution Checklist | Mandatory actions for the start / execution / completion of each stage defined below (Claude Code details: `docs/protocols/autopilot-execution.md`) |

> The Hook layer accesses SOT **read-only** (Absolute Criterion 2).

**Autopilot Execution Checklist (tool-common):**

Mandatory actions that must be performed per stage when executing a workflow under Autopilot in any tool:

| Timing | Mandatory Action |
|--------|------------------|
| **Before stage start** | Check SOT `current_step`, verify that previous-stage deliverable files exist and are non-empty, read `Verification` criteria |
| **During stage execution** | Fully execute every task (no abbreviation — Absolute Criterion 1), produce full-quality deliverables |
| **After stage completion** | Save deliverable to disk, self-verify against `Verification` criteria, re-execute only the failed parts on failure (up to 10 times, 15 when ULW is active — §5.1.1), record the path in SOT `outputs`, `current_step` +1, create Decision Log |
| **Absolutely forbidden** | Incrementing `current_step` by 2 or more at once, proceeding without a deliverable, abbreviating "because it's automated," proceeding while Verification is FAIL |

> **Claude Code details**: `docs/protocols/autopilot-execution.md` defines additional Claude Code-specific checklists for `(team)` stages, translation, Hook integration, etc.

**Activation:** Default is inactive (interactive). Activated by specifying `Autopilot: enabled` in the workflow Overview or by user instruction at execution time. Can be toggled during execution.

### 5.1.1 ULW Mode (Claude Code)

**ULW (Ultrawork)** is a **thoroughness-intensity overlay** orthogonal to Autopilot. It is activated by including `ulw` in the prompt.

- **Autopilot** = automation axis (HOW) — skip `(human)` approvals
- **ULW** = thoroughness axis (HOW THOROUGHLY) — nothing omitted, perfect completion through error resolution

**2x2 matrix:**

|  | **ULW OFF** | **ULW ON** |
|---|---|---|
| **Autopilot OFF** | Standard interactive | Interactive + Sisyphus Persistence (3 retries) + mandatory task decomposition |
| **Autopilot ON** | Standard automated workflow | Automated workflow + Sisyphus reinforcement (3 retries) + team thoroughness |

**3 reinforcement rules (Intensifiers):**
1. **I-1. Sisyphus Persistence** — Up to 3 retries, each with a different approach. 100% completion, or report impossibility.
2. **I-2. Mandatory Task Decomposition** — TaskCreate → TaskUpdate → TaskList mandatory
3. **I-3. Bounded Retry Escalation** — No more than 3 retries on the same target (quality gates have a separate budget); when exceeded, escalate to the user

**Deterministic reinforcement:** A Python Hook deterministically verifies compliance with the 3 reinforcement rules (Compliance Guard). On violation, a warning is recorded in the IMMORTAL section of the snapshot.

> **Combination rule**: ULW **reinforces** Autopilot — the Autopilot quality-gate retry limit is raised 10→15. Safety Hook blocks are always respected.

Details: `docs/protocols/ulw-mode.md`

### 5.1.5 Pre-Invocation Validation (Sub-agent Fork Context)

Every Sub-agent invocation is preceded by fork context validation to ensure deterministic fork decisions and maintain audit traceability.

**Core procedure**:

Before `Task(subagent_type=...)` invocation, the Orchestrator calls the pre-invocation validator:

```python
decision = validate_and_set_fork_context(subagent_name)
```

The validator performs 3 steps:

1. **Check Categorization Rule**: Look up the sub-agent in the CATEGORIZATION dict
   - Known rule (always_fork, always_fresh, team_decision) → proceed
   - Unknown agent → raise RuntimeError (blocks invocation)

2. **Record Decision**: Append to Decision Log with timestamp, rule, and rationale

3. **Return Context**: Pass the fork decision to the Task invocation

**Implementation file**: `.claude/hooks/scripts/pre_subagent_invocation.py`

**Validation rules**:

| Sub-agent | Fork Decision | Rationale |
|-----------|---------------|-----------|
| **@translator** | Always Fork | Glossary persistence (per-fork state) → isolation required |
| **@reviewer** | Always Fork | Independent L2 calibration → isolated context |
| **@fact-checker** | Always Fresh | Stateless verification logic → fresh analysis |
| **[New agent TBD]** | Team Decision (first invocation only) | Requires explicit ADR + context-depth heuristic |

**Decision Logic (3-Tier Hierarchy)**:

```
TIER 1: Deterministic
  if pacs_score < 70 → fork=true (automatic recovery)

TIER 2: Explicit Category
  if agent in CATEGORIZATION → apply rule

TIER 3: Default
  if unknown → team_decision (require ADR before 2nd invocation)
```

**SOT Recording**: Fork decision recorded in `state.yaml` under `steps[step-N].invocations[]` (Orchestrator writes only).

### 5.2 English-First Execution and Translation Protocol + Sub-agent Categorization

When **executing** a workflow, every agent **works in English** and produces **deliverables in English**. Because AI performs best in English, English-first execution is a direct realization of **Absolute Criterion 1 (Quality)**.

#### Language Boundaries

| Activity | Language | Rationale |
|----------|----------|-----------|
| Workflow design (workflow-generator skill) | Korean | Conversation with the user |
| Agent definitions (`.claude/agents/*.md`) | English | Maximize agent prompt quality |
| Workflow execution (agent work) | **English** | Maximize AI performance |
| Deliverable translation | English → Korean | `@translator` specialized sub-agent |
| SOT records | Language-agnostic | Structural data such as paths and numbers |

> **Design documents (`workflow.md`) remain in Korean.** Since it is a blueprint that the user reads and reviews, it uses the user's language. Language transitions occur at the **design → execution** boundary.

#### Determining Translation Targets

Not every stage requires translation:

| Deliverable Type | Translate? | Example |
|------------------|-----------|---------|
| Text content (analysis, report, summary) | **Translate** | `.md`, `.txt` |
| Code file | Do not translate | `.py`, `.js`, `.ts` |
| Data file | Do not translate | `.json`, `.csv` |
| Config file | Do not translate | `.yaml` config, `.env` |

When designing a workflow, specify `Translation: @translator` or `Translation: none` per stage to decide whether translation applies.

#### Translation Execution Protocol

**Rationale for sub-agent selection**: Because terminology consistency and context accumulation are key to translation quality, a **specialized Sub-agent** has a quality advantage over an agent group (factors "context depth" + "deliverable consistency" in the §5 quality matrix).

**Execution order**:

```
Step N English deliverable complete
  → record in SOT outputs.step-N + Anti-Skip Guard verification
  → invoke @translator sub-agent (only for stages with Translation: @translator)
    ① Read translations/glossary.yaml (terminology — RLM external persistent state)
    ② Read the full English source
    ③ Fully translate using established terms (no abbreviation — Absolute Criterion 1)
    ④ Self-review: compare against the source, check terminology consistency
    ⑤ Update glossary.yaml (add new terms)
    ⑥ Generate *.ko.md file
  → record in SOT outputs.step-N-ko
  → confirm the translation file exists and is non-empty
  → P1 validation: python3 .claude/hooks/scripts/validate_translation.py --step N --project-dir . --check-pacs --check-sequence
  → proceed to Step N+1
```

#### Terminology Glossary

`translations/glossary.yaml` is the translation agent's **persistent external memory** (RLM pattern). Together with `memory: project` (ADR-051), it forms a 2-layer memory: glossary.yaml = explicit terminology mapping, persistent memory = implicit style/tone pattern accumulation.

```yaml
# translations/glossary.yaml
terms:
  "Single Source of Truth": "단일 소스 오브 트루스(Single Source of Truth)"
  "Anti-Skip Guard": "Anti-Skip Guard"  # kept in English
  "workflow step": "워크플로우 단계"
```

**Architectural consistency**:
- The glossary is **not an SOT** — it is a local work file of the translation agent
- Not managed by the Orchestrator — managed by the translation agent itself
- No concurrent-write risk — translation runs sequentially (once after each stage)
- Hierarchical memory: glossary.yaml (explicit terminology) + `memory: project` (implicit experience accumulation) as 2 layers (ADR-051)

#### SOT Recording Rules

```yaml
outputs:
  step-1: "research/raw-contents.md"          # English source
  step-1-ko: "research/raw-contents.ko.md"    # Korean translation
  step-2: "data/processed.json"               # translation unnecessary → no -ko
  step-3: "analysis/report.md"
  step-3-ko: "analysis/report.ko.md"
```

- The `step-N-ko` key follows the suffix convention: it is automatically skipped by Anti-Skip Guard's `.isdigit()` guard
- Anti-Skip Guard validates only `step-N` (the English source) → translation verification is performed by the Orchestrator checklist
- Stages without translation do not generate `-ko` keys

#### Translation in `(team)` Stages

The translation targets in agent-group stages are **only the official deliverables recorded in SOT `outputs.step-N`**:

1. Team Lead merges all Teammate deliverables
2. Records in SOT `outputs.step-N` + Anti-Skip Guard verification
3. Team Lead invokes `@translator` (on the merged official deliverable)
4. Records in SOT `outputs.step-N-ko`

> Individual Teammate deliverables are intermediate artifacts (not recorded in SOT), and therefore are not translated.

#### Independent Translation Verification (optional — for final deliverables)

By default, the translator's **self-review** is sufficient. For stages where quality is especially critical, such as final deliverables, an independent verification sub-agent can be added:

```
@translator → output.ko.md
  → @translation-verifier (separate sub-agent)
    ① Read English source and Korean translation simultaneously
    ② Verify accuracy, completeness, terminology consistency, naturalness
    ③ Pass/Fail verdict + feedback
  → On Fail: request re-translation from @translator with feedback
```

This pattern is applied optionally in workflow design.

#### Sub-agent Categorization Rules

Every sub-agent invocation is governed by explicit categorization rules that determine fork context and execution isolation.

| Sub-agent | Fork Decision | Rationale |
|-----------|---------------|-----------|
| **@translator** | Always Fork | Glossary persistence (per-fork state) → isolation required; prevents concurrent write to glossary.yaml |
| **@reviewer** | Always Fork | Independent L2 calibration → isolated context; ensures adversarial perspective without interference |
| **@fact-checker** | Always Fresh | Stateless verification logic → fresh analysis; no accumulated state required |
| **[New agent TBD]** | Team Decision | Requires explicit ADR + context-depth analysis before first invocation |

**Implementation**: Fork decision validated by `pre_subagent_invocation.py` (§5.1.5) before Task() invocation. Unknown agents raise RuntimeError to ensure explicit categorization.

#### RLM Pattern in Sub-agent Invocation

Each Sub-agent operates within the RLM (Recursive Language Models) pattern, which defines clear external object boundaries and write authority:

**External Objects & Access Rules**:

1. **workflow.md** (Design specification — invariant)
   - Access: Read-only by all agents
   - Write: None (frozen during execution)

2. **state.yaml** (Workflow state — SOT)
   - Access: Read by all agents
   - Write: Orchestrator only (never Sub-agents)

3. **glossary.yaml** (Terminology mapping — persistent memory)
   - Access: Read by Sub-agents during execution
   - Write: Read-only during execution; Team Lead updates post-execution (sequential, no concurrent writes)

4. **Deliverable outputs** (step-N-result.md — Sub-agent work products)
   - Access: Read by Orchestrator
   - Write: Sub-agent in fork context

**Access Invariant**: Sub-agents NEVER write to workflow.md or state.yaml. Orchestrator NEVER modifies deliverable content directly (only records location in state.yaml).

**Enforcement**: Hook-based validation (§5.1.5) + Python SOT guard in state_manager.py prevents unauthorized writes.

### 5.3 Verification Protocol (Work Verification)

A protocol that verifies whether each stage deliverable of the workflow has **100% achieved the functional goal**.

**Core principle:**
> **"Declare the definition of done first, verify after execution, and re-execute on failure."**

Anti-Skip Guard (file existence + ≥ 100 bytes) guarantees **physical existence**, and the Verification Protocol guarantees **content completeness**. The two layers operate independently, and both must pass before proceeding to the next stage.

```
Quality-guarantee layer structure:

  Anti-Skip Guard (Hook — deterministic)
    "Does the file exist and have meaningful size?"
      ↓ PASS
  Verification Gate (Agent — semantic)
    "Has the functional goal been 100% achieved?"
      ↓ PASS
  Update SOT + proceed to next stage
```

#### Declaring Verification Criteria

Define a `Verification` field in each stage of the workflow. **Place it before the Task** so that the agent starts work after first recognizing "what constitutes completion."

```markdown
### N. [Step Name]
- **Verification**:
  - [ ] [specific, measurable criterion]
  - [ ] [specific, measurable criterion]
- **Task**: [task description]
```

#### Verification Criterion Types (5)

| Type | Verification Target | Good Example | Bad Example |
|------|---------------------|--------------|-------------|
| **Structural completeness** | Internal structure of the deliverable | "All 5 sections (Intro, Analysis, Comparison, Recommendation, References) are included" | "Well-organized" |
| **Functional goal** | Achievement of the task goal | "Each competitor pricing data includes ≥ 3 tiers + exact amounts" | "Pricing info exists" |
| **Data integrity** | Data accuracy | "All URLs are valid and contain no placeholder/example.com" | "Links checked" |
| **Pipeline connection** | Compatibility with next stage input | "Contains competitor_name, pricing_tiers, feature_list fields required by the Step 4 analysis agent" | "Next stage compatible" |
| **Cross-step traceability** | Logical derivation from previous-stage data | "≥ 80% of analysis claims are traceable via the [trace:step-N] marker to their source" | "Data-based" |

> **Criterion-writing rule**: Each criterion must be **mechanically pass/fail judgeable by a third party**. Subjective judgments ("good quality," "sufficient depth") must not be used as criteria. Subjective quality judgments are handled by the existing `(human)` checkpoints.

#### Domain Knowledge Structure (DKS)

A pattern for verifying the validity of domain-specialized reasoning. In the Research stage, build `domain-knowledge.yaml`, and in the Implementation stage, use it as verification criteria. Optional — not required for every domain. Validation script: `validate_domain_knowledge.py` (DK1-DK7).

**DKS necessity criteria**:

| Domain | DKS Necessity | Reason |
|--------|---------------|--------|
| Medicine/clinical, law | High | Validity of domain-specialized reasoning (symptom→disease, precedent→principle) must be verified |
| Competitive analysis, market research | Medium | Structuring entity relationships (dominance, competition) improves quality |
| Blog/content, code generation | Low | Type systems / tests substitute, or domain reasoning is unnecessary |

#### Execution Protocol

```
1. Read verification criteria — agent first recognizes the definition of "100% complete"
2. Execute stage — produce the full-quality deliverable (Absolute Criterion 1)
3. Anti-Skip Guard — file existence + ≥ 100 bytes (deterministic)
4. Verification Gate — self-verify deliverable against each criterion (semantic)
   ├─ All criteria PASS → create verification-logs/step-N-verify.md → update SOT → proceed
   └─ Even one FAIL:
       ├─ Identify the failure cause + re-execute only the failing part (not full rework)
       ├─ Re-verify (up to 10 retries)
       └─ If still FAIL after 10 → escalate to user
5. Update SOT — record outputs, `current_step` +1
```

> **Scope of Self-Verification**: The verification in this protocol is a **completeness** check — "Was what had to be executed executed?" Subjective **quality judgment** is handled by the existing `(human)` checkpoints, and the Verification Protocol does not replace them.

#### Verification Log Format

Recorded in `verification-logs/step-N-verify.md`:

```markdown
# Verification Report — Step {N}: {Step Name}

## Criteria Check
| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | [criterion text] | PASS | [specific evidence from the deliverable] |
| 2 | [criterion text] | FAIL→PASS | [first-round failure reason] → [evidence after re-execution] |

## Result: PASS (retry: 1)
## Verified Output: research/insights.md (2,847 bytes)
```

#### 3-Layer Verification for (team) Stages

Agent-group stages perform a 3-layer verification:

| Layer | Performer | Verification Target | SOT Write |
|-------|-----------|---------------------|-----------|
| **L1** | Teammate (self-verification) | Verification criteria of own Task | **None** — completed inside the session |
| **L1.5** | Teammate (pACS) | Confidence of own Task deliverable | **None** — score is included in the report message |
| **L2** | Team Lead (comprehensive verification + stage pACS) | Verification criteria of the whole stage | **Yes** — update SOT outputs + pacs |

```
Teammate: Execute Task → self-verify (L1) → pACS self-score (L1.5)
            → On PASS + GREEN/YELLOW: report to Team Lead (include pACS score)
            → On FAIL or RED: self-correct, then re-verify/re-score

Team Lead: Receive Teammate deliverables + pACS scores
            → Comprehensive verification against stage criteria (L2)
            → Stage pACS = min(each Teammate pACS) — apply min-score principle
            → On PASS: update SOT (outputs + pacs)
            → On FAIL: SendMessage with concrete feedback + re-execution directive
```

> **SOT compatibility**: Teammate still produces only deliverable files and does not write to SOT. Self-verification and pACS self-scoring are completed inside the Teammate's session and conveyed to the Team Lead via the report message (Absolute Criterion 2). Only the Team Lead records in `pacs-logs/` and updates the SOT.

#### Backward Compatibility

| Situation | Behavior |
|-----------|----------|
| `Verification` field **present** | Verification Gate active — verify against criteria before proceeding |
| `Verification` field **absent** | Existing behavior — proceed using only Anti-Skip Guard |

When creating new workflows, include the `Verification` field as mandatory. Existing workflows can add it incrementally.

#### SOT Impact

**None.** The Verification Protocol is an agent-execution protocol (prompt layer) and does not change the SOT structure. Advancement of `current_step` already implicitly means that verification has completed, and the verification details are recorded in `verification-logs/` files.

### 5.4 pACS — predicted Agent Confidence Score (Self-Confidence Rating)

A protocol where an agent **structurally self-rates the confidence of its own deliverable** during workflow execution. Inspired by AlphaFold's pLDDT (predicted Local Distance Difference Test).

**Core principle:**
> **"Before assigning a score, speak about the weaknesses first."** (Pre-mortem Protocol)

While the Verification Protocol (§5.3) verifies "completeness" — was what had to be executed executed? — pACS **quantifies "confidence" — how much can we believe the result?** The two protocols guarantee quality on different dimensions and operate independently.

#### 3 Evaluation Dimensions (Orthogonal Dimensions)

| Dimension | Target of Measurement | Signs of Low Score |
|-----------|----------------------|--------------------|
| **F — Factual Grounding** | Robustness of factual grounding | Unknown sources, memory-based inference, unverified assumptions |
| **C — Completeness** | No omissions against requirements | Some items skipped, insufficient analysis depth |
| **L — Logical Coherence** | Internal consistency of argument / structure | Contradictions, leaps, mismatch between evidence and conclusion |

> **Reason for limiting to 3 dimensions**: Agent self-rating is a subjective estimate without calibration data. The more dimensions, the larger the precision illusion and the greater the interference between dimensions. 3 orthogonal dimensions is the practical upper bound.

#### Min-Score Principle

> **pACS = min(F, C, L)**

Weighted averaging is not used. If any one dimension is low, the overall confidence is low. The weakest link determines overall quality.

#### Pre-mortem Protocol (Mandatory — perform before scoring)

A mechanism that structurally prevents score inflation. The agent must answer the 3 questions below **before** scoring:

1. **"Where is the most uncertain part of this deliverable?"** — areas where sources are unverified, recency is unclear, or reliance on estimation exists
2. **"What is most likely to have been omitted?"** — partial requirement unmet, edge cases unconsidered, data gaps
3. **"Where is the weakest link in this argument?"** — evidence→conclusion leaps, insufficient premise verification, unexplored alternatives

If the Pre-mortem responses reveal serious issues, you cannot assign a high score to the corresponding dimension.

#### Action Triggers

| Grade | Score Range | Action | Rationale |
|-------|-------------|--------|-----------|
| **GREEN** | pACS ≥ 70 | Automatic progression | High agent confidence — normal quality |
| **YELLOW** | 50 ≤ pACS < 70 | Proceed but flag weaknesses | Partial uncertainty — subject to post-review |
| **RED** | pACS < 50 | Rework or escalation | Untrustworthy — re-execution of that part is mandatory |

#### Quality-Guarantee Layer Structure (4 Layers)

```
L0  Anti-Skip Guard (Hook — deterministic)
      "Does the file exist and have meaningful size?"
        ↓ PASS
L1  Verification Gate (Agent — semantic)
      "Has the functional goal been 100% achieved?"
        ↓ PASS
L1.5  pACS Self-Rating (Agent — confidence)
        Pre-mortem → score F, C, L → min(F,C,L) = pACS
        ↓ GREEN/YELLOW: proceed (YELLOW flagged)
        ↓ RED: rework or escalation
L2    Adversarial Review (Enhanced — stages with a Review: field)
        @reviewer / @fact-checker independently reviews the deliverable adversarially (§5.5)
```

> **Relationship between L1 and L1.5**: The Verification Gate is "checklist item PASS/FAIL" — a binary judgment. pACS is "overall confidence 0-100" — a continuous self-rating. Even when every Verification item is PASS, pACS can still be low (e.g., every item was addressed but source quality is low).

#### SOT Record

```yaml
workflow:
  # ... existing fields ...
  pacs:
    current_step_score: 72          # pACS of current stage
    dimensions: {F: 72, C: 85, L: 78}
    weak_dimension: "F"             # min-score dimension
    pre_mortem_flag: "Step 3: 2 data sources unverified"
    history:                        # per-stage history
      step-1: {score: 85, weak: "C"}
      step-2: {score: 72, weak: "F"}
```

- The `pacs` field is **append-only** to the existing SOT schema — independent of existing `workflow`, `autopilot`, `outputs`, `active_team` fields
- SOT without `pacs` still functions normally (backward compatible)
- Because the Hook's `capture_sot()` includes the entire SOT in the snapshot, the `pacs` field is also automatically preserved across session boundaries

#### Translation pACS (for Translation Deliverables)

Additional 3 dimensions for the `@translator` sub-agent's translation deliverables:

| Dimension | Target of Measurement | Signs of Low Score |
|-----------|----------------------|--------------------|
| **Ft — Fidelity** | Accurate transfer of source meaning | Over-paraphrasing, meaning distortion, terminology inconsistency |
| **Ct — Translation Completeness** | No omissions vs. source | Paragraphs/sentences/footnotes omitted |
| **Nt — Naturalness** | Natural Korean rather than translationese | English word-order literalisms, translation tone |

Translation pACS = min(Ft, Ct, Nt). Action triggers are identical (GREEN/YELLOW/RED).

#### L2 Adversarial Review (Enhanced — stages with a Review: field)

An enhanced quality-verification layer that replaces the previous L2 Calibration. `@reviewer` (critical analysis of code/deliverables, read-only) and `@fact-checker` (external fact verification, web access) independently review the deliverable. Review results are deterministically guaranteed in quality via P1 validation (`validate_review.py`).

Applied to stages where the workflow design specifies `Review: @reviewer` or `Review: @reviewer + @fact-checker`. Default is self-rating (L1.5) only.

Details: see §5.5 Adversarial Review.

#### pACS Log Format

Recorded in `pacs-logs/step-N-pacs.md`:

```markdown
# pACS Report — Step {N}: {Step Name}

## Pre-mortem
1. **Most uncertain**: [the uncertain part]
2. **Likely omission**: [possible omission]
3. **Weakest link**: [the weakest argumentative link]

## Scores
| Dimension | Score | Rationale |
|-----------|-------|-----------|
| F (Factual Grounding) | {0-100} | [specific evidence] |
| C (Completeness) | {0-100} | [specific evidence] |
| L (Logical Coherence) | {0-100} | [specific evidence] |

## Result: pACS = {min(F,C,L)} → {GREEN|YELLOW|RED}
## Weak Dimension: {F|C|L} — {description of weakness}
```

#### pACS Under Autopilot

- pACS GREEN → automatic progression
- pACS YELLOW → automatic progression + record weak dimension in Decision Log
- pACS RED → automatic rework (up to 10 times). If still RED after → escalate to user
- Add `pacs_score`, `weak_dimension` fields to the Autopilot Decision Log

#### pACS During Sub-agent Invocation

When a stage invokes a Sub-agent (§5.1.5, §5.2 categorization), pACS scoring applies to the Sub-agent's deliverable independently:

```yaml
pacs:
  step-N-subagent-translator: {score: 88, dimensions: {Ft: 88, Ct: 90, Nt: 85}}
  step-N: {score: 85, dimensions: {F: 85, C: 87, L: 83}}
```

- **Sub-agent pACS**: Scored by the Sub-agent after fork isolation (independent context)
- **Stage pACS**: Scored by the Generator or Team Lead for the main deliverable (original fork)
- **Relationship**: Both are recorded independently in SOT; they do not constrain each other
- **Progression rule**: Stage proceeds if stage pACS ≥ 50 (rework if RED) — Sub-agent pACS does not block stage progression, only flags quality concerns in the Decision Log

#### Backward Compatibility

| Situation | Behavior |
|-----------|----------|
| No pACS reference in the workflow | Proceed with only existing L0 + L1 |
| No `pacs` field in SOT | Normal operation — ignored by both Hook and agent |
| pACS alone without Verification | Not permitted — pACS is performed only after Verification Gate passes |

> **Design decision**: pACS in isolation without Verification is forbidden. Performing confidence rating (L1.5) without completeness verification (L1) can lead to the contradictory state of "everything omitted, but confidence high."

### 5.5 Adversarial Review (Enhanced L2 — Adversarial Review)

An enhanced quality-verification layer that replaces the previous L2 Calibration. Deliverables are independently reviewed using the Generator-Critic pattern.

#### Quality Layer Architecture

```
L0   Anti-Skip Guard (Hook — deterministic)
L1   Verification Gate (Agent self-check)
L1.5 pACS Self-Rating (Agent confidence)
L2   Adversarial Review (Enhanced L2) ← this section
       ├── Content critical analysis (LLM — @reviewer / @fact-checker)
       ├── Independent pACS scoring (LLM → Python validates)
       └── P1 deterministic validation (Python — validate_review.py)
```

#### Agent Definitions

| Agent | Tools | Role | Model |
|-------|-------|------|-------|
| `@reviewer` | Read, Glob, Grep (read-only) | Critical analysis of code/deliverables — flaws, logical gaps, completeness review | opus |
| `@fact-checker` | Read, Glob, Grep, WebSearch, WebFetch | Fact verification — claim-by-claim confirmation against independent sources | opus |

- **Rationale for tool separation (P2)**: `@reviewer` reviews internal logic of code/docs, so it only needs read access. `@fact-checker` needs web access because external fact verification is required. Principle of least privilege.
- **Rationale for Sub-agent selection**: Single reviewer = Sub-agent (synchronous feedback loop). Since review results must be reflected immediately, this is more efficient than an Agent Team asynchronous pattern.

#### Execution Protocol

1. Generator produces the deliverable → passes L0/L1/L1.5
2. Orchestrator invokes the agent specified in the `Review:` field as a Sub-agent
3. The reviewer agent produces the review report (returned via stdout)
4. Orchestrator saves the report to `review-logs/step-N-review.md`
5. P1 validation: `python3 .claude/hooks/scripts/validate_review.py --step N --project-dir .`
6. Proceed based on verdict:

```
PASS → Translation (if any) → SOT update → next stage
FAIL → Rework (up to 10 times) → Re-review
       ↓ after 10
       Escalate to user
```

#### Review Field Syntax

Specify the `Review:` attribute per stage in the workflow:

```markdown
### Step 3: Analysis Report (agent)
- Agent: @analyst
- Review: @reviewer          ← code/deliverable review
- Translation: @translator
- Verification:
  - [ ] ...
```

| Review Value | Behavior |
|--------------|----------|
| `@reviewer` | Critical analysis of code/deliverable |
| `@fact-checker` | Fact verification (against external sources) |
| `@reviewer + @fact-checker` | Both run (high-risk stages) |
| `none` or unspecified | Skip review (up to L1.5 only) |

#### Rubber-stamp Prevention (4-Layer Defense)

| Defense Layer | Mechanism |
|---------------|-----------|
| 1. Adversarial Persona | "Critic, not validator" identity embedded in the agent definition |
| 2. Pre-mortem | Writing 3 failure hypotheses before analysis is mandatory — prevents confirmation bias |
| 3. Minimum 1 Issue | P1 validation auto-rejects reviews with 0 issues (R5 check) |
| 4. Independent pACS | Reviewer scores independently → compared with Generator (Delta ≥ 15 → arbitration) |

#### P1 Hallucination Containment

5 tasks that must be 100% accurate in the review system are enforced by Python code:

| Check | Function | Location |
|-------|----------|----------|
| R1: Review file existence | `validate_review_output()` | `_context_lib.py` |
| R2: Minimum size (100 bytes) | `validate_review_output()` | `_context_lib.py` |
| R3: 4 required sections exist | `validate_review_output()` | `_context_lib.py` |
| R4: Explicit extraction of PASS/FAIL | `parse_review_verdict()` | `_context_lib.py` |
| R5: Issue table ≥ 1 row | `validate_review_output()` | `_context_lib.py` |
| pACS Delta computation | `calculate_pacs_delta()` | `_context_lib.py` |
| Review → Translation order | `validate_review_sequence()` | `_context_lib.py` |

Standalone script: `python3 .claude/hooks/scripts/validate_review.py --step N --project-dir .`
Output: JSON `{"valid": true, "verdict": "PASS", "critical_count": 0, ...}`

#### Translation P1 Hallucination Containment

9 tasks that must be 100% accurate for translation deliverables are enforced by Python code:

| Check | Function | Location |
|-------|----------|----------|
| T1: Translation file existence | `validate_translation_output()` | `_context_lib.py` |
| T2: Minimum size (100 bytes) | `validate_translation_output()` | `_context_lib.py` |
| T3: English source existence | `validate_translation_output()` | `_context_lib.py` |
| T4: .ko.md extension | `validate_translation_output()` | `_context_lib.py` |
| T5: Non-whitespace content | `validate_translation_output()` | `_context_lib.py` |
| T6: Heading count ±20% | `validate_translation_output()` | `_context_lib.py` |
| T7: Code block count match | `validate_translation_output()` | `_context_lib.py` |
| T8: Glossary timestamp freshness | `check_glossary_freshness()` | `_context_lib.py` |
| T9: pACS min() arithmetic correctness (generic) | `verify_pacs_arithmetic()` | `_context_lib.py` |

Standalone script: `python3 .claude/hooks/scripts/validate_translation.py --step N --project-dir . --check-pacs --check-sequence`
Output: JSON `{"valid": true, "checks": {"T1": true, ...}, "pacs_valid": true}`

#### Verification Log P1 Hallucination Containment

Structural integrity of the verification log is enforced by Python code across 3 items:

| Check | Function | Location |
|-------|----------|----------|
| V1a: Verification log file existence | `validate_verification_log()` | `_context_lib.py` |
| V1b: Per-criterion PASS/FAIL explicit | `validate_verification_log()` | `_context_lib.py` |
| V1c: Logical consistency (if any FAIL, overall PASS is impossible) | `validate_verification_log()` | `_context_lib.py` |

Standalone script: `python3 .claude/hooks/scripts/validate_verification.py --step N --project-dir .`
Output: JSON `{"valid": true, "checks": {"V1a": true, "V1b": true, "V1c": true}}`

#### Issue Severity Classification

| Severity | Definition | Verdict Impact |
|----------|------------|----------------|
| **Critical** | Factual error, missing required content, logical flaw, security vulnerability | → FAIL |
| **Warning** | Incomplete coverage, weak argument, style inconsistency, minor inaccuracy | → PASS (recorded) |
| **Suggestion** | Improvement opportunity, alternative approach, readability improvement | → PASS (optional) |

#### Review Report Format

Recorded in `review-logs/step-N-review.md`:

```markdown
# Adversarial Review — Step {N}: {Step Name}
Reviewer: @{reviewer|fact-checker}

## Pre-mortem (MANDATORY — before analysis)
1. **Most likely critical flaw**: [...]
2. **Most likely factual error**: [...]
3. **Most likely logical weakness**: [...]

## Issues Found
| # | Severity | Location | Problem | Suggested Fix |
|---|----------|----------|---------|---------------|
| 1 | Critical | file:line | [...] | [...] |

## Independent pACS (Reviewer's Assessment)
| Dimension | Score | Rationale |
|-----------|-------|-----------|
| F | {0-100} | [...] |
| C | {0-100} | [...] |
| L | {0-100} | [...] |

Reviewer pACS = min(F,C,L) = {score}
Generator pACS = {score}
Delta = |Reviewer - Generator| = {N}

## Verdict: {PASS|FAIL}
```

#### Adversarial Review Under Autopilot

- Review PASS → automatic progression (including Translation)
- Review FAIL → automatic rework (up to 10 times, escalate to user on exceeding)
- pACS Delta ≥ 15 → record in Decision Log + recommend recalibration
- Review Decision Log: include review result in `autopilot-logs/step-N-decision.md`

#### Execution Order Constraint

```
Task → L0 → L1 → L1.5 → Review(L2) → PASS → Translation → SOT update
```

- Translation is executed only after Review PASS (enforced by P1 `validate_review_sequence()`)
- Translation execution is forbidden while Review is FAIL
- Stages with Review unspecified (`none`) can proceed directly to Translation after L1.5

#### Sub-agent Invocation in (team) Stages

When a workflow stage is designated as `(team)`, multiple agents execute in parallel to produce independent deliverables. The Sub-agent invocation (§5.1.5 fork context) applies at the **Team Lead verification stage**, not at individual Teammate execution:

**Execution Flow**:

```
Step N: (team) stage
  ① TaskCreate(step=Research, type=team, agents=[A, B, C, D, E])
  ② Team members execute in parallel
     ├─ Teammate A → deliverable-A.md (internal verification L0/L1/L1.5 only)
     ├─ Teammate B → deliverable-B.md
     └─ ... (all execute independently)
  ③ TaskUpdate(status=completed) — individual results produced
  ④ Team Lead collects + validates individual outputs
     └─ Comprehensive verification against stage criteria (L2 equivalent)
  ⑤ Team Lead merges results → merged_deliverable.md
  ⑥ Orchestrator invokes @reviewer as Sub-agent (fork context = always_fork per categorization)
     └─ @reviewer reads merged_deliverable.md in isolated fork
     └─ Produces review-logs/step-N-review.md
  ⑦ Orchestrator validates review (P1 validate_review.py)
  ⑧ On PASS: Translation (if any) → SOT update → proceed to Planning
     On FAIL: Team Lead reworks → re-verify → re-invoke @reviewer
```

**Key differences from (agent) stages**:
- Individual Teammates do NOT invoke Sub-agents — only perform L0/L1/L1.5 self-verification
- Team Lead performs comprehensive verification (L2 equivalent) before Sub-agent invocation
- Sub-agent invocation (@reviewer) is called only once per stage (on the merged official deliverable)
- Fork context decision for @reviewer is deterministic (always_fork) — no team decision needed
- SOT write authority remains with Orchestrator only (after review PASS and validation)

**Rationale**: This sequencing preserves RLM pattern (single write point) while enabling parallel team execution in the core work phase, with expert review applied to the unified result.

#### Backward Compatibility

| Situation | Behavior |
|-----------|----------|
| Workflow has no `Review:` specified | Proceed with only existing L0 + L1 + L1.5 |
| `review-logs/` does not exist | Normal operation — P1 functions fail gracefully |
| `@reviewer`/`@fact-checker` agents undefined | On Sub-agent invocation failure, escalate to user |

> **Design decision**: Adversarial Review is positioned as the Enhanced version of the existing L2 Calibration. The "cross-verification" of L2 Calibration is strengthened to "adversarial review," while the existing L0/L1/L1.5 layers are not changed at all. Stages without the `Review:` field behave identically to before.

---

### 5.6 Abductive Diagnosis Protocol

When a quality gate (Verification Gate, pACS, Adversarial Review) fails, instead of retrying immediately, pass through a **3-step diagnosis** to raise retry quality. The existing 4-layer QA (L0→L1→L1.5→L2) is not changed; this is an additional layer inserted **between** FAIL and retry.

#### 3-Step Process

| Step | Actor | Input | Output | Nature |
|------|-------|-------|--------|--------|
| **Step A — P1 pre-evidence collection** | `diagnose_context.py` | SOT, log files, retry history | Structured evidence bundle (JSON) | Deterministic |
| **Step B — LLM diagnosis** | Orchestrator (Claude) | Evidence bundle + hypothesis priority | Diagnosis log (`diagnosis-logs/step-N-gate-timestamp.md`) | Judgmental |
| **Step C — P1 post-validation** | `validate_diagnosis.py` | Diagnosis log | AD1-AD10 structural integrity (JSON) | Deterministic |

#### Hypothesis System (H1/H2/H3/H4)

| Hypothesis | Label | Priority Determination Criterion |
|------------|-------|----------------------------------|
| **H1** | Upstream data quality issue | Top priority when prior-stage deliverables are missing/under-delivered |
| **H2** | Current-stage execution gap | Default top priority (most frequent) |
| **H3** | Criteria interpretation error | Priority rises at Review gates |
| **H4** | Capability gap — missing tools/scripts/infrastructure | Auto-promoted when H2 fails to resolve in 2 consecutive iterations |

#### Fast-Path (FP1-FP3)

Deterministic shortcut paths that skip LLM diagnosis:

| ID | Condition | Diagnosis | Action |
|----|-----------|-----------|--------|
| **FP1** | Deliverable file missing | "File not created" | Immediate re-execution |
| **FP2** | Deliverable size < 100B | "Incomplete creation" | Immediate re-execution |
| **FP3** | Same hypothesis selected 2 times in a row | "Approach lock-in" | Escalate to user |

#### P1 Post-Validation (AD1-AD10)

| Check | Description |
|-------|-------------|
| AD1 | Diagnosis log file exists |
| AD2 | Minimum size ≥ 100 bytes |
| AD3 | Gate field matches |
| AD4 | Selected hypothesis exists (H1/H2/H3/H4) |
| AD5 | Evidence items ≥ 1 |
| AD6 | Action Plan section exists |
| AD7 | Forward step references forbidden |
| AD8 | Hypotheses ≥ 2 (alternatives considered) |
| AD9 | Selected hypothesis is one of the listed hypotheses |
| AD10 | References previous diagnosis (when retry > 0) |

#### Backward Compatibility

| Situation | Behavior |
|-----------|----------|
| `diagnosis-logs/` does not exist | Existing behavior — retry without diagnosis |
| Retry executed without diagnosis | Normal operation — safety net only emits a stderr warning |
| Fast-Path applies | Skip LLM diagnosis — decide immediately with only P1 pre-evidence |

> **Design decision**: Abductive Diagnosis is an additional layer that does not change the existing 4-layer QA. Diagnosis results are recorded only in `diagnosis-logs/` and SOT is not modified. They are archived to the Knowledge Archive as `diagnosis_patterns`, enabling cross-session learning.

---

## 6. Skill System

### workflow-generator

A skill that designs and generates the workflow definition file (`workflow.md`).

- **Triggers**: "Make a workflow," "design an automation pipeline," "define a task flow"
- **Entry point**: `.claude/skills/workflow-generator/SKILL.md`
- **Two cases**: (1) idea only → interactive Q&A, (2) description document available → document analysis first

### doctoral-writing

A skill for writing with doctoral-level academic rigor and clarity.

- **Triggers**: "Write in thesis style," "academic writing," "polish paper sentences"
- **Entry point**: `.claude/skills/doctoral-writing/SKILL.md`
- **Core principles**: Clarity, conciseness, academic rigor, logical flow

---

## 7. Skill Development Rules

When creating a new skill or modifying an existing skill:

1. **All Absolute Criteria must be included** — contextualized per domain (for non-code-change domains, Absolute Criterion 3 may be N/A)
2. **Role separation between files** — skill definition (WHY), reference material (WHAT/HOW/VERIFY)
3. **Explicitly specify conflict scenarios among the Absolute Criteria** — concrete field judgments, not abstract rules
4. **Mandatory reflection after modification** — do not merely insert wording; check for conflicts with existing content

---

## 8. Language and Style

- **Framework documents / user conversation**: Korean
- **Workflow execution**: English (maximize AI performance — Absolute Criterion 1 basis). Details: §5.2
- **Final deliverables**: English source + Korean translation pair
- **Technical terminology**: Keep in English (SOT, Agent, Orchestrator, Hooks, etc.)
- **Visualization**: Prefer Mermaid diagrams
- **Narrative depth**: Prefer comprehensive, data-driven narration over brief summaries
- **Code comments**: Korean (framework code) / English (workflow execution code)

---

## 9. Universal System-Prompt System (Hub-and-Spoke)

This project is designed so that **the same methodology is applied automatically regardless of which AI CLI tool is used**.

### Architecture

```
                AGENTS.md (Hub — methodology SOT)
               /    |    |    \    \     \
          CLAUDE  GEMINI .cursor  .github/
          .md     .md    /rules   copilot-
                         (Spoke)  instructions.md
```

- **Hub (AGENTS.md)**: Sole definition point for Absolute Criteria, design principles, and workflow structure
- **Spoke (tool-specific files)**: Reference the Hub while providing implementation mappings tailored to each tool's own functionality

### Tool File Mapping

| AI CLI Tool | System-Prompt File | Auto-Read | AGENTS.md Recognition |
|-------------|--------------------|-----------|----------------------|
| **Claude Code** | `CLAUDE.md` | Yes | Separate file |
| **Gemini CLI** | `GEMINI.md` | Yes | Loaded additionally by config |
| **Codex CLI** | `AGENTS.md` (directly) | Yes | Native |
| **Copilot CLI** | `.github/copilot-instructions.md` | Yes | Auto-recognized |
| **Cursor** | `.cursor/rules/agenticworkflow.mdc` | Yes (alwaysApply) | Recognized |

### Spoke File Principles

1. **Inline Absolute Criteria + reference details**: Each Spoke includes the core definitions of the Absolute Criteria (1-2 sentences) inline, and delegates the details to `AGENTS.md §2`.
2. **Tool implementation mapping**: Specifies the correspondence between the tool's own functionality (Hook, Agent, Plugin, etc.) and AgenticWorkflow concepts.
3. **Context Preservation alternatives**: For tools that cannot use Claude Code's Context Preservation System, guide to the alternatives available in that tool.

### Conflict Resolution

> **AGENTS.md's Absolute Criteria take precedence over every Spoke.** When tool-dependent implementation conflicts with a principle, the principle wins.

### Synchronization Upon Changes to the Absolute Criteria

When the Absolute Criteria in AGENTS.md change, every Spoke file's inline duplicates must also be synchronized:
- `CLAUDE.md`, `GEMINI.md` — modify directly
- `.cursor/rules/` — modify the inline portion
- `.github/copilot-instructions.md` — modify the inline portion
