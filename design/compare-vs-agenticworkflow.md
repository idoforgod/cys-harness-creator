All claims verified on disk:
- Engine compiles cleanly (all 9 py files).
- `genome_file_count: 228` confirmed in GENOME.json provenance stamp; vendored genome dir has 230 (228 + 2 incidental).
- Child carries `.harness/` with graph.json, workflow.js (11.5KB emitted), harness.lock, MANIFEST.json, GENOME.json — CYS engine artifacts — PLUS the full AWF genome (289 total files, 118 .claude hooks, prompt-runner present).
- 3 topologies (pipeline/dispatch/producer-reviewer) and 4 decision mechanisms (single/majority-vote/debate/reflect) confirmed in emit_workflow.py.

The critical honesty point holds: `lift-gate-fixture.json` self-labels as an M1 *sample* fixture (`"_note": "M1 lift-gate sample fixture..."`), confirming performance evidence is hand-authored/session-measured, not repo-reproducible runs.

I have enough grounded verification. Producing the comparison.

---

# 2차 종합 비교 — cys-harness-creator vs AgenticWorkflow (ORIGINAL)

> **본질적 프레임: 슈퍼셋 관계 (경쟁 아님)**
> 이번 비교는 1차 라이벌 비교와 *근본적으로 다르다*. CYS는 이제 AWF의 전체 게놈(228파일)을 **상속**한다.
> 정직한 등식: **CYS child = (AWF 전체 게놈, 상속) + (CYS 엔진, 원본)**
> 디스크 검증 완료 — deep-research child = 289파일(.claude 훅 118 + prompt-runner + soul/AGENTS/DECISION-LOG) **AND** `.harness/`(graph.json·workflow.js 11.5KB·harness.lock·MANIFEST·GENOME provenance stamp `genome_file_count:228`). 두 런타임이 한 하네스에 공존함을 실측.

---

## 1. 관계 본질 — 슈퍼셋, 경쟁 아님

| | AWF (ORIGINAL) | CYS (harness-creator) |
|---|---|---|
| **정체** | Pluripotent **마스터 워크플로우** — 하나의 살아있는 유기체. 30+ 프로젝트에서 검증된 machinery. | Deterministic **FACTORY** — AWF 게놈을 통째로 상속해 *자식 시스템을 찍어내는* 공장. |
| **자식 생성** | `workflow-generator` 스킬 → `workflow.md` (대화형, 설계 청사진). | `emit_workflow.py` graph.json → `workflow.js` (결정론적 실행 코드). |
| **유전 메커니즘** | soul.md §0 줄기세포 철학을 **문서 규율**로 상속 보장. | `inherit_genome.py`가 228파일을 **기계적 transplant** + py_compile/import 검증. |
| **자식 = ?** | AWF DNA를 가진 분화 세포. | **AWF DNA 전체 + CYS 엔진 오버레이** = 기능적 **슈퍼셋**. |

**핵심 명제**: CYS는 AWF를 *대체*하거나 *경쟁*하지 않는다. CYS child는 AWF가 가진 모든 것을 가지고(verbatim 상속), 그 위에 실행 엔진·기계검증·비용거버넌스를 *추가로* 얹는다. 따라서 capability 집합에서 **CYS child ⊇ AWF**.
단, "슈퍼셋"은 *capability 집합* 차원의 주장이지 *성숙도·신뢰도* 주장이 아니다 (6장 참조).

---

## 2. CYS가 AWF 위에 추가하는 것 (CYS-ORIGINAL only)

> 원칙: **AWF가 산문·방법론으로만 가진 것을, CYS가 실행 가능/강제 가능하게 만든 것**만 여기 기재. AWF에서 상속받은 것은 CYS 공로 아님.

