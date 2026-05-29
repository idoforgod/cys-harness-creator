# ADR-058: skillbased-implementation-pipeline.md v1.0 (최초 버전) — Long-Horizon Autonomous Layer + Pipeline × Long Harness Integration Protocol 6항

- **Date**: 2026-05-12
- **Status**: Accepted
- **Authors**: 박사님 (ysfuture) + javis master claude (Sub-agent)
- **Base reference**: `implementation-pipeline.md` v1.0 fork — ADR-059 (Base v1.0 — 워크플로우 구현 표준 프로세스 + Skill-driven SOT + 3축 통합)
- **본 ADR SOT 위치**: `docs/adr/ADR-058-skillbased-pipeline-v130.md` (본 파일 v1.0 결정 detail SOT)

---

## §1. Context

박사님 *long 하네스 '자율주행' AI 에이전트 workflow 시스템* (이하 *Long Harness*) 구축에 특화된 메타 빌드 프로세스 필요성. 박사님 자산 `docs/long-harness-system-design.md` (7대 설계 원칙 + D1~D8 + Run Manifest + 3-Tier Verification + Wall-Clock 적응 cache 전략) 와 메타 프로세스 결합 구조 정의 필요.

기존 `implementation-pipeline.md` v1.2.0 (ADR-057) — 3축 (전통 SW 엔지니어링·하네스 엔지니어링·Skill-driven SOT) 만으로는 다음 4 영역 부족:
- (a) Time Budget Management — 장기간 자율 실행 시 비용 폭발·시간 한계 부재
- (b) Drift Containment — 시간 누적 위험 3종 (Compaction Destruction·Sub-agent Isolation·Reward Hacking)
- (c) Pause/Resume Protocol — 장시간 task의 세션 복원·cache 적응
- (d) Skill Orchestration & Verification — 스킬 자산 조립 기반의 자율 실행 안전성

→ 4번째 축 (Long-Horizon Autonomous Layer / Time-Cumulative Operation Layer) 신설 + base fork SOT 분리 결정.

---

## §2. ADR 3-조건 충족 검증

박사님 자산 `docs/protocols/skillbased-implementation-pipeline.md §0` 셋째 축 + `§2 횡단 A` verbatim ADR 3-조건:

| 조건 | 충족 여부 | 근거 |
|---|---|---|
| Hard to reverse | O | 4번째 축 도입 + 본 파일 SOT 분리 후 v1.2.0 회귀 시 Long Harness 시스템 빌드 인프라 전면 폐기 의무 (가역 어려움) |
| Surprising without context | O | Long-Horizon Autonomous Layer = 기존 3축 (전통 SW·하네스·Skill SOT) 와 다른 패러다임 (시간 누적 layer). 박사님 자산 외 context 없이 이해 불가 |
| Real trade-off | O | Pipeline (LLM-assisted human process, 빌드 단계) ↔ Long Harness (자율 런타임, 실행 단계) layer 분리 + SOT 분리 + 복잡도 증가 vs 시간 누적 위험 차단 trade-off |

→ **3-조건 모두 충족. ADR 등록 의무**.

---

## §3. Decision

### 3.1. 본 파일 v1.0 최초 버전 신규 생성

`docs/protocols/implementation-pipeline.md` v1.2.0 base fork → `docs/protocols/skillbased-implementation-pipeline.md` v1.0 (최초 버전) 신규 SOT 분리. Long-Horizon Autonomous 시스템 빌드 전용 변형 SOT.

### 3.2. 4번째 축 (Long-Horizon Autonomous Layer) 도입

본 프로토콜 §0 셋째 축 (Skill-driven SOT) 다음에 4번째 축 신설. 4 sub-element:

| Sub-element | 정의 |
|---|---|
| **(a) Time Budget Management** | `mission-spec.md` 7번째 항목 Wall-Clock Budget immutable. target × 1.5 hard ceiling 초과 시 자동 pause + 박사님 alert |
| **(b) Drift Containment** | 시간 누적 위험 3종 (Compaction Destruction·Sub-agent Isolation·Reward Hacking) 구조적 차단 — Mission Spec Immutability + Spec-vs-Output Diff @ every N step + Cost/Time Budget Gate + 3-tier verification (T1·T2·T3) + Sub-agent inject 강제 + 결정·추론 분리 |
| **(c) Pause/Resume Protocol** | 매 phase 종료 시 `_handoff_latest.md` 기록. Resume 시 `verifier-reports/<phase>.json` 먼저 읽고 pass 확인 후 진입. Wall-clock 적응 cache 전략 (≤6h: ephemeral / 6~24h: 1h persistent 병행 / >24h: 축소 / >7d: 비의존) |
| **(d) Skill Orchestration & Verification** | 3-Layer 수정 진단 protocol (스킬·Orchestrator routing·Verifier criteria 외 수정 금지) + 스킬 자산 leverage (`skills_snapshot` freeze) + plan.md Gate 0 Strict (DAG depth ≤ f(wall-clock)) + Mission Spec 7항목 Schema |

