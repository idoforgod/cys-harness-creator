#!/usr/bin/env python3
"""CYS Harness Creator — orchestrator emitter (Claude Code PRIMITIVE substrate).

The pivot's core emit target. For execution_mode in {agent, team, hybrid} this REPLACES
emit_workflow.py's workflow.js: instead of compiling graph.json into an opaque Workflow-tool
script, it renders graph.json into (a) a PROSE orchestrator SKILL.md that drives a LIVE
Claude Code host session via Agent (default) / TeamCreate, and (b) per-node .claude/agents
files whose frontmatter (model + tools allowlist + maxTurns) the Agent primitive
RUNTIME-ENFORCES (the inverse of Mode A's general-purpose downgrade). This is the substrate
where the inherited AWF genome (hooks, L0-L2 gates, SOT, adversarial review) actually fires.

graph.json stays the immutable machine-checkable contract (CYS's edge over idoforgod's
schemaless prose); validate_harness.py gates the produced orchestrator+agents+genome.

CLI: emit_orchestrator.py <harness_dir>
"""
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "lib"))
from toposort import toposort           # noqa: E402
from atomic_write import atomic_write   # noqa: E402
from inherit_genome import inherit      # noqa: E402
from validate_harness import _role_class_of  # noqa: E402

_TEMPLATES = os.path.join(_HERE, "templates")
_DEFAULT_MAXTURNS = 25
# Least-privilege tool defaults by role-class (node.tools overrides).
_ROLE_TOOLS = {
    "gather": "Read, Glob, Grep, WebSearch, WebFetch",
    "extract": "Read, Glob, Grep",
    "format": "Read, Write",
    "qa-scan": "Read, Glob, Grep, Bash",
    "voter": "Read, Glob, Grep, WebSearch",
    "debater": "Read, Glob, Grep, WebSearch",
    "reviser": "Read, Write, Glob, Grep",
    "synthesis": "Read, Write, Glob, Grep",
    "judge": "Read, Glob, Grep",
    "critic": "Read, Glob, Grep, WebSearch, WebFetch",
    "architecture": "Read, Glob, Grep",
}


def _load(path):
    with open(path) as f:
        return json.load(f)


def _split_frontmatter(text):
    """Return (frontmatter_dict, body). Minimal line-scan, matches validate_harness."""
    fm, body = {}, text
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            block = text[3:end]
            body = text[end + 4:].lstrip("\n")
            for line in block.splitlines():
                if ":" in line and not line.lstrip().startswith("#"):
                    k, _, v = line.partition(":")
                    if k.strip().isidentifier() or "-" in k.strip():
                        fm[k.strip()] = v.strip().strip('"').strip("'")
    return fm, body


def _tools_for(node):
    if node.get("tools"):
        return ", ".join(node["tools"])
    return _ROLE_TOOLS.get(_role_class_of(node), "Read, Glob, Grep")


def _write_agent_files(graph, harness_dir):
    """Ensure each node.agent has .claude/agents/<agent>.md with RUNTIME-bound frontmatter
    (model=node.model, tools allowlist, maxTurns). Preserves any existing hand-written body
    and description; only normalizes the runtime-enforced fields."""
    adir = os.path.join(harness_dir, ".claude", "agents")
    os.makedirs(adir, exist_ok=True)
    for n in graph["nodes"]:
        path = os.path.join(adir, n["agent"] + ".md")
        existing_fm, body = ({}, "")
        if os.path.isfile(path):
            existing_fm, body = _split_frontmatter(open(path, encoding="utf-8").read())
        rc = _role_class_of(n)
        desc = existing_fm.get("description") or (
            "%s-class worker for the %s harness (node '%s'). Spawned by the orchestrator via the "
            "Agent tool; receives the prior step's output and returns JSON per its output schema."
            % (rc, graph["harness_name"], n["id"]))
        rationale = existing_fm.get("model_rationale") or (
            "role-class '%s' -> tier %s per model-tier-policy" % (rc, n["model"]))
        tools = existing_fm.get("tools") or _tools_for(n)
        maxturns = existing_fm.get("maxTurns") or str(_DEFAULT_MAXTURNS)
        if not body.strip():
            body = ("핵심 역할: %s 노드의 작업을 수행한다.\n\n작업 원칙: 입력(직전 노드 출력)을 받아 "
                    "output_schema에 맞는 JSON만 반환한다. 도구는 frontmatter allowlist로 제한된다.\n" % n["id"])
        fm = ("---\n"
              "name: %s\n"
              "description: \"%s\"\n"
              "model: %s\n"
              "model_rationale: \"%s\"\n"
              "tools: %s\n"
              "maxTurns: %s\n"
              "---\n" % (n["agent"], desc.replace('"', "'"), n["model"],
                         rationale.replace('"', "'"), tools, maxturns))
        atomic_write(path, fm + body.rstrip("\n") + "\n")


