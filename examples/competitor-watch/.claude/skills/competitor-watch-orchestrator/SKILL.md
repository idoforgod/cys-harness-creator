---
name: competitor-watch-orchestrator
description: "competitor-watch 하네스를 Claude Code 프리미티브(Agent/TeamCreate)로 실행하는 오케스트레이터. 'competitor-watch' 관련 작업·생성·분석 요청 시 사용. 후속: 다시 실행, 재실행, 업데이트, 수정, 보완, 'competitor-watch의 일부만 다시', 이전 결과 기반 개선 요청 시에도 반드시 이 스킬을 사용."
---
# competitor-watch Orchestrator

graph.json(불변 계약)에서 emit된 오케스트레이터. 산출 하네스를 **라이브 Claude Code 호스트 세션**에서
실행하며, 이 세션에 상속된 AWF 게놈 hook(컨텍스트 보존·보안·SubagentStop)이 발화하고, 각 노드의
`.claude/agents/<agent>.md` frontmatter(model·tools·maxTurns)가 Agent 도구에 의해 런타임 강제된다.

## 실행 모드: team (agent=순차 sub-spawn; team/hybrid=TeamCreate/SendMessage 실제 emit; hybrid 단계별 혼합은 future work=현재 team 레시피)

## 에이전트 구성

| 노드 | agent | model | mechanism | tools | 출력 |
|---|---|---|---|---|---|
| gather | scout | haiku | single | Read, Glob, Grep, WebSearch, WebFetch | _workspace/01_gather/items.json |
| dedupe | deduper | haiku | single | Read, Write, Glob, Grep | _workspace/02_dedupe/items.json |
| brief | briefer | opus | single | Read, Write, Glob, Grep | _workspace/03_brief/brief.json |

## 워크플로우

### Phase 0: 장기기억 회상 + 컨텍스트 + SOT 초기화
1. `<harness>/` 존재로 분기: 초기 / 재실행 / 부분 재실행 / 마이그레이션.
2. **장기기억 회상 (Tier II — 작업 입력, 실행 단계·MANDATORY)**: graph 실행 *전에* 과거 도메인 지식을 회상한다 — `Grep "<query 정규화 토큰>" .harness/memory/runs/index.jsonl`로 유사 run을 찾아 **매치된 run만** `Read .harness/memory/runs/<run_id>/` + `Read .harness/memory/domain-knowledge.yaml`(+ `risk/decisions.jsonl`로 금기 확인) → 회상한 엔티티·제약을 `_workspace/_recall.json`에 떨궈 **하류 에이전트의 작업 입력**으로 넘기고, `state.yaml`의 `audit_log`에 `{"recall": "hit|miss", "injected": [...]}`를 기록한다. 무매치/콜드면 `_workspace/_recall.json = {"cold": true}`로 진행(선례 없음). 회상 직후 **run START**로 `.harness/memory/runs/index.jsonl`에 `{"run_id": <id>, "status": "in_progress", "query_norm": ...}` 1줄을 append한다 — Tier-II 쓰기는 종단 일괄이 아니라 **증분 스트리밍**이라 크래시·재개·병렬 run이 부분 진행을 회상한다(완료 시 Phase 3에서 같은 레코드를 `status: "completed"`로 갱신). 이는 아래 "메모리 운영" 섹션의 prose가 아니라 **Phase 0의 실행 단계**다 — 회상→주입 도관의 입력 절반(맹신 금지: 회상은 현재 요건에 맞게 검증 후 사용).
3. `.harness/state.yaml`(SOT)을 작성/갱신한다 — **오케스트레이터 단독 쓰기**. 필드:
   `current_step, outputs{}, budget{spawns_used:0, max_spawns:<warrant fanout 합>}, pacs{}, audit_log[]`.
   state.yaml 작성이 ap_state-gated AWF 기능(SOT 스키마·autopilot·Decision Log·SOT-restore)을 깨운다.