적용 조건 (본 프로토콜 §3 4번째 축 적용 조건 verbatim):
1. Wall-Clock Budget > 4시간
2. 자율 실행 (사용자 입력 없이 LLM 자체 진행)
3. LLM 코어 시스템 (LLM 핵심 추론 담당)

3 조건 모두 충족 시 필수. 그 외 시스템 (짧은 batch·결정론·실시간 응답) 은 N/A 처리 (ADR 사유 등재).

### 3.3. Pipeline × Long Harness Integration Protocol 6항

`docs/long-harness-system-design.md §8` SOT + 본 프로토콜 §1·§2 정합 결합:

| # | 항목 | SOT 위치 |
|---|---|---|
| **1** | 객체 차이 — System Build vs Runtime Execution | `docs/long-harness-system-design.md §8` "객체 차이" 표 verbatim |
| **2** | 자산 매핑 | `docs/long-harness-system-design.md §8` "자산 매핑" 표 verbatim |
| **3** | /diagnose 6-Phase ↔ T1/T2/T3 매핑 | `docs/long-harness-system-design.md §8` 매핑 표 verbatim |
| **4** | 환류 채널 | `docs/long-harness-system-design.md §8` "환류 채널" verbatim — (1) task-level → Pipeline 5a (T1 fail 패턴 누적 시 risk-register + no-seam findings → 다음 Pipeline 4f /improve-codebase-architecture 입력) (2) multi-task → Pipeline §8 + §7 결정 #8 (cost-ledger.jsonl 누적치 정기 회수 cross-reference). 자동 환류는 박사님 명시 승인 후에만 (closed-loop drift 방지) |
| **5** | 빌드 단계 vs 자율 실행 단계 SOT 분리 — Phase 5a /diagnose 6-Phase 강제 | 본 프로토콜 §1 Phase 5a verbatim — Phase 5a `/diagnose` 6-Phase 강제는 **빌드 단계 한정**. 자율 실행 단계 처리는 `docs/long-harness-system-design.md §8` 참조 (Phase 1~4 자율 자동, Phase 5~6 박사님 spot-check). RLM 패턴 정합 — 자율 실행 단계 즉시 fix 금지 + `spot_check_queue` 외부 객체 등재 |
| **6** | 빌드 단계 vs 자율 실행 단계 SOT 분리 — @reviewer/@fact-checker | 본 프로토콜 §2 횡단 C verbatim — 자율 실행 단계: @reviewer + @fact-checker 페르소나는 T2 LLM verifier prompt에 통합. 빌드 단계 phase 게이트 적대적 검토는 자율 실행 T2 통합과 별도 작동 (SOT 분리). 빌드 단계 페르소나·도구·통과 기준 SOT 5 layer — `reviewer.md`·`fact-checker.md` frontmatter + `AGENTS-ko-backup.md §5.5` 도구 분리 + `validate_review.py` P1 결정론적 통과 기준 + `Review:` 필드 트리거 + Generator-Critic·pACS F/C/L·claim-by-claim |

### 3.4. 본 파일 v1.0 핵심 구조

