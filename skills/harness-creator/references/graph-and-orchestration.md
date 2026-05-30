> ⚠️ **구현 현황은 [`IMPLEMENTATION-STATUS.md`](IMPLEMENTATION-STATUS.md)가 우선한다.** 이 문서의 설계 서술 중 dispatch(dynamic)/supervisor·expert-pool·hierarchical 등은 M1-deferred(미구현)이며, `.claude/commands` 비우기 규칙은 폐기됐다.

# graph.json과 오케스트레이션

> ⚠️ **PIVOT (2026-05-29)**: 오케스트레이터의 canonical 산출물은 이제 **emit된 오케스트레이터 SKILL.md**(`emit_orchestrator.py`, Claude Code 프리미티브 Agent/TeamCreate 구동)다. `workflow.js`(`emit_workflow.py`)는 `execution_mode='workflow'`(byte-결정론 replay) **선택지**로 잔존한다. 이 문서의 "오케스트레이터 = workflow.js" 서술은 그 선택지에 한정해 읽고, 기본은 프리미티브 SKILL로 치환한다. 구현 현황은 `IMPLEMENTATION-STATUS.md` 우선, 근거는 `design/pivot-to-claude-primitives-strategy.md`.

> 출처: 원본 `orchestrator-template.md`을 CYS 패러다임으로 적응. 원본의 "오케스트레이터 = 프롬프트로 작성하는 상위 스킬(팀 기본)" 모델을 "오케스트레이터 = `graph.json`이 컴파일된 `workflow.js`(Mode A 결정론 런타임 기본)"로 전환했다.

---

## 목차

