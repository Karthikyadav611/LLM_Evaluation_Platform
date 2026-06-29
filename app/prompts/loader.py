from pathlib import Path


def load_prompt_file(path: Path) -> str:
    content = path.read_text(encoding="utf-8").strip()
    if not content:
        raise ValueError(f"Prompt file is empty: {path}")
    return content


def load_prompts(prompt_dir: Path) -> dict[str, str]:
    prompts: dict[str, str] = {}
    for path in sorted(prompt_dir.glob("*.txt")):
        prompts[path.stem] = load_prompt_file(path)
    return prompts
