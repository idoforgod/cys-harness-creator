# Skillbased Implementation Pipeline Protocol — Long-Horizon Autonomous 워크플로우 구현 표준 프로세스

- Status: **v1.0 (최초 버전, 2026-05-12)**
- Scope: 본 프로토콜은 **장기간 자율 실행 시스템 (Long-Horizon Autonomous System)** 구축에 적용되는 범용 메타 빌드 프로세스다. 어떤 도메인 스킬 카탈로그를 사용하든 (예: foresight-* / vision-* / 사용자 정의 카탈로그 등), 스킬 자산을 조립해 4시간 이상 자율 주행하는 LLM 코어 시스템에 범용 적용한다. **Long-Horizon Autonomous Layer (4번째 축)** 가 핵심 구조다.
- 절대 기준 (사용자 ABSOLUTE ANCHOR 4원칙 + 본 프로토콜 절대 기준 3개):
  - **ABSOLUTE ANCHOR 1** — 최고의 품질 실현이 절대원칙. 속도·토큰 소모량 무시.
  - **ABSOLUTE ANCHOR 2** — 워크플로우 최종 결과물 수준과 품질에 가장 적합한 것 선택.
  - **ABSOLUTE ANCHOR 3** — 로컬 실행 불변. 로컬 실행 전제를 흔드는 결함은 최우선 배제.
  - **ABSOLUTE ANCHOR 4** — LLM 사용 시 Claude Max 구독모델 사용 절대 규칙. API·SDK 방식 절대 사용 금지.
  - **본 프로토콜 절대 기준**: 1(품질 최우선) → 2(SOT) → 3(CCP)
- **본 파일 ADR**: **ADR-058 (최초 버전 — Long-Horizon Autonomous Layer + Pipeline × Long-Horizon Autonomous Integration Protocol 6항)**
- **Base reference**: `implementation-pipeline.md` v1.0 fork — **ADR-059 (Base v1.0 — 워크플로우 구현 표준 프로세스 + Skill-driven SOT + 3축 통합)**. 본 파일은 base를 fork하여 Long-Horizon Autonomous Layer (4번째 축) 를 추가한 별도 SOT.
- 상세 메커니즘 SOT (인스턴스별 명시): 각 Long-Horizon Autonomous 시스템 인스턴스는 자체 design SOT 문서를 가진다 (7대 설계 원칙·D1~D8·Run Manifest 정밀 구조·3-tier verification·Wall-Clock 적응 cache 전략). **인스턴스 예시 (Long Harness Autonomous Agent System)**: `cys-claude-foresight-skills/docs/long-harness-system-design.md`. 새 인스턴스 빌드 시 §4 Step 1에 따라 자체 design SOT 작성.

> 이 문서는 long-horizon autonomous 워크플로우 제작의 절차적 SOT다. 어떤 도메인 인스턴스(foresight·vision·미래비전코칭·설교 준비·금융투자·경영 컨설팅·고객 응대 자율 에이전트 등)든 본 프로세스를 따른다. Phase 단축·생략은 ADR 등록을 통해서만 가능하다.

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

**자율 실행 단계 (Long-Horizon Autonomous 런타임) 적용 제약** [v1.0 최초 버전]: 본 §-1 표의 9 mattpocock-skills는 **빌드 단계 전용**이다. 자율 실행 중 자동 호출은 금지된다. 자율 실행의 LLM 호출 대상은 **각 인스턴스의 도메인 스킬 카탈로그**로 한정된다 (인스턴스 예시: Long Harness Autonomous Agent System은 `foresight-* / vision-*` 카탈로그 사용. SOT = 인스턴스 design 문서의 "객체 차이" 표 LLM 사용 컬럼). **코드 차원 차단** — §0 (d) "*스킬 자산 leverage — 빌드 시 `skills_snapshot` freeze, Task 시작 시 immutable inject, 도중 스킬 업그레이드 무시(재현성 보장)*" verbatim 메커니즘에 의해, `skills_snapshot` 에 빌드 도구 미포함 → §0 (d) "*python 결정론 stateless dispatch loop*" 의 호출 대상에서 자연 배제된다. dispatch 결정은 `decisions.log` D7 5 필드 (timestamp · skill_id · T1_result · plan_ref · cost — `docs/long-harness-system-design.md §5 D7` verbatim) 에 기록된다 (RLM Variable Persistence 활용). `/diagnose` 6-Phase 의 자율 자동 처리(Phase 1~4) ↔ T1/T2/T3 매핑은 `docs/long-harness-system-design.md §8` "`/diagnose` 6-Phase ↔ T1/T2/T3 매핑" 표 verbatim 으로 도구 자체 호출과는 분리된다. **자율 실행 시 추가 차단 layer (sub-agent context inject 자산 · Phase 3.7 build-time system prompt 4 항목 메타데이터 포함 여부 · §2 횡단 B `knowledge-index.jsonl` 빌드 도구 카탈로그 등재 여부) 의 본 프로토콜 내 정책 명시 위치는 §10 후속 신규 분리 (B1.5)**.

**Long-Horizon Autonomous 시스템 빌드 시 도구 카탈로그 정합** [v1.0 최초 버전]: 본 §-1 표 9 mattpocock-skills 는 Long-Horizon Autonomous 시스템 자체를 빌드하는 단계에서 master claude agent 가 호출하는 도구 카탈로그다 (LLM-assisted human process로 빌드, 시스템 자체는 자율 런타임). 각 인스턴스 빌드 단계의 **산출물** 4종 — (a) **python orchestrator** (Python Script Orchestrator / Stateless Dispatch Loop 양식) (b) **verifier 코드 자산** (T1 Hard Gate 코드 차원 강제 — LLM 외부 코드로 실행) (c) **cache 영역 prompt 구성** (Cache 전략 5-15KB system prompt 4항목) (d) **dry-run simulator** (가짜 mission-spec 2~3개로 종이 위 시뮬레이션 + 1h prototype + wall-clock full run prototype). 산출물 정의는 **본 §-1 표가 아닌 인스턴스별 design SOT + 본 프로토콜 §1 Phase 2.5·3.5·3.7·4 산출물 자산**에 있다. **§-1 표 = 도구 카탈로그 SOT / 인스턴스 design 자산 = 빌드 산출물 SOT** 분리 (SOT 단일·응집도 보호). **인스턴스 예시 (Long Harness Autonomous Agent System)**: 산출물 4종 detail SOT = `cys-claude-foresight-skills/docs/long-harness-system-design.md` §2·§5 D1·§7·§10.

---

## §0. 설계 원칙

본 프로토콜은 **네 축(Layer)의 결합**이다.

