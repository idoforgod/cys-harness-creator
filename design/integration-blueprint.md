I have everything needed: real AWF assets (`translations/glossary.yaml`, `.claude/hooks/scripts/*` incl. the security trio and validate_* P1 suite, `soul.md` stem-cell genome, `prompt-runner/state_manager.py`) and the exact CYS seams (emitter injection points, validator check names, MANIFEST/evolve as the cross-run memory). Now I'll write the blueprint.

# cys-harness-creator × AgenticWorkflow — 통합 청사진 (INTEGRATION BLUEPRINT)

> 작성: 마스터 클로드 (원칙 설계자) · 2026-05-29
> 제약: **AgenticWorkflow는 READ-ONLY.** 모든 신규 산출물은 `/Users/cys/Desktop/CYSjavis/cys-harness-creator/`에 착지한다.
> 원칙: 개인용 도구 — **무게값을 하는 DNA만 이식**한다. AWF가 30개 프로젝트에서 검증한 자산은 *재구현하지 말고 복사*하되, prose는 머신체크 게이트로 승격한다.
> 근거 검증: CYS 실파일(`emit_workflow.py`, `validate_harness.py`, `graph.schema.json`, `design/_raw/06_MANIFEST*.md`, `design/strategy.md`) + AWF 실자산(`soul.md`, `translations/glossary.yaml`, `.claude/hooks/scripts/{security 3종, validate_* P1 14종}`, `prompt-runner/state_manager.py`) 직접 확인.

---

## 핵심 판단 (먼저 읽을 것)

AWF DNA를 CYS에 넣는 방법은 **세 가지뿐**이고, 헷갈리면 청사진 전체가 무너진다:

| 착지 위치 | 의미 | 무게 기준 |
|---|---|---|
| **graft-into-factory** | cys-harness-creator 자신의 코드(`emit_workflow.py`/`validate_harness.py`/`lib/`)에 들어가 *모든* 생성 하네스에 영향 | 팩토리가 직접 강제·검증할 수 있을 때만 |
| **graft-into-generated** | 팩토리가 *emit하는* 템플릿이 되어 자식 하네스의 `.claude/`·`.harness/`에 복사됨 | 자식이 런타임에 실제로 쓸 때만 |
| **template-only** | `references/`에 문서로만 존재, emit 안 됨 (구현자가 필요시 참조) | "있으면 좋지만 강제 불가"일 때 |
| **skip** | 개인용·플랫폼 제약·과설계로 제외 | 무게값 못 함 |

**가장 중요한 한 줄:** AWF의 "Stem Cell Genome"과 CYS의 "graph.json 계약"은 **같은 사상의 두 표현**이다. AWF는 그것을 *prose(soul.md)*로, CYS는 *assertion(validate_harness.py)*으로 강제한다. 통합의 본질 = **AWF의 영혼(soul)을 CYS의 검증기가 강제하는 게이트로 변환**하는 것. 이미 strategy.md가 "rules-as-essays → rules-as-assertions"로 명문화했다 — 이 청사진은 그 원칙을 DNA 6클러스터에 일괄 적용한다.

---

## 1. DNA 인벤토리 & 등급

> 등급 기준: crown-jewel/high만 결정 대상으로 올린다. medium/low는 §1 말미에 일괄 처리. CYS가 **이미 가진** DNA(Mode A 런타임, 11 정적검증, 토포소트, MANIFEST/evolve, lift/h2h, 모델티어)는 "이미 보유 — 이식 불요"로 표기.

### 1-A. 이미 CYS가 보유 (이식 불요, 재확인만)

| DNA 요소 | CYS 현존 자산 | 조치 |
|---|---|---|
| Mode A Deterministic Runtime | `emit_workflow.py` → Workflow .js | 보유. AWF prompt-runner state-machine과 **융합**(§4 충돌해소) |
| Static Validation (11 checks) | `validate_harness.py` | 보유. AWF W1-W8/P1 어휘로 **확장** |
| Topological Sort | `lib/toposort.py` | 보유 |
| Workflow Tool / Graph→JS Compiler | `emit_workflow.py` | 보유 |
| 모델 티어 거버넌스 | `model-tier-policy.js` + validator V1/V2/V3 | 보유. AWF "Quality>Everything"이 이미 인코딩됨 |
| Delivery Readiness Gate | `warrant.py` (Phase -1 + cost-band) | 보유 |
| lift 게이트 / H2H | `lift_gate.py` + `h2h_aggregate.py` + `h2h_suite.workflow.js` | 보유 |
| Harness Metadata SoT | `constants.json` | 보유 |

### 1-B. crown-jewel & high DNA — 이식 결정표

