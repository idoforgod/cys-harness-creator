> ⚠️ **구현 현황은 [`IMPLEMENTATION-STATUS.md`](IMPLEMENTATION-STATUS.md)가 우선한다.** 이 문서의 설계 서술이 코드와 충돌하면 코드(그리고 그것을 요약한 IMPLEMENTATION-STATUS)가 정답이다. `.claude/commands` 비우기 규칙(`NO_COMMANDS`)은 폐기됐다.

# 하네스 테스트 & 측정 가이드 (CYS)

> ⚠️ **PIVOT (2026-05-29) — 제품 런타임은 100% Claude Code 프리미티브다.** 생성된 하네스는 **오케스트레이터 SKILL**이 `Agent`/`TeamCreate`/`TaskCreate`/`SendMessage`로 구동하는 프리미티브 기질 위에서 돈다. Mode-A `workflow.js`는 **제품에서 은퇴**(`WORKFLOW_RETIRED`)했고, **공장내부 측정 도구로만 생존**한다(`emit_workflow.py`·`h2h_suite.workflow.js`·`lift_probe.workflow.js`). 측정 인프라(warrant·validate·lift·h2h)는 substrate-무관하게 그대로지만, (1) Gate 3 h2h는 이제 byte-결정론이 아니라 **통계적(n≥5) 측정**이고, (2) 인용된 모든 h2h/lift 수치는 `evals/*.verdict.json`(디스크)과 일치해야 하며 `validate_harness.py` `MEASUREMENT_DRIFT`가 강제한다(stale 수치 차단). 구현 현황은 `IMPLEMENTATION-STATUS.md` 우선.

> 출처: 원본 `skill-testing-guide.md`을 CYS 패러다임으로 적응.

생성한 하네스의 품질을 **머신체크 게이트**와 **블라인드 측정**으로 검증·등록·반복 개선하는 방법론. SKILL.md Phase 5~7의 보충 레퍼런스.

원본은 테스트 방법론을 **prose 규칙**(사람이 읽고 따르는 권고)으로 기술했다. CYS는 같은 설계 지혜를 **실행 가능한·강제되는 게이트**로 바꾼다. 이 문서의 핵심 메시지: *원본의 "구조를 검증하라 / A·B로 비교하라 / 트리거를 점검하라"는 모두 옳다 — 다만 CYS에서는 그것이 산문이 아니라 `python3`로 돌아가는 exit-code다.*

---

## 목차

