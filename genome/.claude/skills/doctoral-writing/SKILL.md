---
name: doctoral-writing
description: Doctoral-level academic thesis writing skill. Implements both scholarly rigor (academic precision) and clarity simultaneously. Supports Korean and English; applicable across humanities, social sciences, and natural sciences. Used when users request "write in thesis style", "academic writing", "doctoral thesis tone", "academic writing", "refine thesis prose", "revise for academic expression", etc. Applied to dissertations/theses, journal submissions, research reports, academic presentations.
---

# Doctoral-Level Academic Writing

## Overview

This skill systematically supports doctoral-level thesis writing combining scholarly rigor and clarity. Supports both Korean and English while reflecting academic conventions across all disciplines: humanities, social sciences, and natural sciences.

Core philosophy: **"Clear and concise" writing is NOT "simple and short" writing. It is efficient communication of complex ideas.** Removing unnecessary elements to reveal the core.

## When to Use This Skill

- Review and write dissertation/thesis chapters
- Refine and improve journal submission manuscripts
- Write research reports and academic presentations
- Provide academic writing instruction and feedback
- Apply style for Korean ↔ English academic translation
- **Primary Use Case**: Writing Phase standard in doctoral research workflow

## Absolute Criteria

### Absolute Criterion 1: Final Manuscript Academic Quality

> **Revision count, workload, length constraints are completely ignored.**
> **The sole criterion for all writing/revision decisions is final manuscript academic quality — rigor, clarity, argumentation depth.**
> Choose to iterate revisions to improve quality over reducing revisions to finish faster.
> Do not sacrifice academic depth or nuance for conciseness.

### Absolute Criterion 2: Manuscript Consistency — Single SOT + Hierarchical Structure

> **Consistency of terminology, argumentation, citations, and style across the entire manuscript is the foundation of academic credibility.**
> **The manuscript itself is the single SOT (Single Source of Truth); all revisions must preserve manuscript-wide consistency.**

Design implications:
- **Terminology SOT**: Specialist term definitions and abbreviations are finalized at first use, then used identically throughout. Avoid "elegant variation."
- **Argumentation SOT**: Research questions/hypotheses in introduction form consistent axis through methodology, results, discussion. Edits to one section must not conflict with argumentation in other sections.
- **Citation SOT**: Citation style (APA, Chicago, etc.) follows single style throughout. In-text citations and bibliography must correspond 1:1.
- **Style SOT**: Person (first/third), tense, active/passive choices are decided once per field convention, then applied consistently throughout.

```
Bad:  Chapter 1: defined as "self-efficacy"
      Chapter 3: variant use as "self-efficacy sense" → terminology mismatch, credibility reduced
Good: Chapter 1: defined as "self-efficacy"
      Thereafter: consistent use of "self-efficacy" → single terminology SOT
```

### Absolute Criterion 3: Code Change Protocol (CCP)

> **This skill's application domain (academic writing) is N/A.**

However, when modifying the skill itself (SKILL.md, references/ files), Absolute Criterion 3 applies. See AGENTS.md for detailed protocol.

### Absolute Criteria Priority

> **Absolute Criterion 1 (Quality) is highest priority. Criterion 2 (Consistency) and Criterion 3 (CCP) are equal-priority means to guarantee quality.**
> Do not reduce academic accuracy or argumentation quality to maintain consistency.
> Consistency is a means to guarantee quality, not a purpose constraining quality.

Conflict scenarios:

```
Conflict Scenario 1 — Terminology Accuracy vs Consistency:
  Chapter 1 used "structural inequality"; Chapter 4 analysis shows
  "systemic inequality" is academically more precise
  → Absolute Criterion 1 priority: change to more precise term,
     apply retroactively in Chapter 1 to restore consistency

Conflict Scenario 2 — Style Consistency vs Argumentation Quality:
  Throughout used third person; qualitative research reflection section
  where first person enhances authenticity and depth
  → Absolute Criterion 1 priority: permit first person in that section
     + explicitly state reason for person shift in manuscript
```

