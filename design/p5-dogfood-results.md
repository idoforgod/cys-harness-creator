# P5 — 라이브 dogfood 결과 (실측)

> 2026-05-29. agent-mode dogfood(`dogfood-research`, `_workspace/dogfood/`, 게놈 active 전수, validate PASS 0/0)를 nested `claude -p` 라이브 세션으로 실행. 질의: "Python 최초 공개 연도 + 창시자".

## ✅ 실행 + AWF 활성화 PROVEN (피벗의 핵심 약속 실증)

라이브 세션 부수효과로 확정(`claude -p` exit 0):

| 증거 | 실측 | 의미 |
|------|------|------|
| `runs/log.jsonl` (SubagentStop hook) | **4 spawn: researcher · fetcher · verifier · reviewer** (동일 session_id) | 커스텀 `.claude/agents` agentType **resolve 확인**(Mode A general-purpose 강등의 정반대) |
| 그 중 `reviewer` | verify 노드 `review:{agent:reviewer}` 속성으로 wired → **실제 spawn** | **L2 적대적 리뷰가 Mode A 휴면 → LIVE 발화** — 사용자 핵심 요구 충족 |
| `work_log.jsonl` (PostToolUse update_work_log) | 도구 시퀀스 `{Bash:8, Agent:4, Write:3}` (4859B) | PostToolUse hook 발화 + Agent 4회(= 4 spawn 일치) |
| SubagentStop `cys_log_tokens` | 4회 기록 | CYS 토큰로그 hook 라이브 발화 |

**결론**: emit_orchestrator로 만든 프리미티브 하네스는 라이브 호스트 세션에서 **전체 파이프라인이 실행**되고, 상속된 **AWF 게놈이 active**(커스텀 agent resolve + 적대적 reviewer spawn + lifecycle hook 발화)다. 이는 Mode A(`workflow.js`)에서 구조적으로 불가능했던 것 — 피벗 thesis가 **컴포넌트(P-1)에 이어 전체 하네스 수준에서도** 실증됨.

### 부분 관측 (비-blocker)
- Stop hook의 `latest.md` 스냅샷은 미생성(work_log만 누적). generate_context_summary의 ap_state-gated 경로가 prose 오케스트레이터의 state.yaml 작성에 의존 — 빠른 `-p` 런에서 state.yaml 미작성. 후속: 오케스트레이터 Phase 0이 state.yaml을 확실히 쓰도록 강화(설계에 이미 명시).
- `claude -p` 최종 stdout 텍스트는 캡처되지 않음(headless+서브에이전트 버퍼링) — 부수효과 증거가 실행을 확정하므로 비-blocker.

## ⏸️ n≥5 h2h 재측정 — 정직한 미완 (날조 금지)

**현 상태**: 유일 stamped h2h는 여전히 **n=1, BASELINE-WINS −16.67pp**(Mode-A `workflow.js` 측정). 피벗된 프리미티브 하네스(L0-L2 + 적대적 reviewer active)가 이를 뒤집는지는 **아직 미측정** — **시도했으나 계정 사용량 한도에 막힘**.

**시도 + 블로커(2026-05-30 실측)**: `_workspace/h2h/run_h2h.py`로 동일 deep-research 과제에 C2(피벗 하네스) vs C3(no-harness) ×5 blind 채점을 시도. 결과:
- C3 단일 deep-research run은 **~5분 소요**(`run0_C3.md` 7388B 산출 — A5/A8 충족하는 강한 답변; C3가 이 과제에 강함은 n=1의 C3=1.0과 정합).
- 그러나 무거운 run 1–2회로 **계정 세션 사용량 한도 도달**: `"You've hit your session limit · resets 11:20am (Asia/Seoul)"`. trivial 호출(7s)은 통과하나 멀티분 리서치 run이 quota를 빠르게 소진.
- 따라서 n≥5 라이브 측정은 **외부 사용량 한도라는 하드 제약**에 막혀 단일 윈도우로 완료 불가. 한 윈도우 quota로 10개 무거운 run(C2×5+C3×5+채점)을 못 채움.

**+37.5pp 교훈 준수**: 약한/부분 데이터를 n=5로 **날조하지 않음**. 측정은 *실측*이어야 한다.

**재측정 준비 완료 (resumable)**: 드라이버가 ① 타임아웃에도 완성본 회수 ② **점진적 저장 + resume**(이미 기록된 run 인덱스 skip, 여러 리셋 윈도우에 걸쳐 누적) ③ 사용량 한도/연속 빈응답 감지 시 클린 중단. **실행법**: 리셋(11:20am KST) 후 `H2H_N=5 python3 _workspace/h2h/run_h2h.py`를 quota 윈도우마다 반복 → `runs.json` 누적 → 5 run 도달 시 `h2h_aggregate`가 `verdict.json` 산출 → `examples` stamp + `testing-and-measurement.md` 동기화(MEASUREMENT_DRIFT 강제).

**team 모드 기본승격은 이 측정 결과에 게이트**(현재 agent 모드 우선).

## 결론
P5의 *실행/활성화* 질문(프리미티브 하네스가 실제로 돌고 AWF가 발화하는가)은 **PROVEN**. P5의 *경험적 우월성* 질문(no-harness를 능가하는가)은 전용 n≥5 측정으로 남았고, 약한 데이터로 날조하지 않았다.
