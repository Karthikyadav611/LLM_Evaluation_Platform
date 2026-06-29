# LLM Eval CI/CD

A lightweight, self-hosted, multi-provider LLM regression-testing and evaluation platform for developers and small teams.

The project compares prompts and models against golden datasets, scores deterministic and judge-based metrics, writes CI-friendly reports, exposes a Streamlit dashboard, and can block deployments through configurable quality gates.

## How It Fits

- **Promptfoo** is broader for prompt test scripting; this project focuses on a small Python-first regression harness with reports, dashboard, SQLite history, and CI gates.
- **LangSmith** and **Braintrust** provide hosted observability and evaluation platforms; this project is self-hosted and intentionally lightweight.
- **Phoenix** is strong for tracing and observability; this project centers on repeatable prompt/model regression tests and deployment gates.

It is not an enterprise evaluation suite. There is no billing, RBAC, Kubernetes orchestration, or distributed queue.

## Architecture

```text
app/
  providers/      Groq, Gemini, OpenAI, Anthropic provider adapters
  datasets/       JSON/CSV loading, validation, summaries, draft generation helpers
  prompts/        prompt loading and hashing
  evaluators/     deterministic evaluator registry and LLM judge bridge
  experiments/    prompt comparison, model comparison, matrix expansion, summaries
  storage/        SQLite persistence via SQLAlchemy
  reports/        CSV/JSON/ZIP helpers
dashboard/        Streamlit multi-page dashboard
scripts/          CLI entry points and offline validation
tests/            offline unit tests with fake providers
```

## Supported Providers

Generation and judge providers are configured independently:

- `groq` via `groq`
- `gemini` via `google-genai`
- `openai` via `openai`
- `anthropic` via `anthropic`

Environment variables:

```bash
GROQ_API_KEY=
GEMINI_API_KEY=
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
```

Dashboard API keys are password fields and remain in Streamlit session memory only. They are not written to reports, logs, databases, URLs, caches, or ZIP files.

## Evaluation Modes

- **Prompt comparison:** baseline prompt versus candidate prompt on the same dataset and model.
- **Model comparison:** multiple models on the same prompt and dataset.
- **Prompt-model matrix:** every selected prompt/model combination.

The judge is called exactly once for each successful generation. Generation failures and judge failures become `ERROR` rows and do not count as hallucinations, unsafe outputs, or fast latency.

## Dataset Format

JSON and CSV datasets support:

```text
id, category, difficulty, question, context, expected_answer,
must_include, must_not_include, expected_behavior, metadata
```

Allowed `expected_behavior` values are `answer`, `unanswerable`, `clarify`, and `refuse`.

Uploaded dashboard datasets are temporary unless you explicitly save them in your self-hosted environment. Generated datasets are labeled as drafts requiring human review.

## Metrics And Gates

Metrics include keyword checks, forbidden-term checks, expected-behavior checks, semantic similarity, relevancy, faithfulness, correctness, safety, hallucination, latency, token counts, and optional estimated cost.

Quality gates cover pass rate, correctness, relevancy, faithfulness, safety pass rate, hallucination rate, P95 latency, average cost when configured, generation errors, judge errors, valid evaluation ratio, and regressions.

Pipeline exit codes:

- `0` = `PASS`
- `1` = `FAIL`
- `2` = `ERROR`

## Local Setup

```bash
pip install -r requirements-dev.txt
cp .env.example .env
python scripts/validate_project.py
pytest -q
ruff check .
```

Run prompt comparison:

```bash
python -m scripts.run_evaluation --test-limit 3
```

Run a matrix experiment:

```bash
python -m scripts.run_matrix --config experiment.yaml
```

Run the dashboard:

```bash
streamlit run dashboard/streamlit_app.py
```

## Reports

Reports are written to `reports/`:

- `experiment_summary.json`
- `configuration_results.csv`
- `test_results.csv`
- `model_comparison.csv`
- `prompt_comparison.csv`
- `quality_gates.csv`
- `failed_tests.csv`
- `regressed_tests.csv`
- `fixed_tests.csv`

Backward-compatible files are also retained:

- `evaluation_summary.json`
- `baseline_evaluation_results.csv`
- `candidate_evaluation_results.csv`
- `failed_candidate_tests.csv`
- `test_level_comparison.csv`

Dashboard report ZIP downloads are created in memory with `io.BytesIO`. Report ZIP upload is only for viewing previous evaluation reports, not source-code project archives, and extraction is protected against path traversal.

## Experiment History

SQLite is the default persistence layer through SQLAlchemy. Configure another database later with:

```bash
DATABASE_URL=sqlite:///./data/llm_eval.db
```

The schema stores experiments, configurations, results, metric summaries, quality gates, and report file metadata. API keys are never stored.

## CI/CD

`.github/workflows/test.yml` runs compile, validation, tests, Ruff, and MyPy without real API keys.

`.github/workflows/llm-evaluation.yml` runs the same offline checks and then a small live smoke evaluation using repository secrets. Reports are uploaded even when the evaluation returns `FAIL`.

## Docker

```bash
docker compose up --build
```

The image uses `python:3.11-slim`, runs Streamlit as a non-root user, supports runtime environment variables, exposes a health check, and mounts named volumes for SQLite data and reports.

## Security Notes

- `.env` is ignored; `.env.example` is committed.
- Secret-like errors are sanitized before display.
- Provider clients are not cached with API keys.
- Reports and ZIPs exclude API keys.
- Live generated reports and database files are excluded from source archives.
- Pricing is optional local configuration; unknown cost remains `None`, never zero.

## Limitations

- Provider adapters are unit-tested with fake SDK clients; live verification depends on your own API keys.
- SQLite is intended for local and small-team deployments.
- Pricing data must be supplied locally if you want cost estimates.
- External hosting and production hardening are deployment responsibilities.

## Resume-Ready Description

Built a self-hosted multi-provider LLM evaluation platform with Python, Streamlit, SQLAlchemy, Docker, and GitHub Actions. Implemented prompt/model matrix experiments, deterministic and LLM-judge metrics, secure temporary API-key handling, report ZIP generation, SQLite experiment history, quality gates, and CI/CD deployment blocking.