All absolute criteria supersede core principles below. When criteria conflict, **Absolute Criterion 1 > (Criterion 2, Criterion 3)**.

---

## Core Writing Principles

> The 4 core principles below are **subordinate to all absolute criteria (1. Quality, 2. Consistency, 3. Code Change Protocol)**. When principles conflict, absolute criteria take priority.

### 1. Clarity

Deliver core ideas precisely so readers need not guess author intent.

**Key Requirements**:
- Subject-predicate alignment clear
- Core concepts and key sentences transparent
- Specialized terminology defined at first use
- Active voice preferred (where appropriate)
- Precise word selection

**Common Issues**:
- Ambiguous pronouns/demonstratives
- Multiple clauses creating relationship confusion
- Undefined terminology/acronyms
- Long sentences with unclear antecedents

### 2. Conciseness

Express ideas in minimum words while preserving meaning and nuance.

**Key Requirements**:
- One sentence = one idea
- Sentence length in 3-tier standard:
  - **Recommended**: Korean 20-40 characters, English 15-25 words
  - **Caution**: Korean 40+ characters, English 25+ words — consider splitting
  - **Maximum**: Korean 60 characters, English 30 words — must split
- Remove unnecessary modifiers, adjectives, adverbs
- Replace redundant and verbose phrases

**Common Issues**:
- Long sentences with multiple digressions and parentheticals
- Redundant expressions (e.g., "the past history")
- Over-use of "is/has" constructions
- Excessive prepositional phrases/particles

### 3. Academic Rigor

Maintain scholarly standards and precision while keeping writing accessible to target academic audience.

**Key Requirements**:
- Use specialized terminology only when necessary
- Define important concepts at first use
- Follow field conventions
- Support claims with evidence and citations
- Maintain formal academic tone (usually third person)
- Choose verbs that precisely describe actions and relationships

### 4. Logical Flow

Ideas develop in clear, logical sequence; connections between sentences and paragraphs are explicit.

**Key Requirements**:
- One main idea per paragraph
- Clear topic sentence
- Effective transition phrases
- Consistent argumentation structure
- Explicit relationships between claims and evidence

## Quick Reference: Practical Transformation Rules

### Target Expressions for Deletion

| Type | Target | Replacement/Action |
|------|--------|-------------------|
| Modifier excess | various, several, diverse | replace with specific numbers or categories |
| Adverb overuse | very, considerably, somewhat, relatively | replace with quantitative expression |
| Passive habit | is...ed, is being...ed | convert to active form |
| Dependent nouns | it is considered that, being ... | shorten to direct statement |
| Redundancy | approximately...degree, most highest | use only one |

### Transformation Examples

```
❌ This research aimed to derive results through analysis of various factors.
✅ This research analyzed three factors to establish causal relationships.

❌ Numerous prior studies have been found to report this phenomenon.
✅ 37 prior studies report this phenomenon.

❌ Comparatively considerable positive results appear to have been derived.
✅ Effect size 0.65 yielded moderate positive results.
```

### Conjunction Usage Principles

**Permitted conjunctions**:
- **Causal**: Therefore, consequently, thus
- **Contrast**: However, conversely, on the other hand
- **Elaboration**: That is, in other words
- **Sequential**: First/second, first/next

**Avoided conjunctions**:
- And (replace with parallel structure)
- So (replace with "therefore")
- Also (integrate sentence or delete)
- Furthermore (integrate into parallel structure)

```
❌ Conducted surveys. And conducted interviews. Also performed observations.
✅ Conducted surveys, interviews, and participatory observation.
```

### Academic Vocabulary Selection

**Colloquial → Formal conversion**:

| Colloquial | Academic Formal |
|------------|-----------------|
| do...because | do...thereby, do...such that |
| find out | analyze, examine, consider |
| show | demonstrate, indicate, present |
| think | judge, conclude, infer |
| use | employ, apply, utilize |

**Vague → Concrete**:

| Vague | Concrete |
|------|----------|
| many studies | 37 studies |
| recent | after 2020 |
| most | 78.3% |
| significant difference | t(45)=2.31, p<.05 |

### Argumentative Tone

