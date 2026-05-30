> ⚠️ **구현 현황은 [`IMPLEMENTATION-STATUS.md`](IMPLEMENTATION-STATUS.md)가 우선한다.** 이 문서의 설계 서술 중 dispatch(dynamic)/supervisor·expert-pool·hierarchical 등은 M1-deferred(미구현)이며, `.claude/commands` 비우기 규칙은 폐기됐다.

# 아키텍처 패턴 — Topology × Decision-Mechanism 설계

> ⚠️ **PIVOT (2026-05-29)**: 산출 하네스의 canonical 실행모델은 이제 **Claude Code 프리미티브**(`emit_orchestrator.py` → 오케스트레이터 SKILL.md + `.claude/agents`, `execution_mode` `agent`(디폴트)`|team|hybrid`)다. 이 문서의 `workflow.js`/Mode-A 서술은 `execution_mode='workflow'`(byte-결정론 replay) **선택지**에만 적용된다. 구현 현황은 `IMPLEMENTATION-STATUS.md`가 우선하고, 근거는 `design/pivot-to-claude-primitives-strategy.md`.

> 출처: 원본 `agent-design-patterns.md`을 CYS 패러다임으로 적응 (team-vs-subagent 6패턴 모델 → 3 topology × 4 decision-mechanism 매트릭스 + graph.json 계약 + Mode-A/Mode-B + 머신체크 게이트).

이 문서는 **도메인 한 문장 → `graph.json`** 을 저작할 때 "어떤 구조로 짤 것인가"를 결정하는 설계 두뇌다. 원본의 설계 지혜(에이전트 분리 4축, 팀 크기 가이드, 복합 패턴 사고)는 보존하되, CYS의 계약 우선·결정론·역할티어 패러다임으로 재배선했다.

---

## 목차

