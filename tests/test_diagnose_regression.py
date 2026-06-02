#!/usr/bin/env python3
"""Regression tests for the 2026-06-02 latent-defect audit (/diagnose).

Each test pins a defect that the 134-test factory suite did NOT catch, confirmed by
independent reproduction. Written BEFORE the fix (they fail on the pre-fix tree), so they
lock the fix in. Kept in a separate file so `pytest tests/test_factory.py` stays at 134;
`make test` (unittest discover) runs these too.

Defects:
  A  role-class substring/order misclassification  (role-class-policy.json + validate_harness)
  B  MEASUREMENT_DRIFT swallows all-corrupt verdicts (validate_harness._measurement_drift)
  C  re-emit preserves stale model_rationale/tools   (emit_orchestrator._write_agent_files)
  D  non-UTF8 locale crash in validate/emit           (open() without encoding=)
  E  h2h double-rounding boundary flip                (h2h_aggregate.aggregate)
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "lib"))

import emit_orchestrator        # noqa: E402
import h2h_aggregate            # noqa: E402
import validate_harness         # noqa: E402


def _rc(idv, agentv, mech="single"):
    return validate_harness._role_class_of(
        {"id": idv, "agent": agentv, "decision_mechanism": mech})


class TestRoleClassCollision(unittest.TestCase):
    """A — a retrieval/format substring must not shadow a high-reasoning node's true class."""

    def test_research_is_not_search(self):
        # 'research' embeds 'search' but is NOT a retrieval action — must not resolve to gather(haiku).
        self.assertNotEqual(_rc("research_report", "researchreport"), "gather")
        self.assertNotEqual(_rc("research", "researcher_node"), "gather")

    def test_research_report_defaults_to_synthesis(self):
        self.assertEqual(_rc("research_report", "researchreport"), "synthesis")

    def test_report_critic_is_a_critic(self):
        # an explicit 'critic' token must win — 'report' must not pin it to format(haiku).
        self.assertEqual(_rc("report_critic", "reportcritic"), "critic")

    def test_real_search_still_gathers(self):
        # word-boundary fix must not break a genuine search node.
        self.assertEqual(_rc("web_search", "searcher"), "gather")
        self.assertEqual(_rc("gather", "researcher"), "gather")  # pins the existing factory test

    def test_legit_format_unchanged(self):
        # writer/render/publish remain format; only the ambiguous bare 'report' moved.
        self.assertEqual(_rc("report_writer", "writer"), "format")
        self.assertEqual(_rc("render_page", "renderer"), "format")

    def test_examples_classification_unchanged(self):
        # the 4 shipped examples must classify identically after the fix (regression net).
        import glob
        expected = {
            "competitor-watch": {"gather": "gather", "dedupe": "synthesis", "brief": "synthesis"},
            "deep-research": {"gather": "gather", "fetch": "gather", "verify": "reviser",
                              "synthesize": "synthesis"},
            "design-decision": {"propose": "synthesis", "adjudicate": "debater"},
            "ticket-triage": {"classify_category": "voter", "classify_priority": "voter",
                              "route": "synthesis"},
        }
        for gp in glob.glob(os.path.join(ROOT, "examples", "*", ".harness", "graph.json")):
            name = gp.split(os.sep)[-3]
            if name not in expected:
                continue
            g = json.load(open(gp, encoding="utf-8"))
            for n in g["nodes"]:
                self.assertEqual(validate_harness._role_class_of(n), expected[name][n["id"]],
                                 "%s/%s role-class drifted" % (name, n["id"]))