1. **전통 SW 엔지니어링 축**: 의도 → 인터페이스 → 명세 → 절차 → 구현 → 검증 (Phase 0~5).
2. **하네스 엔지니어링 축**: LLM 코어 시스템 고유의 활동 통합 — Eval Suite, Prompt Engineering, Observability, Failure Mode, Cost-Latency, Safety, Continuous Learning.
3. **하네스 운용 축 (Skill-driven SOT)**: 모든 Phase의 도메인 어휘는 `CONTEXT.md`에 응결되고, 가역하기 어려운 결정은 `docs/adr/`에 기록되며, 작업 단위는 이슈 트래커의 `needs-triage` → `ready-for-agent` 상태 머신을 따른다. ADR 등록은 `/grill-with-docs`의 **3-조건**(Hard to reverse · Surprising without context · Real trade-off)을 모두 충족할 때만 한다. 그 외의 도메인 어휘 변동은 ADR이 아니라 `CONTEXT.md` 인라인 갱신으로 처리한다.
4. **Long-Horizon Autonomous 축 (Time-Cumulative Operation Layer)** [v1.0 최초 버전]: 장기간 자율 실행 시스템 고유의 활동 통합. **본 축은 §3에 명시된 적용 조건에 한해 필수**이며, 그 외 시스템에서는 N/A 처리하되 ADR로 N/A 사유 등재. **적용 조건 detail (3 조건 · N/A 시스템 예시 · N/A 절차) 은 §3 "4번째 축 적용 조건" sub-section 참조** (SOT 단일). 본 축은 다음 4 sub-element로 구성된다.

   **(a) Time Budget Management** — `mission-spec.md` 7번째 항목 **Wall-Clock Budget** 을 task별 immutable로 정의·강제. **Cost ceiling 공식·1h prototype 측정은 Phase 3.5 Dry-Run 참조** (SOT 단일). Hard ceiling = target × 1.5 초과 시 자동 pause + 사용자 alert.

   **(b) Drift Containment** — 시간 누적 위험 3종(Compaction Destruction · Sub-agent Isolation · Reward Hacking)을 다음 메커니즘으로 구조적 차단.
   - *Mission Spec Immutability* — 매 step 시작 시 verbatim 재주입, compaction 대상 제외, SHA256 hash check
   - *Spec-vs-Output Diff @ every N step* — Verifier가 항목별 충족 체크, 미충족 chain K개 누적 시 자동 stop + alert
   - *Cost/Time Budget Gate* — phase별 ceiling 초과 시 자동 pause
   - *3-tier verification* — T1 (외부 python deterministic hard gate, LLM 우회 불가) · T2 (LLM verifier, 사용자 영역 전문 기준, *예측의 진실성은 검증 불가* 명시. **@reviewer + @fact-checker 페르소나 통합은 A9에서 결정**) · T3 (사용자 사후 spot-check, 자율의 사후 안전망. **빈도·시간 protocol은 위험 3 결정에 위임**). 상세는 Phase 2-Eval (3-tier 정형 명문화) + `docs/long-harness-system-design.md §4` 참조
   - *Sub-agent inject 강제* — mission-spec verbatim + `plan.md`의 declarative dependency graph 명세대로 prior artifacts + 산출 schema (blanket "직전 step output" 금지)
   - *결정·추론 분리* — `decisions.log`(python 결정론: timestamp · skill_id · T1_result · plan_ref · cost) vs `reasoning_trace.log`(LLM narrative: "왜 그 결정을 했나"). T3 spot-check는 두 파일 cross-reference로 reward hacking(자기 결정 사후 미화) 차단

   **(c) Pause/Resume Protocol** — 매 phase 종료 시 `_handoff_latest.md` 기록. Resume 시 직전 phase의 `verifier-reports/<phase>.json`을 **반드시 먼저** 읽고 pass 상태 확인 후에만 다음 phase 진입. Wall-clock 적응 cache 전략으로 비용 효율 유지 (**System prompt 5~15KB 4항목 build-time 구성은 Phase 3.7 Prompt Engineering 참조** — SOT 단일).
   - ≤6h: TTL 5분 ephemeral cache
   - 6~24h: TTL 5분 + Anthropic 1시간 persistent cache 옵션 병행 검토
   - >24h: cache 영역 축소 (build-time 자산 외부화)
   - >7d: cache 비의존 (매 phase 시작 시 cache 재구성 비용 감수)

   Run Manifest(`_runs/<task-id>/`)와 부모 SOT는 공간 분리 — task 산출은 `_runs/`에만, 부모 `CONTEXT.md`·`MEMORY.md` 변경은 task 종료 후 사용자 명시 지시 시에만. Task 실행은 별도 작업 루트(`_runs/<task-id>/workdir/`)의 minimal CLAUDE.md에서 진행해 master CLAUDE.md 자동 inject 차단.

   **(d) Skill Orchestration & Verification** — 본 시스템은 일반 LLM agent와 달리 spec 정의부터 시작하지 않고 **스킬 자산을 조립**한다(*skillbased*). 다음 4 게이트로 안전성 확보.
   - *3-Layer 수정 진단 protocol* — 성능 업그레이드·결과물 미흡 시 수정 진입점은 단 3개로 한정: ① 스킬(능력 담당) ② Orchestrator routing(어떤 skill을 언제 어떤 순서로 — *python 결정론 stateless dispatch loop*) ③ Verifier criteria(무엇이 통과인가). 그 외 영역 수정 금지
   - *스킬 자산 leverage* — 빌드 시 `skills_snapshot` freeze. Task 시작 시 immutable inject. 도중 스킬 업그레이드 무시(재현성 보장)
   - *plan.md Gate 0 Strict* — DAG depth ≤ f(wall-clock budget) [≤6h: depth ≤3 / 6~24h: ≤2 / >24h: ≤2 + 8h마다 checkpoint phase 강제]. 사용자 1회 검토·승인 후 immutable lock. Soft replan(같은 phase 파라미터 조정·재실행: 자동 허용 + 횟수 상한) vs Hard replan(phase 추가·삭제·순서 변경: alert + pause) 2-tier
   - *Mission Spec 7항목 Schema* — 7항목 정의·verbatim confirm 의무·orchestrator 시작 거부(코드 차원)는 **Phase 0 종료 게이트 (5번째 항목) 참조** (SOT 단일)

   상세 메커니즘(7대 설계 원칙·D1~D8 implementation details·Run Manifest 정밀 구조·3-tier verification 정밀 정의·Wall-Clock 적응 cache 전략·Pipeline × 인스턴스 Integration ADR 6항): 각 인스턴스의 design SOT 문서 참조 (§4 Step 1). **인스턴스 예시 (Long Harness Autonomous Agent System)**: `cys-claude-foresight-skills/docs/long-harness-system-design.md` 참조.

각 Phase의 산출물이 다음 Phase의 검증 가능한 입력 제약이 되는 구조로, 절대 기준 1(품질)을 프로세스 차원에서 보장한다. 도구 레벨에서는 §-1 Skill Toolkit이 그 검증 게이트를 자동화한다. **운영 단계의 학습 회로**는 Phase 5a의 발견이 Phase 4f의 다음 회차로, Phase 6의 신호가 §7 결정 #8(정기 아키텍처 회수)을 통해 다시 Phase 4f의 입력으로 환류되는 구조로 닫혀 있다. **Long-horizon 시스템 빌드 시 본 학습 회로는 task 누적 `cost-ledger.jsonl` 데이터를 추가 입력으로 한다.**

---

## §1. 전체 단계 흐름

각 행의 "핵심 산출물"과 "종료 게이트"는 §-1 Skill Toolkit의 슬래시 커맨드 호출을 표준 동작으로 가정한다.

