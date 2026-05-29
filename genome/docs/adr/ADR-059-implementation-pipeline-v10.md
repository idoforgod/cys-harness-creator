# ADR-059: implementation-pipeline.md v1.0 (최초 버전) — 워크플로우 구현 표준 프로세스 + Skill-driven SOT + 3축 통합

- **Date**: 2026-05-12
- **Status**: Accepted
- **Authors**: 박사님 (ysfuture) + javis master claude (Sub-agent)
- **W1 인스턴스 historical reference**: ADR-052·053 (W1 FVC-Profiler 인스턴스 — `implementation-pipeline.md` 일반화 source. ADR-056에서 deprecation 처리됨)
- **본 ADR SOT 위치**: `docs/adr/ADR-059-implementation-pipeline-v10.md` (본 파일 v1.0 결정 detail SOT)

---

## §1. Context

박사님 AgenticWorkflow 프로젝트에서 새 워크플로우를 구현할 때 적용되는 **범용 메타 빌드 프로세스** 필요성. LLM 코어 시스템·결정론 시스템·하이브리드 시스템 모두에 적용 가능한 표준 SOT.

기존 자산:
- W1 인스턴스 (FVC-Profiler) 빌드 경험 — `implementation-pipeline.md` 일반화 source
- mattpocock-skills 카탈로그 (`/setup-matt-pocock-skills` · `/grill-me` · `/grill-with-docs` · `/to-prd` · `/to-issues` · `/triage` · `/tdd` · `/diagnose` · `/improve-codebase-architecture` · `/zoom-out`)
- 박사님 `soul.md` §0 부모 게놈 (3 Absolute Criteria + Single-File SOT + 3-Phase Structure + 4-Layer QA + P1 Hallucination Prevention 등)

→ 워크플로우 구현 표준 프로세스 SOT 분리 결정.

---

## §2. ADR 3-조건 충족 검증

박사님 자산 `docs/protocols/implementation-pipeline.md §0` 셋째 축 + `§2 횡단 A` verbatim ADR 3-조건:

| 조건 | 충족 여부 | 근거 |
|---|---|---|
| Hard to reverse | O | 본 파일 SOT 분리 후 v0 회귀 시 모든 인스턴스 워크플로우 빌드 인프라 전면 폐기 의무 (가역 어려움) |
| Surprising without context | O | 3축 통합 (전통 SW + 하네스 엔지니어링 + Skill-driven SOT) + Phase 0~6 + mattpocock-skills binding = 박사님 자산 외 context 없이 이해 불가 |
| Real trade-off | O | 표준 메타 프로세스 SOT 의무화 (복잡도 증가) vs 인스턴스 워크플로우 품질·일관성·DNA 유전 보장 trade-off |

→ **3-조건 모두 충족. ADR 등록 의무**.

---

## §3. Decision

### 3.1. 본 파일 v1.0 최초 버전 신규 생성

`docs/protocols/implementation-pipeline.md` v1.0 (최초 버전) 신규 SOT. 박사님 AgenticWorkflow 프로젝트의 워크플로우 구현 표준 프로세스 메타 SOT.

### 3.2. 3축 결합

본 프로토콜 §0 설계 원칙 — 다음 3축의 결합:

| 축 | 정의 |
|---|---|
| **1. 전통 SW 엔지니어링 축** | 의도 → 인터페이스 → 명세 → 절차 → 구현 → 검증 (Phase 0~5) |
| **2. 하네스 엔지니어링 축** | LLM 코어 시스템 고유의 활동 통합 — Eval Suite, Prompt Engineering, Observability, Failure Mode, Cost-Latency, Safety, Continuous Learning |
| **3. 하네스 운용 축 (Skill-driven SOT)** | 모든 Phase의 도메인 어휘 = `CONTEXT.md`. 가역 어려운 결정 = `docs/adr/`. 작업 단위 = 이슈 트래커 `needs-triage` → `ready-for-agent` 상태 머신. ADR 등록 = 3-조건 (Hard to reverse · Surprising · Real trade-off) 모두 충족 시 |

### 3.3. 본 파일 v1.0 핵심 구조

