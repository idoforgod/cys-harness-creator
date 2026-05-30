---
name: harness-creator
description: "도메인 한 문장을 검증된·비용통제된·재개가능한 에이전트 하네스로 변환하는 메타스킬(CYS Harness Creator). '하네스 만들어줘', '하네스 구성', '에이전트 팀 설계', '이 도메인 자동화 하네스', 하네스 점검·확장·진화 요청 시 사용. 후속: 하네스 재실행, 수정, 보완, 부분 재생성, 이전 결과 개선 요청 시에도 반드시 이 스킬을 사용."
---

# Harness Creator (CYS) — 메타스킬

도메인 요청 → `graph.json`(불변 계약) + agent 파일(런타임 바인딩 frontmatter) + schema + emit된 **오케스트레이터 SKILL**(Claude Code 프리미티브 런타임) + 게놈 전수(active) + 검증기 + git repo.
원본 idoforgod/harness 대비 우위: **prose 규칙이 아니라 머신체크 게이트 + 실재 실행 런타임 + 비용 거버넌스 + 헤드투헤드 측정 + AWF 게놈이 실제로 발화.**

핵심 원칙:
1. **산출 하네스는 Claude Code 프리미티브(Agent/TeamCreate/SendMessage)에 실행을 위임한다(디폴트).** 이 기질에서만 상속된 AWF 게놈(lifecycle hook·L0-L2 게이트·SOT·적대적 리뷰)이 발화하고, 커스텀 `.claude/agents`의 model·tools가 런타임 강제된다. `execution_mode`: `agent`(순차 sub-spawn, 디폴트) / `team`(TeamCreate, P5 입증 후) / `hybrid`. **결정론 byte-replay가 필수인 드문 경우에만** `workflow`(Mode A `workflow.js`).
2. **모든 규칙은 강제된다** — `validate_harness.py`가 위반 시 생성 실패(빌드타임 머신체크 유지). 런타임 게이트는 `gate_or_block.py`가 advisory validator를 exit-2 인터록으로 승격.
3. **비용은 사전 승인 + 런타임 ceiling** — `warrant.py`가 토큰 밴드 표시 후 실행, 런타임은 `budget_block.py`가 spawn-count ceiling을 exit-2 강제(토큰 tally는 advisory).
4. **생성 하네스는 git repo** — rollback substrate. 진행 상태는 `.harness/state.yaml`(오케스트레이터 단독쓰기 SOT).
> 상세 전략·설계·검증: `design/pivot-to-claude-primitives-strategy.md` + `design/p1-probe-results.md`.

## 호출 & 경로 (이 스킬이 전역 설치되어도 자족 작동)

- **트리거:** `/harness-creator <도메인 한 문장>` (또는 "하네스 구성해줘" 등 description 매칭).
- **TOOLS_ROOT** = `/Users/cys/Desktop/CYSjavis/cys-harness-creator` — 모든 도구(`warrant.py`·`emit_orchestrator.py`·`emit_workflow.py`·`validate_harness.py`·`inherit_genome.py`)와 게놈(`genome/`)이 여기 있다. 항상 `python3 "$TOOLS_ROOT"/<tool>.py` 형태로 호출.
- **TARGET** = 새 하네스 생성 경로. 사용자가 지정하면 그곳, 없으면 `./<harness_name>/`(현재 작업 디렉토리 하위). 이하 `<TARGET>`.

**실행 명령 (Phase 5~6, 그대로 사용):**
```bash
TR=/Users/cys/Desktop/CYSjavis/cys-harness-creator
python3 "$TR"/warrant.py --predicates <TARGET>/.harness/predicates.json   # Phase -1 분류
python3 "$TR"/warrant.py --graph <TARGET>/.harness/graph.json             # Phase 6 비용밴드
python3 "$TR"/emit_orchestrator.py <TARGET>                               # Phase 4(디폴트): graph→오케스트레이터 SKILL+agents + 게놈 active 전수
# (또는 execution_mode='workflow'인 경우에만) python3 "$TR"/emit_workflow.py <TARGET>   # Mode-A 결정론 replay
python3 "$TR"/validate_harness.py <TARGET>                                # Phase 5: 빌드 게이트(통과해야 함)
```
> `emit_orchestrator.py`(agent/team/hybrid)와 `emit_workflow.py`(workflow) 모두 게놈 전수(`inherit_genome.py`)를 자동 호출한다 — 별도 실행 불필요. `execution_mode`로 분기.
> **실행 핸드오프(R4)**: 산출 후 하네스를 *실행*하려면 `cd <TARGET> && claude`로 **새 세션**을 열어야 그 세션의 settings.json hook이 발화한다(공장 세션이 아님).

## 워크플로우

### Phase -1: Warrant 게이트 (필요한가?)
1. 사용자 요청에서 5개 술어 추출: `{distinct_expertise_domains, has_dependent_or_parallel_stages, will_be_rerun, output_objective, noisy}`.
2. `python3 warrant.py --predicates <preds.json>` 실행.
3. 판정:
   - `answer-directly` → 하네스 없이 직접 답한다. **종료.**
   - `single-agent` → 단일 에이전트 1회. **종료.**
   - `build-harness(topology, decision_mechanism, n_agents)` → Phase 0 진행.

### Phase 0: 컨텍스트 확인
`<harness>/` 존재 여부로 초기/재실행/부분재실행/마이그레이션(import) 분기.

