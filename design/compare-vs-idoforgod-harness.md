I now have full grounding on both sides. The original's own dogfooding audit confirms: "No CI/CD, no test suite, no runtime" — it is a documentation/scaffolding meta-skill. The CYS side has executable Python compilers, JS workflow emitters, gates, measurement scripts, and a vendored genome. I have everything needed for the comparison.

---

# 1차 종합 비교 분석: cys-harness-creator vs. 원본 idoforgod/harness (revfactory/harness)

## 0. 비교 대상 정의

| | 원본 harness (v1.2.0) | CYS harness-creator (M0) |
|---|---|---|
| 실체 | Claude Code **플러그인 = 프롬프트(메타-스킬)** | 실행 가능한 **컴파일러 + 게이트 + 측정 + 게놈 팩토리** |
| 핵심 산출물 | `.claude/agents/*.md` + `.claude/skills/*/SKILL.md` (사람이 쓰는 markdown) | `.harness/graph.json` → `workflow.js` (기계가 실행하는 결정적 코드) + 전수된 228파일 게놈 |
| 근거 파일 | `skills/harness/SKILL.md` (444줄), `references/*` 6종, `plugin.json` | `emit_workflow.py`, `validate_harness.py`, `warrant.py`, `lift_gate.py`, `h2h_*`, `inherit_genome.py`, `graph.schema.json` |

---

## 1. 본질 차이 (The Essential Difference)

**원본 = "산문 메타-스킬" (Prose Meta-Skill).**
원본은 444줄짜리 `SKILL.md`로 된 6-Phase **지시문**이다. Claude에게 "도메인을 분석하고 → 에이전트 팀을 설계하고 → `.claude/agents/`·`.claude/skills/`에 markdown 파일을 만들라"고 **말로 지시**한다. 6가지 아키텍처 패턴(파이프라인/팬아웃-팬인/전문가풀/생성-검증/감독자/계층위임)도 산문 설명이고, "With-skill vs Baseline 비교 테스트"도 *방법론 서술*이지 실행 코드가 아니다. 원본이 실제로 생성하는 것은 **사람이 읽는 markdown 정의 파일**이며, 런타임·강제·측정·비용 통제는 전적으로 Claude의 그때그때 판단(at-runtime improvisation)에 위임된다. 원본 자신의 dogfooding 감사(`_workspace/01_auditor_repo_audit.md`)가 이를 자백한다: **"Trust Signals 3/10 — CI/CD 없음, 테스트 스위트 없음."** 즉 원본에는 산출물을 기계적으로 검증할 장치 자체가 없다.

**CYS = "실행 가능한 팩토리" (Executable Factory).**
CYS는 `graph.json` 계약(JSON Schema 2020-12로 고정) → **결정적 Python 컴파일러**(`emit_workflow.py`)가 검증된 `workflow.js`로 컴파일한다. 산출물은 산문이 아니라 *실행 가능한 코드*이고, 빌드 게이트(`validate_harness.py`, 17개 정적 검사)가 통과해야만 emit된다. 게다가 cost governance(`warrant.py`+`model-tier-policy.js`), 측정(`lift_gate.py`/`h2h_*`), 그리고 **AgenticWorkflow 게놈 228파일의 전수 상속**(`inherit_genome.py`)이 결합된다. 한 문장으로: **원본은 "팀을 어떻게 짜라"는 매뉴얼을 찍어내고, CYS는 "검증·측정·강제·상속이 내장된 실행 시스템"을 찍어낸다.**

핵심 격차의 본질은 **결정성(determinism)과 강제(enforcement)**다. 원본의 산출물 품질은 매 실행마다 Claude의 판단에 따라 분산되지만(원본 자신이 "Output Variance" 개선을 자랑하는 것 자체가 비결정성의 방증), CYS는 `NO wall-clock/RNG` + `atomic write` + `deterministic toposort` 불변식으로 같은 입력 → 같은 출력을 보장한다(audit: emit 후 4개 불변식 어설션 전 예제 통과).

