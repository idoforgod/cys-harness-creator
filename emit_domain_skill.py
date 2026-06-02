#!/usr/bin/env python3
"""emit_domain_skill — M3 hybrid domain-skill emitter (locked decision 5).

idoforgod's defining feature is generating per-agent SKILLS (the 'how') separate from agent definitions
(the 'who'). CYS adopts that FORM (it IS the Claude-native 'how' encapsulation) but makes the
author-or-inline choice a MACHINE-CHECKED graph.json field: each node may carry
skill_authoring{mode, reason, shared_by}.

For every node with skill_authoring.mode == 'skill', this writes
.claude/skills/<harness>-<node_id>/SKILL.md — a pushy-described 'how' package the node's agent uses.
mode == 'inline' (the default) keeps the 'how' in the agent body (emit_orchestrator). The hybrid
criterion (reuse / complex / conditional) mirrors AWF's own bundling discipline, so we author a skill
only where the form adds capability — not a throwaway skill per node.

validate_harness enforces consistency (SKILL_AUTHORING_JUSTIFIED / INLINE_NO_ORPHAN_SKILL / LIFT_UNMEASURED).
CLI: emit_domain_skill.py <harness_dir>
"""
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "lib"))
from atomic_write import atomic_write          # noqa: E402
from validate_harness import _role_class_of    # noqa: E402


def skill_name(graph, node):
    return "%s-%s" % (graph["harness_name"], node["id"])


def _skill_md(graph, node):
    name = skill_name(graph, node)
    rc = _role_class_of(node)
    hn, nid = graph["harness_name"], node["id"]
    out = (node.get("outputs") or ["(return)"])[0]
    sch = node.get("output_schema") or "(none)"
    sa = node.get("skill_authoring") or {}
    reason = sa.get("reason", "complex")
    shared = sa.get("shared_by") or []
    shared_line = ("\n> 공유(reuse): 이 스킬은 노드 %s 가 재사용한다." % ", ".join(shared)) if shared else ""
    fm = ("---\n"
          "name: %s\n"
          "description: \"%s 하네스의 '%s'(%s-class) 작업 방법(how)을 캡슐화한 스킬. '%s' 관련 생성·분석·"
          "재실행·보완 작업 시 반드시 이 스킬을 사용. 후속: 다시, 수정, 개선 요청 시에도 사용.\"\n"
          "---\n" % (name, hn, nid, rc, nid))
    body = ("# %s — '%s' 노드의 how (도메인 스킬)\n\n"
            "graph.json의 `skill_authoring.mode='skill'`(reason=%s)로 emit된 도메인 스킬. 이 노드의 *어떻게*를 "
            "담는다(누가=`%s` 에이전트는 `.claude/agents/`).%s\n\n"
            "## 작업 원칙 (Why-not-ALWAYS)\n"
            "- 입력(직전 노드 출력)을 받아 **%s 스키마**에 맞는 산출물만 만든다 — 스키마는 다음 단계 계약이므로 "
            "어긴 산출물은 파이프라인을 끊는다.\n"
            "- %s-class 역할에 충실: 추측 금지, 불확실하면 출처를 병기한다(삭제 금지).\n\n"
            "## 입출력 프로토콜\n"
            "- 출력 스키마: `%s`\n"
            "- 산출물 경로: `%s`\n\n"
            "## 품질\n"
            "- 산출 직후 L0(존재+≥100B)·L1(기능목표 100%%)·L1.5(pACS)를 통과해야 한다(오케스트레이터 + "
            "`qa_gate_runner` hook이 강제).\n"
            % (name, nid, reason, node["agent"], shared_line, sch, rc, sch, out))
    return fm + body


def emit_domain_skills(graph, harness_dir):
    """Author .claude/skills/<harness>-<id>/SKILL.md for each skill-mode node. Returns the names written."""
    written = []
    for n in graph["nodes"]:
        if (n.get("skill_authoring") or {}).get("mode") == "skill":
            sn = skill_name(graph, n)
            sd = os.path.join(harness_dir, ".claude", "skills", sn)
            os.makedirs(sd, exist_ok=True)
            atomic_write(os.path.join(sd, "SKILL.md"), _skill_md(graph, n))
            written.append(sn)
    return written


def main():
    if len(sys.argv) < 2:
        print("usage: emit_domain_skill.py <harness_dir>", file=sys.stderr); sys.exit(2)
    hd = os.path.abspath(sys.argv[1])
    graph = json.load(open(os.path.join(hd, ".harness", "graph.json"), encoding="utf-8"))
    w = emit_domain_skills(graph, hd)
    print("emitted %d domain skill(s): %s" % (len(w), ", ".join(w) or "(none — all inline)"))


if __name__ == "__main__":
    main()