| # | Phase | 목적 | 핵심 산출물 (패턴) | 종료 게이트 |
|---|---|---|---|---|
| **0** | Intent Alignment | 사용자와의 의도·목표·품질 수준 정렬 | **분기 조건** [v1.0 최초 버전 — §4 Step 4 verbatim "*비코드 의도 정렬은 `/grill-me`, 도메인 위 작업이면 처음부터 `/grill-with-docs`로 시작*" 정합]: **(a) 도메인 컨텍스트 없음 → `/grill-me`** (비코드 의도 정렬·정책 결정 인터뷰, 한 번에 한 질문) **(b) 기존 도메인 위 → `/grill-with-docs`** (도메인 모델·`CONTEXT.md`·ADR 적대적 다그침 + 즉석 문서 갱신). 산출물 = 세션 트랜스크립트 + 합의 메모 + ADR 초안 + (해당 시) `CONTEXT.md` 초안 갱신 + **`mission-spec.md` D8 v2 7항목 schema 초안** [v1.0 최초 버전] | 종료 게이트 (5항): (1) 사용자 승인 (2) 합의 사항이 `CONTEXT.md`(있는 경우)에 반영 (3) **트랜스크립트가 "한 번에 한 질문" 원칙을 지켰음을 확인** (4) **코드베이스 탐색으로 답할 수 있는 질문은 사용자에게 묻지 않고 직접 탐색했음을 확인** (5) **`mission-spec.md` D8 v2 7항목 schema verbatim confirm 의무** [v1.0 최초 버전] — 7항목 = ① Goal ② Non-Goal ③ Success Criteria (T1 checkable) ④ Out-of-Scope ⑤ Acceptance Test ⑥ Deliverable Schema ⑦ **Wall-Clock Budget** (target wall-clock + hard ceiling = target × 1.5). **사용자 본인이 1회 verbatim confirm**. confirm 없이 orchestrator 시작 거부(코드 차원). |
| **1** | Interface | 본 워크플로우와 다운스트림 시스템의 인터페이스 동결 | `{workflow}-output-contract.md` (Interface = 호출자가 알아야 할 모든 것: 타입·invariant·error mode·ordering·config) **+ Long-Horizon Autonomous 시스템의 경우 3-part contract** [v1.0 최초 버전] — **(a) skill 호출 ABI**: §0 (b) "*Sub-agent inject 강제 — mission-spec verbatim + plan.md의 declarative dependency graph 명세대로 prior artifacts + 산출 schema*" verbatim 4 항목 명세 (`docs/long-harness-system-design.md §10` "Phase 1: 인스턴스 인터페이스 contract (skill 호출 ABI)" 자산). **(b) verifier API**: T1·T2·T3 3-tier verifier 의 input · output · status code 명세 (`docs/long-harness-system-design.md §4` "3-Tier Verification" 메커니즘 + §5 D1 "T1 Hard Gate 코드 차원 강제" 자산 reference). **(c) orchestrator dispatch API**: `docs/long-harness-system-design.md §2` "*master claude agent가 python script를 호출, script는 매 step마다 (mission-spec.md + plan.md 현재 상태 + 직전 step output) 만 disk에서 읽기, 다음 step을 결정하고 skill을 inline으로 호출*" verbatim 4 단계 명세. **일반 워크플로우 (§3 4번째 축 적용 조건 N/A) 는 단일 contract 유지.** | **인터페이스 contract 자체는 ADR 3-조건을 자동 충족하므로 ADR 등록**. 단 contract 안의 세부 결정 중 3-조건을 충족하지 않는 항목은 ADR이 아니라 `CONTEXT.md`로만 흡수 + `/grill-with-docs`로 contract와 도메인 모델의 정합 확인 **+ Long-Horizon Autonomous 시스템의 경우 3-part contract (a/b/c) 동결 확인 의무** [v1.0 최초 버전] |
| **1.5** | Contract Stress Test | 인터페이스 적대적 검증 (경계 케이스·악성 입력·확장성·버전 호환) + **장기간 자율 3대 위험 시나리오 검증** [v1.0 최초 버전] | Stress Report + contract v1.x 패치 + vertical-slice 시나리오 ≥3 + adversarial review 트랜스크립트 + **장기간 자율 3대 위험 시나리오 카탈로그** [v1.0 최초 버전] — 시나리오 카탈로그: **(1) Compaction Destruction** (시간 누적, 강) — 가상 `mission-spec.md` verbatim 무결성 검증 (SHA256 hash + Mission Spec Immutability 메커니즘 작동 확인). 검증 시점은 **A5 (Phase 3.5 Dry-Run)** 또는 인스턴스 파이프라인 문서에서 Wall-Clock Budget 기준으로 결정. **(2) Sub-agent Isolation** (시간 무관) — 단일 call 단위로 declarative dependency graph 위반 inject 시도 → T1 verifier 차단 확인. 통과 기준 정량화는 **A4 (Phase 2-Eval)** 에서 결정. **(3) Reward Hacking** (시간 누적, 강) — verifier 우회 시도(schema는 맞추지만 referential integrity 위반·표면적으로 그럴듯한 산출 등) → T1·T2 검출 확인. 시간 임계는 **A5**, 통과 기준은 **A4** 에서 결정. | @reviewer + @fact-checker 통과 (페르소나 자격·도구·통과 기준 SOT = §2 횡단 C reference link · AgenticWorkflow 5 자산 verbatim 적용 — `reviewer.md` + `fact-checker.md` frontmatter / `AGENTS-ko-backup.md §5.5` 도구 분리 + Generator-Critic / `validate_review.py` P1 결정론적 통과 기준 / `README.md` 페르소나 명세) [v1.0 최초 버전] + `/grill-with-docs` cross-check로 `CONTEXT.md` 충돌 0건 + **3대 위험 시나리오 카탈로그 정의 완료** [v1.0 최초 버전] |
| **2** | Specification | 명세 4문서 작성 | PRD + Functional-Spec + Test-Plan + Eval-Plan | 사용자 승인 |
| ↳ 2-PRD | PRD | mattpocock 표준 PRD 7섹션 + IPP 하네스 5섹션 | `{workflow}-prd.md` (이슈 트래커에 `needs-triage` 라벨로 게시) | **PRD 작성 전: 이 PRD가 만들 모듈 후보를 스케치하고, deep modules 후보를 추출하며, 사용자에게 "어느 모듈에 테스트가 필요한지"를 확인 완료** + `/to-prd` 산출물이 이슈 트래커에 게시됨 **+ 도메인 위 작업이면 `/grill-with-docs`로 PRD의 도메인 어휘·`CONTEXT.md` 충돌 cross-check 완료** [v1.0 최초 버전] |
| ↳ 2-Spec | Functional-Spec | 알고리즘 의사코드 (도메인 결정론·LLM 통합 분기 다이어그램) — 모듈 구조는 PRD에 이미 deep modules 후보로 들어있음 **+ 결정론 vs LLM 영역 분리 표 강제** [v1.0 최초 버전] — 표 양식 4 열: ① **행동** (§1 Phase 4a "*행동 카탈로그*" verbatim 어휘 활용 — Phase 4a ID 부여 전 사전 가설, Phase 4a 매핑 확정 의무) ② **분류** (§1 Phase 4c·4d verbatim "*결정론(4c) / LLM 통합(4d)*" 어휘) ③ **Phase 4 라우팅** (4c / 4d — §1 Phase 4c·4d verbatim "*행동 단위로 분기*" 자산 정합) ④ **Verifier 매핑** (T1 / T2 / T3 — Phase 2-Eval (A4) 3-tier verification 정형 입력 자산 + `docs/long-harness-system-design.md §4` verbatim reference). **Phase 4c/4d 사전 분류 입력 자산** 이며 Phase 2-Test (*결정론 영역*) + Phase 2-Eval (*LLM 분포 영역*) 분기의 sanity check (§1 자산 어휘 정합). | `{workflow}-spec.md` | **결정론 vs LLM 영역 분리 표 작성 완료 — 행동 단위 분기·Phase 4 라우팅·Verifier 매핑 4 열 정합 확인** [v1.0 최초 버전] |
| ↳ 2-Test | Test-Plan | 단위·통합 테스트 (결정론 영역) — **단위 테스트는 내부 구현이 아니라 모듈 인터페이스를 검증한다** | `{workflow}-test-plan.md` | 인터페이스-만-테스트 게이트 통과 + **테스트 슈트는 *행동 카탈로그* 형태로만 보관(실제 실패 테스트로의 변환은 4a에서 1건씩만 — horizontal slicing 사전 차단)** |
| ↳ 2-Eval | Eval-Plan | Behavioral·Adversarial·Regression·Calibration evals — **prompt-aware tests 포함** + **3-tier Verification 정형 명문화** [v1.0 최초 버전] (LLM 분포 영역) | `{workflow}-eval-plan.md` — **3-tier 카테고리 명시** [v1.0 최초 버전]: **T1 — Rule-based deterministic hard gate** (외부 python 코드, LLM 우회 불가, count·format·schema·필수 항목 검증 + referential integrity hard check). **T2 — LLM verifier** (구조·일관성 검증, 사용자 영역 전문 기준. **명시적 한계: 예측의 진실성 검증 불가** — protocol 명문화. @reviewer + @fact-checker 페르소나 통합은 **A9** 에서 결정). **T3 — Spot-check** (자율의 사후 안전망. 빈도·시간 protocol은 위험 3 결정에 위임 — ADR 갱신 트리거). 상세 메커니즘: `docs/long-harness-system-design.md §4` 참조. 정량 임계 SOT: **A7 (Phase 4d Free-부분 편차 KPI)**. | **3-tier 카테고리 명시 완료 + `docs/long-harness-system-design.md §4` cross-reference link 검증** [v1.0 최초 버전] |
| **2.5** | Build-Time Asset Curation | 정적 자산 합성 + 사용자 큐레이션 | 도메인 정적 자산 (reference docs · 결정론 lookup table · controlled vocabulary 등) **+ 사용자 voice reference document** [v1.0 최초 버전] — **Long-Horizon Autonomous 시스템 (§3 4번째 축 적용 조건) 의 경우 사용자 자산 의존 시** 적용. 구체 자산 형태 (예: 사용자 글쓰기 스타일 스킬·사용자 기존 글·전형 어휘 표 등) 는 인스턴스 파이프라인 문서에서 결정. **Reward Hacking 차단 사전 자산** — Phase 1.5 (A3) "장기간 자율 3대 위험 시나리오 카탈로그" 3번째 위험 (Reward Hacking) verbatim 대응 자산. Phase 4d LLM 통합 모듈의 사용자 voice 정합 ground truth. §0 (b) verbatim "*T3 spot-check는 두 파일 cross-reference로 reward hacking(자기 결정 사후 미화) 차단*" 사후 안전망과는 layer 분리 (사전 자산 vs 사후 안전망). | 사용자 큐레이션 완료 + 자산이 도입한 신규 도메인 용어가 `CONTEXT.md`에 등재 + **`/zoom-out` 식 자산 지도(자산 ↔ 호출 모듈) 1매 생성** **+ Long-Horizon 시스템 + 사용자 자산 의존 시 사용자 voice reference document 등재 완료** [v1.0 최초 버전] |
| **3** | Procedure Design | 워크플로우 단계별 절차 설계 | `workflows/{name}/workflow.md` | DNA 유전 P1 검증 통과 + `/zoom-out` 1회 실행으로 부모 시스템 내 위치를 모듈 지도로 부착 + **`workflow.md`의 모든 단계 명칭이 `CONTEXT.md`에 등재된 어휘만 사용**(정형 게이트로 격상) + **Long-Horizon Autonomous 시스템의 경우 `workflow.md` 동결 시 `plan.md` DAG depth gate 정책 명시 의무** [v1.0 최초 버전] — §0 (d) verbatim "*plan.md Gate 0 Strict — DAG depth ≤ f(wall-clock budget) [≤6h: depth ≤3 / 6~24h: ≤2 / >24h: ≤2 + 8h마다 checkpoint phase 강제]*" 자산. **`plan.md` 자체는 task 시작 시 orchestrator 생성** (인스턴스 design 문서 §5 D2 양식 — 예: Long Harness 인스턴스 `cys-claude-foresight-skills/docs/long-harness-system-design.md §5 D2` verbatim "*Task 시작 시 orchestrator가 plan.md 생성, 사용자가 1회 검토/승인 후 immutable로 lock*" + 2-tier replan: Soft replan 자동 허용·횟수 상한 / Hard replan alert + pause). Wall-Clock Budget 자산 = §0 (a) reference. `plan.md` = Run Manifest (`docs/long-harness-system-design.md §3` "*_runs/<task-id>/plan.md*") External Environment Objects 자연 한정 (§3 4번째 축 적용 조건). |
| **3.5** | Workflow Dry-Run | 가상 시나리오 2-3개로 종이 위 시뮬레이션 + **1h prototype + wall-clock full run prototype** [v1.0 최초 버전] | Dry-Run Report + `workflow.md` 패치 + **Prototype Report** [v1.0 최초 버전] — prototype 명세: **(1) 1h prototype** — cost ceiling 측정 (`unit_cost_per_skill × expected_steps × 안전계수 1.5`). 인스턴스 design 문서 (예: cys-claude-foresight-skills/docs/long-harness-system-design.md) §5 D3 명시. **(2) Wall-clock full run prototype 1회** — 인스턴스 파이프라인 문서의 wall-clock budget 100% 시점까지 실제 LLM call로 가동. | 모든 Verification 자동 검증 가능 확인 (= `/diagnose` Phase 1의 deterministic / fast / sharp feedback loop 체크리스트 통과) + **dry-run 검증 자동화의 정량 목표 = T1 verifier 2초 deterministic 루프** (step 전체는 LLM call TTL에 의존·분 단위 — 미달 시 루프 자체를 product로 보고 개선 후 재진입) + **cost ceiling 측정 완료 (1h prototype)** [v1.0 최초 버전] + **wall-clock full run prototype 완료** [v1.0 최초 버전] |
| **3.7** | Prompt Engineering | `workflow.md`의 추상 단계를 실제 프롬프트로 변환 + **cache 영역 5-15KB system prompt 구성** [v1.0 최초 버전] | System prompts + Few-shot 예시 큐레이션 + Prompt versioning 체계 (프롬프트의 도메인 용어 = `CONTEXT.md` 표기) + **cache 영역 정의** [v1.0 최초 버전] — **System prompt (`cache_control: ephemeral`, 5-15KB — Claude Max 환경 자동 적용 · 사용자 ABSOLUTE ANCHOR 4 정합)**: `mission-spec.md` verbatim · `plan.md` verbatim (lock 후) · `skills_snapshot` · 현재 phase schema 요구사항. **User prompt (cache 외, 매 step 변화)** — runtime 메커니즘이므로 Phase 4e Run Manifest + `docs/long-harness-system-design.md §7` 참조. **Wall-clock 적응 cache 전략** — §0 4번째 축 (c) Pause/Resume Protocol 참조. **Cache invalidation trigger** — `docs/long-harness-system-design.md §7` 안전장치 참조. **정량 임계 (cache hit ratio) 는 A14 (Prototype 추가 측정 지표) 에서 결정**. **Few-shot 예시 cache 포함 여부는 인스턴스 파이프라인 문서에서 결정**. | Eval-Plan의 prompt-aware test 통과 + `/grill-with-docs`로 예시별 용어 적정성 다그침 완료 + **prompt-aware test의 어서션이 모델 내부 추론 토큰이 아니라 *공개 출력의 행동*을 검증함을 확인**(모델 버전 의존적 회귀 폭탄 방지) + **cache 영역 system prompt 4항목 정의 완료 + wall-clock 적응·invalidation trigger cross-reference link 검증** [v1.0 최초 버전] |
| **4** | Implementation (TDD via `/tdd`, vertical slice per behavior) | TDD 사이클로 구현 — **horizontal slicing 금지**. **Phase 4 진입 직전 `/to-issues`로 PRD/계획을 vertical-slice(tracer-bullet) 단위 이슈로 분해 의무** [v1.0 최초 버전] | 코드·Hook·Sub-agent 일체 | 4f 통과 |
| ↳ 4a | Test 슈트 골격 **[`/tdd` RED 단계 강제]** | Test-Plan / Eval-Plan을 *행동 카탈로그*로 변환. 한 행동당 한 테스트만 실패 상태로 미리 둠. 나머지는 카탈로그 형태로 보관. **`/tdd` red-green-refactor 사이클의 RED 진입** [v1.0 최초 버전 — §-1 verbatim "*/tdd \| 한 테스트 → 한 구현의 vertical-slice red-green-refactor \| **Phase 4 (a~f) 전체***" 호출 위치 정합] | 행동 카탈로그 + 첫 tracer-bullet 실패 테스트 | tracer-bullet 1건이 RED 상태 |
| ↳ 4b | 빌드 타임 자산 코드화 **[`/tdd` 자산 무결성 테스트 강제]** | Phase 2.5 자산을 import 가능 형태로. **자산 무결성 테스트는 `/tdd` 양식 RED→GREEN 통과** (public lookup API 레벨) | `assets/*` lookup 모듈 | 자산 무결성 테스트가 **public lookup API 레벨**에서 PASS (내부 구조 비교 금지) |
| ↳ 4c · 4d | 행동별 RED → GREEN 반복 **[`/tdd` 메인 사이클 강제]** | 결정론(4c) / LLM 통합(4d) 경계는 **모듈 단위가 아니라 행동 단위**로 분기. 각 행동마다 한 테스트 → 한 구현 (= `/tdd` red-green-refactor verbatim 양식, 각 행동별 1 사이클) | 결정론 모듈 코드 + LLM 통합 모듈 코드 + **Free-부분 편차 KPI 3종 정의** [v1.0 최초 버전]: **(1) T2 Verifier 일관성 95%+** (동일 입력을 n회 동일 LLM에 inject → schema 통과율) · **(2) Skill 산출 referential integrity 100%** (같은 prior artifact + 같은 `mission-spec.md` → 후속 skill 산출 ID 인용 일치율) · **(3) Cache hit consistency 98%+** (cache hit/miss 상황에서 LLM 산출 의미 동일성 — **A6 Phase 3.7 cache hit ratio 측정과 별개**). **출처**: 본 프로토콜 v1.0 정의 시점에서 도출 (각 인스턴스 design 문서에 직접 명시는 선택). **n (동일 입력 반복 횟수) · 측정 protocol 정밀화는 §10 후속 대기열 A16 (Free-부분 편차 KPI 측정 protocol 정밀화) 또는 인스턴스 파이프라인 문서에서 결정**. | 4a 카탈로그의 모든 행동이 RED→GREEN을 1주기 통과 + **4d Free-부분 편차 KPI 통과 (T2 95%+ / referential 100% / cache 98%+)** [v1.0 최초 버전] + **LLM 통합 모듈 디버깅 시 모든 임시 로그는 `[DEBUG-xxxx]` 태그 의무**(5a의 "DEBUG 0건" 게이트와 직결) |
| ↳ 4e | HITL · Hook · Sub-agent · Safety · Observability 통합 **[`/tdd` E2E 시나리오 강제]** | 게이트 인터페이스 + Safety filter + 관측성 hooks. **E2E 단일 시나리오는 `/tdd` 양식 RED→GREEN 통과** + `/diagnose` Phase 1 deterministic 2초 루프 결합 | `.claude/agents/*.md`, `settings.json`, Safety Layer, Observability dashboard | E2E 단일 시나리오가 `/diagnose` Phase 1식 *deterministic 2초 루프*로 통과 |
| ↳ 4f | 통합 테스트 (horizontal 허용 격리 구간) **[`/tdd` 4a~4e 누적 검증 강제]** | 모든 sub-phase 결합 검증. 본 절에 한해 horizontal 통합 테스트 허용. **4a~4e의 `/tdd` 사이클로 만들어진 모든 단위·통합·eval 슈트 GREEN 확인 + `/improve-codebase-architecture` 1-pass 의무 실행** | 통합 테스트 통과 보고 + **모듈별 deletion test 결과 1줄 기록(살아남음 / 흩어짐)** | 모든 단위·통합·eval 슈트 GREEN + **`/improve-codebase-architecture` 1-pass 의무 실행** + **deletion test에서 "흩어짐" 판정 모듈은 5a 진입 금지 — 통합 또는 삭제 후 4f 재실행** + **5a에서 환류된 'no-seam findings'를 본 회차의 입력으로 처리** |
| **5a** | Unit / Integration / Eval Validation + Failure Mode Coverage **(빌드 단계 한정)** [v1.0 최초 버전] | **Phase 5a 진입 시 `/zoom-out` 1회 실행으로 모듈 지도 재확인** [v1.0 최초 버전] + Test-Plan + Eval-Plan + 실패 모드 카탈로그 자동 검증. 발견된 모든 버그는 `/diagnose` 6-Phase 강제 (feedback loop → reproduce → hypothesise → instrument → fix+regression test → cleanup+post-mortem) — **본 절차는 빌드 단계에서만 적용** [v1.0 최초 버전]. **자율 실행 단계 (long-horizon autonomous task 실행 중) 처리는 `docs/long-harness-system-design.md §8` 참조** — `/diagnose` Phase 1~4는 자율 자동, Phase 5~6은 사용자 spot-check. RLM 패턴 정합 (자율 실행 단계 즉시 fix=신경망 직접 처리 금지, fail은 `spot_check_queue` 외부 객체에 등재). | KPI 보고 + 실패 모드 회귀 테스트 통과 + 각 버그의 commit / PR 메시지에 **(a) 맞은 가설 + (b) (있다면) 아키텍처 hand-off 권고 + (c) (있다면) `/improve-codebase-architecture` 트리거 사유** 3종 세트 명시 | 전 항목 PASS + `grep '\[DEBUG-'` 결과 0건 + 아키텍처 hand-off 필요 여부 판단 완료 + **올바른 seam이 없어 회귀 테스트를 적절히 만들지 못한 버그는 'no-seam finding'으로 risk-register에 등재 + Phase 4f의 다음 회차 `/improve-codebase-architecture` 1-pass에 자동 입력**(폐쇄 학습 루프, 빌드 단계 한정) + **빌드 단계 한정 명시 (자율 실행 단계는 `docs/long-harness-system-design.md §8` 처리)** [v1.0 최초 버전] |
| **5b** | Acceptance Test | 골든 페르소나·골든 시나리오 실제 실행 + 사용자 평가 | 도메인 KPI 실증 보고 (수용 결정의 근거 문장이 PRD의 Implementation Decisions와 1:1 대응) + **수용 평가 보고는 `CONTEXT.md` 어휘로만 작성** | 사용자 수용 |
| **6** | Continuous Learning Setup | 운영 단계 진입 전 6+1+1대 정책 결정 + 인프라 활성화 | ADR + Feedback Logger · Drift Detector · Pattern Miner · Asset Updater · Regression Guard · Recalibration Pipeline (모든 메트릭 명칭이 `CONTEXT.md` 어휘로 명명) + `/triage` 자동 등록 파이프라인 + **`/zoom-out` 자동 트리거 파이프라인**(신규 메트릭/사건이 임계 초과 시 모듈 지도 1매 자동 생성 → 인스턴스 파이프라인 문서에 첨부) **+ Long-Horizon Autonomous 시스템 적용 방식** [v1.0 최초 버전]: **모듈 지도 대응 자산** = `docs/long-harness-system-design.md §8` "자산 매핑" verbatim "*`/zoom-out` 모듈 지도 | `plan.md` dependency graph + Gate 0 depth*". **자동 트리거 임계** = `docs/long-harness-system-design.md §9` Phase 6 8개 결정 디폴트 #2 verbatim "*공격적 (T1 fail 누적 ≥3 즉시 pause)*" (§7 결정 #2 Drift threshold 의 인스턴스 디폴트 (예: Long Harness)). **트리거 결과** = §0 (d) verbatim "*Hard replan (phase 추가·삭제·순서 변경: alert + pause)*" 메커니즘. **"지속 운영" 의미 자체의 일반 vs Long-Horizon Autonomous task 일회성 관계 명확화는 §10 §B B10 위임** (SOT 분리). + **§7 결정 #8(정기 아키텍처 회수) 스케줄러** | 사용자 정책 승인 |

