---
name: workflow-generator
description: Automatic workflow.md generation skill for Claude Code. Used when users request "create workflow", "workflow generation", "automate pipeline design", "define task flow". Conducts interactive dialogue to understand user intent, then generates workflow.md with 3-stage structure (Research → Planning → Implementation). Includes implementation design using Claude Code sub-agents, agent teams (swarm), hooks, skills, slash commands, and MCP servers.
---

# Workflow Generator

Skill for designing and generating workflow definition files (workflow.md) for Claude Code.

## Use Case Discrimination

**Start by understanding the user's situation:**

| Condition | Case | Approach |
|-----------|------|----------|
| Document/PDF attached | Case 2 | Document analysis first → confirmation dialogue |
| Idea only mentioned | Case 1 | Interactive questions to gather requirements |

---

## Case 1: Idea-Only Scenarios

When user has only a vague idea without supporting documentation.

### Step 1: Purpose Clarification

Derive workflow purpose with these questions:

1. "What output/deliverable do you want to create?"
2. "What problem should this workflow solve?"
3. "What are the primary input sources?"

### Step 2: Stage Definition

Develop specific steps per Phase:

1. "What information must be collected in the Research stage?"
2. "What review/approval is needed in the Planning stage?"
3. "What is the final deliverable format and quality standard?"

### Step 3: Human-in-the-Loop Identification

1. "At which stages do you need human review/approval?"
2. "Distinguish stages that can be automated from those requiring confirmation."

### Step 4: Implementation Design → Generation

After gathering requirements, generate workflow.md.

---

## Case 2: Supporting Document Scenarios

When user provides specific documentation (PDF, specifications, etc).

### Step 1: Deep Document Analysis

**Must read document thoroughly and extract:**

```
1. Core Purpose: Final goal the workflow aims to achieve
2. Major Stages: Process/stages mentioned in document
3. Input/Output Definition: Each stage's inputs and outputs
4. Technical Requirements: Required tools, APIs, data sources
5. Constraints: Quality standards, time limits, dependencies
6. Human-in-the-Loop: Points requiring human involvement
```

### Step 2: Analysis Results Sharing

After document analysis, present summary to user:

```markdown
## Document Analysis Results

**Workflow Purpose**: [extracted purpose]

**Identified Major Stages**:
1. [Stage 1]: [description]
2. [Stage 2]: [description]
...

**Identified Human-in-the-Loop Points**:
- [Point 1]: [reason]

**Technical Implementation Direction**:
- Sub-agents: [agent list — delegation within single session]
- Agent Team: [team composition — parallel collaboration across independent sessions]
- Hooks: [automation triggers — quality gates, formatting, validation]
- Required Tools: [tools/MCP list]

**Items Requiring Confirmation**:
1. [Question 1]
2. [Question 2]
```

### Step 3: Confirmation Dialogue

Brief confirmation questions based on analysis:

- "Is my understanding correct?"
- "Any sections to add or modify?"
- "Can you clarify [unclear section]?"

### Step 4: Generation

Generate workflow.md after confirmation.

---

## Absolute Criteria

### Absolute Criterion 1: Final Deliverable Quality

> **Speed and token cost are completely ignored.**
> **The sole criterion for all design decisions is the quality of the final deliverable — rigor, clarity, depth of argumentation.**
> Choose to add stages to improve quality over reducing stages to finish faster.
> Increased SOT complexity to improve quality is acceptable (Absolute Criterion 1 > Absolute Criterion 2).

### Absolute Criterion 2: Single-File SOT + Hierarchical Memory Structure

> **Under single-file SOT (Single Source of Truth) + hierarchical memory architecture, dozens of agents operate simultaneously without data inconsistencies.**

Design implications:
- **State Management**: All workflow shared state concentrates in **a single file** (e.g., `state.json`). Do not distribute state across multiple files.
- **Memory Hierarchy**: Clearly separate agent-local memory (task context) from global memory (shared state).
- **Write Authority**: Only Orchestrator or designated single agent has write access to SOT file. Other agents access read-only or report results to Orchestrator for merging.
- **Conflict Prevention**: Design parallel agents (Agent Team/Swarm) to avoid simultaneous modification of same data.

```
Bad:  Agent A → direct modify state.json
      Agent B → direct modify state.json  → data conflict/inconsistency
Good: Agent A → report results to Orchestrator
      Agent B → report results to Orchestrator
      Orchestrator → merge into state.json  → single write point, no inconsistency
```

### Absolute Criterion 3: Code Change Protocol (CCP)

> **When writing/modifying code during workflow implementation (Phase 2), always execute: Intent Clarification → Impact Analysis → Change Design.**

