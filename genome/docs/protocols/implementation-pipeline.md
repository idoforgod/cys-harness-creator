# Implementation Pipeline Protocol — 워크플로우 구현 표준 프로세스

- Status: **v1.0 (최초 버전, 2026-05-12)**
- Scope: 본 프로젝트(AgenticWorkflow)에서 새 워크플로우를 구현할 때 적용되는 범용 구현 프로세스. LLM 코어 시스템·결정론 시스템·하이브리드 시스템 모두에 적용.
- 절대 기준: 1(품질 최우선) → 2(SOT) → 3(CCP)
- **본 파일 ADR**: **ADR-059 (최초 버전 — 워크플로우 구현 표준 프로세스 + Skill-driven SOT + 3축 통합)**
- **W1 인스턴스 historical reference**: ADR-052·053 (W1 FVC-Profiler 인스턴스 — 본 파일 v1.0 일반화 source. deprecation 처리됨)

> 이 문서는 워크플로우 제작의 절차적 SOT다. 어떤 워크플로우를 만들든 이 프로세스를 따른다. Phase 단축·생략은 ADR 등록을 통해서만 가능하다.

---

## §-1. Skill Toolkit (mattpocock-skills binding)

본 프로토콜의 운용 도구는 다음 Claude Code 스킬을 표준으로 채택한다. 모든 Phase의 "사용자 승인" 게이트는 아래 스킬의 산출물이 존재함을 묵시적 전제로 한다.

| 스킬 | 용도 | 본 프로토콜에서의 주 호출 위치 |
|---|---|---|
| `/setup-matt-pocock-skills` | 이슈 트래커·triage 라벨·도메인 문서 레이아웃 1회 셋업 | §3 "Skill Setup" 0차 행, §4 Step 0 |
| `/grill-me` | 비코드(의도 정렬·정책 결정) 인터뷰 | Phase 0 (도메인 컨텍스트가 없을 때), §7 6+1+1대 결정 |
| `/grill-with-docs` | 도메인 모델·`CONTEXT.md`·ADR과 충돌하는 계획을 적대적으로 다그치며 즉석에서 문서 갱신 | Phase 0(기존 도메인 위), 1, 1.5, 2-PRD, 3.7, 횡단 A·D, §7 결정 #7 |
| `/to-prd` | 누적된 대화 컨텍스트를 PRD로 응결해 이슈 트래커에 게시 | Phase 2-PRD |
| `/to-issues` | PRD/계획을 vertical-slice(tracer-bullet) 단위 이슈로 분해 | Phase 4 진입 직전, §7 결정 #3 자동 PR 생성 |
| `/triage` | 이슈를 5-state 머신(`needs-triage` → `needs-info` / `ready-for-agent` / `ready-for-human` / `wontfix`)으로 운영 | §4 Step 5, Phase 6, 횡단 D |
| `/tdd` | 한 테스트 → 한 구현의 vertical-slice red-green-refactor | Phase 4 (a~f) 전체 |
| `/diagnose` | 6-Phase 진단 루프(feedback loop 우선) | Phase 3.5 게이트 보조, Phase 5a 모든 버그, 횡단 D |
| `/improve-codebase-architecture` | Module / Interface / Depth / Seam 어휘로 deepening 기회 발굴 | Phase 4f 직후 1-pass(횡단 C), Phase 5a 후속, **§7 결정 #8 정기 회수** |
| `/zoom-out` | 모듈 지도 재요청 | Phase 2.5 종료, Phase 3 종료 게이트, Phase 5a 진입 점검, **Phase 6 운영 단계 sanity check** |

**전제 조건**: 신규 레포에서는 본 프로토콜 진입 전에 `/setup-matt-pocock-skills`를 1회 실행해 `docs/agents/issue-tracker.md`, `docs/agents/triage-labels.md`, `docs/agents/domain.md`가 생성되어 있어야 한다. 이 셋업이 없으면 `/to-prd`·`/to-issues`·`/triage`·`/diagnose`·`/tdd`·`/improve-codebase-architecture`·`/zoom-out`이 컨텍스트 부족 상태로 동작한다.

---

## §0. 설계 원칙

본 프로토콜은 **세 축의 결합**이다.

1. **전통 SW 엔지니어링 축**: 의도 → 인터페이스 → 명세 → 절차 → 구현 → 검증 (Phase 0~5).
2. **하네스 엔지니어링 축**: LLM 코어 시스템 고유의 활동 통합 — Eval Suite, Prompt Engineering, Observability, Failure Mode, Cost-Latency, Safety, Continuous Learning.
3. **하네스 운용 축 (Skill-driven SOT)**: 모든 Phase의 도메인 어휘는 `CONTEXT.md`에 응결되고, 가역하기 어려운 결정은 `docs/adr/`에 기록되며, 작업 단위는 이슈 트래커의 `needs-triage` → `ready-for-agent` 상태 머신을 따른다. ADR 등록은 `/grill-with-docs`의 **3-조건**(Hard to reverse · Surprising without context · Real trade-off)을 모두 충족할 때만 한다. 그 외의 도메인 어휘 변동은 ADR이 아니라 `CONTEXT.md` 인라인 갱신으로 처리한다.