4. 재실행이면 첫 단계로 `state.yaml` + 최신 `.claude/context-snapshots/latest.md`를 읽어 맥락 복원.

### Phase 1: 비용 승인
1. `python3 ../../warrant.py --graph .harness/graph.json` 로 비용밴드 표시(`.harness/warrant.json` 기록 — PRE 게이트 산출물).
2. `budget.approval_required=true`이면 사용자 'approve' 대기 후 진행. 승인 시 `.harness/APPROVED`(승인토큰)를 기록하고 state.yaml audit_log에도 남긴다. (`constants.BUILD_GATES`를 warn/error로 켜면 warrant.json·audit.json·APPROVED 부재 시 validate가 차단 — 4-스테이지 워크플로 강제.)
3. `budget.max_spawns`를 warrant fanout 합으로 설정 → 런타임 `budget_block.py`(PreToolUse)가 spawn 초과 시 exit-2 차단.

### Phase 2: 노드 실행 + 품질 게이트
**실행 모드: team** — 오케스트레이터(=Team Lead)가 팀 프리미티브로 직접 실행한다. Agent() 순차 spawn이 아니라 TeamCreate로 팀을 구성하고 TaskCreate(의존성 포함)로 할당하며, 팀원은 SendMessage로 자체 조율한다.

1. **`TeamCreate(team_name="competitor-watch-team", members=[...])`** — 멤버(각 노드 agent; frontmatter model·tools 런타임 강제):
   - `scout` (model=haiku, tools=Read, Glob, Grep, WebSearch, WebFetch) — 'gather' 노드
   - `deduper` (model=haiku, tools=Read, Write, Glob, Grep) — 'dedupe' 노드
   - `briefer` (model=opus, tools=Read, Write, Glob, Grep) — 'brief' 노드
   spawns_used += 멤버수 (PostToolUse `spawn_counter`가 자동 증분; `budget_block`이 천장 강제).
2. **`TaskCreate`** — 각 노드를 task로 생성, 의존성은 graph edges(toposort 보존):
   - `TaskCreate(subject="gather", owner="@scout")`
   - `TaskCreate(subject="dedupe", owner="@deduper", depends_on=["gather"])`
   - `TaskCreate(subject="brief", owner="@briefer", depends_on=["dedupe"])`
3. **`SendMessage`** — 팀원 간 직접 통신: 상충·누락 발견 시 관련 팀원에게 공유(리더 우회 peer-to-peer). 적대적 검증 노드는 격리 — 팀원이 아니라 별도 `Agent(subagent_type="reviewer")`로 spawn(L2).
4. **Team Lead L2** — `TaskUpdate(status=completed)` 시 Lead가 산출물을 `_workspace/`에서 읽어 품질게이트(L0-L2, `gate_or_block`) 통과 + SOT `outputs.step-N` 기록(단일쓰기). PostToolUse `qa_gate_runner`가 같은 게이트를 host 인터록으로 재확인.
5. **`TeamDelete`** — 모든 task 완료 후 팀 정리(세션당 한 팀; 다음 팀 전 반드시 TeamDelete). 산출물은 `_workspace/`에 flush.
> **Graceful degrade (A2-iii)**: `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` 플래그가 없으면 각 task를 `Agent(subagent_type=...)` fan + `_workspace/` 핸드오프로 강등한다 — 팀 없이도 동일 그래프가 실행된다.


