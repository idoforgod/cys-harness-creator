# 피벗 전략·설계안 — 산출 하네스 실행모델을 Claude Code 프리미티브로

> 작성일 2026-05-29. 검증 3중 수렴(직접 도구실행 + 8-에이전트 설계워크플로우 파일실측 + 프로젝트 self-diagnosis).
> 사용자 의도: 산출 하네스 실행모델을 Mode A(`workflow.js`) → **Claude Code 프리미티브(TeamCreate/Agent/SendMessage) 100% 위임**(idoforgod 방식)으로 전환하되, CYS 6축 우위(머신체크·비용·모델티어·안전·기억보존·실행런타임 엄격성)는 유지·이식하고, AWF 게놈 기능(보안hook·L0-L2·pACS·SOT·Adversarial Review)이 **실제로 작동**하게 한다.
> **구현은 사용자 명령으로만 착수.** 본 문서는 승인용 설계도이며, 진행 게이트는 P-1 라이브 프로브 결과다.

---

## 0. 결론

피벗 방향은 **타당하다**. 프리미티브 기질은 AWF 게놈이 설계된 바로 그 실행평면이라, 6축 중 **4축이 보존+활성화**되고 **모델티어는 오히려 격상**된다. 그러나 첫 설계초안의 "AWF 게이트가 *런타임 강제*된다"는 주장 상당수가 파일 실측 결과 **과장**이었고, **emit 리워크보다 먼저 해소할 3개 blocker**(전부 런타임 미지수)가 존재한다. 이를 무시하면 "graph는 team인데 hook은 안 도는" worst-of-both 상태가 된다.

---

## 1. 근거 — 왜 이 피벗이 옳은가 (thesis)

직전 평가에서 ground-truth로 확정된 사실(`design/compare-vs-*`, `awf-philosophy-mixup-analysis.md`와 정합):

1. Mode A에서 두 실행평면이 **직교**한다. `workflow.js`는 ambient `agent/parallel/pipeline/budget`만 호출(require/spawn/exec/validate_*/pACS/autopilot = 0건 실측). AWF 게놈 hook은 settings.json으로 **호스트 세션** lifecycle에 배선 → Workflow 도구 내부 `agent()` 호출에는 발화 안 함.
2. 결과: 게놈 228파일이 전수·검증되지만 Mode A 실행경로에서 **대부분 휴면**(L0-L2·pACS·SOT·Autopilot·reviewer/fact-checker·Context Preservation).
3. Workflow 런타임은 커스텀 `.claude/agents` agentType을 resolve 못 해 전부 general-purpose 강등, role은 프롬프트 인라인(tools/model 런타임 미강제).
4. 유일 실측 h2h(n=1): CYS `workflow.js`=0.833 vs no-harness opus=1.0 → **BASELINE-WINS −16.67pp**. 실패항목 A5(다측면 구분)·A7(상충출처 양면제시)는 정확히 적대적 품질게이트가 잡아야 할 결함.

→ 프리미티브 기질에서는 (a) Agent가 커스텀 `.claude/agents`를 resolve(tools/model/maxTurns 런타임 바인딩), (b) AWF lifecycle hook이 호스트 세션에 발화, (c) 오케스트레이터가 SOT를 쓰고 L0-L2를 호출할 수 있다. 즉 dormancy의 원인(Mode A)을 제거하고 AWF가 설계된 곳으로 옮긴다.

### 6축 이송 판정 (설계워크플로우 merge 분석)

| 축 | 판정 | 비고 |
|----|------|------|
| 1 머신체크 | **보존**(리타겟) | validate_harness 대부분 무변경; RUNTIME_DECLARED만 flip + 신규 체크 |
| 2 비용 | **at-risk** | 사전 warrant 밴드는 생존; 런타임 하드ceiling은 회귀(§3 CD-1/CD-3) |
| 3 모델티어 | **격상** | Agent가 frontmatter `model:` honoring → advisory→runtime-enforced (피벗 최대 단일 이득) |
| 4 안전 | **보존+활성화** | 보안 hook이 라이브 세션에 발화(Mode A에선 휴면) |
| 5 기억보존 | **보존+활성화** | Context Preservation hook이 라이브 세션에 발화 |
| 6 실행런타임 엄격성 | **보존(계약)+결정론 회귀** | graph.json 계약·validate 게이트 유지; byte-결정론·resume 회귀 |

