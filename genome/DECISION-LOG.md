# AgenticWorkflow Decision Log (ADR)

This document records **every major design decision** of the AgenticWorkflow project in chronological order.
Each decision follows the ADR (Architecture Decision Record) format and contains Context, Decision, Rationale, Alternatives, and Status.

> **Purpose**: To trace the project's "why?" so that future decision-makers (human or AI) can understand the context of prior decisions and make consistent judgments.

---

## ADR Format

```
### ADR-NNN: Title
- **Date**: YYYY-MM-DD (based on commit)
- **Status**: Accepted / Superseded / Deprecated
- **Context**: The situation that required the decision
- **Decision**: The direction chosen
- **Rationale**: Why it was chosen
- **Alternatives**: Directions considered but not chosen
- **Related Commit**: Hash + message
```

---

## 1. Foundation

### ADR-001: The Workflow Is an Intermediate Artifact; the Running System Is the Final Deliverable

- **Date**: 2026-02-16
- **Status**: Accepted
- **Context**: Many automation projects stop at "making a plan." The trap of making workflow.md creation itself the goal had to be prevented.
- **Decision**: The project is divided into 2 phases — Phase 1 (workflow.md design = intermediate deliverable), Phase 2 (agents, scripts, and automation actually running = final deliverable).
- **Rationale**: No matter how precise a blueprint is, it is incomplete unless it runs. Phase 1 without Phase 2 achieves only half the value.
- **Alternatives**: Treat workflow.md itself as the final deliverable → rejected (executability cannot be verified)
- **Related Commit**: `348601e` Initial commit: AgenticWorkflow project

### ADR-002: The Absolute Criteria System — Hierarchical Priority Among 3 Criteria

- **Date**: 2026-02-16
- **Status**: Accepted
- **Context**: The project has multiple design principles, and a judgment criterion was needed when principles conflict. Trade-offs such as "go fast vs. raise quality" and "SOT simplicity vs. functional extension" kept recurring.
- **Decision**: Define 3 Absolute Criteria and set an explicit priority:
  1. **Absolute Criterion 1 (Quality)** — Highest. The reason every criterion exists.
  2. **Absolute Criterion 2 (SOT)** — Means to guarantee data integrity. Subordinate to quality.
  3. **Absolute Criterion 3 (CCP)** — Means to guarantee code-change quality. Subordinate to quality.
- **Rationale**: The abstract claim "all principles are important" does not work in practice. Explicit priority is required so that conflicts can be resolved deterministically.
- **Alternatives**:
  - All principles equal → rejected (no conflict-resolution basis)
  - SOT as the highest → rejected (data integrity is a means, not the goal)
- **Related Commit**: `348601e` Initial commit

### ADR-003: Quality Absolutism — Completely Ignoring Speed, Cost, and Length

- **Date**: 2026-02-16
- **Status**: Accepted
- **Context**: AI-based automation tends to minimize token cost, execution time, and agent count. This creates anti-patterns of skipping stages, abbreviating deliverables, or skipping verification.
- **Decision**: "Speed, token cost, workload, and length limits are **completely ignored**. The sole decision criterion is the quality of the final deliverable."
- **Rationale**: If quality drops due to cost-cutting, the cost of rework is ultimately higher. Targeting the highest quality from the start is more efficient in the long run.
- **Alternatives**: Cost-quality trade-off matrix → rejected (increased decision complexity, incentive structure always tilts toward cost)
- **Related Commit**: `348601e` Initial commit

### ADR-004: Research → Planning → Implementation 3-Stage Structural Constraint

- **Date**: 2026-02-16
- **Status**: Accepted
- **Context**: When the number and structure of workflow stages can be set freely, problems arise such as agents skipping Research or moving into implementation without Planning.
- **Decision**: Every workflow must follow 3 stages (Research → Planning → Implementation). This is a structural constraint, not a convention.
- **Rationale**:
  - Skipping Research → working with insufficient information → quality drop (violates Absolute Criterion 1)
  - Skipping Planning → implementing without human review → directional errors accumulate
  - Skipping Implementation → an incomplete system with only a blueprint (violates ADR-001)
- **Alternatives**: Flexible N stages → rejected (no structural guarantee)
- **Related Commit**: `348601e` Initial commit

### ADR-005: Design Principles P1-P4 — Subordinate Principles Under the Absolute Criteria

- **Date**: 2026-02-16
- **Status**: Accepted
- **Context**: The Absolute Criteria define "what we optimize for," but concrete guidance on "how" was needed.
- **Decision**: Define 4 design principles:
  - **P1**: Data refinement for accuracy (Code refines, AI judges)
  - **P2**: Expertise-based delegation structure (Orchestrator only coordinates)
  - **P3**: Resource accuracy (placeholders may not be omitted)
  - **P4**: Question design rules (at most 4, each with 3 options)
- **Rationale**: P1 corresponds to Code-based Filtering in the RLM paper, and P2 to recursive Sub-calls. P3 ensures executability, P4 minimizes user fatigue.
- **Alternatives**: Operating with only the Absolute Criteria (no principles) → rejected (too abstract)
- **Related Commit**: `348601e` Initial commit

### ADR-006: Single-File SOT Pattern

- **Date**: 2026-02-16
- **Status**: Accepted
- **Context**: In an environment where dozens of agents operate concurrently, distributing state across multiple files makes data inconsistency unavoidable.
- **Decision**: All shared state is concentrated in a single file (`state.yaml`). Only the Orchestrator / Team Lead has write permission, and the other agents only read and produce deliverable files.
- **Rationale**: The single-write-point pattern is a proven pattern for guaranteeing data consistency in distributed systems. It fundamentally blocks conflicts caused by simultaneous modification by multiple agents.
- **Alternatives**:
  - Distributed state + merge strategy → rejected (complexity explosion, conflict-resolution overhead)
  - Database-based → rejected (external dependency, over-engineering)
- **Related Commit**: `348601e` Initial commit

### ADR-007: Code Change Protocol (CCP) + Proportionality Rule

- **Date**: 2026-02-16
- **Status**: Accepted
- **Context**: If ripple effects are not analyzed when changing code, a modification in one place can cause errors in unexpected places (shotgun surgery).
- **Decision**: Before changing code, always perform 3 steps (Understand Intent → Ripple Effect Analysis → Change Plan). However, use the Proportionality Rule to scale analysis depth to the scope of the change:
  - Minor (typos, comments) → Step 1 only
  - Standard (function/logic changes) → full 3 steps
  - Large-scale (architecture, API) → full 3 steps + prior user approval
- **Rationale**: The protocol itself is never skipped, but excessive analysis for trivial changes violates Absolute Criterion 1 (Quality). The Proportionality Rule guarantees both the existence and the practicality of the protocol.
- **Alternatives**: Apply the same depth to all changes → rejected (full analysis for a typo fix is unproductive)
- **Related Commit**: `348601e` Initial commit

---

## 2. Documentation Architecture

### ADR-008: Hub-and-Spoke Document Structure — AGENTS.md as the Hub

- **Date**: 2026-02-16
- **Status**: Accepted
- **Context**: Multiple AI tools (Claude Code, Cursor, Copilot, Gemini) each have their own configuration files, and writing the common rules redundantly in each file causes synchronization problems.
- **Decision**: Adopt the Hub-and-Spoke pattern:
  - **Hub**: `AGENTS.md` — common rules for all AI agents (methodology SOT)
  - **Spokes**: `CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md`, `.cursor/rules/agenticworkflow.mdc` — per-tool implementation details
- **Rationale**: It maintains a single definition point (AGENTS.md) for the common rules, while handling tool-specific specifics (Hook settings, Slash Commands, etc.) in each Spoke. This is Absolute Criterion 2 (SOT) applied at the documentation dimension.
- **Alternatives**:
  - Single unified document → rejected (becomes bloated with tool-specific specifics)
  - Fully independent documents → rejected (common rules duplicated, synchronization impossible)
- **Related Commit**: `5b649cb` feat: Hub-and-Spoke universal system prompt for all AI CLI tools

### ADR-009: Adopt the RLM Paper as the Theoretical Foundation

- **Date**: 2026-02-16
- **Status**: Accepted
- **Context**: A design backdrop for the agent architecture was needed. A theoretical basis was required for "Why manage SOT as an external file?" and "Why pre-process in Python?"
- **Decision**: Adopt MIT CSAIL's Recursive Language Models (RLM) paper as the theoretical foundation. The core paradigm of RLM — "Do not feed prompts directly to the neural network; treat them as objects in an external environment" — is applied across the design of AgenticWorkflow.
- **Rationale**: The structural correspondences are precise: RLM's Python REPL ↔ SOT, recursive Sub-call ↔ Sub-agent delegation, Code-based Filtering ↔ P1 principle, etc. Having theoretical roots makes it easier to maintain design consistency.
- **Alternatives**: Proprietary framework → rejected (no theoretical verification)
- **Related Commit**: `e051837` docs: Add coding-resource PDF

### ADR-010: Separating the Independent Architecture Document

- **Date**: 2026-02-16
- **Status**: Accepted
- **Context**: We had CLAUDE.md (what exists), AGENTS.md (what the rules are), and USER-MANUAL (how to use them), but no systematic document describing "why we designed it this way."
- **Decision**: Create `AGENTICWORKFLOW-ARCHITECTURE-AND-PHILOSOPHY.md` as a separate document. It describes design philosophy, architectural overview, component relationships, and the theoretical background of the design principles.
- **Rationale**: Without a "WHY" document, the context of design decisions is lost over time and conflicting modifications occur.
- **Alternatives**: Merge into CLAUDE.md → rejected (increased prompt size; tool-specific directives and a philosophy document differ in nature)
- **Related Commit**: `feba502` docs: Add architecture and philosophy document

### ADR-011: Spoke File Cleanup — Removing Unused Tools

