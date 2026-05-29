---
name: ticket-triage-orchestrator
description: "ticket-triage 하네스를 실행하는 오케스트레이터. 지원 티켓 분류/우선순위/라우팅 요청 시 사용. 후속: 티켓 재분류, 큐 재배정, 우선순위 재평가, 다시 트리아지 요청 시에도 반드시 이 스킬을 사용."
---

# Ticket Triage Orchestrator (Mode A — Workflow 런타임)

`graph.json`의 사람용 뷰. 실제 실행은 `.harness/workflow.js`(emit 결과)를 `Workflow({scriptPath})`로 호출한다.
결정론 서브에이전트 dispatch. 에이전트 간 실시간 comms 없음(Mode A).

## 실행 모드: workflow (결정론 서브에이전트, topology=dispatch)

## 파이프라인 (3 Phase)

| Phase | 노드 | 에이전트 | 모델 | 메커니즘 | 출력 |
|------|------|---------|------|---------|------|
| Phase 1 | classify_category | classifier | sonnet | majority-vote (n=3, quorum=2, tie_break=first) | `_workspace/01_category/classification.json` |
| Phase 2 | classify_priority | prioritizer | sonnet | majority-vote (n=3, quorum=2, tie_break=first) | `_workspace/02_priority/priority.json` |
| Phase 3 | route | router | haiku | single | `_workspace/03_route/routing.json` |

Phase 1·2는 dispatch fan-out으로 **병렬** 실행, Phase 3은 두 승자를 fan-in 하는 단일 sink.

## 실행

1. **컨텍스트 확인:** `_workspace/` 존재 여부로 초기/재실행/부분재실행 판별.
2. **입력:** 티켓 본문을 `_workspace/00_input/ticket.md`에 저장.
3. **비용 승인:** `python3 warrant.py --graph .harness/graph.json` → 비용 밴드(토큰) 표시 → 승인 대기(approval_required=true).
4. **실행:** `Workflow({ scriptPath: ".harness/workflow.js", args: { ticket } })`. `budget.total`(120000)이 하드 ceiling.
5. **재개:** 중단 시 `Workflow({ scriptPath, resumeFromRunId })` — 변경 안 된 노드는 캐시, 변경 노드부터 라이브.

## 데이터 흐름

```
ticket.md → ┌─ [classify_category: sonnet majority-vote n=3] ─┐
            │                                                 ├─→ [route: haiku single] → routing.json
            └─ [classify_priority: sonnet majority-vote n=3] ─┘
```
route는 fanned `[classification, priority]` 배열을 받아 queue·sla_hours·summary로 병합한다.

## 에러 핸들링

- 노드 실패: graph.json `on_exhaust`(classify_*=proceed-with-gap, route=escalate). classify는 1회 retry 후 부분결과로 진행.
- 정족수 미달: reduceMajority가 quorum 미달이어도 최빈 ballot(또는 tie_break=first)을 반환 — null 폭주를 막는다.
- 예산 초과: `ensure()` 가드가 fan-out 전 차단, `budget.total` 도달 시 `agent()` throw → 부분결과 반환.
- 한쪽 축 누락: route가 null 원소 수신 → 안전 기본값(other→triage_backlog, P3→72h)으로 degraded 진행, `summary`에 표기.

## 테스트 시나리오

- **정상:** ticket → Phase 1·2 병렬 majority-vote(각 3 ballot) → Phase 3 병합 → `routing.json`(category, priority, queue, sla_hours, summary) 생성.
- **에러:** 한 노드가 3개 서로 다른 ballot 반환(정족수 미달) → tie_break=first로 최초 ballot 선택 → route가 병합 진행.