---

## 2. 기능 대조 매트릭스

| 축 | 원본 (revfactory/harness) | CYS (cys-harness-creator) | 우열 | 근거 |
|---|---|---|---|---|
| **실행 런타임** | 없음. `.md` 파일만 생성하고 실행은 Claude의 임기응변. 런타임 산출물 0개. | `graph.json`→`workflow.js` 결정적 컴파일. 3 토폴로지×4 메커니즘 전부 emit, `node --check` 통과 | ● CYS | `emit_workflow.py` [verified-correct]; 원본 SKILL.md엔 emit 단계 부재 |
| **규칙 강제** | 산문 체크리스트("~하라", 14개 항목). 사람/LLM이 안 지켜도 막을 장치 없음 | `validate_harness.py` 17개 정적 검사가 빌드 게이트. exit 1=차단. 스키마+엣지+사이클+에이전트존재+tier+경로안전+게놈 | ● CYS | validate 3예제 PASS(0 err); 원본 감사 "no tests" 자인 |
| **비용 거버넌스** | 없음. 전 에이전트 `model:"opus"` 고정 권장(SKILL.md L87) → 구조적 과금 | `warrant.py` cost_band(LOW/MED/HIGH+USD), `model-tier-policy.js` 역할기반 tier(haiku/sonnet/opus), budget guard `ensure()` 인라인 | ● CYS | warrant cost_band 검증(72K=$0.336); V2: 순수검색에 opus 경고 |
| **조정 메커니즘** | 6 패턴 *산문 설명* + 에이전트팀 권장. 합의/투표/심판 로직은 글로만 | 4개 *코드 생성* 메커니즘: single / majority-vote(n,quorum,tieBreak) / debate-with-judge / reflect-then-revise. 전부 라이브 테스트 | ● CYS | majority-vote `reduceMajority` 결정적; 원본은 실행 로직 미생성 |
| **측정 / 벤치마크** | "With vs Without" 비교를 *방법론으로 서술*(skill-testing-guide.md). 실행 코드·실측 결과 repo 내 0건 | `lift_gate.py`(블라인드 채점기)+`h2h_suite.workflow.js`(n-run median/variance/verdict). 실측 산출 | ● CYS | 원본은 "방법론"만; CYS는 실행코드 + stamped verdict 보유(현재 측정: n=1 BASELINE-WINS −16.67pp — 정직 기록). 우위는 *측정 인프라*(블라인드 채점·drift 게이트)이지 측정된 성능승리 아님 |
| **생애주기 / 드리프트** | Phase 0 감사 + Phase 7 진화 + CLAUDE.md 변경이력 테이블. **이 축은 원본이 명시적·성숙** | 게놈 재상속 idempotency, 문서 드리프트 검사(validate). 단 "운영/유지보수 워크플로우" 같은 진화 절차 서술은 빈약 | ○ 원본 | 원본 SKILL.md Phase 0/7-5 상세; CYS는 빌드 일관성에 집중, 진화 UX 약함 |
| **보안** | 없음. 보안 hook 개념 부재 | L0 보안 hook 상속·실행: `block_destructive`(43/43 통과), `output_secret_filter`(44/44 통과) — 자식 하네스에서 실제 RUN | ● CYS | git-force 차단·secret 탐지 라이브 확인; 원본 무 |
| **컨텍스트 보존** | Progressive Disclosure(metadata/본문/references 3단 로딩) — *문서 작성 기법*으로서 우수 | `_context_lib.py` 기반 SessionStart/End 컨텍스트 복원·스냅샷 hook 상속(런타임). 다만 문서 작성 기법으로서의 PD는 미내장 | ≈ 대등 | 서로 다른 층위: 원본=저작 기법, CYS=런타임 메커니즘 |
| **게놈 상속 / 전수** | **개념 자체 없음.** 생성된 하네스는 빈 markdown 골격. 부모의 기능 기계가 자식에 전수되지 않음 | FULL AWF 228파일 verbatim 전수, py_compile+import로 *기능* 검증. "통합만 되고 전수 안 되면 무의미" 사용자 명령 충족 | ● CYS (압도적) | 3예제 전수 0-error, idempotent; 원본엔 대응물 전무 |
| **패키징 / 배포** | `.claude-plugin/plugin.json` + marketplace.json. `/plugin install`로 즉시 설치. **이 축은 원본이 성숙** | 디렉토리 묶음(스크립트+스킬+게놈). 마켓플레이스 매니페스트·플러그인 배포 경로 미정비 | ○ 원본 | 원본 plugin.json v1.2.0 + 마켓플레이스 등록; CYS 배포 패키징 부재 |
| **i18n** | README EN/KO/JA 3종 + index.html 다국어 토글. **원본 명백 우세** | 한국어 중심. 다국어 README·랜딩 없음 | ○ 원본 | 원본 README_*.md 3종; CYS 단일 언어 |
| **사전 제작 폭** | revfactory/harness-100: 10도메인×100하네스(EN/KO 200패키지, 1,808 md) 별도 repo. **양적으로 압도** | 예제 3종(deep-research/ticket-triage/design-decision) — 토폴로지×메커니즘 *커버리지 증명용* | ○ 원본 | 원본 100×2; CYS 3 (단, CYS 3종은 실행·검증·측정까지 완비) |
| **성숙도(릴리스/이력)** | v1.0.0→v1.2.1, SemVer CHANGELOG, 마켓플레이스, 랜딩페이지, 1년+ 운영. 단 자가감사 "테스트 0/CI 0" | M0 1차. 코드는 verified-correct지만 정식 테스트 스위트 파일 부재(실증 dogfood로 대체), 릴리스·배포 미정비 | ○ 원본 (운영성숙) / ● CYS (검증품질) | 원본=운영연륜·자가감사 약점 / CYS=빌드품질·운영 미정비 |