각 Phase의 산출물이 다음 Phase의 검증 가능한 입력 제약이 되는 구조로, 절대 기준 1(품질)을 프로세스 차원에서 보장한다. 도구 레벨에서는 §-1 Skill Toolkit이 그 검증 게이트를 자동화한다. **운영 단계의 학습 회로**는 Phase 5a의 발견이 Phase 4f의 다음 회차로, Phase 6의 신호가 §7 결정 #8(정기 아키텍처 회수)을 통해 다시 Phase 4f의 입력으로 환류되는 구조로 닫혀 있다.

---

## §1. 전체 단계 흐름

각 행의 "핵심 산출물"과 "종료 게이트"는 §-1 Skill Toolkit의 슬래시 커맨드 호출을 표준 동작으로 가정한다.

| # | Phase | 목적 | 핵심 산출물 (패턴) | 종료 게이트 |
|---|---|---|---|---|
| **0** | Intent Alignment | 사용자와의 의도·목표·품질 수준 정렬 | **분기 조건** [§4 Step 4 verbatim "*비코드 의도 정렬은 `/grill-me`, 도메인 위 작업이면 처음부터 `/grill-with-docs`로 시작*" 정합]: **(a) 도메인 컨텍스트 없음 → `/grill-me`** (비코드 의도 정렬·정책 결정 인터뷰, 한 번에 한 질문) **(b) 기존 도메인 위 → `/grill-with-docs`** (도메인 모델·`CONTEXT.md`·ADR 적대적 다그침 + 즉석 문서 갱신). 산출물 = 세션 트랜스크립트 + 합의 메모 + ADR 초안 + (해당 시) `CONTEXT.md` 초안 갱신 | 사용자 승인 + 합의 사항이 `CONTEXT.md`(있는 경우)에 반영 + **트랜스크립트가 "한 번에 한 질문" 원칙을 지켰음을 확인** + **코드베이스 탐색으로 답할 수 있는 질문은 사용자에게 묻지 않고 직접 탐색했음을 확인** |
| **1** | Interface | 본 워크플로우와 다운스트림 시스템의 인터페이스 동결 | `{workflow}-output-contract.md` (Interface = 호출자가 알아야 할 모든 것: 타입·invariant·error mode·ordering·config) | **인터페이스 contract 자체는 ADR 3-조건을 자동 충족하므로 ADR 등록**. 단 contract 안의 세부 결정 중 3-조건을 충족하지 않는 항목은 ADR이 아니라 `CONTEXT.md`로만 흡수 + `/grill-with-docs`로 contract와 도메인 모델의 정합 확인 |
| **1.5** | Contract Stress Test | 인터페이스 적대적 검증 (경계 케이스·악성 입력·확장성·버전 호환) | Stress Report + contract v1.x 패치 + vertical-slice 시나리오 ≥3 + adversarial review 트랜스크립트 | @reviewer + @fact-checker 통과 + `/grill-with-docs` cross-check로 `CONTEXT.md` 충돌 0건 |
| **2** | Specification | 명세 4문서 작성 | PRD + Functional-Spec + Test-Plan + Eval-Plan | 사용자 승인 |
| ↳ 2-PRD | PRD | mattpocock 표준 PRD 7섹션 + IPP 하네스 5섹션 | `{workflow}-prd.md` (이슈 트래커에 `needs-triage` 라벨로 게시) | **PRD 작성 전: 이 PRD가 만들 모듈 후보를 스케치하고, deep modules 후보를 추출하며, 사용자에게 "어느 모듈에 테스트가 필요한지"를 확인 완료** + `/to-prd` 산출물이 이슈 트래커에 게시됨 **+ 도메인 위 작업이면 `/grill-with-docs`로 PRD의 도메인 어휘·`CONTEXT.md` 충돌 cross-check 완료** [§-1 Skill Toolkit verbatim "*/grill-with-docs ... Phase 0(기존 도메인 위), 1, 1.5, 2-PRD, 3.7, 횡단 A·D*" 호출 위치 정합] |
| ↳ 2-Spec | Functional-Spec | 알고리즘 의사코드 (도메인 결정론·LLM 통합 분기 다이어그램) — 모듈 구조는 PRD에 이미 deep modules 후보로 들어있음 | `{workflow}-spec.md` | — |
| ↳ 2-Test | Test-Plan | 단위·통합 테스트 (결정론 영역) — **단위 테스트는 내부 구현이 아니라 모듈 인터페이스를 검증한다** | `{workflow}-test-plan.md` | 인터페이스-만-테스트 게이트 통과 + **테스트 슈트는 *행동 카탈로그* 형태로만 보관(실제 실패 테스트로의 변환은 4a에서 1건씩만 — horizontal slicing 사전 차단)** |
| ↳ 2-Eval | Eval-Plan | Behavioral·Adversarial·Regression·Calibration evals — **prompt-aware tests 포함** (LLM 분포 영역) | `{workflow}-eval-plan.md` | — |
| **2.5** | Build-Time Asset Curation | 정적 자산 합성 + 사용자 큐레이션 | 도메인 정적 자산 (reference docs · 결정론 lookup table · controlled vocabulary 등) | 사용자 큐레이션 완료 + 자산이 도입한 신규 도메인 용어가 `CONTEXT.md`에 등재 + **`/zoom-out` 식 자산 지도(자산 ↔ 호출 모듈) 1매 생성** |
| **3** | Procedure Design | 워크플로우 단계별 절차 설계 | `workflows/{name}/workflow.md` | DNA 유전 P1 검증 통과 + `/zoom-out` 1회 실행으로 부모 시스템 내 위치를 모듈 지도로 부착 + **`workflow.md`의 모든 단계 명칭이 `CONTEXT.md`에 등재된 어휘만 사용**(정형 게이트로 격상) |
| **3.5** | Workflow Dry-Run | 가상 시나리오 2-3개로 종이 위 시뮬레이션 | Dry-Run Report + `workflow.md` 패치 | 모든 Verification 자동 검증 가능 확인 (= `/diagnose` Phase 1의 deterministic / fast / sharp feedback loop 체크리스트 통과) + **dry-run 검증 자동화의 정량 목표 = 2초 deterministic 루프**(미달 시 루프 자체를 product로 보고 개선 후 재진입) |
| **3.7** | Prompt Engineering | `workflow.md`의 추상 단계를 실제 프롬프트로 변환 | System prompts + Few-shot 예시 큐레이션 + Prompt versioning 체계 (프롬프트의 도메인 용어 = `CONTEXT.md` 표기) | Eval-Plan의 prompt-aware test 통과 + `/grill-with-docs`로 예시별 용어 적정성 다그침 완료 + **prompt-aware test의 어서션이 모델 내부 추론 토큰이 아니라 *공개 출력의 행동*을 검증함을 확인**(모델 버전 의존적 회귀 폭탄 방지) |
| **4** | Implementation (TDD via `/tdd`, vertical slice per behavior) | TDD 사이클로 구현 — **horizontal slicing 금지**. **Phase 4 진입 직전 `/to-issues`로 PRD/계획을 vertical-slice(tracer-bullet) 단위 이슈로 분해 의무** [§-1 Skill Toolkit verbatim "*/to-issues \| PRD/계획을 vertical-slice(tracer-bullet) 단위 이슈로 분해 \| Phase 4 진입 직전, §7 결정 #3 자동 PR 생성*" 호출 위치 정합] | 코드·Hook·Sub-agent 일체 | 4f 통과 |
| ↳ 4a | Test 슈트 골격 **[`/tdd` RED 단계 강제]** | Test-Plan / Eval-Plan을 *행동 카탈로그*로 변환. 한 행동당 한 테스트만 실패 상태로 미리 둠. 나머지는 카탈로그 형태로 보관. **`/tdd` red-green-refactor 사이클의 RED 진입** [§-1 verbatim "*/tdd \| 한 테스트 → 한 구현의 vertical-slice red-green-refactor \| **Phase 4 (a~f) 전체***" 호출 위치 정합] | 행동 카탈로그 + 첫 tracer-bullet 실패 테스트 | tracer-bullet 1건이 RED 상태 |
| ↳ 4b | 빌드 타임 자산 코드화 **[`/tdd` 자산 무결성 테스트 강제]** | Phase 2.5 자산을 import 가능 형태로. **자산 무결성 테스트는 `/tdd` 양식 RED→GREEN 통과** (public lookup API 레벨) | `assets/*` lookup 모듈 | 자산 무결성 테스트가 **public lookup API 레벨**에서 PASS (내부 구조 비교 금지) |
| ↳ 4c · 4d | 행동별 RED → GREEN 반복 **[`/tdd` 메인 사이클 강제]** | 결정론(4c) / LLM 통합(4d) 경계는 **모듈 단위가 아니라 행동 단위**로 분기. 각 행동마다 한 테스트 → 한 구현 (= `/tdd` red-green-refactor verbatim 양식, 각 행동별 1 사이클) | 결정론 모듈 코드 + LLM 통합 모듈 코드 | 4a 카탈로그의 모든 행동이 RED→GREEN을 1주기 통과 + 4d Free-부분 편차 KPI 통과 + **LLM 통합 모듈 디버깅 시 모든 임시 로그는 `[DEBUG-xxxx]` 태그 의무**(5a의 "DEBUG 0건" 게이트와 직결) |
| ↳ 4e | HITL · Hook · Sub-agent · Safety · Observability 통합 **[`/tdd` E2E 시나리오 강제]** | 게이트 인터페이스 + Safety filter + 관측성 hooks. **E2E 단일 시나리오는 `/tdd` 양식 RED→GREEN 통과** + `/diagnose` Phase 1 deterministic 2초 루프 결합 | `.claude/agents/*.md`, `settings.json`, Safety Layer, Observability dashboard | E2E 단일 시나리오가 `/diagnose` Phase 1식 *deterministic 2초 루프*로 통과 |
| ↳ 4f | 통합 테스트 (horizontal 허용 격리 구간) **[`/tdd` 4a~4e 누적 검증 강제]** | 모든 sub-phase 결합 검증. 본 절에 한해 horizontal 통합 테스트 허용. **4a~4e의 `/tdd` 사이클로 만들어진 모든 단위·통합·eval 슈트 GREEN 확인 + `/improve-codebase-architecture` 1-pass 의무 실행** | 통합 테스트 통과 보고 + **모듈별 deletion test 결과 1줄 기록(살아남음 / 흩어짐)** | 모든 단위·통합·eval 슈트 GREEN + **`/improve-codebase-architecture` 1-pass 의무 실행** + **deletion test에서 "흩어짐" 판정 모듈은 5a 진입 금지 — 통합 또는 삭제 후 4f 재실행** + **5a에서 환류된 'no-seam findings'를 본 회차의 입력으로 처리** |
| **5a** | Unit / Integration / Eval Validation + Failure Mode Coverage | **Phase 5a 진입 시 `/zoom-out` 1회 실행으로 모듈 지도 재확인** [§-1 Skill Toolkit verbatim "*/zoom-out \| 모듈 지도 재요청 \| Phase 2.5 종료, Phase 3 종료 게이트, **Phase 5a 진입 점검**, Phase 6 운영 단계 sanity check*" 호출 위치 정합] + Test-Plan + Eval-Plan + 실패 모드 카탈로그 자동 검증. 발견된 모든 버그는 `/diagnose` 6-Phase 강제 (feedback loop → reproduce → hypothesise → instrument → fix+regression test → cleanup+post-mortem) | KPI 보고 + 실패 모드 회귀 테스트 통과 + 각 버그의 commit / PR 메시지에 **(a) 맞은 가설 + (b) (있다면) 아키텍처 hand-off 권고 + (c) (있다면) `/improve-codebase-architecture` 트리거 사유** 3종 세트 명시 | 전 항목 PASS + `grep '\[DEBUG-'` 결과 0건 + 아키텍처 hand-off 필요 여부 판단 완료 + **올바른 seam이 없어 회귀 테스트를 적절히 만들지 못한 버그는 'no-seam finding'으로 risk-register에 등재 + Phase 4f의 다음 회차 `/improve-codebase-architecture` 1-pass에 자동 입력**(폐쇄 학습 루프) |
| **5b** | Acceptance Test | 골든 페르소나·골든 시나리오 실제 실행 + 사용자 평가 | 도메인 KPI 실증 보고 (수용 결정의 근거 문장이 PRD의 Implementation Decisions와 1:1 대응) + **수용 평가 보고는 `CONTEXT.md` 어휘로만 작성** | 사용자 수용 |
| **6** | Continuous Learning Setup | 운영 단계 진입 전 6+1+1대 정책 결정 + 인프라 활성화 | ADR + Feedback Logger · Drift Detector · Pattern Miner · Asset Updater · Regression Guard · Recalibration Pipeline (모든 메트릭 명칭이 `CONTEXT.md` 어휘로 명명) + `/triage` 자동 등록 파이프라인 + **`/zoom-out` 자동 트리거 파이프라인**(신규 메트릭/사건이 임계 초과 시 모듈 지도 1매 자동 생성 → 인스턴스 파이프라인 문서에 첨부) + **§7 결정 #8(정기 아키텍처 회수) 스케줄러** | 사용자 정책 승인 |