- **Date**: 2026-02-20
- **Status**: Accepted
- **Context**: Initially we created Spoke files for various AI tools such as Amazon Q, Windsurf, and Aider, but configuration files for tools we did not actually use became a maintenance burden.
- **Decision**:
  - Delete `.amazonq/`, `.windsurf/` and remove references from all documents
  - Delete `.aider.conf.yml` and remove references
  - `.github/copilot-instructions.md` is deleted and then restored (actually in use)
- **Rationale**: Unused files only increase synchronization targets without contributing to quality. They can be re-created when needed.
- **Alternatives**: Keep all Spokes → rejected (unnecessary workload increase during documentation sync)
- **Related Commits**: `162a322`, `a4afb26`, `708cb57` (restore), `5634b0e`

---

## 3. Context Preservation System

### ADR-012: Hook-Based Automatic Context Preservation System

- **Date**: 2026-02-16
- **Status**: Accepted
- **Context**: When Claude Code's context window is exhausted (`/clear`, compaction), the in-progress work context is completely lost. Manual saving is easy to forget and inconsistent.
- **Decision**: Connect Python scripts to 5 Hook events (SessionStart, PostToolUse, Stop, PreCompact, SessionEnd) to build an automatic save/restore system. Apply the RLM pattern (external memory object + pointer-based restore).
- **Rationale**: Automated preservation works 100% without user intervention. Applying the RLM pattern allows loading only the needed parts via pointer + summary, rather than injecting the entire history.
- **Alternatives**:
  - Manual save (`/save` command) → rejected (easy to forget)
  - Full transcript backup → rejected (size issues, cannot fit into the context window)
- **Related Commit**: `bb7b9a1` feat: Add Context Preservation Hook System

### ADR-013: Knowledge Archive — Cross-Session Accumulation Index

- **Date**: 2026-02-17
- **Status**: Accepted
- **Context**: Snapshots of a single session alone cannot track the long-term history of the project. Cross-session questions like "How did we solve a similar error before?" could not be answered.
- **Decision**: Structure session metadata and accumulate it in `knowledge-index.jsonl`. Design it so it can be programmatically searched via Grep (corresponding to RLM sub-call).
- **Rationale**: The JSONL format is append-only, has fewer concurrency issues, and is programmatically searchable via Grep/jq. This aligns with the RLM "external environment search" pattern.
- **Alternatives**:
  - SQLite → rejected (external dependency, cannot be searched with text tools)
  - Plain MD file listing → rejected (structured metadata cannot be searched)
- **Related Commit**: `d1acb9f` feat: RLM long-term memory + context quality optimization

### ADR-014: Smart Throttling — 30-Second + 5KB Threshold

- **Date**: 2026-02-17
- **Status**: Accepted
- **Context**: When the Stop hook runs on every response, unnecessary snapshots are repeatedly created even for short responses, impacting performance.
- **Decision**: Apply a 30-second dedup window + 5KB growth threshold to the Stop hook. SessionEnd/PreCompact uses a 5-second window, and SessionEnd is exempt from dedup (guaranteed last chance).
- **Rationale**: Regenerating a snapshot of identical content when there was no change within 30 seconds is waste. The 5KB growth threshold ensures updates only when there is meaningful change.
- **Alternatives**: Always save → rejected (performance burden); time-only check → rejected (saves without change occur)
- **Related Commit**: `7363cc4` feat: Context memory quality optimization — throttling, archive, restore

### ADR-015: IMMORTAL-aware Compression + Audit Trail

- **Date**: 2026-02-19
- **Status**: Accepted
- **Context**: When a snapshot exceeds the size limit, simple truncation can lose core context (current work, design decisions, Autopilot/ULW state).
- **Decision**: Preserve sections with the `<!-- IMMORTAL -->` marker with priority, truncating non-IMMORTAL content first. Record the number of characters removed in each compression Phase (1~7) as HTML comments (audit trail).
- **Rationale**: "Current work" and "design decisions" are the core of session restoration. If these are lost, restoration quality plummets. The audit trail enables debugging of the compression behavior.
- **Alternatives**: Uniform truncation → rejected (risk of losing core context); unprioritized FIFO → rejected (only recent context is preserved; old core decisions are lost)
- **Related Commit**: `2c91985` feat: Context Preservation quality reinforcement — 18-item audit/reflection implementation

### ADR-016: E5 Empty Snapshot Guard — Multi-Signal Detection

- **Date**: 2026-02-20
- **Status**: Accepted
- **Context**: An empty snapshot with 0 tool_use was overwriting the existing rich `latest.md`. Simple size comparison could not accurately distinguish "small but meaningful" snapshots.
- **Decision**: Define "rich snapshot" via multi-signal detection (size ≥ 3KB OR ≥ 2 section markers), and protect it in both the Stop hook and save_context.py via the central functions `is_rich_snapshot()` + `update_latest_with_guard()`.
- **Rationale**: A single criterion (size only) has high false positive/negative. Multi-signal of size OR structural markers is more accurate.
- **Alternatives**: Always overwrite → rejected (data loss); compare size only → rejected (the small-but-rich case is not handled)
- **Related Commit**: `f76a1fd` feat: P1 hallucination containment + E5 Guard centralization

### ADR-017: Error Taxonomy 12 Patterns + Error→Resolution Matching

- **Date**: 2026-02-19
- **Status**: Accepted
- **Context**: When recording error patterns in the Knowledge Archive, the "unknown" classification dominated, making cross-session error analysis impossible.
- **Decision**: Classify errors with 12 regex patterns (file_not_found, permission, syntax, timeout, dependency, edit_mismatch, type_error, value_error, connection, memory, git_error, command_not_found). Apply negative lookahead and qualifier matching to prevent false positives. Detect successful tool invocations within 5 entries after an error with file-aware matching, and record resolutions.
- **Rationale**: Structured error classification is required to programmatically search for "how was this error solved in the past?" Resolution matching automatically links error-resolution pairs.
- **Alternatives**: Record raw error text → rejected (unsearchable; no pattern analysis)
- **Related Commits**: `ce0c393` fix: 2nd audit, 22 issues implemented, `eed44e7` fix: 3rd reflection, 5 items fixed

### ADR-018: context_guard.py Unified Dispatcher

- **Date**: 2026-02-17
- **Status**: Accepted
- **Context**: Connecting 4 events (Stop, PostToolUse, PreCompact, SessionStart) to separate scripts in the Global Hook (~/.claude/settings.json) makes configuration complex and duplicates common logic (path resolution, error handling).
- **Decision**: Use `context_guard.py` as the single entry point and route via the `--mode` argument. Only the Setup Hook runs directly from project settings (it is infrastructure verification before session start, so it is independent of the dispatcher).
- **Rationale**: A single entry point is easier to maintain and allows common logic (paths, errors) to be managed in one place.
- **Alternatives**: Independent scripts per event → rejected (configuration complexity increase, common logic duplication)
- **Related Commit**: `0f38784` feat: Fix broken hooks + optimize context memory for quality

---

## 4. Automation Modes

### ADR-019: Autopilot Mode — Auto-Approval at Human Checkpoints

- **Date**: 2026-02-17
- **Status**: Accepted
- **Context**: If a user must directly approve at every `(human)` stage during workflow execution, the user cannot step away during long-running workflows.
- **Decision**: When `autopilot.enabled: true` is set in SOT, `(human)` stages and `AskUserQuestion` are auto-approved with the quality-maximizing default. However, Hook exit code 2 still blocks unchanged (deterministic verification is not a proxy target for automation).
- **Rationale**: AI only proxies human judgment, and the deterministic verification of code is preserved as-is. All auto-approvals are recorded in the Decision Log to ensure transparency.
- **Alternatives**:
  - Full automation (ignore Hook blocks as well) → rejected (nullifies quality gates)
  - Time-based auto-approval (after N minutes of waiting) → rejected (artificial waiting, unproductive)
- **Related Commit**: `b0ae5ac` feat: Autopilot Mode runtime enforcement

### ADR-020: Autopilot Runtime Reinforcement — Hybrid Hook + Prompt

- **Date**: 2026-02-17
- **Status**: Accepted
- **Context**: The design intent of Autopilot (complete execution, no abbreviation, Decision Log recording) can be lost across session boundaries if enforced by prompt alone.
- **Decision**: Build a hybrid reinforcement system:
  - **Hook (deterministic)**: SessionStart injects the rules, snapshot preserves state as IMMORTAL, Stop detects missing Decision Logs
  - **Prompt (behavioral)**: Execution Checklist specifies the mandatory actions for each stage
- **Rationale**: Hooks act deterministically without depending on AI interpretation. Prompts guide AI behavior but do not guarantee it. The combination of both layers is the strongest.
- **Alternatives**: Prompt only → rejected (lost at session boundaries); Hook only → rejected (fine-grained behavioral guidance not possible)
- **Related Commit**: `b0ae5ac` feat: Autopilot Mode runtime enforcement

### ADR-021: Agent Team (Swarm) Pattern — 2-Layer SOT Protocol

- **Date**: 2026-02-18
- **Status**: Accepted
- **Context**: When parallel agents work simultaneously, it had to prevent concurrent writes to SOT while still allowing teammates to reference each other's deliverables.
- **Decision**: Only the Team Lead has SOT write permission; Teammates only produce deliverable files. Direct reference between teammates' deliverables is allowed only when a quality improvement is demonstrated (cross-verification, feedback loops).
- **Rationale**: A balance point between Absolute Criterion 2 (SOT) and Absolute Criterion 1 (Quality). Keep SOT single-write while allowing direct teammate references as an exception for quality.
- **Alternatives**: All teammates write SOT → rejected (violates Absolute Criterion 2); full isolation between teammates → rejected (cross-verification not possible)
- **Related Commit**: `42ee4b1` feat: Agent Team (Swarm) pattern integration

### ADR-022: Verification Protocol — Anti-Skip Guard + Verification Gate + pACS

