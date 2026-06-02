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
from toposort import CycleError, toposort  # noqa: E402
from atomic_write import atomic_write   # noqa: E402
from inherit_genome import inherit      # noqa: E402
from validate_harness import TIER_BY_ROLE_CLASS, _role_class_of  # noqa: E402

sys.path.insert(0, os.path.join(_HERE, "templates", "hooks"))
from sot_init import estimate_max_spawns  # noqa: E402  (SAME deterministic seeder sot_init uses at cold start)
from query_norm import query_norm  # noqa: E402  (SAME normalizer bootstrap writes — recall key baked as literal)

# Node keys emit_orchestrator dereferences directly (n["..."]). Used by _require_valid_graph to fail
# CLEANLY when a hand-authored / schema-invalid graph reaches emit (I3) BEFORE validate (I5) runs —
# else a missing key surfaced as a raw KeyError traceback instead of an actionable error.
_REQUIRED_NODE_KEYS = ("id", "agent", "model", "decision_mechanism")
_REQUIRED_GRAPH_KEYS = ("harness_name", "execution_mode", "topology", "nodes", "edges", "budget")

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
    with open(path, encoding="utf-8") as f:
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


# P2-B (audit): per-role-class working principles so the emitted agent body is a real, reusable persona
# (idoforgod's who/how deliverable) rather than a 2-line stub.
_ROLE_PRINCIPLES = {
    "gather": "다양한 출처를 광범위 검색·수집한다. 1차 출처 우선, 각 주장에 source_id를 붙이고 미검증 주장은 confidence를 낮춘다. 누락보다 과수집 후 정제.",
    "extract": "입력에서 구조화된 사실만 추출한다. 원문에 없는 내용 생성 금지; 추출 불가 항목은 명시적으로 표기한다.",
    "format": "검증된 콘텐츠를 지정 스키마/형식으로 직렬화한다. 내용 변경 없이 구조만 다루고, 모든 사실의 인용을 보존한다.",
    "qa-scan": "산출물을 계약(schema·inputs·write_paths) 대비 점검한다. 존재 확인이 아니라 인터페이스 교차비교; FAIL은 증거와 함께 보고한다.",
    "voter": "독립적으로 판단해 투표한다. 다른 투표자를 참조하지 않고 자기 근거로만; quorum 집계는 오케스트레이터가 한다.",
    "debater": "입장을 근거로 변호하고 상대를 반박한다. 라운드마다 새 증거를 제시하며, 최종 판정은 judge에게 맡긴다.",
    "reviser": "비평을 받아 결함을 수정한다. 모든 지적을 반영하거나 반박 근거를 남기고, approved 전까지 반복한다.",
    "synthesis": "검증된 입력을 통합해 최종 산출물을 만든다. 상충은 삭제가 아니라 출처를 병기하고, 모든 사실에 인용을 단다.",
    "judge": "후보들을 기준 대비 블라인드·일관 평가해 승자를 정하고 근거를 명시한다.",
    "critic": "적대적으로 결함을 찾는다. 통과가 아니라 반증을 시도하며, 최소 1개 이슈 또는 명시적 approved를 낸다.",
    "architecture": "구조·계획을 설계한다. 트레이드오프를 명시하고 결정 근거를 남긴다.",
}


# P1 (3-tier memory): every emitted agent READS the recall relay as work input, so the Phase-0
# recall is actually CONSUMED (closes the field-observed 'agents are memory-blind' gap). Appended to
# hand-written bodies too (body preserved); validate's AGENT_MEMORY_CONTRACT enforces presence.
_MEMORY_INPUT_BLOCK = (
    "## 메모리 입력 (회상 주입)\n"
    "작업 산출 전, 오케스트레이터가 Phase 0에서 떨군 `_workspace/_recall.json`(과거 유사 실행의 회상)과 "
    "`.harness/memory/domain-knowledge.yaml`(IMMORTAL 도메인 제약)을 **Read**한다. 회상된 엔티티·제약을 "
    "작업에 반영하고, 알려진 제약을 위반하는 주장은 flag하거나 출처로 재검증한다(맹신 금지 — provenance·recency 가중). "
    "`_recall.json`이 `{\"cold\": true}`면 선례 없음으로 진행한다.\n"
)


