from __future__ import annotations

import json

from scripts.controlled_cases import (
    ITEM_DETAIL_INSTRUCTION,
    OllamaOptionsClient,
    SystemInstructionClient,
)


class Response:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self) -> bytes:
        return json.dumps({"choices": [{"message": {"content": "ok"}}]}).encode()


def test_ollama_experiment_client_sends_explicit_sampling_options(monkeypatch) -> None:
    captured = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["body"] = json.loads(request.data)
        captured["timeout"] = timeout
        return Response()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    client = OllamaOptionsClient(
        model="test-model",
        base_url="http://localhost:11434/v1/",
        timeout_s=45,
        temperature=0,
        top_p=0.1,
        seed=42,
    )

    assert client.complete("system", "question") == "ok"
    assert captured["url"] == "http://localhost:11434/v1/chat/completions"
    assert captured["timeout"] == 45
    assert captured["body"]["temperature"] == 0
    assert captured["body"]["top_p"] == 0.1
    assert captured["body"]["seed"] == 42
    assert "options" not in captured["body"]


def test_item_detail_instruction_is_appended_as_a_separate_system_instruction() -> None:
    captured = {}

    class RecordingClient:
        def complete(self, system: str, user: str) -> str:
            captured["system"] = system
            captured["user"] = user
            return "ok"

    client = SystemInstructionClient(RecordingClient(), ITEM_DETAIL_INSTRUCTION)

    assert client.complete("base system", "question") == "ok"
    assert captured["system"] == f"base system\n\n{ITEM_DETAIL_INSTRUCTION}"
    assert captured["user"] == "question"