---

## §2. 횡단 활동 (모든 Phase에 지속 적용)

| # | 활동 | 적용 방식 |
|---|---|---|
| **A** | Decision Log (ADR) | 모든 Phase의 설계 결정을 `DECISION-LOG.md`에 ADR로 등록. 단 ADR은 `/grill-with-docs`의 **3-조건**(Hard to reverse · Surprising without context · Real trade-off)을 모두 충족할 때만 만든다. 그 외의 도메인 어휘 변동은 `CONTEXT.md` 인라인 갱신으로 처리해 ADR 인플레이션을 방지. |
| **B** | Context Preservation | Hook 시스템(`save_context.py` / `restore_context.py`)이 모든 Phase에서 자동 작동. 컨텍스트 직렬화 포맷에 **`CONTEXT.md` 해시 · `docs/adr/` 최신 ADR 번호**를 함께 저장하여 세션 복원 시 도메인 어휘 동기화. |
| **C** | Adversarial Review | 각 Phase 종료 게이트에서 @reviewer + @fact-checker 적대적 검토. **Phase 4f 직후 `/improve-codebase-architecture` 1-pass를 의무화** — deletion test에서 "흩어짐" 판정 모듈은 Phase 5a 진입 금지. **Phase 5a의 'no-seam findings'는 Phase 4f의 다음 회차 1-pass 입력으로 자동 환류**. Phase 1.5는 활동 자체가 적대적 검증이므로 중복 제외. |
| **D** | Risk Register + Failure Mode Library | `{workflow}-risk-register.md` 살아있는 문서. Phase 2에서 초안, 모든 Phase에서 발견된 위험·실패 모드 추가. **운영 단계에서 발견된 모든 실패는 `/diagnose`의 Phase 6(post-mortem)을 거쳐 결과 가설을 risk-register에 1행으로 기록**. **'no-seam findings'는 별도 태그로 분류해 §7 결정 #8 정기 회수의 우선 검토 입력으로 사용**. Phase 5a 회귀 테스트 입력으로 사용. **risk-register 등재 항목은 `/triage` 5-state 머신을 통해 라우팅 의무** [§-1 Skill Toolkit verbatim "*/triage \| 이슈를 5-state 머신으로 운영 \| §4 Step 5, Phase 6, **횡단 D***" 호출 위치 정합] — `needs-triage` 등록 → `needs-info` / `ready-for-agent` / `ready-for-human` / `wontfix` 분기로 처리. /grill-with-docs로 ADR 3-조건 충족 시 ADR 등재 (횡단 A 정합). |
| **E** | Observability Layer | 에이전트 사고 trace + 도구 사용 로그 + LLM 분산 추적 + HITL 결정 분포. Phase 4e에서 인프라 구축, Phase 5·6에서 활성 운영. **관측 데이터에서 추출되는 도메인 사건 명칭은 반드시 `CONTEXT.md` 어휘로 정규화**(예: "lesson materialization cascade"). **임계 초과 사건은 Phase 6의 `/zoom-out` 자동 트리거 파이프라인의 입력**이 된다. |