class TestMeasurementDriftCorruptVerdict(unittest.TestCase):
    """B — all-corrupt verdict files must NOT let a 'CYS-WINS' doc claim pass as if unmeasured."""

    def _setup(self, verdict_files):
        td = tempfile.mkdtemp(prefix="chc-drift-")
        os.makedirs(os.path.join(td, "evals"))
        for fn, content in verdict_files.items():
            open(os.path.join(td, "evals", fn), "w", encoding="utf-8").write(content)
        open(os.path.join(td, "README.md"), "w", encoding="utf-8").write("# x\nCYS-WINS 우세\n")
        return td

    def _drift(self, td):
        r = validate_harness.Report()
        validate_harness._measurement_drift(td, r, False)
        return [i for i in r.items if i["code"] == "MEASUREMENT_DRIFT"]

    def test_all_corrupt_verdicts_block_win_claim(self):
        td = self._setup({"a.verdict.json": "NOT JSON {", "b.verdict.json": "{trunc"})
        self.assertTrue(self._drift(td), "corrupt verdicts must not silently pass a CYS-WINS claim")
        shutil.rmtree(td)

    def test_no_verdict_files_is_allowed(self):
        td = tempfile.mkdtemp(prefix="chc-drift-")
        open(os.path.join(td, "README.md"), "w", encoding="utf-8").write("CYS-WINS\n")
        self.assertFalse(self._drift(td), "no evals dir at all -> nothing to police")
        shutil.rmtree(td)

    def test_genuine_win_allowed(self):
        td = self._setup({"a.verdict.json": '{"verdict":"CYS-WINS"}'})
        self.assertFalse(self._drift(td), "a real CYS-WINS verdict may be advertised")
        shutil.rmtree(td)

    def test_loser_verdict_blocks(self):  # control: already-correct path stays correct
        td = self._setup({"a.verdict.json": '{"verdict":"BASELINE-WINS"}'})
        self.assertTrue(self._drift(td))
        shutil.rmtree(td)


class TestReEmitReStampsPolicyFields(unittest.TestCase):
    """C — re-emit must re-derive model_rationale + tools from the graph (not preserve stale)."""

    def _graph(self, model, tools):
        return {"schema_version": "0.1", "harness_name": "demo", "harness_version": "0.1.0",
                "execution_mode": "agent", "topology": "pipeline",
                "nodes": [{"id": "gather", "agent": "researcher", "model": model,
                           "decision_mechanism": "single", "mechanism_params": {},
                           "inputs": [], "outputs": ["_workspace/g.json"],
                           "write_paths": ["_workspace/g/"], "output_schema": "schemas/g.json",
                           "tools": tools, "retries": 1, "on_exhaust": "proceed-with-gap",
                           "max_rounds": 1, "tier_override_reason": "test override"}],
                "edges": []}

    def _fm(self, td, key):
        p = os.path.join(td, ".claude", "agents", "researcher.md")
        block = open(p, encoding="utf-8").read().split("---")[1]
        m = re.search(r"^%s:\s*(.+)$" % key, block, re.M)
        return m.group(1).strip() if m else ""

    def test_reemit_updates_tools_and_rationale(self):
        td = tempfile.mkdtemp(prefix="chc-emit-")
        emit_orchestrator._write_agent_files(self._graph("haiku", ["Read"]), td)
        self.assertEqual(self._fm(td, "model"), "haiku")
        # mutate the contract: widen model + tools, re-emit
        emit_orchestrator._write_agent_files(
            self._graph("opus", ["Read", "WebSearch", "Bash"]), td)
        self.assertEqual(self._fm(td, "model"), "opus", "model must re-stamp (baseline)")
        self.assertIn("Bash", self._fm(td, "tools"),
                      "tools allowlist must re-derive from the new graph (least-priv)")
        self.assertNotIn("policy tier haiku", self._fm(td, "model_rationale"),
                         "rationale must not keep asserting the stale haiku tier for an opus node")
        shutil.rmtree(td)


