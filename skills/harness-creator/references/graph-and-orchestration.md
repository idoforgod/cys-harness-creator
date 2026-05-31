> ⚠️ **구현 현황은 [`IMPLEMENTATION-STATUS.md`](IMPLEMENTATION-STATUS.md)가 우선한다.** 이 문서의 설계 서술이 무엇을 주장하든, 실제로 emit/validate에 구현됐는지는 그 문서로 확정한다. (근거: `emit_orchestrator.py`·`warrant.py`·`validate_harness.py`·`graph.schema.json` 실측.)

# graph.json과 오케스트레이션

> ⚠️ **PIVOT (2026-05-29) — 제품 런타임은 100% Claude Code 프리미티브다.** 산출 하네스의 canonical 오케스트레이터는 **emit된 오케스트레이터 SKILL.md**(`emit_orchestrator.py` 생성, Claude Code 프리미티브 `Agent`/`TeamCreate`/`SendMessage`/`TaskCreate` 구동)다. Mode-A `workflow.js`(`emit_workflow.py`)는 **제품에서 은퇴**했고(`WORKFLOW_RETIRED`), **공장내부 측정 도구로만** 잔존한다(h2h 측정 레인). 이 문서에서 `workflow.js`/`emit_workflow`가 등장하는 곳은 (a) 옛 설계와의 대조이거나 (b) "공장내부 측정 전용"으로 명시된 경우뿐이다 — **산출 하네스가 실행되는 방식이 아니다.** 구현 현황은 `IMPLEMENTATION-STATUS.md` 우선.

> 출처: 원본 `orchestrator-template.md`을 CYS 패러다임으로 적응. 원본의 "오케스트레이터 = 프롬프트로 직접 쓰는 상위 스킬(팀 기본)" 모델을 "오케스트레이터 = `graph.json`(불변 계약)에서 **emit된** 프리미티브 오케스트레이터 SKILL"로 전환했다 — 산문을 직접 쓰는 대신 graph를 저작하면 도구가 산문을 생성한다.

---

## 목차