---

## §3. Phase 적용 규칙 — 필수 / 조건부 / 선택적

워크플로우 성격에 따라 일부 Phase는 조건부로 적용된다. **생략 시 반드시 ADR 등록**.

| Phase | 적용 분류 | 조건 |
|---|---|---|
| **(전제) Skill Setup** | **필수 (1회)** | 신규 레포에서는 `/setup-matt-pocock-skills`를 1회 실행해 이슈 트래커·triage 라벨·도메인 문서 레이아웃을 등록한 뒤 Phase 0 진입. 이 셋업 없이는 `/to-prd` · `/to-issues` · `/triage` · `/diagnose` · `/tdd` · `/improve-codebase-architecture` · `/zoom-out`이 컨텍스트 부족 상태로 동작한다. |
| 0 Intent Alignment | **필수** | 모든 워크플로우 |
| 1 Interface | **필수** | 다운스트림 소비자가 있는 워크플로우 (대부분). 단일 종결형이면 출력 형식 규약만 정의 |
| 1.5 Contract Stress | **조건부** | Phase 1 산출물이 있는 경우 필수. Phase 1 생략 시 자동 생략 |
| 2-PRD | **필수** | 모든 워크플로우 |
| 2-Spec | **필수** | 모든 워크플로우 |
| 2-Test | **필수** | 모든 워크플로우 |
| 2-Eval | **조건부** | LLM 에이전트 또는 확률론적 출력이 있는 경우 필수. 순수 결정론 워크플로우는 생략 가능 |
| 2.5 Asset Curation | **조건부** | 빌드 타임 정적 자산(lookup table · controlled vocab · 도메인 reference docs 등)이 있는 경우 필수 |
| 3 workflow.md | **필수** | 모든 워크플로우 |
| 3.5 Dry-Run | **필수** | 모든 워크플로우 |
| 3.7 Prompt Engineering | **조건부** | LLM 에이전트 사용 시 필수. 순수 결정론 워크플로우는 생략 가능 |
| 4 Implementation (4a~4f) | **필수** | 모든 워크플로우. 4d(LLM 통합)는 LLM 사용 시에만 |
| 5a Unit / Integration / Eval | **필수** | 모든 워크플로우 |
| 5b Acceptance | **필수** | 모든 워크플로우 |
| 6 Continuous Learning | **조건부** | 운영 단계에서 진화·드리프트가 발생할 수 있는 시스템(LLM 기반 · 외부 데이터 의존 · 사용자 분포 변화 가능)에 필수. 일회성 도구는 선택 |

