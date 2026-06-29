import json
import re
import shutil
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class PreparedExperimentDirectory:
    experiment_id: str
    reports_root: Path
    experiments_root: Path
    final_dir: Path
    temp_dir: Path
    relative_report_directory: str


def resolve_reports_root(reports_dir: Path) -> Path:
    root = reports_dir if reports_dir.is_absolute() else PROJECT_ROOT / reports_dir
    return root.resolve()


def sanitize_experiment_id(experiment_id: str) -> str:
    raw = experiment_id.strip()
    if not raw:
        raise ValueError("Experiment ID must not be blank")
    if "/" in raw or "\\" in raw:
        raise ValueError("Experiment ID must not contain path separators")
    if raw in {".", ".."} or ".." in raw.split("."):
        raise ValueError("Experiment ID must not contain path traversal segments")
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "-", raw).strip(".-")
    if not safe:
        raise ValueError("Experiment ID does not contain safe filename characters")
    return safe


def prepare_experiment_directory(reports_dir: Path, experiment_id: str) -> PreparedExperimentDirectory:
    reports_root = resolve_reports_root(reports_dir)
    experiments_root = (reports_root / "experiments").resolve()
    _ensure_child(reports_root, experiments_root)
    experiments_root.mkdir(parents=True, exist_ok=True)

    base_id = sanitize_experiment_id(experiment_id)
    final_id = base_id
    final_dir = (experiments_root / final_id).resolve()
    suffix = 1
    while final_dir.exists():
        final_id = f"{base_id}-{suffix}"
        final_dir = (experiments_root / final_id).resolve()
        suffix += 1
    _ensure_child(experiments_root, final_dir)

    temp_dir = (experiments_root / f".tmp-{final_id}-{uuid.uuid4().hex[:8]}").resolve()
    _ensure_child(experiments_root, temp_dir)
    relative_report_directory = _relative_to_project(final_dir)
    return PreparedExperimentDirectory(
        experiment_id=final_id,
        reports_root=reports_root,
        experiments_root=experiments_root,
        final_dir=final_dir,
        temp_dir=temp_dir,
        relative_report_directory=relative_report_directory,
    )


def write_experiment_files(
    prepared: PreparedExperimentDirectory,
    files: dict[str, str | bytes],
    *,
    run_id: str,
    status: str,
    created_at: str,
) -> None:
    if prepared.temp_dir.exists():
        shutil.rmtree(prepared.temp_dir)
    prepared.temp_dir.mkdir(parents=True)
    try:
        for filename, content in files.items():
            destination = (prepared.temp_dir / filename).resolve()
            _ensure_child(prepared.temp_dir, destination)
            destination.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(content, bytes):
                destination.write_bytes(content)
            else:
                destination.write_text(content, encoding="utf-8")
        prepared.temp_dir.rename(prepared.final_dir)
        _write_latest_pointer(
            prepared.reports_root,
            {
                "experiment_id": prepared.experiment_id,
                "run_id": run_id,
                "status": status,
                "created_at": created_at,
                "report_directory": prepared.relative_report_directory,
            },
        )
    except Exception:
        if prepared.temp_dir.exists():
            shutil.rmtree(prepared.temp_dir, ignore_errors=True)
        raise


def read_latest_pointer(reports_dir: Path) -> dict | None:
    latest_path = resolve_reports_root(reports_dir) / "latest.json"
    if not latest_path.exists():
        return None
    return json.loads(latest_path.read_text(encoding="utf-8"))


def latest_report_directory(reports_dir: Path) -> Path | None:
    pointer = read_latest_pointer(reports_dir)
    if not pointer:
        return None
    report_directory = pointer.get("report_directory")
    if not isinstance(report_directory, str):
        return None
    path = (PROJECT_ROOT / report_directory).resolve()
    _ensure_child(PROJECT_ROOT, path)
    return path if path.exists() and path.is_dir() else None


def list_experiment_directories(reports_dir: Path) -> list[Path]:
    experiments_root = resolve_reports_root(reports_dir) / "experiments"
    if not experiments_root.exists():
        return []
    return sorted(
        [path for path in experiments_root.iterdir() if path.is_dir() and not path.name.startswith(".tmp-")],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )


def _write_latest_pointer(reports_root: Path, payload: dict) -> None:
    reports_root.mkdir(parents=True, exist_ok=True)
    payload = {**payload, "created_at": payload.get("created_at") or datetime.now().astimezone().isoformat()}
    latest_path = reports_root / "latest.json"
    temp_path = reports_root / f".latest-{uuid.uuid4().hex}.tmp"
    temp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    temp_path.replace(latest_path)


def _ensure_child(root: Path, child: Path) -> None:
    root_resolved = root.resolve()
    child_resolved = child.resolve()
    try:
        child_resolved.relative_to(root_resolved)
    except ValueError as exc:
        raise ValueError(f"Unsafe path outside expected root: {child}") from exc


def _relative_to_project(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.resolve().as_posix()