1. [측정 프레임워크 개요 — 4개 게이트](#1-측정-프레임워크-개요--4개-게이트)
2. [Gate 0: warrant.py — Phase -1 정당성 + 비용 사전승인(dry-run)](#2-gate-0-warrantpy--phase--1-정당성--비용-사전승인dry-run)
3. [Gate 1: validate_harness.py — 정적 빌드 게이트 (구조 검증의 실행화)](#3-gate-1-validate_harnesspy--정적-빌드-게이트-구조-검증의-실행화)
4. [Gate 2: lift_gate.py — with-skill vs haiku-baseline 리프트 (등록/거부)](#4-gate-2-lift_gatepy--with-skill-vs-haiku-baseline-리프트-등록거부)
5. [Gate 3: h2h_suite + h2h_aggregate — n-run 중앙값 헤드투헤드](#5-gate-3-h2h_suite--h2h_aggregate--n-run-중앙값-헤드투헤드)
6. [빌드레벨 parity 평가 — eval_topology.py (8 use case)](#6-빌드레벨-parity-평가--eval_topologypy-8-use-case)
7. [테스트 프롬프트 & assertion 작성법 (보존된 원본 지혜)](#7-테스트-프롬프트--assertion-작성법-보존된-원본-지혜)
8. [블라인드 독립 채점자 규율 (자기채점 금지)](#8-블라인드-독립-채점자-규율-자기채점-금지)
9. [Description 트리거 검증 — near-miss 중심](#9-description-트리거-검증--near-miss-중심)
10. [반복 개선 루프 & 진화 피드백](#10-반복-개선-루프--진화-피드백)
11. [워크스페이스 & provenance 구조](#11-워크스페이스--provenance-구조)
12. [원본 prose → CYS 게이트 대응표](#12-원본-prose--cys-게이트-대응표)

---

## 1. 측정 프레임워크 개요 — 4개 게이트

하네스 품질 검증은 **순차적으로 통과해야 하는 4개의 실행 게이트**다. 각 게이트는 사람의 판단이 아니라 **exit code**를 낸다. 앞 게이트를 통과하지 못하면 뒤로 넘어가지 않는다.

| 게이트 | 도구 | 언제 | 무엇을 측정 | 통과 신호 |
|--------|------|------|------------|-----------|
| **Gate 0 — 정당성·비용** | `warrant.py` | Phase -1, Phase 6 | "하네스가 필요한가" + 토큰 cost-band | 분류 verdict + 사용자 승인 |
| **Gate 1 — 정적 빌드** | `validate_harness.py` | Phase 5 | 구조·계약·티어·게놈·프리미티브 머신체크 세트 | `exit 0` (error 0건) |
| **Gate 2 — 리프트 등록** | `lift_gate.py` | Phase 7 (등록 전) | with-skill(sonnet) vs haiku baseline lift ≥ 0.2 | `register` (exit 0) |
| **Gate 3 — 헤드투헤드** | `h2h_suite` + `h2h_aggregate.py` | Phase 7 (선택, 엄밀) | C2(CYS) vs C3(no-harness) n-run 중앙값 delta ≥ 15pp | `CYS-WINS` |

원본의 핵심 루프(**작성 → 테스트 → 평가 → 개선 → 재테스트**)는 그대로다. 바뀐 것은 "평가"가 사람의 눈 검토가 아니라 위 4개 게이트의 자동 판정이라는 점이다.

```
Phase -1   Gate 0  warrant.classify    → 하네스 만들 가치 있나?
   ↓
Phase 1-4  (graph.json + agents + schemas + 오케스트레이터 SKILL emit)
   ↓
Phase 5    Gate 1  validate_harness    → 구조가 계약을 지키나?   [BLOCKING]
   ↓
Phase 6    Gate 0  warrant.cost_band   → 비용 승인              [BLOCKING]
   ↓
Phase 7    Gate 2  lift_gate           → baseline을 이기나? 등록 자격?
           Gate 3  h2h_suite/aggregate → 엄밀한 우위 입증 (선택)
```

> **정성 vs 정량의 재배치.** 원본은 "정성적 평가(사람 리뷰) + 정량적 평가(assertion 자동채점)"의 조합이라 했다. CYS에서 *정량 채점은 전부 게이트로 자동화*되고, *정성 판단은 채점자를 모델 에이전트로 격상*시켜 블라인드로 만든다(§8). 즉 "사람이 본다"는 측정 경로에서 빠지고, 사람은 게이트 결과를 보고 **개선 의사결정**을 내린다.

> **측정 런타임은 어디 있나 — 제품과 분리.** Gate 2/3의 probe·suite(`lift_probe.workflow.js`·`h2h_suite.workflow.js`)는 Mode-A `workflow.js` 포맷의 **공장내부 측정 도구**다. 생성된(제품) 하네스 안에는 들어가지 않는다 — 제품은 오케스트레이터 SKILL + 프리미티브로만 돈다(`WORKFLOW_RETIRED`가 produced child의 `.harness/workflow.js`를 빌드 실패로 막는다). 이 도구들은 "프리미티브 하네스가 baseline을 이기는가"를 *측정*하기 위해서만 공장에서 실행된다.

---

## 2. Gate 0: warrant.py — Phase -1 정당성 + 비용 사전승인(dry-run)

원본에는 "이 스킬을 만들 가치가 있나"를 시작 전에 강제하는 단계가 없었다. CYS는 이것을 **Phase -1 정당성 게이트**로 만들고, 동시에 **dry-run 비용 사전승인**까지 담당한다. 코드를 한 줄도 실행하지 않고(NO agent calls, NO wall-clock/RNG) verdict와 토큰 추정을 낸다 — 그래서 무료·반복가능·resume-safe다.

### 2-1. 정당성 분류 (Phase -1)

사용자 요청에서 5개 술어를 추출해 JSON으로 넘기면 verdict가 나온다.

```bash
python3 "$TR"/warrant.py --predicates <TARGET>/.harness/predicates.json
```

5개 술어:
```json
{
  "distinct_expertise_domains": 4,
  "has_dependent_or_parallel_stages": true,
  "will_be_rerun": true,
  "output_objective": true,
  "noisy": true
}
```

verdict 3분기:
- `answer-directly` — 1도메인·원자적·재실행X·noise X·객관적 → 하네스가 사주는 게 없다. **종료.**
- `single-agent` — 1도메인·원자적이지만 재실행/noisy/주관적 → 전용 단일 패스 1회. **종료.**
- `build-harness(topology, decision_mechanism, n_agents)` → Phase 0 진행. **이 verdict가 topology·mechanism 초안까지 제안한다.**

분류 로직이 topology와 mechanism을 함께 제안하는 것이 핵심이다(원본의 6-패턴 수동 선택을 대체):
- `staged && domains≥2` → **pipeline**
- `domains≥2` (단일 스테이지) → **dispatch**
- 그 외(단일도메인 다단계 정제) → **producer-reviewer**
- `!objective` → **debate-with-judge** / `staged` → **reflect-then-revise** / `noisy` → **majority-vote** / else **single**

> **이것이 "테스트의 첫 줄"인 이유.** 가장 비싼 실패는 "만들지 말았어야 할 하네스를 만든 것"이다. warrant.classify는 그 실패를 0토큰으로 차단한다. 원본의 "Why-not-ALWAYS 본문 원칙"(스킬이 항상 발동되면 안 되는 이유)을 *생성 시작 전*으로 끌어올린 셈이다.

### 2-2. 비용 cost-band = dry-run (Phase 6)

graph.json이 완성되면 실행 전에 토큰 비용을 추정한다. 이것이 CYS의 **dry-run**이다 — 실제 `Agent()`/`TeamCreate()`를 spawn하지 않고 그래프만 읽어 비용을 낸다.

```bash
python3 "$TR"/warrant.py --graph <TARGET>/.harness/graph.json
```

핵심 계산:
- `est_tokens(node) = expected_tokens × fanout × (retries + 1)`
- `fanout`은 mechanism이 곱한다: `single`=1, `majority-vote`=n, `debate-with-judge`=2·rounds+1, `reflect-then-revise`=2·rounds (critic+reviser).
- `weighted_units = Σ est_tokens × TIER_COST_WEIGHT`(haiku 1 / sonnet 3 / opus 5) → band `LOW`(<5e5) / `MEDIUM`(<5e6) / `HIGH`. 밴드 경계는 `constants.json`(`BAND_LOW`/`BAND_MED`).

출력 예(breakdown 포함):
```json
{
  "cost": {
    "total_tokens": 168000,
    "weighted_units": 612000,
    "band": "MEDIUM",
    "usd_estimate": 1.93,
    "breakdown": [
      {"id": "gather", "model": "haiku", "fanout": 1, "est_tokens": 16000, "weighted_units": 16000},
      {"id": "verify", "model": "sonnet", "fanout": 4, "est_tokens": 32000, "weighted_units": 96000}
    ]
  }
}
```

규칙:
1. warrant는 budget.total_tokens를 **제안**할 뿐 — graph.json이 단일 writer(retry/분산 여유로 floor의 2배까지 잡을 수 있다).
2. `approval_required=true`면 밴드를 **표시하고 사용자의 명시적 "approve"를 기다린다**. 첫 spawn이 일어나기 전에 BLOCK한다.
3. 실제 실행 시 `budget.total`이 런타임의 **하드 ceiling**이다 — cost-band 추정과 별개로, 프리미티브 기질에서는 `spawn_counter` hook이 `budget.spawns_used`를 증분하다 천장에서 발화(exit-2)해 초과 spawn을 강제 차단한다(`budget_block.py`).

> dry-run의 가치: 비싼 그래프(HIGH band)는 사람이 보고 mechanism을 낮추거나 fanout을 줄이는 의사결정을 *실행 전에* 할 수 있다. 원본에는 "토큰 비용이 높으니 안정화 후 실행하라"는 권고만 있었다 — CYS는 그 권고를 숫자가 박힌 BLOCKING 승인으로 만든다.

---

## 3. Gate 1: validate_harness.py — 정적 빌드 게이트 (구조 검증의 실행화)

원본의 **"구조 검증"은 prose였다** — "agent 파일이 있는지 확인하라", "절대경로를 쓰지 마라", "모든 에이전트가 opus면 안 된다" 같은 권고를 사람이 읽고 지켰다. CYS는 이를 **머신체크 세트**로 바꾼다. 위반은 `exit 1`이고, 그러면 **생성이 중단된다**. 권고가 컴파일러가 된 것이다.

```bash
python3 "$TR"/validate_harness.py <TARGET>            # 사람용 출력
python3 "$TR"/validate_harness.py <TARGET> --json     # 기계용 (status/errors/warns)
# exit 0 = pass, 1 = error(생성 중단), 2 = warn-only
```

### 3-1. 머신체크 세트 (대표 코드 — 전체 49종 중 일부)

> 아래는 대표 코드만 추린 것이다. `validate_harness.py`는 총 **49개** 머신체크 코드를 emit하며, 여기 없는 것에는 4대 장기기억 게이트(`MEMORY_RECALL_WIRED`·`AGENT_MEMORY_CONTRACT`·`MEMORY_RELAY_WIRED`·`MEMORY_INCREMENTAL_WIRED`)·`RECALL_KEY_DETERMINISTIC`·`TOPOLOGY_STRUCTURE`·`QA_TOKEN_TRAP`·`GRAPH_PROVENANCE` 등이 포함된다(전체 카탈로그는 `validate_harness.py` 코드가 단일 진실원천).

아래 코드는 모두 `validate_harness.py` 실측이다. 두 그룹으로 나뉜다: **A) substrate-무관 정적 계약**, **B) 프리미티브 기질 전용**(`execution_mode != workflow`일 때 오케스트레이터 SKILL을 스캔).

**A) substrate-무관 정적 계약**

| 코드 | level | 검증 내용 | 원본 대응 prose |
|------|-------|----------|----------------|
| `GRAPH_MISSING` | error | `.harness/graph.json` 존재 | — (CYS 신규: 계약 우선) |
| `GRAPH_SCHEMA` | error | graph.json이 graph.schema.json 준수 | "구조가 올바른가" |
| `EDGE_INTEGRITY` | error | edge가 존재하는 node만 참조 | — |
| `GRAPH_CYCLE` | error | pipeline/dispatch는 비순환(toposort) | — (자동화로 신규) |
| `AGENT_EXISTS` | error | node.agent → `.claude/agents/<agent>.md` 실재 | "agent 파일이 있는가" |
| `AGENT_FRONTMATTER` | error | frontmatter에 name/description/model 존재 | "pushy description" |
| `RATIONALE_MISSING` | warn* | frontmatter에 model_rationale 존재 | — (티어정책 신규) |
| `TIER_MISMATCH` | error | node.model == agent frontmatter model (**V3**) | — |
| `TIER_MISSING` | error | node.model이 유효 티어(haiku/sonnet/opus) (**V1**) | "model을 명시하라" |
| `TIER_OVERSPEND` | error/warn | pure-retrieval 역할이 opus면 위반 (**V2**) | "all agents use opus 금지" |
| `SCHEMA_FILE_EXISTS` | error | output_schema 파일 실재 + top-level type | "output 계약" |
| `ABSOLUTE_PATHS` | error | inputs/outputs/write_paths는 상대경로 | "절대경로 쓰지 마라" |
| `WRITE_PATH_OVERLAP` | error | 두 node가 같은 write_path 소유 금지 | — (병렬 안전 신규) |
| `REVIEW_AGENT_PRESENT` | error | review 노드의 `review.agent` 정의 파일 실재 (L2 적대적 리뷰가 spawn 가능) | — (4계층 QA 신규) |
| `SKILL_AUTHORING_JUSTIFIED` | error | `skill_authoring.mode=skill`은 reason∈{reuse,complex,conditional}; reuse면 shared_by≥2 | — (하이브리드 신규) |
| `INLINE_NO_ORPHAN_SKILL` | error | mode=skill 노드는 `.claude/skills/<harness>-<id>/SKILL.md` 실재 | — (하이브리드 신규) |
| `LIFT_UNMEASURED` | warn* | 저작한 스킬에 `lift_verdict.json` 없음(미측정) | — (Gate 2 배선) |
| `LIFT_REFUSED` | error | 측정했으나 `decision≠register`(또는 verdict 손상) → 출하 금지 | — (Gate 2 배선) |
| `MEASUREMENT_DRIFT` | error | evals verdict가 **존재**하고 그중 `CYS-WINS`가 하나도 없는데 README/SKILL이 `CYS-WINS` 광고(verdict 0개면 통과 — 측정 안 한 승리 주장은 이 체크 범위 밖) | — (정직성 신규) |
| `DOC_DRIFT` | error | README phase-count == 도메인 오케스트레이터 SKILL phase-count | "문서 일치" |
| `AUDIT_VERDICT_PRESENT` | error | `.harness/audit.json` 있으면 branch∈{new,extend,maintain}+drift list | — (Phase-0 신규) |
| `EVOLUTION_LOG_PRESENT` | error | `.harness/change-history.jsonl` 각 줄이 feedback_type/target/change 구비 | — (Phase-7 신규) |
| `MEMORY_STORE_INIT` | error | settings.json 있으면 `.harness/memory/`(archive.manifest.json·domain-knowledge.yaml·runs/index.jsonl) 시드됨 | — (Tier-II 신규) |
| `W1_GENOME` | error/warn | harness.md(또는 in-project `.harness/harness.md`)에 inherited-DNA 마커(Inherited DNA·AC-1~3) | — (게놈 신규) |
| `GENOME_PRESENT` | error | load-bearing 게놈 머신 전수 이식 | — (게놈 신규) |
| `RUNTIME_DECLARED` | error | `.harness/RUNTIME.json` canonical이 execution_mode와 일치 | — (런타임 명시) |
| `RUNTIME_MANIFEST_CLEAN` | error | produced child가 은퇴 런타임(workflow.js/prompt-runner)을 runnable로 광고 금지 | — (M0 누수 스크럽) |
| `WORKFLOW_RETIRED` | error | `execution_mode=workflow` 또는 `.harness/workflow.js` 동봉 금지 | — (M0 프리미티브) |
| `HOOK_REGISTERED` | error | settings.json이 보안·컨텍스트·예산 hook을 wiring | — (보안 신규) |

\* `RATIONALE_MISSING` level은 `constants.json`의 `MODEL_RATIONALE_MISSING`(기본 `warn`), `LIFT_UNMEASURED` level은 `LIFT_UNMEASURED`(기본 `warn` → `error` 전환가능)가 결정한다.

**B) 프리미티브 기질 전용** — `execution_mode != workflow`일 때 도메인 오케스트레이터 SKILL(`.claude/skills/<harness>-orchestrator/SKILL.md`)을 스캔한다:

| 코드 | level | 검증 내용 |
|------|-------|----------|
| `GRAPH_SKILL_CONSISTENCY` | error | 오케스트레이터 SKILL이 graph의 모든 node id를 본문에서 호명(prose-vs-graph 드리프트) |
| `ALL_PRIMITIVES_PRESENT` | error | SKILL이 **호출형** `Agent(` **그리고** `TeamCreate(`를 둘 다 인스턴스화(A2 all-6 floor) |
| `TEAM_EMIT_PRESENT` | error | `execution_mode=team`이면 SKILL이 실제 `TeamCreate`/`TaskCreate`/`TeamDelete`를 emit(Agent fan 위장 금지) |
| `TEAM_GRACEFUL_DEGRADE` | error | 팀 사용 시 experimental Agent-Teams 플래그 부재 대비 sub-agent 강등 경로 문서화 |
| `TOPOLOGY_PRIMITIVE_CONSISTENCY` | error | 선언한 topology의 emit 레시피 존재 + 팀필요 topology는 `TeamCreate(` 동반 |
| `CONTEXT_PRESERVATION_FIRSTCLASS` | error | SKILL이 `메모리 운영`·`knowledge-index`·`latest.md`를 명시(장기메모리 일급화) |
| `MEMORY_SKILL_SECTION` | error | SKILL이 Tier-II 회상·기록 레시피(`교차-실행 도메인 메모리`+`runs/index.jsonl`) 보유 |
| `EVOLUTION_WIRED` | error | SKILL이 Phase-7 진화 섹션(`진화`+`evolve_harness`) 보유 |

> `Agent(`/`TeamCreate(`를 **호출형(괄호 포함)** 으로 검사하는 이유: description 줄이 "Agent/TeamCreate"라는 *단어*를 항상 언급하므로 단어-존재 검사는 무의미하다. 실제 spawn은 괄호 호출 형태를 쓴다.

### 3-2. 모델 티어 정책 V1/V2/V3 — "all agents use opus" 폐기의 실행화

원본의 흔한 안티패턴 "모든 에이전트를 opus로"를 CYS는 **머신으로 거부**한다. role→tier 정책의 단일 SoT는 `role-class-policy.json`이며 `model-tier-policy.js`와 `validate_harness.py`가 **둘 다 이 파일을 로드**한다(손복사 미러 없음 — 드리프트 불가):

- **gather / extract / format / qa-scan → haiku** (순수 검색·추출·포맷·스캔)
- **voter / debater / reviser → sonnet** (판단 보조 역할 = mechanism이 부여)
- **synthesis / judge / critic / architecture → opus** (종합·심판·비평·설계)

체크 3단:
- **V1 `TIER_MISSING`**: node.model이 비었거나 무효 → error. 디폴트 티어를 메시지로 알려준다.
- **V2 `TIER_OVERSPEND`**: pure-retrieval(gather/extract/format/qa-scan) 역할인데 opus → error. (단 `tier_override_reason`이 있으면 warn으로 완화 — 의도된 오버라이드는 허용하되 기록을 강제.)
- **V3 `TIER_MISMATCH`**: node.model ≠ agent frontmatter model → error. 계약과 에이전트 정의의 불일치는 빌드 실패.

> **왜 이게 "테스트"인가.** 원본은 "에이전트를 분할하는 기준(전문성/병렬성/컨텍스트/재사용)"을 잘 정리했지만, 분할 *후* 각 에이전트가 적정 모델을 쓰는지는 사람 검토에 맡겼다. CYS는 role-class를 id/agent 이름에서 정규식으로 추론해(`_base_role_class`) 티어 위반을 자동 검출한다. mechanism이 부여하는 보조역할(voter/debater/reviser)은 `_role_class_of`가 먼저 잡는다. 즉 *비용/품질 트레이드오프가 빌드 게이트로 강제된다.*

### 3-3. 게놈 무결성 — 상속이 깨지지 않았는지

모든 자식 하네스는 AgenticWorkflow 게놈(자족)을 `inherit_genome.py`로 전수 상속한다. validator는 이 상속이 *부분*이 아니라 *전수*임을 강제한다:

- `GENOME_PRESENT`: load-bearing 머신 — `.claude/hooks/scripts/_context_lib.py`(hook 공유 spine), `context_guard.py`, `block_destructive_commands.py`, `output_secret_filter.py`, `security_sensitive_file_guard.py`, 그리고 `.harness/GENOME.json` + 헌법 3종(`soul.md`·`AGENTS.md`·`CLAUDE.md`) — 이 중 하나라도 없으면 error. (in-project 모드에서는 헌법 3종이 `.harness/genome/`으로 재배치되므로 거기서 찾는다.)
- `RUNTIME_DECLARED`: `RUNTIME.json`의 `canonical_runtime`이 execution_mode와 정합해야 한다 — 프리미티브 기질(`agent`/`team`/`hybrid`)이면 `<harness>-orchestrator`, 측정용 `workflow` 모드일 때만 `cys-mode-a`. 불일치면 error.
- `RUNTIME_MANIFEST_CLEAN`: produced child의 `RUNTIME.json`이 은퇴 런타임(`workflow.js` 엔트리포인트/`prompt-runner`/`cys-mode-a-workflow`/`awf-prompt-runner`)을 runnable로 광고하면 error — 자식은 **정확히 하나의** 실행 런타임(오케스트레이터 SKILL)만 가진다.
- `WORKFLOW_RETIRED`: `execution_mode=workflow`이거나 produced child가 `.harness/workflow.js`를 동봉하면 error — Mode-A workflow.js는 제품에서 은퇴했고 공장내부 측정용으로만 산다.
- `HOOK_REGISTERED`: settings.json이 보안·컨텍스트 hook 5종(`block_destructive_commands`·`output_secret_filter`·`security_sensitive_file_guard`·`context_guard`·`save_context`)을 wiring해야 한다. 프리미티브 기질(`!=workflow`)이면 **발화 hook 4종**(`budget_block`·`spawn_counter`·`sot_init`·`qa_gate_runner`)도 추가로 wiring해야 한다 — 그래야 예산 천장과 QA 게이트가 실제로 발화한다(이 hook들이 없으면 게놈 DNA가 휴면 상태로 남는, 감사가 짚은 바로 그 갭).

> 이 체크들이 보장하는 것: 자식 하네스는 **이미 풍부한 운영 머신(컨텍스트 보존 hook·4계층 품질 게이트·보안 hook·발화 hook)을 가지고 태어난다.** 그래서 이 문서가 안내하는 테스트는 상속된 back-half가 아니라 **front-half 설계(domain→graph.json+agents+schemas+오케스트레이터 SKILL)의 정확성**에 집중한다.

### 3-4. 게이트 통과 절차 (Phase 5)

```
1. validate_harness.py 실행
2. error 0건 (exit 0) → Phase 6 진행
3. error ≥1건 → 생성 중단·코드별 리포트 → 고치고 재실행 (BLOCKING, 절대 우회 금지)
4. warn만 있으면 (exit 2) → 진행 가능하되 RATIONALE_MISSING / LIFT_UNMEASURED 등은 보강 권장
```

---

## 4. Gate 2: lift_gate.py — with-skill vs haiku-baseline 리프트 (등록/거부)

이것이 **원본의 "With-skill vs Baseline A/B 비교"를 CYS의 강제 게이트로 만든 것**이다. 원본의 A/B 규율은 옳았다 — 다만 권고였고, 평가가 자기채점으로 새기 쉬웠다. CYS는: ① 비교를 *등록의 필수 조건*으로 만들고, ② 채점을 *독립 블라인드 채점자*로 강제하며, ③ 판정을 *결정론적 스코어러*에 맡긴다.

**계약: 도메인 스킬(하이브리드 `skill_authoring.mode=skill` 노드)은 no-skill baseline을 측정 가능하게 능가할 때만 출하된다.**

```
lift = pass_rate_with(sonnet + skill) − pass_rate_without(haiku baseline)
등록 조건: lift ≥ LIFT_GATE_THRESHOLD (0.2, constants.json)
```

### 4-1. 세 단계 (probe 생성 → 런타임 실행 → 채점·기록)

`lift_gate.py`는 순수·결정론이라 agent를 직접 spawn하지 않는다(측정 런타임만 가능). 그래서 책임을 나눈다:

**① emit-probe** — 스킬 스펙에서 `lift_probe.workflow.js` 템플릿(공장내부 측정 도구)을 생성:
```bash
python3 "$TR"/lift_gate.py emit-probe <skill.json> > examples/_probes/<skill>.lift_probe.workflow.js
```
`skill.json` 형태:
```json
{
  "name": "cited-research",
  "prompt": "In 4-6 sentences, summarize the documented reliability limitations of multi-agent LLM systems as of 2026.",
  "instructions": "Attach an inline [source_id] citation to EVERY factual sentence. End with a Sources list of at least 3 distinct, real sources...",
  "assertions": [
    {"id": "A1", "text": "Every factual sentence carries an inline [source_id] citation", "polarity": "must"},
    {"id": "A2", "text": "At least 3 distinct sources are listed with URLs", "polarity": "must"},
    {"id": "A3", "text": "No fabricated/uncited statistics", "polarity": "must-not-violate"}
  ]
}
```

**② 측정 런타임이 probe 실행** → with/without results를 PRODUCE:
- with_skill arm: **sonnet** + 스킬 가이드를 프롬프트에 inline(probe의 `agent()`에 `skill:` 옵션이 없으므로 PROMPT INLINING — 검증된 옵션은 agentType/schema/model/label/phase).
- baseline arm: **haiku**, 스킬 없음.
- 두 arm은 *답만 생산한다 — 자기채점 금지.*
- 별도의 **블라인드 opus 채점자**가 두 답(A=with-skill, B=baseline)을 채점한다. 채점자는 어느 쪽이 스킬인지 모른다.

**③ score** — 런타임이 낸 results.json을 결정론적으로 채점하고 verdict를 **정확한 경로에 기록**:
```bash
python3 "$TR"/lift_gate.py score <results.json> \
  --out <TARGET>/.claude/skills/<harness>-<node>/lift_verdict.json
# exit 0 = register, 3 = refuse
```
`--out`이 핵심이다(P1.3 배선): verdict를 `validate_harness.py`가 읽는 그 경로에 쓴다. 그래서 Gate 1이 다음을 강제할 수 있다:
- **미측정**(`lift_verdict.json` 없음) → `LIFT_UNMEASURED`(정책, 기본 `warn` → `error` 전환가능: 미측정 스킬 출하 금지).
- **측정했으나 baseline 미달**(`decision≠register`, 또는 verdict 손상/비객체) → `LIFT_REFUSED`(**hard error**) — baseline에 진 스킬에 의존하는 건 정당화 불가. inline하거나 개선하라. 이것이 게이트에 이빨을 준다(이전엔 presence-warn뿐이었다).

### 4-2. pass_rate 규칙 — must는 게이팅, should는 부분점수

`_pass_rate`는 단순 비율이 아니다:
- `must` / `must-not-violate` assertion이 하나라도 실패하면 **그 조건의 pass_rate = 0.0** (하드 요구는 부분점수 없음 — 테스트가 discriminating해진다).
- `should` assertion은 비율에 기여하지만 단독으로 게이팅하지 않는다.

판정 출력:
```json
{
  "pass_rate_with": 1.0,
  "pass_rate_without": 0.3333,
  "lift": 0.6667,
  "threshold": 0.2,
  "decision": "register",
  "with":  {"passed": ["A1","A2","A3"], "failed": []},
  "without": {"passed": ["A1"], "failed": ["A2","A3"]},
  "rationale": "lift 0.67 >= 0.20 -> skill earns registration."
}
```
거부 시:
```json
{ "decision": "refuse",
  "rationale": "lift 0.10 < 0.20 -> REFUSED: skill does not beat the haiku baseline enough to justify a tier upgrade." }
```

> **핵심 통찰(M1, 경험적).** 초기 self-check 버전에서는 각 arm이 *자기 출력을 자기가 채점*했다 → haiku baseline이 자기 점수를 all-pass로 부풀려 lift가 0으로 붕괴, 게이트가 아무것도 측정하지 못했다. 수정: 두 arm은 답만 생산하고, **분리된 블라인드 opus 채점자**가 둘 다 채점한다(어느 쪽이 스킬인지 모름). 이것이 §8의 독립채점자 규율이고, 헤드투헤드 suite와 동일한 원칙이다.

### 4-3. baseline이 왜 haiku인가

원본은 baseline을 "스킬 없이 같은 프롬프트"로 두되 모델은 동일했다. CYS는 baseline을 **haiku**로 고정한다 — 이유: 등록의 의미가 "이 스킬은 *티어 업그레이드(sonnet)를 정당화할 만큼* 싼 baseline(haiku)을 능가하는가"이기 때문이다. 스킬+sonnet이 그냥 haiku보다 0.2 미만으로밖에 못 이긴다면, 그 스킬은 비용 대비 가치가 없다 → 거부. 이것은 §2의 cost-band 철학과 한 몸이다.

---

## 5. Gate 3: h2h_suite + h2h_aggregate — n-run 중앙값 헤드투헤드

원본의 "Comparator(블라인드 비교자)"는 *선택적 고급 기능*이었고 1회 비교였다. CYS는 이를 **n-run 중앙값 + provenance가 박힌 정식 suite**로 격상한다. lift_gate(Gate 2)가 "스킬 한 단위의 등록 자격"을 본다면, h2h(Gate 3)는 "CYS 하네스 파이프라인이 no-harness baseline을 *엄밀하게* 이기는가"를 입증한다.

### 5-1. suite 구조 (h2h_suite.workflow.js — 공장내부 측정 도구)

n번 반복(run = 0..n-1), wall-clock/RNG 없이 **정수 인덱스로만** 변주(완전 결정론·resume-safe):

- **C2 = CYS pipeline**: gather(haiku) → fetch(haiku) → verify(reflect-then-revise: opus critic + sonnet reviser, max_rounds=2) → synthesize(opus).
- **C3 = no-harness baseline**: 같은 query+assertions에 대한 single opus pass(파이프라인·툴 없음, 동일 출력 계약 = 공정 채점).
- **BLIND GRADE**: 조건 라벨을 제거하고 채점자에게 (A, B)만 준다. **결정론 매핑 A=C2 / B=C3를 기록**하되 채점자는 어느 쪽이 하네스인지 추론할 수 없다. 채점 후 기록된 매핑으로 c2/c3 pass_rate를 재부착.

**StructuredOutput-resilient (P1.4).** suite는 모든 `agent()` 호출을 `tryAgent` 래퍼로 감싼다 — null/throw 시 `ATTEMPTS`회(기본 3, `--attempts`로 조정) 재시도하되 **라벨을 변주**해 runner의 캐시된 null 회피. 한 run이 모든 재시도 후에도 report/grade를 못 내면 그 run은 **0점이 아니라 DROP**된다(`valid:false`) — 가짜 0이 중앙값을 왜곡하는 것을 구조적으로 막는다. provenance에 `n_attempted`/`n_valid`/`n_dropped`를 박는다.

산출: `{ runs:[{run, c2_pass_rate, c3_pass_rate, a_is, b_is, valid, ...}], provenance }`. runs[] 배열을 aggregator에 넘긴다.

### 5-2. 집계 (h2h_aggregate.py)

순수 stdlib·결정론·agent 호출 없음. per-run 스코어카드들을 받아:

```bash
python3 "$TR"/h2h_aggregate.py <runs.json> \
  --model-id <id> --git-sha <sha> --harness-version 0.1.0 [--margin-pp 15]
```

- **드롭 필터링(P1.4)**: `valid:false`이거나 `c2_pass_rate`/`c3_pass_rate` 키가 없는 run은 **필터링**(이전엔 첫 발견에 raise → 부분실패 suite 전체가 죽었다). `n_attempted`/`n_dropped`를 보고하고, 유효 run이 **0건일 때만** raise. 가짜 0으로 채점하지 않으므로 부분실패 suite를 정직하게 집계한다.
- 조건별 **median(pass_rate)** — 단일 나쁜 run에 강건.
- 조건별 **variance** — run-to-run 불안정 신호(높으면 n을 늘려라).
- **delta_pp = (median(C2) − median(C3)) × 100**.
- **verdict**: delta ≥ +15pp → `CYS-WINS` / delta ≤ −15pp → `BASELINE-WINS` / 그 사이 → `INCONCLUSIVE`. 마진은 `HEAD_TO_HEAD_WIN_MARGIN_PP`(15).
- **provenance**: schema_version / model_id / harness_version / git_sha / n_runs / n_attempted / n_dropped를 스탬프 → 재현·감사 가능.

실제 deep-research fixture(`examples/deep-research/evals/deep-research.runs.json`)는 현재 **n=5 실측**이다(피벗 후 프리미티브 기질, 라이브 웹 리서치, 블라인드 채점) — C2(CYS 하네스) median=1.0 vs C3(no-harness 단일 opus) median=0.875:
→ delta=**+12.5pp**, 15pp 마진 미달 → `INCONCLUSIVE`. **CYS가 앞선다 — 이전 n=1 −16.67pp `BASELINE-WINS`를 뒤집었다(정직 기록).** 활성화된 L0-L2·적대적 리뷰가 baseline의 **A4(미검증 주장 잔존, 3/5)·A6(통계 날조, 4/5)** 실패를 잡아낸 것이 격차의 원인 — 피벗이 약속한 게놈 발화가 실제로 작동. 단 15pp `CYS-WINS` 마진은 못 넘어 INCONCLUSIVE이므로, 더 강한 결론(다도메인·더 큰 n)은 추가 측정이 필요하다(C2 variance 0.0025로 매우 안정적). 확정 수치는 `examples/deep-research/evals/deep-research.verdict.json`.
> ⚠️ 이전 판본의 "median(C2)=0.875 / +37.5pp / CYS-WINS"는 **hand-authored HYPOTHESIS fixture**였고 실측과 모순되어 **폐기**됐다. 모든 h2h/lift 인용 수치는 `evals/*.verdict.json`(디스크)과 일치해야 하며, `validate_harness.py`의 `MEASUREMENT_DRIFT` 체크가 이를 강제한다(verdict가 **존재하고 그중 승리가 없는데** doc이 `CYS-WINS`를 광고하면 빌드 실패; verdict가 0개면 통과).

### 5-3. 정직성 규율

aggregate 출력 note가 강제하는 것: *"INCONCLUSIVE면 마진을 못 넘은 것; variance가 높으면 n을 늘려라; `n_dropped`가 크면 유효 n이 얇으니 재실행하라; CYS가 이기지 못하는 도메인은 정직하게 보고하라."* scorecard(`deep-research.scorecard.json`)도 동일: *"Report domains where CYS does NOT win honestly."* 그리고 `MEASUREMENT_DRIFT`(Gate 1)가 이 정직성을 빌드 게이트로 박는다 — verdict 없이 승리를 광고하는 doc은 출하 불가.

> **Gate 2 vs Gate 3 구분.** Gate 2(lift)는 *스킬 한 단위가 등록될 자격*(with-skill sonnet vs haiku, threshold 0.2). Gate 3(h2h)는 *완성된 하네스 파이프라인이 no-harness를 이기는지*(C2 CYS vs C3 opus single, margin 15pp, n-run median). 둘 다 동일한 블라인드 독립채점자 원칙을 쓰지만, 단위와 baseline과 마진이 다르다. Gate 3는 엄밀성이 필요할 때(예: 새 topology 입증, 회귀 의심) 돌린다.

---

## 6. 빌드레벨 parity 평가 — eval_topology.py (8 use case)

재구성된 벤치마크는 idoforgod와의 **피처 패리티**다: 공장은 idoforgod README의 모든 use case(Deep Research·Website Dev·Webtoon·YouTube·Code Review·Tech Docs·Data Pipeline·Marketing)에 대해 **conforming 하네스를 EMIT**할 수 있어야 한다. `eval_topology.py`는 이를 **빌드레벨(L-factory)** 로 본다 — Gate 3의 run-level h2h(쿼터-게이트 별도 레인)와 분리된, agent 호출 없는 순수 matcher다.

```bash
python3 "$TR"/eval_topology.py <harness_dir> <expected.json>
# PASS → exit 0 / FAIL(mismatch 나열) → exit 1
```

`match(graph, skill_text, expected)`가 검사하는 것(빈 리스트 = conform):
- **topology** == expected.topology, **execution_mode** == expected.exec_mode.
- **all-6 floor(A2)**: 오케스트레이터 SKILL에 `TeamCreate(` 그리고 `Agent(` 둘 다 존재.
- **필수 DNA 섹션**: `메모리 운영`(컨텍스트 보존), `교차-실행 도메인 메모리`(Tier-II), `진화`(Phase-7).
- **first-class topology 레시피**: pipeline/dispatch/producer-reviewer를 넘는 4종(`fan-out-fan-in`·`supervisor`·`expert-pool`·`hierarchical`)은 `### 토폴로지: <hdr>` 레시피가 SKILL에 있어야 함.

`TestEightUseCases`(factory 테스트)가 idoforgod 8 use case 전부를 이 matcher로 빌드레벨 conform 확인하며, 5개 토폴로지(fan-out-fan-in·pipeline·producer-reviewer·supervisor·hierarchical)를 행사한다. 이 게이트는 Gate 1과 상보적이다: Gate 1은 *한* 하네스의 내부 정합성을, eval_topology는 *use-case별 기대 형상*과의 일치를 본다.

---

## 7. 테스트 프롬프트 & assertion 작성법 (보존된 원본 지혜)

게이트들은 좋은 **프롬프트**와 좋은 **assertion**이 있어야 의미가 있다. 여기는 원본의 설계 지혜를 거의 그대로 보존한다 — 이것이 측정 품질의 토대다.

### 7-1. 테스트 프롬프트 원칙

**실제 사용자가 입력할 법한 구체적·자연스러운 문장**이어야 한다. 추상적·인공적 프롬프트는 가치가 낮다.

나쁜 예:
```
"PDF를 처리하라"  /  "데이터를 추출하라"  /  "차트를 생성하라"
```
좋은 예:
```
"다운로드 폴더의 'Q4_매출_최종_v2.xlsx'에서 C열(매출)과 D열(비용)으로
 이익률(%) 열을 추가하고, 이익률 기준 내림차순 정렬해줘."
```

다양성: 공식/캐주얼 톤 혼합, 명시적/암시적 의도 혼합, 단순/복잡 작업 혼합, 일부에 약어·오타.

커버리지(2~3개로 시작): 핵심 사용 사례 1 + 엣지 케이스 1 + (선택) 복합 작업 1.

### 7-2. Assertion 작성 — discriminating해야 한다

**좋은 assertion:**
- 객관적으로 참/거짓 판별 가능
- 서술적 이름(결과만 봐도 무엇을 검사하는지 명확)
- 스킬/하네스의 **핵심 가치**를 검증

**나쁜 assertion:**
- 스킬 유무와 무관하게 항상 통과("출력이 존재한다")
- 주관적 판단 필요("잘 작성되었다")

**non-discriminating assertion 주의 (CYS에서 더 치명적).** 원본에서는 "차별력 없음"이 측정을 흐릴 뿐이었다. CYS에서는 *게이트가 그 assertion으로 lift/delta를 계산*하므로, 양쪽 모두 통과하는 assertion은 lift를 0 쪽으로 끌어내려 좋은 스킬도 거부시킬 수 있다. variance/lift가 의외로 낮으면 **먼저 assertion을 의심하라.**

**polarity를 반드시 명시.** CYS의 채점은 polarity로 게이팅한다(§4-2):
- `must` — 충족해야 함(실패 시 그 조건 pass_rate=0).
- `must-not-violate` — 위반하면 안 됨(예: 날조 통계 금지).
- `should` — 부분점수에 기여, 단독 게이팅 안 함.

실제 deep-research assertion 세트(8개, `deep-research.scorecard.json`)가 모범이다 — A1~A6은 must/must-not-violate(인용·다출처·해소가능 URL·검증실패 제거·team vs pipeline 구분·날조금지), A7~A8은 should(상충 출처 양립·자체 스코프 한계 명시).

> **QA 경계 교차비교 + 7개 실버그 패턴(보존).** 채점자가 산출물에서 검증가능한 claim을 추출해 교차검증하는 원본 규율은 그대로 유효하다 — CYS에서는 이것이 채점자 에이전트(§8)의 일이다. QA 노드(qa-scan, haiku)를 하네스에 두면 인접 노드의 출력 경계를 교차비교해 흔한 버그 패턴(누락 인용, 잘못된 조인, 침묵 해소된 충돌, 단위 불일치 등)을 잡는다. 이 패턴 카탈로그는 assertion 설계의 원천이다. 프리미티브 기질에서는 이 교차비교가 `qa_gate_runner` hook(L0-L2)으로 발화한다.

---

## 8. 블라인드 독립 채점자 규율 (자기채점 금지)

원본의 Grader/Comparator/Analyzer 3역할을 CYS는 **하나의 강제 규율**로 응축한다: *"답을 만든 에이전트는 절대 자기 답을 채점하지 않는다. 분리된 블라인드 채점자가 채점한다."*

이것은 미적 선호가 아니라 **경험으로 증명된 필수 조건**이다(§4-2 노트): 자기채점은 baseline의 점수를 부풀려 lift를 0으로 붕괴시킨다.

### 채점자 3역할 (CYS 매핑)

- **Grader (채점자)** → lift_probe와 h2h_suite의 블라인드 opus 채점자. assertion별 통과/실패 + 근거. claim 추출·교차검증. `GRADE_SCHEMA`/`grade_schema`로 출력 강제(`{checks:{id:boolean}}` 또는 `{candidate, pass_rate, passed[], failed[]}`).
- **Comparator (블라인드 비교자)** → h2h_suite의 A/B 블라인드 매핑(A=C2, B=C3, 기록되되 채점자에 비공개). "새 버전이 정말 더 나은가"를 엄밀히 볼 때.
- **Analyzer (분석자)** → h2h_aggregate.py의 variance(고분산 eval) + lift_gate의 non-discriminating 검출 + cost-band의 time/token 트레이드오프. 통계 패턴을 자동 산출.

채점자 모델은 **opus**(judge/critic role-class)다 — 채점은 종합·심판이므로 티어 정책상 최상위.

> 블라인드 매핑이 *결정론적이되 기록*되는 게 핵심이다. RNG로 셔플하면 resume-safe가 깨진다. 그래서 A=C2/B=C3로 고정하고, 채점자에게는 조건을 숨기되 매핑은 audit용으로 남긴다.

---

## 9. Description 트리거 검증 — near-miss 중심

원본의 트리거 검증은 그대로 유효하고 CYS에서도 필수다 — 하네스의 오케스트레이터 SKILL이 잘못 발동되거나 발동되지 않으면 게이트를 다 통과해도 무용지물이다.

### 9-1. 20개 eval 쿼리 (should 10 + should-NOT 10)

품질 기준:
- 실제 사용자가 입력할 법한 구체적·자연스러운 문장(파일 경로·회사명·열 이름 등 디테일)
- 길이·톤·형식 다양
- 명확한 정답보다 **경계 케이스**에 집중

**Should-trigger(8~10):** 같은 의도의 다양한 표현(공식/캐주얼), 스킬을 명시 안 했지만 분명히 필요한 경우, 비주류 사용 사례, 다른 스킬과 경쟁하지만 이겨야 하는 경우.

**Should-NOT-trigger(8~10) — near-miss가 핵심:** 키워드는 유사하지만 다른 도구가 적합한 쿼리. 명백히 무관한 쿼리("피보나치 함수 작성")는 테스트 가치 없음. 인접 도메인·모호한 표현·키워드 겹침 but 맥락이 다른 경우.

### 9-2. 기존 스킬 충돌 검증

새 하네스 description이 기존 스킬(특히 게놈 상속 스킬: `workflow-generator`, `doctoral-writing`, `spec-grounded-workflow` 등)의 트리거 영역과 겹치지 않는지 확인:
1. 기존 스킬 목록 description 수집.
2. 새 하네스의 should-trigger 쿼리가 기존 스킬을 잘못 트리거하지 않는지 확인.
3. 충돌 시 description의 경계 조건을 더 명확히 기술.

> CYS 자식 하네스는 게놈에서 여러 스킬을 상속하므로 **트리거 충돌 위험이 원본보다 높다.** near-miss verification은 "내 도메인 오케스트레이터 SKILL이 발동될 자리에 상속된 workflow-generator가 발동되지 않는가"를 반드시 포함해야 한다.

### 9-3. 자동 최적화 (선택, 고급)

20개 쿼리를 Train(60%)/Test(40%) split → 현재 description 트리거 정확도 측정 → 실패 케이스 분석해 개선 description 생성 → **Test set 기준**으로 best 선택(과적합 방지) → 최대 5회. 토큰 비용이 높으므로 하네스가 안정화된 최종 단계에서만.

---

## 10. 반복 개선 루프 & 진화 피드백

### 10-1. 개선 원칙 (보존)

1. **피드백을 일반화하라** — 테스트 예시에만 맞는 좁은 수정은 오버피팅. 원리 수준에서 수정. (CYS에서는 graph.json/agent 본문/오케스트레이터 SKILL을 고치는 것이지 특정 입력에 분기 추가가 아니다.)
2. **무게를 벌지 않는 것은 제거하라** — 트랜스크립트를 읽고 비생산적 작업을 시키는 부분을 삭제. (TIER_OVERSPEND warn이 나는 노드를 다운티어하는 것도, LIFT_REFUSED 스킬을 inline하는 것도 여기 포함.)
3. **Why를 설명하라** — 간결한 피드백이라도 왜 중요한지 이해해 반영(agent의 `model_rationale`, 작업원칙에).
4. **반복 작업은 번들링하라** — 모든 run에서 같은 헬퍼가 생기면 미리 포함. (대부분은 이미 게놈이 제공하므로 새로 만들지 말 것 — §3-3.)

### 10-2. 반복 절차 (CYS 게이트 통합)

```
1. graph.json 또는 agent/schema/오케스트레이터 SKILL 수정
2. validate_harness.py 재실행 (Gate 1 PASS 확인)        ← 구조·프리미티브 회귀 즉시 검출
3. warrant --graph 로 cost-band 재확인                  ← 비용 회귀 검출
4. (스킬 변경 시) lift_gate score --out 재측정 (Gate 2)  ← 등록 자격 유지 확인 (LIFT_REFUSED 회귀)
5. (엄밀히) h2h_suite n-run 재집계, 이전 verdict와 비교  ← 우위 회귀 검출
6. 결과 비교 → 다시 수정 → 반복
```

**종료 조건:** Gate 1 PASS + (저작 스킬이 있으면) Gate 2 register + (필요시) Gate 3 CYS-WINS, 그리고 의미 있는 개선이 더 없을 때.

### 10-3. 초안 → 재검토 패턴 (보존)

agent 본문·schema·description·오케스트레이터 SKILL을 한 번에 완벽히 쓰려 하지 말고 초안을 쓴 뒤 **새로운 시각으로 다시 읽고** 개선한다.

### 10-4. provenance 기반 회귀 추적 (CYS 신규)

git repo가 rollback substrate다(Phase 7). h2h_aggregate의 provenance(git_sha + harness_version + model_id)를 매 측정에 스탬프하면, *어느 커밋·어느 모델에서 우위가 바뀌었는지*를 정확히 추적할 수 있다. 원본의 "iteration-N 디렉토리 보존"을 git history + provenance로 대체한 것이다. 진화 루프 자체는 `evolve_harness.py`(피드백 유형→대상 라우팅 + `.harness/change-history.jsonl` append-only)가 구동하고, `EVOLUTION_WIRED`/`EVOLUTION_LOG_PRESENT`가 그것이 살아있음을 게이트한다.

---

## 11. 워크스페이스 & provenance 구조

CYS 하네스의 테스트/측정 산출물은 하네스 repo 안에 산다(원본의 별도 `_workspace/`와 달리 자식 repo의 일부). 단 측정 도구(`*.workflow.js`)는 **공장**에 산다 — produced child 안에 들어가면 `WORKFLOW_RETIRED`로 차단된다:

```
<TARGET>/                          # 생성된(제품) 하네스 (git repo = rollback substrate)
├── .harness/
│   ├── graph.json                 # 계약 (단일 writer = 메타스킬)
│   ├── predicates.json            # warrant Phase -1 입력
│   ├── RUNTIME.json               # canonical=<harness>-orchestrator (프리미티브 기질)
│   ├── GENOME.json                # install_mode 마커 (self-contained / in-project)
│   ├── audit.json                 # (선택) Phase-0 상태감사
│   ├── change-history.jsonl       # (선택) Phase-7 진화 로그 (append-only)
│   ├── memory/                    # Tier-II 교차-실행 메모리 (RLM 외부환경)
│   ├── constants.json             # 팩토리 SoT 전파 (SPAWN_CEILING_MARGIN 등 — budget_block이 읽음)
│   └── graph.lock                 # emit가 stamp한 graph.json sha256 provenance (GRAPH_PROVENANCE)
├── .claude/
│   ├── skills/<harness>-orchestrator/SKILL.md   # 제품 실행 런타임 (프리미티브 구동)
│   ├── skills/<harness>-<node>/lift_verdict.json # (저작 스킬) Gate 2 verdict — validate가 읽음
│   ├── agents/*.md                # node agent + 게놈 reviewer/fact-checker
│   ├── hooks/                     # 게놈 발화 hook (budget/spawn/sot/qa + 보안)
│   └── settings.json              # hook wiring
├── schemas/*.json                 # output 계약
└── evals/
    ├── <domain>.scorecard.json    # discriminating assertion 세트 (1회 + 메타)
    ├── <domain>.runs.json         # n-run 블라인드 스코어카드 → h2h_aggregate 입력
    └── <domain>.verdict.json      # h2h_aggregate 출력 (MEASUREMENT_DRIFT가 읽음)

<공장 측>                          # produced child에 들어가지 않음 (측정 전용)
└── examples/_probes/
    └── <skill>.lift_probe.workflow.js   # emit-probe 산출 (DO NOT EDIT BY HAND)
```

**규칙:**
- scorecard/runs/verdict 파일은 **서술적 도메인 이름** 사용(예: `deep-research.verdict.json`). 인용 수치는 디스크 verdict와 일치해야 한다(`MEASUREMENT_DRIFT`).
- probe·measurement-suite(`*.workflow.js`)는 자동생성·공장내부 도구 — **손으로 고치지 않는다**(헤더 경고 준수). 고칠 게 있으면 graph.json/skill.json을 고치고 재emit. **produced child 안에는 동봉하지 않는다.**
- runs.json에는 항상 `harness_version` + (CLI로) `git_sha`·`model_id`를 남겨 **재현·감사** 가능하게 한다.
- iteration 보존은 git commit이 담당 — 이전 측정을 덮어쓰지 말고 commit으로 분리.

---

## 12. 원본 prose → CYS 게이트 대응표

| 원본 (prose 권고) | CYS (실행 게이트) | 실행 방식 |
|------------------|------------------|----------|
| "구조를 검증하라" (사람 검토) | `validate_harness.py` 머신체크 세트 | `exit 1` → 생성 중단 |
| "오케스트레이터가 그래프대로 노드를 호명하나" | `GRAPH_SKILL_CONSISTENCY` (프리미티브) | `exit 1` |
| "팀·서브에이전트 둘 다 쓰나(A2)" | `ALL_PRIMITIVES_PRESENT` / `TEAM_EMIT_PRESENT` | `exit 1` |
| "With-skill vs Baseline 동시 실행" | `lift_gate.py` (with sonnet vs haiku baseline) | `register`/`refuse` (exit 0/3) |
| "측정 안 한/진 스킬을 출하 마라" | `LIFT_UNMEASURED`(policy) / `LIFT_REFUSED`(hard) | `exit 1`(refused) |
| "assertion 기반 자동 채점" | lift score + h2h grade, polarity 게이팅 | 결정론 스코어러 |
| "Grader가 채점·교차검증" | 블라인드 opus 채점자 (자기채점 금지) | schema로 출력 강제 |
| "Comparator로 블라인드 비교"(선택) | `h2h_suite` A=C2/B=C3 블라인드 매핑 | n-run, 기록된 매핑 |
| "Analyzer로 통계 패턴" | `h2h_aggregate` variance + lift non-disc 검출 | median/variance/delta |
| "flake를 0점 처리하지 마라" | `tryAgent` 재시도 + drop-not-zero + `n_dropped` | 드롭 필터링 |
| "측정해서 못 이겼으면 이겼다 말하지 마라" | `MEASUREMENT_DRIFT` (verdict 존재·전부 비승리인데 `CYS-WINS` 광고 시 차단; verdict 0개면 통과) | `exit 1` |
| "non-discriminating assertion 제거" | lift/delta가 자동으로 노출(낮은 lift → 의심) | 게이트 산출물 |
| "all agents use opus 금지" (권고) | `TIER_OVERSPEND` V2 머신체크 | `exit 1` |
| "model을 명시하라" | `TIER_MISSING` V1 + `TIER_MISMATCH` V3 | `exit 1` |
| "절대경로 쓰지 마라" | `ABSOLUTE_PATHS` 체크 | `exit 1` |
| "문서 일치(README↔SKILL)" | `DOC_DRIFT` phase-count 체크 | `exit 1` |
| "토큰 비용 높으니 신중히" (권고) | `warrant.py` cost-band + approval BLOCK | 사용자 승인 게이트 |
| "이 스킬 만들 가치 있나" (암묵) | `warrant.classify` Phase -1 verdict | answer-directly/single-agent/build |
| "트리거 near-miss 검증" | (보존) 20쿼리 + 게놈 스킬 충돌 검증 | should/should-NOT |
| "use-case 패리티" | `eval_topology.py` 8 use case 빌드레벨 conform | `exit 0/1` |
| "iteration-N 보존" | git repo + provenance(git_sha/version) | commit history |

> **한 줄 요약.** 원본은 *"어떻게 테스트해야 하는가"*를 잘 가르쳤다. CYS는 그 가르침을 *"테스트하지 않으면 빌드가 실패하고, baseline을 못 이기면 등록이 거부되며, 측정 없이 승리를 광고하면 빌드가 막히고, 비용 승인 없이는 실행이 막힌다"*로 강제한다. 측정이 권고에서 계약으로 바뀐 것 — 그것이 CYS 하네스가 idoforgod/harness 대비 갖는 우위의 핵심이다.
