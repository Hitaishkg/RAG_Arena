.PHONY: serve test ingest build-indexes eval safety

serve:
	uvicorn src.api.main:app --host 0.0.0.0 --port 8000

test:
	pytest tests/ -v

ingest:
	python scripts/ingest.py

build-indexes:
	python scripts/build_indexes.py

eval:
	python scripts/run_eval.py

safety:
	python scripts/safety_test.py
