> ⚠️ **구현 현황은 [`IMPLEMENTATION-STATUS.md`](IMPLEMENTATION-STATUS.md)가 우선한다.** 이 문서가 게놈/런타임에 관해 무엇을 서술하든, 실제 emit/validate에 구현됐는지는 그 문서로 확정한다. 출처: `inherit_genome.py`·`emit_orchestrator.py`·`validate_harness.py`·`templates/hooks/` 실측.

# 게놈 상속과 런타임 (genome-and-runtime)

> ⚠️ **PIVOT 이후 정설**: 산출 하네스의 실행 런타임은 **단 하나 — emit된 오케스트레이터 SKILL**(100% Claude Code 프리미티브: Agent / TeamCreate / SendMessage / TaskCreate)이다. Mode-A `workflow.js`는 **제품에서 은퇴**했고 오직 **공장내부 측정 도구**(`emit_workflow.py`·`h2h_suite.workflow.js`·lift probe)로만 잔존한다. 이 문서에서 `workflow.js`는 "공장내부 측정"으로 명시된 자리에만 등장한다.

이 문서가 다루는 것은 **하네스의 운영 후반부(back-half)**다 — 도메인 그래프가 어떻게 설계되느냐(전반부)가 아니라, 모든 하네스가 상속받는 AgenticWorkflow(AWF) 운영 머신이 *어떤 hook으로 배선되어 라이브 세션에서 발화하는가*, 그리고 그 머신이 두 가지 설치 모드(self-contained / in-project 오버레이)로 *어떻게 이식되는가*이다.

---

## 목차