class TestUtf8LocaleRobust(unittest.TestCase):
    """D — validate must not crash on Korean-prose artifacts under a non-UTF8 locale."""

    def test_validate_under_c_locale(self):
        env = dict(os.environ)
        env.update({"LC_ALL": "C", "LANG": "C", "PYTHONUTF8": "0", "PYTHONIOENCODING": "utf-8"})
        ex = os.path.join(ROOT, "examples", "deep-research")
        p = subprocess.run([sys.executable, os.path.join(ROOT, "validate_harness.py"), ex],
                           capture_output=True, text=True, env=env)
        self.assertNotIn("UnicodeDecodeError", p.stderr,
                         "factory tools must read their own UTF-8 artifacts under any locale")
        self.assertEqual(p.returncode, 0, "deep-research must still validate clean under C locale")


class TestH2HBoundaryNoDoubleRound(unittest.TestCase):
    """E — the verdict must come from the raw median delta, not a display-rounded one."""

    def _verdict(self, c2, c3):
        return h2h_aggregate.aggregate([{"c2_pass_rate": c2, "c3_pass_rate": c3}],
                                       model_id="m", git_sha="x", harness_version="v")["verdict"]

    def test_sub_margin_boundary_is_inconclusive(self):
        # true delta 14.995pp (< 15) must NOT be reported as a win via median rounding to 0.65.
        self.assertEqual(self._verdict(0.64995, 0.5), "INCONCLUSIVE")

    def test_exact_margin_wins(self):  # documented >= rule preserved
        self.assertEqual(self._verdict(0.65, 0.5), "CYS-WINS")

    def test_clear_win_unchanged(self):
        self.assertEqual(self._verdict(0.875, 0.5), "CYS-WINS")

    def test_clear_baseline_win_unchanged(self):
        self.assertEqual(self._verdict(0.5, 0.875), "BASELINE-WINS")


import importlib.util  # noqa: E402