Workflow components (Sub-agent, Hook, SOT, Slash Command, MCP) have interdependencies. Changes to one component can cascade to others, so impact analysis is mandatory before code changes.

- **Step 1 — Intent Clarification**: Precisely understand the change purpose and constraints.
- **Step 2 — Impact Analysis**: Verify directly dependent modules, call relationships, SOT files, configuration/environment, test code, and documentation.
- **Step 3 — Change Design**: Design change order and create modification plan for all affected files before executing.

> **Proportionality Rule**: Document modifications in workflow design stage (Phase 1) = minor changes (Step 1 only); code modifications in implementation stage (Phase 2) = standard/major changes (full 3-step protocol).

### Absolute Criteria Priority

> **Absolute Criterion 1 (Quality) is highest priority. Absolute Criteria 2 (SOT) and 3 (CCP) are equal-priority means to guarantee quality.**
> Do not reduce final deliverable quality to maintain SOT structure.
> Do not reduce final deliverable quality to comply with CCP.

All absolute criteria supersede design principles below. When criteria conflict, **Absolute Criterion 1 > (Criterion 2, Criterion 3)**.

---

## Genome Inheritance Protocol

> **When creating offspring, structurally inherit entire parent genome. Creation without inheritance is prohibited.**

AgenticWorkflow is a parent organism generating child workflows. `workflow-generator` is the production line; all children born here embed parent's entire genome in `Inherited DNA` section.

### Inheritance Mechanism

| Parent Genome (DNA) | Form Embedded in Child |
|------------------|----------------------|
| 3 Absolute Criteria | `Inherited DNA` section — contextualized per domain |
| SOT Pattern | Configuration `state.yaml` + single write point |
| 3-Stage Structure | Research → Planning → Implementation workflow structure |
| 4-Layer Validation | `Verification` + `pACS` fields |
| P1 Blocking | Hook-based deterministic validation |
| Safety Hook | PreToolUse blocking patterns |
| Adversarial Review | `Review:` field — `@reviewer` / `@fact-checker` |
| Decision Log | `autopilot-logs/` pattern |
| Context Preservation | Cross-session memory preservation patterns |

### Expression vs Inheritance

Like cells with identical genomes performing different functions, child systems with same DNA **express domain-specifically**. Research automation emphasizes Research stage genes; software development automation emphasizes CCP genes. Same genome, different domains.

### Generation Obligations

1. All workflow.md must include `Inherited DNA (Parent Genome)` section (see template)
2. All state.yaml must include `parent_genome` metadata (see SOT template)
3. Child agent definitions must reflect parent's quality standards (Absolute Criterion 1)

Details: `soul.md §0`, `AGENTS.md §1 Raison d'Être`.

---

## Design Principles (Mandatory Compliance)

Principles that must apply during workflow design. All principles subordinate to **all absolute criteria (1. Quality First, 2. Single-File SOT, 3. Code Change Protocol)**.

### P1. Data Refinement for Accuracy

Passing raw large data to AI degrades accuracy due to noise. Refine data so agents concentrate on essentials.

- Specify **data pre-processing** for each stage: remove noise with Python scripts before passing to AI → **improve analysis accuracy**
- Specify **post-processing** for each stage: refine deliverables before passing to next stage → **improve next stage quality**
- For data correlations, **pre-compute at code level** when possible → **AI focuses on judgment and analysis**

```
Bad:  "Pass entire HTML of collected webpage to agent" → noise degrades analysis quality
Good: "Python script extracts body text only → pass core text to agent" → improve analysis accuracy
```

### P2. Specialization-Based Delegation

Delegate each task to **the most specialized agent** for that domain, maximizing quality. Orchestrator coordinates overall quality; specialized agents focus depth in their domains.

```
Orchestrator (quality coordination & overall flow management)
  ├→ Sub-agent A: specialized research (domain-optimized)
  ├→ Sub-agent B: deep analysis (analysis-focused)
  └→ Skill C: validated pattern application (quality-assured reusable logic)
```

### P3. Image/Resource Accuracy

For stages requiring image resources, specify **exact download paths**. Extract all placeholders; omissions prohibited.

### P4. Question Design Rules

When asking users:
- Maximum 4 questions only
- Each question provides **approximately 3 choice options** (sub-agent/skill/recommendation)
- Proceed without questions if no ambiguity

---

## Workflow Base Structure

All workflows comprise 3 stages:

1. **Research**: Information gathering and analysis
2. **Planning**: Plan establishment and structuring
3. **Implementation**: Actual execution and deliverable generation

