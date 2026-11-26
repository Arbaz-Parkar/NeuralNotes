"""Ollama chat adapter for the provider-neutral answer-generation contract."""

import json
from collections.abc import Sequence
from time import perf_counter
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from opentelemetry import trace

from neuralnotes.generation.models import DraftAnswer, RetrievedPassage
from neuralnotes.generation.prompts import get_answer_prompt
from neuralnotes.telemetry import record_generation


class OllamaGenerationError(RuntimeError):
    """Raised when the local Ollama service cannot return a valid draft."""


class OllamaAnswerGenerator:
    """Generate structured claim-level answers through Ollama's local API."""

    def __init__(
        self,
        *,
        model_name: str = "qwen3.5:4b",
        base_url: str = "http://localhost:11434",
        timeout_seconds: float = 120.0,
        max_output_tokens: int = 512,
    ) -> None:
        if not model_name.strip():
            raise ValueError("model_name must not be empty.")
        if not base_url.strip():
            raise ValueError("base_url must not be empty.")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero.")
        if max_output_tokens <= 0:
            raise ValueError("max_output_tokens must be greater than zero.")
        self._model_name = model_name
        self._endpoint = f"{base_url.rstrip('/')}/api/chat"
        self._timeout_seconds = timeout_seconds
        self._max_output_tokens = max_output_tokens

    def generate(
        self,
        question: str,
        passages: Sequence[RetrievedPassage],
    ) -> DraftAnswer:
        """Call Ollama with JSON Schema-constrained claim and citation output."""
        evidence = [passage.model_dump(mode="json") for passage in passages]
        payload = {
            "model": self._model_name,
            "stream": False,
            # Qwen3.5 otherwise emits long reasoning before its structured answer.
            "think": False,
            "format": DraftAnswer.model_json_schema(),
            "options": {
                "temperature": 0,
                "num_predict": self._max_output_tokens,
            },
            "messages": [
                {
                    "role": "system",
                    "content": get_answer_prompt(),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {"question": question, "evidence": evidence},
                        ensure_ascii=False,
                    ),
                },
            ],
        }
        request = Request(
            self._endpoint,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        started_at = perf_counter()
        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:
                response_payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise OllamaGenerationError(
                f"Ollama returned HTTP {exc.code}: {detail[:500]}"
            ) from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise OllamaGenerationError(
                "Could not reach Ollama at the configured local endpoint. "
                "Start Ollama and confirm the model is installed."
            ) from exc
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise OllamaGenerationError(
                "Ollama returned a response that was not valid JSON."
            ) from exc

        request_duration_ms = (perf_counter() - started_at) * 1_000
        prompt_tokens = response_payload.get("prompt_eval_count")
        completion_tokens = response_payload.get("eval_count")
        if not isinstance(prompt_tokens, int) or isinstance(prompt_tokens, bool):
            prompt_tokens = None
        if not isinstance(completion_tokens, int) or isinstance(
            completion_tokens, bool
        ):
            completion_tokens = None

        span = trace.get_current_span()
        if span.is_recording():
            span.set_attribute("llm.request.duration_ms", request_duration_ms)
            if prompt_tokens is not None:
                span.set_attribute("llm.usage.input_tokens", prompt_tokens)
            if completion_tokens is not None:
                span.set_attribute("llm.usage.output_tokens", completion_tokens)
            if prompt_tokens is not None and completion_tokens is not None:
                span.set_attribute(
                    "llm.usage.total_tokens", prompt_tokens + completion_tokens
                )
            total_duration_ns = response_payload.get("total_duration")
            if isinstance(total_duration_ns, int) and not isinstance(
                total_duration_ns, bool
            ):
                span.set_attribute(
                    "llm.response.duration_ms", total_duration_ns / 1_000_000
                )

        record_generation(request_duration_ms, prompt_tokens, completion_tokens)

        try:
            content = response_payload["message"]["content"]
            if not isinstance(content, str):
                raise TypeError("message.content must be a string")
            return DraftAnswer.model_validate_json(content)
        except (KeyError, TypeError, ValueError) as exc:
            raise OllamaGenerationError(
                "Ollama response did not match the grounded-answer schema."
            ) from exc
