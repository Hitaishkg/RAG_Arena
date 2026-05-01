ingest:
	python scripts/ingest.py

build-indexes:
	python scripts/build_indexes.py

eval:
	python scripts/run_eval.py

dashboard:
	streamlit run src/dashboard/app.py

test:
	pytest tests/ -v

findings:
	python scripts/export_findings.py
