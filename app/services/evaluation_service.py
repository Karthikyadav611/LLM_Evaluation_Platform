def estimate_api_calls(
    *,
    mode: str,
    test_count: int,
    prompt_count: int = 1,
    model_count: int = 1,
) -> dict[str, int]:
    if mode == "prompt_comparison":
        generation_calls = 2 * test_count
        judge_calls = 2 * test_count
    elif mode == "model_comparison":
        generation_calls = model_count * test_count
        judge_calls = model_count * test_count
    else:
        generation_calls = prompt_count * model_count * test_count
        judge_calls = generation_calls
    return {
        "generation_calls": generation_calls,
        "judge_calls": judge_calls,
        "approximate_total": generation_calls + judge_calls,
    }
