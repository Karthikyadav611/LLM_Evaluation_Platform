.PHONY: install install-dev validate test lint typecheck evaluate matrix dashboard docker-build docker-run clean

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt

validate:
	python scripts/validate_project.py

test:
	pytest -q

lint:
	ruff check .

typecheck:
	mypy app scripts dashboard

evaluate:
	python -m scripts.run_evaluation --test-limit 3

matrix:
	python -m scripts.run_matrix --config experiment.yaml

dashboard:
	streamlit run dashboard/streamlit_app.py

docker-build:
	docker build -t llm-eval-cicd .

docker-run:
	docker run --rm -p 8501:8501 --env-file .env -v "$$(pwd)/reports:/app/reports" llm-eval-cicd

clean:
	python -c "import pathlib, shutil; [shutil.rmtree(path, ignore_errors=True) for path in pathlib.Path('.').rglob('__pycache__')]; [path.unlink() for pattern in ('reports/*.csv', 'reports/*.json', 'reports/*.zip') for path in pathlib.Path('.').glob(pattern)]"
