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
import warrant                  # noqa: E402
import lift_gate                # noqa: E402
import validate_harness         # noqa: E402
from toposort import toposort, CycleError  # noqa: E402

GOLDEN = os.path.join(os.path.dirname(__file__), "golden")
CORE_EXAMPLES = ["deep-research", "ticket-triage", "design-decision"]


class TestEmitDeterminism(unittest.TestCase):
    """The single verified-valuable property: same graph.json -> byte-identical workflow.js."""

    def test_emit_byte_identical_to_golden(self):
        for ex in CORE_EXAMPLES:
            hd = os.path.join(ROOT, "examples", ex)
            graph = emit_workflow._load(os.path.join(hd, ".harness", "graph.json"))
            js = emit_workflow.emit(graph, hd)
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