**Each stage must include:**
- Task (Task)
- Responsible Agent (@agent)
- Data Pre-processing (Pre-processing) — noise removal for accuracy improvement (P1)
- Deliverable (Output)
- Adversarial Review (Review) — `@reviewer`, `@fact-checker`, or `none` (AGENTS.md §5.5)
- Translation (Translation) — `@translator` or `none` (text deliverables only)
- Post-processing (Post-processing) — refinement for next stage quality (P1)

## Claude Code Component Mapping

| Workflow Element | Claude Code Implementation | Selection Criteria |
|-----------------|---------------------------|-------------------|
| Single task delegation | Sub-agent (`.claude/agents/*.md`) | Deep focus on specialized domain, maximize quality |
| Large-scale parallel collaboration | Agent Team/Swarm (`TeamCreate`) | Simultaneously execute independent work across sessions |
| Human involvement stage | Slash command (`.claude/commands/`) | Review/approval/selection etc. user interaction |
| Automated validation/trigger | Hooks (`settings.json`) | Formatting, quality gates, security validation |
| Reusable logic | Skill (`.claude/skills/`) | Domain knowledge, recurring patterns |
| External integration | MCP Server | API, DB, external service integration |

### Sub-agent vs Agent Team Selection Criteria

> **The only selection criterion is: 'Which structure produces the highest final deliverable quality?'**
> Do not select Agent Team because parallel execution is faster.
> Do not select Sub-agent because it uses fewer tokens.

| Situation | Choice | Quality Justification |
|-----------|--------|----------------------|
| Single expert handling with sustained deep context achieves highest quality | **Sub-agent** | Maintain consistent depth within single context |
| Different specialized domains each require maximum-level handling | **Agent Team** | Each specialist independently focuses 100% on their domain |
| Multi-perspective analysis/cross-validation improves quality | **Agent Team** | Independent perspectives combine for richer results than single agent |
| Context transfer accuracy across stages is quality-critical | **Sub-agent Sequential** | Precisely transmit stage outputs to next stage |

> **Absolute Criterion 2 Requirement**: When selecting Agent Team, always define SOT design together — SOT file location, Team Lead's single write authority, team member output generation rules. Agent Team without SOT design is not permitted in principle. Details: `references/claude-code-patterns.md` State Management section.
>
> **Absolute Criterion 1 Priority Exception**: For completely independent parallel work (no shared state between agents, agents don't reference each other's outputs), if explicitly documented that SOT design doesn't contribute to quality, SOT can be lightweight. This judgment must be documented during workflow design.

## Reference Documents

- workflow.md template: `references/workflow-template.md`
- Claude Code implementation patterns (Sub-agents, Teams, Hooks): `references/claude-code-patterns.md`
  - Anti-Skip Guard Protocol: §Anti-Skip Execution Protocol (deliverable validation — minimum 100 bytes)
  - Autopilot Execution Checklist: §Autopilot + Agent Team Integration Checklist
  - SOT State Management: §SOT State Management Protocol
- Document analysis guide (Case 2): `references/document-analysis-guide.md`
- Context injection patterns (Sub-agent/Team input delivery): `references/context-injection-patterns.md`
- SOT template (state.yaml bootstrap): `references/state.yaml.example`
- Autopilot Decision Log template: `references/autopilot-decision-template.md`

## Final Generation Procedure

1. Discriminate case (document presence)
2. Case 1: Gather requirements via dialogue / Case 2: Document analysis → confirmation dialogue
3. **Genome Inheritance**: Include `Inherited DNA (Parent Genome)` section in workflow.md (Inheritance Protocol — `references/workflow-template.md`). `parent_genome.version` uses generation date (YYYY-MM-DD). Include coding reference points (CAP-1~4) when contextualizing CCP.
4. Apply design principles P1~P4 while defining tasks in 3-stage structure
   - Evaluate Domain Knowledge Structure (DKS) necessity: workflows requiring domain-specific reasoning (medicine, law, competitive analysis, etc.) must include DKS-building stage in Research. Workflows using DKS include `python3 .claude/hooks/scripts/validate_domain_knowledge.py --project-dir . --check-output --step N` in related stage post-processing. Details: `AGENTS.md §5.3 DKS`
