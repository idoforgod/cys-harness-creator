> ⚠️ **구현 현황은 [`IMPLEMENTATION-STATUS.md`](IMPLEMENTATION-STATUS.md)가 우선한다.** 이 문서가 무엇을 설명하든, 실제로 emit/validate에 구현됐는지는 그쪽으로 확정한다. 산출 하네스의 **실행 런타임은 100% Claude Code 프리미티브**(Agent / TeamCreate / SendMessage / TaskCreate)이며, 오케스트레이터 SKILL.md가 그 단일 진입점이다. Mode-A `workflow.js`는 **제품에서 은퇴**했고 `emit_workflow.py`는 **공장내부 측정 전용**으로만 남는다(`WORKFLOW_RETIRED`).

# 스킬 & 에이전트 작성 가이드 (CYS)

> 출처: 이 문서는 옛 `skill-writing-guide.md`(CYS + idoforgod)를 개명·계승하여 **에이전트(`.claude/agents/<agent>.md`) 저작**으로 확장한 것이다(Impl I1/I2). `skill-writing-guide.md`는 더 이상 별도 파일로 존재하지 않는다.

도메인 오케스트레이터 **SKILL.md**, 노드 **에이전트 정의(`.md`)**, 노드 **output_schema**(머신검증 JSON Schema), 그리고 하이브리드 **도메인 스킬**(`emit_domain_skill.py`)을 고품질로 저작하기 위한 상세 가이드. harness-creator 메타스킬 **Implementation 단계(I1/I2)**의 보충 레퍼런스.

원본은 "스킬 본문이 곧 트리거이자 실행 지시서"라는 모델이었다. CYS에서는 **실행 지시가 3원천으로 분산**된다: (a) `graph.json`(불변 머신계약), (b) `emit_orchestrator.py`가 graph.json에서 렌더한 **오케스트레이터 SKILL.md**(라이브 Claude Code 호스트 세션을 Agent/TeamCreate로 구동하는 프로즈 지시서), (c) 노드별 **`.claude/agents/<agent>.md`**(서브에이전트의 실제 작업 지시서, frontmatter가 model·tools·maxTurns를 **런타임 강제**). 따라서 원본의 트리거 설계·Why-First·Progressive Disclosure 지혜는 **그대로 보존**하되, "출력 형식 정의"는 산문 템플릿이 아니라 **머신검증 output_schema 설계**로 승격되고, "본문 실행 지시"는 **에이전트 `.md` 저작**으로 승격된다.

---

## 목차

