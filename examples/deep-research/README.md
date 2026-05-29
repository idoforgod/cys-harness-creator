# deep-research (CYS Harness Creator dogfood)

CYS Harness Creator로 생성된 첫 하네스. Mode A(Workflow 결정론 서브에이전트 런타임).
도메인 한 문장("심층 리서치 팀")을 검증된·비용통제된·재개가능한 파이프라인으로 변환한 예시.

## 파이프라인 (4 Phase)

- **Phase 1 — gather** (researcher, haiku): 웹 검색으로 후보 소스·초안 주장 수집
- **Phase 2 — fetch** (fetcher, haiku): 소스 fetch·주장에 source_id 부착·미지원 주장 제거
- **Phase 3 — verify** (verifier, sonnet + opus critic): reflect-then-revise로 적대적 팩트체크·교정 (max_rounds=2)
- **Phase 4 — synthesize** (synthesizer, opus): 검증된 findings → 인용 포함 리포트

## 실행

```bash
python3 ../../warrant.py --graph .harness/graph.json     # 비용 밴드(토큰) 확인·승인
python3 ../../emit_workflow.py .                          # graph.json → .harness/workflow.js
python3 ../../validate_harness.py .                       # 정적 게이트 통과 확인
# 그 다음 Claude Code에서:  Workflow({ scriptPath: ".harness/workflow.js", args: { query: "<주제>" } })
```

## 구조

- `.harness/graph.json` — 계약(spine, single source of truth)
- `.harness/workflow.js` — emit된 Mode A 런타임 (수정 금지; graph.json 편집 후 재emit)
- `.harness/harness.lock` — write-path 소유 정적 맵 (validator WRITE_PATH_OVERLAP)
- `.harness/MANIFEST.json` — 최소 provenance
- `.claude/agents/*.md` — 역할 정의 (model 티어 + least-privilege tools)
- `.claude/skills/deep-research-orchestrator/SKILL.md` — graph의 사람용 뷰
- `schemas/*.json` — 노드 output 스키마 (workflow.js에 인라인됨)
- `evals/deep-research.scorecard.json` — head-to-head 단일 scorecard fixture