---

## 2. 목표 아키텍처

### 2.1 빌드 파이프라인 전환

`graph.json`(불변 계약 — **유지**: CYS가 idoforgod 대비 갖는 머신체크 우위의 핵심) → `emit_workflow.py`를 **`emit_orchestrator.py`로 리워크**:
- ① `.claude/skills/<도메인>-orchestrator/SKILL.md` — idoforgod식 prose가 라이브 빌드를 구동(toposort 순서로 TeamCreate 멤버/Agent spawn 생성, 결정기제 확장, L0-L2 게이트 단계 삽입, adversarial-review 단계 주입).
- ② 노드별 `.claude/agents/<agent>.md` — frontmatter `{name, description, model=resolveModel(node), model_rationale, tools=최소권한, maxTurns}` + role 본문(이제 **embed**, 인라인 아님).
- `workflow.js` emit은 폐기가 아니라 `execution_mode='workflow'` 선택지로만 잔존(byte-exact replay가 필요한 드문 경우).

### 2.2 메타스킬 8 Phase

| Phase | 목적 | 산출 | CYS 게이트 | AWF 요소 |
|-------|------|------|-----------|---------|
| -1 Warrant | 하네스 필요성 판정 | predicates.json, verdict | warrant.py classify() (결정론) | 없음(사전) |
| 0 컨텍스트/SOT init | 초기/재실행/부분/마이그 분기 + state.yaml 최초 작성 | state.yaml, harness.lock | SOT_SCHEMA(신규) | **ap_state-gated 트리오 wake**(SOT스키마·autopilot·SOT-restore) |
| 1 도메인 분해 | 노드화 + 역할→티어 매핑 | node list + 티어 | model-tier-policy resolveModel | 없음 |
| 2 graph.json 저작 | 불변 계약(단일쓰기) | graph.json | GRAPH_SCHEMA·EDGE·CYCLE | AC-2 단일쓰기 |
| 3 agents/schema/categorization | 노드별 agent·schema·categorization.yaml | .claude/agents/*, schemas/*, categorization.yaml | AGENT_*·TIER·TOOLS_ALLOWLIST(신규)·CATEGORIZATION_COMPLETE(신규) | reviewer/fact-checker frontmatter가 런타임 spec |
| 4 emit 오케스트레이터 | graph→prose 오케스트레이터 SKILL + agent body | orchestrator SKILL.md, README, MANIFEST, RUNTIME | GRAPH_SKILL_CONSISTENCY(신규)·DOC_DRIFT | prose가 후속 AWF 게이트의 **caller** |
| 5 게놈 전수+검증 | 게놈 rsync + settings 병합 | 게놈 228파일, settings.json | GENOME_PRESENT·HOOK_REGISTERED·_verify | 보안+Context hook 배선 dormant→**live** |
| 6 빌드게이트+비용승인 | validate(exit0) + 비용밴드 표시·승인 | validate report, 승인 기록 | validate_harness 하드 인터록 | 비용 tally 베이스라인 |
| 7 라이브 실행 | 호스트 세션에서 노드 spawn + L0-L2 인터리브 | 산출물, *-logs/, state.yaml | gate_or_block 래퍼(신규)·budget hook·return validator | **L0/L1/L1.5/L2/Diagnosis/Translation 발화 — A5/A7 잡는 곳** |
| 8 git+h2h | rollback + n≥5 재측정 | git repo, scorecard, verdict | h2h_aggregate(무변경) | 측정 |

### 2.3 산출 런타임

라이브 Claude Code 호스트 세션. `execution_mode`로 선택: **agent**(순차 sub-spawn, 부모/자식 hook 발화가 더 확실 — §4에 따라 첫 dogfood 기본값) / **team**(TeamCreate 피어팀, opt-in) / **hybrid**. 게놈 hook이 세션 도구이벤트마다 발화(PreToolUse Bash→block_destructive exit-2, PostToolUse→context_guard+secret_filter, SubagentStop→cys_log_tokens, Stop→snapshot, PreCompact/SessionEnd→save, SessionStart→restore).

### 2.4 도구 처분

| 도구 | 처분 | 변경 |
|------|------|------|
| warrant.py | survives | classify/cost_band 무변경; **단 team 가격 추가 필요(§3 CD-3)** |
| model-tier-policy.js | survives(격상) | 로직 무변경; frontmatter가 런타임 honoring |
| graph.schema.json | survives | execution_mode에 agent\|hybrid 추가, node.tools·node.review 옵션 추가 |
| h2h_aggregate.py | survives | 무변경; upstream run-producer만 재구현 |
| constants.json, lib/atomic_write, lib/toposort | survives | ENSURE_GUARD 재해석/은퇴 |
| emit_workflow.py | **rework(primary)** | → emit_orchestrator.py(.js core 은퇴, orchestrator SKILL+agent 2종 emit) |
| validate_harness.py | rework | RUNTIME_DECLARED dual-accept + 신규 체크 5종 |
| inherit_genome.py | rework | 피벗이 정당화(hook 배선 dormant→live); _RUNTIME_MANIFEST/_CLAUDE_PTR 재작성; timeout 5000→5 버그수정; 수정된 pre_subagent 동봉 |
| lift_gate.py | rework | probe를 prose/primitive로 재emit; blind grader 불변식 유지 |
| workflow.js (산출물) | retire(선택) | execution_mode='workflow'에서만 |

### 2.5 헌법 개정 3건

- **AC-2**: "런타임 진행은 Workflow resumeFromRunId, 별도 state 파일 금지" 삭제 → `state.yaml`(AWF SOT)을 라이브 진행 저장소로. 단일쓰기·atomic_write·harness.lock 단일소유는 **유지·강화**(병렬 멤버는 SendMessage, 공동쓰기 금지). 'AC-2' 마커 문자열 보존.
- **AC-1**: 비용 ceiling 문구를 **입증 후** 보강(§4 — 토큰이 아니라 spawn-count/fanout 기반으로 명시).
- **RUNTIME_DECLARED 계약**: canonical을 오케스트레이터 스킬로(workflow.js는 선택 대안). **flip이 아니라 execution_mode별 dual-accept**(§3 CD-6).

---

## 3. ⚠️ 적대적 검증이 드러낸 정직한 위험

첫 설계초안은 "AWF 게이트가 runtime-enforced"라 했으나 파일 실측 결과 다수가 **prose-invoke(LLM 순응 의존)**임이 드러났다 — idoforgod의 바로 그 약점. 착수 전 해소 필수.

### Blocker (emit 리워크보다 먼저)

- **R1/CD-1** — `validate_pacs.py`·`validate_review.py`는 **`valid:false`여도 exit 0**(직접 실행 확인), docstring "NOT a Hook — manually invoked". 게이트 부활 = idoforgod prose 약점 재현.
  - **수정**: `gate_or_block.py` 래퍼(JSON→`valid==false`면 exit-2)를 만들어 그것을 SubagentStop/PostToolUse에 배선. hook 강제 가능 게이트 vs 불가피 prose-invoke 게이트를 **명시 경계**.
- **R2/CD-2** — 신규 hook 3종이 전부 PreToolUse 매처 `'Agent'`에 걸리는데 게놈은 `Task(subagent_type=...)`로 spawn(AGENTS.md:220,240). 기본 team의 실제 spawn 동사가 Task/TeamCreate면 **hook이 조용히 no-op** → governance가 Mode A보다 약해짐.
  - **수정**: 라이브 프로브로 실제 spawn 동사 확정 → 매처를 `Agent|Task|TeamCreate` 합집합. `HOOK_MATCHER_COVERS_SPAWN` 체크. **P0 최우선**.
- **R3** — `pre_subagent_invocation.py`(유일한 미등록-agent 하드블록)가 **stdin 무시·self-test만·exit 0**(라이브 실측). 키는 `@`-접두, payload는 bare. fork-rule은 인가 모델 아님.
  - **수정**: stdin main + 이름 정규화 + 별도 `authorized` 필드 + 미등록 도메인agent 기본 exit-2(단 categorization 자동생성 선행).

### Major

- **R4** — **스킬은 세션을 못 띄운다.** hook은 `claude` 프로세스 project-dir에 바인딩 → 메타스킬이 *공장 세션*에서 spawn하면 발화하는 건 *공장의* hook(dormancy 재현). **세션 경계 핸드오프 명시**: 공장 세션 산출 → 사용자가 `cd <harness> && claude`로 별도 세션 → 거기서 hook 발화. RUNTIME.json에 `launch` 필드.
- **R5** — team 모드는 미검증 가정 위. **team을 기본값에서 opt-in으로 강등**, 첫 dogfood는 agent 모드.
- **R6/CD-1** — 토큰 ceiling은 신뢰 feeder 없음(cys_log_tokens self-admit). → **spawn-count/fanout 기반 재정의**(host-관측·결정론), 토큰은 advisory.
- **CD-3** — warrant가 team의 SendMessage 조율 트래픽 미가격 → 기본 substrate 과소가격. `member_count×coord_tokens×rounds` 항 추가.
- **R7** — SessionStart restore 매처가 `clear|compact|resume`뿐 → 한 세션 긴 빌드는 중간 restore 미발화. 매처 확장 or 오케스트레이터가 첫 단계에 항상 state.yaml 읽기.
- **CD-4** — byte-결정론 회귀 anchor 상실 + n≥5 h2h가 비정상 시스템 측정 → 변량/검정력 분석 + 구조추출 golden 유지.
- **CD-5/CD-6** — AC-1에 budget_block을 ceiling으로 **조기 확정 금지**(입증 후). RUNTIME_DECLARED는 dual-accept(역호환). `inherit_genome.py:107` timeout 5000 버그 수정.

---

## 4. 수정된(하드닝된) 전략

**교훈**: "AWF를 부활시킨다" ≠ "AWF가 자동으로 강제된다". prose-invoke 게이트는 hook으로 승격해야 진짜 인터록이 되고, 그 전에 런타임 미지수(spawn 동사·hook 발화)를 라이브로 확정해야 한다. 빌드타임 머신체크(validate_harness)는 **여전히 머신강제로 유지**; 바뀌는 건 *런타임 게이트 호출* 방식이며 가능한 한 hook으로 결정론화한다.

```
P-1  라이브 프로브 (선행 게이트 — 통과해야 emit 리워크 착수)
     · 실제 spawn 동사 확정(Agent/Task/TeamCreate)              → R2
     · 커스텀 .claude/agents resolve + tools/model 바인딩 확인     → A1
     · 라이브 세션 hook 발화(Stop snapshot, SessionStart restore)  → A2
     · gate_or_block / pre_subagent exit-2 차단 확인               → R1,R3
P0   스키마+헌법(무행동변경): execution_mode agent|hybrid, node.tools/review;
     AC-2/AC-1/RUNTIME 개정; RUNTIME_DECLARED dual-accept(역호환)
P1   hook 정비: pre_subagent 수정, gate_or_block.py, budget_block(spawn-count),
     validate_agent_return, 매처 합집합, timeout 수정
P2   emit_orchestrator.py (core 리워크) — agent 모드 우선
P3   validate_harness + inherit_genome 리타겟 (신규 체크 5종)
P4   메타스킬 SKILL.md + reference 3종 재작성 + MEASUREMENT_DRIFT 체크(+37.5pp drift 차단)
P5   라이브 dogfood + n≥5 h2h 재측정 → "능가/미달" 데이터 확정 (team 기본승격은 이 결과에 게이트)
```

---

## 5. 승인 필요 — 결정 사항

1. **기본 실행모드**: agent 모드 기본(첫 dogfood), team은 P5 입증 후 승격 — 사용자 의도(team 100% 위임)와 검증순서(agent 우선)의 절충.
2. **비용 거버넌스**: 토큰 하드ceiling 포기, spawn-count/fanout 기반 + 토큰 advisory 수용 여부.
3. **결정론**: byte-exact replay 포기, AWF semantic resume + 구조추출 golden 대체 수용 여부.
4. **범위**: config flip이 아니라 재아키텍처(emit 전면 재작성 + reference ~2,500줄 + hook 5개 + validate 체크 5개 + 헌법 3조). 단계적(P-1→P5) 진행.

---

## 부록 — P-1 프로브 결과

> P-1 실행 결과는 `design/p1-probe-results.md`에 stamp. 본 설계의 모든 "feasible/conditional" 추론은 P-1로 검증/반박된다.