| 위치 | 본 파일 결정 |
|---|---|
| §-1 Skill Toolkit | mattpocock-skills 9종 (`/setup-matt-pocock-skills`·`/grill-me`·`/grill-with-docs`·`/to-prd`·`/to-issues`·`/triage`·`/tdd`·`/diagnose`·`/improve-codebase-architecture`·`/zoom-out`) + Long Harness 자율 실행 단계 적용 제약 + 빌드 도구 카탈로그 정합 |
| §0 설계 원칙 | 4축 결합 (전통 SW + 하네스 엔지니어링 + Skill-driven SOT + Long-Horizon Autonomous) + 4번째 축 4 sub-element |
| §1 전체 단계 흐름 | Phase 0~6 + 4번째 축 sub-element 발현 위치 (Phase 0 mission-spec 7항목 · Phase 1.5 3대 위험 카탈로그 · Phase 2-Eval T1/T2/T3 3-tier · Phase 2.5 voice reference · Phase 3 plan.md DAG depth Gate · Phase 3.5 prototype · Phase 3.7 cache 영역 · Phase 4d Free-부분 편차 KPI · Phase 5a 빌드 단계 한정) |
| §2 횡단 활동 | A (Decision Log) · B (Context Preservation + knowledge-index.jsonl + task 단위 Resume) · C (Adversarial Review + 빌드 단계 페르소나 SOT 5 layer + 자율 실행 T2 통합) · D (Risk Register) · E (Observability + cost-ledger.jsonl) |
| §3 Phase 적용 규칙 | 4번째 축 적용 조건 sub-section (3 조건 + N/A 절차) |
| §4 인스턴스화 절차 | Step 0~5 + Long Harness 빌드 환경 vs 자율 실행 환경 /triage 5-state 매핑 |
| §5 절대 기준 매핑 | 박사님 ABSOLUTE ANCHOR 4 ↔ Pipeline 절대 기준 1·2·3 정합 검증 표 |
| §6 DNA 유전 | RLM Pattern + Long-Horizon Autonomous 5 게놈 (Wall-Clock Budget·plan.md DAG depth gate·T1/T2/T3 3-tier·Cache wall-clock 적응·ADR Integration Protocol 6항) |
| §7 6+1+1+1대 결정 항목 | 9 결정 항목 (Wall-Clock Budget 갱신 정책 포함) |
| §8 인스턴스 레지스트리 | Long Harness Autonomous Agent System 첫 인스턴스 |
| §9 변경 이력 | 본 파일 v1.0 최초 버전 1행 |
| §10 미래 결정 대기열 | 박사님 별도 결정 위임 항목 9개 (Skill Snapshot·Trust Boundary·Prototype 측정 지표·시나리오 실측·KPI protocol·mattpocock 추가 차단·9종 vs 7종 격차·voice 일반화·ADR-052~057 위치) |

---

## §4. Rationale

### 4.1. 박사님 ABSOLUTE ANCHOR 4 원칙 정합

| ABSOLUTE ANCHOR | 본 ADR 정합 결과 |
|---|---|
| 1. 최고의 품질 실현 (속도·토큰 무시) | O 4번째 축 4 sub-element + 3-tier verification + Wall-Clock hard ceiling + 3-Layer 수정 진단 protocol = 장기간 자율 시스템 품질 다층 안전망 |
| 2. 워크플로우 결과물 수준 적합 선택 | O Long Harness 시스템 = 박사님 미래학자 본업 (foresight-* 카탈로그) 자율 실행 필요성. 본 파일 SOT 분리로 박사님 결과물 정밀화 |
| 3. 로컬 실행 불변 | O 4번째 축 4 sub-element 모두 로컬 자산 (mission-spec·plan·skills_snapshot·Run Manifest `_runs/<task-id>/` 모두 로컬 디스크 객체) |
| 4. Claude Max 구독 (API·SDK 금지) | O §1 Phase 3.7 verbatim "*cache_control: ephemeral, 5-15KB — Claude Max 환경 자동 적용*" Claude Max 환경 명시 |

### 4.2. RLM (Recursive Language Models) 패턴 정합

박사님 `soul.md` §0 부모 게놈 verbatim RLM 4 패턴 (MIT CSAIL 논문 기반):
- **External Environment Objects**: mission-spec.md·plan.md·skills_snapshot·Run Manifest·spot_check_queue·knowledge-index.jsonl·voice reference document·plan.md dependency graph·`docs/agents/*.md` 모두 외부 환경 객체
- **Variable Persistence**: decisions.log·reasoning_trace.log·cost-ledger.jsonl·_handoff_latest.md·verifier-reports/·risk-register.md 영속 저장
- **Code-based Filtering**: T1 외부 python deterministic + python orchestrator (stateless dispatch loop) + SHA256 hash check + decisions.log python 결정론 + skills_snapshot freeze 자연 배제 + validate_review.py P1 검증
- **포인터 + 요약**: _handoff_latest.md + verifier-reports/<phase>.json + save_context.py/restore_context.py + 동적 RLM 쿼리 힌트 (`extract_path_tags()`)

→ RLM 4 패턴 모두 본 프로토콜에 깊이 적용. §6 DNA 유전 RLM Pattern 행 + Long-Horizon Autonomous 5 게놈 행으로 부모 게놈 완전성 확보.

### 4.3. SOT 무결성

박사님 신규 원칙 "SOT + RLM 불변" 정합:
- 박사님 자산 SOT 다중 위치 (skillbased-implementation-pipeline.md·docs/long-harness-system-design.md·.claude/agents/reviewer.md·fact-checker.md·validate_review.py·AGENTS-ko-backup.md·README.md·DECISION-LOG.md) verbatim 인용 + reference link 모두 무손상
- SOT 분리 응집도 보호 — 빌드 단계 ↔ 자율 실행 단계 (Phase 5a·§2 횡단 C·§4 Step 5) / 도구 카탈로그 ↔ 빌드 산출물 (§-1 ↔ §10·§5 D1~D8·§8)

