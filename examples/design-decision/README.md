# design-decision (CYS Harness Creator example)

producer-reviewer + debate-with-judge를 함께 행사하는 최소 예제 하네스. Mode A(Workflow 결정론 서브에이전트 런타임).
도메인 한 문장("기술 설계 결정 내리기")을, 제안자가 안을 내고 토론 심사가 채택할 때까지 반복하는 비용통제·재개가능 루프로 변환한 예시.

## 토폴로지: producer-reviewer (2 Phase, 루프)

- **Phase 1 — propose** (proposer, opus, single): 후보 설계안(추천안 + 대안 + tradeoff) 생산. 프로듀서.
- **Phase 2 — adjudicate** (debater, sonnet 토론자 + opus 심판, debate-with-judge, n=2 max_rounds=2): n=2 적대 토론 후 심판이 `approved` 포함 verdict 산출. 리뷰어.

루프: `propose → adjudicate → (approved? 종료 : propose 재제안)`. `verdict.approved=true`이거나 producer max_rounds(3)에 도달하면 종료.
emitter는 producer-reviewer를 `producer→reviewer` while 루프로 풀고 `reviewer.approved`에서 break하므로, **adjudicate의 verdict 스키마는 반드시 `approved`를 낸다.**

> 주의: 되돌이 edge(adjudicate→propose)는 토폴로지가 암묵적으로 구현한다. `edges`에는 정렬용 forward edge(`propose→adjudicate`)만 둔다 — 리터럴 사이클은 emit 시 toposort에서 막힌다.

## 실행

```bash
python3 ../../warrant.py --graph .harness/graph.json     # 비용 밴드(토큰) 확인·승인
python3 ../../emit_workflow.py .                          # graph.json → .harness/workflow.js
python3 ../../validate_harness.py .                       # 정적 게이트 통과 확인
# 그 다음 Claude Code에서:  Workflow({ scriptPath: ".harness/workflow.js", args: { query: "<결정 문항>" } })
```

## 구조

- `.harness/graph.json` — 계약(spine, single source of truth)
- `.harness/workflow.js` — emit된 Mode A 런타임 (수정 금지; graph.json 편집 후 재emit)
- `.harness/harness.lock` — write-path 소유 정적 맵 (validator WRITE_PATH_OVERLAP)
- `.harness/MANIFEST.json` — 최소 provenance
- `.claude/agents/proposer.md` — 프로듀서 역할(opus single)
- `.claude/agents/debater.md` — 리뷰어 wired agentType. 토론자 패스(sonnet) + 심판 패스(opus)를 한 파일에 담음(deep-research verifier와 동형)
- `.claude/agents/judge.md` — 심판 패스의 사람용 문서(런타임은 debater.md가 수행)
- `.claude/skills/design-decision-orchestrator/SKILL.md` — graph의 사람용 뷰
- `schemas/design.json` / `schemas/verdict.json` — 노드 output 스키마 (workflow.js에 인라인됨). verdict는 `approved`+`chosen`+`rationale`+`concerns`.