**조건부 Phase 생략 결정 절차**:

1. ADR 등록 (왜 적용 안 되는지 명시 — `/grill-with-docs` 3-조건 충족 시).
2. 해당 Phase를 인스턴스 파이프라인 문서에서 "N/A — ADR-XXX" 표기.
3. 횡단 활동(특히 D Risk Register)에 생략으로 인한 잠재 위험 등록.

---

## §4. 인스턴스화 절차 — 새 워크플로우에 이 프로토콜 적용하기

새 워크플로우 `{name}`을 만들 때 다음 단계를 수행한다.

### Step 0. Skill Setup 확인

`/setup-matt-pocock-skills` 실행 결과(`docs/agents/issue-tracker.md`, `docs/agents/triage-labels.md`, `docs/agents/domain.md`)가 존재하는지 확인. 없으면 먼저 실행. 본 프로토콜은 이 셋업이 끝났음을 전제로 한다.

### Step 1. 인스턴스 파이프라인 문서 생성

`docs/{domain}/{name}-implementation-pipeline.md` 또는 `workflows/{name}/implementation-pipeline.md`에 인스턴스 문서를 만든다. 본 프로토콜의 §1 표를 복사하되 다음을 인스턴스화:

- `{workflow}` 플레이스홀더를 워크플로우 이름으로 치환.
- 산출물 경로를 워크플로우 도메인에 맞게 구체화.
- 도메인 정적 자산이 있으면 §1 Phase 2.5 행에 구체 자산 목록 명시.
- §3 Phase 적용 규칙에 따라 생략할 Phase 결정.
- 머리말에 "본 인스턴스는 `CONTEXT.md`(또는 멀티 컨텍스트의 경우 해당 컨텍스트의 `CONTEXT.md`)와 `docs/adr/`를 SOT로 사용한다"를 박아둘 것.

