---
name: deep-research-orchestrator
description: "deep-research 하네스를 실행하는 오케스트레이터. 심층 리서치/조사/팩트체크 요청 시 사용. 후속: 리서치 재실행, 결과 업데이트, 보완, 다시 조사, 이전 결과 개선 요청 시에도 반드시 이 스킬을 사용."
---

# Deep Research Orchestrator (Mode A — Workflow 런타임)

`graph.json`의 사람용 뷰. 실제 실행은 `.harness/workflow.js`(emit 결과)를 `Workflow({scriptPath})`로 호출한다.
결정론 서브에이전트 파이프라인. 에이전트 간 실시간 comms 없음(Mode A).

## 실행 모드: workflow (결정론 서브에이전트)

## 파이프라인 (4 Phase)

| Phase | 노드 | 에이전트 | 모델 | 메커니즘 | 출력 |
|------|------|---------|------|---------|------|
| Phase 1 | gather | researcher | haiku | single | `_workspace/01_gather/findings.json` |
| Phase 2 | fetch | fetcher | haiku | single | `_workspace/02_fetch/findings.json` |
| Phase 3 | verify | verifier | sonnet(+opus critic) | reflect-then-revise (max_rounds=2) | `_workspace/03_verify/findings.json` |
| Phase 4 | synthesize | synthesizer | opus | single | `_workspace/04_report/report.json` |

## 실행

1. **컨텍스트 확인:** `_workspace/` 존재 여부로 초기/재실행/부분재실행 판별.
2. **입력:** 쿼리를 `_workspace/00_input/query.md`에 저장.
3. **비용 승인:** `python3 warrant.py --graph .harness/graph.json` → 비용 밴드(토큰) 표시 → 승인 대기(approval_required=true).
4. **실행:** `Workflow({ scriptPath: ".harness/workflow.js", args: { query } })`. `budget.total`(600000)이 하드 ceiling.
5. **재개:** 중단 시 `Workflow({ scriptPath, resumeFromRunId })` — 변경 안 된 노드는 캐시, 변경 노드부터 라이브.

## 데이터 흐름

```
query.md → [gather:haiku] → [fetch:haiku] → [verify:reflect critic=opus/reviser=sonnet] → [synthesize:opus] → report.json
```

## 에러 핸들링

- 노드 실패: graph.json `on_exhaust`(gather/fetch/verify=proceed-with-gap, synthesize=escalate). 1회 retry 후 부분결과로 진행.
- 예산 초과: `ensure()` 가드가 fan-out 전 차단, `budget.total` 도달 시 `agent()` throw → 파이프라인 부분결과 반환.
- 빈 입력/스킵: 다운스트림 노드가 null prev 수신 → degraded 진행(크래시 없음), 최종 로그에 표기.

## 테스트 시나리오

- **정상:** query → 4 Phase 순차 → `report.json`(title, markdown, citations) 생성.
- **에러:** verify critic이 round 0에서 미승인 → reviser 1회 → round 1 재비평 → max_rounds 도달 시 현재 draft로 synthesize 진행.
