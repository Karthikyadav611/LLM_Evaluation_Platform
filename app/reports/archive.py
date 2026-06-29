import zipfile
from pathlib import Path

from app.exceptions import ReportArchiveError


def safe_extract_report_zip(uploaded_file, target_dir: Path, max_bytes: int = 50_000_000) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    target_root = target_dir.resolve()
    total_size = 0

    try:
        with zipfile.ZipFile(uploaded_file) as archive:
            for member in archive.infolist():
                total_size += member.file_size
                if total_size > max_bytes:
                    raise ReportArchiveError("The uploaded ZIP is too large")
                destination = (target_root / member.filename).resolve()
                try:
                    destination.relative_to(target_root)
                except ValueError as exc:
                    raise ReportArchiveError("The uploaded ZIP contains an unsafe path") from exc
            archive.extractall(target_root)
    except zipfile.BadZipFile as exc:
        raise ReportArchiveError("The uploaded file is not a valid ZIP archive") from exc
    return target_root