---

## §2. 횡단 활동 (모든 Phase에 지속 적용)

| # | 활동 | 적용 방식 |
|---|---|---|
| **A** | Decision Log (ADR) | 모든 Phase의 설계 결정을 `DECISION-LOG.md`에 ADR로 등록. 단 ADR은 `/grill-with-docs`의 **3-조건**(Hard to reverse · Surprising without context · Real trade-off)을 모두 충족할 때만 만든다. 그 외의 도메인 어휘 변동은 `CONTEXT.md` 인라인 갱신으로 처리해 ADR 인플레이션을 방지. |
| **B** | Context Preservation | Hook 시스템(`save_context.py` / `restore_context.py`)이 모든 Phase에서 자동 작동. 컨텍스트 직렬화 포맷에 **`CONTEXT.md` 해시 · `docs/adr/` 최신 ADR 번호**를 함께 저장하여 세션 복원 시 도메인 어휘 동기화. **`knowledge-index.jsonl`** (AgenticWorkflow RLM 자산 — Grep으로 검색 가능한 과거 세션 인덱스, 메타데이터: `phase` · `phase_flow` · `primary_language` · `error_patterns(+resolution)` · `tool_sequence` · `final_status` · `tags` · `session_duration_entries`) 를 통한 프로그래밍적 탐색 기반 RLM sub-call. Resume Protocol에는 **동적 RLM 쿼리 힌트** 포함 — `extract_path_tags()` 로 경로 태그 추출 (CamelCase/snake_case 분리 + 확장자 매핑 `_EXT_TAGS`) → 세션별 맞춤 Grep 예시 자동 생성. **+ Long-Horizon Autonomous 시스템의 경우 task 단위 Resume protocol 결합 명시** [v1.0 최초 버전] — 본 §2 횡단 B의 **세션-level resume (Claude Code 채널, `save_context.py` / `restore_context.py`)** 자산과 **별도 layer** 로, Long-Horizon Autonomous **task 단위 Resume (Run Manifest 채널)** 시 §0 (c) verbatim "*Resume 시 직전 phase의 `verifier-reports/<phase>.json`을 **반드시 먼저** 읽고 pass 상태 확인 후에만 다음 phase 진입*" 의무 (`docs/long-harness-system-design.md §5 D5` "Pause/Resume 시 Verifier 재실행" + §3 Run Manifest verbatim "*verifier-reports/  # T1/T2/T3 결과. resume 진입 시 먼저 확인*" 자산 정합). **두 layer 결합** — 세션 복원 (Claude Code 채널) + task 단위 Resume (Run Manifest 채널) 자산 모두 활용. §3 4번째 축 적용 조건 자연 한정 (Run Manifest 자산). |
| **C** | Adversarial Review | 각 Phase 종료 게이트에서 @reviewer + @fact-checker 적대적 검토. **Phase 4f 직후 `/improve-codebase-architecture` 1-pass를 의무화** — deletion test에서 "흩어짐" 판정 모듈은 Phase 5a 진입 금지. **Phase 5a의 'no-seam findings'는 Phase 4f의 다음 회차 1-pass 입력으로 자동 환류**. Phase 1.5는 활동 자체가 적대적 검증이므로 중복 제외. **자율 실행 단계: @reviewer + @fact-checker 페르소나는 T2 LLM verifier prompt에 통합** [v1.0 최초 버전]. 빌드 단계 phase 게이트의 적대적 검토는 자율 실행 T2 통합과 **별도 작동** (SOT 분리). Phase 2-Eval (T2 verifier 카테고리 정의) 참조. **빌드 단계 적대적 검토 페르소나·도구·통과 기준 SOT** [v1.0 최초 버전]: 본 §2 횡단 C의 "각 Phase 종료 게이트에서 @reviewer + @fact-checker 적대적 검토" verbatim 에 사용된 두 페르소나의 자격·도구·통과 기준은 AgenticWorkflow 자산에 정의되어 있다. **(a) 페르소나 자격 SOT** = `AgenticWorkflow/.claude/agents/reviewer.md` frontmatter verbatim "*Adversarial code/output reviewer — Enhanced L2 quality layer with independent pACS scoring*" + `model: opus` / `AgenticWorkflow/.claude/agents/fact-checker.md` frontmatter verbatim "*Adversarial fact verification agent — independent source verification with claim-by-claim analysis*" + `model: opus`. **(b) 도구 분리 SOT** = `AgenticWorkflow/AGENTS-ko-backup.md §5.5` verbatim P2 도구 분리 근거 "*@reviewer는 코드/문서의 내부 논리를 검토하므로 읽기만 필요. @fact-checker는 외부 사실 검증이 필요하므로 웹 접근이 필요. 최소 권한 원칙*" — reviewer 도구 = `Read, Glob, Grep` (읽기 전용) / fact-checker 도구 = `Read, Glob, Grep, WebSearch, WebFetch`. **(c) 통과 기준 SOT** = `AgenticWorkflow/.claude/hooks/scripts/validate_review.py` 결정론적 P1 검증 (`AGENTS-ko-backup.md §5.5` verbatim "*P1 검증(`validate_review.py`)으로 결정론적 품질 보장*"). **(d) 트리거 명시 SOT** = `AGENTS-ko-backup.md §5.5` verbatim "*워크플로우 설계 시 `Review: @reviewer` 또는 `Review: @reviewer + @fact-checker`를 명시한 단계에서 적용. 기본값은 자기 평가(L1.5)만*". **(e) prompt 정밀 양식** (Generator-Critic 패턴 = `AGENTS-ko-backup.md:33` verbatim · 독립적 pACS(F/C/L) 재채점 = `README.md:86` verbatim · claim-by-claim 분석 = `README.md:87` verbatim) **은 사용자 AgenticWorkflow 4 자산 SOT 에 위임** — 본 프로토콜은 reference link 만 유지 (SOT 단일·사용자 자산 권위 보존). 본 §2 횡단 C 빌드 단계 적대적 검토는 사용자 AgenticWorkflow 5 자산 SOT 그대로 적용하며, 자율 실행 단계 T2 통합 (A9) 와는 **별도 작동** (현재 본문 verbatim "*별도 작동 (SOT 분리)*" 정합). |
| **D** | Risk Register + Failure Mode Library | `{workflow}-risk-register.md` 살아있는 문서. Phase 2에서 초안, 모든 Phase에서 발견된 위험·실패 모드 추가. **운영 단계에서 발견된 모든 실패는 `/diagnose`의 Phase 6(post-mortem)을 거쳐 결과 가설을 risk-register에 1행으로 기록**. **'no-seam findings'는 별도 태그로 분류해 §7 결정 #8 정기 회수의 우선 검토 입력으로 사용**. Phase 5a 회귀 테스트 입력으로 사용. **risk-register 등재 항목은 `/triage` 5-state 머신을 통해 라우팅 의무** [v1.0 최초 버전 — §-1 Skill Toolkit verbatim "*/triage \| 이슈를 5-state 머신으로 운영 \| §4 Step 5, Phase 6, **횡단 D***" 호출 위치 정합] — `needs-triage` 등록 → `needs-info` / `ready-for-agent` / `ready-for-human` / `wontfix` 분기로 처리. /grill-with-docs로 ADR 3-조건 충족 시 ADR 등재 (횡단 A 정합). |
| **E** | Observability Layer | 에이전트 사고 trace + 도구 사용 로그 + LLM 분산 추적 + HITL 결정 분포. Phase 4e에서 인프라 구축, Phase 5·6에서 활성 운영. **관측 데이터에서 추출되는 도메인 사건 명칭은 반드시 `CONTEXT.md` 어휘로 정규화**(예: "lesson materialization cascade"). **임계 초과 사건은 Phase 6의 `/zoom-out` 자동 트리거 파이프라인의 입력**이 된다. **+ Long-Horizon 시스템의 경우 `cost-ledger.jsonl` 결합 명시** [v1.0 최초 버전] — Long-Horizon Autonomous Observability Layer 입력 채널에 `docs/long-harness-system-design.md §3` Run Manifest verbatim "*`cost-ledger.jsonl`  # 토큰·달러 누적*" 자산 추가. **임계 초과 트리거** = `docs/long-harness-system-design.md §9` Phase 6 8개 결정 디폴트 #6 verbatim "*자동 롤백 임계 = T1 fail ≥3 + cost-ledger 1.5× 초과*" 또는 §0 (a) verbatim "*Hard ceiling = target × 1.5 초과 시 자동 pause + 사용자 alert*" 메커니즘 (두 자산 동일 1.5× 임계의 다른 표현). **다중 task 누적치 환류** = `docs/long-harness-system-design.md §8` 환류 채널 verbatim "*multi-task → Pipeline §8 + §7 결정 #8: `cost-ledger.jsonl` 누적치를 정기 회수 시 cross-reference → 본 프로토콜 v1.x 진화 입력*". **B7 (§1 Phase 6 `/zoom-out` 자동 트리거 임계 = §9 #2 verbatim "T1 fail 누적 ≥3") 와는 별개 임계** (§9 #6 + §0 (a) cost-ledger 1.5× 초과) — SOT 분리. §3 4번째 축 적용 조건 자연 한정 (`cost-ledger.jsonl` = Run Manifest 자산). |

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
| 6 Continuous Learning | **조건부** (Long-Horizon Autonomous 시스템은 **필수**) | 운영 단계에서 진화·드리프트가 발생할 수 있는 시스템(LLM 기반 · 외부 데이터 의존 · 사용자 분포 변화 가능)에 필수. 일회성 도구는 선택. **+ Long-Horizon Autonomous 시스템: 시스템 운영 (지속) vs task 실행 (일회성) 분리 명확화** [v1.0 최초 버전] — `docs/long-harness-system-design.md §8` 객체 차이 표 verbatim "*적용 시점: 시스템 빌드 1회 / task 단위 N회*" 자산. **시스템 자체** = 1회 빌드 후 운영 단계 진입 (지속 운영). **task 실행** = 일회성 (task 단위 N회 반복). **Phase 6 학습 회로는 시스템 운영 레벨에 적용** = `docs/long-harness-system-design.md §8` 환류 채널 verbatim "*task-level → Pipeline 5a / multi-task → Pipeline §8 + §7 결정 #8*" + `docs/long-harness-system-design.md §9` Phase 6 8개 결정 디폴트 (인스턴스 디폴트 (예: Long Harness)). **Long-Horizon Autonomous 시스템 = LLM 기반 코어 → 본 표 조건부 분류상 자연 필수**. **B7 (§1 Phase 6 적용 방식 inject) 와 SOT 분리** — B7 = §1 자산 (운영 단계 진입 전 인프라·자동 트리거 메커니즘) / B10 = §3 자산 (적용 분류 + 의미 명확화). |

