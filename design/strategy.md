# idoforgod/harness 전수조사 + CYS Harness Creator 전략

> 작성: 마스터 클로드 (claude-cysfuturist) · 2026-05-29
> 방법: repo clone → 6 클러스터 병렬 전수조사 → 6 렌즈 적대적 비평(경쟁 웹리서치 포함) → 전략 합성 → 비평가 검증 → 마스터 교차검증·정정 (15 에이전트, ~107만 토큰)
> 원본: https://github.com/idoforgod/harness (실제 upstream = revfactory/harness, Apache-2.0, v1.2.0)

---

## Part A. 전수조사 — 이 저장소는 무엇인가

### A-1. 본질
**실행 코드가 아니다.** Claude Code가 따르는 **프롬프트 기반 메타스킬(=팀 아키텍처 팩토리)** 이다.
도메인 한 문장 → `.claude/agents/*.md`(누가) + `.claude/skills/*/SKILL.md`(어떻게) + 오케스트레이터 스킬(언제·순서) + `CLAUDE.md` 포인터(트리거)를 **스캐폴딩**한다.

### A-2. 전체 구성 (코드 ext: md 21, yml 4, json 2, html 2)
- **핵심**: `skills/harness/SKILL.md` (443줄, 8-Phase 워크플로우)
- **레퍼런스 6종** (~1,700줄):
  - `agent-design-patterns.md` — 2 실행모드 + 의사결정트리 + 6 패턴(패턴별 team-mode 적합도 판정) + 복합패턴 + agent 타입선택 + agent 정의구조 + 분리기준 4축 + skill↔agent 연결 3방식
  - `orchestrator-template.md` — 오케스트레이터 템플릿 A(팀)/B(서브)/C(하이브리드) + 데이터흐름 + 에러핸들링 매트릭스 + 테스트 시나리오 + 후속키워드 규칙
  - `skill-writing-guide.md` — pushy description, Why-first, <500줄, progressive disclosure
  - `skill-testing-guide.md` — with-skill vs without-skill A/B, should/should-NOT near-miss 트리거, assertion grading
  - `qa-agent-guide.md` — boundary cross-comparison, incremental QA, 실제 7버그 사례(단 Next.js 전용)
  - `team-examples.md` — 실제 팀 구성 예시(단 6패턴 중 5개만, Hierarchical 누락)
- **문서**: README ×3(EN/KO/JA), docs/quickstart, docs/experimental-dependency
- **메타/배포**: plugin.json, marketplace.json, CHANGELOG, CONTRIBUTING, .github 템플릿 4종, index.html(랜딩, 1,393줄), privacy.html
- **dogfooding `_workspace/`**: 하네스가 자기 자신에게 적용한 실제 산출물(launch team: auditor/content/scout/strategist + release audit 2건)

### A-3. 8-Phase 워크플로우 (README는 6-Phase로 광고 — 불일치)
Phase 0 현황감사(드리프트·분기 매트릭스) → 1 도메인분석 → 2 팀아키텍처(실행모드+6패턴) → 3 에이전트정의(전부 파일·`model:opus`) → 4 스킬생성 → 5 통합/오케스트레이션 → 6 검증/테스트 → 7 하네스진화(피드백·변경이력)

### A-4. 6 아키텍처 패턴
Pipeline · Fan-out/Fan-in · Expert Pool · Producer-Reviewer · Supervisor · Hierarchical Delegation
(+ 3 실행모드: 에이전트 팀[기본] / 서브에이전트 / 하이브리드)

### A-5. 생태계 (3-repo 분산)
- `revfactory/harness-100` — 100개 production 하네스(EN/KO 200패키지, 1,808 md)
- `revfactory/claude-code-harness` — +60% 품질주장의 A/B 연구(n=15, author-measured)
- 본 플러그인 repo

### A-6. 진짜 강점 (베껴와야 할 통찰)
1. **패턴별 team-mode 적합도 판정** — "Fan-out은 반드시 팀, Expert Pool은 서브가 낫다" 식 구체 판정
2. **anti-dead-code 규칙** — 오케스트레이터 description에 후속키워드 강제("재실행/수정/보완"), 없으면 첫 실행 후 죽은 코드
3. **boundary cross-comparison QA** — "존재 확인"이 아니라 "경계면 교차비교"(API 응답 ↔ 프론트 훅 shape 비교)
4. **진화 루프 개념** — 하네스를 정적 산출물이 아닌 진화 시스템으로 정의(Phase 7)
5. **Phase-0 감사·드리프트 분기** — 신규/확장/유지보수 자동 분기
6. **dogfooding 품질** — post-m0-audit은 실제로 정교(병렬 에이전트의 plugin.json 무단편집 충돌을 잡아냄)

