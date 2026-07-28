.PHONY: run scan ingest test docker-build docker-run help

run:
	@./run.sh run-cycle

scan:
	@./run.sh scan

ingest:
	@./run.sh ingest

test:
	@.venv/bin/pytest

docker-build:
	docker build -t burn-job:latest .

docker-run:
	docker run --rm -v $(shell pwd):/app burn-job:latest run-cycle

help:
	@./run.sh --help
