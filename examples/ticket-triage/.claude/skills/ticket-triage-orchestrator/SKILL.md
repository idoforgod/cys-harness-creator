---
name: ticket-triage-orchestrator
description: "ticket-triage 하네스를 Claude Code 프리미티브(Agent/TeamCreate)로 실행하는 오케스트레이터. 'ticket-triage' 관련 작업·생성·분석 요청 시 사용. 후속: 다시 실행, 재실행, 업데이트, 수정, 보완, 'ticket-triage의 일부만 다시', 이전 결과 기반 개선 요청 시에도 반드시 이 스킬을 사용."
---
# ticket-triage Orchestrator

graph.json(불변 계약)에서 emit된 오케스트레이터. 산출 하네스를 **라이브 Claude Code 호스트 세션**에서
실행하며, 이 세션에 상속된 AWF 게놈 hook(컨텍스트 보존·보안·SubagentStop)이 발화하고, 각 노드의
`.claude/agents/<agent>.md` frontmatter(model·tools·maxTurns)가 Agent 도구에 의해 런타임 강제된다.

## 실행 모드: agent (기본=agent; team은 P5 입증 후 승격)

## 에이전트 구성

| 노드 | agent | model | mechanism | tools | 출력 |
|---|---|---|---|---|---|
| classify_category | classifier | sonnet | majority-vote | Read, Glob, Grep, WebSearch | _workspace/01_category/classification.json |
| classify_priority | prioritizer | sonnet | majority-vote | Read, Glob, Grep, WebSearch | _workspace/02_priority/priority.json |
| route | router | haiku | single | Read, Write, Glob, Grep | _workspace/03_route/routing.json |

## 워크플로우

### Phase 0: 컨텍스트 + SOT 초기화
1. `<harness>/` 존재로 분기: 초기 / 재실행 / 부분 재실행 / 마이그레이션.
2. `.harness/state.yaml`(SOT)을 작성/갱신한다 — **오케스트레이터 단독 쓰기**. 필드:
   `current_step, outputs{}, budget{spawns_used:0, max_spawns:<warrant fanout 합>}, pacs{}, audit_log[]`.
   state.yaml 작성이 ap_state-gated AWF 기능(SOT 스키마·autopilot·Decision Log·SOT-restore)을 깨운다.
3. 재실행이면 첫 단계로 `state.yaml` + 최신 `.claude/context-snapshots/latest.md`를 읽어 맥락 복원.

### Phase 1: 비용 승인
1. `python3 ../../warrant.py --graph .harness/graph.json` 로 비용밴드 표시.
2. `budget.approval_required=true`이면 사용자 'approve' 대기 후 진행. 승인은 state.yaml audit_log에 기록.
3. `budget.max_spawns`를 warrant fanout 합으로 설정 → 런타임 `budget_block.py`(PreToolUse)가 spawn 초과 시 exit-2 차단.

### Phase 2: 노드 실행 + 품질 게이트
**실행 모드: agent** — toposort 순서로 노드를 spawn하고, 각 노드 후 품질 게이트를 통과시킨다.
spawns_used를 spawn마다 +1(단일쓰기).

- **classify_category** (`classifier`, mech=majority-vote): `Agent(subagent_type="classifier", model="sonnet")` — 입력=Phase 1 입력(query), 반환=JSON(schemas/classification.json 스키마 준수).
  - 3개 `Agent`를 병렬 spawn(독립 투표) → quorum 2로 다수결 집계.
- **classify_priority** (`prioritizer`, mech=majority-vote): `Agent(subagent_type="prioritizer", model="sonnet")` — 입력='classify_category' 노드 출력, 반환=JSON(schemas/priority.json 스키마 준수).
  - 3개 `Agent`를 병렬 spawn(독립 투표) → quorum 2로 다수결 집계.
- **route** (`router`, mech=single): `Agent(subagent_type="router", model="haiku")` — 입력='classify_priority' 노드 출력, 반환=JSON(schemas/routing.json 스키마 준수).

**노드별 품질 게이트(autopilot-execution.md 순서, 각 단계 산출물 작성 직후):**
- **L0 Anti-Skip**: `python3 ../../templates/hooks/gate_or_block.py .claude/hooks/scripts/validate_pacs.py --check-l0 --step <N>` (산출물 존재+≥100B).
- **L1 Verification**: `gate_or_block.py validate_verification.py --step <N>` (기능 목표 100% 달성).
- **L1.5 pACS**: `gate_or_block.py validate_pacs.py --step <N>` (Pre-mortem + F/C/L min, RED 차단).
- **L2 Adversarial Review** (review 노드만): reviewer/fact-checker spawn 후 `gate_or_block.py validate_review.py --step <N>`.
- FAIL → `diagnose_context.py` → `validate_diagnosis.py`, `validate_retry_budget.py` 예산 내 재시도.
> `gate_or_block.py`가 advisory validator(exit 0)를 **exit-2 인터록**으로 승격하므로, 게이트 FAIL이 단계를 실제로 멈춘다.

### Phase 3: 통합 산출 + 측정
1. 마지막 노드 출력을 최종 산출물로 기록(state.yaml outputs).
2. `git init && git add -A && git commit`(rollback substrate).
3. (선택) head-to-head: `evals/ticket-triage.scorecard.json` 기준 C2(이 하네스) vs C3(no-harness) n≥5 → `h2h_aggregate.py`.

## 비용 거버넌스
사전: warrant 비용밴드 승인. 런타임: `budget_block.py` spawn-count ceiling(exit-2). 토큰 tally는 advisory.

## 에러 핸들링
| 상황 | 전략 |
|------|------|
| 노드 1회 실패 | 1회 재시도(retries), 재실패 시 on_exhaust(proceed-with-gap/escalate) |
| 게이트 FAIL | abductive diagnosis → 예산 내 재시도 → 초과 시 사용자 에스컬레이션 |
| spawn 초과 | budget_block exit-2 — graph.budget 상향 또는 fan-out 축소 |
| 상충 데이터 | 삭제 금지, 출처 병기 |

## 테스트 시나리오
- 정상: query 입력 → 노드 순차 실행 + 게이트 PASS → 최종 산출물 생성.
- 에러: 한 노드 FAIL → diagnosis → 재시도 → 부분 결과로 진행, 보고서에 누락 명시.