- **Date**: 2026-02-19
- **Status**: Accepted
- **Context**: It was necessary to prevent issues where Autopilot moves to the next stage without a deliverable or marks completion merely formally.
- **Decision**: Introduce a 4-layer quality-guarantee architecture:
  - **L0 Anti-Skip Guard** (deterministic): deliverable file exists + minimum size (100 bytes)
  - **L1 Verification Gate** (semantic): self-verify that the deliverable achieves 100% of the Verification criteria
  - **L1.5 pACS Self-Rating** (confidence): Pre-mortem Protocol → score F/C/L on 3 dimensions → rework on RED (< 50)
  - **L2 Calibration** (optional): a separate verifier agent cross-verifies pACS
- **Rationale**: Physical verification (file existence), semantic verification (content completeness), and confidence verification (weakness awareness) are different dimensions. Each layer independently catches a different type of failure.
- **Alternatives**: Anti-Skip Guard only → rejected (empty files can pass); Verification Gate only → rejected (AI self-verification tends to overestimate)
- **Related Commit**: `f592483` feat: Verification Protocol added

### ADR-023: ULW (Ultrawork) Mode — A Universal Mode Operating Without SOT

- **Date**: 2026-02-20
- **Status**: Superseded by ADR-043
- **Context**: Autopilot is workflow-dedicated (SOT-based), but a mode that "does not stop until complete" was also needed for non-workflow general tasks (refactoring, document updates, etc.).
- **Decision**: Create ULW mode, which is activated by including `ulw` in the prompt. It operates without SOT via 5 execution rules (Sisyphus, Auto Task Tracking, Error Recovery, No Partial Completion, Progress Reporting). It is implicitly deactivated in a new session (no explicit deactivation required).
- **Rationale**: Autopilot is SOT-dependent and thus unsuited for general tasks. ULW is lightened with a TaskCreate/TaskList base, providing completion guarantees even without workflow infrastructure.
- **Alternatives**: Extend Autopilot → rejected (forcing SOT is excessive for general tasks); no mode → rejected (the issue of AI stopping midway is unresolved)
- **Related Commit**: `c7324f1` feat: ULW (Ultrawork) Mode implementation

---

## 5. Quality & Safety

### ADR-024: P1 Hallucination Containment — 4 Mechanisms

- **Date**: 2026-02-20
- **Status**: Accepted
- **Context**: There are tasks in the Hook system that must be 100% accurate repeatedly (schema validation, SOT write prevention, etc.), and relying on AI probabilistic judgment creates hallucination risk.
- **Decision**: Implement 4 deterministic mechanisms in Python code:
  1. **KI schema validation**: `_validate_session_facts()` — guarantees 10 required keys
  2. **Partial failure isolation**: archive failure does not block index update
  3. **SOT write pattern validation**: AST-based detection of SOT write attempts in Hook scripts
  4. **SOT schema validation**: `validate_sot_schema()` — 6-item structural integrity
- **Rationale**: "Tasks that must be 100% accurate repeatedly" must be performed by code, not AI (extreme application of the P1 principle). Code does not hallucinate.
- **Alternatives**: Ask AI to validate the schema → rejected (probabilistic, risk of omission); operate without validation → rejected (silent corruption risk)
- **Related Commit**: `f76a1fd` feat: P1 hallucination containment + E5 Guard centralization

### ADR-025: Atomic Write Pattern — Crash-Safe File Writing

- **Date**: 2026-02-18
- **Status**: Accepted
- **Context**: If the process crashes while Hook scripts are writing snapshots, archives, or logs, partial writes can corrupt files.
- **Decision**: Apply the atomic write pattern (temp file → `os.rename`) to all file writes. Protect concurrent access with `fcntl.flock` and ensure durability with `os.fsync()`.
- **Rationale**: `os.rename` is atomic on POSIX, so intermediate state is never exposed. Prior state is preserved intact even on process crash.
- **Alternatives**: Direct writes → rejected (partial writes on crash); database transactions → rejected (over-engineering)
- **Related Commit**: `2c91985` feat: Context Preservation quality reinforcement

### ADR-026: Decision-Quality Tag Ordering — IMMORTAL Slot Optimization

- **Date**: 2026-02-19
- **Status**: Accepted
- **Context**: In the snapshot's "key design decisions" section (15 slots), everyday intent declarations (the "I will do ..." pattern) were pushing out actual design decisions.
- **Decision**: Introduce 4-stage quality-tag-based ordering: `[explicit]` > `[decision]` > `[rationale]` > `[intent]`. Also extract comparison, trade-off, and selection patterns, so that high-signal decisions occupy the 15 slots with priority.
- **Rationale**: In limited slots, "I chose B instead of A, because..." is far more valuable for restoration than "I will do...".
- **Alternatives**: Chronological → rejected (recent intent pushes out older decisions); no filtering → rejected (noise overwhelms signal)
- **Related Commit**: `2c91985` feat: Context Preservation quality reinforcement

### ADR-047: Abductive Diagnosis Layer — Structured Diagnosis on Quality Gate FAIL

- **Date**: 2026-02-23
- **Status**: Accepted
- **Context**: In the 4-layer quality-guarantee (L0→L1→L1.5→L2), a structure that retries immediately on gate FAIL does not analyze "why did it fail?" This leads to repeated identical failures or inefficient retries.
- **Decision**: Insert a 3-step diagnosis (P1 pre-evidence collection → LLM judgment → P1 post-validation) between FAIL and retry. Implement as an additive-only layer that does not change the existing 4-layer QA. Diagnosis results are recorded only in `diagnosis-logs/` and SOT is not modified. Fast-Path (FP1-FP3) provides deterministic shortcut paths.
- **Rationale**: (1) Retry quality improvement — selecting a correction strategy matched to the failure cause, (2) Backward compatibility — with no diagnosis-logs/, existing behavior is preserved, (3) Cross-session learning — patterns are accumulated via diagnosis_patterns archiving in Knowledge Archive.
- **Alternatives**: (a) Add diagnostic state to SOT → rejected (SOT schema complexity increase, burden on Absolute Criterion 2), (b) Only increase retry count → rejected (root cause not analyzed, identical failures repeat), (c) Separate diagnosis agent → rejected (excessive complexity; diagnosis within the Orchestrator suffices)
- **Related Commit**: (pending)

### ADR-051: Claude Code v2.1 New Feature Research — Existing Design Validity Verification + Selective Adoption

- **Date**: 2026-03-02
- **Status**: Accepted
- **Context**: Investigated 5 new features in Claude Code v2.1 (Ralph Loop, Remote Control, Auto-memory, `/simplify` 3-agent parallel review, `/batch` parallel stage execution) via the YouTube video "Cascading Claude Code Updates" (Dev Brother) and claudefa.st technical documents. Performed three rounds of deep reflection (CCP Step 2 ripple-effect analysis + Absolute Criterion 1 quality verification + necessity re-examination) and judged adopt / hold / reject.
- **Decision**:
  1. **3-Lens parallel review — hold**: applying the `/simplify` 3-agent parallel pattern to L2 review. The existing `@reviewer` protocol (7 steps + 5 lenses + Pre-mortem + minimum 1 issue + independent pACS) is already systematic, and no empirically proven quality problem solved by 3-Lens was identified. Identified structural mismatches between pACS 3 dimensions and 3-Lens specialization (flaw 1), cross-area defect detection gap (flaw 2), and a P1 gap in the synthesis stage (flaw 3). Reconsider when cases accumulate in which `@reviewer` systematically misses a specific type of defect.
  2. **Batch Autopilot — rejected**: the `/batch` parallel-stage-execution pattern. Parallel execution of independent stages is **identical** in deliverable quality to sequential execution (no quality benefit). The single integer `current_step` is a load-bearing wall across 8+ files, and changing it would constitute an architecture change (violates the functional-improvement condition). The existing `(team)` mechanism already supports quality-based parallelization.
  3. **Sub-agent Persistent Memory — adopt only for @translator**: add `memory: project` to `@translator`. Accumulation of style judgments beyond glossary.yaml becomes possible. Do not add to `@reviewer` (past-bias risk) or `@fact-checker` (information freshness problem + conflict with independent verification principle). A natural extension of the RLM pattern.
  4. **Self-Optimization Command — rejected**: Workflow structural optimization is the responsibility of the workflow-generator skill. Improving the generator itself, rather than a post-hoc analysis tool, is the correct approach.
- **Key finding — existing design validity verification**:
  - `/simplify` 3-agent → already addressed by the existing 4-layer quality gate (L0→L1→L1.5→L2)
  - `/batch` parallel → already addressed by the existing `(team)` mechanism
  - Auto-memory → already addressed by the existing RLM pattern (glossary.yaml, Knowledge Archive, knowledge-index.jsonl)
  - Ralph Loop → the existing retry budget + Abductive Diagnosis is more fine-grained
  - Agent Teams → **identical pattern** to existing `(team)` stages + SOT single-write
- **Rationale**:
  - **Absolute Criterion 1 (Quality)**: every proposal is judged by "Is a quality benefit empirically demonstrated?" The criterion for adoption is the existence of a problem, not the appeal of the technology.
  - **Preservation of the existing**: strict application of the condition "this is a functional improvement, not creating a new workflow." The `current_step` load-bearing wall destruction is an architecture change and therefore rejected.
  - **RLM pattern preservation**: `@translator`'s `memory: project` is an extension of the RLM external memory object. Complementary to glossary.yaml.
- **Alternatives**:
  - Implement 3-Lens as 3 new agent .md files → rejected (invoking the existing `@reviewer` with different prompts 3 times has the same effect; new files are unnecessary)
  - Implement Batch as a `(team)` meta-stage → rejected (loss of per-stage quality gates)
  - Persistent memory on all 3 agents → rejected (@reviewer: past bias; @fact-checker: information staleness + independence undermined)
- **Related files**: `translator.md` (`memory: project` added)

---

## 6. Language & Translation

### ADR-027: English-First Execution Principle

- **Date**: 2026-02-17
- **Status**: Accepted
- **Context**: Conversation with the user is in Korean, but AI agents' work quality is highest in English. Producing deliverables directly in Korean degrades quality.
- **Decision**: When executing a workflow, every agent works in English and produces deliverables in English. Korean is provided via a separate translation protocol.
- **Rationale**: Direct realization of Absolute Criterion 1 (Quality). AI performs best in English, so English-first execution guarantees the highest quality.
- **Alternatives**: Direct generation in Korean → rejected (quality degradation); delegating language choice to the user → rejected (no consistency)
- **Related Commit**: `5b649cb` feat: Hub-and-Spoke universal system prompt

