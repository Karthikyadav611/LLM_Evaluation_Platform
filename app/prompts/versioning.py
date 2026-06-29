import hashlib


def hash_prompt(prompt_text: str) -> str:
    normalized = "\n".join(line.rstrip() for line in prompt_text.strip().splitlines())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