### A-7. 검증된 치명적 약점 (전수조사 + 적대적 비평 공통분모)
| # | 약점 | 근거 |
|---|------|------|
| W1 | **런타임 없음 — 전부 .md 생성** | 실행엔진·스케줄러·상태머신·관측·예산 거버넌스 0. 신뢰성이 100% LLM 해석 prose |
| W2 | **자기 규칙 강제 불가** | authoring principles가 전부 advisory. 검증기·CI 부재. CONTRIBUTING이 주장한 CI/스크립트가 repo에 **실재하지 않음** |
| W3 | **`model:opus` 전역 하드코딩** | 자기 "high token cost" 경고와 모순. 역할 티어링 없음. 자기 예제마저 규칙 위반 |
| W4 | **조정 이론 축 공백** | 토폴로지(데이터흐름 모양)만 있고 decision mechanism(투표·토론·반영) 없음 → -32% variance 주장의 메커니즘 부재 |
| W5 | **수렴/종료 보장 없음** | 루프·대기에 정지 보장 없음. retry 규칙이 예제마다 모순(2회/force-PASS/50% REDO/재할당) |
| W6 | **end-to-end 벤치마크 없음** | +60%가 author-measured n=15 순환참조. baseline 대조 없음 → "능가"가 falsifiable하지 않음 |
| W7 | **A/B가 "가능하면"(optional)** | 헤드라인 rigor가 첫 압박에 드롭되는 구조 |
| W8 | **쓰기 동시성 사후탐지만** | 병렬 agent가 선언된 write-boundary 무단침범, post-hoc 운으로 발견. 사전 lock 없음 |
| W9 | **least-privilege 없음** | 커스텀 agent 전부 풀 Write/Bash/network 디폴트 |
| W10 | **drift/evolution이 phantom** | Phase-0 = LLM에게 diff 부탁(강제·캐노니컬 상태·rollback 없음). `/harness:evolve`가 문서에만 존재, 실재 안 함 |
| W11 | **문서 드리프트** | README 6 vs SKILL 8 phase, install 명령 3종 불일치, dead-link 5개, EN README엔 진화 섹션 자체가 없음 |
| W12 | **"harness 필요한가?" 게이트 없음** | 사소한 작업도 멀티에이전트 팀으로 over-engineer. off-ramp 부재 |
| W13 | **QA 자기검증 없음·도메인 monoculture** | 예측 실패를 실제 재현 안 함(정적 grep). 모든 구체절차가 Next.js/React 전용 |
| W14 | **버전 정합성 구조적 취약** | plugin.json + marketplace.json 2중 버전필드, CI 동기화 없음 → v1.2.1 desync 재발 가능 |

---

## Part B. 경쟁 지형 (2025–2026, 웹리서치)