1. [핵심 전환: graph.json 계약 → emit된 오케스트레이터 SKILL](#1-핵심-전환-graphjson-계약--emit된-오케스트레이터-skill)
2. [graph.json 저작 템플릿 (채워넣기)](#2-graphjson-저작-템플릿-채워넣기)
3. [node 필드 레퍼런스](#3-node-필드-레퍼런스)
4. [7 topology × 4 decision_mechanism — 직교 좌표계](#4-7-topology--4-decision_mechanism--직교-좌표계)
5. [emit_orchestrator.py: graph.json → 오케스트레이터 SKILL + agents](#5-emit_orchestratorpy-graphjson--오케스트레이터-skill--agents)
6. [데이터 패싱: inputs/outputs · _workspace · output_schema](#6-데이터-패싱-inputsoutputs--_workspace--output_schema)
7. [에러 핸들링: on_exhaust + retries (원본 에러 매트릭스 대체)](#7-에러-핸들링-on_exhaust--retries-원본-에러-매트릭스-대체)
8. [budget / approval](#8-budget--approval)
9. [RUNTIME.json 라우팅: 단일 실행 런타임 = 오케스트레이터 SKILL](#9-runtimejson-라우팅-단일-실행-런타임--오케스트레이터-skill)
10. [후속 작업 지원 (재실행 · 부분 재실행 · 마이그레이션)](#10-후속-작업-지원-재실행--부분-재실행--마이그레이션)
11. [team / hybrid — 언제, 왜, 어떻게 emit되나](#11-team--hybrid--언제-왜-어떻게-emit되나)
12. [작성 원칙 (강제 게이트로 환원)](#12-작성-원칙-강제-게이트로-환원)

---

## 1. 핵심 전환: graph.json 계약 → emit된 오케스트레이터 SKILL

원본은 오케스트레이터를 **프롬프트로 직접 쓰는 상위 스킬**로 보았다 — Phase별 산문, `TeamCreate`/`SendMessage`/`TaskCreate` 호출을 사람이 작성, "팀이 기본". CYS는 그 *산문 직접저작*을 버리되, idoforgod의 *프리미티브 실행모델*(Agent/TeamCreate/SendMessage/TaskCreate)은 채택한다.

**CYS 계약:** 모든 하네스는 하나의 불변 `graph.json`(JSON-Schema로 검증되는 척추)이다. 메타스킬이 그것을 저작하고, 도구가 그것을 emit·검증한다. 사람이 산문으로 오케스트레이션 로직을 쓰지 않는다. **graph.json을 저작하면 `emit_orchestrator.py`가 그것을 다음으로 emit한다:**

- `.claude/skills/<harness>-orchestrator/SKILL.md` — **프리미티브 오케스트레이터 산문**(Phase 0-3, 노드별 spawn 레시피, 품질게이트, 메모리·진화 섹션). 이 emit된 SKILL이 바로 오케스트레이터다.
- 노드별 `.claude/agents/<agent>.md` — 런타임 바인딩 frontmatter(`model`·`tools` allowlist·`maxTurns`). Agent 프리미티브가 이 frontmatter를 **런타임 강제**한다(Mode-A의 general-purpose 다운그레이드의 역).
- (M3) `skill_authoring.mode='skill'`인 노드마다 `.claude/skills/<harness>-<node_id>/SKILL.md` — 그 노드의 "어떻게"를 담은 도메인 스킬(`emit_domain_skill.py`).
- 전수 상속된 AWF 게놈(hook·L0-L2 게이트·SOT·적대적 리뷰) — `inherit_genome.py`.

| 원본 (team-vs-subagent + 산문 직접) | CYS (graph.json 계약, 프리미티브 기질) |
|---|---|
| 오케스트레이터 = 사람이 쓰는 산문 스킬 | 오케스트레이터 = graph.json이 **emit한** SKILL.md(검증·재현 가능) |
| 팀 모드가 기본 (2명 이상 협업 시 최우선) | 빌드 하네스는 **`team`(기본) 또는 `hybrid`** — A2 floor(`ALL_PRIMITIVES_PRESENT`)상 순수 `agent`는 `TeamCreate`를 emit하지 않아 validate 실패; `agent`는 개념상 sub-spawn 기질일 뿐 빌드 모드 아님. `hybrid`는 현재 team 레시피를 emit(P0-2; Phase별 혼합 emit만 future work) |
| `TeamCreate`/`TaskCreate`/`depends_on`/`SendMessage` (산문 직접) | `graph.nodes[]` + `edges[]`(ordering) → emit이 `Agent()`/`TeamCreate`/`TaskCreate(depends_on)`/`SendMessage`/`TeamDelete` 호출 산문을 생성 |
| 6개 패턴을 하나의 축에 혼재 | 7 topology(데이터흐름) × 4 mechanism(합의이론) — **직교 두 축** |
| "모든 에이전트 opus" | role→tier 정책(gather=haiku, voter=sonnet, judge=opus) — agent frontmatter가 **런타임 강제** |
| 산문 권고 규칙 | `validate_harness.py` 머신체크 + 런타임 `gate_or_block.py` exit-2 인터록 |
| 에러 매트릭스(리더가 감지·재시작) | node별 `retries` + `on_exhaust` + abductive diagnosis |

**왜 프리미티브가 THE 경로인가:** Mode-A(`workflow.js`)는 byte-결정론 replay를 주지만, 그 기질에서는 상속된 AWF 게놈 전체(hook·L0-L2·SOT·적대적 리뷰)가 **휴면**한다(두 실행평면 직교 — 실측 확인). 프리미티브 기질(라이브 호스트 세션)에서만 게놈이 발화하고 커스텀 agent frontmatter가 런타임 강제된다. 따라서 결정론 replay는 *비용*으로 판정됐고, Mode-A는 **제품에서 은퇴**(`WORKFLOW_RETIRED`)해 **공장내부 측정 도구로만** 남았다. 모든 산출 하네스 — graph.json → emit된 오케스트레이터 SKILL이 유일한 실행 경로다. `agent`/`team`/`hybrid`는 그 SKILL이 노드를 어떻게 spawn하느냐의 차이일 뿐, 셋 다 라이브 프리미티브 세션에서 돈다.

> **상속(genome) 맥락:** 생성된 모든 하네스는 `inherit_genome.py`로 AgenticWorkflow 머신(컨텍스트 보존 hook, 4계층 품질 게이트, 보안 hook, 에이전트·스킬 라이브러리, Tier-II 교차실행 메모리 스토어)을 **전수 상속**한다. 즉 자식 하네스는 이미 풍부한 운영 후반부(back-half)를 갖고 태어난다. 이 문서는 그 후반부가 아니라, 도메인 → `graph.json` + agent + schema로 가는 **전반부 설계(front-half)**를 다룬다. 오케스트레이션을 "어떻게 코딩하느냐"가 아니라 "어떤 그래프를 저작하면 그것이 원하는 오케스트레이터로 emit되느냐"의 문제로 본다.

---

## 2. graph.json 저작 템플릿 (채워넣기)

`.harness/graph.json`에 저작한다. **이 메타스킬만이 graph.json의 단일 writer다.** `graph.schema.json`을 준수해야 하며, 위반 시 `validate_harness.py`(GRAPH_SCHEMA)가 생성을 실패시킨다.

```jsonc
{
  "schema_version": "0.1",                       // const "0.1" 고정
  "harness_name": "domain-name",                 // ^[a-z][a-z0-9-]{1,48}[a-z0-9]$ (소문자-하이픈)
  "harness_version": "0.1.0",                    // ^[0-9]+\.[0-9]+\.[0-9]+$ (semver). 첫 생성 0.1.0
  "execution_mode": "team",                      // team(빌드 기본) | hybrid | agent(개념 기질, A2 floor상 빌드엔 부적합) | workflow(은퇴, 미사용)
  "topology": "pipeline",                        // pipeline|dispatch|fan-out-fan-in|producer-reviewer|supervisor|expert-pool|hierarchical
  "budget": {
    "total_tokens": 600000,                      // 하드 ceiling. warrant.py 추정(+여유). approval_required=true면 null 불가
    "approval_required": true                    // true면 실행 전 비용밴드 승인 BLOCK
  },
  "nodes": [
    {
      "id": "gather",                            // ^[a-z][a-z0-9_]{0,30}[a-z0-9]$ (소문자_언더스코어)
      "agent": "researcher",                     // -> .claude/agents/researcher.md (반드시 존재)
      "model": "haiku",                          // haiku|sonnet|opus (REQUIRED, role-tier 정책 준수)
      "decision_mechanism": "single",            // single|majority-vote|debate-with-judge|reflect-then-revise
      "mechanism_params": {},                    // mechanism별 필수 키 (§4 참조)
      "inputs": ["_workspace/00_input/query.md"],          // 읽을 경로 (상대)
      "outputs": ["_workspace/01_gather/findings.json"],   // 쓸 산출물 (상대)
      "write_paths": ["_workspace/01_gather/"],            // 이 노드가 소유하는 쓰기 경로 (minItems 1, 겹침 금지)
      "output_schema": "schemas/findings.json",            // JSON-Schema 파일 (반드시 존재, top-level type 필수)
      "retries": 1,                              // 0..3
      "on_exhaust": "proceed-with-gap",          // proceed-with-gap | force-pass | escalate
      "max_rounds": 1,                           // 1..3 (loop 노드의 라운드 상한)
      "expected_tokens": 8000,                   // (선택) cost_band 입력. 없으면 8000 기본
      "tier_override_reason": "...",             // (선택) pure-retrieval에 opus 쓸 때 필수
      "tools": ["Read", "Glob", "Grep"],         // (선택) least-privilege allowlist → agent frontmatter. 없으면 role-class 기본
      "review": { "agent": "fact-checker" },     // (선택) 이 노드 후 L2 적대적 리뷰 agent를 spawn
      "skill_authoring": { "mode": "inline" }     // (선택) inline(기본) | skill(+reason: reuse|complex|conditional)
    }
    // ... 노드 추가
  ],
  "edges": [
    { "from": "gather", "to": "fetch" }          // ORDERING ONLY. depends_on 그래프가 아님!
  ],
  "metadata": {}                                 // (선택) 자유 객체
}
```

**저작 시 절대 원칙:**

- **`edges`는 순서(ordering)일 뿐 의존성 그래프가 아니다.** 원본의 `TaskCreate(depends_on=[...])`와 혼동하지 말 것. edges는 토폴로지 스케줄링을 위한 위상정렬(toposort) 입력이다. 데이터 의존은 `inputs`/`outputs` 경로로 표현한다. (단 `team` 모드 emit에서는 edges가 `TaskCreate(depends_on=[...])`로도 번역된다 — §11.)
- **spine 필드명은 절대 바꾸지 않는다.** `emit_orchestrator.py`·`validate_harness.py`·사전 cost band(`warrant.py`)가 모두 이 파일에서 파생된다(emit가 stamp하는 무결성 파일은 `graph.lock` — sha256 provenance).
- **모든 경로는 상대.** 절대경로는 `ABSOLUTE_PATHS` 에러. `_workspace/` 기준.
- **`write_paths`는 노드 간 겹치면 안 된다** — `WRITE_PATH_OVERLAP` 에러. `validate_harness.py`가 graph.json에서 write_path→node 소유권 맵을 **메모리에서 직접 도출·검증**한다(별도 lock 파일 불필요).

---

## 3. node 필드 레퍼런스

| 필드 | 타입/제약 | 의미 | 게이트 |
|---|---|---|---|
| `id` | `^[a-z][a-z0-9_]{0,30}[a-z0-9]$` | 노드 고유 id, phase·spawn 레시피 라벨이 됨 | GRAPH_SCHEMA |
| `agent` | `^[a-z][a-z0-9-]{1,48}[a-z0-9]$` | `.claude/agents/<agent>.md`로 해석. emit이 frontmatter 정규화 | AGENT_EXISTS |
| `model` | `haiku\|sonnet\|opus` | 이 노드 호출의 티어. agent frontmatter `model:`과 일치 강제 | TIER_MISSING / TIER_MISMATCH / TIER_OVERSPEND |
| `decision_mechanism` | enum 4 | 합의 메커니즘 (§4) | GRAPH_SCHEMA + 조건부 params |
| `mechanism_params` | object | mechanism별 필수 키 | allOf if/then |
| `inputs` | string[] | 읽을 경로. 보통 직전 노드의 `outputs` | ABSOLUTE_PATHS |
| `outputs` | string[] | 쓸 산출물 파일 | ABSOLUTE_PATHS |
| `write_paths` | string[] (minItems 1) | 이 노드 전용 쓰기 디렉토리/파일 | WRITE_PATH_OVERLAP |
| `output_schema` | string (파일경로) | 노드 반환을 강제할 JSON-Schema. spawn 레시피가 "이 스키마 준수" 지시 | SCHEMA_FILE_EXISTS |
| `retries` | int 0..3 | 노드 실패 시 재시도 횟수 | GRAPH_SCHEMA |
| `on_exhaust` | enum 3 | 재시도 소진 후 행동 (§7) | GRAPH_SCHEMA |
| `max_rounds` | int 1..3 | loop 노드 라운드 상한 | GRAPH_SCHEMA |
| `expected_tokens` | int >0 (선택) | cost_band 입력. 없으면 8000 | warrant.py |
| `tier_override_reason` | string (선택) | pure-retrieval 노드에 opus를 쓰는 이유. 없으면 TIER_OVERSPEND | model-tier-policy |
| `tools` | string[] (선택) | least-privilege allowlist → agent frontmatter `tools:`에 stamp. 없으면 role-class 기본 | (emit) |
| `review` | `{agent}` (선택) | 이 노드 후 critic agent(reviewer/fact-checker)를 L2 게이트 스텝으로 spawn | REVIEW_AGENT_PRESENT |
| `skill_authoring` | `{mode, reason?, shared_by?}` (선택) | M3 하이브리드. `mode=skill`이면 도메인 스킬 저작; `mode=inline`(기본)은 agent 본문 유지 | SKILL_AUTHORING_JUSTIFIED / INLINE_NO_ORPHAN_SKILL |

**`skill_authoring` (M3 하이브리드 — idoforgod의 who=agent / how=skill):**

- `mode: "inline"`(기본) → 노드의 "어떻게"가 agent 본문에 산다. throwaway 스킬을 만들지 않는다.
- `mode: "skill"` → `emit_domain_skill.py`가 `.claude/skills/<harness>-<node_id>/SKILL.md`를 저작한다. `reason`(enum: `reuse`|`complex`|`conditional`)이 머신체크된다 — `reason=reuse`면 `shared_by`가 **2개 이상**의 노드를 가리켜야 한다(`SKILL_AUTHORING_JUSTIFIED`). `mode=inline`인데 스킬 디렉토리가 생기면 `INLINE_NO_ORPHAN_SKILL` 에러.

**`review` (L2 적대적 리뷰 — head-to-head 변별력의 핵심):**

`review.agent`를 단 노드는 emit 시 spawn 레시피에 한 줄이 추가된다 — 본체 실행 후 `Agent(subagent_type="<review.agent>")`를 spawn해 최소 1개 이슈를 내고 `gate_or_block.py .claude/hooks/scripts/validate_review.py --step <N>`로 검증한다(검증기 스크립트는 `.claude/hooks/scripts/`에 있다). `validate_harness.py`(REVIEW_AGENT_PRESENT)는 그 agent의 정의 파일 존재를 강제한다(빈 review가 게이트를 가짜 통과하지 못하게).

**model 티어 — role→tier 정책 (원본의 "전부 opus" 대체):**

`validate_harness.py`의 `_role_class_of`가 노드 id·agent명·mechanism에서 role-class를 추론해 강제한다.

- **haiku** — `gather`/`fetch`/`search`/`retriev`/`collect`/`extract`/`parse`/`format`/`render`/`report`/`qa`/`lint`/`verify`(스캔) (순수 검색·추출·포맷·스캔 = `PURE_RETRIEVAL`). **주의:** id/agent에 `verify` 부분문자열이 들어가면 mechanism 오버라이드가 없는 한 haiku/PURE_RETRIEVAL로 고정된다 — 실질적 검증 노드라면 `decision_mechanism`(예: `reflect-then-revise`)을 달아 그 메커니즘 티어(reviser→sonnet)로 끌어올려라(아래 오버라이드 규칙 참조).
- **sonnet** — `voter`(majority-vote), `debater`(debate-with-judge), `reviser`(reflect-then-revise) (메커니즘이 부여하는 role-class)
- **opus** — `synth`/`aggregate`/`merge`/`judge`/`critic`/`review`/`architect`/`plan`/`design` (합성·심판·비평·설계)

> mechanism이 role-class를 덮어쓴다: `decision_mechanism: majority-vote`면 node.model이 무엇이든 role-class=voter→sonnet 기준으로 검증된다. **`reflect-then-revise`/`debate-with-judge`는 노드 본체 model과 별개로 `mechanism_params.critic`/`judge`에 opus 같은 상위 티어를 지정해 critic·judge 패스만 더 비싸게 돌린다** (deep-research의 verify가 본체 sonnet + critic opus인 이유). 순수 검색 노드를 opus로 두려면 `tier_override_reason`을 반드시 적어라(없으면 `TIER_OVERSPEND`).

---

## 4. 7 topology × 4 decision_mechanism — 직교 좌표계

원본은 6개 패턴(fan-out, expert-pool, hierarchical, pipeline …)을 **한 축에 섞어** 나열했다. CYS는 이를 **두 직교 축**으로 분해한다 — 이것이 원본에 없던 좌표계다.

### 축 1 — topology (데이터 흐름, schema enum 7종)

| topology | 의미 | emit 레시피 (오케스트레이터 SKILL Phase-2) |
|---|---|---|
| **pipeline** | 순차. node→node, 출력이 다음 입력 | toposort 순서로 노드 spawn, 직전 출력을 다음 입력으로 |
| **dispatch** | 병렬 fan-out + 단일 sink | source 노드 병렬 spawn(`run_in_background`) → 단일 sink |
| **fan-out-fan-in** | 병렬 수집 → 합성 | 무의존 `TaskCreate` 병렬 → Lead가 `_workspace/` 수집 → 합성 sub-agent → `TeamDelete` |
| **producer-reviewer** | 생산자↔검토자 bounded loop | producer→reviewer 라운드, `max_rounds` 상한, approved 시 조기 종료 |
| **supervisor** | 동적 작업 할당 | Lead가 초기 `TaskCreate` 배치 → 완료마다 **런타임에 다음 배치 동적 발행** → 소진 시 종합 |
| **expert-pool** | 상황별 전문가 라우팅 | 라우터 노드(haiku/sonnet)가 분류 → **매칭된 전문가만** 조건부 spawn(전체 호출 안 함) |
| **hierarchical** | 2단계 위임 (depth ≤ 2) | L1: sub-coordinator 팀 / L2: 각 coordinator가 sub-agent를 `Agent()`로 spawn |

> 선언한 topology는 오케스트레이터 SKILL에 그 emit 레시피가 **실제로 나타나야** 한다 — `_topology_addendum`이 fan-out-fan-in/supervisor/expert-pool/hierarchical 산문을 Phase-2에 덧붙이고, `validate_harness.py`(`TOPOLOGY_PRIMITIVE_CONSISTENCY`)가 그 일치를 강제한다.

### 축 2 — decision_mechanism (합의 이론, 신규 직교 축, schema enum 4종)

| mechanism | params (필수) | 의미 | fanout (cost 배율) |
|---|---|---|---|
| **single** | `{}` | 1회 호출 | 1 |
| **majority-vote** | `n`(2..5), `quorum`, (`tie_break`) | n명 독립 투표 → 정족수 다수결 | n |
| **debate-with-judge** | `max_rounds`(1..3), `judge`, (`n`) | n명이 max_rounds 토론 → judge 판정 | 2·rounds + 1 |
| **reflect-then-revise** | `max_rounds`(1..3), `critic` | critic→reviser 라운드 (approved 시 조기 종료) | 2·rounds |

이 둘은 **조합 가능(composable)**하다. 같은 topology가 노드마다 다른 mechanism을 쓸 수 있다:

- deep-research(pipeline): gather/fetch=single, **verify=reflect-then-revise(critic=opus)**, synthesize=single
- ticket-triage(dispatch): classify_category·classify_priority=**majority-vote(n=3,quorum=2)** → route=single
- design-decision(producer-reviewer): propose=single → **adjudicate=debate-with-judge(max_rounds=2,judge=opus)**

> `warrant.py`의 `classify()`가 5개 술어에서 topology·mechanism을 **제안**한다(`build-harness` verdict): `has_dependent_or_parallel_stages` && domains≥2 → pipeline; domains≥2(단일스테이지) → dispatch; 그 외(단일도메인) → producer-reviewer. mechanism은 first-match: `!output_objective` → debate-with-judge; staged → reflect-then-revise; noisy → majority-vote; 그 외 → single. `distinct_expertise_domains`가 `MAX_FANOUT=5`를 넘으면 capped + 경고. 이 제안을 graph.json에 확정한다. (supervisor/expert-pool/hierarchical/fan-out-fan-in은 classify가 제안하지 않는 — 저자가 직접 선택하는 — first-class emit 타겟이다.)

---

## 5. emit_orchestrator.py: graph.json → 오케스트레이터 SKILL + agents

```
python3 "$TOOLS_ROOT"/emit_orchestrator.py <harness_dir> [--in-project]
```

`<harness_dir>/.harness/graph.json`을 읽어 다음을 emit한다(+ genome 전수 자동 호출):

- `.claude/skills/<harness>-orchestrator/SKILL.md` — 프리미티브 오케스트레이터.
- 노드별 `.claude/agents/<agent>.md` — 런타임 바인딩 frontmatter.
- `mode=skill` 노드별 `.claude/skills/<harness>-<node_id>/SKILL.md` (M3).
- `README.md`·`harness.md`·`.harness/RUNTIME.json`·`.harness/GENOME.json` + 전수 게놈.

> `emit_orchestrator`는 `execution_mode in {agent, team, hybrid}`만 처리한다(assert). `execution_mode='workflow'`는 은퇴했고 — 이 도구가 처리하지 않는다(공장내부 측정용 `emit_workflow.py`로만 분기).

**emitter는 순수 구조 번역기(structural translator)다.** 토폴로지와 메커니즘만 알고 **도메인은 모른다**. 도메인 행동은 agent `.md` 본문(또는 도메인 스킬)에 살고, 런타임에 `Agent(subagent_type=...)`로 주입된다. emit된 spawn 레시피는 "직전 노드 출력을 입력으로, output_schema대로 JSON 반환"을 지시하는 얇은 산문일 뿐이다.

**emit 매핑 (`emit_orchestrator()` 내부):**

1. **mode-flip guard** — `.harness/GENOME.json`의 `install_mode`(in-project / self-contained)가 이번 요청과 다르면 거부(in-project↔self-contained 재emit이 호스트 파일을 클로버하지 못하게).
2. `toposort(nodes, edges)` — edges로 위상정렬해 노드 실행 순서 확정.
3. `_write_agent_files()` — 각 `node.agent`마다 `.claude/agents/<agent>.md`를 `model`=node.model, `tools`=allowlist, `maxTurns`로 정규화. **기존 손작성 본문·description은 보존**하고 런타임 강제 필드만 정규화. `--in-project`면 `cys_emitted` provenance 마커를 찍고, 마커 없는 동명 호스트 agent는 **emit 거부**(호스트 agent 하이재킹 금지).
4. `emit_domain_skills()` — `skill_authoring.mode='skill'` 노드의 도메인 스킬 저작 (M3).
5. `_orchestrator_skill()` — 오케스트레이터 SKILL.md 렌더(아래).
6. `inherit()` — 전수 게놈 + `RUNTIME.json`. 라이브 세션에서 hook·게이트·SOT가 발화하게 함.
7. `_categorization_merge()` — 게놈 이식 후 도메인 agent를 `categorization.yaml`에 `always_fresh`로 등록(미등록 agent에 hard-block 가드가 RuntimeError 내지 않게).

**오케스트레이터 SKILL 구조 (`_orchestrator_skill`):** frontmatter(`name: <harness>-orchestrator` + **후속 트리거 description**) + 본문 — 에이전트 구성 표, Phase 0-3 워크플로우, 노드별 품질게이트, 메모리 운영(Tier I/II), 진화 루프, 비용 거버넌스, 에러 핸들링, 테스트 시나리오.

- **Phase 0** — `<harness>/` 존재로 분기(초기/재실행/부분/마이그레이션) + `.harness/state.yaml`(SOT, **오케스트레이터 단독 쓰기**) 작성/갱신.
- **Phase 1** — `warrant.py --graph`로 비용밴드 표시 + 승인 대기 + `budget.max_spawns` 설정(`budget_block.py` PreToolUse가 spawn 초과 시 exit-2).
- **Phase 2** — 모드별 노드 실행(아래) + 토폴로지 addendum + 노드별 품질게이트(L0 anti-skip / L1 verification / L1.5 pACS / L2 review — 각각 `gate_or_block.py <validator> --step N`).
- **Phase 3** — 최종 산출물 기록 + git commit(rollback substrate) + (선택) head-to-head.

**mode별 Phase-2 spawn 레시피:**

- **agent**(개념 기질 — 빌드 모드 아님, `_spawn_recipe`) — toposort 순서로 `Agent(subagent_type="<agent>", model="<model>")`를 spawn(병렬 fan-out은 `run_in_background`), 각 노드 후 게이트. mechanism별로 줄이 확장된다: majority-vote=병렬 N spawn + quorum 집계, debate-with-judge=N debater × rounds + judge, reflect-then-revise=critic→reviser 루프(approved 시 종료). `review` 단 노드는 L2 리뷰 줄 추가.
- **team**(`_team_recipe`) — 오케스트레이터(=Team Lead)가 `TeamCreate`/`TaskCreate(depends_on=edges)`/`SendMessage`/`TeamDelete` 실제 호출(§11).
- **hybrid** — 현재 `team`과 동일하게 `_team_recipe`를 emit(P0-2: `emit_orchestrator.py`의 `if mode in ("team","hybrid")` 분기). Phase별 agent/team 기질 *혼합* emit만 future work.

**spawn 카운팅·게이트 인터록:** spawn마다 `spawns_used += 1`(단일쓰기). PostToolUse `spawn_counter` hook이 자동 증분하고 `budget_block`이 천장을 강제한다. `gate_or_block.py`가 advisory validator(exit 0)를 **exit-2 인터록**으로 승격하므로, 게이트 FAIL이 단계를 실제로 멈춘다.

> **오케스트레이터 SKILL을 손으로 고치지 않는다.** 오케스트레이션을 바꾸려면 graph.json을 고치고 재-emit한다(§10). 이것이 graph.json 불변성의 의미다. (단 진화 루프가 `evolve_harness.py`로 라우팅한 수정은 예외적·결정론적으로 추적된다 — Phase-7.)

---

## 6. 데이터 패싱: inputs/outputs · _workspace · output_schema

원본은 데이터 흐름을 `SendMessage`(에이전트 간 메시지) + 파일 산출물 혼합으로 다뤘다. CYS는 **`_workspace` 파일을 1차 채널**로 단순화한다:

**채널 1 — _workspace 파일 (1차 데이터 경로 · 감사 · 재개 · 사람용):** 각 노드의 `inputs`/`outputs`/`write_paths`는 `_workspace/` 아래 명시적 파일 경로다. 노드 N은 자기 출력을 `outputs` 경로에 쓰고, 노드 N+1이 그 경로를 `inputs`로 읽는다. team/hybrid 모드에서 Lead의 핸드오프도 이 디렉토리를 통한다. 관례:

```
_workspace/00_input/<name>.md          ← 최초 입력 (사용자/seed)
_workspace/01_<node>/<artifact>.json   ← 노드 1 산출
_workspace/02_<node>/<artifact>.json   ← 노드 2 산출
…
```

- 노드 N의 `inputs`는 보통 노드 N-1의 `outputs`다 (예: fetch.inputs=`01_gather/findings.json` = gather.outputs).
- `write_paths`는 디렉토리 단위 소유권 — 두 노드가 같은 경로를 가지면 `WRITE_PATH_OVERLAP` 에러. `validate_harness.py`가 write_paths→node 맵을 graph.json에서 메모리로 도출해 검증한다(lock 파일 없음).
- `_workspace/`는 **삭제하지 않고 보존** — 사후 검증·감사 추적·부분 재실행 입력.

**채널 2 — SendMessage (team 모드 한정, 실시간 peer-to-peer):** `execution_mode='team'`에서 팀원이 상충·누락 발견 시 `SendMessage`로 관련 팀원에게 직접 공유(리더 우회). 이것이 team 모드를 정당화하는 유일한 능력이다(§11). agent/hybrid의 순차·병렬 패스는 이 채널을 쓰지 않는다.

**output_schema — 구조화 출력 강제:** 각 노드의 `output_schema` 파일이 spawn 레시피에 "이 스키마 준수" 지시로 박혀, 에이전트 반환을 그 JSON-Schema로 강제한다. 이것이 원본의 "에이전트가 마크다운 보고서를 쓴다"는 느슨함을 대체한다 — 노드는 **검증된 JSON**을 반환하고, 그 JSON이 다음 노드의 입력이 된다. 스키마 규약:

- draft 2020-12, bare-filename `$id`(예: `"$id": "findings.json"`), `additionalProperties: false`, **top-level `type` 필수**(없으면 `SCHEMA_FILE_EXISTS` 에러).
- (권장 컨벤션, 게이트 미강제) reflect-then-revise 노드의 critic 패스 반환을 `schemas/critique.json`(`approved`+`issues[]`)으로 모델링하면 추적성이 좋아진다. `validate_harness.py`는 노드의 `output_schema`(SCHEMA_FILE_EXISTS)만 강제하며 critique.json의 존재를 검사하지 않는다 — 없어도 에러가 아니다.
- 스키마끼리 id로 참조 연결 (claim.id ← critique.issues[].claim_id ← report.citations[].source_id) — 데이터가 파이프를 통과하며 추적 가능.

---

## 7. 에러 핸들링: on_exhaust + retries (원본 에러 매트릭스 대체)

원본은 "리더가 감지 → SendMessage 상태확인 → 재시작/재할당"이라는 **산문 절차**로 에러를 다뤘다. CYS는 이를 **노드별 두 선언 필드**로 환원한다 — 오케스트레이터 SKILL과 게놈 hook이 강제하므로 "리더가 깜빡함"이 불가능하다.

| 필드 | 값 | 의미 |
|---|---|---|
| `retries` | 0..3 | 노드 실패 시 동일 노드 재시도 횟수. cost_band은 `(retries+1)` 배율로 계산 |
| `on_exhaust` | `proceed-with-gap` | 재시도 소진 후 **결손을 명시하고 다음 노드로 진행**. 부분 결과 허용 |
| | `force-pass` | 소진 후 **현 상태 그대로 통과**(검증 실패해도). 비핵심 노드 |
| | `escalate` | 소진 후 **중단·사용자에게 에스컬레이션**. 핵심 노드(최종 synthesize 등) |

**원본 에러 시나리오 → CYS 매핑:**

| 원본 상황 | 원본 전략 | CYS 등가 |
|---|---|---|
| 팀원 1명 실패 | 리더 감지→재시작 | 해당 노드 `retries` 소진 |
| 팀원 과반 실패 | 사용자에게 진행 확인 | 핵심 노드 `on_exhaust: escalate` |
| 타임아웃 | 부분 결과 사용 | `on_exhaust: proceed-with-gap` |
| 팀원 간 데이터 충돌 | 출처 병기 | mechanism으로 흡수: majority-vote의 tie_break, debate의 judge |
| 예산 초과 | (원본 없음) | `budget_block.py` spawn ceiling exit-2 → 그룹 중단 |

**mechanism 자체가 에러 흡수기다:** majority-vote의 `quorum`/`tie_break`는 소수 에이전트 실패/이견을 정족수로 흡수한다. reflect-then-revise는 critic이 `approved=false`인 한 max_rounds까지 자가 교정한다(approved 시 조기 break). debate-with-judge는 상충 입장을 judge가 단일 판정으로 수렴한다. **노드 수준 retries/on_exhaust는 "메커니즘으로도 못 살린 실패"의 마지막 그물이다.**

게이트 FAIL 시: 오케스트레이터는 `diagnose_context.py`(abductive diagnosis) → `validate_diagnosis.py` → `validate_retry_budget.py` 예산 내 재시도. 예산 초과 시 사용자 에스컬레이션.

deep-research 예: gather/fetch=`proceed-with-gap`(웹 결손 허용), verify=`proceed-with-gap`, **synthesize=`escalate`**(최종 산출 실패는 부분 진행 불가).

---

## 8. budget / approval

```jsonc
"budget": { "total_tokens": 600000, "approval_required": true }
```

- **`total_tokens`은 하드 ceiling이다.** `warrant.py`의 `cost_band()`가 추정 floor를 제안하고, graph.json 단일 writer가 retry·variance 여유로 floor를 두 배까지 잡을 수 있다. 런타임에서는 `budget_block.py`(PreToolUse)가 **spawn-count 천장**(`budget.max_spawns` = warrant fanout 합)을 exit-2로 강제한다 — wall-clock이 아니라 spawn 수 기반.
- **`approval_required: true`** → 실행 전 `warrant.py --graph`로 `{total_tokens, weighted_units, band(LOW/MEDIUM/HIGH), usd_estimate}` 밴드를 표시하고, **명시적 'approve' 전까지 첫 spawn을 BLOCK**한다. 승인은 `state.yaml` audit_log에 기록.
- schema 조건부: `approval_required: true`면 `total_tokens`는 null 불가(반드시 정수 ≥1).

**cost_band 계산 (`warrant.py`, 실측):**

- `est_tokens = expected_tokens × fanout × (retries + 1)` (`expected_tokens` 기본 8000).
- `fanout`: single=1, majority-vote=`n`, debate-with-judge=`2·rounds + 1`, reflect-then-revise=`2·rounds`.
- `weighted_units = est_tokens × tier_weight`, `tier_weight = {haiku:1, sonnet:3, opus:5}` (2026 블렌디드 가격 추종).
- **team/hybrid 보정(CD-3)**: 팀의 `SendMessage`/자체조율 트래픽은 노드별 single-pass 공식이 못 잡으므로, 멤버당 `TEAM_COORD_TOKENS`(4000, sonnet weight) 일차 보정항을 더한다 — 승인 밴드가 팀 기질에서 체계적 과소계상되지 않게.
- `distinct_expertise_domains > MAX_FANOUT(5)`인 도메인은 묶거나 2단계 합성하라는 경고 + n_agents capped.

---

## 9. RUNTIME.json 라우팅: 단일 실행 런타임 = 오케스트레이터 SKILL

게놈 전수로 하네스는 디스크에 여러 능력을 갖지만, **실행 런타임은 정확히 하나** — 오케스트레이터 SKILL이다(100% Claude Code 프리미티브). `.harness/RUNTIME.json`이 이를 선언한다 (없으면 `RUNTIME_DECLARED` 에러).

| runtime | 역할 | entrypoint | graph.json 연결 |
|---|---|---|---|
| **`<harness>-orchestrator`** | **canonical (유일 실행 런타임)** | `.claude/skills/<harness>-orchestrator/SKILL.md` | **이 하네스 graph.json의 계약** (via emit_orchestrator) |

- `canonical_runtime`은 반드시 `"<harness>-orchestrator"`. `validate_harness.py`(RUNTIME_DECLARED)가 `execution_mode`로 dual-accept한다: `agent|team|hybrid` → `<harness>-orchestrator`; `workflow`(은퇴) → `cys-mode-a`. 산출 하네스는 항상 전자다.
- **은퇴 런타임을 광고하지 않는다(`RUNTIME_MANIFEST_CLEAN`):** Mode-A `workflow.js`(컴파일 .js 런타임)와 상속된 `prompt-runner` 서브프로세스는 **runtime으로 선언되지 않는다**. prompt-runner는 vendored-but-inert(실행에 배선 안 됨). 즉 "같은 작업을 두 런타임으로 돌리는" 모호성 자체가 없다.

**실행:** 하네스 디렉토리에서 `claude` 세션을 열고 `<harness>-orchestrator` 스킬을 트리거한다. **그 세션의 `settings.json` hook이 발화한다**(공장의 것이 아니라). `--in-project` 설치라면 호스트 프로젝트의 `claude` 세션 안에서 같은 스킬을 트리거한다(이 하네스는 호스트의 한 능력이지 호스트 루트의 자체 런타임이 아니다).

---

## 10. 후속 작업 지원 (재실행 · 부분 재실행 · 마이그레이션)

원본의 Phase 0(컨텍스트 확인)을 CYS의 불변 구조로 재해석. **후속 키워드가 없으면 하네스는 첫 실행 후 죽은 코드가 된다** — 오케스트레이터 SKILL의 frontmatter description에 후속 표현(다시 실행/재실행/업데이트/수정/보완/일부만 다시/이전 결과 개선)이 emit된다(원본 원칙 유지, `_orchestrator_skill`이 자동 삽입).

`<harness>/` 및 `_workspace/` 존재 여부로 분기(Phase 0):

1. **`_workspace/` 미존재** → 초기 실행. `_workspace/00_input/`에 입력 저장 후 오케스트레이터 실행.
2. **`_workspace/` 존재 + 재실행 요청** → `state.yaml` + `.claude/context-snapshots/latest.md`로 맥락 복원 후 진행.
3. **`_workspace/` 존재 + 부분 수정 요청** → 해당 노드의 입력(`_workspace/0X_…`)을 갱신하고 **그 노드부터** 재spawn(이전 노드 출력은 `_workspace/`에서 재사용). 게놈 게이트가 변경 노드를 재검증.
4. **`_workspace/` 존재 + 새 입력** → 기존 `_workspace/`를 `_workspace_{YYYYMMDD_HHMMSS}/`로 이동(보존) 후 새 실행.
5. **마이그레이션(import)** → 외부 산출물을 `_workspace/00_input/`로 적재 후 (1)처럼.

> 그래프 자체를 바꾸려면(노드 추가/topology 변경) graph.json을 수정 → `validate_harness.py` 통과 → `emit_orchestrator.py` 재-emit → `harness_version` bump. 오케스트레이터 SKILL·agent 파일을 손으로 고치지 않는다(emit이 손작성 본문은 보존하되 런타임 필드는 재정규화).

---

## 11. team / hybrid — 언제, 왜, 어떻게 emit되나

`execution_mode`는 셋 다 프리미티브 기질에서 돈다 — 차이는 오케스트레이터가 노드를 어떻게 spawn하느냐다.

**agent (개념 기질 — 빌드 모드 아님):** 오케스트레이터가 toposort 순서로 `Agent(subagent_type=...)`를 순차/병렬 spawn하고 `_workspace/` 파일로 핸드오프한다. 실시간 inter-agent 통신이 없다. **단, 순수 `agent`는 `TeamCreate`를 emit하지 않아 A2 `ALL_PRIMITIVES_PRESENT`를 validate에서 실패하므로, 빌드되는 하네스는 `team`/`hybrid`로 emit한다**(team 미사용 환경에선 그 안에서 sub-agent로 graceful-degrade).

**team — 실제 팀 프리미티브 emit (`_team_recipe`, `TEAM_EMIT_PRESENT`):** 오케스트레이터(=Team Lead)가 다음을 실제 호출한다(agent 모드의 `Agent()` fan과 더 이상 byte-동일 아님):

1. `TeamCreate(team_name="<harness>-team", members=[...])` — 멤버 = 각 노드 agent(frontmatter model·tools 런타임 강제).
2. `TaskCreate(subject="<node>", owner="@<agent>", depends_on=[...])` — 의존성은 graph `edges`(toposort 보존). **이것이 edges가 team 모드에서 `depends_on`으로 번역되는 유일한 경로다.**
3. `SendMessage` — 팀원 간 직접 통신(상충·누락을 peer-to-peer 공유). 적대적 검증 노드는 격리 — 팀원이 아니라 별도 `Agent(subagent_type="reviewer")`로 spawn(L2).
4. Team Lead L2 — `TaskUpdate(status=completed)` 시 Lead가 `_workspace/` 산출물을 읽어 품질게이트(L0-L2) 통과 + SOT 기록(단일쓰기). PostToolUse `qa_gate_runner`가 같은 게이트를 host 인터록으로 재확인.
5. `TeamDelete` — 모든 task 완료 후 정리(세션당 한 팀; 다음 팀 전 반드시 TeamDelete).

> **Graceful degrade (A2-iii, `TEAM_GRACEFUL_DEGRADE`):** `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` 플래그가 없으면 각 task를 `Agent(subagent_type=...)` fan + `_workspace/` 핸드오프로 강등한다 — 팀 없이도 동일 그래프가 실행된다.

**team을 쓰는 유일한 정당화:** 에이전트 간 **실시간 inter-agent 통신이 본질적으로 필요**할 때 — 즉 에이전트들이 서로의 중간 상태를 실시간 협상해야 하고 파일/순차 패싱으로 표현 불가능할 때. 그 외엔 개념상 agent로 충분하지만 **빌드되는 하네스는 A2 floor상 team/hybrid로 emit**한다(순수 agent는 `TeamCreate` 미emit → `ALL_PRIMITIVES_PRESENT` 실패; 팀 미사용 시 그 안에서 sub-agent로 graceful-degrade). team은 결정론적으로 스케줄될 수 없으므로(플랫폼 한계), 실시간 협상 가치가 명백할 때만 *실제* 팀 통신을 쓴다.

> debate-with-judge mechanism이 "에이전트 간 의견 충돌·반박"의 90%를 **결정론적으로** 커버한다(transcript를 파일로 누적, judge가 수렴). 실시간 협상이 정말 필요한지 묻기 전에, debate-with-judge로 충분하지 않은지 먼저 확인하라.

**hybrid:** 현재는 `team`과 동일하게 `_team_recipe`를 emit한다(P0-2 — `emit_orchestrator.py`의 `if mode in ("team","hybrid")` 분기). 단계별 agent/team 기질 *혼합* emit(예: 수집=agent fan, 협상만=team)은 future work다. cost_band은 team과 같은 `TEAM_COORD_TOKENS` 보정을 받는다.

---

## 12. 작성 원칙 (강제 게이트로 환원)

원본의 7개 산문 권고를 CYS의 머신체크로 환원. **권고가 아니라 `validate_harness.py`가 error를 내면 생성이 중단된다.**

| 원본 권고 (산문) | CYS 강제 (게이트) |
|---|---|
| "실행 모드를 먼저 명시" | `execution_mode` enum 필드 (GRAPH_SCHEMA) |
| "팀/서브 도구 사용법 구체적으로" | graph.json이 단일 진실; emit이 spawn 레시피 생성 |
| "파일 경로는 상대 금지(절대 사용)" → CYS는 역(상대 강제) | ABSOLUTE_PATHS 게이트 (절대경로=error) |
| "Phase 간 의존성 명시" | `edges` + toposort + GRAPH_CYCLE 게이트 |
| "에러 핸들링 현실적으로" | `retries` + `on_exhaust` 필수 필드 |
| "테스트 시나리오 필수" | `lift_gate.py`(blind grader, LIFT_REFUSED) + h2h_suite (공장내부 측정) |
| "모든 것이 성공한다고 가정 안 함" | `budget_block.py` spawn ceiling + on_exhaust=escalate |
| (원본 "전부 opus") | model-tier-policy: role→tier, TIER_OVERSPEND 게이트 |
| (원본 "리더 산문 조율") | emit된 오케스트레이터 SKILL, 손수정 금지 |

**저작 절차 요약 (graph.json 중심):**

```
1. warrant.py --predicates  → build-harness(topology, mechanism, n_agents) 판정
   → 검증: verdict가 build-harness인가?
2. graph.json 저작 (단일 writer, schema 준수)
   → 검증: 모든 node에 model + on_exhaust + write_paths(겹침 없음)?
3. agent .md + schema 저작 (model + model_rationale + least-privilege tools)
   → 검증: 모든 node.agent 파일 + output_schema 파일 존재(top-level type)?
4. emit_orchestrator.py  → 오케스트레이터 SKILL + agents + 도메인 스킬 + genome 전수
   → 검증: emit 성공 + GENOME VERIFY ok?
5. validate_harness.py  → 머신체크 세트 (error 0)
   → 검증: status == pass?
6. warrant.py --graph  → 비용밴드 → 승인 → claude 세션에서 오케스트레이터 트리거
   → 검증: approval 받음 + budget.max_spawns 천장 내 완주?
```

각 단계의 변경된 모든 줄은 graph.json으로 직접 추적 가능해야 한다 — 오케스트레이터 SKILL·agent 파일은 emit 산물이지 손으로 쓰는 코드가 아니기 때문이다. **오케스트레이터를 "코딩"하지 말고, 그것이 emit되는 그래프를 저작하라.**