1. [스킬의 두 종류: 상속받은 것 vs 저작하는 것](#1-스킬의-두-종류-상속받은-것-vs-저작하는-것)
2. [오케스트레이터 SKILL.md description 작성 패턴](#2-오케스트레이터-skillmd-description-작성-패턴)
3. [본문 작성 스타일 (Why-not-ALWAYS · 일반화 · 명령형 · 컨텍스트 절약)](#3-본문-작성-스타일)
4. [오케스트레이터 본문 구조 (graph.json의 사람용 뷰)](#4-오케스트레이터-본문-구조-graphjson의-사람용-뷰)
5. [에이전트 정의 저작 (NEW — I1: `.claude/agents/<agent>.md`)](#5-에이전트-정의-저작-new--i1-claudeagentsagentmd)
6. [도메인 스킬: 하이브리드 author-or-inline (I2)](#6-도메인-스킬-하이브리드-author-or-inline-i2)
7. [output_schema 설계 (머신검증 계약)](#7-output_schema-설계-머신검증-계약)
8. [Progressive Disclosure 패턴](#8-progressive-disclosure-패턴)
9. [세 원천의 역할 분담 (중복 금지)](#9-세-원천의-역할-분담-중복-금지)
10. [측정·평가 데이터 스키마 표준 (lift_gate · h2h)](#10-측정평가-데이터-스키마-표준-lift_gate--h2h)
11. [SKILL.md/agent에 포함하지 않을 것](#11-skillmdagent에-포함하지-않을-것)
12. [진화·피드백 루프 (관찰 → 일반화)](#12-진화피드백-루프-관찰--일반화)

---

## 1. 스킬의 두 종류: 상속받은 것 vs 저작하는 것

CYS 하네스 안에는 여러 부류의 스킬·에이전트가 공존한다. 둘을 혼동하면 "이미 게놈이 주는 것"을 다시 쓰거나, "직접 써야 할 진입점"을 빠뜨린다.

| 구분 | 상속 스킬 (genome) | 저작 산출물 (이 가이드의 대상) |
|------|-------------------|--------------------------------|
| 출처 | `inherit_genome.py`가 게놈과 함께 복사 | **메타스킬이 Implementation(I1/I2)에서 직접 저작** |
| 위치 | `.claude/skills/{workflow-generator, doctoral-writing, spec-grounded-workflow, ...}/` | `.claude/skills/<harness>-orchestrator/SKILL.md`, `.claude/agents/<agent>.md`, `.claude/skills/<harness>-<node_id>/SKILL.md`(skill-mode 노드만) |
| 역할 | 자식 하네스의 일반 운영 능력(워크플로우 생성·학술 글쓰기 등) | **이 하네스 한 개**를 트리거·설명·실행하는 진입점 + 노드의 실제 작업 지시 |
| 수정 | 손대지 않는다 (게놈 불변) | 이 가이드의 대상 — 도메인마다 새로 쓴다 |

> **핵심 원칙:** 자식 하네스는 게놈을 통째로 물려받아 이미 풍부한 운영 기계(컨텍스트 보존 hook, 4계층 품질 게이트, 보안 hook, reviewer/fact-checker 에이전트, 발화 hook 3종)를 **갖고 태어난다**. 저작 작업은 **앞단(front-half) 설계** — 도메인을 `graph.json` + 에이전트 + schema + (선택적) 도메인 스킬 + 오케스트레이터 SKILL.md로 옮기는 일 — 에 집중한다. 상속된 뒷단(back-half) 기계는 다시 만들지 않는다. 그 발화 메커니즘(게놈 hook·런타임 DNA)의 자세한 동작은 `genome-and-runtime.md`를 참조한다.

검증기는 이 구분을 안다: `validate_harness.py`의 DOC_DRIFT 체크는 README와 오케스트레이터 SKILL.md의 phase 수가 다르면 잡는다. 저작하는 오케스트레이터 스킬 디렉토리는 **반드시 `<harness>-orchestrator` 규칙**을 지키고(`emit_orchestrator.py`가 이 이름으로 emit), skill-mode 노드의 도메인 스킬은 `<harness>-<node_id>` 규칙을 지킨다(`emit_domain_skill.py`의 `skill_name()`).

---

## 2. 오케스트레이터 SKILL.md description 작성 패턴

`description`은 오케스트레이터 스킬의 **유일한 트리거 메커니즘**이다. Claude는 `available_skills` 목록에서 name + description만 보고 이 하네스를 실행할지 결정한다. 이 지혜는 원본에서 1:1로 가져온다.

### 트리거 메커니즘 이해 (원본 보존)

Claude는 자신의 기본 도구로 처리할 수 있는 단순 작업에는 스킬을 호출하지 않는 경향이 있다. "이거 한 번 검색해줘" 같은 요청은 description이 완벽해도 트리거되지 않을 수 있다. **복잡·다단계·전문적·재실행 가능한 작업일수록 트리거 확률이 높다** — 이것은 정확히 하네스가 존재해야 하는 조건(warrant가 `build-harness`를 내는 조건)과 일치한다. 즉 트리거가 잘 되는 description은 곧 "하네스가 정당화되는 상황"을 묘사한 것이다.

### 작성 원칙 (원본 보존 + CYS 추가)

1. **이 하네스가 하는 일** + **구체적 트리거 상황**을 모두 기술.
2. 유사하지만 트리거하면 안 되는 경계 조건 명시.
3. 약간 **pushy**하게 — Claude의 보수적 트리거 경향을 보상.
4. **(CYS 추가) 후속 작업을 description에 명시한다.** 재실행·수정·보완·부분 재생성·이전 결과 개선 요청도 이 스킬을 타야 한다. 하네스는 git repo이자 재개되는 자산이므로, "한 번 만들고 끝"이 아니라 "계속 돌리고 진화시키는" 대상이다. description이 후속을 안 잡으면 사용자는 두 번째 요청에서 하네스를 우회해 버린다.

### emitter가 실제로 쓰는 형태 (`_orchestrator_skill` 실측)

`emit_orchestrator.py`는 오케스트레이터 description을 이 골격으로 emit한다:

```yaml
description: "<name> 하네스를 Claude Code 프리미티브(Agent/TeamCreate)로 실행하는 오케스트레이터.
  '<name>' 관련 작업·생성·분석 요청 시 사용. 후속: 다시 실행, 재실행, 업데이트, 수정, 보완,
  '<name>의 일부만 다시', 이전 결과 기반 개선 요청 시에도 반드시 이 스킬을 사용."
```

이 형태가 좋은 이유: (a) 하는 일(프리미티브로 실행)과 트리거 상황(작업·생성·분석)을 함께 명시, (b) "반드시 이 스킬을 사용"으로 pushy, (c) **후속 6종(다시 실행·재실행·업데이트·수정·보완·부분 재실행·개선)을 명시적으로 잡아** 두 번째 요청에서 우회를 막음. (이 골격은 emitter가 **도메인 무관하게 동일하게** 찍는다 — `<name>`만 치환할 뿐 도메인 동의어를 주입하지 않는다. deep-research 산출물의 on-disk description도 정확히 이 템플릿이다: "deep-research 하네스를 … 후속: 다시 실행, 재실행, 업데이트, 수정, 보완, 'deep-research의 일부만 다시', 이전 결과 기반 개선 요청 시에도 반드시 이 스킬을 사용." 도메인 동의어("조사" 등)는 손작성 agent description이나 §2 트리거 니어미스 보강으로 추가하는 것이지 emitter가 채우지 않는다.)

### 나쁜 예시 (원본 보존)

- `"데이터를 처리하는 스킬"` — 너무 모호. 어떤 도메인·작업인지 불분명, 트리거 안 됨.
- `"리서치 관련 작업"` — 구체적 동작·트리거 상황 미기술.
- `"graph.json을 실행한다"` — 내부 구현 노출. 사용자 언어가 아니라 트리거가 안 걸린다. description은 **사용자가 쓰는 도메인 언어**로 쓴다(`graph.json` 같은 내부 용어는 본문에서만).

### 트리거 니어미스 검증 (원본 보존)

description을 쓴 뒤 **트리거 경계를 의심한다**: "이 도메인과 비슷하지만 하네스를 안 타야 하는 요청"을 3개 떠올려 description이 그것들을 흡수하지 않는지 확인하고, 반대로 "타야 하는데 표현이 살짝 다른 요청"(예: "조사" vs "리서치" vs "팩트체크") 3개를 흡수하는지 확인한다. 흡수 못 하면 동의어·후속 표현을 보강한다.

---

## 3. 본문 작성 스타일

### Why-not-ALWAYS 원칙 (원본 보존)

LLM은 **이유를 이해하면 엣지 케이스에서도 올바르게 판단**한다. `ALWAYS`/`NEVER` 같은 강압 규칙은 규칙이 닿지 않은 상황에서 무너진다. 맥락(왜)을 주면 일반화한다.

**나쁜 예:**
```markdown
ALWAYS run warrant.py before spawning agents. NEVER skip the cost band.
```

**좋은 예:**
```markdown
실행 전 `warrant.py --graph`로 토큰 비용 밴드를 표시하고 승인을 받는다.
budget.approval_required=true이고 budget.max_spawns가 런타임의 하드 ceiling이므로,
승인 없이 돌리면 사용자가 예상 못 한 토큰이 소모되고 ceiling 도달 시
budget_block(PreToolUse)이 exit-2로 spawn을 차단해 파이프라인이 부분결과로 중단되기 때문이다.
```

> **주의 — CYS에서 "강압 규칙"의 자리는 산문이 아니라 게이트·hook이다.** 원본은 모든 규칙을 산문으로 설득해야 했다. CYS에서 진짜 불변(스키마 준수, 모델 티어, write-path 비중첩, 절대경로 금지 등)은 **`validate_harness.py`(빌드 게이트), `warrant.py`(비용 게이트), 발화 hook(`spawn_counter`·`qa_gate_runner`·`gate_or_block`)**이 강제한다. 따라서 SKILL.md/agent 본문은 "Claude가 판단해야 하는 엣지"에만 Why를 쓰고, "기계가 막는 것"은 굳이 산문으로 반복하지 않는다(컨텍스트 절약). 산문으로 `ALWAYS write valid JSON`이라 쓰지 말고, 그건 `output_schema`가 강제하게 둔다.

### 일반화 원칙 (원본 보존)

피드백·테스트에서 문제가 발견되면 특정 예시 패치가 아니라 **원리 수준에서 일반화**한다.

**오버피팅 수정:**
```markdown
"Q4 매출" 티켓은 finance 큐로 보낸다.
```

**일반화된 수정:**
```markdown
티켓 본문에 금액·청구·환불 등 재무를 암시하는 키워드가 있으면 finance 큐로
라우팅한다. 모호하면 큐를 단정하지 말고 confidence를 낮춰 표기한다(다운스트림
합성 노드가 gap을 처리).
```

### 명령형 어조 (원본 보존)

"~합니다", "~할 수 있습니다" 대신 "~한다", "~하라". SKILL.md와 agent 본문은 지시서다.

### 컨텍스트 절약 (원본 보존 + CYS 강화)

컨텍스트 윈도우는 공공재다. 모든 문장이 토큰 비용을 정당화하는지 자문한다:
- "Claude가 이미 아는 내용인가?" → 삭제
- "이 설명이 없으면 실수하는가?" → 유지
- "구체적 예시 하나가 긴 설명보다 효과적인가?" → 예시로 대체
- **(CYS) "이건 게이트·스키마·agent파일·README가 이미 강제/기술하는가?"** → 삭제(중복 SOT 금지). 오케스트레이터 SKILL.md는 **graph.json의 얇은 사람용 뷰**이지 두 번째 진실원천이 아니다.

---

## 4. 오케스트레이터 본문 구조 (graph.json의 사람용 뷰)

오케스트레이터 SKILL.md는 자유 산문이 아니라 **graph.json을 사람·호스트세션이 읽을 수 있게 투영한 정형 문서**다. `emit_orchestrator.py`가 emit하는 실측 골격:

```markdown
# <name> Orchestrator

graph.json(불변 계약)에서 emit된 오케스트레이터. 산출 하네스를 **라이브 Claude Code 호스트 세션**에서
실행하며, 상속된 AWF 게놈 hook(컨텍스트 보존·보안·SubagentStop)이 발화하고, 각 노드의
`.claude/agents/<agent>.md` frontmatter(model·tools·maxTurns)가 Agent 도구에 의해 런타임 강제된다.

## 실행 모드: <mode> (agent=순차 sub-spawn; team/hybrid=TeamCreate/SendMessage 실제 emit; hybrid 단계별 혼합은 future work=현재 team 레시피)

## 에이전트 구성
| 노드 | agent | model | mechanism | tools | 출력 |   ← graph.json에서 그대로 베껴옴

## 워크플로우
### Phase 0: 장기기억 회상 + 컨텍스트 + SOT 초기화   (Tier-II 회상→_recall.json, state.yaml 단독 쓰기, 재실행 분기)
### Phase 1: 비용 승인              (warrant.py --graph → 밴드 → 승인 대기 → budget.max_spawns 설정)
### Phase 2: 노드 실행 + 품질 게이트  (agent: _spawn_recipe / team: _team_recipe + 토폴로지 addendum)
### Phase 3: 통합 산출 + 측정        (state.yaml outputs → git commit → (선택) h2h)

## 메모리 운영 (Tier I 세션연속성 + Tier II 교차실행 메모리 — 상속 게놈 hook이 발화)
## 진화 (매 실행 후 — evolve_harness.py 라우팅)
## 비용 거버넌스 / 에러 핸들링 / 테스트 시나리오
```

규칙:
- **phase-count는 README와 일치해야 한다.** `validate_harness.py`의 DOC_DRIFT가 README와 오케스트레이터 SKILL.md의 phase 수가 다르면 잡는다(level은 constants). emitter의 `PHASES`(4단계)와 `_readme`가 같은 리스트를 공유하므로 기본 emit은 정합하지만, 손으로 단계를 더하면 README도 함께 고친다.
- 표의 model·메커니즘·tools·출력 경로는 **graph.json에서 그대로 베껴온다**(손으로 다른 값을 쓰면 두 SOT 충돌). graph.json이 진실, 표는 뷰. (emitter는 `_tools_for(node)`로 least-privilege 기본을 채운다 — §5.)
- **실행 모드는 본문 첫 줄에 명시**한다. 기본은 `agent`(toposort 순서로 `Agent(subagent_type=…)`를 순차/병렬 spawn, 에이전트 간 실시간 comms 없음). `team`은 **실시간 peer-to-peer 조율이 필수**일 때만이고, 그 경우 `_team_recipe`가 `TeamCreate / TaskCreate(deps) / SendMessage / TeamDelete`를 실제로 emit한다(agent emit과 byte-동일이 아님 — `TEAM_EMIT_PRESENT`). 팀 모드는 `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` 플래그가 없으면 `Agent()` fan + `_workspace/` 핸드오프로 **graceful degrade**한다(`TEAM_GRACEFUL_DEGRADE`).
- 실행 레시피는 **있는 그대로 호출형으로** 적는다(추상적 설명 금지). agent 모드: `Agent(subagent_type="<agent>", model="<model>")` — 입력=직전 노드 출력, 반환=JSON(output_schema 준수). team 모드: `TeamCreate(team_name="<name>-team", members=[…])` → `TaskCreate(subject, owner, depends_on)` → `SendMessage` → `TeamDelete`.
- **토폴로지별 addendum**(`_topology_addendum`): `fan-out-fan-in`·`supervisor`·`expert-pool`·`hierarchical`은 Phase 2에 토폴로지 고유 레시피가 추가된다(`TOPOLOGY_PRIMITIVE_CONSISTENCY`). 토폴로지·메커니즘의 상세는 `graph-and-orchestration.md`를 참조한다.

---

## 5. 에이전트 정의 저작 (NEW — I1: `.claude/agents/<agent>.md`)

원본에는 없던 CYS 산출물이다. 각 노드의 `node.agent`마다 `.claude/agents/<agent>.md` 파일을 저작한다. 이 파일이 **서브에이전트가 읽는 실제 작업 지시서**이고, frontmatter는 Agent/TeamCreate 프리미티브가 **런타임 강제**하는 계약이다(Mode-A 워크플로우의 general-purpose 다운그레이드와 정반대). `emit_orchestrator.py:_write_agent_files`가 기존 손작성 본문·description은 보존하고 **런타임 강제 필드만 정규화**한다.

### 5.1 frontmatter 필드 (전부 emit됨, V1/V3가 강제)

emitter가 채우는 **기본(default) frontmatter 형태**(손작성 값이 없을 때의 fallback). 실제 on-disk `researcher.md`는 `description`("Use FIRST for any deep-research request…")과 `tools`(`WebSearch, WebFetch, Read, Write`)를 손으로 override하며, `_write_agent_files`는 그 손작성 값을 보존한다 — 아래는 override 전 emitter 골격이다:

```yaml
---
name: researcher
description: "gather-class worker for the deep-research harness (node 'gather'). ..."
model: haiku                                  # REQUIRED — node.model과 일치해야 함
model_rationale: "Pure web search + claim drafting, no cross-source judgment — cheapest tier."
tools: Read, Glob, Grep, WebSearch, WebFetch  # least-privilege (role-class 기본 또는 node.tools)
maxTurns: 25                                  # _DEFAULT_MAXTURNS (node 미지정 시)
---
```

- **`name`·`description`·`model` 필수.** 비면 `validate_harness.py`가 `AGENT_FRONTMATTER`(error). agent 파일 자체가 없으면 `AGENT_EXISTS`(error).
- **`model`은 `node.model`과 일치**해야 한다. 어긋나면 `TIER_MISMATCH`(error). model은 **role-tier로 해결**되며 idoforgod의 all-opus와 달리 하드코딩하지 않는다(보존된 강점 — §5.3). model이 비거나 무효면 `TIER_MISSING`(error).
- **`model_rationale` 필수**(기본 level=warn, `constants.MODEL_RATIONALE_MISSING`). 비면 `RATIONALE_MISSING`. emitter는 손작성 rationale이 없으면 `"role-class '<rc>' -> tier <model> per model-tier-policy"`로 채운다.
- **`tools`는 least-privilege.** `node.tools`가 있으면 그대로, 없으면 role-class별 기본(`_ROLE_TOOLS`): gather=`Read, Glob, Grep, WebSearch, WebFetch`, extract=`Read, Glob, Grep`, format=`Read, Write`, qa-scan=`Read, Glob, Grep, Bash`, voter=`Read, Glob, Grep, WebSearch`, debater=`Read, Glob, Grep, WebSearch`, reviser=`Read, Write, Glob, Grep`, synthesis=`Read, Write, Glob, Grep`, judge=`Read, Glob, Grep`, critic=`Read, Glob, Grep, WebSearch, WebFetch`, architecture=`Read, Glob, Grep`. 그 외 fallback `Read, Glob, Grep`. **도구를 넓히려면 node.tools로 명시적으로 추가**하고, 왜 필요한지를 본문 작업원칙에 적는다(추측 기반 권한 확장 금지 — 단순성·최소권한).
- **`maxTurns`는 `node.maxTurns` 또는 기본 25**(`_DEFAULT_MAXTURNS`). 턴 폭주를 막는 런타임 한계.

### 5.2 본문 구조 (서브에이전트가 읽는 실행 지시서)

본문이 비어 있으면 emitter가 최소 골격(핵심역할 + "output_schema에 맞는 JSON만 반환, 도구는 frontmatter allowlist로 제한")을 채운다. 손으로 쓸 때 권장 골격:

```markdown
핵심 역할: <node_id> 노드의 작업을 수행한다.

작업 원칙 (Why-not-ALWAYS): 입력(직전 노드 출력)을 받아 <schema> 스키마에 맞는 JSON만 만든다 —
  스키마는 다음 노드의 계약이므로 어긴 산출물은 파이프라인을 끊는다. 추측 금지, 불확실하면
  출처를 병기한다(삭제 금지).

입출력 프로토콜: 입력 경로 / 출력 스키마(schemas/<name>.json) / 산출물 경로(_workspace/...).

에러 핸들링: on_exhaust와 정합 — proceed-with-gap 노드는 빈 배열로 스키마는 유지(§7.2 규칙4).
```

> **메모리 입력 계약(머신강제, `AGENT_MEMORY_CONTRACT`)**: 모든 에이전트 본문은 Phase-0 회상 릴레이 `_workspace/_recall.json`을 Read한다는 절을 가져야 한다. 손으로 안 써도 `_write_agent_files`가 표준 "메모리 입력 (회상 주입)" 블록을 **자동 append**한다(손작성 본문도 보존 후 append). validate의 `AGENT_MEMORY_CONTRACT`가 노드 agent 파일에 `_recall.json` 참조가 없으면 error로 차단한다 — 회상이 실제로 *소비*되도록(presence가 아니라 wiring) 강제한다.

- **본문 예시가 schema와 어긋나면 모델이 헷갈린다.** schema가 진실, 본문 예시는 그것의 미리보기.
- **에러핸들링은 `node.on_exhaust`와 정합**시킨다. `on_exhaust=proceed-with-gap` 노드의 본문은 "빈 배열(`claims: []`)로 degraded 진행"을 지시한다.

### 5.3 team-comms 섹션 (team/hybrid 모드 노드)

노드가 **team 모드 스테이지**에 속하면 본문에 **team-comms 프로토콜**을 함께 적는다. 이유: `_team_recipe`가 emit하는 멤버 목록은 한 줄짜리 **flat 식별자**(`` `<agent>` (model=…, tools=…) — '<nid>' 노드 ``)일 뿐 역할·I/O·통신 규약을 담지 않는다 — 팀원의 실제 작업·통신 규약은 frontmatter가 가리키는 자기 `.claude/agents/<agent>.md` 본문에서 읽는다. 따라서 team-comms 프로토콜은 오케스트레이터가 아니라 **그 agent 파일 본문**이 SOT이고, 거기에 적지 않으면 팀원이 통신 규약을 모른 채 spawn된다(`TaskCreate`/`SendMessage` 단계는 `_team_recipe`가 별도로 emit하지만 그 안에 노드별 프로토콜은 들어가지 않는다). 본문에 적을 것:

- **peer-to-peer 통신**: 상충·누락 발견 시 `SendMessage`로 관련 팀원에게 직접 공유(리더 우회). 모든 것을 Lead로 올리지 않는다.
- **적대적 검증의 격리**: reviewer/fact-checker는 팀원이 아니라 별도 `Agent(subagent_type="reviewer")`로 spawn된다(L2) — 팀 내부에 두지 않는다.
- **Team Lead 핸드오프**: 산출물은 `_workspace/`에 flush하고 `TaskUpdate(status=completed)`로 알린다. Lead가 거기서 읽어 L0-L2 게이트를 통과시킨다.

### 5.4 in-project 설치: `cys_emitted` provenance 마커

`emit_orchestrator.py <TARGET> --in-project`로 **기존 호스트 프로젝트에 오버레이 설치**할 때, emit된 노드 agent 파일에는 `cys_emitted: "<harness_name>"` frontmatter 마커가 찍힌다. 이건 **provenance 가드**다: `_write_agent_files`는 in-project 모드에서 같은 이름의 호스트 agent 파일이 이미 있고 **`cys_emitted` 마커가 없으면**(즉 호스트 소유면) emit을 **거부**한다(`SystemExit` — 호스트의 `.claude/agents/<x>.md`를 절대 탈취하지 않음). 충돌 시 해결책은 graph 노드의 `.agent` 이름을 바꿔 호스트와 겹치지 않게 하는 것이다.

> 단, **L2 DNA 예외**: 적대적 리뷰 agent(`reviewer`/`fact-checker`)는 head-to-head 변별력의 핵심이라 게놈판을 **강제 설치**하고, 충돌 시 호스트 원본은 `.harness/genome/displaced/`로 백업(파괴 없음)된다. 이 force-install은 도메인 노드 agent의 collision-guard와는 별개의 정책이다(상세는 `genome-and-runtime.md`).

---

## 6. 도메인 스킬: 하이브리드 author-or-inline (I2)

idoforgod의 정의적 기능은 에이전트 정의(**누가=who**, `.claude/agents/`)와 별개로 **per-agent 스킬(어떻게=how)**을 생성하는 것이다. CYS는 그 **FORM**을 채택하되, author-or-inline 선택을 **머신체크되는 graph.json 필드**로 만든다: 각 노드는 `skill_authoring{mode, reason, shared_by}`를 가질 수 있다. `emit_domain_skill.py`가 이 필드를 읽어 **`mode=="skill"` 노드만** `.claude/skills/<harness>-<node_id>/SKILL.md`(pushy-described 'how' 패키지)를 저작한다.

### 6.1 하이브리드 판단 규칙 (throwaway 스킬 방지)

```
mode = "inline"  (기본) → 'how'를 agent 본문에 둔다 (별도 스킬 파일 없음)
mode = "skill"   → .claude/skills/<harness>-<node_id>/SKILL.md 를 저작
```

`mode=="skill"`은 **`reason`이 다음 셋 중 하나일 때만** 정당하다(`validate_harness.py:SKILL_AUTHORING_JUSTIFIED`):

| reason | 언제 | 추가 제약 |
|--------|------|----------|
| `reuse` | 같은 'how'를 **≥2개 노드**가 재사용 | `shared_by`에 재사용 노드를 **2개 이상** 나열해야 함 (미달이면 `SKILL_AUTHORING_JUSTIFIED` error) |
| `complex` | 'how'가 길고 다단계라 agent 본문에 인라인하면 컨텍스트를 과하게 먹음 | — |
| `conditional` | 'how'가 조건부로만 필요(매 실행 로드는 낭비) — progressive disclosure 대상 | — |

`reason`이 이 셋 밖이면 `SKILL_AUTHORING_JUSTIFIED`(error). 이 규칙은 AWF 자신의 번들링 규율을 미러링한 것으로, **FORM이 실제 capability를 더할 때만** 스킬을 저작하게 한다(노드마다 throwaway 스킬을 찍는 것을 막음). 그 외에는 `inline`이 기본이고, 'how'는 agent 본문(§5.2)에 둔다.

### 6.2 정합성 가드 (양방향)

- **`mode=="skill"`인데 SKILL.md가 없으면** → `INLINE_NO_ORPHAN_SKILL`(error). `emit_domain_skill.py`를 돌려야 한다(emit_orchestrator가 1.5단계에서 자동 호출하므로 보통 함께 생성됨).
- (역방향) inline 노드가 도메인 스킬을 가지면 안 된다 — emit이 skill-mode 노드만 디렉토리를 만들므로 구조적으로 막힌다.

### 6.3 LIFT 게이트 — 저작한 스킬은 baseline을 이겨야 산다 (P1.3, "게이트에 이빨")

도메인 스킬을 저작했다고 끝이 아니다. 그 스킬이 **no-skill baseline(haiku)을 실제로 이기는지**를 측정해야 한다:

- **미측정**(`lift_verdict.json` 없음) → `LIFT_UNMEASURED`. 정책 제어(`constants.LIFT_UNMEASURED`, 기본 `warn`; `error`로 올려 미측정 스킬 출하 금지 가능). `lift_gate.py score <results> --out <skill>/lift_verdict.json`이 validate가 읽는 정확한 경로에 verdict를 쓴다.
- **측정했으나 baseline 미달**(`lift_verdict.json` 존재 + `decision != "register"`) → `LIFT_REFUSED`(**hard error**). baseline에 진 스킬은 출하 불가 — **인라인하거나 개선**하라. verdict가 깨졌거나(truncated write·bad merge) JSON object가 아니어도 `LIFT_REFUSED`(읽을 수 없는 verdict는 유효 등록이 아님). 이 hard error가 게이트에 이빨을 준다(이전엔 presence-warn뿐이었다).

즉 측정-실패가 빌드를 실제로 막는다. 약한 스킬을 description만 pushy하게 써서 출하하는 길은 `LIFT_REFUSED`가 닫는다.

### 6.4 emit되는 도메인 스킬 형태 (`_skill_md` 실측)

`emit_domain_skill.py`가 쓰는 SKILL.md는 pushy description("'<node_id>' 관련 생성·분석·재실행·보완 작업 시 반드시 이 스킬을 사용. 후속: 다시, 수정, 개선 요청 시에도 사용.") + 본문(작업 원칙 Why-not-ALWAYS / 입출력 프로토콜 / 품질 L0-L1.5)을 담는다. `reason=="reuse"`면 `shared_by` 노드를 본문에 "공유(reuse): 이 스킬은 노드 X, Y가 재사용한다"로 적시한다. 이 도메인 스킬은 노드의 **how**만 담고 **who**(에이전트)는 `.claude/agents/`에, **트리거**는 오케스트레이터 description에 둔다(§9 중복 금지).

---

## 7. output_schema 설계 (머신검증 계약)

원본의 "출력 형식 정의"는 산문 마크다운 템플릿(`# 제목 / ## 요약 / ...`)이었다. CYS에서 출력 형식은 **노드별 `output_schema` JSON Schema 파일**로 승격된다 — 사람용 권고가 아니라 **런타임이 강제하는 계약**이다. 프리미티브 substrate에서 각 노드는 `Agent(subagent_type, model)`로 spawn되고 **output_schema 준수 JSON을 반환**해야 하며(오케스트레이터 본문의 `_spawn_recipe`가 "반환=JSON(`<schema>` 스키마 준수)"로 명령), 스키마를 어긴 산출물은 다운스트림 계약을 깨므로 품질게이트(L0)에서 막힌다. (스키마가 `agent({schema})`로 강제되던 Mode-A 런타임은 은퇴했고, 프리미티브에서는 반환 JSON을 게이트가 검증한다.)

### 7.1 작성 위치와 참조

- 파일: `schemas/<name>.json` (하네스 루트 기준 상대경로). `node.output_schema`에 이 상대경로를 적는다.
- `reflect-then-revise` 노드는 critic 패스용 `schemas/critique.json`이 **추가로** 필요하다.
- `validate_harness.py`의 `SCHEMA_FILE_EXISTS` 체크가 `node.output_schema`가 가리키는 파일의 존재 + 유효 JSON + 최상위 `type` 키를 강제한다(없으면 빌드 실패).

### 7.2 절대 규칙 (machine-enforced)

1. **`additionalProperties: false`** — 모든 object 레벨에 둔다(중첩 포함). 서브에이전트가 임의 필드를 끼워 넣어 다운스트림을 오염시키는 것을 막는다.
2. **`$schema`·`$id` 메타키는 소스 파일에 적어도 된다**(에디터·IDE 검증 편의; deep-research 실측 `findings.json`도 `$id: "findings.json"`을 가짐). bare-filename `$id`만 쓴다. (참고: 이 두 메타키는 Mode-A 인라인 경로에서 `_clean_schema()`가 떼어냈다 — 그 인라이너는 공장내부 측정 전용 `emit_workflow.py`에 있고 제품 프리미티브 경로에는 무관하다.)
3. **`$ref` 금지.** 공유 구조가 필요하면 그냥 인라인 복제한다(단일 사용 추상화 금지 원칙과도 일치).
4. **`required`를 정직하게 명시.** 다운스트림이 의존하는 키는 required. 단, **빈 결과도 스키마는 유지**되게 설계한다(예: `claims: []`, `sources: []` 허용) — `on_exhaust: proceed-with-gap` 노드가 빈 배열로 degraded 진행할 수 있어야 하므로 배열 자체는 required지만 `minItems`는 두지 않는다.
5. **enum·min/max로 값 도메인을 좁힌다.** `severity: enum[low,med,high]`, `confidence: number min 0 max 1`. 자유 문자열보다 enum이 다운스트림 분기를 안전하게 한다.

### 7.3 스키마가 곧 노드 간 계약 (cross-comparison 가능)

스키마는 **노드 경계의 교차 비교 지점**이다(QA 경계 cross-comparison 지혜의 CYS 구현). 한 노드의 output_schema 필드가 다음 노드의 입력·다음 스키마와 **상호 참조 가능한 안정 키**를 갖도록 설계하면, 적대적 리뷰·팩트체크 노드가 경계를 기계적으로 검증할 수 있다.

deep-research 실측 — `findings.json`이 만든 키를 `critique.json`이 참조하고 `report.json`이 다시 참조한다:

```json
// schemas/findings.json (gather/fetch/reviser 산출)
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "findings.json",                                       // ← bare-filename
  "type": "object", "additionalProperties": false,
  "required": ["claims", "sources"],
  "properties": {
    "claims": { "type": "array", "items": {
      "type": "object", "additionalProperties": false,
      "required": ["id", "text", "source_ids", "confidence"],
      "properties": {
        "id":         { "type": "string" },                     // ← critique가 claim_id로 참조
        "text":       { "type": "string" },
        "source_ids": { "type": "array", "items": { "type": "string" } },  // ← sources[].id로 해소
        "confidence": { "type": "number", "minimum": 0, "maximum": 1 }
      } } },
    "sources": { "type": "array", "items": {
      "type": "object", "additionalProperties": false,
      "required": ["id", "url", "title"],
      "properties": { "id": {"type":"string"}, "url": {"type":"string"}, "title": {"type":"string"} }
    } }
  }
}
```

```json
// schemas/critique.json (reflect-then-revise critic 산출)
{
  "type": "object", "additionalProperties": false,
  "required": ["approved", "issues"],
  "properties": {
    "approved": { "type": "boolean" },                          // ← true면 revise 루프 조기 종료
    "issues": { "type": "array", "items": {
      "type": "object", "additionalProperties": false,
      "required": ["claim_id", "problem", "severity"],
      "properties": {
        "claim_id": { "type": "string" },                       // ← findings claims[].id를 가리킴
        "problem":  { "type": "string" },
        "severity": { "type": "string", "enum": ["low", "med", "high"] }
      } } }
  }
}
```

설계 의도가 스키마에 박혀 있다: `critique.approved=true`는 reviser 루프를 조기 종료시키는 **제어 신호**이고(`_spawn_recipe`의 reflect-then-revise 레시피가 "approved=true면 조기 종료"로 emit), `issues[].claim_id`는 `findings.claims[].id`를 가리켜 **어떤 claim이 왜 문제인지**를 추적한다. 스키마 필드는 단순 데이터가 아니라 **메커니즘의 배선**이다 — "다음 노드가 이 키로 무엇을 분기하는가"를 항상 함께 생각한다.

### 7.4 스키마 description은 토큰을 쓸 값어치가 있다

각 필드의 `description`은 서브에이전트가 무엇을 채워야 하는지 알려주는 인-밴드 지시다. "이 키가 어디서 참조되는지"를 적으면 모델이 안정 키를 일관되게 부여한다. 예: `"id": "Stable claim identifier, referenced by critique.issues[].claim_id."`. 단 컨텍스트 절약 원칙 적용 — 자명한 필드는 description 생략.

---

## 8. Progressive Disclosure 패턴

원본의 3패턴을 CYS 레이아웃으로 보존한다. **얇은 본문 + 깊은 references**가 핵심.

### 패턴 1: 도메인별 분리 (원본 보존)

오케스트레이터가 여러 하위 도메인을 다루면 references로 쪼갠다:

```
<harness>-orchestrator/
├── SKILL.md              (개요 + 노드 표 + 어떤 reference를 언제 읽나)
└── references/
    ├── routing-rules.md  (티켓 → 큐 분류 기준)
    └── escalation.md     (on_exhaust=escalate 시 사람 핸드오프 절차)
```

사용자가 라우팅을 물으면 `routing-rules.md`만 로드.

### 패턴 2: 조건부 상세 (원본 보존)

```markdown
## 실행
표준 실행은 위 4단계(Phase 0~3)를 따른다.

**부분 재실행이 필요하면**(일부 노드만 갱신): [references/resume.md](references/resume.md)
**team 모드로 마이그레이션해야 하면**: [references/team-migration.md](references/team-migration.md)
```

이것이 §6의 `skill_authoring.reason="conditional"`과 짝을 이룬다 — 매 실행에 필요 없는 'how'는 도메인 스킬로 떼어 조건부 로드한다.

### 패턴 3: 대형 레퍼런스 파일 구조 (원본 보존)

150줄 이상 reference 파일은 상단에 목차를 둔다. (이 파일이 그 예다.)

### CYS 추가: "다시 만들지 말 것"을 본문에 1줄 적시

자식 하네스는 게놈을 상속하므로 컨텍스트 보존·품질 게이트·보안 hook을 **이미 갖고 있다**. 오케스트레이터 본문에서 이 기능들을 다시 설명하면 토큰 낭비 + 두 번째 SOT가 된다. 필요하면 "상속된 게놈 기계는 `CLAUDE.md` §CYS Harness Engine / `genome-and-runtime.md` 참조" 한 줄로 가리키고 본문은 도메인 로직에만 쓴다.

---

## 9. 세 원천의 역할 분담 (중복 금지)

원본에서는 "스킬 본문"이 트리거 + 도메인 지식 + 실행 절차를 다 담았다. CYS는 **여러 원천으로 분산**되고, 각 원천이 자기 몫만 가진다(SOT 중복 금지):

| 정보 | 어디에 | 비고 |
|------|--------|------|
| 트리거(언제 이 하네스를) | 오케스트레이터 `description` | §2 |
| 단계·에이전트표·실행/재개 레시피(사람·세션용 뷰) | 오케스트레이터 본문 | §4, graph.json의 투영 |
| **노드의 실제 작업 지시**(핵심역할·작업원칙·I/O 프로토콜·team-comms·에러핸들링) | `.claude/agents/<agent>.md` 본문 | §5 — 서브에이전트가 읽는 실행 지시서 |
| 노드의 'how'(reuse/complex/conditional일 때만) | `.claude/skills/<harness>-<node_id>/SKILL.md` | §6 — 그 외엔 agent 본문에 inline |
| 출력 형식(강제) | `schemas/*.json` | §7 |
| 단계 수 등 사실 | README ↔ 오케스트레이터(일치 강제) | DOC_DRIFT |
| model·tools·maxTurns(런타임 강제) | agent frontmatter (= node.model/tools) | V1/V3 — graph.json이 진실 |

오케스트레이터 SKILL.md에 노드의 작업 지시를 다시 쓰지 않는다 — 그건 agent 파일(inline) 또는 도메인 스킬(skill-mode)의 몫이다. agent 본문에 트리거를 쓰지 않는다 — 그건 description의 몫이다.

---

## 10. 측정·평가 데이터 스키마 표준 (lift_gate · h2h)

스킬/하네스의 테스트·헤드투헤드 측정에 쓰는 표준 스키마(원본 보존 + CYS 도구 연결). CYS에서 측정은 산문 주장이 아니라 **`lift_gate.py`**(with-skill vs haiku baseline, 독립 블라인드 그레이더 → `register`/`refuse`, §6.3의 `LIFT_REFUSED`로 빌드 게이팅)와 **`h2h_suite.workflow.js`/`h2h_aggregate.py`**(n-run median 헤드투헤드, 공장내부 측정 전용)가 수행한다 — 원본의 "with-skill vs without A/B 규율"의 기계화.

### eval_metadata.json (원본 보존)

```json
{
  "eval_id": 0,
  "eval_name": "descriptive-name-here",
  "prompt": "사용자의 작업 프롬프트",
  "assertions": ["산출물에 X가 포함되어 있다", "Y 형식으로 파일이 생성되었다"]
}
```

### grading.json (원본 보존 — 필드명 엄격)

```json
{
  "expectations": [
    { "text": "산출물에 '서울'이 포함됨", "passed": true,
      "evidence": "3번째 단계에서 '서울 지역 데이터 추출' 확인" }
  ],
  "summary": { "passed": 2, "failed": 1, "total": 3, "pass_rate": 0.67 }
}
```

**필드명 주의:** `text`, `passed`, `evidence`를 정확히 사용한다(`name`/`met`/`details` 변형 금지). lift_gate/h2h 그레이더가 이 필드명을 파싱한다.

### timing.json (원본 보존 + CYS budget 연결)

```json
{ "total_tokens": 84852, "duration_ms": 23332, "total_duration_seconds": 23.3 }
```

서브에이전트 완료 알림(SubagentStop)에서 `total_tokens`·`duration_ms`를 **즉시 저장**한다 — 알림 시점에만 접근 가능, 이후 복구 불가. CYS에서 `total_tokens`는 warrant 비용밴드 사후 검증에 직접 쓰이므로 더 중요하다. 단, spawn ceiling은 토큰이 아니라 **spawn 횟수**로 강제된다(`budget.max_spawns`, `spawn_counter`/`budget_block` hook) — duration은 관측용 메타이지 제어 신호가 아니다.

### h2h 측정 정직성 (P1.4)

`h2h_suite`는 flake run(null/throw)을 0점이 아니라 **DROP**한다(가짜 0이 중앙값을 왜곡 못 함) + `tryAgent` 재시도 래퍼 + provenance `n_attempted/n_valid/n_dropped`. `h2h_aggregate.py`는 무효 run을 raise가 아니라 **필터링**해 부분실패 suite를 정직하게 집계한다. 현 stamped 측정은 **n=5 median +12.5pp `INCONCLUSIVE`**(15pp 마진 미달, CYS 우세)이며 — 이 수치를 넘는 주장을 산출 하네스 README/SKILL에 적으면 `validate_harness.py`의 `MEASUREMENT_DRIFT`가 잡는다(verdict 없이 CYS-WINS 광고 금지). (`STALE_BENCHMARK`는 validator 코드가 아니라 공장내부 단위 테스트(`tests/test_factory.py`)이며, 산출 하네스가 아니라 **공장 자신의 `design/` 비교 문서**만 스캔한다 — 산출 하네스 문서는 `MEASUREMENT_DRIFT`만 가드한다.) **약한 데이터를 날조하지 않는다**.

---

## 11. SKILL.md/agent에 포함하지 않을 것

- README.md·CHANGELOG.md·INSTALLATION_GUIDE.md 등 부가 문서 (오케스트레이터 SKILL.md 자체에 녹이지 않는다)
- 스킬/하네스 생성 과정의 메타 정보(테스트 결과, 반복 이력, 어느 warrant 판정이 나왔는지)
- 사용자 대상 설명서 — SKILL.md/agent는 AI 에이전트용 지시서다(사람용은 README)
- 이미 Claude가 아는 일반 지식
- **(CYS) 게놈이 이미 주는 것의 재설명** — 컨텍스트 보존 hook·품질 게이트·보안·발화 hook 동작을 본문에 베끼지 않는다(§8 마지막, `genome-and-runtime.md`로 위임)
- **(CYS) graph.json의 두 번째 사본** — 표는 graph.json의 뷰일 뿐, node 정의·예산·메커니즘 파라미터의 원천이 되려 하지 않는다
- **(CYS) 원천 교차 중복** — 노드 작업지시는 agent/도메인스킬에만, 트리거는 description에만, 출력형식은 schema에만(§9)
- **(CYS) `.claude/commands/`를 비울 필요 없음** — 게놈이 commands(install·maintenance 등)를 정당하게 상속한다(원본 `NO_COMMANDS` 규칙은 폐기). 오케스트레이터는 슬래시 커맨드가 아니라 **description 트리거 + Agent/TeamCreate 호출**로 동작하며, **새 도메인 커맨드를 직접 만들지는 않는다**

---

## 12. 진화·피드백 루프 (관찰 → 일반화)

원본의 진화 루프 + 스크립트 번들링 판단 지혜를 CYS로 적응한다. 헤드투헤드/lift 측정과 실제 실행 트랜스크립트를 **관찰**해서 description·agent·도메인스킬·스키마를 개선한다. 라우팅은 `evolve_harness.py . --type <유형>`이 결정론적으로 대상에 매핑한다(상세는 `evolution-and-memory.md`).

| 관찰 신호 (트랜스크립트/h2h에서) | evolve 유형 | CYS 조치 |
|------|------|------|
| 서브에이전트가 매번 같은 형식 실수를 함 | result-quality | output_schema에 enum/required/`additionalProperties:false` 보강 (산문 경고 추가 아님) |
| 트리거가 안 걸린 near-miss 요청 발견 | trigger-miss | 오케스트레이터 description에 동의어·후속 표현 추가 (§2) |
| 한 노드가 만성적으로 retry 소진 | result-quality | on_exhaust 재검토 + 그 노드의 model 티어/메커니즘 재검토 (예: single → reflect-then-revise) |
| 두 노드 경계에서 키 불일치로 다운스트림 깨짐 | result-quality | 두 schema의 cross-reference 키를 정렬 (§7.3) |
| 비용밴드가 예산을 자주 초과 | agent-role | pure-retrieval 노드 opus → haiku 강등(`TIER_OVERSPEND`), fan-out n 축소, budget 재산정 |
| 한 노드의 'how'가 다른 노드에서도 필요해짐 | result-quality | `skill_authoring.mode=skill`(reason=reuse, shared_by≥2)로 승격 + lift 측정 (§6) |
| 저작한 도메인 스킬이 baseline을 못 이김 | result-quality | `LIFT_REFUSED` — 인라인으로 강등하거나 개선 (§6.3) |

**일반화 규율(원본 보존):** 한 테스트 케이스를 고치려고 좁은 패치를 박지 않는다. 원리 수준으로 올려 스키마·티어 정책·description 동의어 같은 **구조에 반영**한다. 그래야 다음 하네스에도 전이된다.

**번들링 대신 게놈·스키마·도메인스킬(원본 적응):** 원본은 반복 헬퍼를 `scripts/`에 번들했다. CYS에서 반복 절차는 대개 (a) 이미 게놈이 제공(중복 금지)하거나 (b) output_schema/agent 작업원칙으로 표준화하거나 (c) `reason=reuse` 도메인 스킬로 끌어올리면(shared_by≥2 + lift 통과) 사라진다. 정말 도메인 고유의 결정론 헬퍼가 필요하면 graph 외부 스크립트가 아니라 **agent의 tools**(least-privilege)나 **노드 메커니즘**으로 표현할 수 있는지 먼저 본다.

**검증 후 진화:** 어떤 변경도 `validate_harness.py` PASS(머신체크 세트) → `warrant.py` 비용밴드 승인 → 헤드투헤드 재측정의 순서를 다시 통과해야 등록된다. 진화가 계약을 퇴행시키지 못한다(라우팅된 수정은 반드시 validate 재통과). 정직 미달(baseline을 못 이김)이면 `lift_gate`가 refuse(`LIFT_REFUSED`)하고, 그 사실을 사용자에게 정직하게 보고한다(원본의 A/B 정직성 규율의 기계화).