| CYS-원본 추가 | AWF는 무엇을 가졌나 | CYS가 무엇으로 바꿨나 | 디스크 상태 |
|---|---|---|---|
| **결정론적 Mode-A 런타임** (`emit_workflow.py`→`workflow.js`) | `workflow.md` = 사람이 읽는 설계 청사진 (대화형, 휘발성) | 순수함수 컴파일러: RNG·wall-clock 없음, resume-safe, replay 가능한 JS 코드 | ✅ 재실행 가능. 3 topology(pipeline/dispatch/producer-reviewer) × 4 mechanism(single/majority-vote/debate/reflect) 실측 |
| **graph.json 불변 계약** | state.yaml 단일 SOT (가변, 사람이 편집) | 스키마검증·해시핀 불변 계약 + MANIFEST append-only 진화 로그 | ✅ graph.schema.json (4.4KB) on-disk |
| **17-check 기계 빌드 게이트** (`validate_harness.py`) | 3대 절대기준 + P1 = **산문/문서 규율** (사람이 지킴) | exit 0/1/2 정적 검사 17개 (고유 ID·DAG 사이클·스키마·edge·model-tier) | ✅ 12.7KB, 컴파일 OK |
| **role→tier 비용 거버넌스** (`model-tier-policy.js`+`warrant.py`) | "역할별 최선 모델 선택" = **암묵적 판단** | 결정론적 매핑(researcher→opus, fetcher→haiku) + 토큰 cost-band 사전승인 | ✅ on-disk. AWF엔 비용 게이팅 자체가 없음 |
| **4종 decision-mechanism 코드 생성기** | adversarial review = 산문 패턴 | single/majority-vote/debate-with-judge/reflect-then-revise를 *실행 코드로* emit | ✅ emit_workflow.py에서 grep 확인 |
| **lift/head-to-head 측정** (`lift_gate.py`+`h2h_aggregate.py`) | ADR-051 "품질 입증된 것만 채택" = **철학** | +5pp lift 미달 스킬은 graduation 차단하는 *실행 게이트* | ⚠️ 코드는 on-disk·실행가능. **데이터는 hand-authored 샘플** (아래 honesty) |
| **공장/분화 모델** (`inherit_genome.py`+skills/harness-creator) | 줄기세포 철학 = soul.md §0 산문 | 228파일 자동 transplant + 기능검증 + grandchild 재귀 가능 | ✅ 자식이 실제로 게놈+엔진 동시 보유 실측 |

**요약**: CYS의 본질적 기여는 **"AWF의 규범(prose rules)을 기계 단언(machine assertions)으로 컴파일"** 하는 것 — 즉 CYS는 AWF의 *컴파일러*다. 비용 거버넌스 한 축만 순수 신규(AWF에 부재), 나머지는 모두 *AWF가 이미 가진 원리를 강제 가능하게 만든* 것.

---

## 3. 중복·긴장 (정직) — 한 자식에 두 시스템이 공존할 때

> 실측: deep-research child에 **AWF prompt-runner**(prompt_extractor.py + prompts/ + manifest)와 **CYS workflow.js**(.harness/)가 *둘 다* 존재.

| 중복 축 | AWF 측 | CYS 측 | 보완 vs 중복? | 정규(canonical) 권고 |
|---|---|---|---|---|
| **(a) 런타임** | prompt-runner: 110-step `claude -p --resume`, **사람 주도**, stateful, 35 /clear breakpoint, rate-limit 60×5min, battle-tested 30 프로젝트 | workflow.js: **도구 주도**(agent() 호출), immutable, stateless, budget-gated | **운영 중복**(자식이 둘 다 보유) but 아키텍처적 보완 | **장기·사람참여·rate-limit 노출 작업 → AWF prompt-runner. 결정론적·resume-safe·예산통제 작업 → CYS workflow.js.** 둘 다 남기되 *작업 성격으로 라우팅*. 병합 금지(서로 다른 실행 모델) |
| **(b) 생성 패러다임** | `workflow-generator` 스킬 → workflow.md (대화형 설계, distill 인터뷰) | `emit_workflow.py` → workflow.js (graph.json 결정론적 컴파일) | **보완** (설계時 vs 실행時) | **합성(compose) 권고: user → workflow-generator → workflow.md → graph.json → emit → workflow.js.** AWF가 *무엇을*(설계), CYS가 *어떻게 실행*(런타임). 충돌 아님 |
| **(c) 상태/메모리** | context-preservation 훅 (SessionStart/Stop/PreCompact, latest.md snapshot, knowledge-index.jsonl, RLM restore) — battle-tested | MANIFEST.json (provenance/진화 로그) + harness.lock + atomic_write | **부분 중복 가능** (둘 다 "상태 추적") but 다른 층위 | **세션間 컨텍스트·지식누적 → AWF 훅 (정규). 그래프 진화·빌드 provenance → CYS MANIFEST.** CYS workflow.js는 설계상 stateless·resume-safe라 AWF 훅에 무임승차하면 됨. CYS resume(runId)는 *aspirational* — 구현 전까지 AWF 복원이 정규 |

**정직한 평가**: (a)는 *진짜 운영 중복*이다 — 한 자식이 두 실행기를 들고 다닌다. 아키텍처적으로는 비충돌(서로 호출 안 함)이지만, 사용자 입장에서 "어느 것으로 돌리나" 혼란 가능. (b)(c)는 보완적이며 합성하면 오히려 강해진다.