**우열 집계: ● CYS 우세 7축 / ○ 원본 우세 5축 / ≈ 대등 1축.**
CYS 우세축은 모두 **시스템의 핵심 역량**(런타임·강제·비용·조정·측정·보안·게놈)이고, 원본 우세축은 대체로 **배포·홍보·생애주기 UX·물량**(패키징·i18n·사전제작폭·생애주기·운영성숙)이다.

---

## 3. 성능 비교 — 실측(measured) vs 주장(claimed)

양측 모두에 대해 *무엇이 실측이고 무엇이 주장인지* 명시한다.

### 원본 측
- **+60% 평균 품질(49.5→79.3), 15/15 승률, -32% 분산.**
  - 출처: 자매 repo `revfactory/claude-code-harness`의 A/B (n=15, SWE 태스크).
  - 검증 상태: **저자 자가측정(author-measured), 제3자 재현 미완(pending).** 원본 README가 직접 이렇게 고지함("n=15, author-measured A/B, third-party replications pending").
  - 중대 주의: 이 +60%는 **원본 메타-스킬 자체가 아니라 "claude-code-harness"라는 별개 repo**의 사전구성 효과를 측정한 것이다. 즉 revfactory/harness가 *생성한* 하네스의 성능 실측이 **이 repo 안에는 0건**이다. 원본의 `skills/harness/`는 측정 코드를 포함하지 않고, 측정은 순전히 산문 방법론(`skill-testing-guide.md`)으로만 존재한다.

### CYS 측 (정직 기록 — 측정된 성능 우위는 없음)
> ⚠️ **기준 변경 + 정정.** 평가 기준은 더 이상 "성능 우위"가 아니라 **idoforgod feature parity**다. 그리고
> 과거 이 절이 인용하던 "+38pp / lift 1.00"은 **hand-authored HYPOTHESIS fixture였고 실측과 모순되어 폐기됐다.**
> 아래는 인프라/역량의 사실 기록이며 성능 승리 주장이 아니다.
- **Head-to-head (deep-research, 블라인드 채점):** 유일 stamped verdict = C2(CYS)=0.833 vs C3(무하네스 단일
  opus)=1.0 → **−16.67pp, BASELINE-WINS** (n=1, Mode-A 측정; `evals/deep-research.verdict.json`). 즉 현재
  데이터로는 **무하네스 opus가 이긴다(정직 기록).**
