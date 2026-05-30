> ⚠️ **구현 현황은 [`IMPLEMENTATION-STATUS.md`](IMPLEMENTATION-STATUS.md)가 우선한다.** 이 문서는 Stage 4(Phase-7 진화)와 두 층(Tier I/II) 메모리를 설명한다. 인용된 validate code(`EVOLUTION_WIRED`·`EVOLUTION_LOG_PRESENT`·`MEMORY_SKILL_SECTION`·`MEMORY_STORE_INIT`)·라우팅 테이블·파일 경로는 모두 `evolve_harness.py`·`inherit_genome.py`·`emit_orchestrator.py`·`validate_harness.py` 실측이며, 다른 reference의 aspirational 서술에 우선한다.

# 진화 & 메모리 가이드 (CYS)

> ⚠️ **런타임 모델 (PIVOT 이후).** 산출 하네스는 100% Claude Code 프리미티브(Agent / TeamCreate / SendMessage / TaskCreate) 위에서 **라이브 `claude` 세션**으로 돈다. 진화·메모리는 모두 그 세션 안에서 일어난다 — 오케스트레이터 SKILL의 프로즈 레시피가 발화시키고, 상속된 AWF 게놈 hook이 자동으로 스냅샷·복원을 수행하며, Python 가드(`evolve_harness.py`)는 *결정론 라우팅·append-only 기록*만 담당한다. Mode-A `workflow.js`는 제품에서 은퇴했다 — 진화·메모리 어디에도 `.js` 실행 경로는 없다.

> 출처: 원본 AgenticWorkflow의 "진화하는 하네스" + Context Preservation + RLM 메모리 설계를 CYS 패러다임으로 적응.

하네스는 **고정된 산출물이 아니라 살아 있는 시스템**이다. 한 번 만들어 끝내는 것이 아니라 (1) 매 실행 후 피드백을 받아 *정확히 어느 아티팩트를 고칠지* 결정론적으로 라우팅하고, (2) 세션을 넘어 맥락을 보존하며, (3) 실행을 거듭하며 도메인 지식을 외부 메모리에 누적한다. 이 문서는 그 세 가지 — **Phase-7 진화 루프**(Stage 4)와 **두 층 메모리**(Tier I / Tier II) — 를 다룬다.

원본은 이 지혜를 **프로즈 규약**(사람이 읽고 따르는 권고)으로 기술했다. CYS는 같은 설계를 **결정론 아티팩트 + 머신체크 게이트**로 바꾼다: 피드백 유형→대상은 고정 테이블, 변경 이력은 append-only `jsonl`, 메모리 시드는 idempotent 설치 — 그리고 그 존재를 `validate_harness.py`가 강제한다.

---

## 목차