| 프레임워크 | harness가 못 하는데 이들이 하는 것 | 빌려올 것 |
|---|---|---|
| **LangGraph 1.x** | 타입드 State 1급객체, 노드별 checkpoint(SQLite/PG), 시간 안 단위 pause/resume HITL, retry middleware(exp backoff) | state + checkpoint 개념(단 durable interrupt 동치는 플랫폼에 없음) |
| **OpenAI Agents SDK** | 트레이싱 대시보드, typed handoff, 병렬 guardrail(input/output/tool), Sessions 영속메모리 | typed message 형식, guardrail = hook, run-trace |
| **CrewAI 1.0** | Crews(role) vs Flows(deterministic event-driven) 분리, per-agent model, AMP 관측 control plane | Crews/Flows split = team/서브 대응, per-agent 티어 |
| **AutoGen/AG2 + Magentic-One** | speaker-selection 정책, progress-ledger + 동적 재계획, OTel 관측, prompt-injection 보호 | "자체 조율" 대신 progress-ledger, 안전 테스트 레인 |
| **Google ADK + Vertex** | 코드퍼스트 멀티에이전트, managed 런타임 배포, 메모리층, 7M+ 다운로드 | headless 배포·메모리(단 M2+ 연기) |
| **MetaGPT + AFlow (ICLR'25)** | "Code=SOP(Team)" + **자동 워크플로우 생성/탐색** | 패턴 선택을 data-driven/learned로(M3+) |
| **wshobson/agents** (최다 fork) | 50 subagent에 **Haiku/Sonnet/Opus 티어링** + 52 오케스트레이션 커맨드 | per-role 모델 티어 테이블 직접 차용 |
| **Anthropic 자체** | Claude Code subagents + Skills + **Workflow 도구(plan-as-code)** + Dynamic Workflows | → **Part C 마스터 정정 참조** |
| 표준 | A2A 프로토콜(Linux Foundation), MCP, OpenTelemetry GenAI semantic conventions, release-please/changesets | OTel **소비**, 자동 SemVer(메타-repo만) |

**경쟁 결론:** harness의 "team-architecture FACTORY for Claude Code" 각도는 실재하나 **좁고 점점 경합**된다. 자동 워크플로우 생성은 벤치마크된 연구 방향(AFlow)이고, meta-agent generator가 이미 존재한다. **방어 가능한 해자는 "생성 행위"가 아니라 durability + evolution + 측정 가능한 거버넌스**다.

---

## Part C. 마스터 정정 — "실행 런타임은 이미 존재한다" (가장 중요)

비평가와 6 렌즈 에이전트는 **changelog 설명만** 보고 다음을 판정했다:
- ❌ "Dynamic Workflows = 자연어 전용, emit 가능한 plan-as-code 형식 없음"
- ❌ "외부 결정론 드라이버가 팀/서브를 스케줄 불가"
- ❌ "라이브 토큰 예산 abort 불가"

**그러나 이 환경에는 `Workflow` 도구가 실재하며, 그 `script` 파라미터가 바로 emit 가능한 plan-as-code다.** (본 전수조사 자체가 그 도구로 실행되었다.) 사실관계 재검증:

| 비평가 판정 | 마스터 정정 (Workflow 도구 실측) |
|---|---|
| "emit 가능한 워크플로우 스크립트 형식 없음" | **있다.** `Workflow({script})`는 `export const meta` + `agent()/parallel()/pipeline()/phase()` JS 스크립트를 받는다. 메타스킬이 `.js` 파일로 **emit**하고 `Workflow({scriptPath})`로 재호출 가능 |
| "결정론적 스케줄링 불가" | **서브에이전트에 한해 가능.** `pipeline()`(스테이지간 배리어 없는 파이프), `parallel()`(배리어), `phase()`가 결정론적 제어흐름 제공. depends_on은 pipeline 단계로 표현 |
| "라이브 토큰 예산 abort 불가(hook으론 못 함)" | **워크플로우 계층에선 가능.** `budget.total` 도달 시 이후 `agent()` 호출이 **throw**. hook이 아니라 오케스트레이션 계층의 하드 ceiling |
| "durable resume 없음(STATE.json은 best-effort)" | **부분적으로 있다.** `resumeFromRunId` + journal로 변경 안 된 `agent()` 접두부는 캐시 즉시반환, 첫 변경 지점부터 라이브 재실행 |
| "structured output 강제 불가" | **있다.** `agent({schema})`가 StructuredOutput 도구 강제 + 검증 + 모델 재시도 |

**결론(공통분모 + 대립 해소):**
- 비평가가 옳은 부분: **팀(TeamCreate) 모드**는 LLM 턴 내 도구라 외부 결정론 스케줄 **불가**. → 팀 모드는 "계약 + hook 강제/로깅"이 정답(최종 전략 맞음).
- 비평가가 틀린 부분: **서브에이전트 모드의 결정론 런타임은 `claude -p` 헤드리스가 아니라 `Workflow` 도구다.** 인세션이고, **예산 ceiling·resume·structured output·pipeline/parallel을 이미 갖춘다.** 이것이 원본 harness의 최대 결손(W1 런타임 부재)을 **오늘 당장** 메우는 substrate다.

→ 따라서 실행 모델은 **3-mode**로 정리된다(최종 전략의 2-갈래를 대체):

```
Mode A — 결정론 서브에이전트 런타임  (fan-out/pipeline/vote/best-of-N, 디폴트 다수)
  메타스킬이 Workflow .js 스크립트를 emit → budget ceiling + resume + schema + pipeline/parallel
  ★ 원본이 가장 결여한 "실행엔진"을 실재 도구로 충족

Mode B — 협업 팀 (에이전트 간 실시간 comms 필수일 때만)
  graph.json = LLM 오케스트레이터가 따를 계약 + settings.json hook이 write-lock/권한 강제·로깅
  결정론 아님 (플랫폼 제약, 정직하게 광고)

Mode C — 대화형 Dynamic Workflows
  emit 대상 아님(out of scope). 안정 surface 공개 시 재평가
```

`Workflow` 도구가 `claude -p` 갈래를 지배한다: 인세션 · 예산통제 · resume · 구조화출력 모두 우위.

---

## Part D. CYS Harness Creator 전략 (정정 반영판)

### D-1. Thesis (포지셔닝)
원본은 "정적 스캐폴더". CYS는 **"강제 가능한 계약(검증기·티어·매니페스트·lift게이트) + 실재하는 실행 런타임(Workflow 도구) + 헤드투헤드 벤치마크로 무장한 하네스 팩토리"**.
해자 = 생성 행위가 아니라 **durability + 측정 가능한 거버넌스 + 결정론 서브에이전트 런타임**.

### D-2. 5대 차별화 베팅 (전부 실현 검증됨)
1. **검증기-as-린터** — `validate_harness.py` + `validate.yml`를 생성 하네스마다 emit. 파일존재·frontmatter·error scenario·후속키워드·절대경로·`.claude/commands`금지·필수 `model:`·dead-link을 **assert**. 위반 시 생성/CI 실패. 정적이라 거의 무료·100% 결정론. ("rules-as-essays → rules-as-assertions")
2. **결정론 서브에이전트 런타임 = Workflow .js emit** (마스터 정정) — comms 불필요 패턴은 `.md` prose가 아니라 **실행 가능한 Workflow 스크립트**를 emit. 예산 ceiling·resume·schema·pipeline 내장.
3. **이중 축 패턴 라이브러리 — 단 입증된 2~3 조합만 ship** — 토폴로지 × **decision mechanism**(single/majority-vote/debate-with-judge/reflect-then-revise). 30셀 손채움(과설계) 금지. 나머지는 run-log 데이터로 학습.
4. **비용/모델 티어 거버넌스 (eval 비용 포함)** — `model:opus` 전역 금지. 역할→티어 필수 `model:` 필드. TeamCreate/Workflow 전 **팀+eval 비용 밴드 산정·승인**. 서브에이전트는 `budget.total`로 하드 ceiling.
5. **lift 게이트 + 헤드투헤드 벤치마크가 빌드 게이트** — (a) 스킬단위: with-skill(sonnet) vs baseline(haiku) **단일 숫자** lift, 미달 시 등록거부. (b) 메타스킬단위: CYS vs **원본 harness** vs no-harness, ≥3 도메인, **승리 조건 숫자 명시**. → thesis를 falsifiable하게.

### D-3. 모델 티어 디폴트 (wshobson 차용)
`gather/extract/format/QA-scan → haiku` · `voters/debaters → sonnet` · `synthesis/judge/reviewer/architecture → opus`

### D-4. Decision Mechanism 4종
| 메커니즘 | 파라미터 | 언제 | 비용 |
|---|---|---|---|
| `single` | — | 객관·저위험 | 디폴트, 최저 |
| `majority-vote-of-N` | n, quorum, tie-break | 정답 있으나 noisy(추출/분류) | voters=haiku, 집계=결정론 |
| `debate-with-judge` | n, max_rounds, judge | 논쟁·주관(전략/설계) | debaters=sonnet, judge=opus |
| `reflect-then-revise` | max_rounds, critic | 단일 산출물 반복개선 | critic=opus, reviser=sonnet |

**출시 조합 (2~3개만):** ① Pipeline+reflect-then-revise(문서/리서치) ② Dispatch(static)+majority-vote(추출/분류) ③ (선택) Producer-Reviewer+debate-with-judge(설계)

### D-5. 팀 SIZE 산정 (원본·초안 공통 누락 보강)
```
n_agents = min(distinct_expertise_domains, MAX_FANOUT=5)   # 5 = 1 integrator 합성 상한(가설값)
초과 시: "fan-out 폭이 integrator 합성능력 초과 → 2단계 합성/도메인 묶기 권장" 경고
voters N = 3 또는 5 (홀수, MAX_VOTERS=5)
```

### D-6. 생성 하네스 디스크 레이아웃 (아티팩트 4종)
```
<domain-harness>/                 # ← 그 자체가 git repo (rollback substrate, .claude/ commit)
├── .claude/
│   ├── skills/<domain>-orchestrator/SKILL.md   # 계약의 사람용 뷰
│   ├── agents/{role}.md                         # model: 티어 + 권한 스코프
│   └── settings.json                            # hooks (write-lock, active-team check, SubagentStop 토큰로깅)
├── .harness/
│   ├── workflow.js         # Mode A: emit된 Workflow 스크립트 (실행 런타임)
│   ├── graph.json          # Mode B: 오케스트레이터가 따를 계약 (결정론 아님)
│   ├── MANIFEST.json       # artifact→agent→input-hash (드리프트/evolve substrate)
│   ├── harness.lock        # write-ownership lock table
│   └── evals/<skill>.json  # lift 게이트 fixture (단일 숫자)
├── validate_harness.py
└── .github/workflows/validate.yml
```

### D-7. 무엇을 빌려오고 무엇을 제외하는가
**빌려옴:** LangGraph state+checkpoint 개념 / CrewAI Crews-Flows split & per-agent model / AutoGen progress-ledger / OpenAI typed-handoff+guardrail / wshobson 티어 테이블 / OTel **소비** / MetaGPT AFlow(M3+ learned selection)
**제외(over-claim·실현불가):** LangGraph durable interrupt 동치(플랫폼에 없음) / A2A agent card(로컬 세션 못 벗어남) / 직접 OTel-emit(네이티브와 중복) / release-please·ADR per-harness(메타-repo 공개시만) / 라이브 abort hook·no-progress watchdog(플랫폼 제약)

### D-8. 로드맵 (사용자 결정 4건 반영 — 2026-05-29 확정)
> 확정: ① **Mode A(Workflow 결정론) = 디폴트 스파인**, 팀은 comms 필수 시 fallback / ② M0 **넓게(헤드투헤드까지)** / ③ **개인·내부용** → OSS 툴체인 전면 제거 / ④ 기존 ~30 AgenticWorkflow **전면 마이그레이션**
> 마스터 판단: "넓은 M0 + 30개 전면 마이그레이션"을 한 마일스톤에 넣을 수 없음 → **마이그레이션은 import 어댑터 검증 후 M2 본작업**. M0은 "넓되 deep-research 1개로 헤드투헤드 증명"으로 경계.

- **M0 (3~4주) — 넓은 MVP: 검증기 + Workflow 런타임 + warrant + 헤드투헤드 증명:**
  Phase -1 warrant 게이트 + 팀+eval 비용밴드 승인 / 필수 `model:` 티어 + 디폴트 매핑 / `validate_harness.py`(정적 린터) + `validate.yml` / 팀SIZE 캡(MAX_FANOUT=5) / settings.json hooks(write-lock·active-team·SubagentStop 토큰로깅) / **Mode A: Workflow `.js` emit 엔진(budget ceiling·resumeFromRunId·schema·pipeline/parallel)** / **deep-research를 git repo로 dogfood + 헤드투헤드 1도메인 증명**(C1 원본 vs C2 CYS vs C3 no-harness).
  - 성공기준: (1) Workflow `.js`가 budget.total 도달 시 정지 + resumeФromRunId로 재개 / (2) 망가뜨린 agent참조에서 validate 빌드실패 / (3) write-lock hook이 비-owner Write 거부 / (4) warrant가 단순작업을 "no harness" 분류 / (5) **deep-research 헤드투헤드에서 C2가 C1·C3 대비 측정된 우위(또는 미달 시 정직 보고)**.
- **M1 (3~4주) — Decision-Mechanism + lift게이트 + 헤드투헤드 풀스위트:** 4 메커니즘 파라미터화 + 출시조합 2~3 + explainable 선택·override / 스킬단위 lift게이트(haiku baseline 단일숫자 mandatory, n-runs/per-lang opt-in) / **헤드투헤드 3도메인 + 승리조건 숫자 확정**(deep-research/분류추출/설계결정) / 도메인무관 QA(finding triage + 재현의무).
- **M2 (4~6주) — 생애주기·진화 + 기존 30 프로젝트 전면 마이그레이션:**
  MANIFEST 기반 프로그램 Phase-0 audit + `evolve`(hash diff 부분재실행) / 생성 하네스 git-init+SemVer+rollback / **`harness import <path>` 어댑터로 기존 ~30 AgenticWorkflow + deep-research 전면 역생성**(graph.json+MANIFEST+검증기+티어 거버넌스 편입) / 단일 SOT manifest에서 README(EN/KO)·install·trigger 생성 + dead-link 게이트 / claim규율(미백업 수치 emit 금지, 5줄 규칙).
  - 성공기준: 30개 중 batch 마이그레이션 후 전부 `validate_harness.py` 통과 + 각 헤드투헤드에서 import 전후 비퇴행(no-regression).
- **(연기 — 수요 입증 시):** Expert Pool·Team-Relay·best-of-N·weighted-ensemble / AFlow-lite(데이터 기반 패턴 학습) / Dynamic Workflows 컴파일 타겟(안정 surface 공개 시).
- **(전면 제거 — 개인/내부용 결정):** release-please·changesets·commitlint·ADR·CODE_OF_CONDUCT·JA 문서·A2A·직접 OTel-emit·CI claim-linter 서브시스템. (공개 출시로 선회 시에만 재도입.)

### D-9. 헤드투헤드 벤치마크 프로토콜 (thesis 검증 — 초안 최대 누락)
- **3-way:** C1=원본 harness 출력 / C2=CYS 출력 / C3=no-harness 단일에이전트
- **도메인 ≥3:** deep-research(pipeline+reflect) / 분류·추출(dispatch+vote) / 설계결정(producer-reviewer+debate)
- **측정:** 도메인별 gold-labeled discriminating assertion / 조건당 n=3~5 median pass-rate+variance / grader gold-보정·논쟁건 2-grader / blind(라벨strip+순서랜덤, seed기록) / provenance 스탬프
- **승리조건(가설값, M1 데이터로 확정):** C2 median ≥ C1+15%p AND ≥ C3+15%p, ≥2/3 도메인. 비용정규화 보고. **미달 도메인은 정직 보고** ← 원본과의 결정적 차이.
- **주기:** 스킬마다가 아니라 **릴리스마다 1회**.

---

## Part E. 리스크 & 결정 필요사항

### 리스크
1. **hook 거버넌스 한계(잔존):** write-lock은 `PreToolUse`로 강제하나 **Bash 우회 편집은 못 막음**. 완화: write_paths 스코프 + Bash 권한제한 + fan-in merge-integrity audit(사후).
2. **팀 모드 비결정론(불변 제약):** graph.json은 계약일 뿐 LLM 이탈 가능. 완화: 결정론 필수 시 Mode A(Workflow)로 유도. 플랫폼 제약이지 결함 아님.
3. **검증기·게이트가 생성비용 증가:** 완화: lift는 haiku cheap단일숫자, n-runs opt-in, validator 정적무료, 헤드투헤드는 릴리스당 1회.
4. **decision-mechanism 비용 곱(majority N배):** 완화: voters=haiku 강제 + 비용밴드 사전승인 + 출시조합 2~3 제한.
5. **self-measured 신뢰성(잔존):** 헤드투헤드(원본 measured baseline 대조)로 완화하나 third-party replication 없이는 최종적으로 자기측정 — 미달 도메인 정직보고로 신뢰확보.

### 결정 완료 (2026-05-29 사용자 확정)
1. ✅ **디폴트 실행 모드** = **Mode A(Workflow 결정론)**. 팀은 comms 필수 시 fallback.
2. ✅ **M0 범위** = **넓게(헤드투헤드까지)**. 단 마스터 판단으로 마이그레이션은 M2로 분리.
3. ✅ **기존 ~30 AgenticWorkflow** = **전면 마이그레이션**(M2 `harness import` 어댑터로 batch).
4. ✅ **공개 여부** = **개인/내부용** → OSS 거버넌스 툴체인 전면 제거(D-8 참조).

### 잔여 결정 (구현 중 데이터로 확정)
5. **가설 숫자** — lift 0.2 / 헤드투헤드 +15%p / MAX_FANOUT 5 / max_rounds 2~3을 M0/M1에서 초기 가설로 두고 누적 run-log로 분기마다 재보정.

---

## 부록. 원본의 "정직했던 점" (균형)
- +60% 주장에 항상 "n=15, author-measured, third-party replications pending" 병기
- coexistence 표로 경쟁 repo(Archon/meta-harness/ECC/wshobson/LangGraph) 명시 비교
- dogfooding이 실제로 자기 결함(plugin.json 충돌)을 잡아냄 → 시스템이 무가치하지 않음을 입증
이 정직성·자기적용 자세는 CYS도 계승하되, **prose 약속을 머신체크 가능한 게이트로 승격**하는 것이 핵심 차별이다.