| DNA 요소 (출처 클러스터) | 등급 | 무엇인가 (한 줄) | 이식 결정 | 착지 |
|---|---|---|---|---|
| **Stem Cell Genome / DNA Inheritance** (Soul, Agents) | 👑 | 자식이 부모 게놈을 *embed*(참조 아님) | **graft-into-factory + generated** | emit이 `harness.md`에 `Inherited DNA:` 섹션 주입 + validator W1-W8 강제 |
| **Quality > SOT > CCP 절대기준** (Soul, Docs) | 👑 | 품질 최우선·단일쓰기·파급분석 헌법 | **graft-into-factory** | `constants.json`에 AC1/AC2/AC3 + `CONSTITUTION.md`(불변) + validator AC-2 check |
| **Single-File SOT + Hierarchical Memory** (Soul) | 👑 | state는 단일 파일, 쓰기는 오케스트레이터만 | **부분 graft + 재조정** | **CYS는 이미 MANIFEST가 SOT.** AWF state.yaml 패턴은 *generated* `state.json`으로 (§4 canonical 결정) |
| **Sub-agent Specialization (role/tier/tool-gate)** (Agents) | 👑 | 도구게이트 샌드박스 + 최소권한 + RLM 외부메모리 | **graft-into-generated** | emit이 `.claude/agents/{role}.md` frontmatter(model/tools/maxTurns) 생성 + validator least-privilege check |
| **Adversarial Review (Generator-Critic)** (Soul, Agents) | 👑 | 독립 reviewer/fact-checker 이중검증 + Pre-mortem | **이미 보유 + 강화** | `reflect-then-revise`/`producer-reviewer`/`debate-with-judge`가 이미 메커니즘. AWF Pre-mortem 프롬프트만 prompt-inline |
| **pACS (자기신뢰 min-score)** (Agents) | 👑 | 3차원(F/C/L) 자기평가 + min-score 약한고리 차단 | **template-only → opt-in graft (M1)** | `references/pacs-scoring.md` + opt-in `pacs` 노드플래그. 기본 off (개인용 무게) |
| **State Machine Pattern** (prompt-runner) | 👑 | 명시적 상태전이 모델 (if-else 대체) | **graft-into-factory (개념만)** | emit 토폴로지를 명시 상태노드로. **단 런타임 1개 유지** (§4) |
| **Atomic Write + Backup (StateManager)** (prompt-runner) | 👑 | temp→rename+flock 충돌안전 쓰기 | **graft-into-factory** | `lib/atomic_write.py` 신규 — MANIFEST/lock/snapshot 모든 쓰기에 적용 |
| **Unified Single-File SOT + Audit Log** (prompt-runner) | 👑 | audit_log를 state에 병합, 단일 원자쓰기 | **graft-into-factory** | MANIFEST에 `audit_log[]` 필드 추가 (별도파일 금지) |
| **Hook-Based Context Preservation (ADR-012)** (State) | 👑 | /clear·compaction 생존, 코드기반 스냅샷 | **graft-into-generated (MVP)** | emit이 SessionStart/Stop hook만 주입 (PreCompact/SessionEnd는 M2). 복잡도 부채 회피 |
| **Knowledge Archive (ADR-013)** (State) | 👑 | 세션간 학습, grep 검색 가능 | **부분 graft → MANIFEST 재사용** | **별도 knowledge-index.jsonl 만들지 말고** MANIFEST evolve ledger를 1차 메모리로. 에러패턴만 추가 (§2-M2) |
| **4-Layer Quality Gate (L0→L2)** (다수) | 👑 | 직교 검증 게이트 4층 | **부분 graft — CYS 게이트로 매핑** | L0=validator(이미 있음), L1=schema(agent({schema}) 이미 있음), L1.5=pACS(opt-in), L2=Review(이미 메커니즘). *신규 게이트 추가 아니라 명명·문서화* |
| **i18n Glossary + English-First** (Agents, Docs) | high | glossary.yaml RLM + 실행영어/출력이중 | **graft (자산 복사) + template** | AWF `translations/glossary.yaml` 복사·확장 + emit이 자식에 glossary 스캐폴드 |
| **Security Hardening 3종** (State, Docs) | high | block_destructive / secret_filter / sensitive_file_guard | **graft-into-generated (자산 복사)** | AWF 3 스크립트 *그대로 복사* → emit이 자식 `.claude/hooks/`에 + settings.json 등록 |
| **Decision Log / ADR** (다수) | high | 거버넌스 단일기록, 자동승인 감사 | **부분 graft → MANIFEST audit_log 재사용** | MANIFEST audit_log가 ADR 역할. 별도 DECISION-LOG는 *factory 자신*만 보유 (자식엔 emit 안 함 — 개인용 무게) |
| **Sub-agent Categorization + Fork Isolation** (Agents, State) | high | translator→always_fork 등 fork 규칙 | **graft-into-factory** | emit에 CATEGORIZATION dict + validator가 미등록 agent 거부 |
| **P1 Deterministic Validation Suite (14)** (Docs, State) | high | "must-be-true" = prompt 아닌 코드 | **부분 graft (자산 복사, 선별)** | `validate_review.py`/`validate_translation.py`만 복사 (CYS validator의 라이브러리로). 나머지 12는 template-only |
| **Anti-Skip Guard** (Agents) | high | 산출물 존재 결정론 검증 | **이미 보유 + 명명** | MANIFEST `content_hash`가 곧 anti-skip(파일 없으면 dirty). validator에 명시 check 추가 |
| **Fork-Based Multi-Perspective Research** (Prompt Library) | high | 2-4 대립 페르소나 → 충돌맵 → 수렴 | **이미 보유** | `debate-with-judge` + dispatch 토폴로지가 동치. template로 페르소나 가이드만 |
| **Orchestrator Role (SOT write authority)** (Agents) | high | 메인 러너=오케스트레이터, 쓰기 단독권 | **이미 보유 + 명문화** | Mode A는 in-session 러너가 곧 오케스트레이터. write-lock hook이 강제 |
| **3-Stage Constraint (R→P→I)** (Soul) | high | Research/Planning/Implementation 필수 | **template-only** | 도메인마다 3단계 강제는 과설계 위험. `references/`에 권장 스캐폴드만 (CYS 토폴로지가 더 일반적) |

