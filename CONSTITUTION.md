# CYS Harness Creator — CONSTITUTION (불변 절대기준)

> 출처 DNA: AgenticWorkflow `soul.md` (만능줄기세포 게놈). 원본의 *prose 영혼*을 CYS의
> *머신체크 게이트*로 승격한다 — "rules-as-essays → rules-as-assertions".
> 이 문서의 조항은 모든 생성 하네스가 상속(embed)하며, `validate_harness.py`가 강제한다.

## AC-1 — Quality > Everything (품질 최우선)
속도·토큰비용·작업량·시간제약은 **의사결정 기준에서 제외**한다. 유일한 기준은 **최종 산출물 품질**이다.
단계를 줄여 빨리 끝내기보다, 단계를 늘려 품질을 높이는 경로를 선택한다.
- **CYS 강제:** `model-tier-policy.js`가 품질 임계 노드에 최고티어(opus)를 배정 / `warrant.py`가 다층 검증을 비용보다 우선 / 약한 다수(5 weak sub-agents) 대신 강한 소수를 권장.
- **단, 개인용 도구로서:** "품질 우선"이 "무한 비용"은 아니다. 비용은 *무시*하되 사전 비용밴드 승인(`warrant.py`)으로 *가시화*한다.

## AC-2 — Single-File SOT + Single-Writer (단일 진실원·단일 쓰기)
공유 상태는 단일 진실원에 집중하고, 쓰기 권한은 한 주체(오케스트레이터)에게만 있다. 병렬 에이전트는 read-only이거나 자신의 `output-*` 산출물만 쓴다.
- **CYS canonical SOT:** `.harness/MANIFEST.json` (provenance/evolve) + `.harness/graph.json` (불변 계약). 런타임 진행은 Workflow 네이티브 `resumeFromRunId`가 담당 — **별도 state 파일을 만들지 않는다**(2-state 드리프트 금지).
- **CYS 강제:** `harness.lock`(path→node 단일소유) + `write_lock.sh` hook이 비-owner 쓰기 거부 / 모든 SOT 쓰기는 `lib/atomic_write.py`(temp→rename) 경유 / `audit_log`는 **MANIFEST에만** 기록(graph.json 금지 — graph_hash 불변).

## AC-3 — Code Change Protocol (코드 변경 파급분석)
코드를 쓰기·수정·추가·삭제하기 전에 ① 의도 명확화 → ② 영향범위 분석 → ③ 변경 설계를 내부 실행한다. 분석 깊이는 변경 규모에 비례한다(proportionality).
- **CYS 강제:** `/code-review` 게이트가 emit_workflow.py/validate_harness.py 변경 전 CCP 체크리스트 요구 / 변경된 모든 줄이 작업지시로 추적 가능해야 함(외과적 변경).

## 상속 규약 (Stem Cell Genome)
모든 생성 하네스는 위 AC-1/2/3을 **참조가 아니라 임베드**로 상속한다. `harness.md`의
`Inherited DNA:` 섹션에 명시되고, `Gene Expression:` 섹션이 도메인별 발현을 보인다.
`validate_harness.py`의 W1(상속 섹션 존재)·AC-2(단일쓰기)가 위반 시 빌드를 실패시킨다.
