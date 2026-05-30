# IMPLEMENTATION-STATUS — GROUND TRUTH (M0–M8 구현 완료)

> **이 문서가 다른 모든 reference의 aspirational 서술에 우선한다.** reference가 무엇을 설명하든, 실제로 emit/validate에 구현됐는지는 여기로 확정한다. (출처: `emit_orchestrator.py`·`emit_domain_skill.py`·`audit_harness.py`·`evolve_harness.py`·`eval_topology.py`·`inherit_genome.py`·`validate_harness.py`·`templates/hooks/`·`tests/test_factory.py` 실측. 설계 전모: `design/STRATEGY-AND-DESIGN.md`.)
>
> **현 상태: 58 factory tests green, 4 예제 validate 0/0, idoforgod 8 use case 전부 conform, in-project 오버레이 설치(B2)·lift 빌드배선(P1.3)·h2h 측정보강(P1.4) 완료.**

## ✅ 구현·검증 완료 (M0–M8)

### M0 — 프리미티브-위임 모순 봉쇄 (절대규칙)
- `workflow`(Mode-A `workflow.js`)는 **제품에서 은퇴**(`WORKFLOW_RETIRED`). 예제 4개 team 모드 마이그레이션. `emit_workflow.py`는 **공장내부 측정 전용**.
- 자식 `RUNTIME.json`/`CLAUDE.md`가 은퇴 런타임을 광고하던 누수 스크럽(`RUNTIME_MANIFEST_CLEAN`). `emit_orchestrator.py:113` 스키마-참조 버그 수정(node.output_schema 사용).
- **발화 hook 3종 신규**(`templates/hooks/`): `spawn_counter`(`budget.spawns_used` 증분 → 천장 발화), `sot_init`(`state.yaml` 시드), `qa_gate_runner`(L0-L2를 `gate_or_block`로 발화, evidence-gated — L0 in-hook anti-skip + L1/L1.5/L2 fire-on-presence). 실증: spawn ceiling exit-2 발화, 누락 산출물 → L0 차단.
- **실제 team emit**: `execution_mode=team`이 `TeamCreate/TaskCreate(deps)/SendMessage/TeamDelete` 생성(`TEAM_EMIT_PRESENT`) — agent emit과 더 이상 byte-동일 아님.

### M1 — 4계층 QA + Context Preservation 일급화
- 오케스트레이터가 `## 메모리 운영`(Tier I) 섹션 emit(`CONTEXT_PRESERVATION_FIRSTCLASS`). review 노드의 reviewer/fact-checker 파일 존재 강제(`REVIEW_AGENT_PRESENT`). `HOOK_REGISTERED`에 `save_context` 추가.

### M2 — A2 all-6 floor + 6 토폴로지
- 모든 빌드 하네스가 6종 프리미티브 전부 인스턴스화(`ALL_PRIMITIVES_PRESENT`: 호출형 `TeamCreate(`+`Agent(`). 팀 graceful-degrade(`TEAM_GRACEFUL_DEGRADE`).
- `topology` enum 3→7. **supervisor·expert-pool·hierarchical·fan-out-fan-in을 first-class emit 타겟으로 구현**(`_topology_addendum` + `TOPOLOGY_PRIMITIVE_CONSISTENCY`).

### M3 — 하이브리드 도메인 스킬 (idoforgod who=agent / how=skill)
- `node.skill_authoring{mode:inline|skill, reason, shared_by}`(머신체크). `emit_domain_skill.py`: `mode=skill` 노드만 `.claude/skills/<harness>-<id>/SKILL.md` 저작. `SKILL_AUTHORING_JUSTIFIED`(reason 검증, reuse→shared_by≥2)·`INLINE_NO_ORPHAN_SKILL`·`LIFT_UNMEASURED`(warn).

### M4 — Phase-0 상태감사
- `audit_harness.py`: new/extend/maintain 분기 + **결정론 드리프트**(디스크 agents/skills ↔ graph 계약 set-diff) → `.harness/audit.json`(`AUDIT_VERDICT_PRESENT`).

