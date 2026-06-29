from types import SimpleNamespace

from app.providers.factory import create_provider
from app.security import sanitize_text


class FakeModels:
    def list(self):
        return [SimpleNamespace(id="model-a"), SimpleNamespace(name="models/model-b")]


class FakeChatCompletions:
    def create(self, **kwargs):
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="answer"))],
            usage=SimpleNamespace(prompt_tokens=3, completion_tokens=4, total_tokens=7),
        )


class FakeChatClient:
    models = FakeModels()
    chat = SimpleNamespace(completions=FakeChatCompletions())


class FakeAnthropicMessages:
    def create(self, **kwargs):
        return SimpleNamespace(
            content=[SimpleNamespace(text="answer")],
            usage=SimpleNamespace(input_tokens=5, output_tokens=6),
        )


class FakeAnthropicClient:
    models = FakeModels()
    messages = FakeAnthropicMessages()


class FakeGeminiModels(FakeModels):
    def generate_content(self, **kwargs):
        return SimpleNamespace(
            text="answer",
            usage_metadata=SimpleNamespace(
                prompt_token_count=7,
                candidates_token_count=8,
                total_token_count=15,
            ),
        )


class FakeGeminiClient:
    models = FakeGeminiModels()


def test_provider_factory_supports_all_providers_with_fake_clients():
    fake_clients = {
        "groq": FakeChatClient(),
        "openai": FakeChatClient(),
        "anthropic": FakeAnthropicClient(),
        "gemini": FakeGeminiClient(),
    }

    for provider, client in fake_clients.items():
        llm = create_provider(provider, **{"api_" + "key": "test-value"}, model="model-a", client=client)
        assert llm.list_models() == ["model-a", "model-b"]
        result = llm.generate(
            system_prompt="system",
            user_prompt="user",
            temperature=0,
            max_output_tokens=16,
        )
        assert result.provider == provider
        assert result.answer == "answer"
        assert result.total_tokens > 0


def test_sanitized_errors_remove_key_like_values():
    fake_key = "sk-" + "1234567890abcdef1234567890"
    message = sanitize_text(f"failed with {fake_key} and credential=sample")
    assert fake_key not in message