1. [핵심 패러다임 전환](#1-핵심-패러다임-전환)
2. [graph.json — 모든 구조의 계약](#2-graphjson--모든-구조의-계약)
3. [두 직교 축: Topology × Decision-Mechanism](#3-두-직교-축-topology--decision-mechanism)
4. [Topology (3) — 데이터 흐름 축](#4-topology-3--데이터-흐름-축)
5. [Decision-Mechanism (4) — 조율 이론 축](#5-decision-mechanism-4--조율-이론-축)
6. [Topology × Mechanism 합성 매트릭스](#6-topology--mechanism-합성-매트릭스)
7. [원본 6패턴 → CYS 매핑](#7-원본-6패턴--cys-매핑)
8. [Mode-A(workflow) vs Mode-B(team) 선택](#8-mode-aworkflow-vs-mode-bteam-선택)
9. [도메인 → topology+mechanism 선택 알고리즘](#9-도메인--topologymechanism-선택-알고리즘)
10. [에이전트 분리 기준 (4축 — 원본 지혜 보존)](#10-에이전트-분리-기준-4축--원본-지혜-보존)
11. [에이전트 타입·모델 티어 선택](#11-에이전트-타입모델-티어-선택)
12. [팀 크기 / fan-out 가이드](#12-팀-크기--fan-out-가이드)
13. [복합 패턴 사고](#13-복합-패턴-사고)

---

## 1. 핵심 패러다임 전환

원본은 "에이전트 팀이 기본, `.claude/agents/`를 직접 쓴다, 6개 패턴 중 하나를 고른다, 모두 opus"를 가르쳤다. CYS는 이를 다음으로 대체한다:

| 원본 (idoforgod/harness) | CYS Harness Creator |
|---|---|
| 팀(team)이 기본 실행 모드 | **Mode-A(workflow 결정론 서브에이전트)가 디폴트.** 실시간 inter-agent comms가 필수일 때만 Mode-B(team) |
| `.claude/agents/`를 계약 없이 직접 저작 | **먼저 `graph.json`(불변 계약)을 저작** → 도구가 컴파일·검증 |
| 6개 패턴(데이터 흐름 한 축) | **3 topology × 4 decision-mechanism** (두 직교 축) |
| 모든 에이전트 `model: opus` | **role→tier 정책** (gather/extract/format/qa-scan=haiku, voter/debater/reviser=sonnet, synthesis/judge/critic=opus) |
| advisory prose 규칙 | **머신체크 게이트** (`validate_harness.py` 머신체크 세트가 위반 시 빌드 실패) |

> **불변 원칙:** 구조 선택은 산문이 아니라 `graph.json` 필드값으로 확정된다. `topology`·`decision_mechanism`·`model`은 모두 스키마 enum이며, `validate_harness.py`가 강제한다. "이렇게 하는 게 좋다"는 없다 — 게이트를 통과하거나 빌드가 실패하거나 둘 중 하나다.

---

## 2. graph.json — 모든 구조의 계약

모든 하네스는 단 하나의 `graph.json`(불변 spine, JSON-Schema 검증)으로 표현된다. 메타스킬만이 이 파일을 쓴다(single-writer). 구조 설계 = 이 파일의 필드를 채우는 일이다.

```jsonc
{
  "schema_version": "0.1",
  "harness_name": "deep-research",            // ^[a-z][a-z0-9-]+[a-z0-9]$
  "harness_version": "0.1.0",
  "execution_mode": "workflow",               // "workflow"=Mode-A(디폴트) | "team"=Mode-B(폴백)
  "topology": "pipeline",                     // pipeline | dispatch | producer-reviewer
  "budget": { "total_tokens": 600000, "approval_required": true },
  "nodes": [ /* … */ ],
  "edges": [ { "from": "gather", "to": "fetch" } ]  // ORDERING ONLY — depends_on 그래프 아님
}
```

**node 구조** (각 노드 = 그래프의 한 논리 단계):

```jsonc
{
  "id": "verify",                             // ^[a-z][a-z0-9_]+[a-z0-9]$
  "agent": "verifier",                        // -> .claude/agents/verifier.md
  "model": "sonnet",                          // haiku|sonnet|opus (REQUIRED, agent frontmatter에 model_rationale도 필수)
  "decision_mechanism": "reflect-then-revise",// single | majority-vote | debate-with-judge | reflect-then-revise
  "mechanism_params": { "max_rounds": 2, "critic": "opus" },
  "inputs": ["_workspace/02_fetch/findings.json"],
  "outputs": ["_workspace/03_verify/findings.json"],
  "write_paths": ["_workspace/03_verify/"],   // 노드 간 write_path 중첩 금지 (게이트)
  "output_schema": "schemas/findings.json",   // JSON-Schema 파일 (강제 출력)
  "retries": 0,
  "on_exhaust": "proceed-with-gap",           // proceed-with-gap | force-pass | escalate
  "max_rounds": 2
}
```

핵심 의미론:
- **`edges`는 순서(ordering)만 표현한다.** pipeline 스케줄링/parallel fan-out/loop 경계를 정의할 뿐, TaskCreate식 `depends_on` 의존성 그래프가 아니다.
- **`topology`는 graph 전체의 형태**, **`decision_mechanism`은 노드 단위**다. 그래서 한 pipeline 안에서 노드마다 다른 mechanism을 쓸 수 있다(예: deep-research의 verify=reflect-then-revise, 나머지=single).
- 컴파일: `emit_workflow.py`가 `graph.json` → `.harness/workflow.js`(Mode-A 결정론 런타임: `agent()`/`parallel()`/`pipeline()`, `budget.total`=하드 ceiling, `resumeFromRunId`, schema 강제 출력, wall-clock/RNG 없음).

---

## 3. 두 직교 축: Topology × Decision-Mechanism

원본의 가장 큰 한계는 "데이터 흐름"이라는 **한 축**으로만 패턴을 나눈 것이다(파이프라인/팬아웃/풀/생성검증/감독자/계층). CYS는 이를 **두 직교 축**으로 분해한다:

```
                  DECISION-MECHANISM (노드가 결정을 내리는 방법 — 조율 이론 축)
                  single        majority-vote   debate-with-judge   reflect-then-revise
                ┌────────────┬────────────────┬──────────────────┬─────────────────────┐
  T  pipeline   │  순차 단순   │  단계 내 투표    │  단계 내 토론      │  단계 내 반복 정제     │
  O             ├────────────┼────────────────┼──────────────────┼─────────────────────┤
  P  dispatch   │  병렬 단순   │  병렬+투표 합성  │  병렬+토론 합성    │  병렬+sink 정제       │
  O             ├────────────┼────────────────┼──────────────────┼─────────────────────┤
  L  producer-  │  생성→검수   │  (드묾)        │  생성↔검수 토론    │  생성→비평→수정 루프   │
  O  reviewer   │            │                │                  │  (정준 조합)          │
  G            └────────────┴────────────────┴──────────────────┴─────────────────────┘
  Y
  (데이터가 노드 사이를 흐르는 형태 — 데이터 흐름 축)
```

- **Topology**는 "노드들이 시간·공간상 어떻게 배치되는가"(순차/병렬/루프).
- **Decision-Mechanism**은 "한 노드가 답을 어떻게 만드는가"(혼자/투표/토론/반복정제).
- 두 축은 **합성 가능(composable)**하다. topology를 고른 뒤, 그 안의 각 노드에 mechanism을 독립적으로 부여한다.

> 이 직교성이 원본 대비 CYS의 핵심 표현력이다. 원본의 "생성-검증"은 *데이터 흐름이면서 동시에 조율 방법*이라 두 개념이 엉켜 있었다. CYS는 이를 분리한다: producer-reviewer(topology) + reflect-then-revise(mechanism)는 별개이며 따로 조합할 수 있다.

---

## 4. Topology (3) — 데이터 흐름 축

### 4.1 pipeline (순차)

이전 노드의 출력이 다음 노드의 입력. `edges`가 단일 선형 체인.

```
[gather] → [fetch] → [verify] → [synthesize]
```

- **적합:** 각 단계가 이전 단계 산출물에 강하게 의존하고, 순서가 의미를 가질 때.
- **예시:** deep-research(수집→페치→검증→합성), 소설 집필(세계관→캐릭터→플롯→집필→편집).
- **graph.json:** `topology: "pipeline"`, edges는 선형 체인.
- **주의 (원본 지혜 보존):** 병목 한 단계가 전체를 지연시킨다. 각 단계를 가능한 독립적으로 설계해 재실행 시 변경 노드부터만 재개되게 한다(`resumeFromRunId`).
- **Mode-A 적합성:** 순차 의존이 강해 결정론 Mode-A가 이상적. 단계 산출물이 파일(`_workspace/`)로 고정되므로 재개·감사가 자연스럽다.

### 4.2 dispatch (병렬 fan-out + 단일 sink)

분배 노드가 독립 작업을 병렬로 펼치고, 단일 sink 노드가 결과를 통합. 원본의 fan-out/fan-in과 supervisor를 하나로 흡수한다.

```
          ┌→ [expert_a] ─┐
[dispatch]├→ [expert_b] ─┼→ [synthesize] (단일 sink)
          └→ [expert_c] ─┘
```

dispatch는 두 하위 모드를 가진다:

| 하위 모드 | 분배 방식 | 원본 대응 | 언제 |
|---|---|---|---|
| **static** | 사전에 작업을 고정 분배(fan-out) | fan-out/fan-in | 작업 수가 설계 시 결정됨 (예: 4개 영역 동시 조사) |
| **dynamic** | 런타임에 claim/supervisor가 동적 할당 | supervisor | 작업량이 가변적, 런타임에 배치 결정 (예: 파일 목록 마이그레이션) |

- **적합:** 동일 입력에 서로 다른 관점/영역의 처리가 필요하고, 독립 실행 가능할 때.
- **예시:** 종합 리서치(공식/미디어/커뮤니티/배경 동시 조사 → 통합), 코드 마이그레이션(supervisor가 파일 배치 할당).
- **graph.json:** `topology: "dispatch"`, edges가 분배→워커들→sink. fan-out 폭 ≤ `MAX_FANOUT(5)`.
- **주의 (원본 지혜 보존):** **단일 sink의 품질이 전체 품질을 결정한다.** sink는 거의 항상 synthesis role-class → opus. dynamic 모드는 supervisor가 병목이 되지 않게 위임 단위를 충분히 크게.
- **Mode-A 적합성:** static dispatch는 `parallel()`로 완벽히 결정론적. dynamic은 claim 기반으로 가능하나 supervisor의 실시간 재할당이 필요하면 Mode-B 검토(§8).

### 4.3 producer-reviewer (경계 루프)

생성 노드와 검수 노드가 쌍을 이뤄 품질 기준 충족까지 경계된 횟수만큼 반복.

```
[produce] → [review] →(문제시)→ [produce] 재실행  (max_rounds로 경계)
```

- **적합:** 산출물 품질 보장이 중요하고 객관적 검증 기준이 존재할 때.
- **예시:** 웹툰(artist 생성 → reviewer 검수 → 문제 패널 재생성), 코드 생성→린트→수정.
- **graph.json:** `topology: "producer-reviewer"`, 두 노드 + 루프 edge. **무한 루프 방지: `max_rounds` 2~3 필수**(스키마가 max 3으로 강제).
- **CYS의 정련:** producer-reviewer는 종종 **단일 노드의 reflect-then-revise mechanism으로 압축**된다(§5.4). 두 에이전트(producer/reviewer)가 진짜로 다른 전문성·도구를 가질 때만 topology로, 같은 에이전트의 비평·수정 두 패스면 단일 노드 + reflect-then-revise가 더 단순하다.

---

## 5. Decision-Mechanism (4) — 조율 이론 축

원본에 없던 새 직교 축. 한 노드가 답을 만드는 방법을 결정한다. `mechanism_params`로 파라미터화되고 스키마가 mechanism별 필수 필드를 강제한다.

### 5.1 single

노드가 한 번의 에이전트 호출로 답을 낸다. 가장 단순·저렴.

- **params:** 없음.
- **언제:** 답이 결정적이거나 단일 전문가로 충분할 때(수집·페치·포맷·최종 합성 중 추가 검증 불필요한 경우).
- **fan-out 비용:** 1 (agent() 호출 1회).

### 5.2 majority-vote (병렬 투표)

n개 voter가 독립적으로 같은 문제를 풀고 다수결로 답을 확정.

- **params (필수):** `n`(2~5), `quorum`(다수 임계). 선택: `tie_break`(first | highest-confidence).
- **언제:** 답이 **객관적이지만 단일 패스가 노이즈에 취약**할 때(웹 사실 추출, 분류). 같은 정답을 여러 번 독립 추정해 분산을 줄인다.
- **role-class:** voter → sonnet (고정 프레임 내 경계 추론).
- **fan-out 비용:** n.

### 5.3 debate-with-judge (토론 + 심판)

n명의 debater가 max_rounds 동안 논쟁하고, judge가 최종 판정.

- **params (필수):** `max_rounds`(1~3), `judge`(model tier). 선택: `n`.
- **언제:** 답이 **주관적·평가적**이고 관점 충돌에서 더 나은 답이 나올 때(설계 트레이드오프, 전략 평가, 정성 심사).
- **role-class:** debater → sonnet, judge → opus (개방형 최종 판단).
- **fan-out 비용:** 2·max_rounds + 1.

### 5.4 reflect-then-revise (비평→수정 루프)

한 에이전트가 max_rounds 동안 critic 패스(결함 지목)와 reviser 패스(결함 수정)를 번갈아 수행. 단일 산출물을 반복 정제.

- **params (필수):** `max_rounds`(1~3), `critic`(model tier).
- **언제:** **단일 산출물을 점진적으로 정제**해 품질을 끌어올릴 때(사실 검증, 초안 정제). critic이 통과시키면(`approved=true`) 그 라운드에서 루프가 끊겨 reviser는 호출되지 않는다.
- **role-class:** reviser → sonnet, critic → opus (critic은 mechanism_params로 별도 티어링).
- **fan-out 비용:** 2·max_rounds.
- **정준 예시:** deep-research의 verify 노드 — 한 `verifier` 에이전트가 critic 패스(opus, 약한·오인용·과장 claim 지목)와 reviser 패스(sonnet, 수정/삭제)를 라운드마다 수행.

> **mechanism과 model의 결합:** mechanism이 노드의 base role을 override한다. majority-vote→voter, debate→debater, reflect→reviser. judge/critic은 `mechanism_params`에서 따로 티어링된다. 이 매핑은 `model-tier-policy.js`의 `roleClassOf()`가 강제한다.

---

## 6. Topology × Mechanism 합성 매트릭스

각 셀 = 한 노드(또는 sink)에 mechanism을 부여한 조합. **언제 쓰는가**를 명시한다.

| Topology \ Mechanism | single | majority-vote | debate-with-judge | reflect-then-revise |
|---|---|---|---|---|
| **pipeline** | 단계가 결정적, 추가 검증 불필요 (gather/fetch/format) | 한 단계가 노이즈 취약한 객관 추출 (사실 추출 단계) | 한 단계가 주관 평가 (설계 결정 단계) | **정준** — 한 단계가 정제 필요한 검증/초안 (deep-research verify) |
| **dispatch** | 워커들이 독립 수집, sink가 단순 병합 | 각 워커가 같은 문제 투표 후 sink 합성 | 워커들이 관점 충돌, sink/judge가 판정 | sink가 통합 산출물을 반복 정제 |
| **producer-reviewer** | 생성→1회 검수→통과/재생성 | (드묾 — 검수에 투표 필요할 때만) | producer↔reviewer가 실시간 토론 (→ Mode-B 신호) | **정준 압축** — 단일 노드로 융합 |

읽는 법:
1. 먼저 도메인의 **데이터 흐름**으로 topology를 고른다(§9 알고리즘).
2. 그 다음 **각 노드**의 답 생성 특성으로 mechanism을 고른다(객관/노이즈→majority-vote, 주관→debate, 단일산출물 정제→reflect).
3. 대부분 노드는 `single`이고, **품질이 임계인 1~2개 노드만** 비용이 높은 mechanism을 받는다(AC-1 품질 우선 + 비용 거버넌스 균형).

---

## 7. 원본 6패턴 → CYS 매핑

원본의 6패턴을 어떻게 흡수했는지 명시한다(마이그레이션·이해용).

| 원본 패턴 | CYS 매핑 | 비고 |
|---|---|---|
| **1. 파이프라인** | `topology: pipeline` | 그대로 |
| **2. 팬아웃/팬인** | `topology: dispatch` (static) | 사전 고정 분배 → static 하위 모드 |
| **3. 전문가 풀** | **deferred** | 라우터 기반 선택 호출. M0 미지원. dispatch + 조건부 노드로 근사하거나 차기 버전 대기 |
| **4. 생성-검증** | `topology: producer-reviewer` **+** `decision_mechanism: reflect-then-revise` | 두 개념으로 분해 — 진짜 다른 두 에이전트면 topology, 비평·수정 두 패스면 단일 노드 mechanism |
| **5. 감독자** | `topology: dispatch` (dynamic) | 런타임 동적 할당 → dynamic 하위 모드(claim/supervisor) |
| **6. 계층적 위임** | **deferred** | 중첩 위임. M0 미지원(팀 중첩 불가 + 결정론 스케줄 어려움). 평탄화하여 dispatch로 근사하거나 차기 버전 |

> **deferred 2개(전문가 풀·계층적 위임)**는 M0에서 의도적으로 제외했다. 둘 다 런타임 분기·재귀가 핵심이라 결정론 Mode-A로 깔끔히 컴파일되지 않는다. 도메인이 이를 강하게 요구하면 (a) dispatch로 평탄화, (b) Mode-B 검토(§8), (c) 차기 버전 대기 순으로 판단한다.

---

## 8. execution_mode 선택 (agent 디폴트 / team / hybrid / workflow)

`graph.json`의 `execution_mode`가 산출 하네스의 런타임을 정한다. **프리미티브 기질(agent/team/hybrid)이 기본**이다 — 그래야 상속된 AWF 게놈(lifecycle hook·L0-L2 게이트·SOT·적대적 리뷰)이 발화하고, 커스텀 `.claude/agents`의 model·tools가 런타임 강제된다(P-1 실측). `workflow`는 byte-결정론 replay가 필수인 드문 경우의 선택지다.

| mode | 런타임 | emit | 언제 |
|------|--------|------|------|
| **`agent`** (디폴트) | Agent 도구 순차/병렬 sub-spawn | `emit_orchestrator.py` | 거의 전부. 부모/자식 hook 발화가 가장 확실(P-1 검증) |
| `team` | TeamCreate 피어팀 + SendMessage | `emit_orchestrator.py` | 실시간 inter-agent 협상이 품질을 좌우할 때. **P5 라이브 입증 후 승격**(현재 opt-in) |
| `hybrid` | Phase별 agent/team 혼합 | `emit_orchestrator.py` | 병렬 수집(agent) → 합의 통합(team) 등 |
| `workflow` | Workflow 도구 `workflow.js` | `emit_workflow.py` | byte-결정론 replay·`resumeFromRunId`가 필수인 좁은 경우. **이 기질에선 AWF 게놈이 휴면**(두 평면 직교) |

### 선택 의사결정

```
byte-exact 결정론 replay가 이 하네스에 필수인가?
├── No  → 프리미티브 기질        ← 디폴트. 거의 전부.
│        실시간 inter-agent 협상이 품질에 본질적?
│        ├── No  → execution_mode = agent   (디폴트; 순차/병렬 sub-spawn)
│        └── Yes → execution_mode = team    (opt-in, P5 입증 후)
│        (Phase별 혼합이면 hybrid)
└── Yes → execution_mode = workflow         ← Mode-A 선택지. AWF 게놈 휴면 감수.
```

> **핵심 전환(피벗):** 초기 CYS는 "workflow가 기본"이었으나, 그 기질에서 AWF 게놈 전체가 휴면함이 실측됐다(두 실행평면 직교). 피벗 후 **프리미티브가 기본** — AWF가 설계된 곳이고, 게놈이 실제로 발화하며, 모델티어가 런타임 강제된다. agent vs team은 "실시간 통신이 필수인가"로 가르되, agent를 먼저(부모/자식 hook 발화가 검증된 경우).

### RUNTIME 라우팅 주의

생성 하네스는 게놈으로 여러 런타임을 상속한다. `.harness/RUNTIME.json`(프리미티브 모드는 `emit_orchestrator`가, workflow 모드는 `inherit_genome`이 작성)이 정규를 선언한다:
- **CANONICAL = `<name>-orchestrator` SKILL** (프리미티브 디폴트) — `cd <harness> && claude`로 연 라이브 세션에서 이 스킬을 트리거. 그 세션의 settings.json hook이 발화한다(**공장 세션이 아님 — R4 핸드오프**).
- **OPTIONAL = `.harness/workflow.js`** (Mode-A) — `execution_mode='workflow'`에서만.
- **ALTERNATIVE = 상속된 `prompt-runner/run.py`** — AWF 범용 `claude -p` 배치(graph.json 미연결). 같은 작업을 둘로 돌리지 않는다.

---

## 9. 도메인 → topology+mechanism 선택 알고리즘

`warrant.py`의 `classify()`가 5개 술어로 이 결정을 결정론적으로 내린다. LLM은 도메인 한 문장에서 5개 술어를 *한 번* 추출하고, 게이트가 나머지를 한다.

### 5개 술어

```jsonc
{
  "distinct_expertise_domains": 4,          // 서로 다른 전문성 영역 수
  "has_dependent_or_parallel_stages": true, // 순차 의존 또는 병렬 단계가 있는가
  "will_be_rerun": true,                     // 재사용·재실행 되는가
  "output_objective": true,                  // 출력이 객관적(정답 존재)인가
  "noisy": false                             // 단일 패스가 노이즈에 취약한가
}
```

### 분류 로직 (warrant.py classify)

**1단계 — 하네스가 필요한가 (off-ramp):**
```
domains < 2 AND no staged?
├── not rerun AND not noisy AND objective  → answer-directly  (하네스 없이 직접 답)
└── else                                    → single-agent     (단일 에이전트 1회)
else → build-harness (아래 2단계)
```

**2단계 — topology 선택:**
```
staged AND domains >= 2  → pipeline       (순차/병렬 다단계, 단계 간 의존)
domains >= 2 (단일 단계)  → dispatch        (다영역 병렬 fan-out + sink)
else                      → producer-reviewer  (단일영역 다단계 정제)
```

**3단계 — decision_mechanism 선택 (FIRST match):**
```
not objective  → debate-with-judge   (주관 평가 — 관점 충돌이 품질을 만듦)
staged         → reflect-then-revise (순차 파이프라인 — 단일 산출물 반복 정제)
noisy          → majority-vote       (단일단계 객관+노이즈 — 병렬 투표로 분산 감소)
else           → single              (결정적 — 추가 조율 불필요)
```

**n_agents:** `min(distinct_expertise_domains, MAX_FANOUT=5)`. 초과 시 도메인 묶기 또는 2단계 합성.

> 이 분류는 **제안(proposal)**이다. graph.json의 single-writer(메타스킬)가 최종 확정하며, 노드별로 mechanism을 다르게 줄 수 있다(예: pipeline 전체는 reflect 제안이라도 gather/fetch는 single, verify만 reflect-then-revise). classify의 mechanism은 "이 도메인의 가장 임계 단계에 어떤 조율이 어울리는가"의 기본값이다.

### 워크스루: deep-research

술어 `{domains:4, staged:true, rerun:true, objective:true, noisy:true}` →
- off-ramp 통과(domains≥2, staged) → build-harness
- topology: staged AND domains≥2 → **pipeline**
- mechanism(first match): not-objective? 아니오 → staged? 예 → **reflect-then-revise** (가장 임계 단계 = verify)
- 실제 graph: gather(single)→fetch(single)→verify(reflect-then-revise)→synthesize(single). pipeline + 노드별 mechanism 혼합.

---

## 10. 에이전트 분리 기준 (4축 — 원본 지혜 보존)

> 원본의 핵심 설계 지혜. **그대로 보존한다.** 한 노드를 하나의 에이전트로 둘지, 쪼갤지 판단하는 4축.

| 기준 | 분리 | 통합 |
|------|------|------|
| **전문성 (expertise)** | 영역이 다르면 분리 | 영역이 겹치면 통합 |
| **병렬성 (parallelism)** | 독립 실행 가능하면 분리 | 순차 종속이면 통합 고려 |
| **컨텍스트 (context)** | 컨텍스트 부담이 크면 분리 | 가볍고 빠르면 통합 |
| **재사용성 (reuse)** | 다른 하네스에서도 쓰면 분리 | 이 하네스에서만 쓰면 통합 고려 |

CYS 맥락에서의 적용:
- 분리는 **노드 수 증가 = 비용 증가**다(cost-band가 노드별 est_tokens 합산). 4축이 모두 분리를 가리킬 때만 쪼갠다.
- 분리한 두 에이전트는 각각 **`write_paths`가 겹치면 안 된다**(`validate_harness.py`가 write-path overlap을 error로 차단). 병렬 노드가 같은 파일을 쓰면 분리가 잘못된 것이다.
- reflect-then-revise처럼 **한 에이전트가 두 역할(critic/reviser)**을 패스로 수행하는 경우는 "분리"가 아니라 단일 agentType + mechanism으로 표현한다(deep-research verifier 참조).

---

## 11. 에이전트 타입·모델 티어 선택

### 모델 티어 — role→tier 정책 (원본의 "all opus" 대체)

원본은 모든 에이전트를 opus로 강제했다. CYS는 `model-tier-policy.js`로 role-class별 티어를 강제한다:

| role-class | tier | 키워드 매칭(node.id+agent) |
|---|---|---|
| gather, extract, format, qa-scan | **haiku** | gather/fetch/search/extract/parse/format/render/report/qa/lint/check/verify |
| voter, debater, reviser | **sonnet** | (mechanism이 부여: majority-vote→voter, debate→debater, reflect→reviser) |
| synthesis, judge, critic, architecture | **opus** | synth/aggregate/merge/judge/critic/review/architect/plan/design |

- **모든 노드는 `model:` 필수 + agent frontmatter에 `model_rationale:` 필수**(V1 게이트).
- **pure-retrieval role에 opus 금지** — `tier_override_reason` 없이 gather/extract/format/qa-scan을 opus로 두면 error(V2 게이트).
- **node.model == agent frontmatter model** 일치 강제(V3 게이트).
- 미매핑 role-class는 fail-safe-expensive로 synthesis(opus) 처리 → 검증기가 명시적 model을 강제(은밀히 싸고 틀리는 것 방지).

### 에이전트 정의 (`.claude/agents/<agent>.md`)

모든 `node.agent`는 `.claude/agents/<agent>.md` 파일로 존재해야 한다(`validate_harness.py`가 agent-file-exists 체크). frontmatter:

```yaml
---
name: verifier
description: "역할 + 트리거 키워드 (pushy하게 — 트리거 메커니즘)"
tools: Read, Write          # least-privilege (필요 도구만)
model: sonnet               # node.model과 일치해야 함 (V3)
model_rationale: "왜 이 티어인가 1문장"   # 필수 (V1)
---
```

본문: 핵심역할 / 작업원칙 / 입출력 프로토콜(정확한 `_workspace/` 경로 + 방출 schema) / 에러핸들링. mechanism 노드는 어떤 패스를 도는지 명시(critic 패스 vs reviser 패스).

> **원본 빌트인 타입(general-purpose/Explore/Plan)은 CYS에서 직접 쓰지 않는다.** 모든 에이전트는 명시적 `.claude/agents/` 파일로 정의하고 model 티어 + least-privilege tools를 선언한다. 빌트인 타입의 "읽기 전용" 의도는 CYS에서 `tools:` 화이트리스트(예: `Read` only)로 표현한다.

---

## 12. 팀 크기 / fan-out 가이드

> 원본의 팀 크기·계층 깊이 지혜를 CYS fan-out 한계로 번역.

- **fan-out 폭 ≤ MAX_FANOUT(5).** dispatch의 병렬 워커, majority-vote의 n, debate의 debater 수 모두 이 한계. 초과 시: (a) 영역 묶기, (b) 2단계 합성(워커→중간 sink→최종 sink).
- **계층 깊이 ≤ 2.** 원본의 "3단계 이상은 지연·컨텍스트 손실" 경고를 보존. CYS에서 계층적 위임은 deferred이므로, 자연히 계층적인 도메인은 dispatch로 평탄화하거나 2단계 sink 합성으로 근사한다.
- **노드 수와 비용은 비례한다.** 노드를 늘리기 전에 4축 분리 기준(§10)을 통과하는지 확인. 통과 못 하면 통합이 옳다(단순성 우선).
- **mechanism fan-out 비용 인지:** single=1, majority-vote=n, debate=2·rounds+1, reflect=2·rounds. 임계 노드에만 비싼 mechanism을 부여(§6 마지막 원칙).

---

## 13. 복합 패턴 사고

원본은 단일 패턴보다 복합이 흔하다고 가르쳤다. CYS에서 "복합"은 **topology는 하나, 노드별 mechanism은 혼합**으로 표현된다.

| 원본 복합 패턴 | CYS 표현 | 예시 |
|---|---|---|
| 팬아웃 + 생성-검증 | dispatch topology + 각 워커 노드에 reflect-then-revise mechanism | 4언어 병렬 번역, 각 노드가 비평→수정 |
| 파이프라인 + 팬아웃 | pipeline topology + 중간 단계를 dispatch sink로 (또는 2-graph 합성) | 분석(순차)→구현(병렬 dispatch)→통합(순차) |
| 감독자 + 전문가 풀 | dispatch(dynamic) + (expert-pool은 deferred → 조건부 노드 근사) | 문의 분류 후 동적 할당 |

복합 설계 원칙:
1. **topology는 도메인의 지배적 데이터 흐름** 하나로 정한다(graph 전체는 단일 topology 필드).
2. **mechanism은 노드마다** 그 노드의 답 생성 특성으로 정한다 — 이것이 "복합"을 만든다.
3. 진짜로 두 개의 다른 데이터 흐름이 필요하면(예: 병렬 생성 *그리고* 순차 합성), **단일 sink로 수렴하는 dispatch**로 표현하거나, 단계를 분리해 pipeline 안에 dispatch 구간을 둔다.
4. 실시간 양방향 협업이 *본질적*이어서 어떤 mechanism으로도 표현 안 되면 — 그때만 Mode-B(§8).

> deep-research가 정준 복합 예시다: **pipeline(topology)** 하나에 노드별로 single·single·**reflect-then-revise**·single을 혼합. 원본이라면 "파이프라인 + 생성-검증 복합"이라 불렀을 것을, CYS는 단일 topology + 노드별 mechanism의 깔끔한 직교 표현으로 담는다.