1. [핵심 전환: 오케스트레이터는 emit된 workflow.js다](#1-핵심-전환-오케스트레이터는-emit된-workflowjs다)
2. [graph.json 저작 템플릿 (채워넣기)](#2-graphjson-저작-템플릿-채워넣기)
3. [node 필드 레퍼런스](#3-node-필드-레퍼런스)
4. [3 topology × 4 decision_mechanism — 직교 좌표계](#4-3-topology--4-decision_mechanism--직교-좌표계)
5. [emit_workflow.py: graph.json → workflow.js 컴파일](#5-emit_workflowpy-graphjson--workflowjs-컴파일)
6. [데이터 패싱: inputs/outputs · _workspace · output_schema](#6-데이터-패싱-inputsoutputs--_workspace--output_schema)
7. [에러 핸들링: on_exhaust + retries (원본 에러 매트릭스 대체)](#7-에러-핸들링-on_exhaust--retries-원본-에러-매트릭스-대체)
8. [budget / approval](#8-budget--approval)
9. [RUNTIME.json 라우팅: canonical workflow.js vs 상속 prompt-runner](#9-runtimejson-라우팅-canonical-workflowjs-vs-상속-prompt-runner)
10. [후속 작업 지원 (resume · 부분 재실행 · 재실행)](#10-후속-작업-지원-resume--부분-재실행--재실행)
11. [Mode B (team) — 언제, 왜 예외인가](#11-mode-b-team--언제-왜-예외인가)
12. [작성 원칙 (강제 게이트로 환원)](#12-작성-원칙-강제-게이트로-환원)

---

## 1. 핵심 전환: graph.json 계약 → emit된 오케스트레이터 SKILL

원본은 오케스트레이터를 **프롬프트로 직접 쓰는 상위 스킬**로 보았다 — Phase별 산문, `TeamCreate`/`SendMessage`/`TaskCreate` 호출, "팀이 기본". CYS는 그 *산문 직접저작*을 버리되, idoforgod의 *프리미티브 실행모델*(Agent/TeamCreate/SendMessage)은 채택한다.

**CYS 계약:** 모든 하네스는 하나의 불변 `graph.json`(JSON-Schema로 검증되는 척추)이다. 메타스킬이 그것을 저작하고, 도구가 그것을 emit·검증한다. 사람이 산문으로 오케스트레이션 로직을 쓰지 않는다. **graph.json을 저작하면, `emit_orchestrator.py`가 그것을 `.claude/skills/<name>-orchestrator/SKILL.md`(프리미티브 오케스트레이터) + 노드별 `.claude/agents/*.md`(런타임 바인딩 frontmatter)로 emit한다. 그 emit된 SKILL이 바로 오케스트레이터다.** (`execution_mode='workflow'`인 좁은 경우에만 `emit_workflow.py`가 `.harness/workflow.js`로 컴파일.)

| 원본 (team-vs-subagent + 산문 직접) | CYS (graph.json 계약, 프리미티브 기질) |
|---|---|
| 오케스트레이터 = 사람이 쓰는 산문 스킬 | 오케스트레이터 = graph.json이 emit한 SKILL.md(검증·재현 가능) |
| 팀 모드가 기본 (2명 이상 협업 시 최우선) | `agent` 모드 기본(순차/병렬 sub-spawn); `team`은 실시간 comms 필수 시(P5 입증 후) |
| `TeamCreate`/`TaskCreate`/`depends_on`/`SendMessage` (산문) | `graph.nodes[]` + `edges[]`(ordering) → emit이 Agent/TeamCreate 호출로 prose 생성 |
| 6개 패턴을 하나의 축에 혼재 | 3 topology(데이터흐름) × 4 mechanism(합의이론) — **직교 두 축** |
| "모든 에이전트 opus" | role→tier 정책(gather=haiku, voter=sonnet, judge=opus) — Agent가 **런타임 강제** |
| 산문 권고 규칙 | `validate_harness.py` 머신체크 + 런타임 `gate_or_block.py` exit-2 인터록 |
| 에러 매트릭스(리더가 감지·재시작) | node별 `retries` + `on_exhaust` + abductive diagnosis |

**왜 프리미티브가 기본인가:** Mode-A(`workflow.js`)는 byte-결정론·재개를 주지만, 그 기질에서는 상속된 AWF 게놈 전체(hook·L0-L2·SOT·적대적 리뷰)가 **휴면**한다(두 실행평면 직교 — 실측 확인). 프리미티브 기질(라이브 호스트 세션)에서만 게놈이 발화하고 커스텀 agent가 resolve된다. 따라서 CYS는 결정론 replay를 *비용*으로 인식하고, 그 비용을 지불할 가치(byte-exact 재현)가 명백한 좁은 경우만 `workflow`로 빠진다. 그 외 거의 전부 — graph.json → emit된 오케스트레이터 SKILL이 THE 경로다. 단 `team`은 라이브 입증(P5) 전까지 `agent` 아래의 opt-in이다.

> **상속(genome) 맥락:** 생성된 모든 하네스는 `inherit_genome.py`로 AgenticWorkflow 전체 머신(228 파일: 컨텍스트 보존 hook, 4계층 품질 게이트, 보안 hook, 에이전트·스킬·프롬프트 라이브러리)을 **전수 상속**한다. 즉 자식 하네스는 이미 풍부한 운영 후반부(back-half)를 갖고 태어난다. 이 문서는 그 후반부가 아니라, 도메인 → `graph.json` + agent + schema로 가는 **전반부 설계(front-half)**를 다룬다. 오케스트레이션을 "어떻게 코딩하느냐"가 아니라 "어떤 그래프를 저작하면 그것이 원하는 오케스트레이터로 컴파일되느냐"의 문제로 본다.

---

## 2. graph.json 저작 템플릿 (채워넣기)

`.harness/graph.json`에 저작한다. **이 메타스킬만이 graph.json의 단일 writer다.** `graph.schema.json`을 준수해야 하며, 위반 시 `validate_harness.py`가 생성을 실패시킨다.

```jsonc
{
  "schema_version": "0.1",                       // const "0.1" 고정
  "harness_name": "{domain}-name",               // ^[a-z][a-z0-9-]+[a-z0-9]$ (소문자-하이픈)
  "harness_version": "0.1.0",                    // semver, 첫 생성은 0.1.0
  "execution_mode": "workflow",                  // "workflow"=Mode A(기본) | "team"=Mode B(예외)
  "topology": "pipeline",                        // pipeline | dispatch | producer-reviewer
  "budget": {
    "total_tokens": 600000,                      // 하드 ceiling. warrant.py 추정(+여유)
    "approval_required": true                    // true면 실행 전 비용밴드 승인 BLOCK
  },
  "nodes": [
    {
      "id": "gather",                            // ^[a-z][a-z0-9_]+[a-z0-9]$ (소문자_언더스코어)
      "agent": "researcher",                     // -> .claude/agents/researcher.md (반드시 존재)
      "model": "haiku",                          // haiku|sonnet|opus (REQUIRED, role-tier 정책 준수)
      "decision_mechanism": "single",            // single|majority-vote|debate-with-judge|reflect-then-revise
      "mechanism_params": {},                    // mechanism별 필수 키 (§4 참조)
      "inputs": ["_workspace/00_input/query.md"],          // 읽을 경로 (상대)
      "outputs": ["_workspace/01_gather/findings.json"],   // 쓸 산출물 (상대)
      "write_paths": ["_workspace/01_gather/"],            // 이 노드가 소유하는 쓰기 경로 (겹침 금지)
      "output_schema": "schemas/findings.json",            // JSON-Schema 파일 (반드시 존재, type 필수)
      "retries": 1,                              // 0..3
      "on_exhaust": "proceed-with-gap",          // proceed-with-gap | force-pass | escalate
      "max_rounds": 1,                           // 1..3 (loop 노드의 라운드 상한)
      "expected_tokens": 8000,                   // (선택) cost_band 추정 입력. 없으면 8000 기본
      "tier_override_reason": "..."              // (선택) pure-retrieval에 opus 쓸 때 필수
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

- **`edges`는 순서(ordering)일 뿐 의존성 그래프가 아니다.** 원본의 `TaskCreate(depends_on=[...])`와 혼동하지 말 것. edges는 pipeline/dispatch/loop 스케줄링을 위한 위상정렬(toposort) 입력이다. 데이터 의존은 `inputs`/`outputs` 경로로 표현한다.
- **spine 필드명은 절대 바꾸지 않는다.** `workflow.js`·`harness.lock`·`validate_harness.py`·사전 cost band가 모두 이 파일에서 파생된다.
- **모든 경로는 상대.** 절대경로는 `ABSOLUTE_PATHS` 에러. `_workspace/` 기준.
- **`write_paths`는 노드 간 겹치면 안 된다** — `WRITE_PATH_OVERLAP` 에러. `harness.lock`이 이 소유권 맵을 정적으로 검증한다.

---

## 3. node 필드 레퍼런스

| 필드 | 타입/제약 | 의미 | 게이트 |
|---|---|---|---|
| `id` | `^[a-z][a-z0-9_]*[a-z0-9]$` | 노드 고유 id, `node_<id>` 함수명·phase명이 됨 | GRAPH_SCHEMA |
| `agent` | `^[a-z][a-z0-9-]*[a-z0-9]$` | `.claude/agents/<agent>.md`로 해석 | AGENT_EXISTS |
| `model` | `haiku\|sonnet\|opus` | 이 노드 호출의 티어. agent frontmatter `model:`과 일치해야 함 | TIER_MISSING / TIER_MISMATCH / TIER_OVERSPEND |
| `decision_mechanism` | enum 4 | 합의 메커니즘 (§4) | GRAPH_SCHEMA + 조건부 params |
| `mechanism_params` | object | mechanism별 필수 키 | allOf if/then |
| `inputs` | string[] | 읽을 경로. 보통 직전 노드의 `outputs` | ABSOLUTE_PATHS |
| `outputs` | string[] | 쓸 산출물 파일 | ABSOLUTE_PATHS |
| `write_paths` | string[] (minItems 1) | 이 노드 전용 쓰기 디렉토리/파일 | WRITE_PATH_OVERLAP |
| `output_schema` | string (파일경로) | 노드 반환을 강제할 JSON-Schema. `agent({schema})`에 inline됨 | SCHEMA_FILE_EXISTS |
| `retries` | int 0..3 | 노드 실패 시 재시도 횟수 | GRAPH_SCHEMA |
| `on_exhaust` | enum 3 | 재시도 소진 후 행동 (§7) | GRAPH_SCHEMA |
| `max_rounds` | int 1..3 | loop 노드 라운드 상한 | GRAPH_SCHEMA |
| `expected_tokens` | int >0 (선택) | cost_band 입력 | warrant.py |
| `tier_override_reason` | string (선택) | pure-retrieval 노드에 opus를 쓰는 이유. 없으면 TIER_OVERSPEND=error | model-tier-policy |

**model 티어 — role→tier 정책 (원본의 "전부 opus" 대체):**

`model-tier-policy.js`와 `validate_harness.py`가 노드 id·agent명·mechanism에서 role-class를 추론해 강제한다.

- **haiku** — `gather`/`fetch`/`search`/`extract`/`parse`/`format`/`report`/`qa`/`lint`/`verify`(scan) (순수 검색·추출·포맷·스캔)
- **sonnet** — `voter`(majority-vote), `debater`(debate-with-judge), `reviser`(reflect-then-revise) (메커니즘이 부여하는 role-class)
- **opus** — `synthesis`/`aggregate`/`judge`/`critic`/`architect`/`plan`/`design` (합성·심판·비평·설계)

> mechanism이 role-class를 덮어쓴다: `decision_mechanism: majority-vote`면 node.model이 무엇이든 role-class=voter→sonnet 기준으로 검증된다. **`reflect-then-revise`/`debate-with-judge`는 노드 본체 model과 별개로 `mechanism_params.critic`/`judge`에 opus 같은 상위 티어를 지정해 critic·judge 패스만 더 비싸게 돌린다** (deep-research의 verify가 본체 sonnet + critic opus인 이유). 순수 검색 노드를 opus로 두려면 `tier_override_reason`을 반드시 적어라.

---

## 4. 3 topology × 4 decision_mechanism — 직교 좌표계

원본은 6개 패턴(fan-out, expert-pool, hierarchical, pipeline …)을 **한 축에 섞어** 나열했다. CYS는 이를 **두 직교 축**으로 분해한다 — 이것이 원본에 없던 좌표계다.

### 축 1 — topology (데이터 흐름)

| topology | 의미 | emit 결과 | 원본 매핑 |
|---|---|---|---|
| **pipeline** | 순차. node→node, 출력이 다음 입력 | `pipeline([seed], stage…)` | 원본의 pipeline |
| **dispatch** | 병렬 fan-out + 단일 sink. static=고정 팬아웃 / dynamic=claim·supervisor | `parallel(thunks)` barrier + 단일 sink reduce | 원본 fan-out → dispatch(static); supervisor → dispatch(dynamic) |
| **producer-reviewer** | 생산자↔검토자 bounded loop | `while(producer→reviewer)` 라운드 상한 | (신규; expert-pool·hierarchical은 M1로 deferred) |

### 축 2 — decision_mechanism (합의 이론, 신규 직교 축)

| mechanism | params (필수) | 의미 | fanout (cost) |
|---|---|---|---|
| **single** | `{}` | 1회 호출 | 1 |
| **majority-vote** | `n`(2..5), `quorum`, (`tie_break`) | n명 독립 투표 → 정족수 다수결 | n |
| **debate-with-judge** | `max_rounds`(1..3), `judge`, (`n`) | n명이 max_rounds 토론 → judge 판정 | 2·rounds + 1 |
| **reflect-then-revise** | `max_rounds`(1..3), `critic` | critic→reviser 라운드 (approved 시 조기 종료) | 2·rounds |

이 둘은 **조합 가능(composable)**하다. 같은 topology가 노드마다 다른 mechanism을 쓸 수 있다:

- deep-research(pipeline): gather/fetch=single, **verify=reflect-then-revise(critic=opus)**, synthesize=single
- ticket-triage(dispatch): classify_category·classify_priority=**majority-vote(n=3,quorum=2)** → route=single
- design-decision(producer-reviewer): propose=single → **adjudicate=debate-with-judge(max_rounds=2,judge=opus)**

> warrant.py의 `classify()`가 5개 술어에서 topology·mechanism을 **제안**한다: ordered+멀티도메인→pipeline; 멀티도메인 단일스테이지→dispatch; 단일도메인 정제반복→producer-reviewer. mechanism은 first-match: 주관적→debate-with-judge; staged→reflect-then-revise; noisy→majority-vote; 그 외→single. 이 제안을 graph.json에 확정한다.

---

## 5. emit_workflow.py: graph.json → workflow.js 컴파일

`python3 "$TOOLS_ROOT"/emit_workflow.py <harness_dir>` → `.harness/workflow.js` 생성 (+ genome 전수 자동 호출).

**emitter는 순수 구조 번역기(structural translator)다.** 토폴로지와 메커니즘만 알고 **도메인은 모른다**. 도메인 행동은 agent `.md` 파일에 살고, 런타임에 `agent({agentType})`로 주입된다. emit된 프롬프트는 직전 노드 출력을 넘기고 "스키마대로 반환하라"고 지시하는 얇은 래퍼일 뿐이다.

**컴파일 매핑 (`emit()` 내부):**

1. `_check_refs()` — 모든 `node.agent`→agent 파일, 모든 `output_schema`→파일 존재 확인 (없으면 FileNotFoundError로 emit 중단).
2. `toposort(nodes, edges)` — edges로 위상정렬해 노드 실행 순서 확정.
3. `_inline_schemas()` — 각 `output_schema` 파일을 읽어 JS literal `const S = {...}`로 inline. `$schema`/`$id` 키는 제거(Workflow 런타임 validator가 `$schema`를 ref로 오인해 거부 — 경험적 사실). reflect-then-revise 노드는 `schemas/critique.json`을 `<id>_critique`로 추가 inline.
4. `_helpers()` — `ensure(min)`(예산 가드), `reduceMajority(votes, quorum, tieBreak)` emit.
5. `_prompts()` — 도메인 무관 프롬프트 빌더 `P` emit (single/vote/debater+judge/critic+reviser별).
6. `_node_fn()` — 노드마다 `async function node_<id>(input)`을 mechanism에 맞게 emit.
7. `_topology()` — 토폴로지에 맞는 최종 실행부 emit.

**mechanism별 emit되는 node 함수:**

```js
// single
async function node_gather(input) {
  phase("gather"); log("gather <- " + JSON.stringify(NIN.gather));
  return await agent(P.gather(input), { label:"gather", phase:"gather", model:"haiku", agentType:"researcher", schema: S.gather_schema });
}
// majority-vote: N개 parallel ballot → reduceMajority(quorum, tieBreak)
// debate-with-judge: max_rounds × (n명 parallel 토론) → judge 1회
// reflect-then-revise: for r<max_rounds { critic(opus) → approved면 break → reviser(sonnet) }
```

**topology별 emit되는 실행부:**

```js
// pipeline — 스테이지 간 barrier 없이 순차
const [out] = await pipeline([seed], (prev)=>node_gather(prev), (prev)=>node_fetch(prev), …);

// dispatch — source 노드들 parallel fan-out → 단일 sink reduce
const fanned = (await parallel([ ()=>node_classify_category(args), ()=>node_classify_priority(args) ])).filter(Boolean);
const out = await node_route(fanned);          // 단일 sink 가정 (M0); multi-sink reduce는 M1

// producer-reviewer — bounded loop
let draft = await node_propose(seed);
for (let r=0; r<rounds; r++) { const review = await node_adjudicate(draft); if (!review || review.approved) break; draft = await node_propose(draft); }
```

**emit 불변식 (emitter가 self-assert):**

- 출력은 `// AUTO-EMITTED …`로 시작 + `export const meta = {` 포함 (Workflow 도구 포맷: top-level-statement, `export default` 래퍼 없음).
- **`Date.now(` / `Math.random(` / `new Date(` 금지** — wall-clock·RNG 없음 = 재개 안전(resume-safe). meta는 순수 literal.
- `agent`/`parallel`/`pipeline`/`phase`/`log`/`budget`/`args`는 **ambient** — 런타임이 주입, import 안 함.

> **workflow.js는 수정 금지.** 헤더가 "DO NOT EDIT BY HAND"라 명시한다. 오케스트레이션을 바꾸려면 graph.json을 고치고 재-emit한다. resume는 **첫 변경 노드의 agent() 호출부터** 재실행한다.

---

## 6. 데이터 패싱: inputs/outputs · _workspace · output_schema

원본은 데이터 흐름을 `SendMessage`(에이전트 간 메시지) + 파일 산출물 혼합으로 다뤘다. CYS는 **두 채널**로 단순화한다:

**채널 1 — 런타임 값 패싱 (workflow.js 내부):** `pipeline`은 한 스테이지의 반환값을 다음 스테이지 `input`으로 직접 전달한다(`(prev)=>node_fetch(prev)`). `dispatch`는 fan-out 결과 배열을 sink에 넘긴다. 이것이 1차 데이터 경로이며, emit된 `P.<id>(input)` 프롬프트가 직전 출력을 JSON으로 직렬화해 다음 에이전트 프롬프트에 박는다.

**채널 2 — _workspace 파일 (감사·재개·사람용):** 각 노드의 `inputs`/`outputs`/`write_paths`는 `_workspace/` 아래 명시적 파일 경로다. 관례:

```
_workspace/00_input/<name>.md          ← 최초 입력 (사용자/seed)
_workspace/01_<node>/<artifact>.json   ← 노드 1 산출
_workspace/02_<node>/<artifact>.json   ← 노드 2 산출
…
```

- 노드 N의 `inputs`는 보통 노드 N-1의 `outputs`다 (예: fetch.inputs=`01_gather/findings.json`, gather.outputs도 동일).
- `write_paths`는 디렉토리 단위 소유권 — 두 노드가 같은 경로를 가지면 `WRITE_PATH_OVERLAP` 에러. `harness.lock`이 write_paths→node 맵을 정적으로 검증한다(M0는 런타임 write-lock hook 없음 — Mode A pipeline이 단일-writer를 구조적으로 보장).
- `_workspace/`는 **삭제하지 않고 보존** — 사후 검증·감사 추적·부분 재실행 입력.

**output_schema — 구조화 출력 강제:** 각 노드의 `output_schema` 파일이 `agent({schema})`로 inline되어, 에이전트 반환을 그 JSON-Schema에 강제한다. 이것이 원본의 "에이전트가 마크다운 보고서를 쓴다"는 느슨함을 대체한다 — 노드는 **검증된 JSON**을 반환하고, 그 JSON이 다음 노드의 입력이 된다. 스키마 규약:

- draft 2020-12, bare-filename `$id`(예: `"$id": "findings.json"`), `additionalProperties: false`, top-level `type` 필수.
- reflect-then-revise 노드는 `schemas/critique.json`도 필요 (critic 패스의 반환 스키마; `approved`+`issues[]`).
- 스키마끼리 id로 참조 연결 (claim.id ← critique.issues[].claim_id ← report.citations[].source_id) — 데이터가 파이프를 통과하며 추적 가능.

---

## 7. 에러 핸들링: on_exhaust + retries (원본 에러 매트릭스 대체)

원본은 "리더가 감지 → SendMessage 상태확인 → 재시작/재할당"이라는 **산문 절차**로 에러를 다뤘다. CYS는 이를 **노드별 두 선언 필드**로 환원한다 — 런타임이 강제하므로 "리더가 깜빡함"이 불가능하다.

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
| 작업 상태 지연 | TaskGet 수동 | (해당 없음 — 결정론 스케줄) |
| 예산 초과 | (원본 없음) | `ensure(min)` 가드 → `BUDGET_GUARD` throw → group 중단 |

**mechanism 자체가 에러 흡수기다:** majority-vote의 `quorum`/`tie_break`는 소수 에이전트 실패/이견을 정족수로 흡수한다(votes가 비면 null 반환). reflect-then-revise는 critic이 `approved=false`인 한 max_rounds까지 자가 교정한다(approved 시 조기 break). debate-with-judge는 상충 입장을 judge가 단일 판정으로 수렴한다. **노드 수준 retries/on_exhaust는 "메커니즘으로도 못 살린 실패"의 마지막 그물이다.**

deep-research 예: gather/fetch=`proceed-with-gap`(웹 결손 허용), verify=`proceed-with-gap`, **synthesize=`escalate`**(최종 산출 실패는 부분 진행 불가).

---

## 8. budget / approval

```jsonc
"budget": { "total_tokens": 600000, "approval_required": true }
```

- **`total_tokens`은 하드 ceiling이다.** warrant.py의 `cost_band()`가 추정 floor를 제안하고, graph.json 단일 writer가 retry·variance 여유로 floor를 두 배까지 잡을 수 있다. emit된 `ensure(min)`이 `budget.remaining() < min`이면 그룹을 abort(`BUDGET_GUARD`) — wall-clock이 아니라 토큰 잔량 기반이라 재개 안전.
- **`approval_required: true`** → 실행 전 `warrant.py --graph`로 `{total_tokens, weighted_units, band(LOW/MEDIUM/HIGH), usd_estimate}` 밴드를 표시하고, **명시적 'approve' 전까지 첫 `agent()` spawn을 BLOCK**한다.
- schema 조건부: `approval_required: true`면 `total_tokens`는 null 불가(반드시 정수).

cost_band 계산: `est_tokens = expected_tokens × fanout × (retries+1)`, `weighted_units = est_tokens × tier_weight{haiku:1, sonnet:3, opus:5}`. 이 weighted_units가 USD에 비례하며, MAX_FANOUT=5를 초과하는 도메인은 묶거나 2단계 합성하라는 경고가 뜬다.

---

## 9. RUNTIME.json 라우팅: canonical workflow.js vs 상속 prompt-runner

genome 전수로 하네스는 **두 개의 런타임**을 갖게 된다. `.harness/RUNTIME.json`이 모호성을 해소한다 (없으면 `RUNTIME_DECLARED` 에러).

| runtime | 역할 | entrypoint | graph.json 연결 | 언제 |
|---|---|---|---|---|
| **cys-mode-a** | **canonical** | `.harness/workflow.js` | **이 하네스 graph.json의 계약** | 기본 — 이 하네스가 정의한 모든 작업. graph→workflow.js가 THE 경로 |
| **awf-prompt-runner** | inherited-alternative | `prompt-runner/run.py` | **graph.json에 안 묶임** (범용 AWF batch 실행기) | ad-hoc 장시간·사람개입·rate-limit 노출 100+ step batch. 하네스 기본 아님 |

- `canonical_runtime`은 반드시 `"cys-mode-a"`.
- **라우팅 규칙:** 이 하네스는 canonical 런타임(`workflow.js`)으로 실행한다. prompt-runner는 장시간 사람주도 batch를 위한 **상속된 AWF 능력**이지, 이 하네스 그래프를 돌리는 두 번째 길이 **아니다**. **같은 작업을 두 런타임으로 동시에 돌리지 않는다** — 둘은 서로 호출하지 않고 같은 작업에 둘 다 invoke되지 않는다(prompt-runner는 graph.json에 바인딩되지 않음).

실행: `Workflow({ scriptPath: "<harness>/.harness/workflow.js", args: { query: "…" } })`. 중단 시 `resumeFromRunId`로 재개.

---

## 10. 후속 작업 지원 (resume · 부분 재실행 · 재실행)

원본의 Phase 0(컨텍스트 확인)을 CYS의 불변·결정론 구조로 재해석. **후속 키워드가 없으면 하네스는 첫 실행 후 죽은 코드가 된다** — 오케스트레이터 SKILL description에 반드시 후속 표현(재실행/수정/보완/부분 재생성/이전 결과 개선)을 포함하라(원본 원칙 유지).

`<harness>/` 및 `_workspace/` 존재 여부로 분기:

1. **`_workspace/` 미존재** → 초기 실행. `_workspace/00_input/`에 입력 저장 후 workflow 실행.
2. **`_workspace/` 존재 + resume 요청** → `resumeFromRunId`로 재개. **첫 변경 노드의 `agent()` 호출부터만** 재실행(이전 노드 출력은 `_workspace/`에서 재사용). 이것이 graph.json 불변성과 wall-clock 부재가 사주는 능력이다.
3. **`_workspace/` 존재 + 부분 수정 요청** → 해당 노드의 입력(`_workspace/0X_…`)을 갱신하고 그 노드부터 resume. 결정론이므로 동일 입력은 동일 출력 — 변경 노드만 재계산.
4. **`_workspace/` 존재 + 새 입력** → 기존 `_workspace/`를 `_workspace_{YYYYMMDD_HHMMSS}/`로 이동(보존) 후 새 실행.
5. **마이그레이션(import)** → 외부 산출물을 `_workspace/00_input/`로 적재 후 (1)처럼.

> 그래프 자체를 바꾸려면(노드 추가/topology 변경) graph.json을 수정 → `validate_harness.py` 통과 → `emit_workflow.py` 재-emit → `harness_version` bump. workflow.js를 손으로 고치지 않는다.

---

## 11. Mode B (team) — 언제, 왜 예외인가

`execution_mode: "team"`은 **`emit`되지 않는다** (`emit()`이 `execution_mode == "workflow"`를 assert). team 모드에서는 graph.json이 계약으로 남고, `TeamCreate`가 그것을 직접 해석한다(workflow.js 컴파일 없음).

**Mode B를 쓰는 유일한 정당화:** 에이전트 간 **실시간 inter-agent 통신이 본질적으로 필요**할 때 — 즉 에이전트들이 서로의 중간 상태를 실시간 협상해야 하고 파일/순차 패싱으로는 표현 불가능할 때. 그 외에는 절대 Mode B로 가지 않는다.

**왜 always가 아닌가:** 팀은 결정론적으로 스케줄될 수 없다(플랫폼 한계). 비결정성은 (a) `resumeFromRunId` 재개 불가, (b) 동일 입력의 동일 출력 보장 불가(재현성 상실), (c) `budget.total` hard-ceiling을 토큰 가드로 강제 불가를 의미한다. 이 세 손실은 거의 모든 도메인에서 실시간 협상의 이득을 초과한다. 따라서 **Mode A가 기본, Mode B는 입증된 예외**다.

> debate-with-judge mechanism이 "에이전트 간 의견 충돌·반박"의 90%를 **결정론적으로** 커버한다(transcript를 파일로 누적, judge가 수렴). 실시간 협상이 정말 필요한지 묻기 전에, debate-with-judge로 충분하지 않은지 먼저 확인하라.

---

## 12. 작성 원칙 (강제 게이트로 환원)

원본의 7개 산문 권고를 CYS의 머신체크로 환원. **권고가 아니라 `validate_harness.py`가 error를 내면 생성이 중단된다.**

| 원본 권고 (산문) | CYS 강제 (게이트) |
|---|---|
| "실행 모드를 먼저 명시" | `execution_mode` enum 필드 (GRAPH_SCHEMA) |
| "팀/서브 도구 사용법 구체적으로" | graph.json이 단일 진실; emit이 호출부 생성 |
| "파일 경로는 절대적으로 (상대 금지)" | ABSOLUTE_PATHS 게이트 (절대경로=error) |
| "Phase 간 의존성 명시" | `edges` + toposort + GRAPH_CYCLE 게이트 |
| "에러 핸들링 현실적으로" | `retries` + `on_exhaust` 필수 필드 |
| "테스트 시나리오 필수" | `lift_gate.py`(blind grader) + h2h_suite (with-skill vs haiku-baseline) |
| "모든 것이 성공한다고 가정 안 함" | `ensure()` 예산가드 + on_exhaust=escalate |
| (원본 "전부 opus") | model-tier-policy: role→tier, TIER_OVERSPEND 게이트 |
| (원본 "리더 산문 조율") | emit된 결정론 workflow.js, 수정 금지 |

**저작 절차 요약 (graph.json 중심):**

```
1. warrant.py --predicates  → build-harness(topology, mechanism, n_agents) 판정
   → 검증: verdict가 build-harness인가?
2. graph.json 저작 (단일 writer, schema 준수)
   → 검증: 모든 node에 model + on_exhaust + write_paths(겹침 없음)?
3. agent .md + schema 저작 (model + model_rationale + least-privilege tools)
   → 검증: 모든 node.agent 파일 + output_schema 파일 존재?
4. emit_workflow.py  → workflow.js + genome 전수
   → 검증: emit 성공 + GENOME VERIFY ok?
5. validate_harness.py  → 머신체크 세트 (error 0)
   → 검증: status == pass?
6. warrant.py --graph  → 비용밴드 → 승인 → Workflow 실행
   → 검증: approval 받음 + budget.total 내 완주?
```

각 단계의 변경된 모든 줄은 graph.json으로 직접 추적 가능해야 한다 — workflow.js는 emit 산물이지 손으로 쓰는 코드가 아니기 때문이다. **오케스트레이터를 "코딩"하지 말고, 그것이 emit되는 그래프를 저작하라.**
