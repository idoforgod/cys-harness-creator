---
name: design-decision-orchestrator
description: "design-decision 하네스를 실행하는 오케스트레이터. 기술 설계 결정/아키텍처 선택/트레이드오프 판정 요청 시 사용. 후속: 결정 재검토, 대안 비교, 설계안 보완, 다시 판정, 이전 결정 개선 요청 시에도 반드시 이 스킬을 사용."
---

# Design Decision Orchestrator (Mode A — Workflow 런타임)

`graph.json`의 사람용 뷰. 실제 실행은 `.harness/workflow.js`(emit 결과)를 `Workflow({scriptPath})`로 호출한다.
결정론 서브에이전트 producer-reviewer 루프. 에이전트 간 실시간 comms 없음(Mode A).

## 실행 모드: workflow (결정론 서브에이전트)

## 토폴로지 (2 Phase, producer-reviewer 루프)

| Phase | 노드 | 에이전트 | 모델 | 메커니즘 | 출력 |
|------|------|---------|------|---------|------|
| Phase 1 | propose | proposer | opus | single | `_workspace/01_propose/design.json` |
| Phase 2 | adjudicate | debater | sonnet(토론자) + opus(심판) | debate-with-judge (n=2, max_rounds=2) | `_workspace/02_adjudicate/verdict.json` |

루프 종료 조건: `verdict.approved=true` 또는 producer max_rounds=3 도달.

## 실행

1. **컨텍스트 확인:** `_workspace/` 존재 여부로 초기/재실행/부분재실행 판별.
2. **입력:** 결정 문항을 `_workspace/00_input/decision.md`에 저장.
3. **비용 승인:** `python3 warrant.py --graph .harness/graph.json` → 비용 밴드(토큰) 표시 → 승인 대기(approval_required=true).
4. **실행:** `Workflow({ scriptPath: ".harness/workflow.js", args: { query } })`. `budget.total`(300000)이 하드 ceiling.
5. **재개:** 중단 시 `Workflow({ scriptPath, resumeFromRunId })` — 변경 안 된 노드는 캐시, 변경 노드부터 라이브.

## 데이터 흐름

```
decision.md → [propose:opus] → [adjudicate: debater×2 sonnet → judge opus] → approved? ─┐
                   ▲                                                                      │ no
                   └──────────────────── 재제안(concerns 반영) ────────────────────────┘
                                                          yes → verdict.json (approved/chosen/rationale)
```

## 에러 핸들링

- 노드 실패: graph.json `on_exhaust`(propose=escalate, adjudicate=proceed-with-gap).
- 예산 초과: `ensure()` 가드가 토론 라운드 fan-out 전 차단, `budget.total` 도달 시 `agent()` throw → 루프가 현재 draft 반환.
- 무한루프 방지: emitter가 producer max_rounds(3)로 루프를 상한. 그 안에 미승인이면 가장 정제된 design을 반환.

## 테스트 시나리오

- **정상:** decision → propose → adjudicate가 `approved=true` → 루프 종료, 채택 design 반환.
- **루프:** adjudicate가 `approved=false` + `concerns[]` → propose가 revision_note와 함께 재제안 → 재심사. max_rounds 도달 시 현재 draft로 종료.
