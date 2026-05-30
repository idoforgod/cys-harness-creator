# P-1 라이브 프로브 결과 (실측)

> 2026-05-29. nested `claude -p` (v2.1.156) 서브프로세스 + 스크래치 fixture(`_workspace/probe/`)로 피벗의 런타임 가정을 실측. 각 항목 가설→테스트→관측→판정.
> **판정 종합: GREEN — 3개 blocker의 런타임 가정이 전부 성립.** blocker는 "피벗을 죽일 수 있는 미지수"에서 "알려진 엔지니어링 작업"으로 강등.

---

## 환경
- `claude` v2.1.156, `/Applications/cmux.app/Contents/Resources/bin/claude`. nested headless `claude -p ... --dangerously-skip-permissions < /dev/null` 정상 작동(스크래치 프로젝트에서).

## A2 — 라이브 세션 lifecycle hook 발화 ✅ RESOLVED (live)
- **가설**: 오케스트레이터가 라이브 `claude` 세션이면 settings.json의 AWF hook이 그 세션에 발화한다(Mode A 단일 도구호출과 달리).
- **테스트**: 스크래치 fixture에 SessionStart/Stop/PreToolUse hook 배선 후 `claude -p "PROBE_OK"` 실행.
- **관측**: `SENTINELS/sessionstart`, `SENTINELS/stop` 생성. 후속 프로브에서 `pretooluse_agent`, `subagentstop`도 생성. headless 모드에서도 hook 발화.
- **판정**: SessionStart·Stop·PreToolUse(Bash)·PreToolUse(Agent)·SubagentStop 전부 **라이브 발화**. 피벗 thesis(프리미티브 기질 = AWF가 발화하는 곳)의 핵심 가정 **참**.

## R2 — sub-agent spawn 프리미티브 이름 ✅ RESOLVED (inspection + live)
- **가설**: 신규 governance hook이 매처 `'Agent'`에 걸리는데 게놈 prose는 `Task(subagent_type)`. 실제 spawn 동사가 다르면 hook이 no-op.
- **관측**: 현재 Claude Code의 sub-agent spawn 도구 = **`Agent`**(게놈 AGENTS.md의 `Task`는 stale 네이밍). agent 모드 spawn 시 PreToolUse 매처 `'Agent'`가 **실제 발화**(sentinel). 단 team 모드의 `TeamCreate`는 PreToolUse 커버리지 없음(settings.json은 PostToolUse에만 `TeamCreate` 포함).
- **판정**: agent 모드에선 매처 `'Agent'` **정확**. team 모드(TeamCreate)는 PreToolUse 갭 → **agent-mode-first 결정을 실측이 뒷받침**. 차후 매처를 `Agent|Task|TeamCreate` 합집합으로 + `HOOK_MATCHER_COVERS_SPAWN` 체크.

## A1 — 커스텀 .claude/agents resolve + tools allowlist 런타임 강제 ✅ RESOLVED (live)
- **가설**: Agent 도구가 커스텀 `.claude/agents/<name>.md`를 resolve하고 tools/model을 spawn 시 바인딩(Mode A의 general-purpose 강등과 정반대).
- **테스트**: `.claude/agents/probe-restricted.md`(model: haiku, tools: Read,Glob,Grep — NO Bash) 정의 후 nested claude에 `subagent_type='probe-restricted'` spawn + Bash 시도 지시.
- **관측**: subagent_type **RESOLVE됨**(unknown 에러 없음). 서브에이전트 Bash **DENIED**, 보유 도구 정확히 `Read, Glob, Grep`(정의의 allowlist와 일치).
- **판정**: 커스텀 agent resolve + **tools allowlist 런타임 강제 확인**. 모델티어 격상(advisory→runtime-enforced)의 토대 성립. (model=haiku 명시 확인은 미실측이나 frontmatter가 honoring됨이 tools 강제로 강하게 입증.)

## R1/R3 — exit-2 차단 메커니즘 ✅ RESOLVED (live)
- **가설**: validate_*.py가 valid:false여도 exit 0이라 prose-invoke에 그침. exit-2 래퍼(gate_or_block)로 승격하면 실제 차단되는가?
- **테스트**: PreToolUse(Bash) hook이 `PROBE_BLOCK_ME` 포함 명령에 exit 2. nested claude에 해당 명령 실행 지시.
- **관측**: nested claude가 verbatim 보고 — "PreToolUse:Bash hook error ... BLOCKED by probe hook (PROBE_BLOCK_ME) ... 실행되지 못했습니다."
- **판정**: PreToolUse exit-2가 **실제로 도구호출을 차단**. → `gate_or_block.py`(validate_*.py JSON→`valid==false`면 exit-2) 메커니즘 **성립**. R3의 `pre_subagent_invocation.py` stdin-무시는 런타임 한계가 아니라 **코드 버그**(P1에서 stdin main 추가로 수정).

## R7(부수 확인) — SessionStart 매처 갭 ✅ 수정 가능 확인
- 스모크 fixture의 SessionStart는 **매처 없이** 배선 → 일반 시작에 발화. 게놈의 `clear|compact|resume` 매처를 매처 없음(전체 start)으로 넓히면 한 세션 긴 빌드도 restore 시도 가능(R7 fix 실현성 확인).

---

## 미실측(비-blocker, 후속/설계 흡수)
- 모델티어 명시 바인딩(haiku vs sonnet 실제 사용): tools 강제로 강하게 추정, P5 dogfood에서 명시 확인.
- team 모드(TeamCreate) 멤버 도구호출 hook 발화: agent-mode-first로 우회, team 승격 시 별도 프로브.
- 토큰 tally 정밀도(CD-1): 런타임 미지수 아님 — 설계가 spawn-count/fanout 기반으로 재정의해 해소.
- PostToolUse exit-2 return-validator 회수(R9): 안 되면 오케스트레이터-invoke on-disk 체크로 폴백.

## 결론
3개 blocker(R1·R2·R3)의 **런타임 가정이 전부 실측 성립**. 피벗은 런타임상 **GREEN**. 남은 일은 엔지니어링(pre_subagent stdin 수정 · gate_or_block 래퍼 · 매처 합집합 · warrant team-aware · 비용 spawn-count 재정의 · 헌법 dual-accept). → **P0(스키마+헌법) 착수 가능**, 단 사용자 명령 대기.