---

## 4. AWF가 여전히 명백히 앞서는 축 (정직한 크레딧)

| 축 | AWF 우위 근거 |
|---|---|
| **성숙도** | **30+ 프로젝트 battle-tested** vs CYS = **M0 dogfood 프로토타입** (CI·테스트스위트 없음, 1,691 LOC). 격차가 가장 큰 축. |
| **prompt 라이브러리 깊이** | PRD Teammate Executable Library **5,307줄** (core 1,517 + 도메인 deepdive 3종). CYS엔 등가물 전무. |
| **context-preservation/quality machinery** | 39 훅 스크립트·112+ 함수·4-layer QA(L0–L2+pACS)·14 P1 validator·12-pattern Error Taxonomy·Abductive Diagnosis·131 안전테스트 — 전부 battle-tested. CYS는 이걸 *상속만* 함(공로 아님). |
| **workflow.md 3-stage 방법론** | Research→Planning→Implementation 구조적 제약(ADR-004), distill 인터뷰 검증. CYS emit은 더 narrow(graph→JS). |
| **스킬 폭** | `doctoral-writing`(논문급 학술), `workflow-generator`, `spec-grounded-workflow` — CYS는 workflow/automation 도메인 외엔 미관여. doctoral-writing은 CYS와 **직교**(상속도 확장도 아님). |
| **철학·거버넌스 깊이** | soul.md→AGENTS.md→CLAUDE.md→DECISION-LOG **55+ ADR** 포렌식 결정 추적, RLM 이론기반(MIT CSAIL), Hub-and-Spoke. CYS ADR은 *계획만* 있고 repo에 미기록(honesty note). |

**핵심**: CYS가 자식에게 주는 quality·context·philosophy machinery의 거의 전부는 **AWF가 만든 것을 CYS가 transplant한 것**이다. 그 machinery의 *발명 공로는 100% AWF*. CYS는 그것을 *기계적으로 보장*하는 층을 더했을 뿐.

---

## 5. 기능 + 성능 대조표

| 축 | AWF (ORIGINAL) | CYS (harness-creator) | 관계 | 근거 |
|---|---|---|---|---|
| **런타임** | prompt-runner (110-step, claude-p, 사람주도, rate-limit 복원) | workflow.js (Mode-A, 도구주도, immutable, resume-safe) | **CYS추가 + 운영중복** | 자식에 둘 다 실측(prompt-runner + .harness/workflow.js) |
| **생성** | workflow-generator → workflow.md (대화형) | emit_workflow.py → workflow.js (결정론) | **CYS추가 (보완)** | 3 topo × 4 mech grep 확인 |
| **상태/메모리** | context 훅 + knowledge-index.jsonl + RLM restore | graph.json(불변) + MANIFEST(진화) + harness.lock | **상속 + CYS추가(직교)** | 훅=상속, MANIFEST=원본 |
| **품질 게이트** | 4-layer QA, 14 P1 validator, pACS | (자식이 상속) + 17-check 빌드게이트 | **상속 + CYS추가(빌드前)** | validate_harness.py on-disk, 컴파일 OK |
| **비용** | **없음** | warrant.py token cost-band + model-tier | **CYS 순수신규** | AWF에 비용 개념 부재 |
| **보안** | block_destructive·secret-filter·file-guard (131테스트) | (자식이 상속, 추가 없음) | **상속 (CYS 공로 아님)** | 자식 .claude 훅 118파일 실측 |
| **에이전트/스킬** | @reviewer·@fact-checker·@translator·doctoral·spec-grounded | (전부 상속, 추가 없음) | **상속 (CYS 공로 아님)** | 자식에 verbatim 존재 |
| **prompt 라이브러리** | PRD Teammate 5,307줄 | 없음 (상속만) | **AWF 우세** | CYS 등가물 전무 |
| **철학/거버넌스** | soul.md + 55 ADR + RLM | CONSTITUTION.md (AC-1/2/3 기계검증) | **상속 + CYS추가(강제화)** | CONSTITUTION 2.7KB on-disk; CYS ADR 미기록 |
| **i18n** | glossary.yaml SOT + @translator | (상속, 추가 없음) | **상속 (CYS 공로 아님)** | translations/ 자식 보유 |
| **성숙도** | 30+ 프로젝트 battle-tested | M0 prototype (CI/test 無, 1,691 LOC) | **AWF 압도적 우세** | 디스크: 테스트스위트 부재 확인 |
| **결정론/강제** | 산문 절대기준 + P1 deterministic 검증 | 17-check 기계게이트 + 불변계약 + tier정책 | **CYS추가 (핵심 차별)** | CYS = AWF 규범의 *컴파일러* |
| **측정(perf)** | 없음 (정성 품질만) | lift_gate + h2h (코드 실행가능) | **CYS추가** | ⚠️ **데이터는 hand-authored 샘플** |