### Step 2. ADR 등록

`DECISION-LOG.md`에 다음 형식으로 ADR 추가:
ADR-NNN: {workflow} Implementation Pipeline — Instance of Universal Protocol

Date: YYYY-MM-DD
Status: Accepted
Context: {워크플로우 도메인·목적}
Decision: 본 프로토콜(docs/protocols/implementation-pipeline.md, v1.0)을 따름. 인스턴스 문서: {인스턴스 경로}. 생략 Phase: {목록 + ADR 참조}
Rationale: {워크플로우별 도메인 근거}
Related files: 인스턴스 파이프라인 문서, 본 프로토콜, docs/agents/*.md (Skill Setup 산출물)

### Step 3. 횡단 활동 활성화

- A (Decision Log): ADR 등록 시작 — 단, **3-조건** 충족 여부를 매번 확인.
- B (Context Preservation): 자동 작동 (Hook 시스템). `CONTEXT.md` 해시 · 최신 ADR 번호 동기화 활성.
- C (Adversarial Review): 각 Phase 게이트 활성화. Phase 4f 직후 `/improve-codebase-architecture` 1-pass 자동 트리거 등록 + Phase 5a 'no-seam findings' 환류 채널 등록.
- D (Risk Register): `{name}-risk-register.md` 초안 + 'no-seam findings' 분류 태그 준비.
- E (Observability): Phase 4e 시점에 활성. 사건 명칭은 `CONTEXT.md` 어휘로 정규화. Phase 6의 `/zoom-out` 자동 트리거 파이프라인 입력 채널 등록.

### Step 4. Phase 0 진입

사용자와 의도 정렬 대화 시작. **비코드 의도 정렬은 `/grill-me`, 도메인 위 작업이면 처음부터 `/grill-with-docs`**로 시작. 한 번에 한 질문 원칙을 지키고, 코드베이스 탐색으로 답할 수 있는 질문은 사용자에게 묻지않고 직접 탐색한다. 합의가 응결되면 `CONTEXT.md` · ADR이 그 회차 내에서 동시에 갱신되어야 함. Phase 0 합의가 메모리·ADR로 응결되면 Phase 1로 진행.

### Step 5. 진행 추적

인스턴스 파이프라인 문서의 §6 Status 표를 Phase 완료 시마다 갱신. 각 Phase 완료 시 ADR 등록(3-조건 충족 시)에 더해, **이슈 트래커의 해당 PRD / 슬라이스 상태를 `/triage`로 다음 단계 라벨로 이동**(예: `needs-triage` → `ready-for-agent` → 구현 후 close)할 것을 의무화. **Phase 5a에서 발견된 'no-seam findings'는 risk-register 등재와 동시에, 다음 Phase 4f 회차의 `/improve-codebase-architecture` 1-pass 입력 대기열에 자동 등록**한다.

---

## §5. 절대 기준 매핑

| 절대 기준 | 어느 Phase에서 보장되는가 |
|---|---|
| **1 — 품질 최우선** | 전체. 특히 1.5 (stress) · 2-Eval · 3.5 (dry-run) · 5a (failure mode) · 5b (acceptance) · 6 (continuous learning)이 품질 검증의 다층 안전망. **추가**: 4f 직후 `/improve-codebase-architecture` 1-pass 의무화, 5a 모든 버그는 `/diagnose` 6-Phase 강제, **5a → 4f 폐쇄 학습 루프('no-seam findings' 환류)**, **§7 결정 #8 정기 아키텍처 회수**. |
| **2 — 단일 파일 SOT** | Phase 1 (인터페이스 SOT) + Phase 4e (`state.yaml` 런타임 SOT). **추가**: 도메인 어휘 SOT = `CONTEXT.md` (`/grill-with-docs`로만 갱신), 트리아지 라벨 SOT = `docs/agents/triage-labels.md`, 이슈 트래커 워크플로우 SOT = `docs/agents/issue-tracker.md`. |
| **3 — CCP** | Phase 4 전 sub-phase + Phase 6의 Asset Updater (운영 단계 변경에도 CCP 적용). **추가**: 운영 자산 변경은 `/triage`의 `ready-for-agent` / `ready-for-human` 분기를 통과한 이슈를 통해서만 발생. **§7 결정 #8 정기 회수의 산출물(아키텍처 변경 권고)도 동일한 분기를 통해서만 적용**. |

---

## §6. DNA 유전 (Parent Genome Inheritance)

본 프로토콜에 따라 만들어진 모든 워크플로우는 부모(AgenticWorkflow)의 게놈을 구조적으로 내장한다 (`soul.md` §0).

| Parent Genome | 본 프로토콜에서 발현되는 위치 |
|---|---|
| 3 Absolute Criteria | §0, §5 |
| Single-File SOT | Phase 1 (인터페이스 SOT) + Phase 4e (런타임 SOT) |
| 3-Phase Structure | Phase 3 (`workflow.md`)에서 Research → Planning → Implementation으로 발현 |
| 4-Layer QA (L0~L2) | Phase 4f, 5a, 횡단 C |
| P1 Hallucination Prevention | Phase 4c (결정론 모듈), Phase 2.5 (정적 자산) |
| P2 Expert Delegation | Phase 4e (Sub-agent 통합) |
| Safety Hooks | Phase 4e (Safety Layer) |
| Adversarial Review | 횡단 활동 C |
| Decision Log | 횡단 활동 A |
| Context Preservation | 횡단 활동 B |
| Failure Mode Library | 횡단 활동 D |
| Observability | 횡단 활동 E |
| **Domain Glossary (`CONTEXT.md`)** | **Phase 0 / 2-PRD / 3 / 3.7 / 4f / 5b 전반, 횡단 A · E** |
| **ADR 3-조건 (Hard to reverse · Surprising · Real trade-off)** | **횡단 A, Phase 1 게이트(인터페이스 contract 자동 충족)** |
| **Tracer-bullet vertical slices** | **Phase 4 (전체), Phase 6 (자동 PR 생성 정책)** |
| **Triage state machine (5-role)** | **Phase 6, 횡단 D, §4 Step 5** |
| **Module / Interface / Depth / Seam 어휘** | **Phase 1, Phase 4f, 횡단 C** |
| **Deletion test (살아남음 / 흩어짐)** | **Phase 4f 종료 게이트** |
| **`/diagnose` post-mortem 3종 세트(맞은 가설·hand-off·아키텍처 트리거)** | **Phase 5a 종료 게이트, 횡단 D** |
| **No-seam findings 폐쇄 학습 루프 (5a → 4f)** | **Phase 5a → Phase 4f, 횡단 C·D, §4 Step 5** |
| **`/zoom-out` 운영 단계 자동 트리거** | **Phase 6 산출물, 횡단 E** |
| **정기 아키텍처 회수 (`/improve-codebase-architecture` 주기 운영)** | **§7 결정 #8, Phase 6 산출물** |

---

## §7. Phase 6 (Continuous Learning) 6+1+1대 결정 항목

운영 단계 진입 전 사용자가 결정해야 할 정책 (Phase 6 진입 시점). 이 결정들은 Phase 6 시작 시점에 ADR로 일괄 등록한다.

**각 결정 항목 진행 시 `/grill-me` 인터뷰 의무** [§-1 Skill Toolkit verbatim "*/grill-me \| 비코드(의도 정렬·정책 결정) 인터뷰 \| Phase 0 (도메인 컨텍스트가 없을 때), **§7 6+1+1대 결정***" 호출 위치 정합] — 본 §7의 결정 항목은 모두 비코드 정책 결정이므로 `/grill-me` (한 번에 한 질문 원칙) 또는 도메인 위 작업이면 `/grill-with-docs` (옵션 A·C 명시) 로 사용자 의도 정렬 인터뷰를 거쳐야 한다.

