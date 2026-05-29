# CYS Harness Creator

차세대 하네스/에이전트팀 팩토리. `idoforgod/harness`(prose 스캐폴더)를 **머신체크 게이트 + 실재 실행 런타임 + 비용 거버넌스 + 헤드투헤드 측정**으로 능가하는 것이 목표. 개인/내부용.

설계 근거: `design/strategy.md`(전수조사+전략), `design/M0-spec.md`(구현 명세), `design/_raw/`(8 컴포넌트 원설계).

## 핵심 차별 (vs 원본)
| 영역 | 원본 | CYS |
|------|------|-----|
| 규칙 | advisory prose | `validate_harness.py` 정적 **강제** (위반 시 빌드 실패) |
| 실행 | 없음(.md만 생성) | **Mode A: `workflow.js` emit** = Workflow 도구 결정론 런타임(budget ceiling·resume·schema) |
| 비용 | `model:opus` 전역 | 역할→티어 정책 + `warrant.py` 사전 토큰 밴드 승인 |
| 측정 | +60% 순환참조 | 헤드투헤드 C2 vs C3 scorecard (능가 or 정직 미달보고) |
| 조정 | 토폴로지만 | 토폴로지 × decision-mechanism(single/vote/debate/reflect) |

## 도구
- `skills/harness-creator/SKILL.md` — 메타스킬 진입점(요청→하네스)
- `warrant.py` — Phase -1 게이트 + 토큰 비용밴드
- `model-tier-policy.js` — role→tier SoT + V1/V2/V3 검증규칙
- `graph.schema.json` — graph.json 계약 스키마
- `emit_workflow.py` — graph.json → workflow.js (Mode A, 순수 구조변환)
- `validate_harness.py` — 정적 게이트 (exit 0/1/2)
- `constants.json` — 튜너블 상수 단일 SoT (가설값, dogfood 후 재보정)
- `lib/toposort.py` — 결정론 토소트(emitter+validator 공용)

## 빠른 검증 (M0 정적 게이트)
```bash
python3 warrant.py                                  # deep-research → build-harness/pipeline/reflect/LOW $0.34
node model-tier-policy.js examples/deep-research/.harness/graph.json
python3 emit_workflow.py examples/deep-research      # graph.json → workflow.js
node --check examples/deep-research/.harness/workflow.js
python3 validate_harness.py examples/deep-research   # PASS (exit 0)
```

## M0 상태
- ✅ criterion 1: 메타스킬이 완전한 하네스 생성 (deep-research dogfood 전체 조립)
- ✅ criterion 2: validate clean PASS / broken(agent 삭제) FAIL
- ✅ criterion 4: warrant 분기(answer-directly/single-agent/build-harness) + 비용밴드
- ✅ criterion 6: SubagentStop 토큰로그 hook 존재
- ⏳ criterion 3·5: **라이브 dogfood 실행** 필요 — 하네스를 활성 프로젝트로 열고(`cd examples/deep-research`, 커스텀 agentType 해석을 위해) budget 디렉티브와 함께 `workflow.js` 실행 → budget.total 정지/resume + C2 vs C3 헤드투헤드.

## 알려진 통합 경계
커스텀 `agentType`(researcher 등)는 **하네스가 활성 Claude Code 프로젝트일 때** `.claude/agents/`에서 해석된다(플랫폼 정상 동작). 따라서 라이브 실행은 하네스 디렉토리를 CWD로 하여 수행한다. (M2에서 import 마이그레이션 시 동일 규칙 적용.)