| 위치 | 본 파일 결정 |
|---|---|
| §-1 Skill Toolkit | mattpocock-skills 9종 (`/setup-matt-pocock-skills`·`/grill-me`·`/grill-with-docs`·`/to-prd`·`/to-issues`·`/triage`·`/tdd`·`/diagnose`·`/improve-codebase-architecture`·`/zoom-out`) — 모든 Phase의 "사용자 승인" 게이트 묵시적 전제 |
| §0 설계 원칙 | 3축 결합 (전통 SW + 하네스 엔지니어링 + Skill-driven SOT) |
| §1 전체 단계 흐름 | Phase 0 (Intent Alignment) → 1 (Interface) → 1.5 (Contract Stress Test) → 2 (Spec — PRD·Spec·Test·Eval 4문서) → 2.5 (Build-Time Asset Curation) → 3 (workflow.md) → 3.5 (Dry-Run) → 3.7 (Prompt Engineering) → 4 (Implementation TDD a~f) → 5a (Validation + Failure Mode) → 5b (Acceptance) → 6 (Continuous Learning) |
| §2 횡단 활동 | A (Decision Log ADR) · B (Context Preservation hooks) · C (Adversarial Review @reviewer + @fact-checker + /improve-codebase-architecture) · D (Risk Register + no-seam findings) · E (Observability + /zoom-out 자동 트리거) |
| §3 Phase 적용 규칙 | 필수 / 조건부 / 선택적 분류 (Skill Setup 0차 필수 1회) |
| §4 인스턴스화 절차 | Step 0 (Skill Setup) → Step 1 (인스턴스 파이프라인 문서 생성) → Step 2 (ADR 등록 3-조건) → Step 3 (횡단 활동 활성화) → Step 4 (Phase 0 진입) → Step 5 (`/triage` 상태 이동 + Status 표 갱신) |
| §5 절대 기준 매핑 | 1 (품질 최우선) → 2 (단일 파일 SOT) → 3 (CCP) ↔ Phase별 보장 위치 |
| §6 DNA 유전 | 박사님 `soul.md` §0 부모 게놈 (3 Absolute Criteria + Single-File SOT + 3-Phase Structure + 4-Layer QA + P1/P2 + Safety Hooks + Adversarial Review + Decision Log + Context Preservation + Failure Mode Library + Observability + Domain Glossary `CONTEXT.md` + ADR 3-조건 + Tracer-bullet vertical slices + Triage state machine + Module/Interface/Depth/Seam 어휘 + Deletion test + post-mortem 3종 + no-seam findings 폐쇄 루프 + /zoom-out 운영 단계 자동 트리거 + 정기 아키텍처 회수) |
| §7 6+1+1대 결정 항목 | Phase 6 (Continuous Learning) 진입 전 사용자 결정 8 항목 (Privacy boundary · Drift threshold · 자동화 vs 수동 · 화이트리스트 · 모델 업그레이드 · 롤백 · 운영 도메인 어휘 진화 · 정기 아키텍처 회수 주기) |
| §8 참조 인스턴스 | 현재 활성 인스턴스 없음 (첫 인스턴스화 시 §4 Step 5에 따라 1행 추가) |
| §9 변경 이력 | 본 파일 v1.0 최초 버전 1행 |

### 3.4. Fork 자산

본 파일 v1.0 base로 fork된 별도 SOT:

- **`docs/protocols/skillbased-implementation-pipeline.md`** (v1.0, ADR-058) — Long-Horizon Autonomous Layer (4번째 축) 추가 변형. Long Harness 자율 실행 시스템 빌드 전용.

미래 다른 도메인 특화 fork 가능 (예: 결정론 전용·실시간 응답 전용 등).

---

## §4. Rationale

### 4.1. 박사님 ABSOLUTE ANCHOR 4 원칙 정합

| ABSOLUTE ANCHOR | 본 ADR 정합 결과 |
|---|---|
| 1. 최고의 품질 실현 (속도·토큰 무시) | O Phase 0~6 + 횡단 활동 A~E + DNA 유전 = 워크플로우 품질 다층 안전망. ADR 3-조건 + `CONTEXT.md` 인라인 갱신 = ADR 인플레이션 방지로 품질 SOT 무결성 |
| 2. 워크플로우 결과물 수준 적합 선택 | O 표준 메타 프로세스 SOT 의무화 = 모든 인스턴스 워크플로우 품질·일관성 보장 |
| 3. 로컬 실행 불변 | O 본 프로토콜 모든 자산 로컬 디스크 객체 (`docs/`·`docs/agents/`·`workflows/`·`CONTEXT.md`·`docs/adr/`) |
| 4. Claude Max 구독 (API·SDK 금지) | O 본 프로토콜 자체는 LLM 사용 정책 무관 (메타 프로세스). 인스턴스 워크플로우에서 LLM 사용 시 Claude Max 적용 (인스턴스별 명시) |