def _spawn_recipe(n, prev_label):
    """Prose recipe for spawning one node via the Agent primitive, expanding its mechanism."""
    nid, agent, model, mech = n["id"], n["agent"], n["model"], n["decision_mechanism"]
    mp = n.get("mechanism_params", {})
    sch = ("schemas/%s.json" % nid) if n.get("output_schema") else "(none)"
    base = ("`Agent(subagent_type=\"%s\", model=\"%s\")` — 입력=%s, 반환=JSON(%s 스키마 준수)."
            % (agent, model, prev_label, sch))
    lines = ["- **%s** (`%s`, mech=%s): %s" % (nid, agent, mech, base)]
    if mech == "majority-vote":
        nn = mp.get("n", 3); q = mp.get("quorum", (nn // 2) + 1)
        lines.append("  - %d개 `Agent`를 병렬 spawn(독립 투표) → quorum %d로 다수결 집계." % (nn, q))
    elif mech == "debate-with-judge":
        lines.append("  - %d명 debater를 %d라운드 토론 후 judge(`%s`) Agent가 판정."
                     % (mp.get("n", 2), mp.get("max_rounds", 2), mp.get("judge", "opus")))
    elif mech == "reflect-then-revise":
        lines.append("  - critic(`%s`) Agent가 적대적 비평 → reviser가 수정, max_rounds=%d, approved=true면 조기 종료."
                     % (mp.get("critic", "opus"), mp.get("max_rounds", 2)))
    if n.get("review"):
        lines.append("  - **L2 적대적 리뷰**: 이후 `Agent(subagent_type=\"%s\")` 를 spawn(최소 1개 이슈), "
                     "`gate_or_block.py validate_review.py` 로 검증." % n["review"]["agent"])
    return "\n".join(lines)


PHASES = ["Phase 0: 컨텍스트 + SOT 초기화", "Phase 1: 비용 승인", "Phase 2: 노드 실행 + 품질 게이트",
          "Phase 3: 통합 산출 + 측정"]


def _orchestrator_skill(graph, order):
    by = {n["id"]: n for n in graph["nodes"]}
    name = graph["harness_name"]
    mode = graph["execution_mode"]
    rows = ["| 노드 | agent | model | mechanism | tools | 출력 |", "|---|---|---|---|---|---|"]
    for nid in order:
        n = by[nid]
        out = (n.get("outputs") or ["(return)"])[0]
        rows.append("| %s | %s | %s | %s | %s | %s |" % (nid, n["agent"], n["model"],
                    n["decision_mechanism"], _tools_for(n), out))
    spawn = []
    prev = "Phase 1 입력(query)"
    for nid in order:
        spawn.append(_spawn_recipe(by[nid], prev))
        prev = "'%s' 노드 출력" % nid
    fm = ("---\n"
          "name: %s-orchestrator\n"
          "description: \"%s 하네스를 Claude Code 프리미티브(Agent/TeamCreate)로 실행하는 오케스트레이터. "
          "'%s' 관련 작업·생성·분석 요청 시 사용. 후속: 다시 실행, 재실행, 업데이트, 수정, 보완, "
          "'%s의 일부만 다시', 이전 결과 기반 개선 요청 시에도 반드시 이 스킬을 사용.\"\n"
          "---\n" % (name, name, name, name))
    body = """# {name} Orchestrator

graph.json(불변 계약)에서 emit된 오케스트레이터. 산출 하네스를 **라이브 Claude Code 호스트 세션**에서
실행하며, 이 세션에 상속된 AWF 게놈 hook(컨텍스트 보존·보안·SubagentStop)이 발화하고, 각 노드의
`.claude/agents/<agent>.md` frontmatter(model·tools·maxTurns)가 Agent 도구에 의해 런타임 강제된다.

## 실행 모드: {mode} (기본=agent; team은 P5 입증 후 승격)

## 에이전트 구성

{table}

## 워크플로우

### {p0}
1. `<harness>/` 존재로 분기: 초기 / 재실행 / 부분 재실행 / 마이그레이션.
2. `.harness/state.yaml`(SOT)을 작성/갱신한다 — **오케스트레이터 단독 쓰기**. 필드:
   `current_step, outputs{{}}, budget{{spawns_used:0, max_spawns:<warrant fanout 합>}}, pacs{{}}, audit_log[]`.
   state.yaml 작성이 ap_state-gated AWF 기능(SOT 스키마·autopilot·Decision Log·SOT-restore)을 깨운다.
3. 재실행이면 첫 단계로 `state.yaml` + 최신 `.claude/context-snapshots/latest.md`를 읽어 맥락 복원.

### {p1}
1. `python3 ../../warrant.py --graph .harness/graph.json` 로 비용밴드 표시.
2. `budget.approval_required=true`이면 사용자 'approve' 대기 후 진행. 승인은 state.yaml audit_log에 기록.
3. `budget.max_spawns`를 warrant fanout 합으로 설정 → 런타임 `budget_block.py`(PreToolUse)가 spawn 초과 시 exit-2 차단.

### {p2}
**실행 모드: agent** — toposort 순서로 노드를 spawn하고, 각 노드 후 품질 게이트를 통과시킨다.
spawns_used를 spawn마다 +1(단일쓰기).

{spawn}

**노드별 품질 게이트(autopilot-execution.md 순서, 각 단계 산출물 작성 직후):**
- **L0 Anti-Skip**: `python3 ../../templates/hooks/gate_or_block.py .claude/hooks/scripts/validate_pacs.py --check-l0 --step <N>` (산출물 존재+≥100B).
- **L1 Verification**: `gate_or_block.py validate_verification.py --step <N>` (기능 목표 100% 달성).
- **L1.5 pACS**: `gate_or_block.py validate_pacs.py --step <N>` (Pre-mortem + F/C/L min, RED 차단).
- **L2 Adversarial Review** (review 노드만): reviewer/fact-checker spawn 후 `gate_or_block.py validate_review.py --step <N>`.
- FAIL → `diagnose_context.py` → `validate_diagnosis.py`, `validate_retry_budget.py` 예산 내 재시도.
> `gate_or_block.py`가 advisory validator(exit 0)를 **exit-2 인터록**으로 승격하므로, 게이트 FAIL이 단계를 실제로 멈춘다.

### {p3}
1. 마지막 노드 출력을 최종 산출물로 기록(state.yaml outputs).
2. `git init && git add -A && git commit`(rollback substrate).
3. (선택) head-to-head: `evals/{name}.scorecard.json` 기준 C2(이 하네스) vs C3(no-harness) n≥5 → `h2h_aggregate.py`.

## 비용 거버넌스
사전: warrant 비용밴드 승인. 런타임: `budget_block.py` spawn-count ceiling(exit-2). 토큰 tally는 advisory.

## 에러 핸들링
| 상황 | 전략 |
|------|------|
| 노드 1회 실패 | 1회 재시도(retries), 재실패 시 on_exhaust(proceed-with-gap/escalate) |
| 게이트 FAIL | abductive diagnosis → 예산 내 재시도 → 초과 시 사용자 에스컬레이션 |
| spawn 초과 | budget_block exit-2 — graph.budget 상향 또는 fan-out 축소 |
| 상충 데이터 | 삭제 금지, 출처 병기 |

## 테스트 시나리오
- 정상: query 입력 → 노드 순차 실행 + 게이트 PASS → 최종 산출물 생성.
- 에러: 한 노드 FAIL → diagnosis → 재시도 → 부분 결과로 진행, 보고서에 누락 명시.
""".format(name=name, mode=mode, table="\n".join(rows), spawn="\n".join(spawn),
           p0=PHASES[0], p1=PHASES[1], p2=PHASES[2], p3=PHASES[3])
    return fm + body


def _readme(graph):
    name = graph["harness_name"]
    ph = "\n".join("- **%s**" % p for p in PHASES)
    return ("# %s — CYS harness (Claude Code primitive substrate)\n\n"
            "graph.json -> orchestrator SKILL.md + .claude/agents (emit_orchestrator). "
            "Runs as a live host session via Agent/TeamCreate; the inherited AWF genome fires.\n\n"
            "## Phases\n%s\n\n실행: 이 디렉토리에서 `claude` 세션을 열고 `%s-orchestrator` 스킬을 트리거.\n"
            % (name, ph, name))


def _categorization_merge(harness_dir, graph):
    """After genome transplant, ADD a categorization entry per domain node.agent so the
    (fixed) pre_subagent_invocation guard knows them (else, with hard-block enabled, it would
    RuntimeError on unregistered agents). Domain workers default to 'always_fresh' (stateless)."""
    cpath = os.path.join(harness_dir, ".claude", "config", "categorization.yaml")
    os.makedirs(os.path.dirname(cpath), exist_ok=True)
    try:
        import yaml
        cfg = yaml.safe_load(open(cpath, encoding="utf-8")) if os.path.isfile(cpath) else None
        cfg = cfg or {}
        agents = cfg.setdefault("agents", {})
        for n in graph["nodes"]:
            key = "@" + n["agent"]
            if key not in agents:
                agents[key] = {"rule": "always_fresh",
                               "note": "auto-emitted domain worker for node '%s'" % n["id"]}
        atomic_write(cpath, yaml.safe_dump(cfg, allow_unicode=True, sort_keys=True))
    except Exception:
        # PyYAML absent in factory env: append a minimal note (genome merge happens in-child where yaml exists)
        lines = ["agents:"]
        for n in graph["nodes"]:
            lines.append("  '@%s': {rule: always_fresh}  # node %s" % (n["agent"], n["id"]))
        if not os.path.isfile(cpath):
            atomic_write(cpath, "\n".join(lines) + "\n")


def _harness_md(graph, order):
    """Genome-inheritance visualization (validate W1_GENOME needs Inherited DNA + AC markers)."""
    tpl = os.path.join(_TEMPLATES, "inherited-dna.md.tmpl")
    by = {n["id"]: n for n in graph["nodes"]}
    table = "\n".join("  | %s | %s | %s | %s |" % (nid, by[nid]["agent"], by[nid]["model"],
                                                   by[nid]["decision_mechanism"]) for nid in order)
    if os.path.isfile(tpl):
        md = open(tpl, encoding="utf-8").read()
        repl = {"{{HARNESS_NAME}}": graph["harness_name"], "{{TOPOLOGY}}": graph["topology"],
                "{{MECHANISMS}}": ", ".join(sorted(set(n["decision_mechanism"] for n in graph["nodes"]))),
                "{{NODE_COUNT}}": str(len(graph["nodes"])),
                "{{NODE_TABLE}}": "  | node | agent | model | mechanism |\n  |---|---|---|---|\n" + table,
                "{{BUDGET_TOKENS}}": str(graph["budget"]["total_tokens"]),
                "{{APPROVAL}}": str(graph["budget"]["approval_required"]).lower()}
        for k, v in repl.items():
            md = md.replace(k, v)
        return md
    return ("# %s — Inherited DNA\n\nAC-1 (품질) · AC-2 (SOT) · AC-3 (CCP) 상속. "
            "execution_mode=%s, %d nodes.\n" % (graph["harness_name"], graph["execution_mode"], len(graph["nodes"])))


def _runtime_manifest(graph):
    name = graph["harness_name"]
    return {
        "schema_version": "0.1",
        "canonical_runtime": "%s-orchestrator" % name,
        "runtimes": [
            {"name": "%s-orchestrator" % name, "role": "canonical",
             "entrypoint": ".claude/skills/%s-orchestrator/SKILL.md" % name,
             "driver": "Claude Code primitives (Agent / TeamCreate / SendMessage), live host session",
             "kind": "prose-driven, genome-active (hooks/L0-L2/SOT fire), graph.json-contracted, semantic-resume",
             "wired_to": "graph.json (this harness's contract) via emit_orchestrator",
             "use_when": "default — ALL of this harness's work runs as a live session driven by this skill",
             "launch": "cd <harness_dir> && claude   # THAT session's settings.json hooks fire (not the factory's)"},
            {"name": "cys-mode-a-workflow", "role": "optional-deterministic",
             "entrypoint": ".harness/workflow.js",
             "driver": "Workflow tool", "kind": "byte-deterministic replay (resumeFromRunId)",
             "wired_to": "graph.json (only when execution_mode='workflow')",
             "use_when": "rare deterministic-replay-critical case; NOT the primitive default"},
            {"name": "awf-prompt-runner", "role": "inherited-alternative",
             "entrypoint": "prompt-runner/run.py", "driver": "claude -p --resume",
             "kind": "human-driven batch", "wired_to": "NOT wired to graph.json",
             "use_when": "ad-hoc long / rate-limit-exposed batch; NOT the default"},
        ],
        "routing_rule": "Run this harness by opening a `claude` session in its dir and triggering the "
                        "<name>-orchestrator skill. workflow.js is an optional deterministic alternative; "
                        "prompt-runner is inherited batch capability. Never route one task through two.",
    }


def emit_orchestrator(graph, harness_dir):
    assert graph["execution_mode"] in ("agent", "team", "hybrid"), \
        "emit_orchestrator handles primitive substrate; execution_mode='workflow' -> emit_workflow.py"
    order = toposort(graph["nodes"], graph["edges"])
    # 1) agent files with runtime-bound frontmatter
    _write_agent_files(graph, harness_dir)
    # 2) orchestrator skill + README + schemas-presence check
    skill_dir = os.path.join(harness_dir, ".claude", "skills", graph["harness_name"] + "-orchestrator")
    os.makedirs(skill_dir, exist_ok=True)
    atomic_write(os.path.join(skill_dir, "SKILL.md"), _orchestrator_skill(graph, order))
    atomic_write(os.path.join(harness_dir, "README.md"), _readme(graph))
    # 3) genome transplant (orchestrator-canonical RUNTIME) — wakes hooks/gates/SOT
    errs = inherit(harness_dir, runtime_manifest=_runtime_manifest(graph))
    # 4) post-inherit: merge categorization (genome + domain agents) + harness.md genome viz
    _categorization_merge(harness_dir, graph)
    atomic_write(os.path.join(harness_dir, "harness.md"), _harness_md(graph, order))
    return errs


def main():
    if len(sys.argv) < 2:
        print("usage: emit_orchestrator.py <harness_dir>", file=sys.stderr); sys.exit(2)
    hd = os.path.abspath(sys.argv[1])
    graph = _load(os.path.join(hd, ".harness", "graph.json"))
    errs = emit_orchestrator(graph, hd)
    if errs:
        print("emitted orchestrator for %s; GENOME VERIFY FAILED:" % graph["harness_name"])
        for e in errs:
            print("  -", e)
        sys.exit(1)
    print("emitted .claude/skills/%s-orchestrator/SKILL.md + agents + FULL AWF genome (active substrate)"
          % graph["harness_name"])


if __name__ == "__main__":
    main()