5. Specify data pre-processing/post-processing for each stage (P1)
6. Mark human-in-the-loop points
7. **Define `Verification` field for each stage** (AGENTS.md §5.3 — Mandatory):
   - Position `Verification` field **before** `Task` field (agent recognizes first)
   - **Verification mandatory for all agent execution stages** — Research/Planning/Implementation without distinction (Research also needs "completeness" validation: e.g., "all 5 competitors analyzed")
   - Exception: `(human)` stages only — human is the validator, so `Verification` unnecessary
   - Each criterion written as **concrete statement verifiable as true/false by third party**
   - Combine 5 criterion types:
     - **Structural Completeness**: internal deliverable structure → "all 5 sections included", "each item has 3+ sub-items"
     - **Functional Goals**: task objective achievement → "price data from 3+ competitors", "all API endpoints implemented"
     - **Data Consistency**: data accuracy → "all URLs valid, no placeholders", "numerical data sources cited"
     - **Pipeline Connection**: next-stage input compatibility → "includes fields Step N requires", "output format matches Step N+1 input"
     - **Cross-Stage Traceability**: logical derivation from prior stages → "80%+ analysis claims traceable with [trace:step-N] markers"
   - **Tip**: Using `(source: Step N)` annotation when writing criteria makes Verification itself explicitly reference prior stages, enabling automatic upstream impact analysis during diagnosis. Example: "Competitive analysis reflects Step 2 research results (source: Step 2)"
8. Set **Review field** for each stage (AGENTS.md §5.5 — optional):
   - Research/analysis deliverables (fact verification needed) → `@fact-checker`
   - Code/technical deliverables (logic/completeness verification needed) → `@reviewer`
   - High-risk stages (both) → `@reviewer + @fact-checker`
   - Low/medium risk stages → `none` (up to L1.5 only)
   - **Execution Order**: Review PASS → Translation (Translation prohibited in Review FAIL state)
9. Set **Translation field** for each stage — text deliverables (`.md`, `.txt`) use `@translator`, code/data/config use `none`
10. Add Claude Code implementation design (Sub-agents, Teams, Hooks, Commands, Skills, MCP)
    - **Choose Context Injection Pattern** (per agent stage):
      - Input < 50KB → Pattern A (Full Delegation — pass file path)
      - Input 50-200KB + partial relevance → Pattern B (Filtered — refine with pre-processing script before passing)
      - Input > 200KB or needs splitting → Pattern C (Recursive Decomposition — parallel chunk processing)
      - Absolute Criterion 1 Priority: select Pattern B regardless of size if filtering improves quality
      - Details: `references/context-injection-patterns.md`
    - **SOT Design Mandatory When Using Agent Team** (Absolute Criterion 2):
      - SOT file location (`.claude/state.yaml`), Team Lead single write authority, team member output rules
      - `active_team` schema: name, status, tasks_completed/pending, completed_summaries
      - SOT update 4 points: immediately after TeamCreate → when teammate completes → when all complete → after TeamDelete
      - Details: `references/workflow-template.md §Agent Team SOT Schema`
    - **Checkpoint Pattern**: Evaluate expected turns per Task, select `standard`(≤ 10 turns) or `dense`(> 10 turns) pattern. Details: `references/claude-code-patterns.md §DCP`
11. **Apply English-First Execution Principle** (AGENTS.md §5.2):
    - All agent Task descriptions and prompts written in **English** (maximize AI performance — Absolute Criterion 1)
    - Workflow design user dialogue in Korean, agent execution in English
    - `@translator` sub-agent handles English→Korean translation (specify in Translation field)
12. Generate workflow.md file
13. **(Optional) Distill Validation**: maximize generated workflow quality through review
    - "Does this stage contribute to final quality?" — remove quality-irrelevant stages only
    - "Does automating this stage stabilize quality further?" — discover automation opportunities
    - "Are stages needed to increase quality?" — add validation/reinforcement stages
    - "Do all `Verification` criteria include **pipeline connection**?" — validate data flow across stages
    - **DNA Inheritance P1 Validation**: run `python3 .claude/hooks/scripts/validate_workflow.py --workflow-path ./workflow.md` → confirm W1-W8 pass
    - Reference: `prompt/distill-partner.md`

## Autopilot Mode Support

Include Autopilot Mode field in generated workflow.md.

- Add `- **Autopilot**: [disabled|enabled]` to Overview section (default: disabled)
- If user requests "auto-execute", "non-stop execution", set to `enabled`
- Do not change `(human)` stage design itself — Autopilot is execution mode, not design change
- Optional: specify default behavior in each `(human)` stage with `Autopilot Default` field for auto-approval

## pACS Support

Include pACS (self-confidence evaluation) field in generated workflow.md.

- Add `- **pACS**: [enabled|disabled]` to Overview section (default: enabled, AGENTS.md §5.4)
- pACS operates independently from Autopilot mode — applies in manual execution too
- `(human)` stages don't need pACS — human is evaluator, same as Verification principle
- If user explicitly requests "without pACS", set to `disabled`