### 4.4. 박사님 통찰 "최초 버전" 정합

박사님 verbatim 통찰: "*현재가 최초 버전이다. 이전에 무엇을 했는지는 중요하지 않다. 이전 작업들은 현재의 최초 버전을 만드는 과정에 불과했다.*" + "*필요 없는 내용을 담고 있는 것은 품질 최우수와 맞지는 않는다.*"

→ 본 파일 = v1.0 최초 버전. patch 진행 과정 (A1~A11·A8.5·B1~B10·C1~C5·D1~D3·S1) = 최초 버전 만드는 과정 = 본 ADR-058 detail로 응결 (위 §3 본 파일 v1.0 핵심 구조 + 4번째 축 + 6항). 과정 자산 (§9 patch detail entry·§10 [x] 완료 표) 제거.

---

## §5. Related Files

### 5.1. 본 파일 (v1.0 SOT)

- `docs/protocols/skillbased-implementation-pipeline.md` (v1.0 최초 버전 SOT)

### 5.2. 4번째 축 상세 메커니즘 SOT

- `/Users/cys/Desktop/CYSjavis/cys-claude-foresight-skills/docs/long-harness-system-design.md` (7대 설계 원칙·D1~D8·Run Manifest 정밀 구조·3-Tier Verification·Wall-Clock 적응 cache 전략·Pipeline × Long Harness Integration 6항)

### 5.3. 빌드 단계 적대적 검토 페르소나·도구·통과 기준 SOT

- `AgenticWorkflow/.claude/agents/reviewer.md` (페르소나 자격 frontmatter)
- `AgenticWorkflow/.claude/agents/fact-checker.md` (페르소나 자격 frontmatter)
- `AgenticWorkflow/.claude/hooks/scripts/validate_review.py` (P1 결정론적 통과 기준)
- `AgenticWorkflow/AGENTS-ko-backup.md §5.5` (Adversarial Review Enhanced L2 + Generator-Critic + P2 도구 분리)
- `AgenticWorkflow/README.md` (페르소나 명세 + pACS F/C/L + claim-by-claim)

### 5.4. 이슈 트래커 + /triage 5-state SOT

- `docs/agents/issue-tracker.md` (이슈 트래커 워크플로우 SOT — `/setup-matt-pocock-skills` 1회 생성)
- `docs/agents/triage-labels.md` (트리아지 라벨 SOT — 5-state 머신 `needs-triage` → `needs-info` / `ready-for-agent` / `ready-for-human` / `wontfix`)
- `docs/agents/domain.md` (도메인 문서 SOT)

### 5.5. 박사님 부모 게놈 SOT

- `soul.md §0` (3 Absolute Criteria + Single-File SOT + 3-Phase Structure + 4-Layer QA + P1 Hallucination Prevention + P2 Expert Delegation + Safety Hooks + Adversarial Review + Decision Log + Context Preservation + Failure Mode Library + Observability + RLM Pattern)
- `CLAUDE.md` (AgenticWorkflow 부모 작업 루트)
- `MEMORY.md` (박사님 auto-memory — `/Users/cys/.claude/projects/-Users-cys/memory/MEMORY.md`)

### 5.6. Base reference

- `docs/protocols/implementation-pipeline.md` (v1.0 base, ADR-059) — 본 파일 fork 출처

---

## §6. 후속 결정 위임 항목 (박사님 별도 결정 필요)

본 ADR-058 적용 후 박사님 별도 결정 위임 항목 = 본 파일 `§10 미래 결정 대기열` 참조.

총 9 항목:
- Skill Snapshot 별도 자산 검토
- Trust Boundary 메커니즘 검토
- Prototype 추가 측정 지표
- Prototype에서 Phase 1.5 카탈로그 3 시나리오 실측 검증
- Free-부분 편차 KPI 측정 protocol 정밀화
- 자율 실행 시 mattpocock 추가 차단 2 layer
- §-1 9종 vs §8 7종 잔여 격차 검증
- 일반 사용자 voice reference document 일반화 protocol
- ADR-052~057 외부 ADR 저장소 위치 확인

---

## §7. 변경 이력

| 일자 | 변경 |
|---|---|
| 2026-05-12 | 본 ADR-058 작성 — `skillbased-implementation-pipeline.md` v1.0 (최초 버전) 결정 detail SOT. 박사님 통찰 "최초 버전" 정합 양식 (과정 자산 제거 + 결과 자산만 응결). ABSOLUTE ANCHOR 4 정합 + RLM 패턴 정합 + SOT 무결성. `docs/adr/` 폴더 신규 생성 (§0 셋째 축 verbatim 정합). |
