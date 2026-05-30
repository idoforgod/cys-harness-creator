---
name: deep-research-orchestrator
description: "deep-research 하네스를 Claude Code 프리미티브(Agent/TeamCreate)로 실행하는 오케스트레이터. 'deep-research' 관련 작업·생성·분석 요청 시 사용. 후속: 다시 실행, 재실행, 업데이트, 수정, 보완, 'deep-research의 일부만 다시', 이전 결과 기반 개선 요청 시에도 반드시 이 스킬을 사용."
---
# deep-research Orchestrator

graph.json(불변 계약)에서 emit된 오케스트레이터. 산출 하네스를 **라이브 Claude Code 호스트 세션**에서
실행하며, 이 세션에 상속된 AWF 게놈 hook(컨텍스트 보존·보안·SubagentStop)이 발화하고, 각 노드의
`.claude/agents/<agent>.md` frontmatter(model·tools·maxTurns)가 Agent 도구에 의해 런타임 강제된다.

## 실행 모드: team (기본=agent 순차 sub-spawn; team=TeamCreate/SendMessage 실제 emit; hybrid=단계별 혼합)

## 에이전트 구성

| 노드 | agent | model | mechanism | tools | 출력 |
|---|---|---|---|---|---|
| gather | researcher | haiku | single | Read, Glob, Grep, WebSearch, WebFetch | _workspace/01_gather/findings.json |
| fetch | fetcher | haiku | single | Read, Glob, Grep, WebSearch, WebFetch | _workspace/02_fetch/findings.json |
| verify | verifier | sonnet | reflect-then-revise | Read, Write, Glob, Grep | _workspace/03_verify/findings.json |
| synthesize | synthesizer | opus | single | Read, Write, Glob, Grep | _workspace/04_report/report.json |

## 워크플로우

### Phase 0: 컨텍스트 + SOT 초기화
1. `<harness>/` 존재로 분기: 초기 / 재실행 / 부분 재실행 / 마이그레이션.
2. `.harness/state.yaml`(SOT)을 작성/갱신한다 — **오케스트레이터 단독 쓰기**. 필드:
   `current_step, outputs{}, budget{spawns_used:0, max_spawns:<warrant fanout 합>}, pacs{}, audit_log[]`.
   state.yaml 작성이 ap_state-gated AWF 기능(SOT 스키마·autopilot·Decision Log·SOT-restore)을 깨운다.
3. 재실행이면 첫 단계로 `state.yaml` + 최신 `.claude/context-snapshots/latest.md`를 읽어 맥락 복원.

### Phase 1: 비용 승인
1. `python3 ../../warrant.py --graph .harness/graph.json` 로 비용밴드 표시.
2. `budget.approval_required=true`이면 사용자 'approve' 대기 후 진행. 승인은 state.yaml audit_log에 기록.
3. `budget.max_spawns`를 warrant fanout 합으로 설정 → 런타임 `budget_block.py`(PreToolUse)가 spawn 초과 시 exit-2 차단.

### Phase 2: 노드 실행 + 품질 게이트
**실행 모드: team** — 오케스트레이터(=Team Lead)가 팀 프리미티브로 직접 실행한다. Agent() 순차 spawn이 아니라 TeamCreate로 팀을 구성하고 TaskCreate(의존성 포함)로 할당하며, 팀원은 SendMessage로 자체 조율한다.

1. **`TeamCreate(team_name="deep-research-team", members=[...])`** — 멤버(각 노드 agent; frontmatter model·tools 런타임 강제):
   - `researcher` (model=haiku, tools=Read, Glob, Grep, WebSearch, WebFetch) — 'gather' 노드
   - `fetcher` (model=haiku, tools=Read, Glob, Grep, WebSearch, WebFetch) — 'fetch' 노드
   - `verifier` (model=sonnet, tools=Read, Write, Glob, Grep) — 'verify' 노드
   - `synthesizer` (model=opus, tools=Read, Write, Glob, Grep) — 'synthesize' 노드
   spawns_used += 멤버수 (PostToolUse `spawn_counter`가 자동 증분; `budget_block`이 천장 강제).
2. **`TaskCreate`** — 각 노드를 task로 생성, 의존성은 graph edges(toposort 보존):
   - `TaskCreate(subject="gather", owner="@researcher")`
   - `TaskCreate(subject="fetch", owner="@fetcher", depends_on=["gather"])`
   - `TaskCreate(subject="verify", owner="@verifier", depends_on=["fetch"])`
   - `TaskCreate(subject="synthesize", owner="@synthesizer", depends_on=["verify"])`
3. **`SendMessage`** — 팀원 간 직접 통신: 상충·누락 발견 시 관련 팀원에게 공유(리더 우회 peer-to-peer). 적대적 검증 노드는 격리 — 팀원이 아니라 별도 `Agent(subagent_type="reviewer")`로 spawn(L2).
4. **Team Lead L2** — `TaskUpdate(status=completed)` 시 Lead가 산출물을 `_workspace/`에서 읽어 품질게이트(L0-L2, `gate_or_block`) 통과 + SOT `outputs.step-N` 기록(단일쓰기). PostToolUse `qa_gate_runner`가 같은 게이트를 host 인터록으로 재확인.
5. **`TeamDelete`** — 모든 task 완료 후 팀 정리(세션당 한 팀; 다음 팀 전 반드시 TeamDelete). 산출물은 `_workspace/`에 flush.
> **Graceful degrade (A2-iii)**: `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` 플래그가 없으면 각 task를 `Agent(subagent_type=...)` fan + `_workspace/` 핸드오프로 강등한다 — 팀 없이도 동일 그래프가 실행된다.


