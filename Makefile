# ProvenanceBench — quick commands. The demo needs no install and no API key.
PY ?= python3

.PHONY: help demo contrast test

help:
	@echo "make demo      - run the offline baselines on the 72-case seed set (no install, no API key)"
	@echo "make contrast  - show RAGAS faithfulness=NaN vs ProvenanceBench=pass on correct refusals"
	@echo "make test      - validate the evalset (every gold label traceable) via pytest"

demo:
	@$(PY) scripts/run_baselines.py

contrast:
	@$(PY) scripts/ragas_contrast.py

test:
	@$(PY) -m pytest -q