### ADR-028: @translator Sub-agent + glossary Persistent State

- **Date**: 2026-02-17
- **Status**: Accepted
- **Context**: When translating an English deliverable to Korean, a simple translation tool cannot guarantee consistency of domain terminology.
- **Decision**: Define the `@translator` sub-agent and maintain `translations/glossary.yaml` as an RLM external persistent state. Reference the glossary during translation to ensure terminology consistency and add new terms to the glossary.
- **Rationale**: Application of RLM's Variable Persistence pattern. The glossary maintains state across sub-agent invocations, so that translation quality improves as sessions accumulate.
- **Alternatives**: Re-specify translation rules each time → rejected (terminology inconsistency); external translation API → rejected (no support for domain-specific terminology)
- **Related Commit**: `5b649cb` feat: Hub-and-Spoke universal system prompt

---

## 7. Infrastructure

### ADR-029: Setup Hook — Infrastructure Health Verification Before Session Start

- **Date**: 2026-02-19
- **Status**: Accepted
- **Context**: Hook scripts depend on things like the Python environment, PyYAML, and directory structure; if those are broken, all hooks silent-fail.
- **Decision**: Register `setup_init.py` as a Setup Hook (`claude --init`) to auto-verify 7 items (Python version, PyYAML, script syntax ×6, directories ×2, .gitignore, SOT write patterns) before session start.
- **Rationale**: "Do not assume it works; verify every time." If Hooks silent-fail, context preservation is fully disabled, so preflight verification is essential.
- **Alternatives**: Manual checks → rejected (easy to forget); auto-install on first run → rejected (installing in user environment without permission)
- **Related Commit**: `2c91985` feat: Context Preservation quality reinforcement

### ADR-030: Truncation Constant Centralization — 10 Constants

- **Date**: 2026-02-19
- **Status**: Accepted
- **Context**: Constants for truncating lengths of Edit preview, error messages, etc. during snapshot generation were hard-coded into many functions, causing inconsistent truncation.
- **Decision**: Centrally define 10 truncation constants (`EDIT_PREVIEW_CHARS=1000`, `ERROR_RESULT_CHARS=3000`, `MIN_OUTPUT_SIZE=100`, etc.) in `_context_lib.py`.
- **Rationale**: Centrally defined constants are reflected everywhere with a single modification. Edit preview is 5 lines × 1000 chars to preserve edit intent/context, and error messages are 3000 chars to preserve the full stack trace.
- **Alternatives**: Inline into each function → rejected (risk of value inconsistency, omission during tuning)
- **Related Commit**: `2c91985` feat: Context Preservation quality reinforcement

### ADR-031: PreToolUse Safety Hook — Dangerous Command Blocking

- **Date**: 2026-02-20
- **Status**: Accepted
- **Context**: Among Claude Code's 6 blockable Hook events, only PreToolUse was unimplemented. Dangerous Git / file commands (git push --force, git reset --hard, rm -rf /, etc.) could be executed relying solely on AI judgment.
- **Decision**: Register `block_destructive_commands.py` as a PreToolUse Hook (matcher: Bash). Deterministically detect dangerous commands with 10 patterns (9 regex + 1 procedural rm check), block with exit code 2, and trigger Claude self-correction via stderr feedback.
- **Rationale**: P1 hallucination containment — dangerous-command detection is 100% deterministic via regex. No AI judgment intervenes. Runs independently (does not go through `context_guard.py`) — uses the `if test -f; then; fi` pattern to avoid the issue where the `|| true` pattern swallows exit code 2.
- **Alternatives**: (1) SOT write protection → held (Hook API does not distinguish agent roles); (2) Anti-Skip Guard reinforcement → held (Stop timing is post-hoc, so prevention is impossible)
- **Blocked patterns**: git push --force (NOT --force-with-lease), git push -f, git reset --hard, git checkout ., git restore ., git clean -f, git branch -D, git branch --delete --force (both orderings), rm -rf / or ~

### ADR-032: PreToolUse TDD Guard — Test File Modification Blocking

- **Date**: 2026-02-20
- **Status**: Accepted
- **Context**: Claude, during TDD, tends to modify the test code instead of the implementation code when tests fail. This violates the core TDD principle ("tests are invariant; only implementation is modified").
- **Decision**: Register `block_test_file_edit.py` as a PreToolUse Hook (matcher: `Edit|Write`). Activated only when the `.tdd-guard` file exists in the project root. Deterministically identify test files via 2-tier detection (Tier 1: directory name — test/tests/__tests__/spec/specs, Tier 2: file name pattern — test_*/*_test.*/*.test.*/*.spec.*/*Test.*/conftest.py), and use exit code 2 + stderr feedback to direct Claude to modify the implementation code instead.
- **Rationale**:
  - Reuses the P1 hallucination containment pattern — test file detection is 100% deterministic via regex/string matching
  - Same architecture as ADR-031 (`block_destructive_commands.py`) — standalone execution, `if test -f; then; fi` pattern, Safety-first exit(0)
  - The `.tdd-guard` toggle is independent of SOT (`state.yaml`) — TDD is used outside of workflows too, so SOT dependence is inappropriate
  - `REQUIRED_SCRIPTS` (D-7) synchronization on both sides includes it in the infrastructure-verification target of `setup_init.py` / `setup_maintenance.py`
- **Alternatives**:
  - Always block (no toggle) → rejected (would also block when writing tests, impractical)
  - Control via SOT `tdd_mode: true` → rejected (SOT is workflow-dedicated; TDD is general-purpose)
  - Post-warning in PostToolUse → rejected (the file is already modified, so prevention is impossible)
- **Related Commit**: (pending)

### ADR-033: Context Memory Optimization — success_patterns + Next Step IMMORTAL + Module-Level regex

- **Date**: 2026-02-20
- **Status**: Accepted
- **Context**: A full audit identified 3 Context Memory optimization opportunities. (1) The Knowledge Archive records only error_patterns and omits success patterns, (2) the "Next Step" section is implicitly included in the parent section without an independent IMMORTAL marker, (3) `_extract_decisions()`'s 8 regex + `_extract_next_step()`'s 1 regex + `_SYSTEM_CMD` are compiled on every call.
- **Decision**:
  1. Add the `_extract_success_patterns()` function — deterministically extract Edit/Write → successful Bash sequences and record them as the `success_patterns` field in the Knowledge Archive
  2. Promote the "Next Step" section to an independent `## ` header + `<!-- IMMORTAL: -->` marker — explicit preservation target in the Phase 7 hard truncate
  3. Move 10 regex patterns to module-level constants — compiled once per process
- **Rationale**:
  - success_patterns: RLM cross-session success pattern exploration is possible via `Grep "success_patterns" knowledge-index.jsonl`. Symmetric to error_patterns — just as we learn from failures, we learn from successes.
  - Next Step IMMORTAL: at session restoration, "what to do next" is a cognitive continuity anchor no less important than "what we are currently doing."
  - Module-level regex: recompiling 10 patterns on every run of the 30-second-interval Stop hook is unnecessary overhead.
- **Alternatives**:
  - Include Read in success_patterns → rejected (Read is exploration, not verification, so its signal as a "success pattern" is weak)
  - Split Next Step into a separate file → rejected (over-engineering; the IMMORTAL marker within the snapshot is sufficient)
- **Related Commit**: (pending)

### ADR-034: Adversarial Review — Enhanced L2 Quality Layer + P1 Hallucination Containment

- **Date**: 2026-02-20
- **Status**: Accepted
- **Context**: We wanted to introduce the Generator-Critic pattern (adversarial agents) to reduce hallucinations and raise deliverable quality. The existing L2 Calibration was "optional cross-verification" without a concrete implementation. Independent critical review was needed in both research and development work. The design was finalized after 3 rounds of critical reflection.
- **Decision**:
  1. Replace the existing L2 Calibration with **Adversarial Review (Enhanced L2)** — introduce two specialized agents, `@reviewer` (code/deliverable analysis, read-only) and `@fact-checker` (fact verification, web access)
  2. Add the `Review:` field as a workflow-stage property (identical pattern to the existing `Translation:`)
  3. Add 4 P1 deterministic validation functions to `_context_lib.py`: `validate_review_output()` (R1-R5 5 checks), `parse_review_verdict()` (regex-based issue extraction), `calculate_pacs_delta()` (arithmetic comparison of Generator-Reviewer scores), `validate_review_sequence()` (timestamp validation of Review→Translation ordering)
  4. 4-layer rubber-stamp prevention: adversarial persona + mandatory Pre-mortem + minimum 1 issue (P1 R5) + independent pACS scoring
  5. Execution order: L0 → L1 → L1.5 → Review(L2) → PASS → Translation
  6. Add a missing-Review detection safety net (`_check_missing_reviews()`) to the Stop hook
- **Rationale**:
  - **Enhanced L2 positioning**: the existing L2 is already "cross-verification," so adversarial review is a rigorous implementation of it. Reinforcing the existing layer lowers architectural complexity more than creating a new L3.
  - **2-agent separation (P2)**: code-logic analysis (Read-only) and fact verification (WebSearch) require completely different tools. Separated by principle of least privilege.
  - **Sub-agent choice**: a synchronous feedback loop reflecting review results immediately is needed, so a Sub-agent beats the Agent Team asynchronous pattern for quality maximization.
  - **P1 necessity**: validation of review-report existence/structure/verdict/issue count / pACS delta is a repetitive task that must be 100% accurate — hallucination risk if left to LLM. Enforced via Python regex / filesystem / arithmetic.
- **Alternatives**:
  - A single `@critic` agent → rejected (code analysis and fact verification have different tool profiles)
  - A new `(adversarial)` stage type → rejected (the `Review:` attribute is consistent with the existing `Translation:` pattern and backward compatible)
  - Creating L3 → rejected (reinforcing the existing L2 is cleaner)
  - Reviewer modifying files directly → rejected (read-only keeps role separation with the Generator)