1. **데이터 수집 범위 (Privacy boundary)** — 수집할 것 / 익명화할 것 / 절대 수집 안 할 것.
2. **트리거 임계값 (Drift threshold)** — KPI 이탈·"부분수정" 빈도 등의 알림 기준 정량 정의.
3. **자동화 vs 수동 검수 경계** — 옵션 A(보수: 신호만) / B(중간: PR 자동생성·수동승인 — 자동 PR 생성 시 `/to-issues`의 vertical-slice 규칙을 따른다) / C(진취: 회귀 통과 시 자동적용).
4. **변경 가능 자산의 화이트리스트** — 변경 가능 vs 변경 불가(인터페이스·도메인 핵심 규약·절대 기준).
5. **모델 업그레이드 정책** — 자동채택+자동재교정 / 수동채택+자동재교정 / 수동채택+사용자 수용테스트. 정책 결과에 따라 운영 단계 신호는 `/triage`의 `ready-for-agent` 또는 `ready-for-human` 분기로 자동 라우팅.
6. **롤백 정책** — 자동 롤백 임계 시간 + 롤백 권한자. 롤백 트리거 발생 시 `/triage`로 즉시 `needs-triage` 등록 + 사후 `/diagnose` 6-Phase 강제.
7. **운영 도메인 어휘 진화 정책** — 신규 사용자/사건이 만들어내는 새 용어를 `CONTEXT.md`에 추가할 권한·주기·승인 절차.
   - 옵션 A (보수): 분기별 큐레이션 — 운영 로그를 모아 `/grill-with-docs` 세션 1회로 일괄 반영.
   - 옵션 B (중간): 신호 임계 초과 시 PR 자동생성 → 사람이 승인 → `CONTEXT.md` 갱신 + (필요 시) ADR 등록.
   - 옵션 C (진취): `/grill-with-docs` 세션을 트리거해 즉시 반영, 회귀 테스트 통과 후 자동 머지.