### 1-C. medium/low — 일괄 처리

- **template-only (references/ 문서로만):** Domain Knowledge Structure(DKS), ULW Mode, Theory Grounding/RLM Paradigm 문서, Hub-and-Spoke 문서, Proportionality Rule, Error Taxonomy 12패턴, Translator sub-agent, Slash Commands 아키텍처, Team Protocol 상세, Pre-mortem 체크리스트, IMMORTAL 압축 로직.
  → 이유: 개인용 도구에 강제하면 생성비용·복잡도만 늘고 무게값 못 함. *문서로 두고 필요한 하네스만 채택*.
- **skip (제외):** A2A agent card, 직접 OTel-emit, release-please/changesets/commitlint, JA 문서 풀세트(parity 최소만, §2), per-harness ADR 복제, Knowledge Archive 풀 131줄 상태머신(9 hook event), Glossary post-execution merge hook, ULW I-1/I-2/I-3 컴플라이언스 가드, IMMORTAL 7단계 하드절단.
  → 이유: strategy.md D-8 "개인/내부용 → OSS 거버넌스 툴체인 전면 제거" 결정 + Cautions의 복잡도 부채 경고와 정합.

---

## 2. Part 1 — 원본 동등화 (Parity vs idoforgod/harness)

> 갭 4개: 패키징/배포 · i18n · 사전제작 하네스 폭(harness-100=1808md vs CYS 3예제) · 거버넌스 성숙도.
> **핵심 전략: 갭을 OSS 규모로 메우지 않는다.** strategy.md가 "개인/내부용"을 확정했으므로 parity는 "원본이 가진 *능력*을 CYS가 *증명*"하는 선까지만. AWF의 검증된 i18n/거버넌스 자산을 *재사용*해 가속한다.

### 2-1. 패키징/배포 (원본: plugin.json + marketplace + /plugin install)

- **결정: 부분 parity만.** 개인용이므로 marketplace는 skip. 단 "한 줄 설치"는 가치 있음.
- **산출물:** `cys-harness-creator/plugin.json`(스킬+커맨드 매니페스트, 로컬 설치용) + `install.sh`(심볼릭 링크 또는 `~/.claude/skills/`로 복사).
- **AWF DNA 가속:** 없음(CYS 고유). 단 AWF `.claude/settings.json` hook 등록 패턴을 install이 재사용.
- **무게 절감:** marketplace.json/privacy.html/index.html 랜딩(1393줄) **전부 skip**.

### 2-2. i18n (원본: EN/KO/JA 3종)

- **결정: EN/KO만. JA skip.** (개인용·한국 개발자 — JA는 무게값 못 함.)
- **산출물:**
  1. `translations/glossary.yaml` — **AWF `translations/glossary.yaml` 복사 후 CYS 용어 추가**(graph.json, emit_workflow, warrant, lift_gate, MANIFEST, evolve, decision_mechanism).
  2. `README.md`(EN, 이미 존재) + `README.ko.md` — *단일 SOT에서 생성*하지 말고 수동 유지(개인용, 2개뿐).
  3. emit이 자식 하네스에 glossary 스캐폴드 주입 (Translation 필드 enable 시만).
- **AWF DNA 가속:** glossary.yaml 통째 재사용 + `validate_translation.py`를 CYS validator 라이브러리로 복사(T-check). English-First 실행 규칙은 emit 프롬프트가 영어 강제 — *이미 emit 프롬프트가 영어*이므로 거의 무료.

### 2-3. 사전제작 하네스 폭 (원본: 100도메인 1808md / CYS: 3예제)

- **결정: 폭으로 경쟁하지 않는다 — 깊이로.** strategy.md D-8: M2에서 **기존 ~30 AgenticWorkflow를 `harness import`로 역생성**. 이게 CYS의 "harness-100" 대응이다.
- **산출물 (단계적):**
  1. (M0 현존) 3 예제 — deep-research(LIVE-PROVEN)/ticket-triage/design-decision.
  2. (M1) +2~3 도메인 (헤드투헤드 3도메인 요건과 일치).
  3. (M2) `harness import <path>` 어댑터 → 30개 AWF 프로젝트 batch 역생성 → 각각 graph.json+MANIFEST+검증기 편입.
- **AWF DNA 가속:** **AWF 30개 프로젝트 자체가 import 소스.** 1808md를 손으로 쓰는 대신, AWF가 이미 만든 실전 워크플로우를 graph.json으로 *증류*. 원본은 md 1808개가 검증 안 됨(W2); CYS는 import한 30개가 *전부 validate 통과*해야 함 — 폭은 작아도 **검증된 폭**.