1. [상속 모델: 전수(전체)·자족·검증](#1-상속-모델-전수전체자족검증)
2. [상속 DNA → hook 배선 (각 DNA가 어떻게 발화하는가)](#2-상속-dna--hook-배선-각-dna가-어떻게-발화하는가)
3. [두 설치 모드: self-contained vs in-project 오버레이](#3-두-설치-모드-self-contained-vs-in-project-오버레이)
4. [prompt-runner 배제 (vendored-but-inert)](#4-prompt-runner-배제-vendored-but-inert)
5. [RUNTIME.json: 단 하나의 canonical 런타임](#5-runtimejson-단-하나의-canonical-런타임)
6. [라이브 세션 launch 핸드오프](#6-라이브-세션-launch-핸드오프)
7. [validate가 강제하는 게놈 계약](#7-validate가-강제하는-게놈-계약)

---

## 1. 상속 모델: 전수(전체)·자족·검증

**USER MANDATE (`inherit_genome.py` 모듈 docstring):** cys-harness-creator가 만든 모든 하네스는 AWF의 *전체* 기능 머신을 상속해야 한다 — self-contained, 실제 코드 verbatim, 모든 하네스, 항상. "통합만 되고 전수(유전)되지 않으면 무의미."

- `genome/` = AWF 기능 머신의 **1회성 vendored 스냅샷**. AWF는 READ-ONLY 상류이며, AWF가 바뀌면 수동으로 재-vendor한다.
- `inherit_genome.inherit(harness_dir, ...)`은 그 스냅샷을 자식 하네스로 **이식(transplant)**한 뒤, **실제로 로드되는지 검증**한다 — 단순 복사가 아니라 기능 존재 증명이다.

이식 절차(`inherit`, idempotent):
1. **이식** — self-contained면 `genome/`을 하네스 루트로 `rsync`(`README.md`·`.claude/settings.json` 제외), in-project면 `_transplant_overlay`로 오버레이.
2. **settings.json 병합**(`_merge_settings`) — 호스트 보존 union(§2·§3).
3. **CYS hook 6종 설치** — `templates/hooks/` → 자식 `.claude/hooks/scripts/`.
4. **CLAUDE.md 포인터 append** — 모드별 문구(self-contained / in-project), 1회만.
5. **런타임 디렉토리 생성** — `.claude/context-snapshots`·`.claude/agent-memory`·`pacs-logs`·`verification-logs`(in-project은 로그 디렉토리를 `.harness/` 하위로 둠).
6. **Tier-II 교차-실행 메모리 시드**(`_init_memory_store`, M6).
7. **provenance + RUNTIME 매니페스트 stamp** — `.harness/GENOME.json` + `.harness/RUNTIME.json`.
8. **기능 검증**(`_verify`) — `.claude/hooks/scripts/`의 모든 `.py`를 `py_compile`하고, 공유 척추 `_context_lib`를 격리 subprocess에서 import한다. 에러 리스트를 반환한다(0개여야 통과).

> **CYS hook 6종**(`_CYS_HOOKS`): `cys_log_tokens.py`·`gate_or_block.py`·`budget_block.py`·`spawn_counter.py`·`sot_init.py`·`qa_gate_runner.py`. 이 중 뒤 4개가 상속 DNA를 *발화*시키는 인터록이다(§2).

---

## 2. 상속 DNA → hook 배선 (각 DNA가 어떻게 발화하는가)

게놈을 *상속*하는 것만으로는 부족하다 — DNA가 라이브 세션에서 **발화**해야 한다. `_merge_settings`가 각 DNA를 settings.json hook 이벤트에 배선한다. 아래는 DNA별 배선·발화 메커니즘이다(모든 hook 명령은 `_hook_cmd`로 `if test -f .../scripts/<hook>.py; then python3 ...; fi` 가드 형태로 들어간다 — 파일 부재 시 graceful no-op).

### (A) Context Preservation 사이클 — 세션 연속성 + 장기기억 (Tier I)

컨텍스트 보존 hook은 게놈 settings.json 자체에서 온다 — self-contained 경로에선 `_merge_settings`가 `base = genome`을 직접 채택해 이들이 그대로 실린다. in-project/재emit 설치에선 `_union_hooks`가 이들을 호스트의 기존 settings에 union한다(command-set 시그니처가 이미 있으면 skip). 어느 경로든 `HOOK_REGISTERED`가 `context_guard.py`·`save_context.py` 배선을 강제한다. 발화 경로:

- **`context_guard.py`** (게놈, 컨텍스트 보존 디스패처) — 게놈 settings가 배선한 이벤트에서 발화: Stop / PostToolUse(`Edit|Write|Bash|Task|NotebookEdit|TeamCreate|SendMessage|TaskCreate|TaskUpdate`) / PreCompact / SessionStart(`clear|compact|resume`). **`save_context.py`** (게놈) — SessionEnd(`clear`) 단일 matcher에서만 발화. 두 hook이 `.claude/context-snapshots/latest.md`에 스냅샷을 저장하며, IMMORTAL 섹션(현재 작업·다음 단계·SOT·품질게이트 상태)은 압축에도 우선 보존된다.
- **[CONTEXT RECOVERY] 복원** — 새 세션 시작 시 `[CONTEXT RECOVERY]` 메시지가 뜨면 오케스트레이터는 안내된 `latest.md`를 **반드시 Read로 읽어** 맥락을 복원한 뒤 진행한다(오케스트레이터 SKILL `## 메모리 운영` 섹션이 이 규약을 명시).
- **교차세션 지식(RLM 패턴)** — `.claude/context-snapshots/knowledge-index.jsonl`은 세션별 작업·수정파일·error→resolution을 누적한 외부 메모리다. 통째 로드 금지, **Grep으로 질의**한다.
- `validate`의 **`HOOK_REGISTERED`**가 `context_guard.py`·`save_context.py`를 settings.json에 배선했는지 강제한다(미배선 시 error).

이 사이클이 `CONTEXT_PRESERVATION_FIRSTCLASS`로 일급화되어, 오케스트레이터 SKILL이 `## 메모리 운영`(Tier I) 섹션에 `메모리 운영`·`knowledge-index`·`latest.md` 마커를 모두 emit하도록 강제된다(M1).

### (B) 4계층 품질 게이트 L0–L2 — qa_gate_runner + gate_or_block

게놈의 품질 게이트 validator(`validate_pacs.py`·`validate_review.py`·`validate_verification.py`)는 `{"valid": false}`를 **stdout으로 출력하되 exit 0**으로 빠진다 — 설계상 "Hook이 아니라 수동 호출". 그래서 orchestrator 산문에 의존하면 idoforgod와 같은 prose-compliance 도박이 된다. 두 CYS hook이 이를 강제 인터록으로 승격한다:

- **`gate_or_block.py <validator.py> [args]`** — validator의 JSON stdout을 파싱해 `valid:false`/`status:fail`/`errors`/exit-2를 **hard exit-2 BLOCK**으로 변환한다. 비-JSON 출력은 advisory(pass-through). 오케스트레이터가 각 단계 후 raw validator 대신 이것을 호출한다.
- **`qa_gate_runner.py`** — `_merge_settings`가 **PostToolUse**(matcher `Agent|Task|TaskUpdate`, timeout 15s)로 배선한다. SOT `outputs.step-N`에 산출물이 기록되면 게이트 체인을 발화한다. **false-block 함정**을 피하려 **evidence-gated + split** 설계:
  - 이미 게이트한 단계는 `.harness/.qa_last_gated` sidecar로 추적, 미게이트 단계만 순서대로 1회 발화.
  - **L0 Anti-Skip은 in-hook** — 기록된 산출물 파일이 존재하고 `MIN_OUTPUT_SIZE`(100B) 이상인지만 검사한다(`validate_pacs --check-l0`로 shell out하지 않음 — 그것은 pACS 로그까지 요구해 산출물-있음/로그-없음 단계를 false-block함).
  - **L1 / L1.5 / L2는 fire-on-presence** — 각 validator는 해당 로그 파일(`verification-logs/step-N-verify.md`·`pacs-logs/step-N-pacs.md`·`review-logs/step-N-review.md`)이 존재할 때만 `gate_or_block`을 통해 발화한다. 로그가 있으면 품질을 강제하고, 없으면 false-block하지 않는다.
  - 어디서든 advisory-safe: SOT/gate_or_block/validator/output 경로 부재 시 exit 0.
- **실증**(IMPLEMENTATION-STATUS): 누락 산출물 → L0 차단.

오케스트레이터 SKILL의 Phase-2 게이트 산문도 이 체인을 동일하게 호출한다 — `gate_or_block.py`가 호스트 인터록과 산문 호출 양쪽에서 발화하는 이중 안전망.

### (C) Spawn 천장 — budget_block + spawn_counter (countable ceiling)

Mode A의 hard ceiling은 Workflow 러너의 토큰 미터였다. 프리미티브 기질에는 **호스트 토큰 미터가 없고** per-call 토큰이 hook stdin에 신뢰성 있게 노출되지 않는다(`cys_log_tokens`가 자기-문서화). 그래서 천장을 **countable·host-observable 신호 = 누적 spawn 수**로 re-base한다:

- **`budget_block.py`** — **PreToolUse**(matcher `Agent|Task|TeamCreate`, timeout 5s). `.harness/state.yaml`의 `budget.spawns_used` vs `budget.max_spawns`를 읽어 `spawns_used >= max_spawns - margin`이면 **exit 2로 spawn을 차단**한다. matcher의 disjunction은 기질 버전을 횡단한다(현재 Claude Code=`Agent`, 레거시 게놈 산문=`Task`, 팀=`TeamCreate`). advisory-safe: `max_spawns` 부재 시 절대 차단 안 함.
- **`spawn_counter.py`** — **PostToolUse**(matcher `Agent|Task|TeamCreate`, timeout 5s). budget_block이 읽는 `spawns_used`를 **코드로** 매 spawn마다 +1 증분한다(이전엔 산문만 시켰고 아무도 증분 안 해 천장이 발화 못 함 — dogfood에서 34 spawn 동안 `spawns_used:0` 확인). SOT 규율: 이것은 state.yaml에 대한 **유일하게 허가된 비-오케스트레이터 쓰기**로, flock 하에 예약 정수 키 `budget.spawns_used`만 surgical regex로 만진다(오케스트레이터의 다른 모든 필드 단일-writer 소유권 보존). 항상 exit 0(counter일 뿐, 차단은 budget_block의 일).
- **실증**: spawn ceiling exit-2 발화.

### (D) SOT 초기화 — sot_init

- **`sot_init.py`** — **SessionStart**(matcher `startup|clear|resume`, timeout 5s). cold start 시 `.harness/state.yaml`(SOT)을 결정론적으로 시드한다 — `max_spawns`를 graph.json에서 추정(`estimate_max_spawns`: 노드 mechanism별 fan-out 합 + review 노드당 +1)해 run 1에서도 천장이 실제 bound를 갖게 한다. 파일이 이미 존재하면 **아무것도 안 함**(오케스트레이터의 라이브 state 비클로버 — 단일-writer 보존; cold-start만 처리). exit 0.
- state.yaml 작성이 ap_state-gated AWF 기능(SOT 스키마·autopilot·Decision Log·SOT-restore)을 깨운다.

### (E) 보안 hook (게놈)

게놈의 L0 보안 hook은 settings union으로 그대로 들어와 발화한다:
- `block_destructive_commands.py`·`output_secret_filter.py`·`security_sensitive_file_guard.py` — validate `GENOME_PRESENT`가 이 3종 + 척추 `_context_lib.py`·`context_guard.py`의 디스크 존재를 강제한다.

### (F) 토큰 tally (advisory)

- **`cys_log_tokens.py`** — `_merge_settings`가 **SubagentStop**(matcher `*`, timeout 5s)으로 배선. per-session 토큰/exit을 coarse·post-hoc로 기록(usage는 종종 부재). **차단 아님**(항상 exit 0) — hard ceiling은 (C)의 spawn 천장이다.

> **배선 요약표** (모두 `_merge_settings`가 idempotent union):

| hook | 이벤트 | matcher | 역할 |
|---|---|---|---|
| `context_guard` / `save_context` (게놈) | 컨텍스트 보존 | (게놈 union) | 스냅샷 저장 + IMMORTAL 보존 |
| `qa_gate_runner` | PostToolUse | `Agent\|Task\|TaskUpdate` | L0 in-hook + L1/L1.5/L2 fire-on-presence |
| `budget_block` | PreToolUse | `Agent\|Task\|TeamCreate` | spawn 천장 exit-2 |
| `spawn_counter` | PostToolUse | `Agent\|Task\|TeamCreate` | `spawns_used` +1 |
| `sot_init` | SessionStart | `startup\|clear\|resume` | cold-start SOT 시드 |
| 보안 3종 (게놈) | PreToolUse/PostToolUse | (게놈) | 파괴명령 차단·시크릿 필터·민감파일 가드 |
| `cys_log_tokens` | SubagentStop | `*` | advisory 토큰 tally |

---

## 3. 두 설치 모드: self-contained vs in-project 오버레이

`inherit(in_project=...)`이 두 모드를 분기한다. 둘 다 `_merge_settings`로 settings를 병합하지만(host-preserving union), 이식 형태가 다르다.

### (1) self-contained (기본)

- 빈/새 디렉토리에 `genome/` 전체를 `rsync`(루트 `README.md`·`.claude/settings.json` 제외)로 붓는다. ~440KB 헌법 + `docs/`가 **하네스 루트에** 위치한다.
- 로그 디렉토리는 루트 하위(`pacs-logs`·`verification-logs`).
- `CLAUDE.md`는 상속된 게놈 CLAUDE.md에 CYS 포인터를 append.

### (2) in-project 오버레이 (P1.2 / B2 — idoforgod식)

기존 호스트 프로젝트에 **additive overlay**로 설치한다. 핵심은 **호스트의 그 무엇도 클로버하지 않음**(`_transplant_overlay`):

- **`.claude/hooks`** (런타임 DNA) — `_rsync_ignore_existing`(`--ignore-existing`): 호스트가 *없는* hook만 설치. 호스트 자신의/튜닝된 동명 hook(보안 hook 포함)이 **항상 이긴다**.
- **`.claude/{agents, skills, config}`**(`_INPROJECT_NONCLOBBER_SUBS`) — 동일하게 `--ignore-existing` 비클로버 union: 호스트가 가진 파일은 절대 덮어쓰지 않음.
- **`.claude/commands`** — **SKIPPED**(prompt-runner-coupled; prompt-runner는 in-project에 설치 안 됨).
- **헌법 + `docs/`** — `.harness/genome/`로 **재배치**(`_RELOCATE_EXCLUDES`로 `/.claude`·`/prompt`·`/prompt-runner`·`/translations` 제외하고 rsync). 어떤 런타임 hook도 루트 `.md`를 *읽지 않으므로*(os.path.isfile-guarded doc-sync lint뿐 — behavior-safe) 재배치가 호스트 루트 `CLAUDE.md`/`AGENTS.md`/`README`를 클로버하지 않는다.
- **로그 디렉토리** — `.harness/pacs-logs`·`.harness/verification-logs`(호스트 루트 미오염).
- **`CLAUDE.md`** — 호스트 CLAUDE.md에 in-project 포인터를 **append**(없으면 1개 생성). 호스트 루트 파일은 보존.

### 필수 적대적-리뷰 agent: force-install + backup (L2 DNA 예외)

적대적-리뷰 agent **`reviewer.md` / `fact-checker.md`**(`_MANDATORY_GENOME_AGENTS`)는 head-to-head 변별력의 핵심(credited L2 discriminator)이라, in-project에서도 **게놈판을 강제 설치**한다(`_force_install_mandatory_agents`). 평범한 `--ignore-existing`이면 호스트의 동명 agent가 이겨 L2를 조용히 무력화하고 `REVIEW_AGENT_PRESENT`가 "엉뚱한 호스트 reviewer"로 통과하게 된다. 그래서:

- 게놈 버전을 **보장**하되 호스트 파일을 **파괴하지 않는다**: 내용이 다른 호스트 agent는 `.harness/genome/displaced/`로 **백업**(recoverable) + stderr 통지 후 게놈판으로 덮어쓴다.

### settings 안전 (in-project)

`_merge_settings`가 호스트 settings.json을 보존하며 union:
- 호스트 settings의 hook을 보존 + 게놈 hook을 `_union_hooks`로 union(command-set 시그니처가 이미 있으면 skip).
- `_union_perms`로 게놈 `permissions.deny` 보안 union(호스트가 자기 settings를 가졌다면 게놈 deny-list를 절대 채택 안 하는 보안 parity gap을 메움).
- 호스트 settings.json이 **비객체(`[]`/`null`/scalar)면 graceful coerce**(잃을 호스트 구조가 없음). **파싱불가면 emit 거부**(`SystemExit`) — 호스트의 hook/permissions를 무단 폐기하지 않음. 운영자가 고치게 한다.

### 노드 agent provenance + 충돌 거부

in-project emit 시 노드 agent에 `cys_emitted` provenance 마커를 stamp하고, **`cys_emitted` 없는 동명 호스트 agent와 충돌하면 emit 거부**(`SystemExit`) — in-project 설치가 호스트 자신의 `.claude/agents/<x>.md`를 hijack하지 못하게 한다(`emit_orchestrator._write_agent_files`).

### 모드 전환 가드

`.harness/GENOME.json`의 `install_mode` 마커로 **다른 모드 재emit을 거부**한다(`emit_orchestrator`의 mode-flip 가드). in-project→self-contained 재emit은 게놈을 호스트 루트에 부어 호스트 파일을 파괴하므로 cleanly refuse. 마커 손상 시 `validate`는 `.harness/genome/CLAUDE.md` 존재로 in-project를 **구조적으로 감지**해 `GENOME_PRESENT`·`W1_GENOME`·doc/measurement-drift 경로를 자동 분기한다.

---

## 4. prompt-runner 배제 (vendored-but-inert)

상속된 `prompt-runner/`(AWF의 `claude -p --resume` CLI 배치 실행기)는 **vendored capability이지 실행 경로가 아니다**:

- **self-contained**: `genome/` 전체가 붓려 디스크엔 존재하나, RUNTIME.json에 runnable 런타임으로 **광고되지 않는다**(§5).
- **in-project**: `_transplant_overlay`가 `prompt`·`prompt-runner`·`translations`를 아예 **설치 안 함**(`_RELOCATE_EXCLUDES`).
- `inherit_genome` 모듈 docstring / CLAUDE.md 포인터가 명시: "상속된 `prompt-runner/`는 vendored capability이지 실행 경로가 아니다 — there is no compiled `.js` workflow runtime and no subprocess batch runner."

> ⚠️ 주의: `inherit_genome.py`의 기본 상수 `_RUNTIME_MANIFEST`는 레거시 workflow.js-canonical 매니페스트(2-런타임: `cys-mode-a` + `awf-prompt-runner`)를 담고 있으나, **이는 emit 경로에서 사용되지 않는다.** `emit_orchestrator`가 `inherit(..., runtime_manifest=_runtime_manifest(graph, in_project))`로 **오케스트레이터-canonical 매니페스트를 주입**하여 override한다. 산출 하네스의 실제 RUNTIME.json은 항상 §5의 단일-런타임 형태다.

---

## 5. RUNTIME.json: 단 하나의 canonical 런타임

`emit_orchestrator._runtime_manifest(graph, in_project)`가 생성하는 `.harness/RUNTIME.json`은 **정확히 하나의 실행 런타임 = 오케스트레이터 스킬**만 광고한다(M0/locked-3, `RUNTIME_MANIFEST_CLEAN`):

```json
{
  "schema_version": "0.1",
  "install_mode": "self-contained | in-project",
  "canonical_runtime": "<harness>-orchestrator",
  "runtimes": [{
    "name": "<harness>-orchestrator",
    "role": "canonical",
    "entrypoint": ".claude/skills/<harness>-orchestrator/SKILL.md",
    "driver": "Claude Code primitives (Agent / TeamCreate / SendMessage), live host session",
    "kind": "prose-driven, genome-active (hooks/L0-L2/SOT fire), graph.json-contracted, semantic-resume",
    "wired_to": "graph.json (this harness's contract) via emit_orchestrator",
    "use_when": "default — ALL of this harness's work runs as a live session driven by this skill",
    "launch": "..."
  }],
  "routing_rule": "Run this harness by opening a `claude` session in its dir and triggering the <name>-orchestrator skill. …"
}
```

> 위 `routing_rule`은 가독성을 위해 발췌·축약했다. **실제 `.harness/RUNTIME.json`은 이 값을 1줄 단일 문자열로 기록한다**(`_runtime_manifest`가 문자열 concat으로 emit). 취지는 §4 docstring 인용("there is no compiled `.js` workflow runtime and no subprocess batch runner")과 동일하다.

- **은퇴 런타임은 광고 금지**: `validate`의 `RUNTIME_MANIFEST_CLEAN`이 runtimes에 `workflow.js` entrypoint·`prompt-runner` entrypoint·`cys-mode-a-workflow`/`awf-prompt-runner` name이 끼어들면 error로 차단한다. 자식 `RUNTIME.json`/`CLAUDE.md`가 은퇴 런타임을 광고하던 누수는 이 가드로 스크럽됐다(M0).
- **canonical 일치**: `RUNTIME_DECLARED`가 `canonical_runtime == "<harness>-orchestrator"`(execution_mode=agent|team|hybrid)인지 강제한다(workflow 모드만 `cys-mode-a`이나, 그건 은퇴라 산출 하네스엔 나타나지 않음).
- **workflow.js 잔존 금지**: `WORKFLOW_RETIRED`가 `.harness/workflow.js` 디스크 잔존을 error로 차단("the orchestrator skill is the only execution runtime").

---

## 6. 라이브 세션 launch 핸드오프

산출 하네스는 **라이브 `claude` 세션**으로 실행된다 — 그 세션에서 상속 게놈 hook이 발화하고 노드 agent의 frontmatter(model·tools·maxTurns)가 Agent 도구에 의해 런타임 강제된다. `_runtime_manifest`의 `launch` 필드가 모드별 핸드오프를 stamp한다:

- **self-contained**: `cd <harness_dir> && claude` — **그 세션의 settings.json hook이 발화**(공장의 것이 아니라). 이어서 `<harness>-orchestrator` 스킬을 트리거.
- **in-project**: 호스트 프로젝트의 `claude` 세션 안에서 `<harness>-orchestrator` 스킬을 트리거 — 오버레이: 이 하네스는 호스트의 *한 capability*이지 호스트 루트 자신의 런타임이 아니다.

build gate는 `python3 .../validate_harness.py .`이다. (라이브 풀세션 end-to-end 발화 재확인 — 게이트·메모리·팀 — 은 IMPLEMENTATION-STATUS의 남은 일이다.)

---

## 7. validate가 강제하는 게놈 계약

`validate_harness.py._genome_checks`가 게놈 전수·배선·매니페스트를 머신체크한다(in-project는 재배치 경로로 자동 분기):

| 코드 | 강제 내용 |
|---|---|
| `GENOME_PRESENT` | 척추 + 보안 머신 디스크 존재: `.claude/hooks/scripts/_context_lib.py`·`context_guard.py`·`block_destructive_commands.py`·`output_secret_filter.py`·`security_sensitive_file_guard.py` + `.harness/GENOME.json` + 헌법(`soul.md`·`AGENTS.md`·`CLAUDE.md`; in-project은 `.harness/genome/` 하위). |
| `HOOK_REGISTERED` | settings.json이 보안 3종 + `context_guard.py`·`save_context.py`를 배선. 프리미티브 모드(agent\|team\|hybrid)는 추가로 `budget_block.py`·`spawn_counter.py`·`sot_init.py`·`qa_gate_runner.py`까지 배선(없으면 DNA가 휴면). |
| `RUNTIME_DECLARED` | `.harness/RUNTIME.json` 존재 + `canonical_runtime`이 execution_mode와 일치(`<harness>-orchestrator`). |
| `RUNTIME_MANIFEST_CLEAN` | 산출 하네스 RUNTIME.json이 비-프리미티브 런타임(workflow.js/prompt-runner)을 광고하지 않음. |
| `WORKFLOW_RETIRED` | `execution_mode='workflow'` 또는 `.harness/workflow.js` 잔존을 차단(은퇴). |
| `W1_GENOME` | `harness.md`(in-project은 `.harness/harness.md`)가 Inherited DNA + AC-1/AC-2/AC-3 마커 보유. |
| `MEMORY_STORE_INIT` | settings.json이 있으면 `.harness/memory/`의 Tier-II 시드(archive.manifest.json·domain-knowledge.yaml·runs/index.jsonl) 존재. |

> 검증 깊이는 단순 존재가 아니라 **기능**까지다: `inherit._verify`가 모든 이식 hook을 `py_compile`하고 `_context_lib`를 실제로 import해 "머신이 복사만 된 게 아니라 기능적으로 존재함"을 증명한다 — 실패 시 `inherit`/`emit_orchestrator`가 비-0 종료한다.