```
❌ I believe this result is very important.
✅ This result contributes to extending existing theory.

❌ This is a truly surprising finding.
✅ This finding shows a pattern different from prior research.
```

**Hedging expressions** (use appropriately):
- "can be interpreted as / suggests possibility of"
- "is estimated to / appears to"

## Workflow

### Step 1: Understand the Context

Before feedback or revision, first understand:

1. **Document type and audience**:
   - Dissertation chapter, journal paper, conference presentation, thesis?
   - Target journal or academic audience?
   - Discipline (humanities, social sciences, natural sciences)?

2. **Work scope**:
   - Full manuscript review?
   - Sentence/paragraph-level editing?
   - Educational feedback?
   - Style guide compliance check?

3. **Language and style requirements**:
   - Korean or English?
   - APA, Chicago, MLA, other style guide?
   - Discipline-specific conventions?

### Step 2: Apply Clarity Checklist

Load `references/clarity-checklist.md` and systematically evaluate:
- Subject-verb agreement and clarity
- Sentence structure and length
- Terminology definitions
- Logical flow and transitions
- Active/passive voice use

### Step 3: Identify Common Issues

Reference `references/common-issues.md` to recognize and correct:
- Verbose expressions and redundancy
- Weak verb choices
- Unclear pronoun references
- Excessive nominalization
- Hedging overuse

### Step 4: Provide Revisions or Feedback

**When revising manuscript**:
- Present Before/After comparisons
- Explain rationale for major changes
- Preserve author voice and argumentation structure
- Maintain discipline-specific terminology and standards

**When providing educational feedback**:
- Identify patterns rather than individual instances
- Explain why specific phrasing reduces clarity
- Use concrete examples from `references/before-after-examples.md`

**When writing discipline-specific**:
- Reference discipline conventions in `references/discipline-guides.md`
- Verify differences in citation style, voice use, structural norms
- Respect discipline-specific terminology and conceptual frameworks

### Step 5: Verify Improvements

After revision, confirm:

**Absolute Criteria Verification (Priority)**:
- ✓ **[Criterion 1]** Has academic quality improved (rigor, clarity, argumentation depth)?
- ✓ **[Criterion 2]** Does revision maintain consistency with other manuscript sections (terminology, argumentation, citations, style SOT)?
- ✓ **[Priority]** Are there sections where consistency compromised quality?

**Core Principles Verification**:
- ✓ Meaning and nuance preserved
- ✓ Clarity improved
- ✓ Conciseness strengthened
- ✓ Logical flow enhanced
- ✓ Style guide compliance (if applicable)

## Key Techniques

### Sentence Structure Optimization

**Subject-verb-object clarification**:
- Position subject in sentence opening
- Keep subject and verb close
- Avoid long insertions between subject and verb
- Use parallel structure for related ideas

**Example (Korean)**:
- ❌ "This research, which was conducted over three years across five different sites spanning urban and rural regions through multiple data collection stages, examined the following relationships."
- ✅ "This three-year research examined the following relationships. The study collected data across five sites in urban and rural areas."

**Example (English)**:
- ❌ "The study, which was conducted over a period of three years in multiple locations across five different countries, examined the impact of..."
- ✅ "This three-year study examined the impact of... The research spanned five countries."

### Eliminating Verbosity (Paramedic Method)

1. Identify prepositional phrases (of, in, for) / particles
2. Identify "to be" verbs / "is, has" constructions
3. Find core action and convert to verb
4. Move subject close to verb
5. Remove unnecessary words
6. Eliminate redundancy

### Terminology Management

**Define at first use**:
- Provide definition when introducing specialized term
- Spell out abbreviations at first use: "Structural Equation Modeling (SEM)"
- Provide brief context for field-specific concepts

**Consistency**:
- Use identical term for same concept throughout
- Avoid "elegant variation" with technical terms
- Maintain terminology consistent with cited literature

### Active/Passive Voice Selection

**Use active voice**:
- When describing your own research actions
- When making direct claims
- To ensure clarity and reduce word count