### 2-4. 거버넌스 성숙도 (원본: ADR 문화 but CI 실재 안 함=W2)

- **결정: 원본의 *치명적 약점*(advisory rules, 실재 안 하는 CI)을 그대로 답습하지 않는다.** parity = "원본이 *주장*한 거버넌스를 CYS는 *강제*".
- **산출물:**
  1. `CONSTITUTION.md` — AC1/AC2/AC3(불변). AWF soul.md §0 게놈을 CYS 헌법으로 압축.
  2. `validate_harness.py` 확장 — W1-W8 구조검증(원본이 advisory로 둔 것을 assert).
  3. MANIFEST `audit_log[]` — 자동승인·결정 기록(ADR의 머신 버전).
- **AWF DNA 가속:** soul.md(영혼)와 DECISION-LOG.md(ADR 문화)를 *압축 인용*. 원본·AWF 양쪽의 "정직성"(미백업 수치 경고, 자기적용 dogfooding) 자세를 계승하되 **prose 약속 → 게이트**로 승격.

**Part 1 한 줄 요약:** parity는 "원본의 능력 매트릭스를 따라잡되, 원본의 약점(W1-W14)은 답습 안 함". AWF의 glossary/security/validate 자산을 복사해 i18n·거버넌스를 *공짜로* 메우고, 폭은 "검증된 30개 import"로 깊이 전환.

---

## 3. Part 2 — DNA 이식 통합 아키텍처

> 목표: cys-harness-creator가 **CYS rigor(검증기/런타임/비용/측정) + AWF DNA(영혼/상태머신/스냅샷/hook/결정로그/프롬프트라이브러리/에이전트메모리)를 둘 다 운반하는 하네스를 emit하는 팩토리**가 된다.

### 3-1. 전체 그림 — "주입 가능한 게놈" 모델

```
┌─────────────────────────── cys-harness-creator (FACTORY) ───────────────────────────┐
│                                                                                       │
│  graph.json (계약 스파인)  ──┐                                                          │
│  CONSTITUTION.md (AC1-3)  ──┤                                                          │
│  templates/ (주입 게놈)    ──┼──▶ emit_workflow.py ──▶ <domain-harness>/               │
│    ├ inherited-dna.md.tmpl  │      (구조 번역기 +              ├ .harness/workflow.js   │
│    ├ agent.md.tmpl          │       게놈 주입기)               ├ .harness/graph.json    │
│    ├ settings.json.tmpl     │                                  ├ .harness/MANIFEST.json │
│    ├ hooks/{security 3종}   │                                  ├ .harness/harness.lock  │
│    └ glossary.yaml          │                                  ├ .claude/agents/*.md    │
│  validate_harness.py ───────┴──▶ (빌드게이트: W1-W8+AC+11 check) ├ .claude/settings.json │
│  lib/atomic_write.py (신규, AWF StateManager 이식)              ├ .claude/hooks/*       │
│  warrant.py / lift_gate.py / h2h (측정)                        └ harness.md (게놈 가시화)│
└───────────────────────────────────────────────────────────────────────────────────┘
```

핵심: **AWF DNA는 "팩토리가 자식에 주입하는 템플릿"이 되거나, "팩토리 자신의 코드"가 된다.** prose로 남기지 않는다.

### 3-2. 재사용 TEMPLATE이 되는 DNA (emit이 주입)

`cys-harness-creator/templates/`(신규 디렉터리)에 착지, emit이 자식에 복사:

| 템플릿 파일 | 출처 AWF DNA | emit 주입 방식 |
|---|---|---|
| `inherited-dna.md.tmpl` | Stem Cell Genome / DNA Inheritance | emit이 `harness.md`에 `Inherited DNA:`(부모가 넘긴 것) + `Gene Expression:`(도메인별 발현) 섹션 채움. validator W1이 존재 강제 |
| `agent.md.tmpl` | Sub-agent Specialization | node.agent마다 frontmatter(name/description/model/tools/maxTurns/memory:project) 생성. 최소권한 tools |
| `settings.json.tmpl` | Hook Architecture (MVP) | SessionStart(restore)+Stop(snapshot) hook만 등록. write_lock.sh + stamp_node.sh도 등록 |
| `hooks/block_destructive_commands.py` | Security 3종 | **AWF 자산 그대로 복사**, emit이 자식 `.claude/hooks/`에 배치 |
| `hooks/output_secret_filter.py` | Security 3종 | 동상 |
| `hooks/security_sensitive_file_guard.py` | Security 3종 | 동상 |
| `glossary.yaml` | i18n Glossary | Translation enable 노드 있을 때만 자식에 스캐폴드 |

### 3-3. prompt-runner state-machine ↔ emit_workflow.py + Workflow 런타임 (융합, 중복 금지)

> **이것이 청사진의 가장 어려운 결정이다. 런타임은 단 하나만 유지한다.**