- **Related Commit**: (pending)

### ADR-035: Comprehensive Audit — SOT Schema Extension + Quality Gate IMMORTAL + Error→Resolution Surfacing

- **Date**: 2026-02-20
- **Status**: Accepted
- **Context**: A comprehensive audit of the codebase identified 6 unimplemented/unoptimized areas. (1) pacs/active_team SOT schema not validated, (2) Quality Gate state lost across session boundaries, (3) dependency on manual Grep for prior-session error resolution experience, (4) silent failure when runtime directories are absent, (5) multi-stage transition information not reflected in snapshot headers, (6) CLAUDE.md documentation inconsistent with implementation. Among these, (2) and (3) were particularly important from a Context Memory quality-optimization perspective.
- **Decision**:
  1. Extend `validate_sot_schema()`: add S7 (pacs structure — dimensions F/C/L 0-100, current_step_score, weak_dimension) + S8 (active_team — name, status valid values) → 6 items → 8 items
  2. Introduce `_extract_quality_gate_state()`: extract the latest stage quality-gate results from pacs-logs/, review-logs/, verification-logs/ and preserve them as IMMORTAL snapshot sections
  3. Introduce `_extract_recent_error_resolutions()` (restore_context.py): read recent error→resolution patterns from the Knowledge Archive and automatically display up to 3 at SessionStart output
  4. Introduce `_check_runtime_dirs()` (setup_init.py): when SOT exists, auto-create verification-logs/, pacs-logs/, review-logs/, autopilot-logs/
  5. Display Phase Transition flow in snapshot header: in multi-stage sessions in the form `Phase flow: research(12) → implementation(25)`
  6. Full CLAUDE.md synchronization: ensure consistency across project tree, operating-principle tables, and the 3 Claude-usage levels
- **Rationale**:
  - **Quality Gate IMMORTAL**: if Verification Gate/pACS/Review progress state is lost after compact/clear, there is risk of wrong judgment on entering the next stage → preserve as IMMORTAL to guarantee quality-gate continuity across session boundaries (Absolute Criterion 1)
  - **Error→Resolution surfacing**: with manual Grep dependence, prior-session resolution experience is unused → auto-display at SessionStart to enable immediate resolution when the same error recurs (proactive use of the RLM pattern)
  - **SOT schema extension**: pacs and active_team are core states of Autopilot execution but lack schema validation, so vulnerable to hallucination → contained via P1 deterministic validation
  - **Runtime directories**: when directories are absent, file writes silently fail and Verification/pACS/Review logs are lost → pre-create at Setup time
- **Alternatives**:
  - Store quality-gate state in SOT → rejected (Hook is forbidden from writing SOT — Absolute Criterion 2)
  - Include Error→Resolution in snapshot body → rejected (snapshot size increase; SessionStart output is more immediate)
  - Create runtime directories individually in each Hook → rejected (once-at-Setup is more efficient and deterministic)
- **Related Commit**: (pending)

### ADR-036: Predictive Debugging — Preemptive Warning for Risky Files Based on Error History

- **Date**: 2026-02-20
- **Status**: Accepted
- **Context**: When Claude edits files, there was no preemptive warning about files that had repeatedly produced errors in past sessions. Although error_patterns accumulate in the Knowledge Archive (ADR-017), they were not being used for prevention, only post-hoc analysis. The design was finalized after 3 rounds of critical reflection, verifying P1 hallucination containment and architectural consistency.
- **Decision**:
  1. Add the `aggregate_risk_scores()` function to `_context_lib.py` — aggregate error_patterns from the Knowledge Archive per file and compute a risk score (P1 deterministic arithmetic)
  2. `validate_risk_scores()` (RS1-RS6) schema validation — same P1 pattern as `validate_sot_schema()` (S1-S8), `validate_review_output()` (R1-R5), etc.
  3. Register `predictive_debug_guard.py` as a PreToolUse Hook (matcher: `Edit|Write`) — emit stderr warning when the risk score exceeds the threshold (exit code 0, warning-only)
  4. Generate the risk-scores.json cache at SessionStart in `restore_context.py` — one-time aggregation then cache; PreToolUse only reads the cache (performance optimization)
  5. Weighting system: `_RISK_WEIGHTS` (weights for 13 error types) × `_RECENCY_DECAY_DAYS` (3-tier decay at 30 days / 90 days / infinity)
  6. Cold start guard: no warnings if fewer than 5 sessions (prevents false positives from insufficient data)
- **Rationale**:
  - **L-1 layer**: unlike the existing Safety Hook (L0 blocking), a new layer that **predicts** errors and preemptively draws Claude's attention. It does not block and only warns, so it does not interfere with the workflow.
  - **Extension of ADR-017**: if Error Taxonomy is infrastructure for **classifying** errors, Predictive Debugging is a higher layer that **aggregates the classified data for use in prediction**. Consumes the same error_patterns schema.
  - **Self-contained Hook**: `predictive_debug_guard.py` does not import `_context_lib.py`. Since a new Python process is created on every Edit/Write, loading a 4,500-line module must be avoided (constants duplicated via the D-7 pattern).
  - **Cache pattern**: aggregate once at SessionStart → JSON cache → PreToolUse only reads cache. Limits O(N) aggregation to once per session.
  - **Startup non-support trade-off**: the SessionStart matcher is `clear|compact|resume`, so the cache is not created at the very first startup. Depends on a previous cache (within 2 hours), or created on the first compact/clear. An intentional choice to separate the concerns of restoration and cache creation.
- **Alternatives**:
  - Scan knowledge-index directly on every Edit/Write → rejected (O(N) repetition, severe performance)
  - Block with exit code 2 → rejected (prediction is probabilistic; blocking is excessive)
  - Import `_context_lib.py` → rejected (delays PreToolUse process start)
  - Layer C (auto-analysis in Stop hook) → rejected (B+A suffices; Stop timeout risk)
- **Related ADRs**: ADR-017 (Error Taxonomy — provides error_patterns schema), ADR-024 (P1 Hallucination Containment — RS1-RS6 pattern), ADR-031 (PreToolUse Safety Hook — standalone execution architecture)
- **Related Commit**: (pending)

### ADR-037: Comprehensive Audit II — pACS P1 Validation + L0 Anti-Skip Guard Codification + IMMORTAL Boundary Fix + Context Memory Optimization

- **Status**: Accepted
- **Date**: 2026-02-20
- **Context**: A comprehensive codebase audit identified 3 CRITICAL, 5 HIGH, and 6 MEDIUM defects. The core types were: features specified in design docs but not backed by code (pACS validation, L0 Anti-Skip Guard), logical bugs in code (IMMORTAL boundary detection), and inconsistencies between documents (script count, missing project tree).
- **Decision**:
  1. **C1: IMMORTAL boundary detection fix** — in Phase 7 compression, change `if` → `elif` for marker-priority boundary detection. Fixes the bug where IMMORTAL mode was turned off when a non-IMMORTAL section header sits on the same line as the IMMORTAL marker. Also adds the truncation notice as an IMMORTAL section.
  2. **C2+C3: L0 Anti-Skip Guard + pACS P1 validation codification** — implement `validate_step_output()` (L0a-L0c: file exists, minimum size, non-whitespace) + `validate_pacs_output()` (PA1-PA6: file exists, minimum size, dimension scores, Pre-mortem, min() arithmetic, Color Zone) in `_context_lib.py`. Newly create the `validate_pacs.py` standalone script.
  3. **H1: Team Summaries KI archive** — the `_extract_team_summaries()` function preserves SOT's `active_team.completed_summaries` in the Knowledge Archive. Prevents loss during snapshot rotation.
  4. **H2+H3: Orchestrator role + Sub-agent protocol explicit** — add to AGENTS.md: Orchestrator = main session, Team Lead = Orchestrator (in team stage), Sub-agent Task-tool invocation protocol, and the 7-step (team) stage Task Lifecycle.
  5. **H4: Task Lifecycle standard flow** — add to workflow-template.md the 6-step flow: TeamCreate → TaskCreate → work → SendMessage → SOT update → TeamDelete.
  6. **M1: Decision Slot expansion** — 15 → 20 slots, proportional allocation (high-signal up to 15 + intent the remainder).
  7. **M4: Next Step extraction window** — expand from 3 → 5 assistant responses.
- **Rationale**:
  - **Design-implementation consistency**: if the L0 Anti-Skip Guard and pACS validation specified in design documents (CLAUDE.md, AGENTS.md) do not exist in code, the 4-layer quality-guarantee system effectively shrinks to 2 layers (L1 Verification + L1.5 pACS self-scoring). Design intent is enforced by code implementation.
  - **Severity of IMMORTAL boundary bug**: Phase 7 hard truncate triggers only in extreme situations (context overflow), so the bug is hard to find and, when it triggers, core context (Autopilot state, ULW state, Quality Gate state) is lost. Preemptive fixing is essential.
  - **Context Memory quality optimization**: Decision Slot expansion and Next Step window expansion improve session-restoration quality without increasing token cost (they only widen the preservation scope of already-generated data).
- **Alternatives**:
  - Keep pACS / L0 as prompt-based validation only → rejected (violates P1 — tasks requiring repeated 100% accuracy must be enforced by code)
  - Change IMMORTAL boundary to regex-based → rejected (the current marker-based approach is sufficiently deterministic; additional complexity is unnecessary)
  - Expand Decision Slot to unlimited → rejected (unlimited expansion admits noise; 20 slots is empirically appropriate)
- **Related ADRs**: ADR-024 (P1 Hallucination Containment — extension), ADR-035 (Comprehensive Audit I — SOT schema + Quality Gate), ADR-033 (Context Memory Optimization — extension)
- **Related Commit**: (pending)

---

## 8. Heredity (Inheritance Design)

### ADR-038: DNA Inheritance — Structural Inheritance of the Parent Genome

