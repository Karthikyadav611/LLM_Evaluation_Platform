import hashlib
from collections.abc import Iterable

from app.prompts.versioning import hash_prompt
from app.schemas import ExperimentConfiguration


def build_configuration_id(
    *,
    prompt_hash: str,
    provider: str,
    model: str,
    judge_provider: str,
    judge_model: str,
    dataset_hash: str,
) -> str:
    payload = "|".join(
        [prompt_hash, provider.lower(), model, judge_provider.lower(), judge_model, dataset_hash]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def expand_prompt_model_matrix(
    *,
    experiment_id: str,
    run_id: str,
    prompts: dict[str, str],
    provider_models: Iterable[tuple[str, str]],
    judge_provider: str,
    judge_model: str,
    dataset_name: str,
    dataset_hash: str,
    temperature: float = 0.0,
    max_output_tokens: int = 1024,
) -> list[ExperimentConfiguration]:
    configurations: list[ExperimentConfiguration] = []
    for prompt_name, prompt_text in prompts.items():
        prompt_hash = hash_prompt(prompt_text)
        for provider, model in provider_models:
            configuration_id = build_configuration_id(
                prompt_hash=prompt_hash,
                provider=provider,
                model=model,
                judge_provider=judge_provider,
                judge_model=judge_model,
                dataset_hash=dataset_hash,
            )
            configurations.append(
                ExperimentConfiguration(
                    experiment_id=experiment_id,
                    run_id=run_id,
                    configuration_id=configuration_id,
                    prompt_name=prompt_name,
                    prompt_text=prompt_text,
                    prompt_hash=prompt_hash,
                    provider=provider,
                    model=model,
                    judge_provider=judge_provider,
                    judge_model=judge_model,
                    dataset_name=dataset_name,
                    dataset_hash=dataset_hash,
                    temperature=temperature,
                    max_output_tokens=max_output_tokens,
                )
            )
    return configurations