**사실 정리(코드 확인):**
- CYS `emit_workflow.py`는 graph.json을 받아 **명시적 토폴로지 함수**(`_topology`: pipeline/dispatch/producer-reviewer)로 Workflow .js를 emit. budget guard(`ensure()`)·resume·schema 내장.
- AWF `prompt-runner/state_manager.py`는 **Pydantic StateModel + atomic write**로 110단계 선형 워크플로우의 상태를 관리(별도 Python 프로세스, `claude -p` 갈래).

**충돌 본질:** 둘 다 "다단계 실행을 결정론적으로 구동". 하지만 strategy.md Part C가 이미 판정 — **Workflow 도구가 `claude -p` 갈래를 지배한다**(인세션·예산·resume·구조화출력 우위).

**결정 (융합 ≠ 복제):**
1. **런타임 = CYS `emit_workflow.py` → Workflow .js. 단일.** prompt-runner를 별도 런타임으로 이식하지 **않는다**.
2. **prompt-runner에서 *추출*하는 것은 패턴/클래스 3개뿐:**
   - **State Machine Pattern** → emit의 `_topology`를 *명시 상태노드*로 재서술(현재 if-else로 토폴로지 분기 → 상태 enum으로). 토폴로지 추가 시 상태 추가만. *런타임 변경 없음, 코드 가독성·확장성만 향상*.
   - **StateManager(atomic write + backup)** → `lib/atomic_write.py` 신규. MANIFEST/harness.lock/snapshot 모든 쓰기가 이걸 통과. prompt-runner의 `claude -p` 구동 로직은 **버린다**.
   - **Tool-output 3-layer validator**(silent failure/session expiry/auto-response) → `lib/tool_output_validator.py`로 일반화. h2h 런 분석에 재사용(LLM API 무관).
3. **버리는 것:** prompt-runner의 110단계 스캐폴드, `run.py`(별도 프로세스 구동), `--resume`/`/clear` CLI idiom (Workflow `resumeFromRunId`가 대체), RateLimitHandler 풀구현(개인용 무게 — 정책 JSON만).

→ **한 문장:** prompt-runner는 *런타임으로 이식 안 됨*. 그 *DNA 3조각*(상태머신 패턴, 원자쓰기, 출력검증)만 CYS 런타임을 보강한다.

### 3-4. context-snapshots / agent-memory ↔ MANIFEST / evolve (M2) 매핑

> **AWF context-snapshots와 CYS MANIFEST는 같은 문제(세션간 메모리)의 두 해법.** 둘 다 들고 가면 중복·드리프트.

**결정: MANIFEST/evolve가 CYS의 canonical 세션간 메모리.** (근거: `06_MANIFEST*.md`가 명시 — "Workflow 캐시는 per-run only, MANIFEST가 cross-invocation 메모리".)

매핑:
| AWF 개념 | CYS canonical 대응 | 조치 |
|---|---|---|
| context-snapshot (작업상태 외부파일) | MANIFEST `content_hash` + evolve의 `loadCached(diskpath)` | **MANIFEST 재사용.** 자식 산출물이 곧 스냅샷 |
| Knowledge Archive (knowledge-index.jsonl, 세션간 학습) | MANIFEST `audit_log[]` + (M2) 에러패턴 필드 | MANIFEST 확장. *별도 jsonl 만들지 않음* |
| agent-memory (`memory: project`) | agent.md.tmpl frontmatter `memory: project` | emit이 주입. *플랫폼 네이티브 메모리 사용* |
| IMMORTAL 마커/압축 | **skip** (개인용 무게) | MANIFEST는 압축 불요(content-addressed) |

**M2 재사용 지점:** strategy.md M2의 `evolve`(hash diff 부분재실행)와 `harness import`가 정확히 이 매핑 위에서 돈다. context-snapshot 풀구현(131줄, 9 hook event)은 **M2에서도 안 만든다** — MANIFEST가 80/20을 이미 커버. SessionStart/Stop 스냅샷(MVP)만 generated hook으로(§3-2).

### 3-5. hooks / decision-log ↔ 생성 하네스 `.claude/`

- **hooks:** emit이 자식 `.claude/settings.json`에 등록 (§3-2 settings.json.tmpl).
  - **L0 보안 3종**(block_destructive/secret_filter/sensitive_file_guard) — AWF 자산 복사, PreToolUse/PostToolUse 매처.
  - **write_lock.sh + stamp_node.sh** — `06_MANIFEST*.md` F/G절 그대로(harness.lock 소비, HARNESS_NODE_ID 스탬프).
  - **SessionStart/Stop** — 스냅샷 MVP만.
  - validator 신규 check: hook 스크립트 존재 + settings.json 매처 문법 검증.
- **decision-log:**
  - *factory 자신*은 `DECISION-LOG.md` 보유(AWF 문화 계승, 설계결정 기록).
  - *자식 하네스*에는 풀 DECISION-LOG를 emit하지 **않음**(개인용 무게). 대신 MANIFEST `audit_log[]`가 자동승인·결정을 기록 — 머신 검색 가능, prose 아님.

### 3-6. graph.json 확장 (최소 침습)