def _load_hook(name):
    p = os.path.join(ROOT, "templates", "hooks", name + ".py")
    spec = importlib.util.spec_from_file_location(name, p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestCycleGateAllTopologies(unittest.TestCase):
    """#7 — validate must catch an accidental cycle in EVERY topology except producer-reviewer
    (whose back-edge is intentional per qa-guide), so the gate matches emit's unconditional toposort."""

    def _graph(self, topology, edges):
        def node(i):
            return {"id": "n%d" % i, "agent": "ag%d" % i, "model": "opus" if i == 1 else "sonnet",
                    "decision_mechanism": "single", "mechanism_params": {}, "inputs": [],
                    "outputs": ["_workspace/n%d.json" % i], "write_paths": ["_workspace/n%d/" % i],
                    "output_schema": "schemas/n%d.json" % i, "retries": 0,
                    "on_exhaust": "escalate", "max_rounds": 1}
        return {"schema_version": "0.1", "harness_name": "cyc-demo", "harness_version": "0.1.0",
                "execution_mode": "team", "topology": topology,
                "budget": {"total_tokens": 1000, "approval_required": True},
                "nodes": [node(1), node(2), node(3)], "edges": edges}

    def _codes(self, graph):
        td = tempfile.mkdtemp(prefix="chc-cyc-")
        os.makedirs(os.path.join(td, ".harness"))
        json.dump(graph, open(os.path.join(td, ".harness", "graph.json"), "w", encoding="utf-8"))
        r = validate_harness.validate(td)
        shutil.rmtree(td)
        return {i["code"] for i in r.items}

    def test_hierarchical_cycle_is_caught(self):
        cyc = [{"from": "n1", "to": "n2"}, {"from": "n2", "to": "n3"}, {"from": "n3", "to": "n1"}]
        self.assertIn("GRAPH_CYCLE", self._codes(self._graph("hierarchical", cyc)))

    def test_supervisor_cycle_is_caught(self):
        cyc = [{"from": "n1", "to": "n2"}, {"from": "n2", "to": "n1"}]
        self.assertIn("GRAPH_CYCLE", self._codes(self._graph("supervisor", cyc)))

    def test_producer_reviewer_backedge_exempt(self):
        # the reviewer->producer back-edge is intentional (qa-guide §6-2) — must NOT be flagged.
        cyc = [{"from": "n1", "to": "n2"}, {"from": "n2", "to": "n1"}]
        self.assertNotIn("GRAPH_CYCLE", self._codes(self._graph("producer-reviewer", cyc)))

    def test_acyclic_hierarchical_passes_cycle_check(self):
        dag = [{"from": "n1", "to": "n2"}, {"from": "n1", "to": "n3"}]
        self.assertNotIn("GRAPH_CYCLE", self._codes(self._graph("hierarchical", dag)))


class TestSpawnCounterTeamMembers(unittest.TestCase):
    """#8 — a TeamCreate spawns N members; spawn_counter must increment by N, not 1, so the
    budget ceiling reflects the real spawn count (emit prose: 'spawns_used += 멤버수')."""

    def setUp(self):
        self.sc = _load_hook("spawn_counter")

    def test_increment_counts_team_members(self):
        n = self.sc._spawn_increment({"tool_name": "TeamCreate",
                                      "tool_input": {"members": ["a", "b", "c", "d", "e"]}})
        self.assertEqual(n, 5)

    def test_increment_single_for_agent(self):
        self.assertEqual(self.sc._spawn_increment({"tool_name": "Agent", "tool_input": {}}), 1)

    def test_increment_floor_one_on_garbage(self):
        self.assertEqual(self.sc._spawn_increment({}), 1)
        self.assertEqual(self.sc._spawn_increment({"tool_name": "TeamCreate", "tool_input": {}}), 1)

    def test_bump_by_n(self):
        text = "budget:\n  spawns_used: 7\n  max_spawns: 20\n"
        new_text, val = self.sc.bump(text, by=3)
        self.assertEqual(val, 10)
        self.assertIn("spawns_used: 10", new_text)


class TestQaGateOutOfOrder(unittest.TestCase):
    """#9 — a step recorded out of order must still be gated, not permanently skipped."""

    def setUp(self):
        self.qgr = _load_hook("qa_gate_runner")

    def test_out_of_order_step_not_skipped(self):
        # step-3 gated first; steps 1,2 recorded later -> the lowest UNGATED (1) must be returned.
        self.assertEqual(self.qgr.next_step_to_gate({1, 2, 3}, {3}), 1)

    def test_gates_lowest_ungated(self):
        self.assertEqual(self.qgr.next_step_to_gate({1, 2, 3}, set()), 1)
        self.assertEqual(self.qgr.next_step_to_gate({1, 2, 3}, {1}), 2)
        self.assertIsNone(self.qgr.next_step_to_gate({1, 2, 3}, {1, 2, 3}))
        self.assertEqual(self.qgr.next_step_to_gate({2, 5}, {2}), 5)


class TestEmitPathSafety(unittest.TestCase):
    """#10 — emit (which precedes validate) must refuse a path-unsafe node id/agent rather than
    writing files outside the intended agents/ dir."""

    def _graph(self, idv, agentv):
        return {"schema_version": "0.1", "harness_name": "esc", "harness_version": "0.1.0",
                "execution_mode": "agent", "topology": "pipeline",
                "budget": {"total_tokens": 100, "approval_required": True},
                "nodes": [{"id": idv, "agent": agentv, "model": "haiku",
                           "decision_mechanism": "single", "mechanism_params": {}, "inputs": [],
                           "outputs": ["_workspace/x.json"], "write_paths": ["_workspace/x/"],
                           "output_schema": "schemas/x.json", "retries": 0,
                           "on_exhaust": "proceed-with-gap", "max_rounds": 1}],
                "edges": []}

    def test_rejects_traversal_agent(self):
        with self.assertRaises(SystemExit):
            emit_orchestrator._require_valid_graph(self._graph("n1", "../../escaped"))

    def test_rejects_traversal_id(self):
        with self.assertRaises(SystemExit):
            emit_orchestrator._require_valid_graph(self._graph("../evil", "agent1"))

    def test_accepts_clean_names(self):
        emit_orchestrator._require_valid_graph(self._graph("gather", "researcher"))  # no raise


if __name__ == "__main__":
    unittest.main()
