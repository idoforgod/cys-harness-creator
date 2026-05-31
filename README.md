# CYS Harness Creator

**도메인 한 문장을, 실제로 발화하는 풀스택 Claude Code 프리미티브 하네스로 컴파일하는 메타스킬 팩토리.**

`/harness-creator <도메인 한 문장>` 한 번으로 검증된·비용통제된·재개가능한 하네스(orchestrator SKILL + `.claude/agents` + Sub-agents + Agent Teams + Hooks + `.claude/skills` + 상속 게놈 + 장기기억 + git repo)가 산출됩니다. 개인·내부용.

이 팩토리는 [AgenticWorkflow](https://github.com/idoforgod/AgenticWorkflow)의 **만능줄기세포(Pluripotent Stem Cell) 게놈에서 분화한 세포**입니다. 부모의 전체 DNA(절대기준·품질 게이트·안전·기억 체계)를 그대로 물려받되, 그 *prose 영혼*을 CYS의 *머신체크 게이트*로 승격합니다 — **"rules-as-essays → rules-as-assertions".**

그리고 줄기세포의 분화처럼 — **이 팩토리가 낳는 모든 하네스는 부모의 전체 게놈을 참조가 아니라 그대로 임베드합니다.** `validate_harness.py`가 상속을 정적으로 강제하므로, 게놈을 빠뜨린 하네스는 빌드되지 않습니다. 상세: [`CONSTITUTION.md`](CONSTITUTION.md).

> **절대규칙(A1):** 산출 하네스의 *실행*은 100% Claude Code 프리미티브(Agent / TeamCreate / SendMessage / TaskCreate)다. 결정론 Python(hook·검증기·메모리 스크립트)은 실행이 아니라 가드레일(발화·강제·기억)이다. 제거 시 도메인의 *답*이 바뀌면 불법, 차단·저장·측정·파싱만 하면 합법. **Mode-A `workflow.js`는 제품에서 은퇴** — 공장 내부 측정 도구로만 생존한다.

## 프로젝트 목표

```
입력:  도메인 한 문장              예) "경쟁사 인텔리전스 자동 수집·요약"
  │
  ▼   4-스테이지 컴파일 (Research → Planning → Implementation → Evolution)
  │   graph.json (불변 계약 · 중간 산출물) — 머신체크 빌드 게이트 통과
  ▼
출력:  실제로 발화하는 풀스택 하네스   orchestrator SKILL + agents + hooks + 게놈 + 메모리 + git repo
```

`graph.json`을 만드는 것은 중간 산출물입니다. **`cd <harness> && claude`로 열면 그 세션의 hook이 발화하고 오케스트레이터가 Claude 프리미티브로 그래프를 실행하는 것** — 그것이 최종 목표입니다.

## 워크플로우 구조

팩토리는 AgenticWorkflow의 3단계(Research → Planning → Implementation)를 상속하되, 그 앞에 **PRE 게이트**를, 뒤에 **Evolution 단계**를 더해 4-스테이지로 운영합니다. 각 단계는 CYS 머신체크 게이트로 강제됩니다.

| 단계 | 이름 | 핵심 | 사람 게이트 |
|------|------|------|:----------:|
| **PRE** | Warrant 게이트 | 5 술어 → `answer-directly`/`single-agent`(종료) 또는 `build-harness(topology, mechanism, n_agents)` | — |
| **1** | Research | R1 상태감사(드리프트) · R2 도메인 분해 · R3 토폴로지+모드 · R4 모델티어 | — |
| **2** | Planning | P1 `graph.json` 저작(단일 진실원천) · P2 스키마 · P3 팀 아키텍처 · P4 비용밴드 | **P5 승인** |
| **3** | Implementation | I1 agents · I2 도메인 스킬 · I3 오케스트레이터 emit · I4 게놈 발화 · I5 빌드 게이트 · I6 측정 | — |
| **4** | Evolution | E1 git · E2 head-to-head · E3–E6 진화(피드백 라우팅 + change-history + proactive) | — |

**Implementation은 P5 사람 승인 전 실행 금지.** 진화로 라우팅된 수정은 해당 Implementation 단계로 재진입해 **`validate` 재통과**가 강제됩니다(진화가 계약을 퇴행시키지 못함).

## 프로젝트 구조

```
cys-harness-creator/
├── README.md                    # 이 파일 — 프로젝트 개요
├── CONSTITUTION.md              # 불변 절대기준 (AC-1/2/3) — 모든 산출 하네스가 임베드 상속
├── constants.json               # 튜너블 상수 SoT (티어비용·MAX_FANOUT·밴드·15pp 마진)
├── graph.schema.json            # graph.json 계약 스키마 (7 topology × 4 mechanism)
├── model-tier-policy.js         # 역할 → 모델 티어 SoT
├── install.sh                   # /harness-creator 스킬 전역 설치 (멀티 프로필)
├── Makefile                     # test / eval 타깃
│
├── ─── 팩토리 도구 (제품 emit 파이프라인) ───────────────────
├── warrant.py                   # PRE: 분류 게이트 + team-aware 비용밴드
├── audit_harness.py             # R1: 상태감사 (new/extend/maintain + 드리프트)
├── emit_orchestrator.py         # I3: graph.json → 오케스트레이터 SKILL + agents + 게놈 + 메모리
├── emit_domain_skill.py         # I2: 하이브리드 도메인 스킬 (skill 모드 노드만)
├── inherit_genome.py            # I4: 게놈 전수 + .harness/memory/ 시드
├── validate_harness.py          # I5: 머신체크 빌드 게이트 (exit 0/1/2)
├── lift_gate.py                 # I6: 스킬 lift 측정 게이트 (baseline 미달 시 출하 거부)
├── eval_topology.py             # E2: 8 use case parity matcher
├── h2h_aggregate.py             # E2: 헤드투헤드 집계 (median + 15pp 마진)
├── evolve_harness.py            # E3-E6: 진화 (피드백 라우팅 + change-history + proactive)
├── emit_workflow.py             # 공장내부 측정 전용 (제품 emit 아님)
├── h2h_suite.workflow.js        # 공장내부 측정 전용 (블라인드 h2h 스위트)
│
├── skills/harness-creator/      # 메타스킬 — /harness-creator 진입점
│   ├── SKILL.md                 # 진입점 (WHY + 4-스테이지 워크플로우 + 산출 체크리스트)
│   └── references/              # 8-파일 맵 (필요 시 Read)
│       ├── IMPLEMENTATION-STATUS.md     # 먼저 읽기 — 구현 현황 (모든 서술에 우선)
│       ├── architecture-patterns.md     # 7 토폴로지 × 4 메커니즘 + 8 use case
│       ├── graph-and-orchestration.md   # graph.json 저작 + 실제 team emit
│       ├── skill-and-agent-authoring.md # agent .md + 하이브리드 author-or-inline
│       ├── genome-and-runtime.md        # 게놈 발화 방식 + 2 설치모드
│       ├── evolution-and-memory.md      # Phase-7 진화 + 2-tier 메모리
│       ├── testing-and-measurement.md   # validate 카탈로그 + lift + h2h
│       └── qa-guide.md                  # QA 경계교차 + 7 버그패턴
│
├── genome/                      # AgenticWorkflow 부모 게놈 (모든 하네스에 이식)
│   ├── CLAUDE.md · AGENTS.md · GEMINI.md · soul.md · DECISION-LOG.md
│   ├── .claude/
│   │   ├── settings.json        # Hook 설정
│   │   ├── agents/              # reviewer · fact-checker · translator (적대적 리뷰 DNA)
│   │   ├── commands/            # 6 슬래시 명령어
│   │   ├── hooks/scripts/       # Context Preservation + 검증 + 보안 hook
│   │   └── skills/              # workflow-generator · spec-grounded-workflow · doctoral-writing
│   ├── docs/{protocols,guides,adr}/   # 상세 프로토콜·가이드·ADR
│   ├── prompt-runner/           # 보관 capability (산출 하네스의 실행 경로 아님)
│   ├── prompt/ · translations/glossary.yaml
│   └── soul.md                  # DNA 유전 정의 (CONSTITUTION의 출처)
│
├── templates/
│   ├── hooks/                   # 산출 하네스에 배선되는 런타임 발화 hook
│   │   ├── qa_gate_runner.py    # L0-L2 게이트 발화 (gate_or_block 경유)
│   │   ├── gate_or_block.py     # 게이트 프리미티브 (exit-2 차단)
│   │   ├── budget_block.py      # spawn ceiling 발화 (PreToolUse Agent|Task|TeamCreate)
│   │   ├── spawn_counter.py     # budget.spawns_used 증분
│   │   ├── sot_init.py          # state.yaml 시드 (SessionStart)
│   │   └── cys_log_tokens.py    # 토큰 tally (advisory)
│   └── inherited-dna.md.tmpl    # harness.md 게놈 가시화 템플릿
│
├── lib/
│   ├── toposort.py              # 결정론 위상정렬
│   └── atomic_write.py          # temp→rename 원자적 쓰기
│
├── examples/                    # 4 작동 예제 하네스 (team 모드, validate 0/0)
│   ├── deep-research/           # pipeline — gather→fetch→verify→synthesize
│   ├── competitor-watch/        # 경쟁사 모니터링
│   ├── design-decision/         # producer-reviewer + L2 적대적 리뷰
│   └── ticket-triage/           # 티켓 분류·우선순위·라우팅
│
├── design/                      # 설계·전략 문서
│   ├── STRATEGY-AND-DESIGN.md   # 설계 전모 (잠금결정 · 백로그)
│   ├── compare-vs-idoforgod-harness.md
│   └── … (philosophy · blueprint · pivot)
│
├── tests/test_factory.py        # 팩토리 자기테스트 (125 tests)
└── .claude-plugin/              # plugin.json · marketplace.json (/harness-creator 플러그인)
```

## 메타스킬

팩토리의 진입점은 단 하나의 스킬입니다.

| 스킬 | 설명 |
|------|------|
| **harness-creator** | 도메인 한 문장을 머신체크된 `graph.json`에서 풀스택 Claude 프리미티브 하네스로 emit하는 메타스킬. `/harness-creator <도메인 한 문장>` 또는 "하네스 만들어줘/구성/설계·점검·감사·확장·진화·동기화" 요청 시 발동. SKILL.md(WHY) + references/(WHAT·HOW·VERIFY). |

## 팩토리 도구 (제품 emit 경로)

`graph.json`을 단일 진실원천으로 삼아 하네스를 컴파일하는 결정론 도구들입니다. 모두 `python3 "$TOOLS_ROOT"/<tool>.py`로 호출합니다.

| 단계 | 도구 | 역할 |
|------|------|------|
| PRE | `warrant.py` | 분류 게이트(필요한가?) + team-aware 토큰 비용밴드 |
| R1 | `audit_harness.py` | 상태감사 — new/extend/maintain 분기 + 디스크↔graph 드리프트 set-diff |
| I3 | `emit_orchestrator.py` | `graph.json` → 오케스트레이터 SKILL + agents + 게놈전수 + 메모리 store (`--in-project` 오버레이 지원). `emit_domain_skill.py`·`inherit_genome.py` 자동 호출 |
| I2 | `emit_domain_skill.py` | `skill_authoring.mode='skill'` 노드만 도메인 스킬(how) 저작 (하이브리드) |
| I4 | `inherit_genome.py` | 게놈 + `.harness/memory/`(Tier II) 전수 |
| I5 | `validate_harness.py` | 머신체크 빌드 게이트 — error 시 생성 중단·보고 (exit 0/1/2) |
| I6/E2 | `lift_gate.py` · `h2h_aggregate.py` · `eval_topology.py` | lift 게이트 · 헤드투헤드(median + 15pp 마진) · 8 use case parity |
| E3-E6 | `evolve_harness.py` | 진화 — 피드백 라우팅 + `change-history.jsonl` + `--proactive` |
| SoT | `model-tier-policy.js` · `graph.schema.json` · `constants.json` · `lib/toposort.py` | role→tier 정책 · 계약 스키마 · 튜너블 상수 · 결정론 토소트 |
| 측정 전용 | `emit_workflow.py` · `h2h_suite.workflow.js` | **공장 내부 측정 전용**(제품 emit 아님) |

> `emit_orchestrator.py`가 도메인 스킬·게놈 전수를 자동 호출합니다. **`workflow.js`는 emit되지 않습니다**(은퇴).

## 산출 하네스 — 6종 프리미티브 (A2 floor)

모든 빌드 하네스는 6종 Claude Code 프리미티브를 **전부** 인스턴스화해야 합니다. 하나라도 빠지면 `ALL_PRIMITIVES_PRESENT`가 빌드를 실패시킵니다. 따라서 `execution_mode`는 `team` 또는 `hybrid`이며(pure-`agent`는 TeamCreate가 없어 실패), 실험 플래그가 없는 환경에서 팀은 sub-agent로 graceful-degrade합니다.

| 프리미티브 | 역할 | 산출물 |
|-----------|------|--------|
| **Orchestrator SKILL** | 그래프 실행 진입점(WHO×HOW 조율) | `.claude/skills/<domain>-orchestrator/SKILL.md` |
| **`.claude/agents/`** | 노드별 전문 에이전트(model + rationale + least-priv tools) | `<agent>.md` |
| **Sub-agents (Agent)** | 위임 실행 단위 | 오케스트레이터의 `Agent(...)` 호출 |
| **Agent Teams** | `TeamCreate / TaskCreate(deps) / SendMessage / TeamDelete` | `team` 모드 emit |
| **Hooks** | 런타임 발화 가드레일(settings.json 배선) | `qa_gate_runner` · `budget_block` · `sot_init` 등 |
| **`.claude/skills/`** | 하이브리드 도메인 스킬(how) | `skill_authoring=skill` 노드 |

**토폴로지(7)**: `pipeline` · `dispatch` · `fan-out-fan-in` · `producer-reviewer` · `supervisor` · `expert-pool` · `hierarchical`
**결정 메커니즘(4)**: `single` · `majority-vote` · `debate-with-judge` · `reflect-then-revise`

## 머신체크 빌드 게이트 (validate_harness.py)

idoforgod의 advisory prose와 달리, CYS의 규칙은 **정적으로 강제**됩니다. `validate_harness.py`(~36 머신체크 코드)가 위반 시 빌드를 실패시키고, 런타임 규칙은 hook으로 *발화*합니다. 설치 모드(`self-contained`/`in-project`)는 `.harness/GENOME.json`의 `install_mode`로 자동 분기됩니다.

| 게이트 | 대상 | 위반 시 |
|--------|------|---------|
| `ALL_PRIMITIVES_PRESENT` | 6종 프리미티브 전부 인스턴스화 | error |
| `TOPOLOGY_STRUCTURE` | 토폴로지↔구조 정합(fan-out-fan-in≥2 producer→sink, hierarchical≥3노드) | error |
| `TIER_OVERSPEND` | model:opus 전역 금지(역할→티어) | error |
| `GRAPH_PROVENANCE` | `graph.lock`(sha256) — 사후 손편집 감지 | warn |
| `CONTEXT_PRESERVATION_FIRSTCLASS` · `MEMORY_STORE_INIT` | 2-tier 장기기억 emit·시드 | error |
| `REVIEW_AGENT_PRESENT` · `PRODUCER_REVIEWER_REVIEW` | review 노드의 reviewer/fact-checker 존재 | error |
| `LIFT_REFUSED` | 스킬이 baseline에 패배 시 출하 거부 | hard error |
| `LIFT_UNMEASURED` | lift 미측정 | warn(정책 전환 가능) |
| `MEASUREMENT_DRIFT` · `STALE_BENCHMARK` | 정직성 — 죽은 벤치마크 수치 잔존 | error |

검증은 빌드 게이트(`validate_harness.py`)의 일부이며, 산출 하네스 *내부*에서는 런타임에 L0–L2 4계층 품질 게이트가 hook으로 발화합니다 — L0(Anti-Skip) + L1(Verification, **필수·fail-closed**) + L1.5(pACS) + L2(적대적 리뷰, fire-on-presence).

## 상속 게놈 — 런타임 발화 hook

산출 하네스는 부모 게놈의 hook을 자식 `settings.json`에 배선받아, **실세션에서** 가드레일이 *발화*합니다(advisory 아님). CYS 발화 hook + 부모 게놈 hook이 함께 작동합니다.

| Hook | 트리거 | 발화 |
|------|--------|------|
| `sot_init.py` | SessionStart | `state.yaml` 시드(graph에서 max_spawns) |
| `spawn_counter.py` | PostToolUse | `budget.spawns_used` 증분 |
| `budget_block.py` | PreToolUse (Agent\|Task\|TeamCreate) | spawn ceiling 초과 시 **exit-2 차단** |
| `qa_gate_runner.py` | (게이트) | L0-L2를 `gate_or_block`로 발화 — 누락 산출물 시 **exit-2** |
| `block_destructive_commands.py` | PreToolUse (Bash) | `rm -rf /` · `git reset --hard` 등 차단 (exit-2) |
| `output_secret_filter.py` | PostToolUse (Bash\|Read) | 시크릿 탐지 (3-tier 추출, 25+ 패턴, 2-패스) |
| `security_sensitive_file_guard.py` | PostToolUse (Edit\|Write) | `.env`·`*.pem` 등 보안 민감 파일 경고 |
| `restore_context.py` / `save_context.py` | SessionStart / PreCompact·SessionEnd | 컨텍스트 복원 / 스냅샷 저장 |
| `lint_guard.py` / `spell_guard.py` | PostToolUse (Edit\|Write) | 저장 직후 ruff 코드 린트 + 한국어 맞춤법 — 기계적 위반 자동수정, 의미 위반은 **exit-2** 자가교정 (`.lint-guard` 토글) |
| `precommit_gate.py` | PreToolUse (Bash) | `git commit` 인터셉트 — ruff(스코프)+테스트 미통과 시 **exit-2** "잠깐, 이것부터" |

상세: `references/genome-and-runtime.md`.

## 2-tier 장기기억

세션을 넘어 지식을 축적·활용하는 메커니즘입니다. 이론적 토대는 게놈의 RLM(Recursive Language Models) 논문에 있습니다.

- **Tier I — Context Preservation:** 컨텍스트 토큰 초과·`/clear`·압축 시 작업 내역 상실 방지. 스냅샷 + `[CONTEXT RECOVERY]` 복원 + RLM knowledge-index. (`.claude/context-snapshots/`)
- **Tier II — RLM 교차-실행 메모리:** `.harness/memory/`(`archive.manifest.json`·`domain-knowledge.yaml`·`runs/index.jsonl`·`risk/decisions.jsonl`)에 도메인 지식을 idempotent 누적. 재emit이 기존 run을 파괴하지 않음.

회상·기록·판단은 **프리미티브/agent의 도메인 작업**(A1 준수)이며, Python은 시드·인덱스·파싱만 담당합니다. 상세: `references/evolution-and-memory.md`.

## 비용 거버넌스

"품질 최우선"이 "무한 비용"은 아닙니다. 비용은 *무시*하되 가시화·강제합니다.

- **사전 가시화** — `warrant.py`가 team-aware 토큰 비용밴드를 산정 → **P5 사람 승인** 게이트.
- **런타임 강제** — `budget_block.py`(PreToolUse `Agent|Task|TeamCreate`)가 spawn-count/fanout ceiling을 **exit-2**로 강제. (per-call 토큰 계측은 호스트가 신뢰성 있게 노출하지 않으므로 토큰 tally는 advisory.)
- **티어 정책** — `model-tier-policy.js`가 품질 임계 노드에 최고티어(opus)를 배정. `n_agents ≤ MAX_FANOUT(5)`, 약한 다수 대신 강한 소수.

## 측정 (정직, stamped)

blind 헤드투헤드 — C2(CYS 하네스) vs C3(no-harness opus), 8-assertion scorecard, median + 15pp 마진:

| 도메인 | n | 결과 |
|--------|---|------|
| deep-research | 5 | **+12.5pp `INCONCLUSIVE`** (CYS 우세, 마진 미달) |
| verification-heavy | 5 | **0.0pp `INCONCLUSIVE`** (천장 동률, 둘 다 8/8) |

> **정직한 결론:** 현대 opus single-pass가 객관적 scorecard에서 이미 천장이라 하네스가 **마진으로 이기는 것은 구조적으로 불가**합니다. 더 많은 도메인을 뒤져 ≥15pp를 낚는 것은 벤치마크 게이밍이므로 하지 않습니다(+37.5pp 교훈). 하네스의 가치는 scorecard 승리가 아니라 **parity(목표 충족) + 결정론적 인프라**(DNA 발화·비용 거버넌스·머신체크 계약)에 있습니다.

## 절대기준 (CONSTITUTION)

출처 DNA는 AgenticWorkflow `soul.md`의 만능줄기세포 게놈입니다. 원본의 *prose 영혼*을 CYS의 *머신체크 게이트*로 승격하며, 모든 생성 하네스가 임베드 상속하고 `validate_harness.py`가 강제합니다.

1. **AC-1 — Quality > Everything** — 속도·비용·작업량·시간제약은 의사결정 기준에서 제외. 유일한 기준은 최종 산출물 품질. 단계를 줄여 빨리 끝내기보다 단계를 늘려 품질을 높이는 경로를 선택.
2. **AC-2 — Single-File SOT + Single-Writer** — 공유 상태는 단일 진실원천(`.harness/state.yaml`)에 집중, 쓰기는 오케스트레이터(Team Lead) 단독. 병렬 에이전트는 read-only이거나 자신의 `output-*`만 쓴다. 모든 SOT 쓰기는 `lib/atomic_write.py`(temp→rename) 경유.
3. **AC-3 — Code Change Protocol** — 코드 변경 전 ① 의도 명확화 → ② 영향범위 분석 → ③ 변경 설계. 분석 깊이는 변경 규모에 비례(proportionality), 변경된 모든 줄은 작업지시로 추적 가능(외과적 변경).

상세: [`CONSTITUTION.md`](CONSTITUTION.md).

## 예제 (examples/)

4개의 작동 예제 하네스 — 모두 `team` 모드이며 `validate_harness.py` **PASS(0/0)**.

| 예제 | 토폴로지 | 노드 |
|------|----------|------|
| **deep-research** | pipeline | gather → fetch → verify(reflect-then-revise) → synthesize |
| **competitor-watch** | pipeline | 경쟁사 인텔리전스 수집·요약 |
| **design-decision** | producer-reviewer | 설계안 생성 + L2 적대적 리뷰 |
| **ticket-triage** | dispatch | 분류 · 우선순위 · 라우팅 |

각 예제에는 `.harness/graph.json`(불변 계약) + `harness.md`(게놈 가시화) + `.claude/`(런타임 DNA) + `schemas/`가 포함됩니다.

## 빠른 시작

```bash
# 1) /harness-creator 스킬 전역 설치 (도구는 이 디렉토리에 그대로 둠)
./install.sh                      # 또는: ./install.sh ~/.claude ~/.claude-cysinsight ~/.claude-cysfuturist

# 2) 빠른 검증 (프리미티브 경로)
TR=/Users/cys/Desktop/CYSjavis/cys-harness-creator
python3 "$TR"/warrant.py --graph examples/deep-research/.harness/graph.json   # 비용밴드 (→ 사람 승인)
python3 "$TR"/emit_orchestrator.py examples/deep-research                     # graph.json → 오케스트레이터 + agents + 게놈
python3 "$TR"/validate_harness.py  examples/deep-research                     # PASS (exit 0)
python3 -m pytest tests/test_factory.py -q                                    # 125 factory tests

# in-project 오버레이 설치:  python3 "$TR"/emit_orchestrator.py <host-project> --in-project
```

**실행 핸드오프:** 산출 후 하네스를 *실행*하려면 `cd <harness> && claude`로 **새 세션**을 열어야 그 세션의 `settings.json` hook이 발화합니다(공장 세션이 아님).

## 현재 상태

- **M0–M8 (완료)** — 프리미티브-위임 모순 봉쇄 · 4계층 QA + Context Preservation 일급화 · all-6 프리미티브 floor + 7 토폴로지 · 하이브리드 도메인 스킬 · Phase-0 감사 · Phase-7 진화 · RLM 교차-실행 메모리 · 8 use case parity · 정직성 가드
- **P1.2** in-project 오버레이 설치(호스트 보존) · **P1.3** lift 빌드 배선 · **P1.4** h2h StructuredOutput 견고화
- **P2** 라이브 DNA 발화 end-to-end 증명 + 7-dim 적대적 전수감사(18 confirmed) 후 P0×3·robustness×4·P1×4·P2 보강
- **자동 교정 루프** — 린터(`lint_guard`)+맞춤법(`spell_guard`)+프리커밋(`precommit_gate`)이 `exit-2 + stderr`로 Claude 자가수정 유도(팩토리 자기적용 + 게놈 전수, `.lint-guard` 토글)
- **3층위 장기기억 self-hosting** — 회상→주입→릴레이→증분의 4 게이트(`MEMORY_RECALL_WIRED`·`AGENT_MEMORY_CONTRACT`·`MEMORY_RELAY_WIRED`·`MEMORY_INCREMENTAL_WIRED`)가 메모리 도관을 wiring으로 강제; 팩토리·빌드·산출 하네스 3층위에서 단일 메커니즘 dogfood
- **125 factory tests green · 4 예제 validate 0/0**

## 알려진 통합 경계

커스텀 `agentType`(researcher 등)는 **하네스가 활성 Claude Code 세션의 CWD일 때** `.claude/agents/`에서 해석됩니다. 따라서 라이브 실행은 `cd <harness> && claude`로 새 세션을 열어 수행합니다(그 세션의 `settings.json` hook이 발화 — 공장 세션이 아님).

## 문서 읽기 순서

| 순서 | 문서 | 목적 |
|------|------|------|
| 1 | **README.md** (이 파일) | 프로젝트 개요 파악 |
| 1.5 | [`CONSTITUTION.md`](CONSTITUTION.md) | 불변 절대기준 — 모든 하네스가 임베드 상속 |
| 2 | `skills/harness-creator/references/IMPLEMENTATION-STATUS.md` | **모든 서술에 우선** — 실구현/연기/폐기 현황 |
| 3 | `skills/harness-creator/SKILL.md` | 메타스킬 진입점 — 4-스테이지 워크플로우 |
| 4 | `design/STRATEGY-AND-DESIGN.md` | 설계 전모 — 잠금결정·백로그 |
| 5 | `skills/harness-creator/references/*.md` | 특정 주제(아키텍처·graph·게놈·진화·측정·QA) 심화 |

> **`IMPLEMENTATION-STATUS.md`가 다른 모든 서술(이 README 포함)에 우선합니다.** reference가 무엇을 설명하든, 실제로 emit/validate에 구현됐는지는 그 문서로 확정됩니다.