### 성능 증거 — 정직 경고 (CRITICAL HONESTY)
| 지표 | 출처 | repo 재현 가능? |
|---|---|---|
| **n=1 BASELINE-WINS −16.67pp** (C2=0.833 vs C3 무하네스 opus=1.0) | `evals/deep-research.verdict.json` (stamped) | ✅ **재현 가능** (`h2h_aggregate.py`) — 과거 이 줄의 "+38pp/lift 1.00"은 폐기된 가설 fixture였고 실측과 모순돼 거짓이었음 |
| runs.json / lift-gate-fixture.json | repo 상주 | ⚠️ **hand-authored 샘플/가설** (파일 자체가 `"_note":"M1 lift-gate sample fixture"`로 자기 라벨링 — 실측) |
| emit/validate/genome-transplant/security-hook capability | repo 상주 | ✅ **on-disk 재실행 가능** (9 py 전부 py_compile OK) |

**즉**: CYS의 **capability 주장은 검증됨**(코드가 돌아감). CYS의 **performance 숫자는 세션-측정이지 repo-재현 불가**. 이 둘을 혼동하면 안 됨.

---

## 6. 2차 종합 판정

**CYS는 AWF의 게놈 + 결정론적 강제·실행 층이다 (capability 슈퍼셋), 그러나 AWF 자체 machinery가 더 검증되었고 CYS 엔진은 M0/프로토타입이며 성능 증거는 세션-한정(비-repo-stamped)이다.**

세 층으로 정리하면:

1. **상속 층 (AWF 100% 공로)** — quality 4-layer, 14 P1, 안전훅 131테스트, context-preservation, @reviewer/@fact-checker/@translator, 스킬, glossary, 55 ADR 철학. CYS child가 이걸 다 갖지만 *발명은 AWF*. CYS는 transplant 메커니즘만 기여.

2. **강제 층 (CYS 원본)** — AWF가 *산문/방법*으로 가진 것을 *기계 단언*으로: 17-check 빌드게이트, graph.json 불변계약, model-tier 정책. **CYS = AWF의 컴파일러**. 이것이 가장 정직한 한 줄 요약.

3. **신규 층 (CYS 순수신규, AWF에 부재)** — 비용 거버넌스(warrant/tier), decision-mechanism 코드생성, lift/h2h 측정, 공장/분화 재귀. 단 측정 데이터는 아직 가설 fixture.

**Net 관계**:
- *Capability 집합*: CYS child ⊋ AWF (진부분집합 슈퍼셋) — 디스크로 확인(자식 = 게놈 289파일 + 엔진 .harness/).
- *성숙도·신뢰도*: AWF ≫ CYS (30 프로젝트 vs M0, repo-stamped perf 부재).
- *역할*: **경쟁자 아님 — AWF는 pluripotent 부모 유기체, CYS는 그 게놈을 통째로 물려받아 결정론적 실행+비용통제+측정을 더해 자식을 찍어내는 공장.**

**미해결 운영 긴장 (권고)**: 한 자식이 *두 런타임*(AWF prompt-runner + CYS workflow.js)을 들고 다니는 것은 진짜 중복이다. 정규화 권고 — 작업 성격으로 라우팅(장기·사람참여→AWF / 결정론·예산통제→CYS), 병합 금지. 그리고 CYS의 최우선 다음 과제는 **performance fixture를 hand-authored 샘플에서 repo-reproducible 실측 artifact로 승격**하는 것(현재 honesty의 핵심 구멍).

---
**검증 출처(디스크 실측)**: `/Users/cys/Desktop/CYSjavis/cys-harness-creator/` — engine 9파일 py_compile OK; `examples/deep-research/` = 289파일(.claude 훅 118 + prompt-runner + soul/AGENTS/DECISION-LOG) + `.harness/`(graph.json·workflow.js 11.5KB·harness.lock·MANIFEST·GENOME stamp `genome_file_count:228`); `examples/lift-gate-fixture.json` 자기라벨 "M1 sample fixture".