### 4번째 축 적용 조건 (§0 Long-Horizon Autonomous Layer) [v1.0 최초 버전]

§0 4번째 축 "Long-Horizon Autonomous (Time-Cumulative Operation Layer)"는 다음 3 조건 **모두 충족 시 필수**:

1. **Wall-Clock Budget > 4시간**
2. **자율 실행** (사용자 입력 없이 LLM이 자체 진행)
3. **LLM 코어 시스템** (LLM이 핵심 추론 담당)

그 외 시스템 (짧은 batch · 결정론 · 실시간 응답)에서는 **N/A 처리**. N/A 사유는 ADR로 등재 (아래 "조건부 Phase 생략 결정 절차" 동일 적용).

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
- **Long-horizon 시스템인 경우 (§0 4번째 축 적용): `mission-spec.md` 7항목 schema에 Wall-Clock Budget 명시 + `plan.md` Gate 0 DAG depth ≤ f(wall-clock budget) 사전 검증.**

### Step 2. ADR 등록

`DECISION-LOG.md`에 다음 형식으로 ADR 추가:
ADR-058: {workflow} Implementation Pipeline — Instance of Universal Protocol

Date: YYYY-MM-DD
Status: Accepted
Context: {워크플로우 도메인·목적}
Decision: 본 프로토콜(docs/protocols/skillbased-implementation-pipeline.md, v1.0)을 따름. 인스턴스 문서: {인스턴스 경로}. 생략 Phase: {목록 + ADR 참조}
Rationale: {워크플로우별 도메인 근거}
Related files: 인스턴스 파이프라인 문서, 본 프로토콜, docs/agents/*.md (Skill Setup 산출물), docs/long-harness-system-design.md (4번째 축 상세 SOT)

### Step 3. 횡단 활동 활성화

- A (Decision Log): ADR 등록 시작 — 단, **3-조건** 충족 여부를 매번 확인.
- B (Context Preservation): 자동 작동 (Hook 시스템). `CONTEXT.md` 해시 · 최신 ADR 번호 동기화 활성.
- C (Adversarial Review): 각 Phase 게이트 활성화. Phase 4f 직후 `/improve-codebase-architecture` 1-pass 자동 트리거 등록 + Phase 5a 'no-seam findings' 환류 채널 등록.
- D (Risk Register): `{name}-risk-register.md` 초안 + 'no-seam findings' 분류 태그 준비.
- E (Observability): Phase 4e 시점에 활성. 사건 명칭은 `CONTEXT.md` 어휘로 정규화. Phase 6의 `/zoom-out` 자동 트리거 파이프라인 입력 채널 등록.

### Step 4. Phase 0 진입

사용자와 의도 정렬 대화 시작. **비코드 의도 정렬은 `/grill-me`, 도메인 위 작업이면 처음부터 `/grill-with-docs`**로 시작. 한 번에 한 질문 원칙을 지키고, 코드베이스 탐색으로 답할 수 있는 질문은 사용자에게 묻지않고 직접 탐색한다. 합의가 응결되면 `CONTEXT.md` · ADR이 그 회차 내에서 동시에 갱신되어야 함. Phase 0 합의가 메모리·ADR로 응결되면 Phase 1로 진행.

**Long-horizon 시스템 (§0 4번째 축 적용)** [v1.0 최초 버전]: Phase 0 진입 시점에 `mission-spec.md` D8 v2 7항목 schema 정의 의무 — ① Goal · ② Non-Goal · ③ Success Criteria (T1 checkable) · ④ Out-of-Scope · ⑤ Acceptance Test · ⑥ Deliverable Schema · ⑦ **Wall-Clock Budget** (target wall-clock + hard ceiling = target × 1.5). 사용자 본인 verbatim confirm 의무는 **Phase 0 종료 게이트 (§1 Phase 0 5번째 항목) 참조** (SOT 단일).

### Step 5. 진행 추적

인스턴스 파이프라인 문서의 §6 Status 표를 Phase 완료 시마다 갱신. 각 Phase 완료 시 ADR 등록(3-조건 충족 시)에 더해, **이슈 트래커의 해당 PRD / 슬라이스 상태를 `/triage`로 다음 단계 라벨로 이동**(예: `needs-triage` → `ready-for-agent` → 구현 후 close)할 것을 의무화. **Phase 5a에서 발견된 'no-seam findings'는 risk-register 등재와 동시에, 다음 Phase 4f 회차의 `/improve-codebase-architecture` 1-pass 입력 대기열에 자동 등록**한다.

**Long-Horizon Autonomous 빌드 환경 vs 자율 실행 환경 `/triage` 5-state 작동 위치 매핑** [v1.0 최초 버전]: 본 §4 Step 5의 "이슈 트래커" 실체와 `/triage` 5-state 작동 위치는 AgenticWorkflow 자산에 정의되어 있으며, 빌드 환경과 자율 실행 환경에서 작동 객체가 분리된다. **(a) 이슈 트래커 SOT** = `docs/agents/issue-tracker.md` (`§5` 절대 기준 매핑 verbatim "*이슈 트래커 워크플로우 SOT = `docs/agents/issue-tracker.md`*" + `§-1` Skill Toolkit 전제 조건 verbatim "*신규 레포에서는 본 프로토콜 진입 전에 `/setup-matt-pocock-skills`를 1회 실행해 `docs/agents/issue-tracker.md`, `docs/agents/triage-labels.md`, `docs/agents/domain.md`가 생성되어 있어야 한다*"). **(b) `/triage` 5-state SOT** = `docs/agents/triage-labels.md` (`§5` verbatim "*트리아지 라벨 SOT = `docs/agents/triage-labels.md`*" + `§-1` verbatim 5-state 머신 "*`needs-triage` → `needs-info` / `ready-for-agent` / `ready-for-human` / `wontfix`*"). **(c) 빌드 환경 작동 위치** = Pipeline 적용 환경 (`docs/long-harness-system-design.md §10` verbatim "*Pipeline은 LLM-assisted human process, Long-Horizon Autonomous 시스템은 자율 런타임*"). 즉 Long-Horizon Autonomous 시스템 자체를 빌드하는 단계에서 본 프로토콜 Phase 0~6 진행 시 mattpocock 9종 (§-1) 호출 + 사람 + master claude agent 협업으로 `docs/agents/issue-tracker.md` + `docs/agents/triage-labels.md` SOT 그대로 작동. **(d) 자율 실행 환경 작동 위치 매핑** = `docs/long-harness-system-design.md §8` 자산 매핑 verbatim 2 행 — "*`docs/agents/issue-tracker.md` 5-state | spot-check queue + `rerun_from`*" + "*`/triage` 5-state | hard replan alert + soft replan 자동*". 즉 자율 실행 (long-horizon task 중) 은 `_runs/<task-id>/spot_check_queue/<phase>.md` (T3 안전망 — `docs/long-harness-system-design.md §3` Run Manifest verbatim "*`spot_check_queue/<phase>.md`  # T3 대기 항목. 자율의 사후 안전망*") + `rerun_from <phase>` 재시작 명령 (`§4 T3` verbatim "*사용자 spot-check → fail 판정 시 `rerun_from <phase>` 명령으로 해당 phase부터 재시작*") + Hard replan (alert + pause) / Soft replan (자동 허용·횟수 상한) 메커니즘 (`§5 D2` verbatim) 으로 매핑. **(e) 빌드 환경 vs 자율 실행 환경 SOT 분리** (응집도 보호) — 빌드 환경 SOT = `docs/agents/issue-tracker.md` + `docs/agents/triage-labels.md` / 자율 실행 환경 SOT = Run Manifest (`_runs/<task-id>/`) 외부 환경 객체. 두 환경 모두 RLM External Environment Objects 패턴 정합 (§6 DNA 유전 RLM Pattern 행 자연 적용). §3 4번째 축 적용 조건 자연 한정 (자율 실행 환경 매핑 = Long-Horizon 시스템 한정).

---

## §5. 절대 기준 매핑

| 절대 기준 | 어느 Phase에서 보장되는가 |
|---|---|
| **1 — 품질 최우선** | 전체. 특히 1.5 (stress) · 2-Eval · 3.5 (dry-run) · 5a (failure mode) · 5b (acceptance) · 6 (continuous learning)이 품질 검증의 다층 안전망. **추가**: 4f 직후 `/improve-codebase-architecture` 1-pass 의무화, 5a 모든 버그는 `/diagnose` 6-Phase 강제, **5a → 4f 폐쇄 학습 루프('no-seam findings' 환류)**, **§7 결정 #8 정기 아키텍처 회수**. **v1.0 (최초 버전 — Long-Horizon Autonomous Layer)**: 4번째 축 Drift Containment의 3-tier verification + Time Budget Management의 wall-clock hard ceiling + Skill Orchestration & Verification의 3-Layer 수정 진단 protocol이 long-horizon 시스템 품질의 추가 안전망. |
| **2 — 단일 파일 SOT** | Phase 1 (인터페이스 SOT) + Phase 4e (`state.yaml` 런타임 SOT). **추가**: 도메인 어휘 SOT = `CONTEXT.md` (`/grill-with-docs`로만 갱신), 트리아지 라벨 SOT = `docs/agents/triage-labels.md`, 이슈 트래커 워크플로우 SOT = `docs/agents/issue-tracker.md`. **v1.0 (최초 버전 — Long-Horizon Autonomous Layer)**: task 단위 SOT = `_runs/<task-id>/mission-spec.md` + `plan.md` (immutable lock 후 Gate 0). 부모 SOT와 공간 분리(Pause/Resume Protocol). |
| **3 — CCP** | Phase 4 전 sub-phase + Phase 6의 Asset Updater (운영 단계 변경에도 CCP 적용). **추가**: 운영 자산 변경은 `/triage`의 `ready-for-agent` / `ready-for-human` 분기를 통과한 이슈를 통해서만 발생. **§7 결정 #8 정기 회수의 산출물(아키텍처 변경 권고)도 동일한 분기를 통해서만 적용**. **v1.0 (최초 버전 — Long-Horizon Autonomous Layer)**: long-horizon task의 plan.md Hard replan은 alert + pause + 사용자 검토 후에만 적용. Soft replan은 자동 허용하되 횟수 상한. |

### 사용자 ABSOLUTE ANCHOR 4원칙 ↔ Pipeline 절대 기준 정합 검증 [v1.0 최초 버전]

사용자 머리말 ABSOLUTE ANCHOR 4 원칙 (resume 문서 §4 verbatim) ↔ 본 §5 Pipeline 절대 기준 1·2·3 정합 검증 1:1 매핑.

| ABSOLUTE ANCHOR (사용자 verbatim) | Pipeline 절대 기준 | 본 프로토콜 SOT 위치 |
|---|---|---|
| **1. 최고의 품질 실현이 절대원칙. 속도·토큰 소모량 무시** | **1 — 품질 최우선** (직접 매핑) | 본 §5 절대 기준 1 verbatim 전체 (Phase 전체 + 4번째 축 보강 3종) |
| **2. 워크플로우 최종 결과물 수준과 품질에 가장 적합한 것 선택** | **1 + 2** (품질 + SOT 결합) | 본 §5 절대 기준 1 (품질) + 절대 기준 2 (SOT — `CONTEXT.md`·`docs/agents/*.md`·Run Manifest task SOT) |
| **3. 로컬 실행 불변 — 로컬 실행 전제를 흔드는 결함은 최우선 배제** | **Pipeline 전체 (로컬 실행 전제)** | 본 프로토콜 머리말 ABSOLUTE ANCHOR 명시 + §0 4번째 축 4 sub-element 모두 로컬 자산 (mission-spec·plan·skills_snapshot·Run Manifest `_runs/<task-id>/` 모두 로컬 디스크 객체) |
| **4. LLM 사용 시 Claude Max 구독모델 사용 절대 규칙. API·SDK 절대 사용 금지** | **Pipeline 전체 (Claude Max 환경 자동 적용)** | §1 Phase 3.7 verbatim "*System prompt (`cache_control: ephemeral`, 5-15KB — Claude Max 환경 자동 적용 · 사용자 ABSOLUTE ANCHOR 4 정합)*" + ADR-058 §4.1 ABSOLUTE ANCHOR 4 원칙 정합 검증 verbatim 명시 |

→ **ABSOLUTE ANCHOR 4 ↔ Pipeline 절대 기준 1·2·3 정합 검증 통과. 사용자 4원칙이 Pipeline 절대 기준에 1:1 매핑되어 본 프로토콜 전체에 발현됨.**

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
| **RLM Pattern (Recursive Language Models 이론 기반 — MIT CSAIL 논문)** [v1.0 최초 버전]: ① **External Environment Objects** (프롬프트를 신경망에 직접 넣지 않고 외부 환경 객체로 취급) ② **Variable Persistence** (중간 결과를 외부 환경에 영속 저장) ③ **Code-based Filtering** (Python 결정론으로 노이즈 제거 후 LLM 추론) ④ **포인터 + 요약** (세션 복원 시 외부 메모리에서 포인터로 복원) | **§0 4번째 축 전반 (a Time Budget·b Drift Containment·c Pause/Resume·d Skill Orchestration), §2 횡단 B (Context Preservation hooks + `knowledge-index.jsonl`), Phase 4e (Run Manifest `_runs/<task-id>/`), Phase 5a (`spot_check_queue` 외부 객체), `docs/long-harness-system-design.md` (Run Manifest 정밀 구조·D1~D8)** |
| **Wall-Clock Budget** (Long-Horizon Autonomous 게놈 1) [v1.0 최초 버전] — `mission-spec.md` 7번째 항목 immutable. target wall-clock + hard ceiling = target × 1.5 초과 시 자동 pause + 사용자 alert | **§0 4번째 축 (a) Time Budget Management + §1 Phase 0 종료 게이트 5번째 항목 (7항목 schema) + §1 Phase 3.5 Dry-Run (1h prototype cost ceiling 측정) + §4 Step 1·Step 4 (인스턴스 파이프라인 문서 + Phase 0 진입 게이트)** |
| **plan.md DAG depth gate** (Long-Horizon Autonomous 게놈 2) [v1.0 최초 버전] — DAG depth ≤ f(wall-clock budget) [≤6h: depth ≤3 / 6~24h: ≤2 / >24h: ≤2 + 8h checkpoint]. Task 시작 시 orchestrator 생성, 사용자 1회 검토·승인 후 immutable lock. Soft replan(자동·횟수 상한) vs Hard replan(alert + pause) 2-tier | **§0 4번째 축 (d) Skill Orchestration & Verification + §1 Phase 3 종료 게이트 (B6) + `docs/long-harness-system-design.md §5 D2` (immutable lock) + `docs/long-harness-system-design.md §6` (Failure Cascade 방지 평탄 DAG)** |
| **T1/T2/T3 3-tier Verification** (Long-Horizon Autonomous 게놈 3) [v1.0 최초 버전] — T1 (외부 python deterministic hard gate, LLM 우회 불가) · T2 (LLM verifier, 사용자 영역 전문 기준, 예측 진실성 검증 불가 명시) · T3 (사용자 사후 spot-check, 자율 사후 안전망) | **§0 4번째 축 (b) Drift Containment + §1 Phase 2-Eval (A4 3-tier 정형 명문화) + §2 횡단 C (A9 @reviewer/@fact-checker T2 통합 + D2 페르소나 SOT) + `docs/long-harness-system-design.md §4` (3-Tier Verification 정밀)** |
| **Cache wall-clock 적응** (Long-Horizon Autonomous 게놈 4) [v1.0 최초 버전] — ≤6h: TTL 5분 ephemeral / 6~24h: TTL 5분 + 1h persistent 병행 / >24h: cache 영역 축소 / >7d: cache 비의존. System prompt 5-15KB 4항목 (mission-spec·plan·skills_snapshot·현재 phase schema) Claude Max 환경 자동 적용 (ABSOLUTE ANCHOR 4 정합) | **§0 4번째 축 (c) Pause/Resume Protocol + §1 Phase 3.7 Prompt Engineering (A6) + `docs/long-harness-system-design.md §7` (Cache 전략 + 안전장치)** |
| **ADR Integration Protocol 6항** (Long-Horizon Autonomous 게놈 5) [v1.0 최초 버전] — Pipeline × Long-Horizon Autonomous Integration ADR (작성 예정 ADR-058). 본 파일 v1.0 (최초 버전) 종합 결정 SOT | **§9 변경 이력 (각 patch entry) + §10 `docs/long-harness-system-design.md §8` (Pipeline × Long-Horizon Autonomous Integration 6항)** |

---

## §7. Phase 6 (Continuous Learning) 6+1+1대 결정 항목

운영 단계 진입 전 사용자가 결정해야 할 정책 (Phase 6 진입 시점). 이 결정들은 Phase 6 시작 시점에 ADR로 일괄 등록한다.

**각 결정 항목 진행 시 `/grill-me` 인터뷰 의무** [v1.0 최초 버전 — §-1 Skill Toolkit verbatim "*/grill-me \| 비코드(의도 정렬·정책 결정) 인터뷰 \| Phase 0 (도메인 컨텍스트가 없을 때), **§7 6+1+1대 결정***" 호출 위치 정합] — 본 §7의 결정 항목은 모두 비코드 정책 결정이므로 `/grill-me` (한 번에 한 질문 원칙) 또는 도메인 위 작업이면 `/grill-with-docs` (옵션 A·C 명시) 로 사용자 의도 정렬 인터뷰를 거쳐야 한다.

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
8. **정기 아키텍처 회수 주기** — `/improve-codebase-architecture`를 운영 단계에서 정기적으로 돌리는 주기와 책임자.
   - 옵션 A (보수): **분기 1회** — 분기 마감 직후 1-pass 실행, 결과를 ADR화하여 다음 분기 백로그로 편입.
   - 옵션 B (중간): **6주 1회** — 격주 스프린트 3회마다 1-pass 실행, "흩어짐" 판정 모듈 + 누적 'no-seam findings'를 우선 검토.
   - 옵션 C (진취): **4주 1회** — 매월 1-pass 실행 + 회귀 테스트 통과 시 deepening 후보를 자동으로 `/to-issues`로 분해.
   - 회수 결과의 모든 아키텍처 변경 권고는 §5 절대 기준 3(CCP)에 따라 `/triage`의 `ready-for-agent` / `ready-for-human` 분기를 통과한 이슈를 통해서만 적용된다.