def _agent_body(graph, n):
    """Render a full per-agent body from graph node fields: role + principles + exact I/O protocol +
    mechanism + error handling + team-comms (team mode) + L2 (review nodes). Used only when no hand-written
    body exists (a hand-authored agent .md body is always preserved)."""
    rc, nid, mech = _role_class_of(n), n["id"], n["decision_mechanism"]
    mp = n.get("mechanism_params", {})
    ins = ", ".join(n.get("inputs") or []) or "(직전 노드 출력)"
    outs = ", ".join(n.get("outputs") or []) or "(orchestrator로 반환)"
    wps = ", ".join(n.get("write_paths") or []) or "(없음)"
    p = ["## 핵심 역할",
         "%s 하네스의 '%s' 노드(%s-class, mechanism=%s). 오케스트레이터가 Agent 도구로 spawn하며, 직전 단계 출력을 받아 자기 단계를 수행한다."
         % (graph["harness_name"], nid, rc, mech),
         "", "## 작업 원칙", _ROLE_PRINCIPLES.get(rc, "노드 목표를 달성하는 작업을 수행한다."),
         "", "## 입력/출력 프로토콜",
         "- **입력**: %s — 하드코딩 경로 대신 SOT `state.yaml`의 `outputs.step-<직전>` 포인터로 해소하고, "
         "직전 단계의 검증된 사실은 `.harness/memory/runs/<run_id>/stage-<직전>-facts.jsonl`을 Read한다"
         "(벌크는 `_workspace/`, 검증된 사실 척추는 메모리)." % ins,
         "- **출력**: %s — `%s` 스키마를 준수하는 JSON만 반환한다(스키마 외 텍스트 금지)." % (outs, n.get("output_schema") or "(없음)"),
         "- **쓰기 경로**: %s — 이 경로 밖에 쓰지 않는다(write_path 단독 소유). 도구는 frontmatter allowlist로 제한(최소권한)." % wps,
         "", "## 에러 핸들링",
         "- 실패 시 %d회 재시도, 소진 시 on_exhaust=%s. 상충 데이터는 삭제하지 말고 출처를 병기하며, 미검증은 명시한다."
         % (n.get("retries", 0), n.get("on_exhaust", "escalate")),
         "", _MEMORY_INPUT_BLOCK.rstrip("\n")]
    if mech == "majority-vote":
        p += ["", "## 메커니즘: majority-vote",
              "독립 투표자(%d명, quorum %s)로 동작한다 — 다른 투표를 보지 않고 자기 근거로 판단한다."
              % (mp.get("n", 3), mp.get("quorum", (mp.get("n", 3) // 2) + 1))]
    elif mech == "debate-with-judge":
        p += ["", "## 메커니즘: debate-with-judge",
              "%d라운드 토론 후 judge(%s)가 판정한다." % (mp.get("max_rounds", 2), mp.get("judge", "opus"))]
    elif mech == "reflect-then-revise":
        p += ["", "## 메커니즘: reflect-then-revise",
              "critic(%s)의 적대적 비평을 받아 수정한다(max_rounds=%d, approved 시 조기종료)."
              % (mp.get("critic", "opus"), mp.get("max_rounds", 2))]
    if graph.get("execution_mode") in ("team", "hybrid"):
        p += ["", "## 팀 통신 프로토콜 (team 모드)",
              "TeamCreate 멤버로 동작한다. 상충·누락 발견 시 관련 팀원에게 `SendMessage`로 직접 공유(리더 우회 peer-to-peer)하고, "
              "자기 task를 task list에서 claim하며, 완료 시 산출물을 write_path에 flush한다."]
    if n.get("review"):
        p += ["", "## L2 적대적 리뷰",
              "이 노드 산출 후 별도 `Agent(subagent_type=\"%s\")`가 적대적 리뷰를 수행한다(최소 1개 이슈 또는 approved). "
              "리뷰 통과 전 다음 단계로 진행하지 않는다." % n["review"]["agent"]]
    return "\n".join(p) + "\n"


def _write_agent_files(graph, harness_dir, in_project=False):
    """Ensure each node.agent has .claude/agents/<agent>.md with RUNTIME-bound frontmatter
    (model=node.model, tools allowlist, maxTurns). Preserves any existing hand-written body
    and description; only normalizes the runtime-enforced fields.

    in_project: stamp a `cys_emitted` provenance marker and REFUSE to overwrite a same-named host agent
    that lacks it (an in-project install must never hijack the host's own .claude/agents/<x>.md)."""
    adir = os.path.join(harness_dir, ".claude", "agents")
    os.makedirs(adir, exist_ok=True)
    for n in graph["nodes"]:
        path = os.path.join(adir, n["agent"] + ".md")
        existing_fm, body = ({}, "")
        if os.path.isfile(path):
            existing_fm, body = _split_frontmatter(open(path, encoding="utf-8").read())
            if in_project and not existing_fm.get("cys_emitted"):
                raise SystemExit(
                    "in-project collision: .claude/agents/%s.md already exists and is host-owned "
                    "(no cys_emitted marker) — rename graph node '%s'.agent so the install does not "
                    "clobber the host's agent" % (n["agent"], n["id"]))
        rc = _role_class_of(n)
        desc = existing_fm.get("description") or (
            "%s-class worker for the %s harness (node '%s'). Spawned by the orchestrator via the "
            "Agent tool; receives the prior step's output and returns JSON per its output schema."
            % (rc, graph["harness_name"], n["id"]))
        # Truthful, policy-derived rationale: state the role-class POLICY tier (computed deterministically
        # from role-class-policy.json, NOT the node's chosen model) and any override — so the rationale can
        # never assert a false "X -> tier Y per policy" when the node under/over-rides the policy default.
        _policy_tier = TIER_BY_ROLE_CLASS.get(rc, "sonnet")
        if n["model"] == _policy_tier:
            _rat = "role-class '%s' -> policy tier %s (model-tier-policy)" % (rc, _policy_tier)
        else:
            _rat = ("role-class '%s' policy-default %s; set to %s%s" % (
                rc, _policy_tier, n["model"],
                (" (override: %s)" % n["tier_override_reason"]) if n.get("tier_override_reason") else ""))
        # model_rationale + tools are policy-derived, runtime-bound fields — ALWAYS re-derive from the
        # graph (never preserve a stale value). Otherwise a re-emit after a model/tools change leaves a
        # self-contradictory rationale (e.g. model:opus + "cheapest tier") or a stale, over-broad tool
        # allowlist (a least-privilege regression). Only the hand-written body + description are preserved.
        rationale = _rat
        tools = _tools_for(n)
        maxturns = existing_fm.get("maxTurns") or str(_DEFAULT_MAXTURNS)
        if not body.strip():
            body = _agent_body(graph, n)
        # P1: guarantee the memory-input contract even for a hand-written body (preserved) — append if absent.
        if "_recall.json" not in body:
            body = body.rstrip("\n") + "\n\n" + _MEMORY_INPUT_BLOCK
        marker = ("cys_emitted: \"%s\"\n" % graph["harness_name"]) if in_project else ""
        fm = ("---\n"
              "name: %s\n"
              "description: \"%s\"\n"
              "model: %s\n"
              "model_rationale: \"%s\"\n"
              "tools: %s\n"
              "maxTurns: %s\n"
              "%s"
              "---\n" % (n["agent"], desc.replace('"', "'"), n["model"],
                         rationale.replace('"', "'"), tools, maxturns, marker))
        atomic_write(path, fm + body.rstrip("\n") + "\n")


def _spawn_recipe(n, prev_label):
    """Prose recipe for spawning one node via the Agent primitive, expanding its mechanism."""
    nid, agent, model, mech = n["id"], n["agent"], n["model"], n["decision_mechanism"]
    mp = n.get("mechanism_params", {})
    sch = n.get("output_schema") or "(none)"   # the real schema path (e.g. schemas/findings.json), not schemas/<id>.json
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


PHASES = ["Phase 0: 장기기억 회상 + 컨텍스트 + SOT 초기화", "Phase 1: 비용 승인",
          "Phase 2: 노드 실행 + 품질 게이트", "Phase 3: 통합 산출 + 측정"]


def _team_recipe(graph, order):
    """Team-mode Phase-2 prose: the orchestrator (= Team Lead) drives the ACTUAL team primitives
    (TeamCreate / TaskCreate-with-deps / SendMessage / TeamDelete) — not the Agent() fan of agent mode.
    Closes the 'team emit is byte-identical to agent emit' vaporware gap (validate: TEAM_EMIT_PRESENT)."""
    by = {n["id"]: n for n in graph["nodes"]}
    name = graph["harness_name"]
    deps = {nid: [e["from"] for e in graph.get("edges", []) if e["to"] == nid] for nid in order}
    members = "\n".join(
        "   - `%s` (model=%s, tools=%s) — '%s' 노드" % (by[nid]["agent"], by[nid]["model"], _tools_for(by[nid]), nid)
        for nid in order)
    tasks = "\n".join(
        "   - `TaskCreate(subject=\"%s\", owner=\"@%s\"%s)`" % (
            nid, by[nid]["agent"],
            (", depends_on=[%s]" % ", ".join("\"%s\"" % d for d in deps[nid])) if deps[nid] else "")
        for nid in order)
    return (
        "**실행 모드: team** — 오케스트레이터(=Team Lead)가 팀 프리미티브로 직접 실행한다. Agent() 순차 "
        "spawn이 아니라 TeamCreate로 팀을 구성하고 TaskCreate(의존성 포함)로 할당하며, 팀원은 SendMessage로 "
        "자체 조율한다.\n\n"
        "1. **`TeamCreate(team_name=\"%s-team\", members=[...])`** — 멤버(각 노드 agent; frontmatter model·tools "
        "런타임 강제):\n%s\n"
        "   spawns_used += 멤버수 (PostToolUse `spawn_counter`가 자동 증분; `budget_block`이 천장 강제).\n"
        "2. **`TaskCreate`** — 각 노드를 task로 생성, 의존성은 graph edges(toposort 보존):\n%s\n"
        "3. **`SendMessage`** — 팀원 간 직접 통신: 상충·누락 발견 시 관련 팀원에게 공유(리더 우회 peer-to-peer). "
        "적대적 검증 노드는 격리 — 팀원이 아니라 별도 `Agent(subagent_type=\"reviewer\")`로 spawn(L2).\n"
        "4. **Team Lead L2** — `TaskUpdate(status=completed)` 시 Lead가 산출물을 `_workspace/`에서 읽어 "
        "품질게이트(L0-L2, `gate_or_block`) 통과 + SOT `outputs.step-N` 기록(단일쓰기). PostToolUse "
        "`qa_gate_runner`가 같은 게이트를 host 인터록으로 재확인.\n"
        "5. **`TeamDelete`** — 모든 task 완료 후 팀 정리(세션당 한 팀; 다음 팀 전 반드시 TeamDelete). 산출물은 "
        "`_workspace/`에 flush.\n"
        "> **Graceful degrade (A2-iii)**: `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` 플래그가 없으면 각 task를 "
        "`Agent(subagent_type=...)` fan + `_workspace/` 핸드오프로 강등한다 — 팀 없이도 동일 그래프가 실행된다.\n"
        % (name, members, tasks))


def _topology_addendum(graph):
    """Topology-specific Phase-2 prose for the 4 topologies beyond plain pipeline/dispatch
    (M2-2: supervisor / expert-pool / hierarchical first-class emit targets + fan-out/fan-in).
    Appended to the mode-based phase-2 body; validate: TOPOLOGY_PRIMITIVE_CONSISTENCY."""
    topo = graph.get("topology")
    if topo == "fan-out-fan-in":
        return ("\n\n### 토폴로지: fan-out/fan-in (병렬 수집 → 합성)\n"
                "독립 작업을 팀(`TeamCreate` + 무의존 `TaskCreate`)으로 병렬 실행하고 `SendMessage`로 상충을 "
                "공유한다. Lead가 `_workspace/`에서 결과를 수집해 합성 sub-agent로 통합한 뒤 `TeamDelete`.\n")
    if topo == "supervisor":
        return ("\n\n### 토폴로지: supervisor (동적 작업 할당)\n"
                "Team Lead가 **supervisor**로서 초기 `TaskCreate` 배치를 만들고 팀원이 self-claim한다. 각 "
                "`TaskUpdate(status=completed)` 시 Lead가 결과를 보고 **런타임에 다음 배치 `TaskCreate`를 동적 "
                "발행**한다(정적 fan-out과 달리 작업이 동적으로 추가됨). 모든 작업 소진 시 종합 + `TeamDelete`.\n")
    if topo == "expert-pool":
        return ("\n\n### 토폴로지: expert-pool (상황별 전문가 라우팅)\n"
                "먼저 **라우터 노드**(`Agent`, haiku/sonnet)가 입력을 분류한다. 오케스트레이터는 분류 결과에 따라 "
                "**매칭된 전문가만** `Agent(subagent_type=<expert>)`로 조건부 spawn한다(모든 전문가를 항상 부르지 "
                "않음 — 비용 절감). 팀이 아니라 sub-agent 디스패치다.\n")
    if topo == "hierarchical":
        return ("\n\n### 토폴로지: hierarchical-delegation (2단계 위임, depth ≤ 2)\n"
                "Level-1: sub-coordinator들의 팀(`TeamCreate`). Level-2: 각 coordinator가 자신의 sub-agent를 "
                "`Agent()`로 spawn한다(팀원은 sub-agent를 spawn할 수 있으나 팀은 중첩 불가). **위임 깊이는 2로 "
                "제한**한다.\n")
    return ""


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
    if mode in ("team", "hybrid"):
        # P0-2 (audit): hybrid emits the REAL team recipe so it actually instantiates TeamCreate and passes the
        # A2 ALL_PRIMITIVES_PRESENT floor the validator tells builders to use (it previously fell into the agent
        # branch, emitted 0 TeamCreate, and structurally FAILED A2 — a documented mode that could never pass).
        # True per-stage agent/team mixing remains future work; today hybrid == the team recipe.
        phase2 = _team_recipe(graph, order)
    else:
        # input label = the node's ACTUAL graph-edge predecessor(s), not the linear toposort-prior node
        # (correct for fan-in/dispatch where a node's input is not the immediately-preceding toposort node).
        deps = {nid: [e["from"] for e in graph.get("edges", []) if e["to"] == nid] for nid in order}
        spawn = []
        for nid in order:
            preds = deps.get(nid) or []
            label = ("Phase 1 입력(query)" if not preds
                     else "·".join("'%s' 노드 출력" % d for d in preds))
            spawn.append(_spawn_recipe(by[nid], label))
        phase2 = ("**실행 모드: %s** — toposort 순서로 노드를 spawn하고(병렬 fan-out은 `run_in_background`), "
                  "각 노드 후 품질 게이트를 통과시킨다. spawns_used를 spawn마다 +1(단일쓰기, PostToolUse "
                  "`spawn_counter`).\n\n%s" % (mode, "\n".join(spawn)))
    phase2 = phase2 + _topology_addendum(graph)   # M2-2: topology-specific recipe (supervisor/expert-pool/hierarchical/fan-out)
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

## 실행 모드: {mode} (agent=순차 sub-spawn; team/hybrid=TeamCreate/SendMessage 실제 emit; hybrid 단계별 혼합은 future work=현재 team 레시피)

## 에이전트 구성

{table}

## 워크플로우

### {p0}
1. `<harness>/` 존재로 분기: 초기 / 재실행 / 부분 재실행 / 마이그레이션.
2. **장기기억 회상 (Tier II — 작업 입력, 실행 단계·MANDATORY)**: graph 실행 *전에* 과거 도메인 지식을 회상한다 — `Grep "{recall_key}" .harness/memory/runs/index.jsonl`로 유사 run을 찾아 **매치된 run만** `Read .harness/memory/runs/<run_id>/`(`{recall_key}`는 emit이 `query_norm(harness_name)`로 **결정론적으로 baking**한 회상 키 — LLM이 토큰을 새로 추정하지 않으며 쓰기 키와 글자 단위로 일치) + `Read .harness/memory/domain-knowledge.yaml`(+ `risk/decisions.jsonl`로 금기 확인) → 회상한 엔티티·제약을 `_workspace/_recall.json`에 떨궈 **하류 에이전트의 작업 입력**으로 넘기고, `state.yaml`의 `audit_log`에 `{{"recall": "hit|miss", "injected": [...]}}`를 기록한다. 무매치/콜드면 `_workspace/_recall.json = {{"cold": true}}`로 진행(선례 없음). 회상 직후 **run START**로 `.harness/memory/runs/index.jsonl`에 `{{"run_id": <id>, "status": "in_progress", "query_norm": "{recall_key}"}}` 1줄을 append한다(`query_norm`은 위 회상 키와 동일 리터럴 — 읽기/쓰기 키 동치 보장) — Tier-II 쓰기는 종단 일괄이 아니라 **증분 스트리밍**이라 크래시·재개·병렬 run이 부분 진행을 회상한다(완료 시 Phase 3에서 같은 레코드를 `status: "completed"`로 갱신). 이는 아래 "메모리 운영" 섹션의 prose가 아니라 **Phase 0의 실행 단계**다 — 회상→주입 도관의 입력 절반(맹신 금지: 회상은 현재 요건에 맞게 검증 후 사용).
3. `.harness/state.yaml`(SOT)을 작성/갱신한다 — **오케스트레이터 단독 쓰기**. 필드:
   `current_step, outputs{{}}, budget{{spawns_used:0, max_spawns:{max_spawns}}}, pacs{{}}, audit_log[]`.
   state.yaml 작성이 ap_state-gated AWF 기능(SOT 스키마·autopilot·Decision Log·SOT-restore)을 깨운다.
4. 재실행이면 첫 단계로 `state.yaml` + 최신 `.claude/context-snapshots/latest.md`를 읽어 맥락 복원.

### {p1}
1. `python3 ../../warrant.py --graph .harness/graph.json` 로 비용밴드 표시(`.harness/warrant.json` 기록 — PRE 게이트 산출물).
2. `budget.approval_required=true`이면 사용자 'approve' 대기 후 진행. 승인 시 `.harness/APPROVED`(승인토큰)를 기록하고 state.yaml audit_log에도 남긴다. (`constants.BUILD_GATES`를 warn/error로 켜면 warrant.json·audit.json·APPROVED 부재 시 validate가 차단 — 4-스테이지 워크플로 강제.)
3. `budget.max_spawns`는 emit이 graph에서 **결정론적으로 계산한 {max_spawns}**로 고정한다(LLM이 다시 합산하지 않음 — `sot_init.estimate_max_spawns`가 cold-start에 같은 값을 시드). 런타임 `budget_block.py`(PreToolUse)가 이 천장 초과 시 exit-2 차단.

### {p2}
{phase2}

**노드별 품질 게이트(autopilot-execution.md 순서, 각 단계 산출물 작성 직후):**
- **L0 Anti-Skip**: `python3 ../../templates/hooks/gate_or_block.py .claude/hooks/scripts/validate_pacs.py --check-l0 --step <N>` (산출물 존재+≥100B).
- **L1 Verification (필수/MANDATORY)**: 각 단계 산출물 직후 **`verification-logs/step-<N>-verify.md`를 반드시 작성**(기능 목표 100% 달성 근거) → `gate_or_block.py validate_verification.py --step <N>`. 이 로그가 없으면 `qa_gate_runner`가 **L1 BLOCK(exit-2)** 한다(L0·L1·budget는 필수 계층, L1.5·L2는 fire-on-presence).
- **L1.5 pACS**: `gate_or_block.py validate_pacs.py --step <N>` (Pre-mortem + F/C/L min, RED 차단).
- **L2 Adversarial Review** (review 노드만): reviewer/fact-checker spawn 후 `gate_or_block.py validate_review.py --step <N>`.
- FAIL → `diagnose_context.py` → `validate_diagnosis.py`, `validate_retry_budget.py` 예산 내 재시도.
> `gate_or_block.py`가 advisory validator(exit 0)를 **exit-2 인터록**으로 승격하므로, 게이트 FAIL이 단계를 실제로 멈춘다.

**메모리 릴레이 (단계간 검증된 사실 척추 — P2):** 각 노드의 단계 게이트 통과 *직후*, 검증된 핵심 사실 atom만 `.harness/memory/runs/<run_id>/stage-<N>-facts.jsonl`에 증류하고(벌크 산출물은 `_workspace/`에 유지 — 통째 로드 금지, RLM), SOT `outputs.step-<N>`에 산출물 포인터를 단일쓰기로 기록한다. **다음 노드는 하드코딩 경로 대신 SOT `outputs.step-<N>` + 직전 `stage-<N>-facts.jsonl`을 Read해 입력을 해소한다** — 검증된 사실 척추가 단계마다 *메모리를 통과*한다(벌크는 파일시스템). 데이터 이동이 장기기억을 통해 파이프라인처럼 연동되는 지점이다. 또한 검증된 새 사실은 **단계마다** `domain-knowledge.yaml`에 증분 병합한다(종단 일괄 금지 — P3 증분 스트리밍).

### {p3}
1. **run 완료(메모리 종결)**: `.harness/memory/runs/index.jsonl`의 현재 run 레코드를 `status: "completed"`로 갱신하고 산출물·출처·결정을 `runs/<run_id>/`에 저장 + 새 사실을 `domain-knowledge.yaml`에 최종 병합한다(P3 증분 스트리밍의 종결). 그리고 마지막 노드 출력을 최종 산출물로 `state.yaml outputs`에 기록한다.
2. `git init && git add -A && git commit`(rollback substrate).
3. (선택) head-to-head: `evals/{name}.scorecard.json` 기준 C2(이 하네스) vs C3(no-harness) n≥5 → `h2h_aggregate.py`.

## 메모리 운영 (Context Preservation — 상속 게놈 hook이 발화하는 일급 기능)
이 하네스는 **장기기억**을 일급 기능으로 갖는다. 라이브 세션에서 상속 게놈 hook이 자동 발화한다:
- **세션 연속성(Tier I)**: 토큰 초과·`/clear`·컨텍스트 압축·세션 종료 시 `context_guard`/`save_context`가
  `.claude/context-snapshots/latest.md`에 스냅샷을 저장한다. IMMORTAL 섹션(현재 작업·다음 단계·SOT·품질게이트
  상태)은 압축에도 우선 보존된다. 새 세션 시작 시 `[CONTEXT RECOVERY]` 메시지가 뜨면 **반드시** 안내된
  `latest.md`를 Read로 읽어 맥락을 복원한 뒤 진행한다.
- **교차세션 지식(RLM 패턴)**: `.claude/context-snapshots/knowledge-index.jsonl`은 세션별 작업·수정파일·
  error→resolution을 누적한 **외부 메모리**다. 통째로 로드하지 말고 **Grep으로 질의**한다(RLM):
  예) `Grep "<주제>" .claude/context-snapshots/knowledge-index.jsonl`. 과거 error→resolution은 SessionStart가
  자동 표시한다.
- 작업 시작 시 SOT(`state.yaml`) + `latest.md`를 읽어 현재 단계·산출물·예산을 복원한다.
- **교차-실행 도메인 메모리 (Tier II, `.harness/memory/`)** — 이 하네스가 *반복 실행*을 거쳐 도메인 지식을
  누적한다(RLM 외부 환경 — 통째 로드 금지, 프로그램적으로 질의):
  - **작업 시작 시 회상**: `Grep "{recall_key}" .harness/memory/runs/index.jsonl` 로 과거 유사 실행을
    찾고, **매치된 run만** `Read .harness/memory/runs/<run_id>/`로 가져온다(결과가 많으면 `Agent`로 스니펫을 재귀
    분해). `domain-knowledge.yaml`을 읽어 L1 검증 기준으로 주입하고, `risk/decisions.jsonl`로 금기를 확인한다.
  - **완료 시 기록(단일쓰기=오케스트레이터)**: `runs/index.jsonl`에 1줄 추가
    ({{run_id, ts, query_norm, topology, final_status, outputs[+sha256], sources, tags}}) + `runs/<run_id>/`에
    산출물·출처·결정 저장 + 새 사실을 `domain-knowledge.yaml`에 병합(중복제거) + 표준 위험을 `risk/decisions.jsonl`에 추가.
  - **재사용 전 검증**: 회상된 과거 산출물은 현재 `domain-knowledge.yaml`에 대해 재검증 후 사용한다(맹신 금지;
    provenance·recency 가중).

## 진화 (매 실행 후 — 살아있는 시스템, idoforgod의 진화 규약)
하네스는 고정물이 아니라 진화하는 시스템이다. 매 실행 후:
1. **피드백 수집** — 사용자에게 "개선점/팀 구성 변경점"을 1회 묻는다(강요 금지, 기회 제공).
2. **피드백 라우팅** — `python3 ../../evolve_harness.py . --type <유형> --change "..." --reason "..."`로 유형→대상을
   결정론적으로 `.harness/change-history.jsonl`(append-only)에 기록:
   - `result-quality` → 그 노드의 how(스킬/agent 본문) · `agent-role` → `.claude/agents/<agent>.md`
   - `workflow-order` → 이 오케스트레이터 SKILL · `team-comp` → 오케스트레이터+agents · `trigger-miss` → 스킬 description
3. **변경 검증** — 라우팅된 수정은 해당 Implementation 단계로 재진입 후 **반드시 `validate_harness.py`를 재통과**한다
   (진화가 계약을 퇴행시키지 못함).
4. **선제 진화** — `evolve_harness.py . --proactive`: 같은 유형 피드백 2회↑ 시 자동 제안.
5. **유지보수** — 재감사(`audit_harness.py`) → 드리프트 제시 → 한 번에 하나씩 수정 → 재검증 → CLAUDE.md 동기화.

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
""".format(name=name, mode=mode, table="\n".join(rows), phase2=phase2,
           max_spawns=estimate_max_spawns(graph), recall_key=query_norm(name),
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
    except ImportError:
        # PyYAML absent: textual merge that NEVER silently drops registrations AND never mis-nests them.
        # The new entries MUST live under a top-level `agents:` key (pre_subagent_invocation reads
        # config['agents']). If the file already has a top-level `^agents:` line, INSERT the missing
        # entries right after it (so they cannot nest under a preceding block when agents: is non-trailing);
        # otherwise append a fresh top-level `agents:` block. (Prior EOF-append nested entries under whatever
        # block came last when the file had no trailing agents: key.)
        import re
        existing = open(cpath, encoding="utf-8").read() if os.path.isfile(cpath) else ""
        missing = [n for n in graph["nodes"] if ("@%s" % n["agent"]) not in existing]
        if not missing:
            return
        entries = ["  '@%s': {rule: always_fresh}  # node %s" % (n["agent"], n["id"]) for n in missing]
        block = "\n".join(entries)
        m = re.search(r"(?m)^agents:[ \t]*$", existing)
        if m:
            insert_at = m.end()
            out = existing[:insert_at] + "\n" + block + existing[insert_at:]
            if not out.endswith("\n"):
                out += "\n"
        else:
            out = (existing.rstrip("\n") + "\n" if existing.strip() else "") + "agents:\n" + block + "\n"
        atomic_write(cpath, out)


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


def _runtime_manifest(graph, in_project=False):
    name = graph["harness_name"]
    launch = (("trigger the %s-orchestrator skill inside the host project's `claude` session — in-project "
               "overlay: this harness is one capability of the host, not the host root's own runtime" % name)
              if in_project else
              "cd <harness_dir> && claude   # THAT session's settings.json hooks fire (not the factory's)")
    return {
        "schema_version": "0.1",
        "install_mode": "in-project" if in_project else "self-contained",
        "canonical_runtime": "%s-orchestrator" % name,
        "runtimes": [
            {"name": "%s-orchestrator" % name, "role": "canonical",
             "entrypoint": ".claude/skills/%s-orchestrator/SKILL.md" % name,
             "driver": "Claude Code primitives (Agent / TeamCreate / SendMessage), live host session",
             "kind": "prose-driven, genome-active (hooks/L0-L2/SOT fire), graph.json-contracted, semantic-resume",
             "wired_to": "graph.json (this harness's contract) via emit_orchestrator",
             "use_when": "default — ALL of this harness's work runs as a live session driven by this skill",
             "launch": launch},
        ],
        # M0/locked-3 (RUNTIME_MANIFEST_CLEAN): the produced harness has exactly ONE execution runtime —
        # the orchestrator skill (100% Claude Code primitives). The retired Mode-A workflow.js and the
        # inherited prompt-runner subprocess are NOT advertised as runtimes here; prompt-runner stays
        # vendored-but-inert (never wired into execution).
        "routing_rule": "Run this harness by opening a `claude` session in its dir and triggering the "
                        "<name>-orchestrator skill. This is the ONLY execution runtime — no compiled .js "
                        "workflow runtime and no subprocess batch runner; the inherited genome hooks fire "
                        "in that live session.",
    }


def _require_valid_graph(graph):
    """Fail CLEANLY (SystemExit, not a raw KeyError traceback) on a graph missing a field that emit
    DEREFERENCES — emit (I3) runs before validate (I5), so a hand-authored graph missing e.g.
    decision_mechanism otherwise crashed with an opaque traceback. This is intentionally NARROW: it
    only guards the keys emit reads directly; the FULL schema contract (write_paths minItems, patterns,
    enums, ...) stays validate_harness.py's job at I5 (emit is lenient by design, the gate is strict)."""
    if not isinstance(graph, dict):
        raise SystemExit("emit: graph.json is not a JSON object")
    missing_g = [k for k in _REQUIRED_GRAPH_KEYS if k not in graph]
    if missing_g:
        raise SystemExit("emit: graph.json missing required key(s): %s "
                         "(fix graph.json or re-author it; validate_harness.py details the full contract)"
                         % ", ".join(missing_g))
    if not isinstance(graph.get("nodes"), list) or not graph["nodes"]:
        raise SystemExit("emit: graph.json has no nodes[]")
    for k in ("total_tokens", "approval_required"):
        if k not in (graph.get("budget") or {}):
            raise SystemExit("emit: graph.json budget missing required key '%s'" % k)
    for i, n in enumerate(graph["nodes"]):
        bad = [k for k in _REQUIRED_NODE_KEYS if k not in n]
        if bad:
            raise SystemExit("emit: node[%d] (id=%s) missing required key(s): %s"
                             % (i, n.get("id", "?"), ", ".join(bad)))
        # emit writes <agent>.md and .claude/skills/<harness>-<id>/ — id/agent must be path-safe basenames
        # so a hand-authored graph can't make emit write OUTSIDE the harness dir (emit precedes validate,
        # which enforces the full ^[a-z...]$ pattern; here we block only path traversal).
        for fld in ("id", "agent"):
            v = str(n[fld])
            if not v.strip() or v in (".", "..") or os.path.isabs(v) or v != os.path.basename(v):
                raise SystemExit("emit: node[%d].%s = %r is not a path-safe name (no '/', '..', absolute "
                                 "paths) — fix graph.json; validate_harness.py enforces the ^[a-z...]$ pattern"
                                 % (i, fld, v))
    # edges are dereferenced by toposort (e["from"]/e["to"]) and _team_recipe — a malformed edge dict
    # must fail cleanly here, not crash toposort with a raw KeyError.
    for i, e in enumerate(graph.get("edges") or []):
        if not isinstance(e, dict) or "from" not in e or "to" not in e:
            raise SystemExit("emit: edge[%d] missing 'from'/'to' (%r)" % (i, e))


def emit_orchestrator(graph, harness_dir, in_project=False):
    _require_valid_graph(graph)   # B1: clean failure on a schema-invalid graph (emit precedes validate)
    assert graph["execution_mode"] in ("agent", "team", "hybrid"), \
        "emit_orchestrator handles primitive substrate; execution_mode='workflow' -> emit_workflow.py"
    # mode-flip guard: a dir already installed in one mode must not be re-emitted in the other. An
    # in-project->self-contained re-emit would pour the genome over the host root and DESTROY host files;
    # the reverse would false-trip the agent collision guard. Refuse cleanly (start fresh to change modes).
    gj = os.path.join(harness_dir, ".harness", "GENOME.json")
    if os.path.isfile(gj):
        try:
            prior = json.load(open(gj, encoding="utf-8")).get("install_mode")
        except ValueError:
            prior = None
        want = "in-project" if in_project else "self-contained"
        if prior and prior != want:
            raise SystemExit(
                "install-mode mismatch: %s was built as '%s' but emit was requested as '%s' — re-run with the "
                "matching mode (or build into a clean dir). Refusing to avoid clobbering." % (harness_dir, prior, want))
    try:                                  # B1-sibling: a cyclic/dangling/malformed-edge graph must fail CLEANLY
        order = toposort(graph["nodes"], graph["edges"])   # at emit, not crash with a raw traceback
    except (CycleError, ValueError, KeyError, TypeError) as ex:
        raise SystemExit("emit: graph.json edges are not schedulable (%s) — fix the cycle/edge before emit; "
                         "validate_harness.py reports GRAPH_CYCLE/EDGE_INTEGRITY" % ex)
    # 1) agent files with runtime-bound frontmatter (in-project: collision-guarded + provenance-marked)
    _write_agent_files(graph, harness_dir, in_project)
    # 1.5) domain skills (M3 hybrid): author .claude/skills/<harness>-<id> for skill_authoring.mode='skill'
    from emit_domain_skill import emit_domain_skills
    emit_domain_skills(graph, harness_dir)
    # 2) orchestrator skill + README. In-project, README/harness.md go under .harness/ so the host's own
    #    root README.md / files are never clobbered (W1_GENOME + doc-drift read the relocated paths).
    skill_dir = os.path.join(harness_dir, ".claude", "skills", graph["harness_name"] + "-orchestrator")
    os.makedirs(skill_dir, exist_ok=True)
    atomic_write(os.path.join(skill_dir, "SKILL.md"), _orchestrator_skill(graph, order))
    readme_path = os.path.join(harness_dir, ".harness", "README.md") if in_project \
        else os.path.join(harness_dir, "README.md")
    if in_project:
        os.makedirs(os.path.join(harness_dir, ".harness"), exist_ok=True)
    atomic_write(readme_path, _readme(graph))
    # 3) genome transplant (orchestrator-canonical RUNTIME) — wakes hooks/gates/SOT
    errs = inherit(harness_dir, runtime_manifest=_runtime_manifest(graph, in_project), in_project=in_project)
    # 4) post-inherit: merge categorization (genome + domain agents) + harness.md genome viz
    _categorization_merge(harness_dir, graph)
    hm_path = os.path.join(harness_dir, ".harness", "harness.md") if in_project \
        else os.path.join(harness_dir, "harness.md")
    atomic_write(hm_path, _harness_md(graph, order))
    # 5) provenance lock (P2-C/audit): stamp sha256 of graph.json so validate can detect a hand-tamper
    #    AFTER emit (the 'single-writer' contract was otherwise unenforced — an edited graph validated 0/0).
    import hashlib
    gbytes = open(os.path.join(harness_dir, ".harness", "graph.json"), "rb").read()
    atomic_write(os.path.join(harness_dir, ".harness", "graph.lock"),
                 json.dumps({"sha256": hashlib.sha256(gbytes).hexdigest(),
                             "note": "emit_orchestrator stamp of graph.json; validate warns (GRAPH_PROVENANCE) "
                                     "if graph.json changed after emit — re-emit to re-bless"}, indent=2) + "\n")
    return errs


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print("usage: emit_orchestrator.py <harness_dir> [--in-project]", file=sys.stderr); sys.exit(2)
    hd = os.path.abspath(args[0])
    graph = _load(os.path.join(hd, ".harness", "graph.json"))
    errs = emit_orchestrator(graph, hd, in_project="--in-project" in sys.argv)
    if errs:
        print("emitted orchestrator for %s; GENOME VERIFY FAILED:" % graph["harness_name"])
        for e in errs:
            print("  -", e)
        sys.exit(1)
    print("emitted .claude/skills/%s-orchestrator/SKILL.md + agents + FULL AWF genome (active substrate)"
          % graph["harness_name"])


if __name__ == "__main__":
    main()
