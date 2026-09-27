PY ?= python3
GJ = $(PY) scripts/gj.py

.PHONY: install validate test eval-selfcheck release export check audit leakage gates review-verify

install:            ## core + test dependencies
	$(PY) -m pip install -r requirements.txt

validate:           ## schemas, semantic lint, contrastive self-test, scenarios, eval cases
	$(GJ) validate

test:
	$(PY) -m pytest -q

eval-selfcheck:     ## reference must pass everything; naive baseline shows the checks discriminate
	$(GJ) eval run --predictor reference
	$(GJ) eval run --predictor naive

release:            ## immutable train/validation/test release for configs/versions.yaml
	$(GJ) split

export:             ## training formats are refused until `gj gates` passes (see --allow-draft)
	$(GJ) export --format sft
	$(GJ) export --format preference
	$(GJ) export --format eval

audit:              ## heuristic audits (Problems 1-9) + known issues -> review/audit_findings_v<ver>.json
	$(GJ) audit --write

leakage:            ## layered leakage report (fails on hard findings)
	$(GJ) leakage --distribution

gates:              ## is the release training_ready? (fails until every gate passes)
	$(GJ) gates

review-verify:      ## review log intact (hash chain + snapshots)
	$(GJ) review verify-log

check: validate test eval-selfcheck leakage review-verify