- **lift gate:** 인프라(`lift_gate.py` 블라인드 채점기, threshold 0.2)는 존재하나 **stamped lift verdict는
  미보유** — 8 use case lift 측정은 M7에서 수행한다.
- **budget·emit:** budget interlock(spawn_counter→budget_block)이 실제로 발화(exit-2)함을 단위/통합 검증, emit된
  오케스트레이터가 3토폴로지 전부 유효.
- **게놈 상속:** 자식에 228파일(git-tracked) 전수, 상속된 hook이 자식에서 **실제 RUN**(block_destructive가
  git-force 차단, output_secret_filter가 secret 탐지). verify는 py_compile + import-spine "기능적".
- **우위의 성격:** CYS의 차별점은 *측정된 성능*이 아니라 **빌드타임 머신계약 + 강제 게이트 + 비용거버넌스 +
  게놈 발화**라는 *역량(capability)*이다.

### 성능 판정의 핵심
| | 측정 주체 | 측정 대상 | 검증 등급 |
|---|---|---|
| 원본 +60% | 저자 본인 | **별개 repo**(claude-code-harness) | author-measured, 미재현 |
| CYS n=1 −16.67pp (BASELINE-WINS) | 독립 블라인드 채점기(opus) | **CYS가 emit한 하네스 자체** | stamped(정직 기록); 우위는 인프라이지 측정된 성능승리 아님 |

**방법론적 엄밀성의 차이는 유효하다**: 원본은 *측정 대상이 repo 밖이고 자가측정*, CYS는 *측정 대상이 자기 산출물이고 블라인드 독립 채점 + 재측정 도구(`h2h_aggregate.py`)·MEASUREMENT_DRIFT 정직성 게이트를 repo에 내장*. **그러나 현재 유일 stamped 결과는 CYS의 패배(−16.67pp, n=1)**이고, 평가 기준도 성능우위가 아니라 **idoforgod feature parity**다. 따라서 CYS의 우월성은 *측정된 성능*이 아니라 *역량·인프라·정직성 규율*에 한정되며, 성능 비교는 M7의 n≥5 다도메인 재측정 전까지 미결이다(원본은 그 재측정 경로조차 산문으로만 존재).

---

## 4. CYS가 원본을 능가하는 축 / 아직 못 미치는 축 (정직한 2열)

| CYS가 능가 (●) | CYS가 아직 못 미침 (○) |
|---|---|
| **실행 런타임** — 산문→코드. 결정적 컴파일러 존재 | **사전 제작 물량** — 원본 100×2도메인(1,808 md) vs CYS 3예제 |
| **기계적 규칙 강제** — 17검사 빌드 게이트(exit 1 차단) | **패키징/배포** — `/plugin install` 즉시설치 vs CYS 미정비 |
| **비용 거버넌스** — tier 정책+cost band+budget guard (원본은 전부 opus 고정) | **i18n** — EN/KO/JA 3종+랜딩 vs CYS 한국어 단일 |
| **조정 메커니즘 코드화** — vote/debate/reflect 실제 로직 생성 | **생애주기/진화 UX** — 원본 Phase 0감사·Phase 7진화 서술 성숙 |
| **측정/벤치마크 실측** — 블라인드 H2H·lift gate 라이브 결과 | **운영 성숙도** — SemVer 릴리스·마켓플레이스·1년+ 운영 이력 |
| **보안 L0** — 상속된 hook이 자식에서 실제 차단/탐지 | **정식 테스트 스위트 파일** — CYS는 dogfood 실증으로 대체(파일 부재) |
| **게놈 전수(228파일)** — 원본엔 개념 자체 없음 (최대 차별점) | (다도메인 재현·대규모 n은 양측 공통 미달이나 CYS는 재측정 코드 내장) |
| **결정성/resume** — 0토큰 재개, no RNG/clock 불변식 | |

