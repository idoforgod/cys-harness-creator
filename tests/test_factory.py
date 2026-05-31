#!/usr/bin/env python3
"""CYS Harness Creator — factory self-test (P0-4).

The first FACTORY-NATIVE test suite (the 35 test_*.py on disk are all inherited
genome, not the factory's own). Pure/deterministic unit layer — no genome, no live
runs — so it runs clean from a fresh checkout and guards the verified core
(emit byte-determinism, validate gate codes, warrant, lift gate, toposort) against
silent regression. Stdlib unittest only.

Run: python3 -m unittest discover -s tests   (or: make test)
"""
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "lib"))

import emit_workflow            # noqa: E402
import emit_orchestrator        # noqa: E402
import warrant                  # noqa: E402
import lift_gate                # noqa: E402
import h2h_aggregate            # noqa: E402
import validate_harness         # noqa: E402
from toposort import toposort, CycleError  # noqa: E402
import importlib.util           # noqa: E402


def _load_hook(name):
    """Import a templates/hooks/<name>.py module by path (not on sys.path)."""
    p = os.path.join(ROOT, "templates", "hooks", name + ".py")
    spec = importlib.util.spec_from_file_location(name, p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

GOLDEN = os.path.join(os.path.dirname(__file__), "golden")
CORE_EXAMPLES = ["deep-research", "ticket-triage", "design-decision"]
# M0: emit_workflow (Mode-A) is retired from the product; its determinism is now guarded against
# FROZEN workflow-mode fixtures, decoupled from the product examples/ (which are now primitive mode).
MEASUREMENT_FIX = os.path.join(ROOT, "_measurement", "fixtures")


class TestEmitDeterminism(unittest.TestCase):
    """Factory-internal: emit_workflow (the retired Mode-A emitter, kept for measurement only) stays
    byte-deterministic. Fixtures are FROZEN workflow-mode graphs under _measurement/fixtures/ —
    decoupled from the product examples/, which are now primitive (agent/team) mode (M0)."""

    def test_emit_byte_identical_to_golden(self):
        import shutil
        for ex in CORE_EXAMPLES:
            with tempfile.TemporaryDirectory() as td:
                dst = os.path.join(td, ex)
                shutil.copytree(os.path.join(MEASUREMENT_FIX, ex), dst)
                graph = emit_workflow._load(os.path.join(dst, ".harness", "graph.json"))
                js = emit_workflow.emit(graph, dst)
                golden = open(os.path.join(GOLDEN, ex + ".workflow.js")).read()
                self.assertEqual(js, golden, "%s: emit() drifted from golden (determinism regression)" % ex)

    def test_emitted_has_no_clock_or_rng(self):
        for ex in CORE_EXAMPLES:
            js = open(os.path.join(GOLDEN, ex + ".workflow.js")).read()
            for forbidden in ("Date.now(", "Math.random(", "new Date("):
                self.assertNotIn(forbidden, js, "%s: emitted JS contains %s (breaks resume)" % (ex, forbidden))

    def test_emitted_is_top_level_format(self):
        for ex in CORE_EXAMPLES:
            js = open(os.path.join(GOLDEN, ex + ".workflow.js")).read()
            self.assertIn("export const meta = {", js)
            self.assertNotIn("export default", js, "%s: must be top-level-statement format" % ex)


class TestM0Hooks(unittest.TestCase):
    """M0d: the three hooks that make the budget ceiling + 4-layer QA actually fire — selftests pass,
    the interlock loop (sot_init seed -> spawn_counter increment -> budget_block ceiling) closes, and
    qa_gate_runner's L0 anti-skip blocks a missing deliverable without false-blocking a present one."""

    def test_hook_selftests_pass(self):
        import subprocess
        for h in ("spawn_counter", "sot_init", "qa_gate_runner"):
            p = os.path.join(ROOT, "templates", "hooks", h + ".py")
            rc = subprocess.run([sys.executable, p, "--selftest"], capture_output=True).returncode
            self.assertEqual(rc, 0, "%s --selftest failed" % h)

    def test_budget_interlock_loop_fires(self):
        spawn = _load_hook("spawn_counter"); budget = _load_hook("budget_block"); sot = _load_hook("sot_init")
        self.assertFalse(budget.decide(2, 8, 1)[0], "under ceiling allows")
        self.assertTrue(budget.decide(7, 8, 1)[0], "at ceiling-margin blocks (the loop the audit said never fired)")
        txt, val = spawn.bump("budget:\n  spawns_used: 4\n  max_spawns: 8\n")
        self.assertEqual(val, 5); self.assertIn("spawns_used: 5", txt)
        self.assertGreaterEqual(sot.estimate_max_spawns({"nodes": [{"decision_mechanism": "single"}]}), 1)

    def test_safe_hook_merge_preserves_host(self):
        # P1/B2: in-project install must UNION genome hooks into a host project's settings, never clobber
        # the host's existing hooks/permissions.
        import inherit_genome as ig
        with tempfile.TemporaryDirectory() as td:
            os.makedirs(os.path.join(td, ".claude"))
            json.dump({"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "echo HOSTHOOK"}]}]},
                       "permissions": {"allow": ["Bash(ls:*)"]}},
                      open(os.path.join(td, ".claude", "settings.json"), "w"))
            ig._merge_settings(td)
            d = json.load(open(os.path.join(td, ".claude", "settings.json")))
            h = json.dumps(d["hooks"])
            self.assertIn("HOSTHOOK", h, "host hook must be preserved (not clobbered)")
            self.assertEqual(d.get("permissions", {}).get("allow"), ["Bash(ls:*)"], "host permissions preserved")
            self.assertIn("context_guard", h, "genome hooks unioned in")

    def test_qa_gate_runner_l0_anti_skip(self):
        qa = _load_hook("qa_gate_runner")
        with tempfile.TemporaryDirectory() as td:
            os.makedirs(os.path.join(td, "_workspace", "n"))
            good = os.path.join("_workspace", "n", "ok.md")
            open(os.path.join(td, good), "w").write("x" * 200)
            self.assertFalse(qa.l0_block(1, {1: good}, td)[0], "present deliverable must not false-block")
            self.assertTrue(qa.l0_block(1, {1: "_workspace/n/missing.md"}, td)[0], "missing deliverable must block")


class TestToposort(unittest.TestCase):
    def test_linear_order(self):
        nodes = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
        edges = [{"from": "a", "to": "b"}, {"from": "b", "to": "c"}]
        self.assertEqual(toposort(nodes, edges), ["a", "b", "c"])

    def test_tie_break_by_array_index(self):
        nodes = [{"id": "a"}, {"id": "b"}, {"id": "sink"}]
        edges = [{"from": "a", "to": "sink"}, {"from": "b", "to": "sink"}]
        self.assertEqual(toposort(nodes, edges), ["a", "b", "sink"])  # a before b (index)

    def test_cycle_detected(self):
        nodes = [{"id": "a"}, {"id": "b"}]
        edges = [{"from": "a", "to": "b"}, {"from": "b", "to": "a"}]
        self.assertRaises(CycleError, toposort, nodes, edges)


class TestWarrant(unittest.TestCase):
    def test_offramp_trivial_answer_directly(self):
        v = warrant.classify({"distinct_expertise_domains": 1, "has_dependent_or_parallel_stages": False,
                              "will_be_rerun": False, "output_objective": True, "noisy": False})
        self.assertEqual(v["verdict"], "answer-directly")

    def test_offramp_single_agent(self):
        v = warrant.classify({"distinct_expertise_domains": 1, "has_dependent_or_parallel_stages": False,
                              "will_be_rerun": True, "output_objective": True, "noisy": True})
        self.assertEqual(v["verdict"], "single-agent")

    def test_build_harness_pipeline(self):
        v = warrant.classify({"distinct_expertise_domains": 4, "has_dependent_or_parallel_stages": True,
                              "will_be_rerun": True, "output_objective": True, "noisy": True})
        self.assertEqual(v["verdict"], "build-harness")
        self.assertEqual(v["topology"], "pipeline")
        self.assertEqual(v["n_agents"], 4)

    def test_max_fanout_cap_and_warning(self):
        v = warrant.classify({"distinct_expertise_domains": 7, "has_dependent_or_parallel_stages": False,
                              "will_be_rerun": True, "output_objective": True, "noisy": False})
        self.assertEqual(v["n_agents"], warrant.MAX_FANOUT)
        self.assertTrue(v["warnings"], "over-cap must warn")

    def test_cost_band_tokens_unit(self):
        band = warrant.cost_band([{"id": "x", "model": "haiku", "decision_mechanism": "single", "retries": 0}])
        self.assertIn(band["band"], ("LOW", "MEDIUM", "HIGH"))
        self.assertGreater(band["total_tokens"], 0)


class TestLiftGate(unittest.TestCase):
    def test_register_on_positive_lift(self):
        r = lift_gate.score(
            {"checks": {"A1": True, "A2": True}},
            {"checks": {"A1": False, "A2": False}},
            [{"id": "A1", "polarity": "must"}, {"id": "A2", "polarity": "must"}])
        self.assertEqual(r["decision"], "register")

    def test_refuse_on_zero_lift(self):
        r = lift_gate.score(
            {"checks": {"A1": True}},
            {"checks": {"A1": True}},
            [{"id": "A1", "polarity": "must"}])
        self.assertEqual(r["decision"], "refuse")


class TestGraphSchemaConditionals(unittest.TestCase):
    """graph.schema.json must enforce the conditional mechanism_params requirements."""

    def setUp(self):
        try:
            import jsonschema  # noqa: F401
        except ImportError:
            self.skipTest("jsonschema not installed")
        self.schema = json.load(open(os.path.join(ROOT, "graph.schema.json")))

    def _node(self, **kw):
        n = {"id": "node1", "agent": "agt", "model": "haiku", "decision_mechanism": "single",
             "mechanism_params": {}, "inputs": [], "outputs": [], "write_paths": ["_workspace/node1/"],
             "output_schema": "", "retries": 0, "on_exhaust": "proceed-with-gap", "max_rounds": 1}
        n.update(kw)
        return n

    def _graph(self, node):
        return {"schema_version": "0.1", "harness_name": "t-h", "harness_version": "0.1.0",
                "execution_mode": "workflow", "topology": "pipeline",
                "budget": {"total_tokens": 1000, "approval_required": True},
                "nodes": [node], "edges": []}

    def test_majority_vote_requires_quorum(self):
        import jsonschema
        bad = self._graph(self._node(decision_mechanism="majority-vote", mechanism_params={"n": 3}))
        self.assertRaises(jsonschema.ValidationError, jsonschema.validate, bad, self.schema)

    def test_debate_requires_judge(self):
        import jsonschema
        bad = self._graph(self._node(decision_mechanism="debate-with-judge", mechanism_params={"max_rounds": 2}))
        self.assertRaises(jsonschema.ValidationError, jsonschema.validate, bad, self.schema)

    def test_valid_graph_passes(self):
        import jsonschema
        ok = self._graph(self._node())
        jsonschema.validate(ok, self.schema)  # must not raise


class TestValidatorTierRules(unittest.TestCase):
    """validate_harness tier mirror: opus on a pure-retrieval role flags TIER_OVERSPEND."""

    def test_role_class_pure_retrieval(self):
        self.assertEqual(validate_harness._base_role_class("gather", "researcher"), "gather")
        self.assertEqual(validate_harness._role_class_of(
            {"id": "synth", "agent": "synthesizer", "decision_mechanism": "single"}), "synthesis")

    def test_opus_on_retrieval_is_pure_retrieval(self):
        self.assertIn("gather", validate_harness.PURE_RETRIEVAL)


class TestEmitOrchestrator(unittest.TestCase):
    """Pivot: graph.json -> orchestrator SKILL + agent frontmatter (primitive substrate).
    Pure/structural — no genome transplant, no live run (keeps the suite fast & clean)."""

    def _graph(self):
        return {"schema_version": "0.1", "harness_name": "demo", "harness_version": "0.1.0",
                "execution_mode": "agent", "topology": "pipeline",
                "budget": {"total_tokens": 1000, "approval_required": True},
                "nodes": [
                    {"id": "gather", "agent": "researcher", "model": "haiku", "decision_mechanism": "single",
                     "mechanism_params": {}, "inputs": [], "outputs": ["_workspace/g.json"],
                     "write_paths": ["_workspace/g/"], "output_schema": "schemas/g.json",
                     "tools": ["Read", "WebSearch"], "retries": 1, "on_exhaust": "proceed-with-gap", "max_rounds": 1},
                    {"id": "synth", "agent": "synthesizer", "model": "opus", "decision_mechanism": "single",
                     "mechanism_params": {}, "inputs": [], "outputs": ["_workspace/s.json"],
                     "write_paths": ["_workspace/s/"], "output_schema": "schemas/s.json",
                     "review": {"agent": "reviewer"}, "retries": 0, "on_exhaust": "escalate", "max_rounds": 1}],
                "edges": [{"from": "gather", "to": "synth"}]}

    def test_orchestrator_names_every_node(self):
        g = self._graph()
        order = toposort(g["nodes"], g["edges"])
        skill = emit_orchestrator._orchestrator_skill(g, order)
        for nid in ("gather", "synth"):
            self.assertIn(nid, skill, "orchestrator SKILL must name node %s (GRAPH_SKILL_CONSISTENCY)" % nid)
        self.assertIn("reviewer", skill, "review node must wire the L2 adversarial reviewer")
        self.assertIn("gate_or_block.py", skill, "gates must be invoked via the blocking wrapper")

    def test_team_mode_emits_real_primitives_not_vaporware(self):
        # M0d: team mode must drive the ACTUAL team primitives, and differ from agent emit (was
        # byte-identical — the verified vaporware gap).
        g = self._graph(); g["execution_mode"] = "team"
        team = emit_orchestrator._orchestrator_skill(g, toposort(g["nodes"], g["edges"]))
        for p in ("TeamCreate", "TaskCreate", "TeamDelete", "SendMessage", "depends_on"):
            self.assertIn(p, team, "team mode must emit %s (TEAM_EMIT_PRESENT)" % p)
        a = self._graph(); a["execution_mode"] = "agent"
        agent_skill = emit_orchestrator._orchestrator_skill(a, toposort(a["nodes"], a["edges"]))
        self.assertNotEqual(team, agent_skill, "team emit must differ from agent emit (was byte-identical)")
        self.assertNotIn("TeamDelete", agent_skill, "agent mode must not emit TeamDelete")

    def test_team_emit_satisfies_all_primitives_floor(self):
        # M2/A2: team-mode orchestrator must reference Agent Teams (TeamCreate() ) AND Sub-agents
        # (Agent() ) + a graceful-degrade note (ALL_PRIMITIVES_PRESENT + TEAM_GRACEFUL_DEGRADE). agent-only
        # must NOT have the team call form, so the floor catches it.
        g = self._graph(); g["execution_mode"] = "team"
        skill = emit_orchestrator._orchestrator_skill(g, toposort(g["nodes"], g["edges"]))
        self.assertIn("TeamCreate(", skill, "team primitive call form (ALL_PRIMITIVES_PRESENT)")
        self.assertIn("Agent(", skill, "sub-agent primitive call form")
        self.assertTrue("강등" in skill or "degrade" in skill.lower(), "graceful-degrade note (A2-iii)")
        a = self._graph(); a["execution_mode"] = "agent"
        self.assertNotIn("TeamCreate(", emit_orchestrator._orchestrator_skill(a, toposort(a["nodes"], a["edges"])),
                         "agent-only must not instantiate teams — ALL_PRIMITIVES_PRESENT must catch it")

    def test_hybrid_emits_team_recipe_and_passes_a2(self):
        # P0-2 (audit): hybrid used to fall into the agent branch, emit 0 TeamCreate, and STRUCTURALLY fail the
        # A2 floor the validator recommends. It must now emit the real team recipe (TeamCreate/TaskCreate/degrade).
        h = self._graph(); h["execution_mode"] = "hybrid"
        sk = emit_orchestrator._orchestrator_skill(h, toposort(h["nodes"], h["edges"]))
        for p in ("TeamCreate(", "Agent(", "TaskCreate("):
            self.assertIn(p, sk, "hybrid must emit the team primitive %s (A2 ALL_PRIMITIVES_PRESENT)" % p)
        self.assertTrue("강등" in sk or "degrade" in sk.lower(), "hybrid must carry the graceful-degrade note")

    def test_topology_recipes_emit_first_class(self):
        # M2-2: the 4 topologies beyond pipeline/dispatch/producer-reviewer each emit their recipe
        # (TOPOLOGY_PRIMITIVE_CONSISTENCY then enforces it at validate time).
        for topo, mode, marker in [("supervisor", "team", "동적"), ("expert-pool", "agent", "라우터"),
                                   ("hierarchical", "team", "깊이는 2"), ("fan-out-fan-in", "team", "병렬 수집")]:
            g = self._graph(); g["topology"] = topo; g["execution_mode"] = mode
            s = emit_orchestrator._orchestrator_skill(g, toposort(g["nodes"], g["edges"]))
            self.assertIn("### 토폴로지:", s, "%s must emit a topology recipe" % topo)
            self.assertIn(marker, s, "%s recipe must contain its signature %r" % (topo, marker))

    def test_memory_operating_cycle_first_class(self):
        # M1: long-term memory must be a declared operating cycle in every orchestrator (CONTEXT_
        # PRESERVATION_FIRSTCLASS) — not the old 1-line gap.
        g = self._graph()
        skill = emit_orchestrator._orchestrator_skill(g, toposort(g["nodes"], g["edges"]))
        for marker in ("메모리 운영", "knowledge-index", "latest.md", "CONTEXT RECOVERY"):
            self.assertIn(marker, skill, "orchestrator must declare memory operating cycle: %s" % marker)

    def test_evolution_loop_wired(self):
        # M5: every orchestrator carries the Phase-7 evolution loop (EVOLUTION_WIRED).
        g = self._graph()
        skill = emit_orchestrator._orchestrator_skill(g, toposort(g["nodes"], g["edges"]))
        for marker in ("진화", "evolve_harness", "change-history"):
            self.assertIn(marker, skill, "orchestrator must wire the evolution loop: %s" % marker)

    def test_tools_respects_node_then_role_class(self):
        g = self._graph()
        self.assertEqual(emit_orchestrator._tools_for(g["nodes"][0]), "Read, WebSearch")  # explicit
        synth = dict(g["nodes"][1]); synth.pop("tools", None)
        self.assertIn("Write", emit_orchestrator._tools_for(synth))  # synthesis role-class default

    def test_runtime_manifest_canonical_is_orchestrator(self):
        rm = emit_orchestrator._runtime_manifest(self._graph())
        self.assertEqual(rm["canonical_runtime"], "demo-orchestrator")
        self.assertIn("launch", rm["runtimes"][0], "must record the session-launch handoff (R4)")


class TestDomainSkill(unittest.TestCase):
    """M3 hybrid authoring: a skill-mode node authors a .claude/skills/<harness>-<id>/SKILL.md (the 'how');
    inline nodes (the default) author nothing — the 'how' stays in the agent body."""

    def _g(self, sa):
        node = {"id": "synth", "agent": "synthesizer", "model": "opus", "decision_mechanism": "single",
                "mechanism_params": {}, "inputs": [], "outputs": ["_workspace/s.json"],
                "write_paths": ["_workspace/s/"], "output_schema": "schemas/s.json", "retries": 0,
                "on_exhaust": "escalate", "max_rounds": 1}
        if sa is not None:
            node["skill_authoring"] = sa
        return {"schema_version": "0.1", "harness_name": "dh", "harness_version": "0.1.0",
                "execution_mode": "team", "topology": "pipeline",
                "budget": {"total_tokens": 1000, "approval_required": True}, "nodes": [node], "edges": []}

    def test_skill_mode_authors_inline_does_not(self):
        import emit_domain_skill
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(emit_domain_skill.emit_domain_skills(self._g({"mode": "skill", "reason": "complex"}), td),
                             ["dh-synth"])
            sk = os.path.join(td, ".claude", "skills", "dh-synth", "SKILL.md")
            self.assertTrue(os.path.isfile(sk))
            body = open(sk, encoding="utf-8").read()
            self.assertIn("name: dh-synth", body)
            self.assertIn("how", body.lower())
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(emit_domain_skill.emit_domain_skills(self._g(None), td), [],
                             "node without skill_authoring (inline default) authors no skill")
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(emit_domain_skill.emit_domain_skills(self._g({"mode": "inline"}), td), [])


class TestEightUseCases(unittest.TestCase):
    """M7 / R2 parity bar: the factory must emit a CONFORMING harness shape for all 8 idoforgod README
    use cases — build-level (graph conforms to the contract; orchestrator has the right topology recipe,
    the A2 all-primitive floor, and the mandatory DNA). Run-level h2h is a separate quota-gated lane."""

    USE_CASES = [
        ("Deep Research", "fan-out-fan-in", "team"),
        ("Website Development", "pipeline", "team"),
        ("Webtoon / Comic Production", "producer-reviewer", "team"),
        ("YouTube Content Planning", "supervisor", "team"),
        ("Code Review & Refactoring", "fan-out-fan-in", "team"),
        ("Technical Documentation", "pipeline", "team"),
        ("Data Pipeline Design", "hierarchical", "team"),
        ("Marketing Campaign", "producer-reviewer", "team"),
    ]

    def _graph(self, topology, exec_mode):
        return {"schema_version": "0.1", "harness_name": "use-case", "harness_version": "0.1.0",
                "execution_mode": exec_mode, "topology": topology,
                "budget": {"total_tokens": 1000, "approval_required": True},
                "nodes": [{"id": "work", "agent": "worker", "model": "sonnet", "decision_mechanism": "single",
                           "mechanism_params": {}, "inputs": [], "outputs": ["_workspace/work.json"],
                           "write_paths": ["_workspace/work/"], "output_schema": "", "retries": 0,
                           "on_exhaust": "proceed-with-gap", "max_rounds": 1}], "edges": []}

    def test_all_eight_use_cases_conform(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema not installed")
        import eval_topology
        schema = json.load(open(os.path.join(ROOT, "graph.schema.json")))
        topos = set()
        for use_case, topology, exec_mode in self.USE_CASES:
            g = self._graph(topology, exec_mode)
            jsonschema.validate(g, schema)  # graph conforms to the machine contract
            skill = emit_orchestrator._orchestrator_skill(g, toposort(g["nodes"], g["edges"]))
            mism = eval_topology.match(g, skill, {"use_case": use_case, "topology": topology, "exec_mode": exec_mode})
            self.assertEqual(mism, [], "%s did not conform: %s" % (use_case, mism))
            topos.add(topology)
        self.assertEqual(len(self.USE_CASES), 8, "all 8 idoforgod use cases covered (USECASE_COVERAGE)")
        self.assertGreaterEqual(len(topos), 4, "the 8 use cases must exercise multiple first-class topologies")


class TestMemoryStore(unittest.TestCase):
    """M6: Tier-II cross-run domain memory store — seeded, idempotent (accretes run over run), RLM-queried."""

    def test_init_seeds_and_is_idempotent(self):
        import inherit_genome as ig
        with tempfile.TemporaryDirectory() as td:
            ig._init_memory_store(td)
            mem = os.path.join(td, ".harness", "memory")
            for rel in ("archive.manifest.json", "domain-knowledge.yaml", os.path.join("runs", "index.jsonl")):
                self.assertTrue(os.path.isfile(os.path.join(mem, rel)), "seed missing: %s" % rel)
            idx = os.path.join(mem, "runs", "index.jsonl")
            with open(idx, "a") as f:
                f.write('{"run_id":"r1"}\n')
            ig._init_memory_store(td)  # re-run
            self.assertIn("r1", open(idx).read(), "re-init must not clobber accumulated runs")

    def test_orchestrator_declares_tier2_rlm_recipe(self):
        g = {"schema_version": "0.1", "harness_name": "m", "harness_version": "0.1.0", "execution_mode": "team",
             "topology": "pipeline", "budget": {"total_tokens": 1000, "approval_required": True},
             "nodes": [{"id": "a", "agent": "agt", "model": "haiku", "decision_mechanism": "single",
                        "mechanism_params": {}, "inputs": [], "outputs": ["_workspace/a.json"],
                        "write_paths": ["_workspace/a/"], "output_schema": "", "retries": 0,
                        "on_exhaust": "proceed-with-gap", "max_rounds": 1}], "edges": []}
        s = emit_orchestrator._orchestrator_skill(g, toposort(g["nodes"], g["edges"]))
        self.assertIn("교차-실행 도메인 메모리", s)
        self.assertIn("runs/index.jsonl", s)
        self.assertIn("Grep", s, "RLM: query the index programmatically, never bulk-load")


class TestEvolve(unittest.TestCase):
    """M5 Phase-7: evolve_harness routes feedback deterministically + proposes evolution on recurrence."""

    def test_route_feedback(self):
        import evolve_harness as ev
        self.assertEqual(ev.route_feedback("workflow-order"), "orchestrator")
        self.assertEqual(ev.route_feedback("trigger-miss"), "skill-description")
        self.assertIsNone(ev.route_feedback("nonsense"))

    def test_record_and_proactive(self):
        import evolve_harness as ev
        with tempfile.TemporaryDirectory() as td:
            ev.record(td, "2026-05-30", "result-quality", "deepen", "shallow")
            ev.record(td, "2026-05-30", "result-quality", "sources", "thin")
            ev.record(td, "2026-05-30", "trigger-miss", "kw", "missed")
            hist = ev.read_history(td)
            self.assertEqual(len(hist), 3, "append-only log accumulates")
            ft = {p["feedback_type"] for p in ev.proactive_proposals(hist)}
            self.assertIn("result-quality", ft, "2x -> proposed")
            self.assertNotIn("trigger-miss", ft, "1x -> not proposed")
            with self.assertRaises(ValueError):
                ev.record(td, "d", "bogus-type", "c", "r")


class TestAudit(unittest.TestCase):
    """M4 Phase-0: audit_harness classifies new/extend/maintain and detects drift deterministically."""

    def test_classify_branch(self):
        import audit_harness as ah
        self.assertEqual(ah.classify_branch({"has_graph": False, "agents_on_disk": set()}, []), "new")
        self.assertEqual(ah.classify_branch({"has_graph": True, "agents_on_disk": {"a"}}, []), "extend")
        self.assertEqual(ah.classify_branch({"has_graph": True, "agents_on_disk": {"a"}}, [{"kind": "agent"}]), "maintain")

    def test_drift_set_diffs(self):
        import audit_harness as ah
        g = {"harness_name": "h", "nodes": [
            {"id": "a", "agent": "researcher"},
            {"id": "b", "agent": "synth", "skill_authoring": {"mode": "skill", "reason": "complex"}}]}
        kinds = {(d["kind"], d["name"]) for d in ah.compute_drift(g, {"researcher", "orphan"}, set())}
        self.assertIn(("agent", "orphan"), kinds, "on-disk agent not in graph = drift")
        self.assertIn(("agent", "synth"), kinds, "graph agent not on disk = drift")
        self.assertIn(("skill", "h-b"), kinds, "graph-implied skill not on disk = drift")
        self.assertNotIn(("agent", "researcher"), kinds, "matched agent is not drift")


class TestMeasurementDrift(unittest.TestCase):
    """The +37.5pp lesson: reference docs must cite the REAL evals verdict, never a stale win."""

    def test_no_stale_h2h_figure_and_real_verdict_cited(self):
        vp = os.path.join(ROOT, "examples", "deep-research", "evals", "deep-research.verdict.json")
        verdict = json.load(open(vp))["verdict"]
        doc = open(os.path.join(ROOT, "skills", "harness-creator", "references",
                                "testing-and-measurement.md")).read()
        self.assertIn(verdict, doc, "doc must cite the real verdict on disk (%s)" % verdict)
        # any mention of the old +37.5pp must be marked deprecated — never presented as a live claim
        for line in doc.splitlines():
            if "37.5" in line:
                self.assertTrue(any(w in line for w in ("폐기", "deprecated", "stale", "차단", "이전 판본")),
                                "a +37.5pp mention must be flagged deprecated, not a live win claim: %r" % line)

    def test_design_docs_no_live_stale_benchmark(self):
        # STALE_BENCHMARK (M8): the FACTORY's own design/ docs are where the marketing lives — extend the
        # honesty gate to them. Any +38pp / 'CYS WINS' mention must be flagged discarded, and the real
        # on-disk verdict must be cited. (The in-harness MEASUREMENT_DRIFT does not scan factory docs.)
        verdict = json.load(open(os.path.join(ROOT, "examples", "deep-research", "evals",
                                              "deep-research.verdict.json")))["verdict"]
        flags = ("폐기", "거짓", "deprecated", "discarded", "버려", "모순")
        for rel in ("design/compare-vs-idoforgod-harness.md", "design/compare-vs-agenticworkflow.md"):
            doc = open(os.path.join(ROOT, rel), encoding="utf-8").read()
            self.assertIn(verdict, doc, "%s must cite the real on-disk verdict (%s)" % (rel, verdict))
            for line in doc.splitlines():
                if "+38" in line or "CYS WINS" in line or "CYS-WINS" in line:
                    self.assertTrue(any(w in line for w in flags),
                                    "%s: +38pp/CYS-WINS must be flagged discarded, never live: %r" % (rel, line))

    def test_validate_flags_cys_wins_without_verdict(self):
        with tempfile.TemporaryDirectory() as td:
            os.makedirs(os.path.join(td, "evals"))
            os.makedirs(os.path.join(td, ".claude", "skills", "x-orchestrator"))
            with open(os.path.join(td, "evals", "x.verdict.json"), "w") as f:
                json.dump({"verdict": "BASELINE-WINS", "delta_pp": -16.67}, f)
            with open(os.path.join(td, "README.md"), "w") as f:
                f.write("This harness is CYS-WINS for sure.\n")
            rep = validate_harness.Report()
            validate_harness._measurement_drift(td, rep)
            codes = [i["code"] for i in rep.items]
            self.assertIn("MEASUREMENT_DRIFT", codes)


class TestTierPolicyMirror(unittest.TestCase):
    """C16: validate_harness.TIER_BY_ROLE_CLASS hand-mirrors model-tier-policy.js. Catch drift."""

    def test_py_and_js_tier_maps_match(self):
        import shutil
        import subprocess
        if not shutil.which("node"):
            self.skipTest("node not installed")
        js = os.path.join(ROOT, "model-tier-policy.js")
        out = subprocess.run(["node", "-e",
                              "process.stdout.write(JSON.stringify(require('%s').TIER_BY_ROLE_CLASS))" % js],
                             capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, "node failed: " + out.stderr)
        self.assertEqual(json.loads(out.stdout), validate_harness.TIER_BY_ROLE_CLASS,
                         "tier map drift between model-tier-policy.js and validate_harness.py — keep in sync")


class TestWarrantTeamCost(unittest.TestCase):
    """CD-3: cost_band adds team-coordination tokens under execution_mode team|hybrid."""

    def test_team_mode_costs_more_than_agent(self):
        nodes = [{"id": "a", "model": "haiku", "decision_mechanism": "single", "retries": 0},
                 {"id": "b", "model": "sonnet", "decision_mechanism": "single", "retries": 0}]
        agent = warrant.cost_band(nodes, execution_mode="agent")
        team = warrant.cost_band(nodes, execution_mode="team")
        self.assertEqual(agent["team_coordination_tokens"], 0)
        self.assertGreater(team["team_coordination_tokens"], 0)
        self.assertGreater(team["total_tokens"], agent["total_tokens"])

    def test_default_is_agent_backward_compatible(self):
        nodes = [{"id": "a", "model": "haiku", "decision_mechanism": "single", "retries": 0}]
        self.assertEqual(warrant.cost_band(nodes)["team_coordination_tokens"], 0)


class TestPivotHooks(unittest.TestCase):
    """gate_or_block (advisory->blocking) and budget_block (spawn-count ceiling) decision logic."""

    def test_gate_or_block_verdict(self):
        g = _load_hook("gate_or_block")
        self.assertTrue(g.verdict('{"valid": false, "violations": ["x"]}', 0)[0])   # block
        self.assertFalse(g.verdict('{"valid": true}', 0)[0])                         # pass
        self.assertTrue(g.verdict('{"status": "fail"}', 0)[0])                       # block
        self.assertFalse(g.verdict("not json", 0)[0])                                # advisory pass
        self.assertTrue(g.verdict("anything", 2)[0])                                 # exit2 -> block

    def test_budget_block_decide(self):
        b = _load_hook("budget_block")
        self.assertFalse(b.decide(5, 10, 1)[0])    # under ceiling
        self.assertTrue(b.decide(10, 10, 1)[0])    # over ceiling
        self.assertFalse(b.decide(0, None, 1)[0])  # no max -> advisory pass


class TestInProjectInstall(unittest.TestCase):
    """P1.2/B2: `--in-project` installs the harness as an ADDITIVE OVERLAY into an existing host project —
    the host's own root files are preserved, the genome constitution is relocated under .harness/genome/,
    runtime log dirs nest under .harness/, and validate passes in-project mode. Self-contained pour unchanged."""

    def _graph(self):
        return {"schema_version": "0.1", "harness_name": "hostfit", "harness_version": "0.1.0",
                "execution_mode": "team", "topology": "pipeline",
                "budget": {"total_tokens": 1000, "approval_required": True},
                "nodes": [
                    {"id": "gather", "agent": "hostfit-gatherer", "model": "haiku", "decision_mechanism": "single",
                     "mechanism_params": {}, "inputs": [], "outputs": ["_workspace/g.json"],
                     "write_paths": ["_workspace/g/"], "output_schema": "schemas/g.json",
                     "retries": 1, "on_exhaust": "proceed-with-gap", "max_rounds": 1},
                    {"id": "synth", "agent": "hostfit-synth", "model": "opus", "decision_mechanism": "single",
                     "mechanism_params": {}, "inputs": [], "outputs": ["_workspace/s.json"],
                     "write_paths": ["_workspace/s/"], "output_schema": "schemas/s.json",
                     "review": {"agent": "reviewer"}, "retries": 0, "on_exhaust": "escalate", "max_rounds": 1}],
                "edges": [{"from": "gather", "to": "synth"}]}

    def _host(self, td, g):
        """A realistic pre-existing host project: own root docs, own agent, own skill, own settings."""
        os.makedirs(os.path.join(td, ".harness"))
        os.makedirs(os.path.join(td, "schemas"))
        json.dump(g, open(os.path.join(td, ".harness", "graph.json"), "w"))
        for s in ("g", "s"):
            json.dump({"type": "object"}, open(os.path.join(td, "schemas", s + ".json"), "w"))
        open(os.path.join(td, "CLAUDE.md"), "w").write("# HOST CLAUDE\nhost-specific instructions\n")
        open(os.path.join(td, "README.md"), "w").write("# Host Project\nthe host's own readme\n")
        open(os.path.join(td, "AGENTS.md"), "w").write("# HOST AGENTS\nhost agent registry\n")
        open(os.path.join(td, "soul.md"), "w").write("# HOST SOUL\n")
        os.makedirs(os.path.join(td, ".claude", "agents"))
        open(os.path.join(td, ".claude", "agents", "reviewer.md"), "w").write(
            "---\nname: reviewer\ndescription: \"host reviewer\"\nmodel: opus\n---\nHOST REVIEWER BODY\n")
        open(os.path.join(td, ".claude", "agents", "my-host-helper.md"), "w").write(
            "---\nname: my-host-helper\ndescription: \"host helper\"\nmodel: haiku\n---\nHOST HELPER BODY\n")
        os.makedirs(os.path.join(td, ".claude", "skills", "host-skill"))
        open(os.path.join(td, ".claude", "skills", "host-skill", "SKILL.md"), "w").write(
            "---\nname: host-skill\ndescription: host\n---\nbody\n")
        # a host-tuned security hook of a genome-shared name must NOT be clobbered
        os.makedirs(os.path.join(td, ".claude", "hooks", "scripts"))
        open(os.path.join(td, ".claude", "hooks", "scripts", "block_destructive_commands.py"), "w").write(
            "# HOST-TUNED HOOK\ndef host_marker():\n    return 'Bash(terraform destroy*)'\n")
        json.dump({"hooks": {"PreToolUse": [{"matcher": "Bash",
                   "hooks": [{"type": "command", "command": "echo HOSTHOOK"}]}]},
                   "permissions": {"allow": ["Bash(ls:*)"]}},
                  open(os.path.join(td, ".claude", "settings.json"), "w"))

    def test_overlay_preserves_host_and_validates(self):
        g = self._graph()
        with tempfile.TemporaryDirectory() as td:
            self._host(td, g)
            errs = emit_orchestrator.emit_orchestrator(g, td, in_project=True)
            self.assertEqual(errs, [], "genome verify must pass in-project: %s" % errs)
            rd = lambda *p: open(os.path.join(td, *p), encoding="utf-8").read()
            # host root files PRESERVED (not clobbered by the genome)
            self.assertIn("host-specific", rd("CLAUDE.md"))
            self.assertIn("CYS Harness Engine (inherited", rd("CLAUDE.md"), "CYS pointer appended to host CLAUDE.md")
            self.assertEqual(rd("README.md"), "# Host Project\nthe host's own readme\n", "host README untouched")
            self.assertIn("host agent registry", rd("AGENTS.md"), "host AGENTS.md preserved")
            self.assertIn("HOST SOUL", rd("soul.md"), "host soul.md preserved")
            self.assertIn("HOST HELPER BODY", rd(".claude", "agents", "my-host-helper.md"),
                          "host's own agent must NOT be clobbered (--ignore-existing)")
            self.assertIn("host-skill", rd(".claude", "skills", "host-skill", "SKILL.md"), "host skill preserved")
            # host-tuned security hook of a genome-shared name preserved (hooks are non-clobber too)
            self.assertIn("HOST-TUNED HOOK", rd(".claude", "hooks", "scripts", "block_destructive_commands.py"),
                          "host-tuned security hook must NOT be clobbered")
            # mandatory L2 agent (reviewer) force-installed from GENOME; host's version preserved (backed up)
            self.assertNotIn("HOST REVIEWER BODY", rd(".claude", "agents", "reviewer.md"),
                             "reviewer must be the genome adversarial agent (L2 DNA), not the host's")
            self.assertIn("HOST REVIEWER BODY", rd(".harness", "genome", "displaced", "reviewer.md"),
                          "displaced host reviewer must be backed up, never destroyed")
            # genome did NOT dump into the host root
            for noisy in ("prompt-runner", "prompt", "DECISION-LOG.md", "GEMINI.md",
                          "AGENTICWORKFLOW-ARCHITECTURE-AND-PHILOSOPHY.md", "translations"):
                self.assertFalse(os.path.exists(os.path.join(td, noisy)),
                                 "genome %s must not land at the host root" % noisy)
            # constitution RELOCATED under .harness/genome/ ; docs/ co-located
            for c in ("soul.md", "AGENTS.md", "CLAUDE.md"):
                self.assertTrue(os.path.isfile(os.path.join(td, ".harness", "genome", c)),
                                ".harness/genome/%s (relocated constitution)" % c)
            self.assertTrue(os.path.isdir(os.path.join(td, ".harness", "genome", "docs")), "docs/ co-located")
            # harness README/harness.md relocated under .harness/ (host root never gets them)
            self.assertTrue(os.path.isfile(os.path.join(td, ".harness", "README.md")))
            self.assertTrue(os.path.isfile(os.path.join(td, ".harness", "harness.md")))
            self.assertFalse(os.path.isfile(os.path.join(td, "harness.md")), "no harness.md at host root")
            # node agents written with the provenance marker; genome capability agents added (non-clobber)
            self.assertIn("cys_emitted", rd(".claude", "agents", "hostfit-gatherer.md"))
            self.assertTrue(os.path.isfile(os.path.join(td, ".claude", "agents", "fact-checker.md")),
                            "genome fact-checker added (host lacked it)")
            # runtime log dirs nested under .harness/, not the host root
            self.assertTrue(os.path.isdir(os.path.join(td, ".harness", "pacs-logs")))
            self.assertFalse(os.path.exists(os.path.join(td, "pacs-logs")), "no pacs-logs/ at host root")
            # settings: host hook + permissions preserved; genome hooks + security denies unioned in
            s = json.load(open(os.path.join(td, ".claude", "settings.json")))
            self.assertIn("HOSTHOOK", json.dumps(s["hooks"]), "host hook preserved")
            self.assertIn("context_guard", json.dumps(s["hooks"]), "genome hooks unioned")
            self.assertEqual(s["permissions"]["allow"], ["Bash(ls:*)"], "host permissions preserved")
            self.assertTrue(s.get("permissions", {}).get("deny"), "genome security deny-list adopted (parity)")
            # marker stamped + in-project validate PASSES with 0 errors
            self.assertEqual(json.load(open(os.path.join(td, ".harness", "GENOME.json")))["install_mode"], "in-project")
            errors = [i for i in validate_harness.validate(td).items if i["level"] == "error"]
            self.assertEqual(errors, [], "in-project harness must validate 0 errors: %s" % errors)

    def test_host_agent_collision_refused(self):
        # a node.agent colliding with a host-owned agent (no cys_emitted marker) must be refused, not hijacked
        g = self._graph(); g["nodes"][0]["agent"] = "my-host-helper"   # collides with host's own agent
        with tempfile.TemporaryDirectory() as td:
            self._host(td, g)
            with self.assertRaises(SystemExit):
                emit_orchestrator.emit_orchestrator(g, td, in_project=True)

    def test_nonobject_settings_does_not_crash(self):
        # adversarial finding: a host settings.json that is valid JSON but NOT an object must not crash emit
        g = self._graph()
        for content in ("[]", "null", "42", "\"hi\""):
            with tempfile.TemporaryDirectory() as td:
                self._host(td, g)
                open(os.path.join(td, ".claude", "settings.json"), "w").write(content)
                errs = emit_orchestrator.emit_orchestrator(g, td, in_project=True)
                self.assertEqual(errs, [], "non-object settings %r must degrade gracefully" % content)
                self.assertIn("context_guard", json.dumps(json.load(
                    open(os.path.join(td, ".claude", "settings.json")))), "genome hooks wired")

    def test_unparseable_settings_refused(self):
        # adversarial finding: never SILENTLY replace an unparseable host settings.json — refuse instead
        g = self._graph()
        with tempfile.TemporaryDirectory() as td:
            self._host(td, g)
            open(os.path.join(td, ".claude", "settings.json"), "w").write("{ not valid json ]")
            with self.assertRaises(SystemExit):
                emit_orchestrator.emit_orchestrator(g, td, in_project=True)

    def test_mode_flip_refused_both_directions(self):
        # adversarial finding: re-emitting a dir in the OTHER install mode must be refused (host-clobber guard)
        g = self._graph()
        with tempfile.TemporaryDirectory() as td:        # self-contained -> in-project
            os.makedirs(os.path.join(td, ".harness")); os.makedirs(os.path.join(td, "schemas"))
            json.dump(g, open(os.path.join(td, ".harness", "graph.json"), "w"))
            for s in ("g", "s"):
                json.dump({"type": "object"}, open(os.path.join(td, "schemas", s + ".json"), "w"))
            emit_orchestrator.emit_orchestrator(g, td, in_project=False)
            with self.assertRaises(SystemExit):
                emit_orchestrator.emit_orchestrator(g, td, in_project=True)
        with tempfile.TemporaryDirectory() as td:        # in-project -> self-contained (the host-destroying flip)
            self._host(td, g)
            emit_orchestrator.emit_orchestrator(g, td, in_project=True)
            with self.assertRaises(SystemExit):
                emit_orchestrator.emit_orchestrator(g, td, in_project=False)
            self.assertEqual(open(os.path.join(td, "README.md")).read(), "# Host Project\nthe host's own readme\n",
                             "refused self-contained re-emit must leave the host README intact")

    def test_self_contained_keeps_root_layout(self):
        # the default (self-contained) pour is unchanged: constitution + harness.md at the ROOT, marker says so
        g = self._graph()
        with tempfile.TemporaryDirectory() as td:
            os.makedirs(os.path.join(td, ".harness")); os.makedirs(os.path.join(td, "schemas"))
            json.dump(g, open(os.path.join(td, ".harness", "graph.json"), "w"))
            for s in ("g", "s"):
                json.dump({"type": "object"}, open(os.path.join(td, "schemas", s + ".json"), "w"))
            errs = emit_orchestrator.emit_orchestrator(g, td, in_project=False)
            self.assertEqual(errs, [])
            self.assertTrue(os.path.isfile(os.path.join(td, "soul.md")), "self-contained keeps constitution at root")
            self.assertTrue(os.path.isfile(os.path.join(td, "harness.md")), "self-contained harness.md at root")
            self.assertFalse(os.path.isdir(os.path.join(td, ".harness", "genome")), "no relocation when self-contained")
            self.assertNotIn("cys_emitted", open(os.path.join(td, ".claude", "agents", "hostfit-gatherer.md")).read(),
                             "self-contained agents carry no in-project marker")
            self.assertEqual(json.load(open(os.path.join(td, ".harness", "GENOME.json")))["install_mode"],
                             "self-contained")
            errors = [i for i in validate_harness.validate(td).items if i["level"] == "error"]
            self.assertEqual(errors, [], "self-contained must still validate 0 errors: %s" % errors)


class TestLiftWiring(unittest.TestCase):
    """P1.3: the skill lift gate has teeth. `score --out` writes the verdict to the path validate reads;
    validate then gates: unmeasured = policy (LIFT_UNMEASURED, default warn), measured-and-refused = hard
    LIFT_REFUSED error (a skill that loses to the baseline must not ship)."""

    def _skill_harness(self, td, verdict=None):
        os.makedirs(os.path.join(td, ".harness"))
        g = {"schema_version": "0.1", "harness_name": "lw", "harness_version": "0.1.0",
             "execution_mode": "team", "topology": "pipeline",
             "budget": {"total_tokens": 1000, "approval_required": True},
             "nodes": [{"id": "synth", "agent": "lw-synth", "model": "opus", "decision_mechanism": "single",
                        "mechanism_params": {}, "inputs": [], "outputs": ["_workspace/s.json"],
                        "write_paths": ["_workspace/s/"], "output_schema": "schemas/s.json",
                        "skill_authoring": {"mode": "skill", "reason": "complex"},
                        "retries": 0, "on_exhaust": "escalate", "max_rounds": 1}], "edges": []}
        json.dump(g, open(os.path.join(td, ".harness", "graph.json"), "w"))
        skdir = os.path.join(td, ".claude", "skills", "lw-synth"); os.makedirs(skdir)
        open(os.path.join(skdir, "SKILL.md"), "w").write("---\nname: lw-synth\ndescription: how\n---\nhow\n")
        if verdict is not None:
            json.dump(verdict, open(os.path.join(skdir, "lift_verdict.json"), "w"))

    def _codes(self, td):
        return {i["code"]: i["level"] for i in validate_harness.validate(td).items}

    def test_score_out_writes_verdict_file(self):
        import subprocess
        with tempfile.TemporaryDirectory() as td:
            res = {"assertions": [{"id": "A1", "polarity": "must"}, {"id": "A2", "polarity": "must"}],
                   "with_results": {"checks": {"A1": True, "A2": True}},
                   "without_results": {"checks": {"A1": False, "A2": False}}}
            rp = os.path.join(td, "results.json"); json.dump(res, open(rp, "w"))
            out = os.path.join(td, "skills", "lw-synth", "lift_verdict.json")
            r = subprocess.run([sys.executable, os.path.join(ROOT, "lift_gate.py"), "score", rp, "--out", out],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)          # lift 1.0 >= 0.2 -> register -> exit 0
            self.assertEqual(json.load(open(out))["decision"], "register", "verdict written to --out path")

    def test_unmeasured_is_policy_warn_by_default(self):
        with tempfile.TemporaryDirectory() as td:
            self._skill_harness(td, verdict=None)
            self.assertEqual(self._codes(td).get("LIFT_UNMEASURED"), "warn",
                             "an authored-but-unmeasured skill defaults to a warning (policy knob)")

    def test_measured_and_refused_is_hard_error(self):
        with tempfile.TemporaryDirectory() as td:
            self._skill_harness(td, verdict={"decision": "refuse", "lift": 0.05, "threshold": 0.2})
            codes = self._codes(td)
            self.assertEqual(codes.get("LIFT_REFUSED"), "error",
                             "a measured skill that lost to the baseline must HARD-fail the build")
            self.assertNotIn("LIFT_UNMEASURED", codes, "a present verdict is not 'unmeasured'")

    def test_measured_and_registered_passes_lift(self):
        with tempfile.TemporaryDirectory() as td:
            self._skill_harness(td, verdict={"decision": "register", "lift": 0.4, "threshold": 0.2})
            codes = self._codes(td)
            self.assertNotIn("LIFT_REFUSED", codes, "a registered skill passes the lift gate")
            self.assertNotIn("LIFT_UNMEASURED", codes)

    def test_forged_register_verdict_refused(self):
        # audit: the gate must trust the MATH — a hand-written {"decision":"register"} with lift<threshold
        # (or non-numeric lift) must NOT pass LIFT_REFUSED.
        with tempfile.TemporaryDirectory() as td:
            self._skill_harness(td, verdict={"decision": "register", "lift": 0.01, "threshold": 0.2})
            self.assertEqual(self._codes(td).get("LIFT_REFUSED"), "error", "forged register (lift<thr) must fail")
        with tempfile.TemporaryDirectory() as td:
            self._skill_harness(td, verdict={"decision": "register", "lift": "bogus", "threshold": 0.2})
            self.assertEqual(self._codes(td).get("LIFT_REFUSED"), "error", "non-numeric lift must fail")

    def test_corrupt_or_nonobject_verdict_errors_not_crashes(self):
        # adversarial finding: a valid-JSON-but-non-object verdict ([]/"x"/123/true/null) or truncated JSON must
        # produce a clean LIFT_REFUSED, never crash validate on v.get()
        for raw in ("[]", "\"register\"", "123", "true", "null", "{ truncated ]"):
            with tempfile.TemporaryDirectory() as td:
                self._skill_harness(td, verdict=None)
                open(os.path.join(td, ".claude", "skills", "lw-synth", "lift_verdict.json"), "w").write(raw)
                codes = self._codes(td)   # must not raise
                self.assertEqual(codes.get("LIFT_REFUSED"), "error",
                                 "corrupt/non-object verdict %r must be a clean LIFT_REFUSED" % raw)


class TestH2HAggregate(unittest.TestCase):
    """P1.4: the aggregator tolerates a partially-failed suite — it DROPS invalid/flaky runs (never scores
    them 0, which would skew the median) and reports n_attempted / n_dropped honestly."""

    def test_drops_invalid_runs_not_zero(self):
        runs = [
            {"valid": True, "c2_pass_rate": 1.0, "c3_pass_rate": 0.8},
            {"valid": False, "reason": "missing grade after 3 attempts"},   # dropped (flake)
            {"c2_pass_rate": 1.0, "c3_pass_rate": 0.9},                      # legacy shape (no 'valid') -> kept
            {"c3_pass_rate": 0.5},                                           # missing c2 -> dropped
        ]
        out = h2h_aggregate.aggregate(runs, model_id=None, git_sha=None, harness_version=None)
        prov = out["provenance"]
        self.assertEqual(prov["n_attempted"], 4)
        self.assertEqual(prov["n_runs"], 2, "only valid runs are aggregated")
        self.assertEqual(prov["n_dropped"], 2)
        self.assertEqual(out["conditions"]["C2"]["median"], 1.0)
        self.assertEqual(out["conditions"]["C3"]["median"], 0.85, "median over the 2 VALID runs, not skewed by 0s")

    def test_all_invalid_raises_clearly(self):
        with self.assertRaises(ValueError):
            h2h_aggregate.aggregate([{"valid": False}, {"c3_pass_rate": 0.5}],
                                    model_id=None, git_sha=None, harness_version=None)


class TestEmittedHarnessDNAFires(unittest.TestCase):
    """P2: end-to-end proof that the inherited DNA actually FIRES on an EMITTED harness — the durable,
    CI-able equivalent of `cd <harness> && claude` (a nested interactive session can't be spawned here).
    Each settings.json-wired hook is run as a subprocess the way Claude Code invokes it (CLAUDE_PROJECT_DIR
    + real .harness/state.yaml), asserting the actual fire behavior: SOT seed -> spawn-count -> ceiling
    exit-2; QA L0 exit-2 on a missing deliverable; the genome security hook blocking rm -rf."""

    def _emit(self, td):
        g = {"schema_version": "0.1", "harness_name": "dnafire", "harness_version": "0.1.0",
             "execution_mode": "team", "topology": "pipeline",
             "budget": {"total_tokens": 1000, "approval_required": True},
             "nodes": [
                 {"id": "collect", "agent": "dnafire-collector", "model": "haiku", "decision_mechanism": "single",
                  "mechanism_params": {}, "inputs": [], "outputs": ["_workspace/c.json"],
                  "write_paths": ["_workspace/c/"], "output_schema": "schemas/c.json",
                  "retries": 1, "on_exhaust": "proceed-with-gap", "max_rounds": 1},
                 {"id": "synth", "agent": "dnafire-synth", "model": "opus", "decision_mechanism": "single",
                  "mechanism_params": {}, "inputs": [], "outputs": ["_workspace/s.json"],
                  "write_paths": ["_workspace/s/"], "output_schema": "schemas/s.json",
                  "review": {"agent": "reviewer"}, "retries": 0, "on_exhaust": "escalate", "max_rounds": 1}],
             "edges": [{"from": "collect", "to": "synth"}]}
        os.makedirs(os.path.join(td, ".harness")); os.makedirs(os.path.join(td, "schemas"))
        json.dump(g, open(os.path.join(td, ".harness", "graph.json"), "w"))
        for s in ("c", "s"):
            json.dump({"type": "object"}, open(os.path.join(td, "schemas", s + ".json"), "w"))
        self.assertEqual(emit_orchestrator.emit_orchestrator(g, td, in_project=False), [], "emit+genome must verify")
        return g

    def _drive(self, td, script, stdin=None):
        """Run a wired hook script as Claude Code does: CLAUDE_PROJECT_DIR=<harness> + optional event stdin."""
        import subprocess
        path = os.path.join(td, ".claude", "hooks", "scripts", script)
        env = dict(os.environ, CLAUDE_PROJECT_DIR=td)
        return subprocess.run([sys.executable, path], env=env, input=stdin, capture_output=True, text=True)

    def test_dna_fires_end_to_end(self):
        import re
        with tempfile.TemporaryDirectory() as td:
            self._emit(td)
            state = os.path.join(td, ".harness", "state.yaml")
            # the produced settings.json WIRES the DNA hooks (so a live session would invoke them)
            sj = json.dumps(json.load(open(os.path.join(td, ".claude", "settings.json")))["hooks"])
            for h in ("sot_init.py", "spawn_counter.py", "budget_block.py", "qa_gate_runner.py",
                      "block_destructive_commands.py", "context_guard.py"):
                self.assertIn(h, sj, "settings.json must wire %s" % h)

            # 1) SessionStart -> sot_init SEEDS the SOT with a real ceiling derived from the graph
            self.assertEqual(self._drive(td, "sot_init.py").returncode, 0)
            self.assertTrue(os.path.isfile(state), "sot_init must seed .harness/state.yaml")
            mx = int(re.search(r"max_spawns:\s*(\d+)", open(state).read()).group(1))
            self.assertGreaterEqual(mx, 2, "graph implies a real spawn ceiling")

            # 2) PreToolUse ceiling is SILENT while under budget (spawns_used=0)
            self.assertEqual(self._drive(td, "budget_block.py").returncode, 0, "ceiling must not false-block at 0")

            # 3) PostToolUse -> spawn_counter increments spawns_used BY CODE up to the ceiling
            for _ in range(mx):
                self.assertEqual(self._drive(td, "spawn_counter.py").returncode, 0)
            self.assertEqual(int(re.search(r"spawns_used:\s*(\d+)", open(state).read()).group(1)), mx,
                             "spawn_counter must increment spawns_used to the ceiling")

            # 4) PreToolUse -> budget_block now FIRES (exit 2): the spawn ceiling is a real interlock
            self.assertEqual(self._drive(td, "budget_block.py").returncode, 2, "spawn ceiling must fire exit-2")

            # 5) PostToolUse -> qa_gate_runner L0 BLOCKS a recorded-but-missing deliverable, passes a present one
            txt = open(state).read().replace("outputs: {}", "outputs:\n  step-1: _workspace/s1/out.md")
            open(state, "w").write(txt)
            self.assertEqual(self._drive(td, "qa_gate_runner.py").returncode, 2, "QA L0 must block a missing deliverable")
            os.makedirs(os.path.join(td, "_workspace", "s1"))
            open(os.path.join(td, "_workspace", "s1", "out.md"), "w").write("x" * 200)
            self.assertEqual(self._drive(td, "qa_gate_runner.py").returncode, 0, "QA L0 passes a present deliverable")

            # 6) the genome security hook FIRES on a destructive command, allows a benign one
            self.assertEqual(self._drive(td, "block_destructive_commands.py",
                                         stdin='{"tool_name":"Bash","tool_input":{"command":"rm -rf /"}}').returncode, 2)
            self.assertEqual(self._drive(td, "block_destructive_commands.py",
                                         stdin='{"tool_name":"Bash","tool_input":{"command":"ls -la"}}').returncode, 0)

            # 7) long-term memory store (Tier II) is seeded, and the orchestrator drives real team primitives
            for f in ("archive.manifest.json", "domain-knowledge.yaml", os.path.join("runs", "index.jsonl")):
                self.assertTrue(os.path.isfile(os.path.join(td, ".harness", "memory", f)), "Tier-II store: %s" % f)
            sk = open(os.path.join(td, ".claude", "skills", "dnafire-orchestrator", "SKILL.md"), encoding="utf-8").read()
            for p in ("TeamCreate(", "TaskCreate(", "SendMessage"):
                self.assertIn(p, sk, "orchestrator must drive the team primitive %s" % p)


class TestA2NotDefeatedByComment(unittest.TestCase):
    """P1-1 (audit): the A2 ALL_PRIMITIVES_PRESENT substring gate must strip HTML comments first — tokens
    hidden in a `<!-- ... -->` disclaimer must NOT satisfy the floor while the real calls are neutered."""

    def test_commented_primitives_do_not_satisfy_a2(self):
        g = {"schema_version": "0.1", "harness_name": "a2c", "harness_version": "0.1.0",
             "execution_mode": "team", "topology": "pipeline",
             "budget": {"total_tokens": 1000, "approval_required": True},
             "nodes": [{"id": "collect", "agent": "a2c-c", "model": "haiku", "decision_mechanism": "single",
                        "mechanism_params": {}, "inputs": [], "outputs": ["_workspace/c.json"],
                        "write_paths": ["_workspace/c/"], "output_schema": "schemas/c.json",
                        "retries": 1, "on_exhaust": "proceed-with-gap", "max_rounds": 1}], "edges": []}
        with tempfile.TemporaryDirectory() as td:
            os.makedirs(os.path.join(td, ".harness")); os.makedirs(os.path.join(td, "schemas"))
            json.dump(g, open(os.path.join(td, ".harness", "graph.json"), "w"))
            json.dump({"type": "object"}, open(os.path.join(td, "schemas", "c.json"), "w"))
            self.assertEqual(emit_orchestrator.emit_orchestrator(g, td, in_project=False), [])
            skp = os.path.join(td, ".claude", "skills", "a2c-orchestrator", "SKILL.md")
            body = open(skp, encoding="utf-8").read().replace("TeamCreate(", "TeamXreate(").replace("Agent(", "Agxnt(")
            body += "\n<!-- this orchestrator uses neither TeamCreate( nor Agent( -->\n"
            open(skp, "w", encoding="utf-8").write(body)
            codes = {i["code"] for i in validate_harness.validate(td).items if i["level"] == "error"}
            self.assertIn("ALL_PRIMITIVES_PRESENT", codes, "commented-out primitives must not satisfy A2")


class TestProducerReviewerReview(unittest.TestCase):
    """P1-2 (audit): a producer-reviewer harness must wire >=1 L2 review node (it exists to review)."""

    def _g(self, with_review):
        n = {"id": "make", "agent": "maker", "model": "opus", "decision_mechanism": "single",
             "mechanism_params": {}, "inputs": [], "outputs": ["_workspace/m.json"],
             "write_paths": ["_workspace/m/"], "output_schema": "schemas/m.json",
             "retries": 0, "on_exhaust": "escalate", "max_rounds": 1}
        if with_review:
            n["review"] = {"agent": "reviewer"}
        return {"schema_version": "0.1", "harness_name": "pr", "harness_version": "0.1.0",
                "execution_mode": "team", "topology": "producer-reviewer",
                "budget": {"total_tokens": 1000, "approval_required": True}, "nodes": [n], "edges": []}

    def _codes(self, g):
        with tempfile.TemporaryDirectory() as td:
            os.makedirs(os.path.join(td, ".harness")); os.makedirs(os.path.join(td, "schemas"))
            json.dump(g, open(os.path.join(td, ".harness", "graph.json"), "w"))
            json.dump({"type": "object"}, open(os.path.join(td, "schemas", "m.json"), "w"))
            return {i["code"] for i in validate_harness.validate(td).items if i["level"] == "error"}

    def test_producer_reviewer_without_review_fails(self):
        self.assertIn("PRODUCER_REVIEWER_REVIEW", self._codes(self._g(False)))

    def test_producer_reviewer_with_review_ok(self):
        self.assertNotIn("PRODUCER_REVIEWER_REVIEW", self._codes(self._g(True)))


class TestValidateRobustness(unittest.TestCase):
    """audit: the build gate must FAIL gracefully on adversarial input, not crash with a traceback."""

    def test_malformed_and_empty_graph_json_do_not_crash(self):
        for raw in ("{ not valid json ]", "", "[]", "null", "42"):
            with tempfile.TemporaryDirectory() as td:
                os.makedirs(os.path.join(td, ".harness"))
                open(os.path.join(td, ".harness", "graph.json"), "w").write(raw)
                rep = validate_harness.validate(td)   # must not raise
                errs = [i for i in rep.items if i["level"] == "error"]
                self.assertTrue(any(e["code"] == "GRAPH_SCHEMA" or e["code"] == "GRAPH_MISSING" for e in errs),
                                "malformed graph.json %r must produce a clean GRAPH_SCHEMA error" % raw)


class TestPromptRunnerAbsent(unittest.TestCase):
    """P0-3 (audit): a produced harness must NOT physically ship the prompt-runner `claude -p` subprocess
    executor or its slash commands (a latent non-primitive execution path) — A1. The self-contained pour now
    excludes them (mirroring in-project), and validate has a FILESYSTEM check symmetric to the workflow.js one."""

    def _emit(self, td):
        g = {"schema_version": "0.1", "harness_name": "prx", "harness_version": "0.1.0",
             "execution_mode": "team", "topology": "pipeline",
             "budget": {"total_tokens": 1000, "approval_required": True},
             "nodes": [{"id": "collect", "agent": "prx-c", "model": "haiku", "decision_mechanism": "single",
                        "mechanism_params": {}, "inputs": [], "outputs": ["_workspace/c.json"],
                        "write_paths": ["_workspace/c/"], "output_schema": "schemas/c.json",
                        "retries": 1, "on_exhaust": "proceed-with-gap", "max_rounds": 1}],
             "edges": []}
        os.makedirs(os.path.join(td, ".harness")); os.makedirs(os.path.join(td, "schemas"))
        json.dump(g, open(os.path.join(td, ".harness", "graph.json"), "w"))
        json.dump({"type": "object"}, open(os.path.join(td, "schemas", "c.json"), "w"))
        self.assertEqual(emit_orchestrator.emit_orchestrator(g, td, in_project=False), [])

    def test_self_contained_does_not_ship_prompt_runner(self):
        with tempfile.TemporaryDirectory() as td:
            self._emit(td)
            self.assertFalse(os.path.exists(os.path.join(td, "prompt-runner")), "no prompt-runner/ in a produced harness")
            self.assertFalse(os.path.exists(os.path.join(td, "prompt")), "no prompt/ samples")
            cmds = os.path.join(td, ".claude", "commands")
            if os.path.isdir(cmds):
                self.assertEqual([f for f in os.listdir(cmds) if "prompt" in f.lower()], [],
                                 "no prompt-runner-coupled slash commands")
            self.assertEqual([i for i in validate_harness.validate(td).items if i["level"] == "error"], [],
                             "clean self-contained harness validates 0 errors")

    def test_planted_prompt_runner_fails_validate(self):
        with tempfile.TemporaryDirectory() as td:
            self._emit(td)
            os.makedirs(os.path.join(td, "prompt-runner"))
            open(os.path.join(td, "prompt-runner", "run.py"), "w").write("# claude -p executor\n")
            codes = {i["code"] for i in validate_harness.validate(td).items if i["level"] == "error"}
            self.assertIn("PROMPT_RUNNER_ABSENT", codes, "a physically-shipped prompt-runner must fail validate")


class TestSotPathReconciled(unittest.TestCase):
    """P0-1 (audit BLOCKER): the genome's Context-Preservation SOT reader must resolve CYS's
    .harness/state.yaml — sot_init/budget_block/spawn_counter/emit all write there, but the genome
    sot_paths() historically resolved only .claude/, so every Tier-I snapshot silently dropped the SOT
    (current_step/budget/outputs). Lock the .harness-first resolution + the .claude fallback."""

    def _lib(self):
        import importlib.util
        p = os.path.join(ROOT, "genome", ".claude", "hooks", "scripts", "_context_lib.py")
        sys.path.insert(0, os.path.dirname(p))
        spec = importlib.util.spec_from_file_location("_context_lib_p0", p)
        m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
        return m

    def _content(self, sot):
        return sot.get("content", "") if isinstance(sot, dict) else str(sot)

    def test_harness_sot_is_seen_by_context_preservation(self):
        cl = self._lib()
        with tempfile.TemporaryDirectory() as td:
            os.makedirs(os.path.join(td, ".harness"))
            open(os.path.join(td, ".harness", "state.yaml"), "w").write(
                "workflow:\n  current_step: 3\noutputs:\n  step-1: x.md\nbudget:\n  spawns_used: 2\n  max_spawns: 8\n")
            self.assertEqual(cl.sot_paths(td)[0], os.path.join(td, ".harness", "state.yaml"),
                             ".harness/ SOT must resolve FIRST (CYS convention)")
            c = self._content(cl.capture_sot(td))
            self.assertIn("current_step: 3", c, "Tier-I snapshot must capture the .harness SOT payload")
            self.assertIn("max_spawns: 8", c)

    def test_claude_sot_still_resolves_as_fallback(self):
        cl = self._lib()
        with tempfile.TemporaryDirectory() as td:
            os.makedirs(os.path.join(td, ".claude"))
            open(os.path.join(td, ".claude", "state.yaml"), "w").write("workflow:\n  current_step: 9\n")
            self.assertIn("current_step: 9", self._content(cl.capture_sot(td)), "plain-AWF .claude SOT must still resolve")


if __name__ == "__main__":
    unittest.main(verbosity=2)