**노드별 품질 게이트(autopilot-execution.md 순서, 각 단계 산출물 작성 직후):**
- **L0 Anti-Skip**: `python3 ../../templates/hooks/gate_or_block.py .claude/hooks/scripts/validate_pacs.py --check-l0 --step <N>` (산출물 존재+≥100B).
- **L1 Verification (필수/MANDATORY)**: 각 단계 산출물 직후 **`verification-logs/step-<N>-verify.md`를 반드시 작성**(기능 목표 100% 달성 근거) → `gate_or_block.py validate_verification.py --step <N>`. 이 로그가 없으면 `qa_gate_runner`가 **L1 BLOCK(exit-2)** 한다(L0·L1·budget는 필수 계층, L1.5·L2는 fire-on-presence).
- **L1.5 pACS**: `gate_or_block.py validate_pacs.py --step <N>` (Pre-mortem + F/C/L min, RED 차단).
- **L2 Adversarial Review** (review 노드만): reviewer/fact-checker spawn 후 `gate_or_block.py validate_review.py --step <N>`.
- FAIL → `diagnose_context.py` → `validate_diagnosis.py`, `validate_retry_budget.py` 예산 내 재시도.
> `gate_or_block.py`가 advisory validator(exit 0)를 **exit-2 인터록**으로 승격하므로, 게이트 FAIL이 단계를 실제로 멈춘다.

**메모리 릴레이 (단계간 검증된 사실 척추 — P2):** 각 노드의 단계 게이트 통과 *직후*, 검증된 핵심 사실 atom만 `.harness/memory/runs/<run_id>/stage-<N>-facts.jsonl`에 증류하고(벌크 산출물은 `_workspace/`에 유지 — 통째 로드 금지, RLM), SOT `outputs.step-<N>`에 산출물 포인터를 단일쓰기로 기록한다. **다음 노드는 하드코딩 경로 대신 SOT `outputs.step-<N>` + 직전 `stage-<N>-facts.jsonl`을 Read해 입력을 해소한다** — 검증된 사실 척추가 단계마다 *메모리를 통과*한다(벌크는 파일시스템). 데이터 이동이 장기기억을 통해 파이프라인처럼 연동되는 지점이다. 또한 검증된 새 사실은 **단계마다** `domain-knowledge.yaml`에 증분 병합한다(종단 일괄 금지 — P3 증분 스트리밍).

### Phase 3: 통합 산출 + 측정
1. **run 완료(메모리 종결)**: `.harness/memory/runs/index.jsonl`의 현재 run 레코드를 `status: "completed"`로 갱신하고 산출물·출처·결정을 `runs/<run_id>/`에 저장 + 새 사실을 `domain-knowledge.yaml`에 최종 병합한다(P3 증분 스트리밍의 종결). 그리고 마지막 노드 출력을 최종 산출물로 `state.yaml outputs`에 기록한다.
2. `git init && git add -A && git commit`(rollback substrate).
3. (선택) head-to-head: `evals/competitor-watch.scorecard.json` 기준 C2(이 하네스) vs C3(no-harness) n≥5 → `h2h_aggregate.py`.

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
- **교차-실행 도메인 메모리 (Tier II, `.harness/memory/`)** — 이 하네스가 *반복 실행*을 거쳐 도메인 지식을
  누적한다(RLM 외부 환경 — 통째 로드 금지, 프로그램적으로 질의):
  - **작업 시작 시 회상**: `Grep "<정규화 query 토큰>" .harness/memory/runs/index.jsonl` 로 과거 유사 실행을
    찾고, **매치된 run만** `Read .harness/memory/runs/<run_id>/`로 가져온다(결과가 많으면 `Agent`로 스니펫을 재귀
    분해). `domain-knowledge.yaml`을 읽어 L1 검증 기준으로 주입하고, `risk/decisions.jsonl`로 금기를 확인한다.
  - **완료 시 기록(단일쓰기=오케스트레이터)**: `runs/index.jsonl`에 1줄 추가
    ({run_id, ts, query_norm, topology, final_status, outputs[+sha256], sources, tags}) + `runs/<run_id>/`에
    산출물·출처·결정 저장 + 새 사실을 `domain-knowledge.yaml`에 병합(중복제거) + 표준 위험을 `risk/decisions.jsonl`에 추가.
  - **재사용 전 검증**: 회상된 과거 산출물은 현재 `domain-knowledge.yaml`에 대해 재검증 후 사용한다(맹신 금지;
    provenance·recency 가중).

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