9. **Wall-Clock Budget 갱신 정책** [v1.0 최초 버전] — task 종료 후 실측 wall-clock이 target × 1.5 (= §0 (a) verbatim "*Hard ceiling = target × 1.5 초과 시 자동 pause + 사용자 alert*" + `docs/long-harness-system-design.md §9 #6` verbatim "*자동 롤백 임계 = T1 fail ≥3 + cost-ledger 1.5× 초과*" 동일 임계) 를 초과한 패턴이 누적될 때 다음 task budget 자동 조정 정책. 적용 범위 = §3 4번째 축 적용 조건 (Wall-Clock Budget > 4시간 + 자율 실행 + LLM 코어) Long-Horizon 시스템 자연 한정.
   - 옵션 A (보수): 패턴 누적 보고서만 자동 생성. 다음 task budget 조정은 사용자 수동 결정.
   - 옵션 B (중간): 자동 추천 (실측 평균치 + 안전계수 1.5) 생성 + `/triage` 5-state `ready-for-human` 분기로 라우팅 + 사용자 수동 승인 후 다음 task budget 갱신.
   - 옵션 C (진취): 실측 1.5× 초과 패턴 3회 이상 누적 시 (`docs/long-harness-system-design.md §9 #6` T1 fail ≥3 임계 양식 정합) 자동 적용 + 회귀 테스트 통과 시 다음 task budget 갱신.