- **Date**: 2026-02-20
- **Status**: Accepted
- **Context**: `soul.md` philosophically defined the reason for AgenticWorkflow's existence (parent organism → DNA inheritance to children), but the actual production line `workflow-generator` lacked an inheritance mechanism. The philosophy was not structurally connected to the codebase and production process.
- **Decision**:
  1. Add the Genome Inheritance Protocol to `SKILL.md` — mandate inclusion of the Inherited DNA section when creating a child
  2. Add the `Inherited DNA (Parent Genome)` section to the base template in `workflow-template.md`
  3. Add `parent_genome` metadata to `state.yaml.example` — lineage tracking
  4. Integrate the inheritance concept into core documents (CLAUDE.md, AGENTS.md, README.md, ARCHITECTURE, 3 Spokes, 3 Agents, manual)
- **Rationale**: "Inheritance is not optional — it is structural." The meaning of inheritance is realized only when the child embeds the DNA. Mere reference allows selective application, so quality consistency cannot be guaranteed.
- **Alternatives**:
  - Only add a reference link to soul.md → rejected (reference is not inheritance — selective application possible)
  - Copy the whole soul.md into child workflows → rejected (unnecessary duplication, maintenance burden)
  - Extract DNA into a separate `dna.yaml` file and auto-inject → rejected (over-engineering; document-based approach is more appropriate)
- **Impact scope**: 16 documents modified (Python Hook scripts unmodified, SOT schema validation unmodified — `parent_genome` is allowed as an unknown key)
- **Related ADRs**: ADR-001 (workflow = intermediate artifact), ADR-009 (RLM theoretical foundation), ADR-010 (architecture document)
- **Related Commit**: `9b99e36`

### ADR-039: Workflow.md P1 Validation — Code-Level Validation of DNA Inheritance

- **Date**: 2026-02-20
- **Status**: Accepted
- **Context**: ADR-038 implemented DNA Inheritance with a document-based approach, but Critical Reflection identified a P1 validation gap. The existing P1 system (pACS/Review/Translation/Verification/L0) all has deterministic code validation, but the presence of Inherited DNA in the generated workflow.md relies only on prompt-based enforcement. Contradicts the P1 philosophy ("code doesn't lie").
- **Decision**:
  1. Add the `validate_workflow_md()` function to `_context_lib.py` — W1-W6 deterministic validation (file existence, minimum size, Inherited DNA header, Inherited Patterns table ≥ 3 rows, Constitutional Principles, Coding Anchor Points (CAP) reference)
  2. Create the `validate_workflow.py` standalone script — identical pattern to the existing `validate_*.py`
  3. Recommend invoking it at `SKILL.md` Step 13 (Distill verification)
  4. Add to `REQUIRED_SCRIPTS` (D-7 synchronization: setup_init.py + setup_maintenance.py)
- **Rationale**: ~80 lines restore P1 consistency. Not "over-engineering" but a natural extension of the existing pattern. Prevents silent failure under Autopilot.
- **Relationship to ADR-038**: partially revises ADR-038's "Python Hook unmodified" decision — Hooks remain unmodified, but a standalone validation script is added to close the P1 gap.
- **Related ADR**: ADR-038 (DNA Inheritance)

### ADR-040: Comprehensive Audit III — Strengthening 4-Layer QA Enforcement (C1r/C2/W4/C4s/W7)

- **Date**: 2026-02-20
- **Status**: Accepted
- **Context**: The comprehensive codebase audit (round 1) + adversarial self-verification (round 2) identified 5 inconsistencies between "design intent vs. code enforcement" in the 4-layer QA. Round 1 audit reported 15 items → round 2 reflection removed 2 misdiagnoses (original C1, W2) and held 2 (C3, W3) → finalized to 5.
- **Decision**:
  1. **C1r**: in `validate_translation.py`, always validate Review verdict=PASS even without `--check-sequence` (existing `validate_review_sequence()` unchanged — maintains timestamp responsibility)
  2. **C2**: add PA7 to `validate_pacs_output()` — return FAIL when pACS < 50 (RED), blocking stage progression
  3. **W4**: in `validate_review.py`, surface a warning message in warnings[] when pACS Delta ≥ 15
  4. **C4s**: add `_check_missing_verifications()` to `generate_context_summary.py` — stderr warning when pacs-log exists but verification-log does not (follows existing `_check_missing_reviews()` pattern)
  5. **W7**: specify in `SKILL.md` Step 7 "Verification is mandatory for every agent execution stage; only (human) is the exception"
- **Rationale**: ~41 lines convert prompt-level rules to code-level enforcement. No change to existing function responsibilities — only reinforcement. No SOT schema changes.
- **Rejected items**:
  - Original C1 (validate_review_sequence fix) → misdiagnosis — the function already checks verdict. The problem is that invocation is optional
  - W2 (Quality Gate IMMORTAL promotion) → already implemented
  - C3 (SOT retry_count) → outside SOT scope — file counting is appropriate
  - W3 (KI quality metrics) → current pacs_min is sufficient — revisit on RLM demand
- **Related ADRs**: ADR-022 (Verification Protocol), ADR-037 (pACS P1), ADR-034 (Adversarial Review)

### ADR-041: Coding Anchor Points (CAP-1~4)

- **Date**: 2026-02-23
- **Status**: Accepted
- **Context**: CCP (Absolute Criterion 3) defines "what to do" during code change (3-step procedure), but "what attitude to do it with" (mindset) was not specified. 4 attitude norms — Think Before Coding, Simplicity First, Goal-Based Execution, Surgical Changes — are needed as preconditions for executing CCP.
- **Decision**: Define CAP-1~4 as a subsection (`#### Coding Anchor Points`) within CCP. Fully defined in AGENTS.md (Hub); compressed reference in CLAUDE.md / 3 Spokes; add 2 observation items for CAP-2 / CAP-4 to reviewer.md's existing Technical Quality lens; add a 1-line reference to ARCHITECTURE.md; add a 1-line inclusion of CAP to SKILL.md Genome Inheritance.
- **Rationale**: (1) CAP is an attitudinal expression (gene expression) of CCP, so it is not an independent genome component — no change to soul.md's genome table (cascade 0). (2) Enforcement of CAP **behavior** is P1-impossible — attitudes are semantic and cannot be deterministically verified. (3) 0 changes to existing Hook / SOT / validation scripts.
- **Alternatives**:
  - Create an independent §2.5 section → rejected (phantom hierarchy; relationship to CCP unclear)
  - Add a row to soul.md's genome table → rejected (12→13 cascade, chain changes across 6+ files)
  - Add a 6th lens to reviewer.md → rejected (@reviewer reviews deliverables; CAP-1/CAP-3 are process attitudes that cannot be observed in deliverables)
  - P1 Python enforcement (behavior validation) → rejected (attitude ≠ structure; semantic judgment cannot be verified via deterministic code, mass-producing false positives)
- **Follow-up fix**: Critical Reflection identified a Category Error — enforcement of CAP **behavior** (semantic, P1-impossible) vs. validation of CAP **document propagation** (structural, P1-possible) are different problems. Whether a generated workflow.md structurally contains CAP references is deterministically verifiable, so W6 (presence of Coding Anchor Points reference) validation is added to ADR-039's `validate_workflow_md()`. This does not contradict ADR-041's "behavior P1 rejection" — W6 is the P1 for document propagation, not behavior.
- **Related ADRs**: ADR-005 (CCP), ADR-038 (DNA Inheritance), ADR-039 (W6 addition)

### ADR-042: Hook Setting Consolidation — Global → Project

- **Date**: 2026-02-23
- **Status**: Accepted
- **Context**: Existing Hook settings were split between Global (`~/.claude/settings.json`) and Project (`.claude/settings.json`), requiring a user who `git clone`s to manually install 7 global Hooks before the codebase works correctly. An asymmetry existed: agents (`.claude/agents/`) are auto-shared at the project level, but only Hooks required global installation.
- **Decision**: Move all 7 global Hooks (Stop, PostToolUse, PreCompact, SessionStart, PreToolUse ×3) to `.claude/settings.json` (Project). Remove the hooks section from the global settings. At the same time, unify the `|| true` pattern (latent bug that swallows exit code 2) to the `if test -f; then; fi` pattern.
- **Rationale**: (1) `git clone` alone auto-applies agents + Hooks + skills — zero-config onboarding. (2) Claude Code supports all Hook events at the project level — no feature restrictions. (3) Switching `|| true` → `if; fi` ensures exit code 2 safely propagates when future blocking features are added.
- **Impact scope**: `.claude/settings.json` (Hook merge), `~/.claude/settings.json` (hooks removed), CLAUDE.md (Hook location description), ARCHITECTURE.md (configuration table), 4 Python docstrings, README.md, AGENTS.md, claude-code-patterns.md — 11 files total
- **Alternatives**: Provide a global installation script → rejected (requires an additional installation step; not auto-applied)
- **Related ADRs**: ADR-012 (Hook-based context preservation), ADR-015 (context_guard.py unified dispatcher)

### ADR-043: ULW Redesign — Orthogonal Thoroughness Overlay

- **Date**: 2026-02-23
- **Status**: Accepted
- **Supersedes**: ADR-023
- **Context**: ADR-023 designed ULW as an "alternative" to Autopilot and stipulated an exclusive relationship (Autopilot takes precedence when both are active). However, the user's intent was a "completeness overlay." Autopilot deals with automation (HOW) and ULW deals with thoroughness (HOW THOROUGHLY), so the two axes are orthogonal.
- **Decision**: Redesign ULW as a **2-axis model orthogonal to Autopilot**. Consolidate the existing 5 execution rules into 3 reinforcement rules (Intensifiers):
  1. **I-1. Sisyphus Persistence** — consolidates existing Sisyphus Mode + Error Recovery + No Partial Completion. Up to 3 retries; each attempt uses a different approach
  2. **I-2. Mandatory Task Decomposition** — consolidates existing Auto Task Tracking + Progress Reporting
  3. **I-3. Bounded Retry Escalation** — new. No more than 3 retries on the same target; escalate to the user when exceeded
