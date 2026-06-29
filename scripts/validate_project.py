import re
import sys
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import Settings
from app.dataset_loader import load_golden_dataset
from app.prompt_manager import PromptManager

REQUIRED_FILES = [
    "app/__init__.py",
    "app/config.py",
    "app/constants.py",
    "app/security.py",
    "app/schemas.py",
    "app/dataset_loader.py",
    "app/providers/base.py",
    "app/providers/factory.py",
    "app/prompt_manager.py",
    "app/evaluators/__init__.py",
    "app/judge.py",
    "app/evaluation_runner.py",
    "app/metrics.py",
    "app/comparison.py",
    "app/quality_gate.py",
    "app/report_generator.py",
    "app/reports/persistence.py",
    "dashboard/__init__.py",
    "dashboard/streamlit_app.py",
    "dashboard/pages/1_Run_Evaluation.py",
    "dashboard/pages/2_Model_Comparison.py",
    "dashboard/pages/3_Experiment_History.py",
    "dashboard/pages/4_Report_Viewer.py",
    "dashboard/pages/5_Settings.py",
    "data/golden_dataset.json",
    "data/sample_dataset.json",
    "prompts/baseline_prompt.txt",
    "prompts/candidate_prompt.txt",
    "prompts/judge_prompt.txt",
    "reports/.gitkeep",
    "scripts/run_evaluation.py",
    "scripts/run_matrix.py",
    "scripts/show_latest_report.py",
    ".github/workflows/llm-evaluation.yml",
    ".github/workflows/test.yml",
    ".streamlit/config.toml",
    ".env.example",
    ".gitignore",
    "Dockerfile",
    "docker-compose.yml",
    "Makefile",
    "requirements.txt",
    "requirements-dev.txt",
    "pyproject.toml",
    "README.md",
    "LICENSE",
]
EXPECTED_ENV_KEYS = {
    "GROQ_API_KEY",
    "GEMINI_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GENERATION_PROVIDER",
    "GENERATION_MODEL",
    "JUDGE_PROVIDER",
    "JUDGE_MODEL",
    "TEMPERATURE",
    "MAX_OUTPUT_TOKENS",
    "REQUEST_DELAY_SECONDS",
    "MAX_RETRIES",
    "TEST_LIMIT",
    "MINIMUM_PASS_RATE",
    "MINIMUM_CORRECTNESS",
    "MINIMUM_RELEVANCY",
    "MINIMUM_FAITHFULNESS",
    "MINIMUM_SAFETY_PASS_RATE",
    "MAXIMUM_HALLUCINATION_RATE",
    "MAXIMUM_P95_LATENCY",
    "MAXIMUM_AVERAGE_COST",
    "MAXIMUM_GENERATION_ERRORS",
    "MAXIMUM_JUDGE_ERRORS",
    "MINIMUM_VALID_EVALUATION_RATIO",
    "MAXIMUM_REGRESSION_COUNT",
    "MAX_CONCURRENT_REQUESTS",
    "DATABASE_URL",
    "PRICING_CONFIG_PATH",
}
SECRET_PATTERNS = [
    re.compile(r"gsk_[A-Za-z0-9_-]{20,}"),
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"(?i)(api[_-]?key|token|password)\s*=\s*['\"][^'\"\s]+['\"]"),
]


def main() -> int:
    failures: list[str] = []

    failures.extend(validate_required_files())
    failures.extend(validate_env_example())
    failures.extend(validate_dataset())
    failures.extend(validate_prompts())
    failures.extend(validate_settings())
    failures.extend(validate_yaml())
    failures.extend(validate_security())

    if failures:
        print("Project validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Project validation passed.")
    return 0


def validate_required_files() -> list[str]:
    failures = []
    for relative_path in REQUIRED_FILES:
        if not (PROJECT_ROOT / relative_path).exists():
            failures.append(f"Missing required file: {relative_path}")
    return failures


def validate_env_example() -> list[str]:
    path = PROJECT_ROOT / ".env.example"
    if not path.exists():
        return ["Missing .env.example"]
    keys = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        keys.add(stripped.split("=", 1)[0])
    if keys != EXPECTED_ENV_KEYS:
        missing = sorted(EXPECTED_ENV_KEYS - keys)
        extra = sorted(keys - EXPECTED_ENV_KEYS)
        return [f".env.example keys mismatch. Missing={missing}, extra={extra}"]
    return []


def validate_dataset() -> list[str]:
    try:
        test_cases = load_golden_dataset(PROJECT_ROOT / "data" / "golden_dataset.json")
    except Exception as exc:
        return [f"Dataset validation failed: {exc}"]

    failures = []
    if len(test_cases) < 4:
        failures.append("Dataset should include multiple behavior types")
    behavior_counts = {behavior: 0 for behavior in ("answer", "unanswerable", "clarify", "refuse")}
    for case in test_cases:
        behavior_counts[case.expected_behavior] += 1
        overlap = {
            include.lower()
            for include in case.must_include
        } & {exclude.lower() for exclude in case.must_not_include}
        if overlap:
            failures.append(f"Case {case.id} has terms in both include and exclude lists: {overlap}")
    missing_behaviors = [behavior for behavior, count in behavior_counts.items() if count == 0]
    if missing_behaviors:
        failures.append(f"Dataset missing behavior types: {', '.join(missing_behaviors)}")
    return failures


def validate_prompts() -> list[str]:
    try:
        prompt_manager = PromptManager(PROJECT_ROOT)
        prompt_manager.get_baseline_prompt()
        prompt_manager.get_candidate_prompt()
        judge_prompt = prompt_manager.get_judge_prompt()
    except Exception as exc:
        return [f"Prompt validation failed: {exc}"]
    required_placeholders = {"{question}", "{context}", "{behavior}", "{expected}", "{actual}"}
    missing = [placeholder for placeholder in required_placeholders if placeholder not in judge_prompt]
    if missing:
        return [f"Judge prompt missing placeholders: {', '.join(missing)}"]
    return []


def validate_settings() -> list[str]:
    try:
        Settings.model_validate({"TEST_LIMIT": ""})
    except Exception as exc:
        return [f"Settings validation failed: {exc}"]
    return []


def validate_yaml() -> list[str]:
    failures = []
    for relative_path in [
        ".github/workflows/llm-evaluation.yml",
        "docker-compose.yml",
        ".streamlit/config.toml",
    ]:
        path = PROJECT_ROOT / relative_path
        if not path.exists():
            continue
        if path.suffix in {".yml", ".yaml"}:
            try:
                yaml.safe_load(path.read_text(encoding="utf-8"))
            except yaml.YAMLError as exc:
                failures.append(f"Invalid YAML in {relative_path}: {exc}")
    return failures


def validate_security() -> list[str]:
    failures = []
    for path in PROJECT_ROOT.rglob("*"):
        if path.is_dir() or should_skip_security_scan(path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                failures.append(f"Potential secret-like value found in {path.relative_to(PROJECT_ROOT)}")
                break

    gitignore = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")
    for required_entry in [
        ".env",
        ".venv/",
        "venv/",
        "__pycache__/",
        "reports/*.json",
        "reports/experiments/",
        "data/*.db",
    ]:
        if required_entry not in gitignore:
            failures.append(f".gitignore missing {required_entry}")
    return failures


def should_skip_security_scan(path: Path) -> bool:
    relative = path.relative_to(PROJECT_ROOT)
    parts = set(relative.parts)
    return path.name == ".env" or path.suffix == ".zip" or bool(
        parts & {".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache"}
    )


if __name__ == "__main__":
    raise SystemExit(main())