8. **정기 아키텍처 회수 주기 (NEW)** — `/improve-codebase-architecture`를 운영 단계에서 정기적으로 돌리는 주기와 책임자.
   - 옵션 A (보수): **분기 1회** — 분기 마감 직후 1-pass 실행, 결과를 ADR화하여 다음 분기 백로그로 편입.
   - 옵션 B (중간): **6주 1회** — 격주 스프린트 3회마다 1-pass 실행, "흩어짐" 판정 모듈 + 누적 'no-seam findings'를 우선 검토.
   - 옵션 C (진취): **4주 1회** — 매월 1-pass 실행 + 회귀 테스트 통과 시 deepening 후보를 자동으로 `/to-issues`로 분해.
   - 회수 결과의 모든 아키텍처 변경 권고는 §5 절대 기준 3(CCP)에 따라 `/triage`의 `ready-for-agent` / `ready-for-human` 분기를 통과한 이슈를 통해서만 적용된다.

운영 단계의 모든 자동 회수 신호(Feedback Logger·Drift Detector)는 자동으로 이슈 트래커에 `needs-triage` 라벨로 등록되고, 그 이후의 진행은 `/triage` 5-state 머신을 통해서만 이뤄진다. **신규 메트릭/사건이 결정 #2의 임계값을 초과하면 `/zoom-out`이 자동 트리거되어 모듈 지도 1매를 생성하고 인스턴스 파이프라인 문서에 첨부**한다.

---

## §8. 참조 인스턴스

| 워크플로우 | 인스턴스 파이프라인 문서 | ADR | 사용 스킬 호출 흔적 | 비고 |
|---|---|---|---|---|
| _현재 활성 인스턴스 없음_ | — | — | — | 첫 인스턴스화 시 §4 Step 5에 따라 1행 추가. 과거 인스턴스 W1(FVC-Profiler)은 deprecation 처리됨 (ADR-052·053 W1 historical reference). |

새 인스턴스가 추가될 때마다 이 표에 1행 추가한다. **"사용 스킬 호출 흔적" 컬럼은 인스턴스가 누적될수록 어느 Phase가 실제로 비싸게 먹히는지를 보여주는 메타 데이터가 되며, 이후 본 프로토콜 자체에 대한 `/improve-codebase-architecture` 회수의 입력으로 쓰인다.**

---

## §9. 변경 이력

본 파일은 **v1.0 최초 버전**이다. 미래 변경 시점부터 본 표에 entry 추가.

| 일자 | 버전 | 변경 | 근거 ADR |
|---|---|---|---|
| 2026-05-12 | v1.0 | 최초 버전 신규 생성 — 워크플로우 구현 표준 프로세스 (3축: 전통 SW 엔지니어링 + 하네스 엔지니어링 + Skill-driven SOT). mattpocock-skills 9종 + Phase 0~6 + 횡단 활동 A~E + DNA 유전. 본 파일 결정 detail SOT = ADR-059. | ADR-059 |