# ADR — 3층위 장기기억 self-hosting (회상 배선)

- **Status**: Accepted (박사님 승인, 2026-05-31)
- **관련 기억**: `three-tier-memory-self-hosting` (project memory — 최우선 원칙)
- **선행 평가**: 산출 하네스 run에서 "장기기억이 데이터 파이프라인 연결조직으로 작동했는가 → NO". 근본 원인은 팩토리 emit 로직.

## Context — 근본 원인 (코드 교차검증 완료)

장기기억의 **read-side**(회상·주입·릴레이)가 오케스트레이터 SKILL의 `## 메모리 운영` 섹션에 **prose로만** 존재하고 실행 단계(Phase 0/2)에 **배선되지 않았다**. `validate_harness.py`는 그 섹션의 **존재**(`MEMORY_SKILL_SECTION`·`MEMORY_STORE_INIT`·`CONTEXT_PRESERVATION_FIRSTCLASS`)만 검사하고 **배선(wiring)**을 검사하지 않아, unwired 상태가 빌드 게이트를 통과한다. → "명세는 있으나 행위로 배선 안 됨" + "presence ≠ wiring" 메타패턴.

더 깊은 결함: 팩토리(cys-harness-creator)는 게놈 메모리를 산출물에만 전수(`inherit_genome._init_memory_store(harness_dir)`)하고 **자기 자신은 `.harness/`조차 없다** — "장기기억 일급"을 표방하면서 게놈을 전수만 하고 발현하지 않는 모순. self-hosting 원칙(자동 교정 루프에서 확립)과도 배치.

## Decision — 3층위 통일 + self-host dogfood

장기기억은 **세 층위 모두**에서 동일 메커니즘으로 작동한다. 회상 → 주입 → 릴레이 → 기록 사이클의 **단일 구현**을 팩토리가 dogfood한다(새 별도 시스템 없음).

| 층위 | "run" | store | 회상 시점 | 기록 시점 |
|------|-------|-------|-----------|-----------|
| **1+2 팩토리/빌드** | 하네스 1개 빌드 | 팩토리 `.harness/memory/` (신규) | Research 이전 (유사 빌드 회상) | Evolution (빌드 경험 기록) |
| **3 산출 하네스** | 도메인 작업 1회 | 산출 하네스 `.harness/memory/` (기존) | 오케스트레이터 Phase 0 | Phase 3 (증분) |

층위 1 = 층위 2 (팩토리의 유일한 도메인 작업이 빌드이므로 같은 store).

## 구현 매핑 (P0a → P0b → P0, 층위 1→2→3 순)

- **P0a (층위 1 부트스트랩)**: `_init_memory_store(dir, kind="domain"|"build")` — seed 문구를 kind로 분기. 팩토리 루트에 `kind="build"` store 시드. 기존 4 예제(deep-research·competitor-watch·design-decision·ticket-triage)를 **빌드 이력으로 임포트**(콜드 해소). 진입점: `bootstrap_factory_memory.py`.
- **P0b (층위 2 회상 배선)**: `harness-creator SKILL.md` 워크플로우에 — RESEARCH 이전 "STAGE 0: 빌드 이력 회상"(Grep 팩토리 `memory/runs/index.jsonl` → 유사 빌드 Read → P1 graph 저작에 주입) + EVOLUTION에 "빌드 경험 기록" 추가.
- **P0 (층위 3 회상 배선)**: `emit_orchestrator.py` Phase 0을 "회상 + 컨텍스트 + SOT"로 확장, 본문에 회상 실행 단계(warm: Grep index → Read run → domain-knowledge Read → `_workspace/_recall.json` 산출 + audit_log; cold: 시드/no-prior 명시) 추가.
- **게이트 self-audit**: `MEMORY_RECALL_WIRED` 신설 — (a) 산출 하네스 오케스트레이터 SKILL + (b) 팩토리 harness-creator SKILL 둘 다 회상 배선을 정적 검사. presence → wiring 승격.

## A1 · RLM 경계 (불변)

- 벌크 데이터는 `_workspace/` 파일시스템. **검증된 사실·결정 atom만 메모리 릴레이.**
- 회상·증류·주입·판단은 프리미티브(Claude)의 도메인 작업. Python은 경로·인덱스·시드·게이트(차단/측정/파싱)만.
- 메모리는 통째 로드 금지 — 얇은 `index.jsonl`을 Grep → 매치된 run만 Read (RLM).

## Consequences

- **이득**: 박사님 기준("데이터가 메모리를 통해 파이프라인처럼") 충족. 팩토리가 빌드할수록 자기 메모리에 축적 → 일관성·학습. 층위 1·2를 먼저 세우면 층위 3 emit이 dogfood로 검증됨.
- **위험**: 회상이 콜드(첫 run)에서 0 기여는 정상 — 4 예제 시드로 완화. 무한 회상 루프는 RLM(매치된 run만 Read)으로 차단.
- **호환**: 기존 산출 하네스는 수정된 팩토리로 재emit(손작성 본문 보존) 시 회상 배선이 주입됨.