기존 스파인 필드명 불변(`additionalProperties:false` 유지). 신규 *옵션* 필드만:
- `metadata.absolute_criteria: ["ac1","ac2","ac3"]` (감사용, 이미 metadata는 자유객체).
- node 레벨 옵션: `pacs: {enabled}`(기본 false), `review: "none|@reviewer|@fact-checker"`(이미 메커니즘으로 표현 가능 — 중복 시 skip), `tools: [...]`(least-privilege, agent.md로도 가능).
- **원칙: 메커니즘으로 이미 표현 가능한 건 schema에 안 넣는다**(reflect/debate가 review를, dispatch가 fan-out을 이미 표현). schema 비대화 방지.

---

## 4. 충돌 & 중복 해소 (concern별 canonical 1개)

| Concern | AWF DNA | CYS 자산 | **Canonical 결정** | 정당화 |
|---|---|---|---|---|
| **실행 런타임** | prompt-runner state-machine (`claude -p`) | emit_workflow.py → Workflow .js | **CYS Workflow .js (단일)** | strategy.md Part C 실측: Workflow 도구가 인세션·예산·resume·schema 전부 우위. prompt-runner는 패턴 3조각만 기증(§3-3) |
| **세션간 메모리** | context-snapshots / knowledge-index.jsonl | MANIFEST + evolve ledger | **CYS MANIFEST/evolve (단일)** | content-addressed, 결정론, LLM 불개입. AWF 131줄 상태머신은 복잡도 부채(Cautions 명시). 80/20을 MANIFEST가 커버 |
| **SOT (단일진실)** | state.yaml (오케스트레이터 쓰기) | MANIFEST (post-run 쓰기) + harness.lock | **MANIFEST=드리프트/evolve SOT, state.json=런타임 작업상태** (둘 역할 분리) | 둘은 다른 것: MANIFEST=provenance ledger(빌드/evolve), state.json=런타임 진행. AWF "쓰기는 오케스트레이터만"은 write_lock.sh가 강제 |
| **원자 쓰기** | StateManager (temp→rename+flock) | (현재 bare file I/O) | **AWF StateManager 이식 → lib/atomic_write.py** | CYS가 결여한 것(FATAL FLAW #2). AWF 검증된 패턴 직수입 |
| **Audit/Decision 기록** | DECISION-LOG.md + autopilot-logs/ + ADR | (없음) | **MANIFEST.audit_log[] (자식) + DECISION-LOG.md (factory만)** | 별도 audit 파일 = async 크래시 창(FATAL FLAW #3). 단일 원자쓰기로 병합 |
| **품질 게이트** | 4-Layer L0→L2 + P1 14 scripts | validator 11 + agent({schema}) + reflect/debate | **CYS 게이트로 매핑·명명** (신규 게이트 추가 X) | L0=validator, L1=schema, L1.5=pACS(opt-in), L2=Review메커니즘. 이미 있는 것을 AWF 어휘로 *명명*만 |
| **적대적 리뷰** | Generator-Critic + Pre-mortem | reflect-then-revise / producer-reviewer / debate-with-judge | **CYS 메커니즘 (단일)** | 이미 동치. Pre-mortem 3질문만 emit 프롬프트에 inline |
| **Fan-out 멀티퍼스펙티브** | Fork-Based Research (페르소나) | dispatch 토폴로지 + debate | **CYS 토폴로지 (단일)** | 동치. 페르소나 가이드는 template-only |
| **에이전트 메모리** | 커스텀 knowledge-index | `memory: project` (플랫폼 네이티브) | **플랫폼 네이티브 memory** | 재발명 금지. frontmatter 한 줄 |
| **i18n** | glossary.yaml + JA + validate_translation | (없음) | **glossary.yaml 복사 (EN/KO) + validate_translation 복사** | JA skip(개인용). AWF 자산 직재사용 |

**충돌해소 원칙:** "AWF가 검증한 *자산*은 복사(security hooks, glossary, StateManager, validate_translation). AWF가 정의한 *개념*이 CYS에 이미 있으면 CYS를 canonical로(런타임·메모리·게이트·리뷰). 둘 다 무게값 못 하면 둘 다 skip."

---

## 5. 단계별 통합 로드맵

> strategy.md M0/M1/M2와 정렬. **이 청사진은 M0 완료 상태(all GREEN)를 전제**하므로, 아래는 "DNA 이식" 증분만. M2 작업과 명시적으로 재사용 표기.

### Phase D0 — 게놈 기반 (1~2주) · "영혼을 게이트로"
선행 작업. 무게 가장 가벼움, 파급 가장 큼.
- **산출물:**
  1. `CONSTITUTION.md`(AC1/AC2/AC3 불변) + `constants.json`에 AC 문구.
  2. `lib/atomic_write.py`(AWF StateManager 이식) — MANIFEST/lock 쓰기에 적용.
  3. `templates/` 디렉터리 + `inherited-dna.md.tmpl`.
  4. validator 확장: W1(Inherited DNA 섹션 존재) + AC-2(SOT 단일쓰기 grep).
- **성공기준:** (a) emit한 하네스의 `harness.md`에 `Inherited DNA:`/`Gene Expression:` 섹션 자동 존재 → validator W1 통과. (b) 그 섹션 삭제 시 validator 빌드실패. (c) MANIFEST 쓰기가 atomic(temp→rename, 크래시 시뮬레이션에서 부분쓰기 0).

### Phase D1 — 보안 + i18n 자산 이식 (1주) · "검증된 자산 직수입"
- **산출물:**
  1. `templates/hooks/{block_destructive, output_secret_filter, security_sensitive_file_guard}.py` (AWF 복사) + `settings.json.tmpl`.
  2. `templates/glossary.yaml`(AWF 복사+CYS 용어) + `lib/validate_translation.py`(AWF 복사).
  3. emit이 자식 `.claude/hooks/` + settings.json에 보안 hook 등록.
  4. validator 신규 check: HOOK_PRESENT(보안 스크립트 존재) + SETTINGS_MATCHER(매처 문법).
- **성공기준:** (a) emit한 자식에서 `git push --force`/secret leak/.env Edit이 hook으로 차단됨(라이브 테스트). (b) Translation enable 노드 있는 하네스만 glossary 스캐폴드 생성. (c) validate_translation이 깨진 glossary에서 T-check 실패.

### Phase D2 — Sub-agent 전문화 + write-lock 완성 (1~2주) · "최소권한 샌드박스"
- **산출물:**
  1. `templates/agent.md.tmpl`(frontmatter: model/tools/maxTurns/memory:project) — emit이 node.agent마다 생성.
  2. emit에 CATEGORIZATION dict(translator→always_fork 등) + validator가 미등록 agent 거부.
  3. `write_lock.sh` + `stamp_node.sh`(MANIFEST 06절 그대로) emit 주입.
  4. validator 신규: LEAST_PRIVILEGE(opus+full-Bash+network 동시 경고), CATEGORIZATION_COMPLETE.
- **성공기준:** (a) write_lock hook이 비-owner Write 거부(라이브). (b) tools 미선언 agent → validator 경고. (c) 미등록 sub-agent 호출 → emit 단계 거부.

### Phase D3 — 상태머신 명시화 + 출력검증 (1주) · "런타임 가독성"
- **산출물:**
  1. emit `_topology` 리팩터: if-else 토폴로지 분기 → 상태 enum 노드(prompt-runner State Machine Pattern). **런타임 동작 불변, 구조만**.
  2. `lib/tool_output_validator.py`(AWF 3-layer 일반화) — h2h 런 분석에 wire.
  3. (옵션) `lib/policies.json`(RateLimitPolicy JSON화).
- **성공기준:** (a) 기존 3 예제 emit 결과 .js가 리팩터 전후 *바이트 동일 또는 동치 실행*(회귀 0). (b) tool_output_validator가 silent-failure/rate-limit/session-expired 분류 정확.

### Phase D4 — Context Preservation MVP + audit_log (1~2주) · "M2 재사용 기반"
> **M2 evolve/import 작업과 직접 재사용.** 여기서 만든 audit_log + 스냅샷 MVP가 M2 Phase-0 audit의 입력.
- **산출물:**
  1. emit이 자식에 SessionStart/Stop hook(스냅샷 MVP) 주입 — *PreCompact/SessionEnd는 안 만듦*.
  2. MANIFEST 스키마에 `audit_log: [{ts, event, details}]` 추가(원자쓰기로 병합).
  3. (M2 선행) MANIFEST `error_patterns` 필드 — Knowledge Archive의 80/20.
- **성공기준:** (a) /clear 후 SessionStart hook이 MANIFEST에서 작업상태 복원. (b) 자동승인 결정이 audit_log에 1엔트리=1원자쓰기로 기록. (c) **M2 `phase0_drift`가 이 audit_log+MANIFEST만으로 dirty 노드 산출**(별도 메모리 불요 증명).

### Phase D5 (= strategy.md M1/M2 합류) — opt-in pACS + import 어댑터
- **D5a (M1 합류):** `references/pacs-scoring.md` + node `pacs:{enabled}` opt-in flag + `lib/validate_pacs.py`(AWF 복사). 헤드투헤드 3도메인에 pACS 차원 추가.
- **D5b (M2 합류):** `harness import <path>` 어댑터 — 30 AWF 프로젝트 역생성. **D0-D4의 게놈/보안/agent/audit 템플릿을 import에 일괄 적용** → import된 30개 전부 validate 통과 + Inherited DNA 섹션 보유.
- **성공기준:** (a) pACS opt-in 켠 노드만 pacs-logs 생성, 끈 노드는 비용 증가 0. (b) 30개 import 후 전부 validator GREEN + 헤드투헤드 비퇴행(no-regression).

**로드맵 한 줄:** D0(영혼→게이트) → D1(자산직수입) → D2(샌드박스) → D3(런타임가독성) → D4(메모리 MVP, M2기반) → D5(M1/M2 합류). **D0-D2가 80%의 무게값**; D3-D5는 점증.

---

## 6. 리스크 & 미해결 결정 (박사님 판단 필요)

### 리스크 (정직 보고)
1. **상태머신 리팩터 회귀 위험(D3):** emit `_topology`를 상태노드로 재서술하면 LIVE-PROVEN deep-research가 깨질 수 있음. → **완화:** D3 전 기존 3예제 emit 결과를 골든파일로 고정, 리팩터 후 바이트/동치 비교. 회귀 시 D3 롤백(런타임은 D3 없이도 작동).
2. **템플릿 주입이 자식 하네스 비대화:** 모든 자식에 보안 3종+hook+glossary 주입 시 단순 하네스가 무거워짐. → **완화:** 보안 hook은 항상(무게값 함), glossary는 Translation enable 시만, pACS는 opt-in. "earns its weight" 원칙을 emit 조건문으로 강제.
3. **MANIFEST에 audit_log 병합 시 파일 비대(D4):** 장기 실행 하네스의 audit_log가 MB급. → **완화:** AWF Knowledge Archive Cautions의 "monthly rollover" 차용 — audit_log 200엔트리 LRU 절단(atomic_write 내). IMMORTAL 압축은 skip.
4. **write-lock Mode B 열화(불변 제약):** 팀 모드는 hook-to-teammate 바인딩 불가(06절 명시). → **완화:** 결정론 필수 시 Mode A 유도. Mode B는 path-ownership만. *플랫폼 제약이지 결함 아님 — 정직 광고*.
5. **AWF 자산 복사의 드리프트:** security 3종/validate_translation을 복사하면 AWF 원본 수정 시 동기 안 됨. → **완화:** 복사 헤더에 `# SOURCE: AgenticWorkflow/.claude/hooks/scripts/<name> @ <commit>` 스탬프. AWF는 READ-ONLY이므로 수동 재pull. (개인용이라 자동동기 불요.)
6. **self-measured 신뢰성(잔존):** 헤드투헤드도 결국 자기측정. → strategy.md대로 미달 도메인 정직보고.

### 미해결 결정 (박사님께)
- **D-A. state.json vs MANIFEST 역할분리 동의?** 청사진은 "MANIFEST=evolve/provenance SOT, state.json=런타임 진행상태"로 *둘 다 유지*(다른 역할)를 제안. 대안: state.json도 MANIFEST에 흡수(더 단순하나 런타임 진행을 content-hash로 표현 부자연). **→ 권고: 역할분리 유지.**
- **D-B. pACS를 M1 opt-in으로 미룸에 동의?** 개인용에서 모든 노드 pACS는 무게 과다 판단. 대안: 고위험 노드(synthesis/judge)만 강제. **→ 권고: opt-in + references 문서.**
- **D-C. 3-Stage Constraint(R→P→I)를 template-only로 강등에 동의?** AWF는 crown급으로 보나, CYS 토폴로지(pipeline/dispatch/producer-reviewer)가 더 일반적이라 강제 시 과설계. 대안: graph.json에 stage 필드 강제. **→ 권고: template-only(권장 스캐폴드).**
- **D-D. JA i18n 완전 skip에 동의?** 개인용·한국 개발자. 대안: parity 명분으로 README.ja만. **→ 권고: skip.**
- **D-E. prompt-runner를 런타임 아닌 "패턴 3조각 기증자"로만 쓰는 데 동의?** 가장 큰 아키텍처 결정. 대안: prompt-runner를 `claude -p` 배치 실행용으로 별도 보존. **→ 권고: 런타임 단일화(Workflow), prompt-runner는 atomic_write/state-machine/output-validator만 추출. 단 prompt-runner 디렉터리 자체는 AgenticWorkflow(READ-ONLY)에 있으므로 *읽어서 CYS에 재구현*, 복사 아님.**

---

### 참조 파일 경로 (절대)
- 팩토리 코어: `/Users/cys/Desktop/CYSjavis/cys-harness-creator/emit_workflow.py`, `/Users/cys/Desktop/CYSjavis/cys-harness-creator/validate_harness.py`, `/Users/cys/Desktop/CYSjavis/cys-harness-creator/graph.schema.json`
- 전략·MANIFEST 설계: `/Users/cys/Desktop/CYSjavis/cys-harness-creator/design/strategy.md`, `/Users/cys/Desktop/CYSjavis/cys-harness-creator/design/_raw/06_MANIFEST.json_+_harness.lock.md`
- AWF 재사용 자산(READ-ONLY 소스): `/Users/cys/Desktop/CYSjavis/AgenticWorkflow/soul.md`, `/Users/cys/Desktop/CYSjavis/AgenticWorkflow/translations/glossary.yaml`, `/Users/cys/Desktop/CYSjavis/AgenticWorkflow/.claude/hooks/scripts/{block_destructive_commands.py, output_secret_filter.py, security_sensitive_file_guard.py, validate_translation.py, validate_pacs.py, validate_review.py}`, `/Users/cys/Desktop/CYSjavis/AgenticWorkflow/prompt-runner/state_manager.py`
- 신규 착지 예정(전부 cys-harness-creator/ 하위): `CONSTITUTION.md`, `lib/atomic_write.py`, `lib/tool_output_validator.py`, `lib/validate_translation.py`, `lib/validate_pacs.py`, `templates/{inherited-dna.md.tmpl, agent.md.tmpl, settings.json.tmpl, glossary.yaml, hooks/*}`, `references/{pacs-scoring.md, 3-stage-scaffold.md, persona-guide.md}`