### M5 — Phase-7 진화 루프
- `evolve_harness.py`: 피드백 유형→대상 라우팅 테이블 + `.harness/change-history.jsonl`(append-only) + `--proactive`(같은 유형 2회↑ 자동 제안). `EVOLUTION_WIRED`·`EVOLUTION_LOG_PRESENT`.

### M6 — RLM 교차-실행 메모리 (Tier II)
- `inherit_genome._init_memory_store`: `.harness/memory/`(`archive.manifest.json`·`domain-knowledge.yaml`·`runs/index.jsonl`·`risk/decisions.jsonl`) 시드, **idempotent 누적**(재emit이 기존 run 미파괴). 오케스트레이터 Tier-II RLM 회상(Grep index)·기록 레시피. `MEMORY_SKILL_SECTION`·`MEMORY_STORE_INIT`.

### M7 — 8 use case parity 평가
- `eval_topology.py`(순수 matcher) + `TestEightUseCases`: idoforgod README 8 use case 전부 **빌드레벨 conform**(토폴로지+exec_mode+all-6+DNA). 5개 토폴로지(fan-out-fan-in·pipeline·producer-reviewer·supervisor·hierarchical) 행사. 런레벨 h2h는 별도 레인.

### M8 — 정직성
- design 문서의 죽은 `+38pp` 교정 + `STALE_BENCHMARK` factory 가드(design/ 스캔). `MEASUREMENT_DRIFT` 구현됨(produced-harness README/SKILL 스캔).

### 측정 (head-to-head, stamped)
- **n=5(deep-research) + 다도메인 추가 → median(C2)=1.0 vs median(C3)=0.875 → +12.5pp `INCONCLUSIVE`** (CYS 우세, 15pp 마진 미달). 이전 n=1 −16.67pp `BASELINE-WINS`를 뒤집음. 활성 **L2 적대적 리뷰**가 baseline(no-harness opus)의 A4(미검증 주장 잔존)·A6(통계 날조) 실패를 잡은 것이 격차. **약한 데이터를 날조하지 않음**(+37.5pp 교훈). `evals/deep-research.verdict.json`.

### P1.2 — in-project 오버레이 설치 (B2) ✅
- `emit_orchestrator.py <TARGET> --in-project`: idoforgod식 **기존 호스트 프로젝트 오버레이 설치**. 자족(self-contained) 기본은 불변.
- **호스트 보존**: 루트 `CLAUDE.md`(포인터만 append)/`AGENTS.md`/`README.md`/`soul.md`, 호스트 `.claude/agents|skills|config|hooks`(동명 파일은 `rsync --ignore-existing`로 **호스트 우선** — 튜닝된 보안 hook 포함) 절대 미클로버. 노드 agent는 `cys_emitted` provenance 마커 + **동명 호스트 agent 충돌 시 emit 거부**.
- **L2 DNA 예외(force-install)**: 적대적 리뷰 agent(`reviewer`/`fact-checker`)는 head-to-head 변별력의 핵심이라 **게놈판을 강제 설치**한다(host-wins 비클로버에서 제외). 충돌 시 호스트 원본은 `.harness/genome/displaced/`로 **백업**(파괴 없음) + stderr 통지 → `REVIEW_AGENT_PRESENT`가 "엉뚱한 호스트 reviewer"로 통과하는 것을 방지.
- **게놈 부분집합**: `.claude/hooks`(런타임 DNA) + `.claude/{agents,skills,config}` 모두 비클로버 union. ~440KB 헌법 + `docs/`는 **`.harness/genome/`로 재배치**(어떤 런타임 hook도 루트 .md를 *읽지 않음* — guarded 문서-동기 lint뿐 — 검증됨). `prompt`/`prompt-runner`/`translations` 미설치. 로그 디렉토리는 `.harness/` 하위.
- **settings 안전**: 호스트 hook·permissions 보존 + 게놈 hook union + 게놈 `permissions.deny` 보안 union(`_union_perms`). 호스트 settings.json이 **비객체(`[]`/`null`)면 graceful coerce**, **파싱불가면 emit 거부**(호스트 제어 무단 폐기 금지).
- **모드 전환 가드**: `install_mode` 마커(`.harness/GENOME.json`)로 `validate`가 `GENOME_PRESENT`(루트 vs `.harness/genome/`)·`W1_GENOME`·doc/measurement-drift 경로 자동 분기(마커 손상 시 `.harness/genome/CLAUDE.md` 존재로 구조적 감지). **다른 모드로 재emit은 거부**(in-project↔self-contained 전환 시 호스트 클로버 방지). 재emit idempotent(포인터 1회).
- **검증**: CLI emit+validate 0/0, **52 factory tests**(+6 in-project), **3-lens 적대적 리뷰**(correctness·host-safety·parity)에서 발견된 4 MAJOR(비객체 settings 크래시·파싱불가 호스트손실·hook 클로버·reviewer 누락) 전부 수정·재현테스트 추가.