### Phase 1: 도메인 분해
1. 작업을 노드로 분해 (id, 역할명, inputs/outputs, write_paths).
2. 각 역할명을 `model-tier-policy.js`의 role-class에 매핑 → `resolveModel()`로 model 티어 확정.
3. `n_agents ≤ MAX_FANOUT(5)` 확인 (초과 시 도메인 묶기/2단계 합성).

### Phase 2: graph.json 저작 (단일 writer)
**이 스킬만이 graph.json을 쓴다.** `graph.schema.json` 준수. `harness_version=0.1.0`. `budget.total_tokens`=warrant 추정(+여유). topology/decision_mechanism=warrant 제안.

### Phase 3: agent 파일 + schema 저작
1. 각 node.agent → `.claude/agents/<agent>.md`: frontmatter(name/description/**model**/**model_rationale**/tools=least-privilege) + 본문(핵심역할/작업원칙/입출력 프로토콜[정확한 _workspace 경로 + 방출 schema]/에러핸들링).
2. 각 node.output_schema → `schemas/<name>.json` (draft 2020-12, bare-filename $id, additionalProperties:false). reflect-then-revise 노드는 `schemas/critique.json`도 필요.

### Phase 4: 오케스트레이터 SKILL + emit
1. `.claude/skills/<domain>-orchestrator/SKILL.md` — graph의 사람용 뷰 (phase-count는 README와 일치).
2. `python3 emit_workflow.py <harness>` → `.harness/workflow.js` (Mode A 런타임).
3. `.harness/harness.lock`(write_paths→node 맵), `.harness/MANIFEST.json`(최소 provenance) 저작.
4. `.claude/settings.json` — SubagentStop 토큰 로그 hook.

### Phase 5: 검증 게이트
1. `python3 validate_harness.py <harness>` → **error 시 생성 중단·보고**(고치고 재실행).
2. README phase-count == 오케스트레이터 SKILL phase-count 확인(DOC_DRIFT).

### Phase 6: 비용 승인 + 실행
1. `python3 warrant.py --graph <harness>/.harness/graph.json` → 토큰/USD 밴드 표시.
2. **사용자 승인 대기**(approval_required=true).
3. `Workflow({ scriptPath: "<harness>/.harness/workflow.js", args: {...} })`. `budget.total`이 하드 ceiling.
4. 중단 시 `resumeFromRunId`로 재개(변경 노드부터).

### Phase 7: git + 헤드투헤드(선택)
1. `git init && git add -A && git commit` (rollback substrate).
2. head-to-head: `evals/<domain>.scorecard.json` 기준 C2(CYS) vs C3(no-harness) 1회 → 능가 or 정직 미달 보고.

## 산출 체크리스트
- [ ] `.harness/graph.json` (schema 통과) · `workflow.js` (emit, 수정금지)
- [ ] `.claude/agents/*.md` (model + model_rationale + least-privilege tools)
- [ ] `schemas/*.json` (workflow.js S-table와 일치)
- [ ] 오케스트레이터 SKILL.md · README (phase-count 일치)
- [ ] `validate_harness.py` PASS (exit 0)
- [ ] warrant 비용밴드 승인 후 실행
- [ ] 절대경로 없음 · model:opus 전역 아님 · 게놈 상속 commands는 정상(NO_COMMANDS 규칙 폐기, 새 도메인 커맨드는 직접 만들지 않음)
- [ ] git repo 초기화

## 도구 (cys-harness-creator/)
- `warrant.py` — Phase -1 게이트 + 토큰 비용밴드
- `model-tier-policy.js` — role→tier SoT + V1/V2/V3 규칙
- `graph.schema.json` — graph.json 계약 스키마
- `emit_workflow.py` — graph.json → workflow.js (Mode A)
- `validate_harness.py` — 정적 게이트
- `constants.json` — 튜너블 상수 SoT
- `lib/toposort.py` — 결정론 토소트(emitter+validator 공용)
- `examples/deep-research/` — M0 dogfood + 첫 헤드투헤드 fixture

## 참고 — 설계 두뇌 (references/, 필요 시 Read로 로드; progressive disclosure)

> 원본 harness의 6개 reference를 CYS 패러다임으로 적응 이식(2,500+줄). **구현 현황은 `IMPLEMENTATION-STATUS.md`가 모든 서술에 우선.**

- `references/IMPLEMENTATION-STATUS.md` — **먼저 읽기.** M0 실구현 / M1-deferred(dispatch dynamic·expert-pool·hierarchical 등) / 폐기규칙(NO_COMMANDS 등). 다른 문서의 aspirational 서술에 우선.
- `references/architecture-patterns.md` — Phase 1~2: topology(3)×decision-mechanism(4) 선택, 원본 6패턴 매핑, 에이전트 분리 4축, Mode-A/B 선택.
- `references/graph-and-orchestration.md` — Phase 2·5: graph.json 저작 템플릿 + emit + 데이터전달(inputs/outputs/_workspace) + on_exhaust 에러핸들링 + RUNTIME 라우팅.
- `references/skill-writing-guide.md` — Phase 3~4: agent/오케스트레이터 skill 작성, pushy description, Why-not-ALWAYS, output_schema(머신검증) 설계.
- `references/testing-and-measurement.md` — Phase 5~6: validate 게이트, lift_gate(독립 블라인드), h2h, 트리거 near-miss 검증.
- `references/qa-guide.md` — QA 경계면 교차비교 + 7 버그패턴 + verify-before-assert + finding triage.
- `references/examples.md` — 3 작동 예시(deep-research/ticket-triage/design-decision)의 graph.json으로 배우기.
