# IMPLEMENTATION-STATUS — M0 실구현 현황 (GROUND TRUTH)

> **이 문서가 다른 모든 reference의 aspirational 서술에 우선한다.** reference가 어떤 기능을 설명하더라도, 실제 emit/validate에 구현됐는지는 여기로 확정한다. (출처: emit_workflow.py·validate_harness.py·warrant.py·graph.schema.json·model-tier-policy.js 실측)

## ✅ M0에 실제 구현됨 (emit/validate가 처리)
- **Topology:** `pipeline`(순차), `dispatch`(**static fan-out + 단일 sink만**), `producer-reviewer`(2노드 경계 루프).
- **Decision-mechanism:** `single`, `majority-vote`(n 2~5, quorum≥1, tie_break), `debate-with-judge`(n, max_rounds≤3, judge), `reflect-then-revise`(max_rounds≤3, critic).
- **게이트:** `validate_harness.py` 머신체크 세트(에러/경고 코드 약 18종) — 위반 시 빌드 실패.
- **모델 티어:** role→tier(gather/extract/format/qa-scan=haiku · voter/debater/reviser=sonnet · synthesis/judge/critic=opus), 필수 `model:`+`model_rationale:`.
- **비용:** warrant.py Phase-1 분류 + 토큰 cost-band(LOW/MED/HIGH).
- **게놈 전수 + RUNTIME.json**(canonical=workflow.js / inherited prompt-runner=대체).
- **측정:** lift_gate(임계 0.2, 독립 블라인드 grader, register/refuse) + h2h(승리마진 15pp, A=C2/B=C3).

## ⏳ M1-deferred (설명은 있으나 **아직 미구현** — 라이브로 쓰지 말 것)
- **`dispatch(dynamic)` / claim / supervisor 동적 할당** — emit는 **static fan-out만** 생성. 동적 할당은 미구현.
- **dispatch 다중 sink reduce** — 단일 sink만(M0). 
- **Expert-pool, Hierarchical-delegation topology** — 미구현(조건부 노드/2단계로 근사하거나 연기).
- **best-of-N race, weighted-ensemble mechanism** — 연기.
- **pACS opt-in, harness import(30개 마이그레이션)** — 연기.

## ❌ 폐기된(원본) 규칙 — 더 이상 적용 안 함
- **"`.claude/commands/`를 비워라(NO_COMMANDS)"** — **폐기됨.** 게놈이 commands(install·maintenance 등)를 정당하게 포함하므로 validate에서 제거됨. 자식은 게놈 commands를 갖는 게 정상. 단 **새 도메인 커맨드를 직접 만들지는 않는다.**
- "모든 에이전트 opus" → role-tier 정책으로 대체.
- "team이 기본" → Mode-A(workflow)가 기본.

## 규약 메모
- **emit 스키마 바인딩:** 노드 output_schema는 workflow.js에 `S.<node_id>_schema`로 인라인된다(예: `S.gather_schema`, `S.verify_schema`). reflect-then-revise critic은 `S.<node_id>_critique`. (에이전트 prose의 "S.findings" 류는 약식 표기 — 실제 바인딩 키는 `S.<id>_schema`.)
- **producer-reviewer topology ≠ reflect-then-revise 강제** — topology(2노드 루프)와 mechanism은 독립. producer-reviewer 안의 reviewer 노드는 어떤 mechanism이든 가질 수 있다(정준 예시 design-decision은 debate-with-judge).
