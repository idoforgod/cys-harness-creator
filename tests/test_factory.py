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

    def test_memory_operating_cycle_first_class(self):
        # M1: long-term memory must be a declared operating cycle in every orchestrator (CONTEXT_
        # PRESERVATION_FIRSTCLASS) — not the old 1-line gap.
        g = self._graph()
        skill = emit_orchestrator._orchestrator_skill(g, toposort(g["nodes"], g["edges"]))
        for marker in ("메모리 운영", "knowledge-index", "latest.md", "CONTEXT RECOVERY"):
            self.assertIn(marker, skill, "orchestrator must declare memory operating cycle: %s" % marker)

    def test_tools_respects_node_then_role_class(self):
        g = self._graph()
        self.assertEqual(emit_orchestrator._tools_for(g["nodes"][0]), "Read, WebSearch")  # explicit
        synth = dict(g["nodes"][1]); synth.pop("tools", None)
        self.assertIn("Write", emit_orchestrator._tools_for(synth))  # synthesis role-class default

    def test_runtime_manifest_canonical_is_orchestrator(self):
        rm = emit_orchestrator._runtime_manifest(self._graph())
        self.assertEqual(rm["canonical_runtime"], "demo-orchestrator")
        self.assertIn("launch", rm["runtimes"][0], "must record the session-launch handoff (R4)")


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


if __name__ == "__main__":
    unittest.main(verbosity=2)