운영 단계의 모든 자동 회수 신호(Feedback Logger·Drift Detector)는 자동으로 이슈 트래커에 `needs-triage` 라벨로 등록되고, 그 이후의 진행은 `/triage` 5-state 머신을 통해서만 이뤄진다. **신규 메트릭/사건이 결정 #2의 임계값을 초과하면 `/zoom-out`이 자동 트리거되어 모듈 지도 1매를 생성하고 인스턴스 파이프라인 문서에 첨부**한다. **결정 #9 wall-clock 패턴 누적 신호는 결정 #6 롤백 정책 + §0 (a) Hard ceiling 메커니즘과 cross-reference로 작동** (cost-ledger.jsonl + verifier-reports/<phase>.json 누적 데이터 입력).

---

## §8. 참조 인스턴스

| 워크플로우 | 인스턴스 파이프라인 문서 | ADR | 사용 스킬 호출 흔적 | 비고 |
|---|---|---|---|---|
| **Long Harness Autonomous Agent System** [v1.0 최초 버전] | `docs/long-harness/long-harness-implementation-pipeline.md` (작성 예정 — `docs/long-harness-system-design.md §10` verbatim "*[Step 1] docs/long-harness/long-harness-implementation-pipeline.md 인스턴스 문서 생성*") | **ADR-058** — Pipeline × Long-Horizon Autonomous Integration Protocol 6항 (`docs/long-harness-system-design.md §8` SOT) | (빌드 진행 시 누적 — `docs/long-harness-system-design.md §10` 시스템 빌드 순서 Phase 0~6 mattpocock 9종 호출 흔적) | 본 프로토콜 v1.0 첫 인스턴스. 4번째 축 (Long-Horizon Autonomous Layer) 상세 메커니즘 SOT = `docs/long-harness-system-design.md` (7대 설계 원칙·D1~D8·Run Manifest 정밀 구조·3-Tier Verification·Wall-Clock 적응 cache 전략·Pipeline × Long-Horizon Autonomous Integration 6항). 빌드 단계는 Pipeline (LLM-assisted human process), 자율 실행 단계는 Long-Horizon Autonomous 시스템 (자율 런타임) — `§10` verbatim 분리. |
| _기타 활성 인스턴스 없음_ | — | — | — | 추가 인스턴스화 시 §4 Step 5에 따라 1행 추가. 과거 인스턴스 W1(FVC-Profiler)은 ADR-056에서 deprecation 처리됨. |

