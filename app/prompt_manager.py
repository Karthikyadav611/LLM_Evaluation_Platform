from pathlib import Path

from app.prompts.loader import load_prompt_file
from app.prompts.versioning import hash_prompt


class PromptManager:
    def __init__(self, project_root: Path):
        self.prompt_dir = project_root / "prompts"

    def _read_prompt(self, filename: str) -> str:
        path = self.prompt_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Prompt file {filename} missing at {path}")
        return load_prompt_file(path)

    def get_baseline_prompt(self) -> str:
        return self._read_prompt("baseline_prompt.txt")

    def get_candidate_prompt(self) -> str:
        return self._read_prompt("candidate_prompt.txt")

    def get_judge_prompt(self) -> str:
        return self._read_prompt("judge_prompt.txt")

    def prompt_hash(self, prompt_text: str) -> str:
        return hash_prompt(prompt_text)