**Permit passive voice** (explicit exceptions to active preference):
- When actor unknown or unimportant
- When action/object warrant emphasis over actor
- When following field convention (some science methods sections)
- **Results reporting sections**: "was found to", "was observed" conventions natural in academic style
- **Methodology description**: "Participants were randomly assigned" etc. natural for procedure description

> **P9 Intersection Resolution**: When "prefer active voice" conflicts with "respect field convention," **field convention takes priority**. Academic accuracy supersedes stylistic preference.

## Language-Specific Guidance

### Korean Academic Writing

**Core Principles**:
- Align subject and predicate clearly
- Don't embed multiple topics in one sentence
- Remove unnecessary modifiers and conjunctions
- Define specialized terminology at first use

**Common Issues**:
- Excessively long sentences (3+ clauses per sentence)
- Overuse of passive expressions
- Unclear subjects
- Unnecessary phrases like "~에 있어서", "~에 대하여"
- Consecutive use of "의" (3+ forbidden)

**Person usage**: Strongly prefer third person
- "This research analyzed..." (✓)
- "The researcher confirmed..." (✓)
- "I analyzed..." (✗)

### English Academic Writing

**Key principles**:
- Prefer active voice where appropriate
- Keep sentences under 25 words when possible
- Define technical terms on first use
- Use transitions to connect ideas explicitly

**Common issues**:
- Excessive nominalization (turning verbs into nouns)
- Overuse of "there is/are" constructions
- Weak verbs (is, has, does) where stronger verbs exist
- Hedging overload (perhaps, possibly, might, etc.)

## Review Checklist

After writing, verify:

- [ ] Every sentence has clear subject?
- [ ] Sentence lengths within 3-tier standard (recommended 40 chars/25 words, max 60 chars/30 words)?
- [ ] Removed unnecessary adjectives/adverbs?
- [ ] Converted passive to active voice?
- [ ] Made vague expressions concrete?
- [ ] Replaced "various", "several", "many" with specific numbers?
- [ ] Minimized "and", "also" conjunctions?
- [ ] Each paragraph addresses one main point?
- [ ] Defined specialized terminology at first use?
- [ ] Claims supported by evidence/citations?
- [ ] Followed discipline-specific style guide?

## Resources

### references/

Comprehensive reference materials included with skill:

- **clarity-checklist.md**: Systematic checklist for evaluating clarity, conciseness, academic rigor (Korean/English)
- **common-issues.md**: Catalog of frequent academic writing problems — Before/After examples
- **before-after-examples.md**: Real doctoral thesis revision cases — field-specific practical examples
- **discipline-guides.md**: Writing conventions, citation styles, voice usage per discipline (humanities, social sciences, natural sciences), multilingual translation guide
- **korean-quick-reference.md**: ❌/✅ transformation examples per thesis section, discipline-specific terminology, frequent error patterns (Korean-only quick reference)

> **File Role Division (P4 Cross-Reference Guide)**:
> Some topics (e.g., missing subjects, passive voice overuse, nominalization) appear in multiple files. This is task division, not duplication:
> - **SKILL.md**: Principles and judgment criteria (WHY)
> - **common-issues.md**: Problem-type systematic catalog + solutions (WHAT)
> - **korean-quick-reference.md**: Korean-specific quick-reference patterns (HOW — Korean)
> - **before-after-examples.md**: Real thesis revision cases (HOW — practical)
> - **clarity-checklist.md**: Review checklist (VERIFY)

Load as needed during review and revision process.

## Notes

- **Criterion 1 application**: Prioritize content over style — do not sacrifice meaning for brevity. Iterate revisions if needed.
- **Criterion 2 application**: When revising manuscript sections, verify that revisions don't create inconsistency with terminology, argumentation, citations in other sections.
- **Criterion 3 application**: Academic writing domain is N/A. When modifying this skill's SKILL.md or references/ files, apply CCP (Intent Clarification → Impact Analysis → Change Design).
- Respect author voice and field conventions
- Provide constructive, educational feedback promoting writing improvement
- When uncertain, reference discipline-specific style guides and exemplar publications
- **"Clear and concise" is not "simple and short"** — it is efficient communication of complex ideas