### 4.2. RLM (Recursive Language Models) 패턴 정합

박사님 `soul.md` §0 부모 게놈 verbatim RLM 4 패턴:
- **External Environment Objects**: `CONTEXT.md`·`docs/agents/*.md`·`docs/adr/`·`workflows/*/workflow.md`·`risk-register.md`·이슈 트래커 모두 외부 환경 객체
- **Variable Persistence**: `DECISION-LOG.md`·`CONTEXT.md` 해시·ADR 번호·`risk-register.md` 영속 저장
- **Code-based Filtering**: `/setup-matt-pocock-skills` 결정론 셋업·`/diagnose` 6-Phase deterministic 루프·`/improve-codebase-architecture` 1-pass deletion test
- **포인터 + 요약**: Hook 시스템 (`save_context.py` / `restore_context.py`) + `CONTEXT.md` 해시 동기화

→ RLM 4 패턴 모두 본 프로토콜에 깊이 적용 (§6 DNA 유전).

### 4.3. SOT 무결성

박사님 신규 원칙 "SOT + RLM 불변" 정합:
- 박사님 자산 SOT 다중 위치 (CONTEXT.md·docs/agents/*.md·docs/adr/·soul.md·MEMORY.md) verbatim 인용 + reference link 무손상
- SOT 분리 응집도 보호 — 도메인 어휘 (`CONTEXT.md`) ↔ 결정 (`docs/adr/`) ↔ 트리아지 라벨 (`docs/agents/triage-labels.md`) ↔ 이슈 트래커 (`docs/agents/issue-tracker.md`)

### 4.4. 박사님 통찰 "최초 버전" 정합

박사님 verbatim 통찰: "*현재가 최초 버전이다. 이전에 무엇을 했는지는 중요하지 않다. 이전 작업들은 현재의 최초 버전을 만드는 과정에 불과했다.*" + "*필요 없는 내용을 담고 있는 것은 품질 최우수와 맞지는 않는다.*"

→ 본 파일 = v1.0 최초 버전. 이전 v1.0.0·v1.1.0·v1.1.1·v1.2.0 진화 = 최초 버전 만드는 과정 = 본 ADR-059 detail로 응결 (§3.3 본 파일 v1.0 핵심 구조). 과정 자산 (§9 patch detail entry 4개·기존 ADR-054·055·056·057 의 자산화) 제거.

---

## §5. Related Files

### 5.1. 본 파일 (v1.0 SOT)

- `docs/protocols/implementation-pipeline.md` (v1.0 최초 버전 SOT)

### 5.2. Fork 자산

- `docs/protocols/skillbased-implementation-pipeline.md` (v1.0, ADR-058) — Long-Horizon Autonomous 변형 fork

### 5.3. mattpocock-skills SOT

- `docs/agents/issue-tracker.md` (이슈 트래커 워크플로우 SOT — `/setup-matt-pocock-skills` 1회 생성)
- `docs/agents/triage-labels.md` (트리아지 라벨 SOT — 5-state 머신)
- `docs/agents/domain.md` (도메인 문서 SOT)

### 5.4. 박사님 부모 게놈 SOT

- `soul.md §0` (3 Absolute Criteria + Single-File SOT + 3-Phase Structure + 4-Layer QA + P1 Hallucination Prevention + P2 Expert Delegation + Safety Hooks + Adversarial Review + Decision Log + Context Preservation + Failure Mode Library + Observability + RLM Pattern)
- `CLAUDE.md` (AgenticWorkflow 부모 작업 루트)
- `MEMORY.md` (박사님 auto-memory — `/Users/cys/.claude/projects/-Users-cys/memory/MEMORY.md`)

### 5.5. W1 인스턴스 historical reference

- ADR-052·053 — W1 FVC-Profiler 인스턴스 (`implementation-pipeline.md` 일반화 source, ADR-056 deprecation 처리)

---

## §6. 변경 이력

| 일자 | 변경 |
|---|---|
| 2026-05-12 | 본 ADR-059 작성 — `implementation-pipeline.md` v1.0 (최초 버전) 결정 detail SOT. 박사님 통찰 "최초 버전" 정합 양식 (과정 자산 제거 + 결과 자산만 응결). ABSOLUTE ANCHOR 4 정합 + RLM 패턴 정합 + SOT 무결성. ADR-054·055·056·057 historical → ADR-059 단일 결정 ADR 응결 (박사님 통찰 정합). |
