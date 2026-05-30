# IMPLEMENTATION-STATUS — M0 실구현 현황 (GROUND TRUTH)

> **이 문서가 다른 모든 reference의 aspirational 서술에 우선한다.** reference가 어떤 기능을 설명하더라도, 실제 emit/validate에 구현됐는지는 여기로 확정한다. (출처: emit_orchestrator.py·emit_workflow.py·validate_harness.py·warrant.py·graph.schema.json·model-tier-policy.js 실측)

## 🔀 PIVOT (2026-05-29) — Claude Code 프리미티브 기질로 전환 (P0–P3 구현·검증 완료)

> 배경·전략·설계: `design/pivot-to-claude-primitives-strategy.md`. 런타임 가정 실측: `design/p1-probe-results.md`(GREEN). 23/23 팩토리 테스트 + 새 agent-mode 예제 validate PASS(0/0)로 검증.

**✅ 이번에 실구현됨 (P0–P3):**
- **`emit_orchestrator.py`** — `execution_mode` agent|team|hybrid에서 graph.json → 오케스트레이터 SKILL.md(prose, Agent/TeamCreate 구동) + 노드별 `.claude/agents/*.md`(model·tools·maxTurns frontmatter, Agent가 **런타임 강제** — P-1 실측 확인) + 게놈 active 전수(orchestrator-canonical RUNTIME). agent 모드가 디폴트.
- **graph.schema.json** — execution_mode에 `agent`/`hybrid` 추가, 노드 옵션 `tools`(allowlist)·`review`({agent}) 추가(역호환).
- **hooks** — `gate_or_block.py`(advisory validate_*.py를 exit-2 인터록으로 승격; P-1 Probe 2가 차단 실증) + `budget_block.py`(PreToolUse `Agent|Task|TeamCreate` spawn-count ceiling, 토큰 아님) + `pre_subagent_invocation.py` stdin-무시 버그 수정(R3, advisory 기본 + env-flag hard-block).
- **inherit_genome.py** — 신규 hook 전수, budget_block 배선, SubagentStop timeout 5000→5(CD-5), RUNTIME manifest 오버라이드.
- **validate_harness.py** — RUNTIME_DECLARED **dual-accept**(workflow→cys-mode-a / agent·team·hybrid→`<name>-orchestrator`), GRAPH_SKILL_CONSISTENCY(오케스트레이터가 모든 노드 언급), 프리미티브 모드 budget_block HOOK_REGISTERED.
- **CONSTITUTION** — AC-2(SOT=state.yaml 라이브 진행·단일쓰기), AC-1(런타임 spawn-count ceiling) 개정.

**⏳ 피벗 잔여 (P4–P5, 미구현):**
- **P4 reference 재작성** — `architecture-patterns.md`·`graph-and-orchestration.md`·`testing-and-measurement.md`는 여전히 'orchestrator==workflow.js' 전제 서술. 본 문서가 우선하며, 그 3종은 후속 재작성 대상. `MEASUREMENT_DRIFT` 빌드체크는 **구현됨**(`validate_harness.py`, tested) — 단 produced-harness 내부 README/SKILL만 스캔하므로 factory `design/` 문서는 별도 factory 테스트(`TestMeasurementDrift`, M8에서 `design/` 스캔 확장)로 커버.
- **P5 라이브 dogfood — 실행/활성화 PROVEN, n≥5 h2h는 미완(전용 런 필요)**. `design/p5-dogfood-results.md`:
  - ✅ **실행/AWF 활성화 실증**: agent-mode dogfood를 라이브 `claude` 세션으로 실행 → 4 서브에이전트 spawn(researcher/fetcher/verifier/**reviewer**), 커스텀 agentType resolve + **L2 적대적 reviewer가 Mode-A 휴면→LIVE 발화**, PostToolUse(work_log: Agent×4)·SubagentStop hook 발화. 프리미티브 하네스가 실제로 돌고 게놈이 active함을 전체 하네스 수준에서 확인.
  - ⏸️ **n≥5 h2h 재측정 — 시도했으나 계정 사용량 한도에 막힘(2026-05-30)**: 유일 stamped h2h는 여전히 n=1 BASELINE-WINS −16.67pp(Mode-A 측정). 동일 deep-research 과제로 C2(피벗 하네스) vs C3 ×5 blind 측정을 시도 → C3 단일 run ~5분(7388B 산출)이나 무거운 run 1–2회로 **세션 사용량 한도 도달**("resets 11:20am KST"). n≥5는 단일 quota 윈도우로 불가. **resumable 드라이버**(`_workspace/h2h/run_h2h.py`: timeout 회수 + 점진 저장 + resume + 한도 감지)로 **리셋 윈도우마다 반복 실행해 누적**하면 완료. 약한 n<5을 n=5로 **날조하지 않음**(+37.5pp 교훈). **team 모드 기본승격은 이 결과에 게이트**(현재 agent 우선).
- R9(PostToolUse return-validator)·team 멤버 nested hook 발화·Stop 스냅샷 ap_state 경로는 추가 검증 필요.

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
