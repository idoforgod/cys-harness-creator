> ⚠️ **구현 현황은 [`IMPLEMENTATION-STATUS.md`](IMPLEMENTATION-STATUS.md)가 우선한다.** 이 문서의 설계 서술 중 dispatch(dynamic)/supervisor·expert-pool·hierarchical 등은 M1-deferred(미구현)이며, `.claude/commands` 비우기 규칙은 폐기됐다.

# Harness Examples — graph.json으로 배우는 CYS 패러다임

> 출처: 원본 `team-examples.md`을 CYS 패러다임으로 적응. 원본은 "팀 vs 서브에이전트" 6개 패턴을 가르쳤다. 이 문서는 **검증된 3개의 실제 harness**를 통해 CYS의 계약(graph.json) + 위상(topology) × 결정기제(decision_mechanism) 모델을 가르친다.

이 문서는 추상 패턴 카탈로그가 아니다. `examples/{deep-research,ticket-triage,design-decision}/`에 실재하며 `validate_harness.py`를 통과한 세 harness의 **실제 graph.json·실제 agent 파일**을 인용한다. 모든 필드·model·rationale은 디스크에 있는 그대로다.

---

## 목차

1. [먼저: CYS에서 harness는 graph다](#1-먼저-cys에서-harness는-graph다)
2. [위상 3개 × 결정기제 4개 — 선택 매트릭스](#2-위상-3개--결정기제-4개--선택-매트릭스)
3. [예시 A — deep-research (pipeline + reflect-then-revise)](#3-예시-a--deep-research-pipeline--reflect-then-revise)
4. [예시 B — ticket-triage (dispatch + majority-vote)](#4-예시-b--ticket-triage-dispatch--majority-vote)
5. [예시 C — design-decision (producer-reviewer + debate-with-judge)](#5-예시-c--design-decision-producer-reviewer--debate-with-judge)
6. [세 예시 교차 비교 — 같은 원리, 다른 좌표](#6-세-예시-교차-비교--같은-원리-다른-좌표)
7. [보존된 설계 지혜 — agent-split·pushy description·QA 경계](#7-보존된-설계-지혜)
8. [Mode-A가 기본, Mode-B는 예외](#8-mode-a가-기본-mode-b는-예외)
9. [산출물 패턴 요약 — graph.json이 척추다](#9-산출물-패턴-요약--graphjson이-척추다)

---

## 1. 먼저: CYS에서 harness는 graph다

원본은 "`.claude/agents/`에 에이전트 파일을 바로 쓰고, 팀을 만들어 SendMessage로 조율하라"고 가르쳤다. CYS는 **그 순서를 뒤집는다**.

> **계약 우선(contract-first).** harness를 설계한다는 것은 곧 `graph.json` 하나를 쓰는 것이다. graph.json은 불변의 척추(immutable spine)이며 `graph.schema.json`으로 검증된다. agent 파일·schema 파일·workflow.js는 모두 graph.json에서 파생된다.

graph.json의 최상위 필드:

| 필드 | 의미 |
|------|------|
| `schema_version` | 계약 스키마 버전 (현재 "0.1") |
| `harness_name` / `harness_version` | 식별자 |
| `execution_mode` | `"workflow"`(Mode-A, 기본) \| `"team"`(Mode-B, 예외) |
| `topology` | `pipeline` \| `dispatch` \| `producer-reviewer` (데이터 흐름 축) |
| `budget` | `{ total_tokens, approval_required }` — 하드 예산 천장 + 승인 게이트 |
| `nodes[]` | 노드 정의 배열 (아래) |
| `edges[]` | **순서만** 표현. `depends_on`이 아니다 — 의존이 아니라 토폴로지 정렬용 |

각 노드(node)의 필드:

| 필드 | 의미 |
|------|------|
| `id` | 노드 식별자 |
| `agent` | `.claude/agents/<agent>.md`를 가리킴 |
| `model` | `haiku` \| `sonnet` \| `opus` — **필수**. agent frontmatter에 `model_rationale:` 동반 필수 |
| `decision_mechanism` | `single` \| `majority-vote` \| `debate-with-judge` \| `reflect-then-revise` (조율 이론 축) |
| `mechanism_params` | 기제별 파라미터 (n, quorum, tie_break, max_rounds, judge, critic …) |
| `inputs[]` / `outputs[]` | 읽는·쓰는 파일 경로 |
| `write_paths[]` | 이 노드가 쓸 수 있는 디렉터리 (겹치면 validate가 차단) |
| `output_schema` | JSON-Schema 파일 (출력 강제) |
| `retries` / `on_exhaust` | 재시도 횟수 / 소진 시 행동: `proceed-with-gap` \| `force-pass` \| `escalate` |
| `max_rounds` | 루프형 기제의 라운드 상한 |

이 계약은 **조언이 아니라 기계 게이트로 강제된다**: `validate_harness.py`(머신체크 세트: 스키마·agent 파일 존재·model 티어·엣지 무결성·사이클·write-path 중복·절대경로·schema 파일 존재·genome 존재·runtime 선언·doc-drift), `warrant.py`(Phase -1 비용 게이트), `model-tier-policy.js`(역할→티어 정책).

---

## 2. 위상 3개 × 결정기제 4개 — 선택 매트릭스

CYS는 원본의 6개 패턴을 **두 개의 직교 축**으로 재구성했다.

**위상(topology) — 데이터가 어떻게 흐르는가 (3개):**
- `pipeline` — 순차. 한 노드 출력이 다음 노드 입력. (원본 파이프라인)
- `dispatch` — 병렬 fan-out + 단일 sink. static(고정 fan-out=원본 팬아웃) / dynamic(claim·supervisor=원본 감독자).
- `producer-reviewer` — 생성↔검증의 경계 루프. (원본 생성-검증)

> 원본의 expert-pool·hierarchical은 deferred. fan-out→dispatch(static), supervisor→dispatch(dynamic)로 흡수됐다.

**결정기제(decision_mechanism) — 한 노드 안에서 판단이 어떻게 내려지는가 (4개, 원본에 없던 새 축):**
- `single` — 단일 에이전트가 결정.
- `majority-vote` — n개 독립 ballot을 JS가 집계 (params: n, quorum, tie_break).
- `debate-with-judge` — n명이 양측 변론 후 judge가 판정 (params: n, max_rounds, judge).
- `reflect-then-revise` — critic이 결함 지적 → reviser가 수정, 라운드 반복 (params: max_rounds, critic).

핵심: **두 축은 조합 가능하다.** dispatch 위상의 source 노드에 majority-vote를, pipeline 위상의 한 노드에 reflect-then-revise를 끼울 수 있다. 이것이 CYS의 조율 이론(coordination-theory) 기여다.

| | single | majority-vote | debate-with-judge | reflect-then-revise |
|--|--------|---------------|-------------------|---------------------|
| **pipeline** | gather/fetch/synthesize (예시 A) | — | — | **verify (예시 A)** |
| **dispatch** | route sink (예시 B) | **classify (예시 B)** | — | — |
| **producer-reviewer** | propose (예시 C) | — | **adjudicate (예시 C)** | — |

아래 세 예시는 이 표의 굵은 셀들을 실제 코드로 보여준다.

---

## 3. 예시 A — deep-research (pipeline + reflect-then-revise)

### 도메인
임의의 주제에 대해 웹 검색을 팬아웃하고, 소스를 fetch하고, claim을 적대적으로 검증한 뒤, 인용된 보고서를 합성한다.

### 위상·기제 선택 근거
- **왜 pipeline인가**: 단계마다 **의존하는 입력의 종류가 다르고 순서가 본질적**이다. gather가 후보 claim/source를 만들어야 fetch가 그것을 grounding하고, fetch가 정리해야 verify가 검증하고, verify가 통과시켜야 synthesize가 인용한다. 병렬화할 여지가 없다 — 각 단계가 직전 단계의 산출에 전적으로 의존한다. 그래서 dispatch(병렬)나 producer-reviewer(루프)가 아니라 **pipeline**이다.
- **왜 verify 노드에만 reflect-then-revise인가**: 4단계 중 사실 검증만이 **적대적 자기교정**을 필요로 한다. gather/fetch/synthesize는 단일 패스로 충분하지만, claim의 사실성은 한 번 써놓고 끝낼 수 없다 — 누군가 결함을 지적하고 누군가 고쳐야 한다. 그래서 그 한 노드에만 `reflect-then-revise(max_rounds=2, critic=opus)`를 끼운다. 위상은 pipeline 그대로, 기제만 그 노드에서 교체된다 (직교성의 실증).

### 노드·에이전트 분해

| node id | agent | model | rationale (frontmatter) | mechanism | on_exhaust |
|---------|-------|-------|-------------------------|-----------|-----------|
| `gather` | researcher | haiku | "순수 웹검색+claim 초안, 교차판단 없음 — 최저 티어" | single | proceed-with-gap |
| `fetch` | fetcher | haiku | "소스 fetch+claim-소스 grounding, 합성 없음 — 최저 티어" | single | proceed-with-gap |
| `verify` | verifier | sonnet | "Reviser 기본 티어; critic 패스는 mechanism_params로 opus 호출" | reflect-then-revise | proceed-with-gap |
| `synthesize` | synthesizer | opus | "교차소스 합성+검증 claim 위 판단 — 최고 티어" | single | escalate |

**model 티어가 역할을 따른다** (model-tier-policy.js): gather/fetch는 단순 수집(haiku), verify는 voter/reviser급(sonnet)이되 critic 패스만 opus로 끌어올림, synthesize는 합성 판단(opus). 원본의 "모든 에이전트 opus" 대신 **역할→티어 정책**이 적용된다.

**reflect-then-revise의 두 패스가 한 agentType에 산다** — verifier.md 하나가 critic 패스(opus, `S.verify_critique` 반환)와 reviser 패스(sonnet, `S.verify_schema` 반환)를 모두 담는다. 프롬프트가 어느 패스인지 고정하고, `approved=true`면 그 라운드에서 루프가 끊긴다.

### graph.json 발췌 (실제)

```json
{
  "schema_version": "0.1",
  "harness_name": "deep-research",
  "harness_version": "0.1.0",
  "execution_mode": "workflow",
  "topology": "pipeline",
  "budget": { "total_tokens": 600000, "approval_required": true },
  "nodes": [
    {
      "id": "gather", "agent": "researcher", "model": "haiku", "decision_mechanism": "single",
      "mechanism_params": {},
      "inputs": ["_workspace/00_input/query.md"],
      "outputs": ["_workspace/01_gather/findings.json"],
      "write_paths": ["_workspace/01_gather/"],
      "output_schema": "schemas/findings.json",
      "retries": 1, "on_exhaust": "proceed-with-gap", "max_rounds": 1
    },
    {
      "id": "verify", "agent": "verifier", "model": "sonnet", "decision_mechanism": "reflect-then-revise",
      "mechanism_params": { "max_rounds": 2, "critic": "opus" },
      "inputs": ["_workspace/02_fetch/findings.json"],
      "outputs": ["_workspace/03_verify/findings.json"],
      "write_paths": ["_workspace/03_verify/"],
      "output_schema": "schemas/findings.json",
      "retries": 0, "on_exhaust": "proceed-with-gap", "max_rounds": 2
    },
    {
      "id": "synthesize", "agent": "synthesizer", "model": "opus", "decision_mechanism": "single",
      "mechanism_params": {},
      "inputs": ["_workspace/03_verify/findings.json"],
      "outputs": ["_workspace/04_report/report.json"],
      "write_paths": ["_workspace/04_report/"],
      "output_schema": "schemas/report.json",
      "retries": 0, "on_exhaust": "escalate", "max_rounds": 1
    }
  ],
  "edges": [
    { "from": "gather", "to": "fetch" },
    { "from": "fetch", "to": "verify" },
    { "from": "verify", "to": "synthesize" }
  ]
}
```
(`fetch` 노드는 지면상 생략 — gather와 동형이다. 전체는 `examples/deep-research/.harness/graph.json`.)

### 읽어야 할 디테일
- `edges`는 순서일 뿐 의존이 아니다. 의존(어떤 파일을 읽나)은 `inputs[]`가 표현한다 — verify의 input은 `02_fetch/findings.json`이지 "fetch 노드"가 아니다.
- `write_paths`가 노드마다 분리(`01_gather/`, `03_verify/`…)되어 validate의 write-path 중복 검사를 통과한다. SOT 안전 원칙의 기계적 강제다.
- 출력 노드(synthesize)의 `on_exhaust: escalate` — 최종 산출 실패는 gap으로 넘기지 않고 사람에게 올린다. 중간 노드는 `proceed-with-gap`로 약점을 안고 진행.

---

## 4. 예시 B — ticket-triage (dispatch + majority-vote)

### 도메인
지원 티켓 하나를 받아 카테고리와 우선순위를 동시에 판정하고, 두 결과를 합쳐 큐·SLA로 라우팅한다.

### 위상·기제 선택 근거
- **왜 dispatch인가**: 카테고리 분류와 우선순위 판정은 **서로 독립적**이다 — category를 모른 채 priority를 정할 수 있고 그 역도 성립. 두 판단이 병렬로 fan-out하고, 단일 sink(route)로 fan-in한다. 이것이 dispatch(static)의 정의다. pipeline이면 둘을 인위적으로 직렬화해 느려지고, producer-reviewer는 루프가 필요 없는 이 작업에 과하다.
- **왜 두 source 노드에 majority-vote인가**: "이 티켓이 bug냐 feature_request냐", "P1이냐 P2냐"는 **경계가 모호한 주관 판단**이다. 단일 에이전트는 흔들린다. 그래서 각 분류를 `majority-vote(n=3, quorum=2, tie_break=first)`로 — 3개 독립 ballot을 JS가 집계해 표결로 안정화한다. sink 노드(route)는 결정이 아니라 **결정론적 병합**이므로 `single`로 충분하다 (기제를 노드마다 다르게 줄 수 있음의 실증).

### 노드·에이전트 분해

| node id | agent | model | rationale | mechanism | params |
|---------|-------|-------|-----------|-----------|--------|
| `classify_category` | classifier | sonnet | "모호한 티켓을 한 카테고리로 판단하는 독립 voter — voter 기본 티어" | majority-vote | n=3, quorum=2, tie_break=first |
| `classify_priority` | prioritizer | sonnet | "영향+긴급을 한 심각도로 종합하는 독립 voter — voter 기본 티어" | majority-vote | n=3, quorum=2, tie_break=first |
| `route` | router | haiku | "두 상류 승자를 큐/SLA로 결정론 병합 — format급, 최저 티어" | single | {} |

**voter는 sonnet, sink format은 haiku.** 정책 그대로다 (voter→sonnet, format→haiku). 원본이라면 셋 다 opus였을 자리에 역할 티어가 들어간다.

**독립성이 agent 본문에 박혀 있다** — classifier.md: "독립 투표다. 다른 ballot을 가정하거나 합의를 노리지 않는다." majority-vote는 ballot 간 통신이 **없어야** 작동한다(Mode-A에서 자연스럽게 보장 — 병렬 호출이 서로 못 본다). sink router.md: "두 majority-vote 승자가 `[classification, priority]` 배열로 fan-in한다; 재판단 없이 병합만."

### graph.json 발췌 (실제)

```json
{
  "schema_version": "0.1",
  "harness_name": "ticket-triage",
  "execution_mode": "workflow",
  "topology": "dispatch",
  "budget": { "total_tokens": 120000, "approval_required": true },
  "nodes": [
    {
      "id": "classify_category", "agent": "classifier", "model": "sonnet",
      "decision_mechanism": "majority-vote",
      "mechanism_params": { "n": 3, "quorum": 2, "tie_break": "first" },
      "inputs": ["_workspace/00_input/ticket.md"],
      "outputs": ["_workspace/01_category/classification.json"],
      "write_paths": ["_workspace/01_category/"],
      "output_schema": "schemas/classification.json",
      "retries": 1, "on_exhaust": "proceed-with-gap", "max_rounds": 1
    },
    {
      "id": "classify_priority", "agent": "prioritizer", "model": "sonnet",
      "decision_mechanism": "majority-vote",
      "mechanism_params": { "n": 3, "quorum": 2, "tie_break": "first" },
      "inputs": ["_workspace/00_input/ticket.md"],
      "outputs": ["_workspace/02_priority/priority.json"],
      "write_paths": ["_workspace/02_priority/"],
      "output_schema": "schemas/priority.json",
      "retries": 1, "on_exhaust": "proceed-with-gap", "max_rounds": 1
    },
    {
      "id": "route", "agent": "router", "model": "haiku", "decision_mechanism": "single",
      "mechanism_params": {},
      "inputs": ["_workspace/01_category/classification.json", "_workspace/02_priority/priority.json"],
      "outputs": ["_workspace/03_route/routing.json"],
      "write_paths": ["_workspace/03_route/"],
      "output_schema": "schemas/routing.json",
      "retries": 0, "on_exhaust": "escalate", "max_rounds": 1
    }
  ],
  "edges": [
    { "from": "classify_category", "to": "route" },
    { "from": "classify_priority", "to": "route" }
  ]
}
```

### 읽어야 할 디테일
- **두 source가 같은 input**(`00_input/ticket.md`)을 읽고 **서로 다른 output**에 쓴다 — fan-out의 전형. 두 edge가 모두 `route`로 들어가 fan-in.
- route의 `inputs[]`가 **두 개**다. agent 본문은 이것이 `[classification, priority]` 순서의 배열로 전달된다고 명시 — 순서가 계약이다.
- budget이 120k로 작다 — 분류는 짧은 작업. budget은 도메인 규모에 맞춰 잡는다 (deep-research 600k와 대비).
- route의 `on_exhaust: escalate` — 라우팅 실패는 티켓이 미아가 되는 것이므로 사람에게. 단, 한쪽 source가 gap이면 router가 안전 기본값(other→triage_backlog, P3→72h)으로 채운다 (agent 본문에 명시).

> **dynamic dispatch는?** 이 예시는 static fan-out(노드 수 고정). 작업 수가 런타임에 정해지는 경우(예: "파일 N개 마이그레이션")는 dynamic dispatch — supervisor가 claim 기반으로 동적 분배. 원본 감독자 패턴이 여기 매핑된다. 단, 동적 claim/supervisor가 실시간 상호통신을 요구하면 Mode-B 후보가 된다(§8).

---

## 5. 예시 C — design-decision (producer-reviewer + debate-with-judge)

### 도메인
기술 설계 결정(아키텍처 선택 등)에 대해 후보안을 제안하고, 적대적 토론으로 검증한 뒤, 미해결 우려가 있으면 재제안하는 경계 루프.

### 위상·기제 선택 근거
- **왜 producer-reviewer인가**: 좋은 설계 결정은 **생성과 비판의 왕복**에서 나온다. proposer가 안을 내면 adjudicate가 흔들고, 결함이 남으면 proposer가 그 concern을 안고 다시 낸다. 이 생성↔검증 경계 루프가 producer-reviewer의 정의다. pipeline은 한 방향이라 재제안을 표현 못 하고, dispatch는 병렬이라 변증법적 왕복이 없다.
- **왜 adjudicate 노드에 debate-with-judge인가**: 설계 채택은 **단일 검토자의 의견보다 양측 변론 후 심판**이 강하다. 추천안을 옹호하는 측(k=0)과 최강 대안을 미는 측(k=1)이 끝까지 다투고, opus judge가 transcript를 근거로 `chosen`+`approved`를 결정한다. 그래서 `debate-with-judge(n=2, max_rounds=2, judge=opus)`. reflect-then-revise(자기교정)보다 **대립 구조**가 설계 비교에 적합하다.
- **두 기제가 한 노드에 중첩**: producer-reviewer 루프의 reviewer 자리(adjudicate)가 그 안에서 debate-with-judge를 돌린다. 위상의 루프 종료 조건이 곧 기제의 산출(`verdict.approved`)이다 — 축의 조합이 가장 깊게 드러나는 예시.

### 노드·에이전트 분해

| node id | agent | model | rationale | mechanism | params |
|---------|-------|-------|-----------|-----------|--------|
| `propose` | proposer | opus | "경쟁 설계 위의 아키텍처급 판단 — 최고 티어" | single | max_rounds=3 |
| `adjudicate` | debater | sonnet | "Debater 기본 티어; judge 패스는 mechanism_params로 opus 호출" | debate-with-judge | n=2, max_rounds=2, judge=opus |

**debate-with-judge의 두 패스 종류가 한 agentType에 산다** — debater.md 하나가 debater 턴(sonnet, 자유 서술 변론, k=0/k=1)과 judge 패스(opus, `S.adjudicate_schema` 반환)를 모두 담는다. judge.md는 **사람이 읽는 그래프 뷰용 문서**일 뿐 실행 wiring은 debater agentType을 탄다 (verifier가 critic+reviser를 한 몸에 담는 것과 동형). 두 파일은 동기화 유지가 규칙.

### graph.json 발췌 (실제, 전체)

```json
{
  "schema_version": "0.1",
  "harness_name": "design-decision",
  "harness_version": "0.1.0",
  "execution_mode": "workflow",
  "topology": "producer-reviewer",
  "budget": { "total_tokens": 300000, "approval_required": true },
  "nodes": [
    {
      "id": "propose", "agent": "proposer", "model": "opus", "decision_mechanism": "single",
      "mechanism_params": {},
      "inputs": ["_workspace/00_input/decision.md"],
      "outputs": ["_workspace/01_propose/design.json"],
      "write_paths": ["_workspace/01_propose/"],
      "output_schema": "schemas/design.json",
      "retries": 0, "on_exhaust": "escalate", "max_rounds": 3
    },
    {
      "id": "adjudicate", "agent": "debater", "model": "sonnet",
      "decision_mechanism": "debate-with-judge",
      "mechanism_params": { "max_rounds": 2, "judge": "opus", "n": 2 },
      "inputs": ["_workspace/01_propose/design.json"],
      "outputs": ["_workspace/02_adjudicate/verdict.json"],
      "write_paths": ["_workspace/02_adjudicate/"],
      "output_schema": "schemas/verdict.json",
      "retries": 0, "on_exhaust": "proceed-with-gap", "max_rounds": 2
    }
  ],
  "edges": [
    { "from": "propose", "to": "adjudicate" }
  ]
}
```

### 읽어야 할 디테일
- **루프가 graph.json에 노드로 보이지 않는다.** producer-reviewer 위상이 propose↔adjudicate 왕복을 암시하고, propose의 `max_rounds=3`이 재제안 상한, adjudicate가 반환하는 `verdict.approved`가 종료 조건. 위상이 곧 제어 흐름이다.
- propose `on_exhaust: escalate`(producer 실패=사람), adjudicate `on_exhaust: proceed-with-gap`(합의 못 봐도 judge는 verdict를 내고 미해결분은 `concerns[]`로 넘김). agent 본문에 둘 다 명시.
- `chosen`은 반드시 `design.options[].name` 중 하나여야 한다 — judge가 입력에 없는 옵션을 만들면 루프 종료 판정이 깨진다 (agent 본문의 경계 조건).
- `approved=true ⟺ concerns=[]` 일관성 강제 — 한쪽만 채우면 루프 제어가 모순된다.

---

## 6. 세 예시 교차 비교 — 같은 원리, 다른 좌표

| | deep-research | ticket-triage | design-decision |
|--|--------------|---------------|-----------------|
| topology | pipeline | dispatch (static) | producer-reviewer |
| 핵심 기제 | reflect-then-revise (verify) | majority-vote (×2 source) | debate-with-judge (adjudicate) |
| 노드 수 | 4 | 3 | 2 |
| budget | 600k | 120k | 300k |
| 흐름 형태 | 직렬 사슬 | fan-out → sink | 경계 루프 |
| 최고 티어 위치 | synthesize(opus) + critic 패스 | 없음(voter=sonnet, sink=haiku) | propose(opus) + judge 패스 |
| 종료 조건 | 마지막 노드 | sink 완료 | verdict.approved |

**한 줄 진단법** — 새 도메인을 받으면 두 질문을 순서대로 던진다:
1. **데이터가 어떻게 흐르나?** 한 줄로 흐르면 pipeline, 갈라졌다 모이면 dispatch, 만들고-부수고-다시 만들면 producer-reviewer → **topology 결정**.
2. **각 판단점에서 신뢰가 어떻게 확보되나?** 한 번이면 single, 표결로 안정화면 majority-vote, 대립 변론이면 debate-with-judge, 자기교정이면 reflect-then-revise → **노드별 mechanism 결정**.

두 답이 곧 graph.json의 `topology`와 노드별 `decision_mechanism`이다. 나머지(model 티어·on_exhaust·schema)는 정책과 검증이 채운다.

---

## 7. 보존된 설계 지혜

원본의 패러다임은 바꿨지만, 패러다임과 무관한 설계 지혜는 그대로 가져온다. 이것이 보존해야 할 진짜 가치다.

### 7.1 에이전트 분할 기준 (4가지)
한 노드를 여러 에이전트로 쪼갤지의 판단:
- **전문성(expertise)**: 판단의 성격이 다른가? deep-research의 critic(결함 찾기)과 reviser(고치기)는 정반대 사고라 패스를 나눈다.
- **병렬성(parallelism)**: 독립 실행이 이득인가? ticket-triage의 category·priority는 독립이라 fan-out.
- **컨텍스트(context)**: 한 에이전트가 다 들면 컨텍스트가 터지나? 단계별 파일 SOT로 분리.
- **재사용(reuse)**: 다른 harness에서도 쓸 조각인가? reviewer·fact-checker·translator는 genome 공통 에이전트로 상속된다.

### 7.2 Pushy description = 트리거 메커니즘
agent frontmatter의 `description`은 설명이 아니라 **트리거**다. 실제 예시:
> classifier: "Use to classify a support ticket into ONE category. … Trigger keywords: classify ticket, categorize, 분류, 카테고리, 티켓 유형. Dispatch source node classify_category of the ticket-triage harness."

패턴: **Use [언제] + [무엇을] ONE [경계] + Trigger keywords(영/한) + [graph 내 좌표]**. "Use FIRST"(researcher/proposer), "Use LAST"(synthesizer/router) 같은 강한 동사가 라우팅을 끈다.

### 7.3 Why-not-ALWAYS 본문 원칙
agent 본문은 항상 지킬 것만 적는다. 추측성 분기·과잉 유연성 없음. classifier 본문이 "독립 투표다. 합의를 노리지 않는다"를 단정형으로 박는 것이 그 예 — 조건문이 아니라 불변 규칙.

### 7.4 Progressive disclosure
경량 본문 + 깊은 references. 각 agent.md는 핵심역할·작업원칙·입력/출력 프로토콜·에러핸들링 5섹션으로 짧게, 상세는 schema 파일과 genome 문서가 진다.

### 7.5 QA 경계 교차비교 + 7대 실버그 패턴
검증 노드(verify의 critic, adjudicate의 debater)는 **경계를 교차 점검**한다. 원본 코드리뷰 팀의 교차영역 통찰("이 SQL 주입은 성능에도 영향")을 CYS에서는 critic/debater 본문의 적대성 규칙으로 옮긴다 — "친절하지 말 것. 통과시키면 안 되는 것은 반드시 흔든다." 점검할 7대 실버그 패턴(미인용 claim, 과장, 오인용, enum 이탈, 입력에 없는 값 생성, 빈/비-JSON 반환, gap 미표기)은 각 agent의 에러핸들링에 박혀 있다.

### 7.6 with-skill vs without A/B + 트리거 near-miss 검증
harness 등록 전 `lift_gate.py`로 with-skill vs haiku-baseline을 **독립 블라인드 채점**해 register/refuse 결정. `h2h_suite`/`h2h_aggregate`로 n-run 중앙값 head-to-head. description은 트리거 near-miss(거의 맞지만 빗나가는 요청)로 오발동을 검증.

### 7.7 진화·피드백 루프 / 팀 크기
노드 수는 작게 시작(2~4). design-decision은 2노드로 충분하다 — 원본의 "팀 크기 가이드"는 CYS에서 "노드 최소화 + 기제로 깊이 확보"로 이어진다. 깊이가 필요하면 노드를 늘리지 말고 그 노드의 mechanism을 single→vote/debate/reflect로 올린다.

---

## 8. Mode-A가 기본, Mode-B는 예외

원본은 "에이전트 팀이 기본"이었다. **CYS는 뒤집는다.**

- **Mode-A (`execution_mode: "workflow"`, 기본)**: `emit_workflow.py`가 graph.json을 `.harness/workflow.js`로 컴파일. 결정론적 Workflow-tool 런타임 — `agent()`/`parallel()`/`pipeline()`, budget.total 하드 천장, `resumeFromRunId`, schema 강제 출력, **wall-clock·RNG 없음**. 위 세 예시 전부 Mode-A다.
- **Mode-B (`execution_mode: "team"`, 예외)**: 실시간 에이전트 간 통신이 **본질적일 때만**. 팀은 결정론적 스케줄이 불가능하다(플랫폼 한계) — 그래서 기본이 아니라 fallback이다. 원본 리서치/코드리뷰 팀의 SendMessage 교차통신이 정말 실시간이어야 하는 드문 경우에만.

> 판별: "에이전트들이 **서로의 중간 산출을 실시간으로 보며 조율**해야 하는가?" 아니오 → Mode-A(거의 항상). 예 → Mode-B 후보. deep-research의 "교차통신"은 사실 순차 grounding으로 충분하므로 Mode-A로 충분하다.

**런타임 라우팅(RUNTIME.json)**: canonical은 항상 `workflow.js`. 상속된 `prompt-runner/run.py`는 graph.json에 wired되지 않은 **대안 런타임**(장기 batch·human-in-the-loop용)일 뿐 graph를 도는 두 번째 길이 아니다. 한 작업을 두 런타임으로 돌리지 않는다.

---

## 9. 산출물 패턴 요약 — graph.json이 척추다

새 harness를 만들 때 생성하는 것:

```
<harness>/
├── .harness/
│   ├── graph.json          ← 척추. 가장 먼저, 손으로 작성. graph.schema.json으로 검증.
│   ├── workflow.js         ← emit_workflow.py가 graph.json에서 컴파일 (직접 수정 금지)
│   ├── GENOME.json / RUNTIME.json / MANIFEST.json / harness.lock  ← 도구 생성
├── .claude/agents/<agent>.md   ← 노드마다. model: + model_rationale: 필수 (frontmatter)
├── schemas/<name>.json         ← 노드 output_schema마다. JSON-Schema.
└── (genome 228파일 상속: hooks·4계층 품질게이트·보안·공통 에이전트·prompt 라이브러리)
```

작성 순서 (계약 우선):
1. **graph.json** — topology + 노드별 model·decision_mechanism·on_exhaust·schema 경로 결정.
2. **schemas/*.json** — 각 노드 출력의 JSON-Schema. graph가 가리키는 경로에.
3. **.claude/agents/*.md** — 노드마다. pushy description + 5섹션 본문 + `model`/`model_rationale`.
4. `inherit_genome.py`로 게놈 상속(자식이 부모의 전체 운영 기계 내장).
5. `python3 ../../validate_harness.py .` — 머신체크 세트 통과.
6. `warrant.py` — Phase -1 비용 게이트 승인.
7. `emit_workflow.py` → `Workflow({ scriptPath: ".harness/workflow.js", args: {...} })`로 실행.
8. `lift_gate.py`로 baseline 대비 lift 입증 → register.

> 핵심 전환: 원본은 "에이전트 파일을 쓰고 팀으로 조율"했다. CYS는 **graph.json 계약을 먼저 쓰고, 도구가 컴파일·검증·측정**한다. 에이전트는 계약에서 파생되는 부품이지 출발점이 아니다. 이 문서의 세 예시가 그 계약의 살아있는 형태다.