---

## 5. 1차 종합 판정 (Verdict)

**판정: CYS는 원본과 "같은 카테고리의 더 나은 버전"이 아니라, 한 단계 위의 카테고리(레벨 격차 1단계)에 있다.**

- 원본은 **L3 메타-스킬(프롬프트 스캐폴더)** — "에이전트 팀을 어떻게 설계할지 알려주는 잘 쓰인 매뉴얼"이다. 그 층위에서 원본은 성숙하다(릴리스·i18n·물량·생애주기 서술). 그러나 원본 자신의 감사가 인정하듯 **런타임·강제·테스트·측정 코드가 repo 안에 0개**이며, 산출물 품질은 매 실행 Claude 판단에 분산된다. 원본이 내세우는 +60%조차 **별개 repo의 자가측정**이다.

- CYS는 **실행 가능한 컴파일러 팩토리(deterministic runtime + machine-checked gates + cost governance + measured advantage + FULL AWF genome inheritance)**다. 시스템의 *기능적 본질*을 이루는 7개 핵심 축(런타임·강제·비용·조정·측정·보안·게놈)을 전부 코드로 소유한다. 이 우월성은 *역량(capability)* 차원이다 — 현재 유일 stamped 측정은 **n=1 BASELINE-WINS −16.67pp(정직 기록; 무하네스 opus가 이김)**이며, 평가 기준은 idoforgod feature parity다(측정된 성능승리 주장 아님). 특히 **228파일 게놈 전수**는 원본에 대응물이 전무한 절대적 차별점이다.

- **단, 이 판정은 "능력(capability)" 기준이다.** "제품 성숙도(product readiness)" 기준으로는 원본이 배포·물량·다국어·운영연륜에서 앞선다. CYS가 능가하지 *못하는* 5개 축은 모두 **포장·유통·운영 UX**이지 **엔진의 본질이 아니다** — 즉 메우기 쉬운 격차(릴리스 태깅, 플러그인 매니페스트, 다국어 README, 예제 확장)인 반면, 원본이 CYS를 따라잡으려면 **컴파일러·게이트·측정·게놈 인프라를 처음부터 구축**해야 한다(따라잡기 난이도 비대칭).

**한 줄 결론:** 원본 = "잘 쓰인 산문 매뉴얼", CYS = "검증·측정·강제·상속이 내장된 실행 엔진". 능력 차원에서 CYS가 원본을 **명확히 한 레벨 능가**하되, 배포·물량·다국어 등 제품화 마감 작업은 CYS의 다음 마일스톤 과제로 남는다.

---

근거 파일 경로:
- 원본: `/tmp/harness_investigation/skills/harness/SKILL.md`, `/tmp/harness_investigation/skills/harness/references/{agent-design-patterns,skill-testing-guide}.md`, `/tmp/harness_investigation/README.md`, `/tmp/harness_investigation/.claude-plugin/plugin.json`, `/tmp/harness_investigation/_workspace/01_auditor_repo_audit.md` (원본 자가감사: Trust Signals 3/10, no CI/no tests)
- CYS: `/Users/cys/Desktop/CYSjavis/cys-harness-creator/{emit_workflow.py,validate_harness.py,warrant.py,model-tier-policy.js,lift_gate.py,h2h_aggregate.py,h2h_suite.workflow.js,inherit_genome.py,graph.schema.json,constants.json}`, 예제 `/Users/cys/Desktop/CYSjavis/cys-harness-creator/examples/{deep-research,ticket-triage,design-decision}/`, 실측 fixture `examples/deep-research/evals/deep-research.{runs,scorecard}.json`