새 인스턴스가 추가될 때마다 이 표에 1행 추가한다. **"사용 스킬 호출 흔적" 컬럼은 인스턴스가 누적될수록 어느 Phase가 실제로 비싸게 먹히는지를 보여주는 메타 데이터가 되며, 이후 본 프로토콜 자체에 대한 `/improve-codebase-architecture` 회수의 입력으로 쓰인다.**

---

## §9. 변경 이력

본 파일은 **v1.0 최초 버전**이다. 미래 변경 시점부터 본 표에 entry 추가.

| 일자 | 버전 | 변경 | 근거 ADR |
|---|---|---|---|
| 2026-05-12 | v1.0 | 최초 버전 신규 생성 — Long-Horizon Autonomous Layer (4번째 축) + Pipeline × Long-Horizon Autonomous Integration Protocol 6항. `implementation-pipeline.md` v1.2.0 base fork. 본 파일 결정 detail SOT = ADR-058. | ADR-058 |

---

## §10. 미래 결정 대기열 (사용자 별도 결정 위임 항목)

본 최초 버전 (v1.0) 작성 시 도출된 후속 결정 위임 항목. 사용자 결정 시점에 v1.1+ patch 진행.

### 시스템 메커니즘 보강 후보

- **Skill Snapshot 별도 자산 검토** — `mission-spec.md` 외부 자산으로 통합 후보 (Phase 2.5 Asset Curation에 흡수 vs 별도 immutable 객체)
- **Trust Boundary 메커니즘 검토** — Claude Max model 버전·외부 데이터 출처·로컬 실행 환경 hash. §0 (c) Pause/Resume의 hash check 메커니즘 확장 vs `mission-spec.md` 외부 검증 자산
- **Prototype 추가 측정 지표** — §1 Phase 3.5 prototype에서 측정할 추가 지표 (step 평균 시간·cache hit 비율·cache TTL 적응)
- **Prototype에서 Phase 1.5 카탈로그 3 시나리오 실측 검증** — Compaction Destruction·Sub-agent Isolation·Reward Hacking 을 wall-clock full run prototype에서 실제 검증. 시간 임계 (위험별 검증 시점) 결정
- **Free-부분 편차 KPI 측정 protocol 정밀화** — n (동일 입력 반복 횟수)·측정 시점 (4d 종료 1회 vs 매 step 누적)·측정 도구·통계 처리 (평균·표준편차·신뢰구간). 본 프로토콜 권장 protocol or 인스턴스화 가이드 발전

### 자율 실행 안전 보강 후보

- **자율 실행 시 mattpocock 추가 차단 2 layer 정책 명시** — (a) sub-agent context inject 자산 (§0 (b) Sub-agent inject 강제 범위 외 빌드 도구 메타데이터 inject 금지) (b) §1 Phase 3.7 build-time system prompt 4 항목 (cache 영역 5-15KB) 메타데이터 포함 여부 (c) §2 횡단 B `knowledge-index.jsonl` 빌드 도구 카탈로그 등재 여부

### §-1 정합성 후속

- **§-1 9종 vs `docs/long-harness-system-design.md §8` "mattpocock-skills 7종" 잔여 격차 검증** — `/caveman` 제거 후 §-1 = 9종, §8 객체 차이 표 verbatim = 7종. 잔여 격차 2종 ABSOLUTE ANCHOR 1 정합 평가 (정합 통과 시 9종 유지, 불통과 시 추가 제거)

### 일반화 후보

- **일반 사용자 voice reference document 일반화 protocol** — 본 파일 작성자 외 사용자가 본 프로토콜 적용 시 voice reference 자산을 해당 사용자 voice 자산으로 일반화. 본 프로토콜 현재 본 파일 작성자 인스턴스 (long-harness 빌드) 전용으로 작성자 voice 한정 명시 (자연 한정). 일반화 시점·protocol·인스턴스 가이드 발전

### ADR historical reference 확인

- **ADR-052~057 외부 ADR 저장소 위치 확인** — `implementation-pipeline.md` v1.1.1 verbatim "*ADR-056 본문은 외부 ADR 저장소로 이관*" 자산. ADR-052~057 외부 저장소 위치 사용자 확인. ADR-058은 `docs/adr/ADR-058-skillbased-pipeline-v130.md` 신규 위치 (본 파일 v1.0 결정).