### P1.3 — lift 빌드 배선 ✅ (게이트에 이빨)
- `lift_gate.py score <results> --out <skill>/lift_verdict.json`: 측정 결과(verdict)를 validate가 읽는 정확한 경로에 기록.
- validate: 미측정=`LIFT_UNMEASURED`(constants.json `LIFT_UNMEASURED` 정책, 기본 `warn`→`error` 전환가능); **측정했으나 baseline 미달(`decision≠register`)=`LIFT_REFUSED`(hard error)** — baseline에 진 스킬은 출하 불가(inline하거나 개선). 측정-실패가 빌드를 실제로 막는다(이전엔 presence-warn만).

### P1.4 — h2h 측정 보강 ✅ (StructuredOutput flakiness)
- `h2h_suite.workflow.js`: `tryAgent` 재시도 래퍼(null/throw 시 ATTEMPTS회, 라벨 변주로 캐시회피) + **flake run은 0점이 아니라 DROP**(보고서/채점 누락 run을 median에서 제외 → 가짜 0이 중앙값 왜곡 불가) + provenance `n_attempted/n_valid/n_dropped`.
- `h2h_aggregate.py`: 무효 run(`valid:false`/키누락) 첫 발견에 raise하던 것을 **필터링**으로 변경(부분실패 suite를 정직하게 집계) + `n_dropped` 보고. 이전 n=5 측정의 7/12 실패 패턴을 구조적으로 흡수.

## ⏳ 남은 일 (P1/P2)
- **references/ 전면 재구성** — `architecture-patterns.md`·`graph-and-orchestration.md` 등에 일부 옛 'workflow.js' 전제 서술 잔존. **본 문서가 우선.** D1의 8-파일 맵(`genome-and-runtime.md`·`evolution-and-memory.md`·`skill-and-agent-authoring.md` 신설)은 후속.
- **라이브 풀세션 end-to-end 증명** — emit 후 `cd <harness> && claude` 실세션에서 전 DNA(게이트·메모리·팀) 발화 재확인.
- **CYS-WINS 재측정** — 어려운/적대적 도메인·스코어카드로 ≥15pp 시도(현재 +12.5pp는 현대 opus가 강해 구조적으로 1 assertion 격차).

## ❌ 폐기된 규칙 — 더 이상 적용 안 함
- **NO_COMMANDS** 폐기(게놈 commands 정상; 새 도메인 커맨드는 직접 안 만듦). **"모든 에이전트 opus"** → role-tier 정책. **"team이 기본 / Mode-A(workflow)가 기본"** → 둘 다 폐기: **workflow 은퇴**, 빌드 하네스는 **all-6(team/hybrid)**.

## 규약 메모
- **producer-reviewer topology ≠ reflect-then-revise mechanism** — topology(2노드 루프)와 mechanism은 독립.
- **skill_authoring 하이브리드** — `reuse`(shared_by≥2)/`complex`/`conditional`일 때만 도메인 스킬 저작, 그 외 inline(throwaway 스킬 방지).
- **A1 경계** — Python은 결정론 가드레일(차단/저장/측정/파싱)만; 도메인 판단·생성은 프리미티브.
