PY ?= python3
GJ = $(PY) scripts/gj.py

.PHONY: install validate test eval-selfcheck release export check

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

export:
	$(GJ) export --format sft
	$(GJ) export --format preference
	$(GJ) export --format eval

check: validate test eval-selfcheck
