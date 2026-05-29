# ticket-triage (CYS Harness Creator example)

CYS Harness Creator로 생성된 dispatch + majority-vote 예시 하네스. Mode A(Workflow 결정론 서브에이전트 런타임).
도메인 한 문장("지원 티켓을 분류·우선순위·라우팅")을 비용통제된·재개가능한 fan-out/fan-in 파이프라인으로 변환한 예시.

topology=**dispatch**: 두 source 노드가 **병렬**로 fan-out 한 뒤 단일 sink로 fan-in 한다.
이 하네스는 majority-vote 노드(독립 ballot N=3, quorum=2, pure-JS reduceMajority 집계)도 함께 보여준다.

## 파이프라인 (3 Phase)

- **Phase 1 — classify_category** (classifier, sonnet, majority-vote n=3 quorum=2 tie_break=first): 티켓 카테고리 분류 (Phase 2와 병렬)
- **Phase 2 — classify_priority** (prioritizer, sonnet, majority-vote n=3 quorum=2 tie_break=first): 티켓 우선순위 평가 (Phase 1과 병렬)
- **Phase 3 — route** (router, haiku, single): 두 승자를 받아 queue·SLA·summary로 병합 (단일 sink)

## 실행

```bash
python3 ../../warrant.py --graph .harness/graph.json     # 비용 밴드(토큰) 확인·승인
python3 ../../emit_workflow.py .                          # graph.json → .harness/workflow.js
python3 ../../validate_harness.py .                       # 정적 게이트 통과 확인
# 그 다음 Claude Code에서:  Workflow({ scriptPath: ".harness/workflow.js", args: { ticket: "<티켓 본문>" } })
```

## 구조

- `.harness/graph.json` — 계약(spine, single source of truth)
- `.harness/workflow.js` — emit된 Mode A 런타임 (수정 금지; graph.json 편집 후 재emit)
- `.harness/harness.lock` — write-path 소유 정적 맵 (validator WRITE_PATH_OVERLAP)
- `.harness/MANIFEST.json` — 최소 provenance
- `.claude/agents/*.md` — 역할 정의 (model 티어 + least-privilege tools)
- `.claude/skills/ticket-triage-orchestrator/SKILL.md` — graph의 사람용 뷰
- `schemas/*.json` — 노드 output 스키마 (draft 2020-12, workflow.js에 인라인됨)
