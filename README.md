# CYS Harness Creator

도메인 한 문장 → 검증된·비용통제된·재개가능한 **풀스택 Claude Code 프리미티브 하네스**(orchestrator skill + `.claude/agents` + Sub-agents + Agent Teams + Hooks + `.claude/skills` + 상속 AWF 게놈 + 장기기억)를 생성하는 메타스킬 팩토리. 개인/내부용.

**기준(목표): `idoforgod/harness` 기능 parity** — idoforgod의 모든 기능을 동일하게 구현 가능하되, 그 위에 CYS의 검증된 강점을 더한다: 머신체크 가능한 `graph.json` 계약, 역할-티어 정책, 비용 거버넌스, 게놈 DNA 발화, 측정 인프라. (성능 우월성이 아니라 기능적 완전성이 기준.)

> **절대규칙(A1):** 산출 하네스의 *실행*은 100% Claude Code 프리미티브(Agent / TeamCreate / SendMessage / TaskCreate). 결정론 Python(hook·검증기·메모리)은 실행이 아니라 가드레일(발화·강제·기억)이다. **Mode-A `workflow.js`는 제품에서 은퇴** — 공장 내부 측정 도구로만 생존.

설계 전모: `design/STRATEGY-AND-DESIGN.md`. 구현 현황(모든 서술에 우선): `skills/harness-creator/references/IMPLEMENTATION-STATUS.md`.

## 핵심 차별 (vs idoforgod/harness)
| 영역 | idoforgod | CYS |
|------|------|-----|
| 규칙 | advisory prose | `validate_harness.py` 정적 **강제**(~38 코드, 위반 시 빌드 실패) |
| 실행 | 없음(.md만 생성) | **라이브 오케스트레이터 SKILL** = Claude 프리미티브로 그래프 실행, 상속 게놈 hook이 발화 |
| 계약 | 산문 | 불변 머신체크 `graph.json`(7 topology × 4 decision-mechanism) |
| 비용 | `model:opus` 전역 | 역할→티어 정책 + `warrant.py` 사전 토큰밴드 승인 + 런타임 spawn ceiling(exit-2) |
| 품질 | prose-compliance | L0–L2 게이트가 hook으로 **발화**(`qa_gate_runner`/`gate_or_block`) |
| 기억 | 세션한정 | Tier I Context Preservation + Tier II RLM 교차-실행 도메인 메모리 |
| 측정 | 자기참조 | blind 헤드투헤드 C2 vs C3 scorecard(능가 or **정직 미달보고**) |
| 설치 | in-project만 | 자족(self-contained) + **in-project 오버레이**(`--in-project`, 호스트 보존) |

## 도구 (제품 emit 경로)
- `skills/harness-creator/SKILL.md` — 메타스킬 진입점(요청 → 4-스테이지 워크플로우 → 하네스)
- `warrant.py` — PRE 게이트(필요한가?) + team-aware 토큰 비용밴드
- `audit_harness.py` — R1 상태감사(new/extend/maintain + 드리프트)
- `emit_orchestrator.py` — **I3 제품 emit**: graph.json → 오케스트레이터 SKILL + agents + 게놈전수 + 메모리 store (`--in-project` 오버레이 지원). `emit_domain_skill.py`·`inherit_genome.py` 자동 호출
- `validate_harness.py` — I5 빌드 게이트(exit 0/1/2)
- `lift_gate.py` · `h2h_aggregate.py` · `eval_topology.py` — I6/E2 측정(lift 게이트 · 헤드투헤드 · 8 use case parity)
- `evolve_harness.py` — E3-E6 진화(피드백 라우팅 + change-history + proactive)
- `model-tier-policy.js` — role→tier SoT · `graph.schema.json` — 계약 스키마 · `constants.json` — 튜너블 상수 · `lib/toposort.py` — 결정론 토소트
- `emit_workflow.py` · `h2h_suite.workflow.js` — **공장 내부 측정 전용**(제품 emit 아님)

## 빠른 검증 (프리미티브 경로)
```bash
python3 warrant.py --graph examples/deep-research/.harness/graph.json   # 비용밴드 (→ 사람 승인)
python3 emit_orchestrator.py examples/deep-research                     # graph.json → 오케스트레이터 SKILL + agents + 게놈
python3 validate_harness.py examples/deep-research                      # PASS (exit 0)
python3 -m pytest tests/test_factory.py -q                              # 60 factory tests
# in-project 오버레이 설치: python3 emit_orchestrator.py <host-project> --in-project
# 실행 핸드오프: cd <harness> && claude  →  <name>-orchestrator 스킬 트리거 (그 세션 hook이 발화)
```

## 상태 (전 백로그 완료)
- ✅ **M0–M8** — 프리미티브 위임 모순 봉쇄 · 4계층 QA + Context Preservation 일급화 · A2 all-6 프리미티브 floor + 7 토폴로지 · 하이브리드 도메인 스킬 · Phase-0 감사 · Phase-7 진화 · RLM 교차-실행 메모리 · 8 use case parity · 정직성 가드
- ✅ **P1.2** in-project 오버레이 설치(호스트 보존, 3-lens 적대적 하드닝) · **P1.3** lift 빌드배선(게이트 이빨) · **P1.4** h2h StructuredOutput 견고화
- ✅ **references/** D1 8-파일 맵 재구성 · **P2** 라이브 DNA 발화 end-to-end 증명(emit된 하네스 hook 구동)
- **60 factory tests green · 4 예제 validate 0/0**

## 측정 (정직, stamped)
blind 헤드투헤드(C2=CYS 하네스 vs C3=no-harness opus, 8-assertion scorecard, median + 15pp 마진):
- deep-research n=5 → **+12.5pp `INCONCLUSIVE`**(CYS 우세, 마진 미달)
- verification-heavy n=5 → **0.0pp `INCONCLUSIVE`**(천장 동률, 둘 다 8/8)

> **정직한 결론:** 현대 opus single-pass가 객관적 scorecard에서 이미 천장이라 하네스가 **마진으로 이기는 것은 구조적으로 불가**. 더 많은 도메인을 뒤져 ≥15pp를 낚는 것은 벤치마크 게이밍이므로 하지 않는다(+37.5pp 교훈). 하네스의 가치는 scorecard 승리가 아니라 **parity(목표 충족) + 결정론적 인프라**(DNA 발화·비용거버넌스·머신체크 계약)에 있다.

## 알려진 통합 경계
커스텀 `agentType`(researcher 등)는 **하네스가 활성 Claude Code 세션의 CWD일 때** `.claude/agents/`에서 해석된다. 따라서 라이브 실행은 `cd <harness> && claude`로 새 세션을 열어 수행한다(그 세션의 `settings.json` hook이 발화 — 공장 세션이 아님).