1. [Phase-7 진화 루프 (Stage 4)](#1-phase-7-진화-루프-stage-4)
2. [피드백 유형 → 대상 라우팅 테이블](#2-피드백-유형--대상-라우팅-테이블)
3. [change-history.jsonl — append-only 회귀 가드](#3-change-historyjsonl--append-only-회귀-가드)
4. [선제 진화 (`--proactive`) & 유지보수 루프](#4-선제-진화---proactive--유지보수-루프)
5. [두 층 메모리 개요](#5-두-층-메모리-개요)
6. [Tier I — Context Preservation + RLM 지식 인덱스](#6-tier-i--context-preservation--rlm-지식-인덱스)
7. [Tier II — `.harness/memory/` 교차-실행 도메인 스토어](#7-tier-ii--harnessmemory-교차-실행-도메인-스토어)
8. [메모리 질의 규율 — Grep, never bulk-load](#8-메모리-질의-규율--grep-never-bulk-load)
9. [진화 ↔ 메모리 연결](#9-진화--메모리-연결)
10. [validate code 대응표](#10-validate-code-대응표)

---

## 1. Phase-7 진화 루프 (Stage 4)

idoforgod는 하네스를 **살아 있는 시스템**으로 다룬다: 매 실행 후 피드백을 묻고, 피드백 유형을 *정확히 고쳐야 할 아티팩트*로 라우팅하고, 그 변경을 CLAUDE.md 변경이력에 기록(회귀 가드)하고, 반복 신호가 보이면 진화를 선제 제안한다. idoforgod는 이 전부를 **프로즈**로 한다. CYS는 라우팅 + 이력을 **결정론 아티팩트**로 만든다.

진화 루프는 오케스트레이터 SKILL의 `## 진화` 섹션(emit_orchestrator의 Phase-7 프로즈)에서 발화하며, 라이브 세션의 매 실행 직후 5단계로 돈다:

```
실행 완료
   ↓
1. 피드백 수집     — 사용자에게 "개선점/팀 구성 변경점"을 1회 묻는다(강요 금지, 기회 제공)
   ↓
2. 피드백 라우팅   — evolve_harness.py . --type <유형> --change "..." --reason "..."
                     유형 → 대상 아티팩트 (고정 테이블) → .harness/change-history.jsonl append
   ↓
3. 변경 검증       — 라우팅된 수정 → 해당 Implementation 단계 재진입 → validate_harness.py 재통과 필수
                     (진화가 계약을 퇴행시키지 못함)
   ↓
4. 선제 진화       — evolve_harness.py . --proactive  (같은 유형 2회↑ 시 자동 제안)
   ↓
5. 유지보수        — audit_harness.py 재감사 → 드리프트 제시 → 한 번에 하나씩 수정 → 재검증 → CLAUDE.md 동기화
```

핵심은 **3단계의 강제 재검증**이다. 진화는 자유롭게 아티팩트를 바꿀 수 있지만, 라우팅된 수정은 *반드시* 해당 Implementation 단계로 재진입한 뒤 `validate_harness.py`를 다시 통과해야 한다. 진화가 계약(graph.json·티어·게놈·all-6)을 퇴행시키지 못하게 막는 잠금장치다.

> **A1 경계.** Python(`evolve_harness.py`)이 하는 일은 *유형→대상 매핑*과 *append-only 기록*뿐이다. "산출물 품질이 낮다"를 *어떻게* 고칠지(스킬 본문을 어떻게 다시 쓸지, 어느 agent를 추가할지)는 전부 프리미티브(사람/Agent)의 도메인 판단이다. Python은 결정론 가드레일만 잡는다.

---

## 2. 피드백 유형 → 대상 라우팅 테이블

진화의 핵심은 **"피드백을 받았는데 그래서 *무엇을* 고치지?"** 를 추측에 맡기지 않는다는 것이다. `evolve_harness.py`의 `_ROUTE` 테이블(고정 dict)이 피드백 유형을 정확한 아티팩트로 매핑한다. 알 수 없는 유형이 들어오면 `record()`가 `ValueError`로 거부한다(임의 유형 난립 방지).

| 피드백 유형 (`--type`) | 대상 아티팩트 (`target`) | 고치는 곳 |
|---|---|---|
| `result-quality` | `domain-skill-or-agent-body` | 그 노드의 *how* — 도메인 스킬 또는 agent 본문 |
| `agent-role` | `agent-def` | `.claude/agents/<agent>.md` (역할/추가) |
| `workflow-order` | `orchestrator` | 오케스트레이터 SKILL (워크플로우 순서) |
| `team-comp` | `orchestrator+agents` | 오케스트레이터 + agents (팀 구성/병합) |
| `trigger-miss` | `skill-description` | 스킬 description (트리거 누락) |

(출처: `evolve_harness.py:23` `_ROUTE`. 오케스트레이터 SKILL의 `## 진화` 2단계가 이 5줄을 그대로 옮겨 적는다 — `result-quality → 그 노드의 how`, `agent-role → .claude/agents/<agent>.md`, `workflow-order → 이 오케스트레이터 SKILL`, `team-comp → 오케스트레이터+agents`, `trigger-miss → 스킬 description`.)

CLI:

```bash
python3 ../../evolve_harness.py <harness_dir> --type result-quality \
    --change "findings 노드 스킬에 출처 신뢰도 가중을 추가" \
    --reason "사용자: 약한 출처가 강한 출처와 동급 취급됨"
# → recorded: result-quality -> domain-skill-or-agent-body (findings 노드 스킬에 ...)
```

`route_feedback(feedback_type)`는 알 수 없는 유형에 `None`을 반환하고, `record()`는 그때 `unknown feedback_type ... (expected one of [...])` 으로 raise한다 — 5종 외 유형은 기록 자체가 안 된다.

---

## 3. change-history.jsonl — append-only 회귀 가드

라우팅된 모든 변경은 `.harness/change-history.jsonl`에 **한 줄씩 추가**된다(append-only). idoforgod가 CLAUDE.md에 프로즈로 남기던 변경이력을, CYS는 머신체크 가능한 결정론 로그로 만든 것이다.

각 엔트리(`record()`가 쓰는 객체):

```json
{"date": "...", "feedback_type": "result-quality", "target": "domain-skill-or-agent-body", "change": "...", "reason": "..."}
```

**append-only 보장.** `record()`는 기존 파일 전체를 읽어(`prior`) 새 줄을 뒤에 붙인 뒤 `atomic_write`로 다시 쓴다 — 과거 엔트리를 절대 덮어쓰지 않는다. 디렉토리가 없으면 `.harness/`를 만들고 시작한다.

**머신체크 (`EVOLUTION_LOG_PRESENT`).** `change-history.jsonl`이 존재하면, `validate_harness.py`는 **모든 비어있지 않은 줄**이 (1) 유효 JSON이고 (2) `feedback_type`·`target`·`change` 키를 전부 가졌는지 검사한다. 한 줄이라도 깨지면 빌드 게이트가 막는다 — 진화 이력이 손상된 채로 출하될 수 없다. (출처: `validate_harness.py:276`.)

> 로그가 *없는* 것은 에러가 아니다(아직 진화하지 않은 신생 하네스). 게이트는 "있다면 잘 형성되어야 한다"를 강제하지, "반드시 있어야 한다"를 강제하지 않는다.

---

## 4. 선제 진화 (`--proactive`) & 유지보수 루프

### 선제 진화

같은 유형의 피드백이 반복되면, 사용자가 매번 명시적으로 요청하기 전에 하네스가 먼저 진화를 제안한다. `_PROACTIVE_THRESHOLD = 2` — **같은 `feedback_type`이 2회 이상** 누적되면 제안 대상이 된다.

```bash
python3 ../../evolve_harness.py <harness_dir> --proactive
# 반복 없음:  no recurring feedback (>= 2) — no evolution proposed.
# 반복 있음:  PROPOSE EVOLUTION: 'result-quality' seen 3x -> change domain-skill-or-agent-body
```

`proactive_proposals(history)`는 `change-history.jsonl`을 읽어 유형별 카운트를 세고, 임계 이상인 유형마다 `{feedback_type, count, target}` 제안을 낸다 — 무엇을 고칠지(target)까지 라우팅 테이블로 같이 알려준다. 즉 "이 유형 피드백이 자꾸 들어온다 → 그 아티팩트를 근본적으로 손볼 때다"를 데이터가 자동으로 짚어준다.

### 유지보수 루프 (5단계)

진화 루프의 마지막 단계는 **재감사 → 한 번에 하나씩 수정 → 재검증 → CLAUDE.md 동기화**다(오케스트레이터 `## 진화` 5단계):

1. **재감사** — `audit_harness.py`로 디스크 상태(실제 agents/skills)와 graph 계약을 set-diff하여 **결정론 드리프트**를 잡는다.
2. **드리프트 제시** — 발견된 드리프트를 사용자/오케스트레이터에게 제시한다.
3. **한 번에 하나씩 수정** — 여러 드리프트를 한꺼번에 뭉개지 않고 하나씩 고친다(변경 추적성 + 회귀 격리).
4. **재검증** — 각 수정 후 `validate_harness.py`를 재통과시킨다.
5. **CLAUDE.md 동기화** — 변경을 헌법 문서에 반영해 문서-실제 드리프트를 봉쇄한다.

---

## 5. 두 층 메모리 개요

산출 하네스의 메모리는 **두 층**으로 나뉜다. 둘은 시간 축이 다르다 — Tier I은 *한 작업의 세션들*을 잇고, Tier II는 *여러 작업(실행)*을 잇는다.

| | **Tier I — Context Preservation** | **Tier II — 교차-실행 도메인 스토어** |
|---|---|---|
| 위치 | `.claude/context-snapshots/` | `.harness/memory/` |
| 시간 축 | 세션 ↔ 세션 (한 작업 안) | 실행 ↔ 실행 (작업을 넘어) |
| 누가 채우나 | 상속 게놈 hook이 **자동** 발화 | 오케스트레이터가 완료 시 **명시적 기록** |
| 무엇을 보존 | 현재 작업·다음 단계·SOT·게이트 상태(IMMORTAL) / 세션별 error→resolution | 도메인 엔티티·관계·제약(DKS) / 표준 위험·결정 / 과거 산출물 |
| 질의 방식 | `[CONTEXT RECOVERY]` 시 `latest.md` Read / 인덱스는 Grep | `runs/index.jsonl` Grep → 매치된 run만 Read |
| validate | `HOOK_REGISTERED`(save_context) · `CONTEXT_PRESERVATION_FIRSTCLASS` | `MEMORY_STORE_INIT` · `MEMORY_SKILL_SECTION` |

두 층 모두 **RLM(외부 메모리) 패턴**을 공유한다: 메모리를 컨텍스트에 **통째로 로드하지 않는다.** 얇은 인덱스를 **Grep으로 질의**하고, 히트한 항목만 Read로 가져온다. 이것이 컨텍스트 윈도를 보호하면서 장기 기억을 가능케 하는 핵심 규율이다.

---

## 6. Tier I — Context Preservation + RLM 지식 인덱스

Tier I은 **한 작업이 여러 세션에 걸칠 때** 맥락을 잃지 않게 한다. 라이브 세션에서 상속된 AWF 게놈 hook이 **자동으로** 발화한다 — 오케스트레이터가 명시적으로 호출하지 않아도 된다.

### 세션 연속성 — 스냅샷 (`context_guard` / `save_context`)

토큰 초과·`/clear`·컨텍스트 압축·세션 종료 시, 게놈 hook(`context_guard.py` / `save_context.py`, `.claude/hooks/scripts/`에 상속됨)이 `.claude/context-snapshots/latest.md`에 스냅샷을 저장한다. **IMMORTAL 섹션**(현재 작업·다음 단계·SOT·품질게이트 상태)은 컨텍스트 압축에서도 우선 보존된다.

새 세션 시작 시 `[CONTEXT RECOVERY]` 메시지가 뜨면, 오케스트레이터는 **반드시** 안내된 `latest.md`를 Read로 읽어 맥락을 복원한 뒤 진행한다. 작업 시작 시에는 SOT(`.harness/state.yaml`) + `latest.md`를 같이 읽어 현재 단계·산출물·예산을 복원한다.

(`save_context`는 `HOOK_REGISTERED`에 등록되며 — IMPLEMENTATION-STATUS M1 — 오케스트레이터의 `## 메모리 운영`(Tier I) 섹션이 일급 기능으로 emit된다: `CONTEXT_PRESERVATION_FIRSTCLASS`.)

### 교차세션 지식 — RLM 지식 인덱스

`.claude/context-snapshots/knowledge-index.jsonl`은 **세션별 작업·수정파일·error→resolution을 누적한 외부 메모리**다. RLM 패턴 그대로: **통째로 로드하지 말고 Grep으로 질의**한다.

```bash
Grep "<주제>" .claude/context-snapshots/knowledge-index.jsonl
```

과거의 error→resolution은 `SessionStart` 시 자동으로 표시되어, 같은 실수를 반복하지 않게 돕는다.

---

## 7. Tier II — `.harness/memory/` 교차-실행 도메인 스토어

Tier II는 **하네스가 *반복 실행*을 거치며 도메인 지식을 누적**하는 RLM 외부 환경이다(M6 / RLM 패턴). Tier I이 한 작업의 세션을 잇는다면, Tier II는 *여러 실행*을 가로질러 도메인 지식이 쌓이게 한다.

### 시드 구조 (`inherit_genome._init_memory_store`)

게놈 상속 시 `_init_memory_store(harness_dir)`가 `.harness/memory/` 스토어를 시드한다 — **idempotent**: 이미 있는 누적 run/지식을 절대 덮어쓰지 않고 *없는 시드 파일만* 만든다(재emit이 기존 메모리를 파괴하지 않음). 구조:

```
.harness/memory/
├── archive.manifest.json    # 스토어 명세 + query_recipe (RLM 사용법 자기기술)
├── domain-knowledge.yaml    # IMMORTAL DKS: entities/relations/constraints (재실행마다 L1 검증 기준으로 주입)
├── runs/
│   └── index.jsonl          # 얇은 append-only 프로브 — run당 1줄. Grep한 뒤 매치된 runs/<id>/만 Read
└── risk/
    └── decisions.jsonl      # IMMORTAL 표준 결정/위험 (예: "출처 X는 절대 쓰지 않는다")
```

- **`archive.manifest.json`** — 스토어 자체의 사용법을 담은 명세(`schema_version`·`purpose`·`sections`·`query_recipe`). `query_recipe`가 "Grep index → hit일 때만 Read run" 패턴을 못박는다.
- **`domain-knowledge.yaml`** — 도메인의 IMMORTAL 지식(엔티티/관계/제약). 시드는 빈 골격(`entities: {}` / `relations: []` / `constraints: []`)으로 시작해 실행마다 새 사실이 병합된다.
- **`runs/index.jsonl`** — run당 한 줄짜리 *얇은 프로브*. 빈 파일로 시드되고 완료 시마다 1줄 append.
- **`risk/decisions.jsonl`** — 실행을 넘어 유효한 표준 위험/결정.

### 회상 → 검증 → 기록 (오케스트레이터 `## 메모리 운영` Tier II 레시피)

오케스트레이터 SKILL의 메모리 섹션이 Tier-II 사용 레시피를 emit한다 — 세 박자다:

1. **작업 시작 시 회상.** `Grep "<정규화 query 토큰>" .harness/memory/runs/index.jsonl`로 과거 유사 실행을 찾고, **매치된 run만** `Read .harness/memory/runs/<run_id>/`로 가져온다(결과가 많으면 `Agent`로 스니펫을 재귀 분해). `domain-knowledge.yaml`을 읽어 L1 검증 기준으로 주입하고, `risk/decisions.jsonl`로 금기를 확인한다.
2. **재사용 전 검증 (recall-verify-before-reuse).** 회상된 과거 산출물은 **맹신하지 않는다.** 현재 `domain-knowledge.yaml`에 대해 재검증한 뒤 사용하며, provenance·recency에 가중을 둔다. (메모리가 stale일 수 있으므로 — 과거 사실이 지금도 참인지 확인.)
3. **완료 시 기록 (단일쓰기 = 오케스트레이터).** `runs/index.jsonl`에 1줄 추가(`{run_id, ts, query_norm, topology, final_status, outputs[+sha256], sources, tags}`) + `runs/<run_id>/`에 산출물·출처·결정 저장 + 새 사실을 `domain-knowledge.yaml`에 병합(중복제거) + 표준 위험을 `risk/decisions.jsonl`에 추가.

### 머신체크 (`MEMORY_STORE_INIT`)

게놈이 상속된 하네스(=`.claude/settings.json` 존재)는 Tier-II 스토어가 시드되어 있어야 한다. `validate_harness.py:294`는 `.harness/memory/`에 `archive.manifest.json`·`domain-knowledge.yaml`·`runs/index.jsonl` 세 파일이 존재하는지 검사한다 — 하나라도 없으면 `MEMORY_STORE_INIT` 에러. (게놈 없는 minimal/비상속 fixture는 면제 — settings.json 게이트로 분기.)

---

## 8. 메모리 질의 규율 — Grep, never bulk-load

두 층 메모리를 관통하는 **단 하나의 규율**: 메모리를 컨텍스트에 **통째로 로드하지 않는다.** 얇은 인덱스를 **프로그램적으로(Grep) 질의**하고, 매치된 항목만 Read로 가져온다. 이것이 RLM(Retrieval-augmented Long-term Memory) 패턴이다.

```
            ┌─────────────────────────────────────────────┐
            │  ❌ runs/index.jsonl 전체를 Read → 컨텍스트 폭발  │
            └─────────────────────────────────────────────┘
                              vs
   ✅  Grep "<query 토큰>" .harness/memory/runs/index.jsonl   ← 얇은 인덱스만 스캔
       → hit한 run_id만  Read .harness/memory/runs/<run_id>/  ← 매치만 가져옴
       → 너무 많으면  Agent로 스니펫 재귀 분해
```

- **Tier I**: `Grep "<주제>" .claude/context-snapshots/knowledge-index.jsonl`
- **Tier II**: `Grep "<query 토큰>" .harness/memory/runs/index.jsonl` → 매치된 `runs/<id>/`만 Read

`runs/index.jsonl`이 *run당 한 줄*인 것은 우연이 아니다 — 인덱스를 의도적으로 얇게 유지해 Grep 한 번이 싸게 끝나게 하고, 무거운 산출물은 `runs/<id>/` 디렉토리로 분리해 hit일 때만 읽도록 설계한 것이다.

**머신체크 (`MEMORY_SKILL_SECTION`).** 오케스트레이터 SKILL은 이 Tier-II 회상+기록 레시피를 반드시 선언해야 한다. `validate_harness.py:499`는 SKILL 본문에 `교차-실행 도메인 메모리`와 `runs/index.jsonl`이 모두 있는지 검사한다 — 없으면 에러. 즉 "Grep으로 질의하라, 통째 로드 금지" 규율이 산출물에 박혀 있음을 게이트가 보증한다.

---

## 9. 진화 ↔ 메모리 연결

진화와 메모리는 독립 기능이 아니라 **하나의 피드백 사이클**이다. Tier II 메모리가 진화에 데이터를 공급한다:

```
실행 N  ─┐
         ├─► Tier II: runs/index.jsonl에 결과·status·tags 기록 → 도메인 지식 누적
         │
         ├─► 피드백 수집 → evolve_harness 라우팅 → change-history.jsonl
         │                                              │
실행 N+1 ◄┤   회상: Grep index → 과거 산출물·DKS·위험 주입 (recall-verify-before-reuse)
         │   진화: --proactive → 같은 유형 2회↑면 자동 제안 (반복 신호 = 근본 수정 시점)
         └─►
```

- **메모리가 진화를 먹인다.** `runs/index.jsonl`의 `final_status`·`tags`와 `change-history.jsonl`의 반복 유형이 합쳐져, 어느 아티팩트가 자꾸 문제를 내는지를 드러낸다. `--proactive`의 *같은 유형 2회↑* 신호가 그 데이터에서 나온다.
- **진화가 메모리를 정제한다.** 라우팅된 수정(예: `result-quality → 도메인 스킬 개선`)은 다음 실행의 회상 품질을 끌어올린다 — 개선된 스킬이 더 나은 산출물을 `runs/<id>/`에 남기고, 그것이 다시 회상된다.
- **두 append-only 로그.** `change-history.jsonl`(진화 이력)과 `runs/index.jsonl`(실행 이력)은 둘 다 파괴 없이 누적되며, 각각 `EVOLUTION_LOG_PRESENT`·`MEMORY_STORE_INIT`가 무결성을 강제한다.

---

## 10. validate code 대응표

진화·메모리의 모든 핵심 속성은 빌드 게이트(`validate_harness.py`)가 강제한다 — 프로즈 권고가 아니라 exit-code다.

| validate code | 무엇을 강제 | 트리거 조건 / 위치 |
|---|---|---|
| `EVOLUTION_WIRED` | 오케스트레이터 SKILL이 Phase-7 진화 섹션을 carry — 본문에 `진화` + `evolve_harness`가 둘 다 있어야 함 | SKILL 존재 시 (`validate_harness.py:494`) |
| `EVOLUTION_LOG_PRESENT` | `change-history.jsonl`이 있으면 모든 줄이 유효 JSON + `feedback_type`·`target`·`change` 키 보유 | 로그 존재 시 (`:276`) |
| `MEMORY_SKILL_SECTION` | 오케스트레이터 SKILL이 Tier-II 회상+기록 레시피 선언 — `교차-실행 도메인 메모리` + `runs/index.jsonl` 둘 다 | SKILL 존재 시 (`:499`) |
| `MEMORY_STORE_INIT` | `.harness/memory/`에 `archive.manifest.json`·`domain-knowledge.yaml`·`runs/index.jsonl` 시드됨 | `.claude/settings.json` 존재(게놈 상속) 시 (`:294`) |

> 관련: `CONTEXT_PRESERVATION_FIRSTCLASS`(오케스트레이터가 `## 메모리 운영` Tier I 섹션을 emit) + `HOOK_REGISTERED`(`save_context` 등록)는 Tier I을 일급화한다 — IMPLEMENTATION-STATUS M1.

---

### 한눈 요약

- **진화 = 결정론 라우팅 + append-only 이력.** 피드백 유형 5종이 `_ROUTE` 테이블로 정확한 아티팩트에 매핑되고, `change-history.jsonl`에 파괴 없이 쌓이며, 라우팅된 수정은 `validate_harness.py` 재통과 필수. `--proactive`가 같은 유형 2회↑에 진화를 선제 제안.
- **메모리 = 두 층 RLM.** Tier I(`.claude/context-snapshots/`)은 게놈 hook이 세션을 자동으로 잇고, Tier II(`.harness/memory/`)는 오케스트레이터가 실행을 넘어 도메인 지식을 명시적으로 누적. 둘 다 **Grep으로 질의(통째 로드 금지)**, 재사용 전 검증.
- **모두 머신체크.** 4개 validate code가 진화·메모리의 존재와 무결성을 빌드 게이트로 강제 — 프로즈가 아니라 exit-code.