- **Rationale**: (1) The "Autopilot takes precedence" rule conflicted with ULW's reinforcement purpose. (2) The weakness that ULW lacks verification compared to Autopilot (no L0-L2) is naturally resolved in the orthogonal model — ULW adds retries on top of existing quality gates. (3) Consolidating 5→3 rules removes conceptual redundancy and introduces a clear boundary of "3-retry limit."
- **Alternatives**: Keep ADR-023 → rejected (2-axis orthogonality matches actual usage patterns); unlimited retries → rejected (infinite-loop risk)
- **Impact scope**: CLAUDE.md, AGENTS.md, `_context_lib.py`, `restore_context.py`, `generate_context_summary.py`, DECISION-LOG.md, README.md, USER-MANUAL.md, ARCHITECTURE.md, GEMINI.md, copilot-instructions.md, agenticworkflow.mdc, soul.md — 13 files total. Additions: `validate_retry_budget.py` (P1 retry-budget containment — RB1-RB3, --check-and-increment atomic mode), `setup_init.py`/`setup_maintenance.py` (REQUIRED_SCRIPTS D-7 synchronization) — 16 files total

### ADR-044: G1 — Cross-Step Traceability

- **Date**: 2026-02-23
- **Status**: Accepted
- **Context**: The existing 4-layer quality guarantee verifies each stage vertically, but horizontal connections between stages (whether the Step 5 analysis was actually derived from the Step 1 research) cannot be verified.
- **Decision**: Add "cross-step traceability" as the 5th Verification criterion type. Make inter-stage logical connections explicit via the inline marker `[trace:step-N:section-id:locator]`. P1 validation script `validate_traceability.py` (CT1-CT5).
- **Rationale**: In Agentic RAG research, "absence of connectivity between chunks" was identified as a core issue. Apply the same principle between workflow stages.
- **Alternatives**: (1) Only natural-language references — rejected (deterministic validation impossible). (2) Whole-deliverable embedding comparison — rejected (excessive infrastructure requirement).
- **Related files**: `_context_lib.py`, `validate_traceability.py`, `generate_context_summary.py`, `setup_init.py`, `setup_maintenance.py`, `AGENTS.md`, `workflow-template.md`

### ADR-045: G2 — Team Intermediate Checkpoint Pattern (Dense Checkpoint Pattern)

- **Date**: 2026-02-23
- **Status**: Accepted
- **Context**: In `(team)` stages, when Team Lead verification occurs after the Teammate completes the entire Task, early-direction errors found then require full rework.
- **Decision**: Add the Dense Checkpoint Pattern (DCP) design pattern. CP-1 (direction setting) → CP-2 (intermediate deliverable) → CP-3 (final deliverable). Use only the existing TaskCreate + SendMessage primitives; no new infrastructure.
- **Rationale**: Apply the "intermediate reward signal" concept from Princeton's Fuzzy Graph Reward research — convert the sparse reward of evaluating only the final deliverable into a dense reward.
- **Alternatives**: (1) Track CP state in SOT — rejected (complexity of schema change not required). (2) Hook-based auto-CP — rejected (SendMessage-based flexibility is better suited).
- **Related files**: `claude-code-patterns.md`, `workflow-template.md`, `SKILL.md`

### ADR-046: G3 — Domain Knowledge Structure

- **Date**: 2026-02-23
- **Status**: Accepted
- **Context**: Existing verification checks only structural quality. The validity of domain-specialized reasoning (medicine: symptoms→disease; law: precedent→principle) cannot be verified.
- **Decision**: Add the `domain-knowledge.yaml` schema + the `[dks:entity-id]` reference marker pattern. Build in the Research stage; use as verification criteria in Implementation. P1 validation script `validate_domain_knowledge.py` (DK1-DK7). Optional pattern — not every workflow needs it.
- **Rationale**: Embed the "KG (Knowledge Graph)-based accuracy improvement" pattern of Hybrid RAG into the workflow genome. Child systems express it matched to their domain.
- **Alternatives**: (1) A full KG DB infrastructure — rejected (excessive dependency). (2) Natural-language verification only — rejected (P1 deterministic validation impossible). (3) Mandatory pattern — rejected (burdens domains such as code generation and blogs where it is unnecessary).
- **Related files**: `_context_lib.py`, `validate_domain_knowledge.py`, `generate_context_summary.py`, `setup_init.py`, `setup_maintenance.py`, `state.yaml.example`, `AGENTS.md`, `soul.md`

### ADR-048: Full-Sweep-Based System Consistency Reinforcement

- **Date**: 2026-02-23
- **Status**: Accepted
- **Context**: A full sweep of the codebase discovered doc-code inconsistencies (NEVER DO conflict, undocumented D-7 instance, logical contradiction between I-3 and the quality-gate retry limit). A structural vulnerability was confirmed in which the LLM can prioritize documents over code and take wrong action.
- **Decision**:
  1. Raise quality-gate retry limits DEFAULT 2→10, ULW 3→15 (path B: sufficient persistence + Abductive Diagnosis mandatory)
  2. Add the P1 doc-code sync validation function (`_check_doc_code_sync()`) to `setup_maintenance.py`: DC-1 (NEVER DO ↔ code constants), DC-2 (D-7 Risk constants), DC-3 (D-7 ULW patterns), DC-4 (D-7 retry limits)
  3. Specify exception "(quality gates apply a separate budget)" in I-3 Bounded Retry Escalation
  4. Document D-7 instance #5: retry-limit 3-file sync (`validate_retry_budget.py` ↔ `_context_lib.py` ↔ `restore_context.py`)
  5. Agent reinforcement: translator Review-context awareness, fact-checker Pre-mortem→pACS linkage
- **Rationale**: In a system where "documents = specification," doc-code inconsistency equals runtime behavior error. The retry-limit increase reflects the user's requirement that "scanning success is the most important goal of the workflow." P1 doc-code sync prevents recurrence of the same bug class.
- **Alternatives**: (1) Unlimited retries (path C) — rejected (I-3 safety catch disabled; infinite-loop risk). (2) Intermediate raise (path A, 5/7) — rejected (user selected path B).
- **Related files**: `validate_retry_budget.py`, `_context_lib.py`, `restore_context.py`, `setup_maintenance.py`, `CLAUDE.md`, `AGENTS.md`, `ARCHITECTURE.md`, 3 Spokes, `translator.md`, `fact-checker.md`, `maintenance.md`, `claude-code-patterns.md`, `state.yaml.example`

### ADR-049: CLAUDE.md Lightening — Switch to TOC Pattern

- **Date**: 2026-03-01
- **Status**: Accepted
- **Context**: A comparative analysis of Anthropic's and OpenAI's harness-engineering principles identified a structural problem: CLAUDE.md (512 lines) consumes context excessively every turn. Anthropic recommendation: "Minimize CLAUDE.md — Would removing this cause mistakes? If not, cut it." OpenAI principle: "AGENTS.md as Table of Contents (~100 lines)."
- **Decision**:
  1. Lighten CLAUDE.md from 512 → 160 lines (69% reduction) — keep only TOC + mandatory behavioral directives
  2. Split detailed protocols into `docs/protocols/`: autopilot-execution.md, quality-gates.md, ulw-mode.md, context-preservation-detail.md, code-change-protocol.md (5 files)
  3. Insert on-demand reference pointers into CLAUDE.md ("Must read before workflow execution: docs/protocols/autopilot-execution.md")
  4. Update the DC-1 check path in `setup_maintenance.py` to `docs/protocols/autopilot-execution.md`
- **Rationale**: The context window is the most important resource. Loading a checklist (~120 lines) that is only needed during workflow execution every turn of general conversation is token waste. Switching to lazy loading (on-demand Read) saves ~350 lines in non-workflow sessions.
- **Alternatives**: (1) Keep CLAUDE.md and lighten only AGENTS.md — rejected (CLAUDE.md is auto-loaded every turn, so lightening it has a larger effect). (2) Auto-merge the full content via @import — rejected (Claude Code does not support @import; even if it did, always-loading would lose the lazy-loading benefit).
- **Related files**: `CLAUDE.md`, `docs/protocols/*.md` (5 files), `setup_maintenance.py`

### ADR-050: Security Hardening — 4-Layer Defense System + claude-forge Security Insights

