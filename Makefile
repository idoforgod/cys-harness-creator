.PHONY: test eval
test:  ## factory self-test (pure, no genome, no live runs)
	python3 -m unittest discover -s tests -p 'test_*.py' -v
eval:  ## (P0-2) run literal workflow.js head-to-head + stamp evidence  [placeholder until P0-2]
	@echo "P0-2: run examples/deep-research/.harness/workflow.js + h2h_aggregate stamp"
