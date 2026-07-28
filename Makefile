.PHONY: run scan ingest test help

run:
	@./run.sh run-cycle

scan:
	@./run.sh scan

ingest:
	@./run.sh ingest

test:
	@.venv/bin/pytest

help:
	@./run.sh --help