- **Date**: 2026-03-02
- **Status**: Accepted
- **Context**: A full sweep of claude-forge (ADR ref: claude-forge-analysis.md) discovered a 6-layer security system (40+ deny patterns, 4 security hooks, rate-limiter, 2-pass secret scan). AgenticWorkflow had only 1.5 layers (1 PreToolUse + 0 settings.json deny). Three vulnerabilities confirmed: secret leakage, code injection, and network exfiltration.
- **Decision**:
  1. **Layer 0 (settings.json deny)**: add 18 static blocking patterns — pipe injection (curl/wget|sh), system commands (sudo, chmod 777, osascript, crontab, mkfs, dd), package publishing (npm/yarn/pnpm publish), sensitive-file writes (~/.ssh/*, ~/.zshrc, ~/.bashrc, ~/.profile)
  2. **Layer 1 (PreToolUse extension)**: add NETWORK_PATTERNS (curl/wget|sh) + SYSTEM_PATTERNS (dd, mkfs) to `block_destructive_commands.py` — Defense in Depth with Layer 0
  3. **Layer 2a (PostToolUse new)**: `output_secret_filter.py` — read actual tool output from transcript JSONL, 2-pass scan across 25+ secret patterns (raw + base64/URL decoded), security.log SOT (fcntl.flock atomic write, chmod 600)
  4. **Layer 2b (PostToolUse new)**: `security_sensitive_file_guard.py` — check 12 security patterns on Edit|Write target files (.env, *.pem, credentials.*, cloud credentials, K8s secrets, Terraform state, etc.), session-level dedup (/tmp marker)
- **Rationale**:
  - **CRITICAL finding**: PostToolUse's `tool_response` is `{}` (empty object) — the original design (tool_response scanning) is invalid. transcript JSONL tail-read is essential to obtain the actual output.
  - **P1 principle compliance**: every security judgment is deterministic Python (regex, string matching, JSON parsing). 0% AI judgment.
  - **Quality > speed (Absolute Criterion 1)**: In 2nd reflection, the speed-optimization design of merging security_sensitive_file_guard.py into predictive_debug_guard.py was withdrawn. SRP (Single Responsibility Principle) violation — security and debugging are independent concerns.
  - **SOT compliance (Absolute Criterion 2)**: security.log is newly introduced as a security event audit log. fcntl.flock guarantees atomic writes. (4th reflection: corrected to audit log, not SOT — no programmatic reading)
  - Safety-first on every hook: `exit(0)` on internal error (never block Claude).
- **Alternatives**:
  - (1) Directly port claude-forge hooks → rejected (remote-session-dedicated design; OPENCLAW_SESSION_ID gating is meaningless locally)
  - (2) tool_response-based scan → ~~rejected~~ re-adopted in 4th reflection (tool_response actually contains data — Bash: stdout/stderr, Read: file.content. Implemented as Tier 1 extraction path)
  - (3) Merge security_sensitive_file_guard into predictive_debug_guard → rejected (SRP violation, Absolute Criterion 1)
- **Verification**: output_secret_filter.py 44/44 tests pass (22 unit + 8 Tier 3 integration + 9 Tier 1 integration + 5 Tier 2 integration), security_sensitive_file_guard.py 44/44 tests pass, block_destructive_commands.py 43/43 tests pass
- **Related files**: `settings.json`, `block_destructive_commands.py`, `output_secret_filter.py` (new), `security_sensitive_file_guard.py` (new), `_test_secret_filter.py` (new), `_test_sensitive_file_guard.py` (new), `_test_block_destructive.py` (new)

---

## 2. Phase 2: Sub-agent Orchestration

### ADR-051: Sub-agent Categorization Rules — Explicit Fork Context Decisions

- **Date**: 2026-04-24
- **Status**: Approved (Implementation Ready)
- **Context**: Sub-agents (@translator, @reviewer, @fact-checker) execute within the Orchestrator context, but need isolation for specific operations. Without explicit categorization, fork context decisions were ad-hoc.
- **Decision**: Define 3-tier categorization rules:
  1. **Always Fork** (@translator, @reviewer): Sub-agent needs isolated fork context for persistent state (glossary) or independent calibration (L2 review)
  2. **Always Fresh** (@fact-checker): Stateless verification; no accumulated context needed
  3. **Team Decision** (new agents): First invocation deferred to team; subsequent invocations automatic via CATEGORIZATION dict
- **Rationale**: 
  - Eliminates 128 ambiguous fork-context combinations into 4 deterministic paths
  - Pre-invocation validation prevents unknown agents from executing
  - SOT recording (state.yaml invocations[]) enables audit trail
- **Alternatives**:
  - (1) No categorization (ad-hoc per invocation) → rejected (non-deterministic, hard to debug)
  - (2) All agents always fork → rejected (glossary would be scattered per-fork; inefficient for read-only access)
  - (3) All agents fresh context → rejected (@translator needs glossary.yaml persistence)
- **Implementation files**: `AGENTS.md` (§5.1.5, §5.2), `.claude/hooks/scripts/pre_subagent_invocation.py`, `prompt-runner/state_manager.py`, `DECISION-LOG.md` (this section)
- **Related Commit**: `b55d161` feat: Quality gates (L0-L2) for P1+P2 implementation

### ADR-001a (Phase 2 Template): Sub-agent Categorization — [Agent Name]

Use this template when introducing a **new Sub-agent** to the system:

```markdown
### ADR-XXX: Sub-agent Categorization — @new-agent

- **Date**: YYYY-MM-DD
- **Status**: Approved (pending Phase 2a PR merge)
- **Context**: 
  - Purpose: [Why this Sub-agent is needed]
  - First invocation: [Workflow stage where it first runs]
  - Context depth estimate: [high/medium/low — complexity of context needed]

- **Decision**: 
  - Fork Rule: [always_fork | always_fresh | team_decision]
  - Rationale: [Why this rule is chosen]

- **Rationale**: 
  - [Factor 1 supporting the decision]
  - [Factor 2]
  - [Factor 3]

- **Alternatives**:
  - (1) [Alternative rule] → rejected ([reason])
  - (2) [Alternative rule] → rejected ([reason])

- **Implementation**:
  1. Add entry to CATEGORIZATION dict in `.claude/hooks/scripts/pre_subagent_invocation.py`
  2. Update `AGENTS.md` § 5.2 Sub-agent Categorization Table (add row)
  3. Create/update `.claude/agents/@new-agent.md` with instructions
  4. Test: `python3 .claude/hooks/scripts/pre_subagent_invocation.py` validates the new agent

- **Related files**: 
  - `.claude/hooks/scripts/pre_subagent_invocation.py` (CATEGORIZATION dict)
  - `AGENTS.md` § 5.2 (Sub-agent Categorization Table)
  - `.claude/agents/@new-agent.md` (Agent instructions)
```

---

## Appendix: Commit-History-Based Timeline

| Date | Commit | Decision |
|------|--------|----------|
| 2026-02-16 | `348601e` | ADR-001~007: Project foundation (goal, Absolute Criteria, 3-stage structure, SOT, CCP) |
| 2026-02-16 | `e051837` | ADR-009: RLM theoretical foundation adopted |
| 2026-02-16 | `feba502` | ADR-010: Independent architecture document separated |
| 2026-02-16 | `bb7b9a1` | ADR-012: Hook-based Context Preservation System |
| 2026-02-17 | `d1acb9f` | ADR-013: Knowledge Archive |
| 2026-02-17 | `7363cc4` | ADR-014: Smart Throttling |
| 2026-02-17 | `5b649cb` | ADR-008, 027, 028: Hub-and-Spoke, English-First, @translator |
| 2026-02-17 | `b0ae5ac` | ADR-019, 020: Autopilot Mode + runtime reinforcement |
| 2026-02-18 | `42ee4b1` | ADR-021: Agent Team (Swarm) pattern |
| 2026-02-18~19 | `2c91985` | ADR-015, 025, 026, 029, 030: 18-item audit/reflection |
| 2026-02-19 | `f592483` | ADR-022: Verification Protocol |
| 2026-02-19 | `ce0c393`, `eed44e7` | ADR-017: Error Taxonomy |
| 2026-02-20 | `c7324f1` | ADR-023: ULW Mode |
| 2026-02-20 | `162a322`~`5634b0e` | ADR-011: Spoke file cleanup |
| 2026-02-20 | `f76a1fd` | ADR-016, 024: E5 Guard, P1 hallucination containment |
| 2026-02-20 | (pending) | ADR-031: PreToolUse Safety Hook |
| 2026-02-20 | (pending) | ADR-032: PreToolUse TDD Guard |
| 2026-02-20 | (pending) | ADR-033: Context Memory optimization (success_patterns, Next Step IMMORTAL, regex) |
| 2026-02-20 | (pending) | ADR-034: Adversarial Review — Enhanced L2 + P1 hallucination containment |
| 2026-02-20 | (pending) | ADR-035: Comprehensive audit — SOT schema extension + Quality Gate IMMORTAL + Error→Resolution surfacing |
| 2026-02-20 | (pending) | ADR-036: Predictive Debugging — preemptive risky-file warning based on error history |
| 2026-02-20 | (pending) | ADR-037: Comprehensive audit II — pACS P1 + L0 Anti-Skip Guard + IMMORTAL boundary + Context Memory |
| 2026-02-20 | (pending) | ADR-038: DNA Inheritance — structural inheritance of the parent genome |
| 2026-02-20 | (pending) | ADR-039: Workflow.md P1 Validation — code-level validation of DNA inheritance |
| 2026-03-02 | (pending) | ADR-050: Security Hardening — 4-layer defense system + claude-forge security insights |
| 2026-03-02 | accepted | ADR-051: Claude Code v2.1 new-feature research — existing design validity verification + @translator memory: project adoption |
| 2026-02-20 | (pending) | ADR-040: Comprehensive audit III — 4-layer QA enforcement reinforcement (C1r/C2/W4/C4s/W7) |
| 2026-02-23 | (pending) | ADR-041: Coding Anchor Points (CAP-1~4) |
| 2026-02-23 | (pending) | ADR-042: Hook setting Global → Project consolidation |
| 2026-02-23 | accepted | ADR-043: ULW redesign — orthogonal thoroughness overlay (Supersedes ADR-023) |
| 2026-02-23 | (pending) | ADR-044: G1 — Cross-Step Traceability |
| 2026-02-23 | (pending) | ADR-045: G2 — Team Intermediate Checkpoint Pattern (Dense Checkpoint Pattern) |
| 2026-02-23 | (pending) | ADR-046: G3 — Domain Knowledge Structure |
| 2026-02-23 | (pending) | ADR-047: Abductive Diagnosis Layer — structured diagnosis on quality-gate FAIL |
| 2026-02-23 | accepted | ADR-048: Full-sweep-based system consistency reinforcement — retry limit 10/15 + P1 doc-code sync + D-7 #5 |
| 2026-03-01 | accepted | ADR-049: CLAUDE.md lightening — switch to TOC pattern (512→160 lines, `docs/protocols/` split) |

---

## Document Management

- **Update rule**: When a new `feat:` commit contains a design decision, add the corresponding ADR to this document.
- **Numbering rule**: Assign sequentially in `ADR-NNN` format. Deleted numbers are not reused.
- **Status transitions**: `Accepted` → `Superseded by ADR-NNN` → `Deprecated` (reason specified)
- **Location**: Project root (`DECISION-LOG.md`). Included in the project-structure tree.
## Fork Decision: @reviewer → always_fork
**Timestamp**: 2026-04-23T23:13:45.157346+00:00
**Rationale**: Independent L2 calibration → isolated context
**Recorded by**: orchestrator

## Fork Decision: @reviewer → always_fork
**Timestamp**: 2026-04-23T23:16:15.185639+00:00
**Rationale**: Independent L2 calibration → isolated context
**Recorded by**: orchestrator