**노드별 품질 게이트(autopilot-execution.md 순서, 각 단계 산출물 작성 직후):**
- **L0 Anti-Skip**: `python3 ../../templates/hooks/gate_or_block.py .claude/hooks/scripts/validate_pacs.py --check-l0 --step <N>` (산출물 존재+≥100B).
- **L1 Verification**: `gate_or_block.py validate_verification.py --step <N>` (기능 목표 100% 달성).
- **L1.5 pACS**: `gate_or_block.py validate_pacs.py --step <N>` (Pre-mortem + F/C/L min, RED 차단).
- **L2 Adversarial Review** (review 노드만): reviewer/fact-checker spawn 후 `gate_or_block.py validate_review.py --step <N>`.
- FAIL → `diagnose_context.py` → `validate_diagnosis.py`, `validate_retry_budget.py` 예산 내 재시도.
> `gate_or_block.py`가 advisory validator(exit 0)를 **exit-2 인터록**으로 승격하므로, 게이트 FAIL이 단계를 실제로 멈춘다.

### Phase 3: 통합 산출 + 측정
1. 마지막 노드 출력을 최종 산출물로 기록(state.yaml outputs).
2. `git init && git add -A && git commit`(rollback substrate).
3. (선택) head-to-head: `evals/deep-research.scorecard.json` 기준 C2(이 하네스) vs C3(no-harness) n≥5 → `h2h_aggregate.py`.

## 메모리 운영 (Context Preservation — 상속 게놈 hook이 발화하는 일급 기능)
이 하네스는 **장기기억**을 일급 기능으로 갖는다. 라이브 세션에서 상속 게놈 hook이 자동 발화한다:
- **세션 연속성(Tier I)**: 토큰 초과·`/clear`·컨텍스트 압축·세션 종료 시 `context_guard`/`save_context`가
  `.claude/context-snapshots/latest.md`에 스냅샷을 저장한다. IMMORTAL 섹션(현재 작업·다음 단계·SOT·품질게이트
  상태)은 압축에도 우선 보존된다. 새 세션 시작 시 `[CONTEXT RECOVERY]` 메시지가 뜨면 **반드시** 안내된
  `latest.md`를 Read로 읽어 맥락을 복원한 뒤 진행한다.
- **교차세션 지식(RLM 패턴)**: `.claude/context-snapshots/knowledge-index.jsonl`은 세션별 작업·수정파일·
  error→resolution을 누적한 **외부 메모리**다. 통째로 로드하지 말고 **Grep으로 질의**한다(RLM):
  예) `Grep "<주제>" .claude/context-snapshots/knowledge-index.jsonl`. 과거 error→resolution은 SessionStart가
  자동 표시한다.
- 작업 시작 시 SOT(`state.yaml`) + `latest.md`를 읽어 현재 단계·산출물·예산을 복원한다.
> Tier II(교차-실행 도메인 메모리 `.harness/memory/` — 반복 실행을 거쳐 도메인 지식을 누적)는 후속 마일스톤(M6)에서 추가된다.

## 진화 (매 실행 후 — 살아있는 시스템, idoforgod의 진화 규약)
하네스는 고정물이 아니라 진화하는 시스템이다. 매 실행 후:
1. **피드백 수집** — 사용자에게 "개선점/팀 구성 변경점"을 1회 묻는다(강요 금지, 기회 제공).
2. **피드백 라우팅** — `python3 ../../evolve_harness.py . --type <유형> --change "..." --reason "..."`로 유형→대상을
   결정론적으로 `.harness/change-history.jsonl`(append-only)에 기록:
   - `result-quality` → 그 노드의 how(스킬/agent 본문) · `agent-role` → `.claude/agents/<agent>.md`
   - `workflow-order` → 이 오케스트레이터 SKILL · `team-comp` → 오케스트레이터+agents · `trigger-miss` → 스킬 description
3. **변경 검증** — 라우팅된 수정은 해당 Implementation 단계로 재진입 후 **반드시 `validate_harness.py`를 재통과**한다
   (진화가 계약을 퇴행시키지 못함).
4. **선제 진화** — `evolve_harness.py . --proactive`: 같은 유형 피드백 2회↑ 시 자동 제안.
5. **유지보수** — 재감사(`audit_harness.py`) → 드리프트 제시 → 한 번에 하나씩 수정 → 재검증 → CLAUDE.md 동기화.

## 비용 거버넌스
사전: warrant 비용밴드 승인. 런타임: `budget_block.py` spawn-count ceiling(exit-2). 토큰 tally는 advisory.

## 에러 핸들링
| 상황 | 전략 |
|------|------|
| 노드 1회 실패 | 1회 재시도(retries), 재실패 시 on_exhaust(proceed-with-gap/escalate) |
| 게이트 FAIL | abductive diagnosis → 예산 내 재시도 → 초과 시 사용자 에스컬레이션 |
| spawn 초과 | budget_block exit-2 — graph.budget 상향 또는 fan-out 축소 |
| 상충 데이터 | 삭제 금지, 출처 병기 |

## 테스트 시나리오
- 정상: query 입력 → 노드 순차 실행 + 게이트 PASS → 최종 산출물 생성.
- 에러: 한 노드 FAIL → diagnosis → 재시도 → 부분 결과로 진행, 보고서에 누락 명시.
