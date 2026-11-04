"""Tests for fast Hugging Face tokenizer offset adaptation."""

import sys
from collections.abc import Mapping
from types import ModuleType

import pytest

from neuralnotes.chunking import HuggingFaceOffsetTokenizer, TokenSpan


class FakeFastTokenizer:
    is_fast = True

    def __init__(self, offsets: object) -> None:
        self.offsets = offsets
        self.call_options: dict[str, bool] = {}

    def __call__(
        self,
        text: str,
        *,
        add_special_tokens: bool,
        return_offsets_mapping: bool,
        truncation: bool,
    ) -> Mapping[str, object]:
        self.call_options = {
            "add_special_tokens": add_special_tokens,
            "return_offsets_mapping": return_offsets_mapping,
            "truncation": truncation,
        }
        return {"offset_mapping": self.offsets}


def test_huggingface_tokenizer_returns_character_spans_without_special_tokens() -> None:
    tokenizer = FakeFastTokenizer([(0, 6), (7, 12)])
    adapter = HuggingFaceOffsetTokenizer(tokenizer)

    spans = adapter.token_spans("Neural notes")

    assert spans == (TokenSpan(0, 6), TokenSpan(7, 12))
    assert tokenizer.call_options == {
        "add_special_tokens": False,
        "return_offsets_mapping": True,
        "truncation": False,
    }


def test_huggingface_tokenizer_ignores_zero_length_special_offsets() -> None:
    adapter = HuggingFaceOffsetTokenizer(FakeFastTokenizer([(0, 0), (0, 4)]))

    assert adapter.token_spans("text") == (TokenSpan(0, 4),)


def test_huggingface_tokenizer_rejects_slow_tokenizers() -> None:
    class SlowTokenizer(FakeFastTokenizer):
        is_fast = False

    with pytest.raises(ValueError, match="fast tokenizer"):
        HuggingFaceOffsetTokenizer(SlowTokenizer([]))


@pytest.mark.parametrize(
    "offsets",
    [None, [(0, 3), (2, 4)], [(0, 5)], [("0", 2)], [(0, 0), (2, 2)]],
)
def test_huggingface_tokenizer_rejects_invalid_offsets(offsets: object) -> None:
    adapter = HuggingFaceOffsetTokenizer(FakeFastTokenizer(offsets))

    with pytest.raises(ValueError):
        adapter.token_spans("text")


def test_huggingface_tokenizer_requires_nonempty_model_name() -> None:
    with pytest.raises(ValueError, match="model_name"):
        HuggingFaceOffsetTokenizer.from_pretrained(" ")


def test_from_pretrained_requests_fast_tokenizer_without_downloading_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tokenizer = FakeFastTokenizer([(0, 4)])
    call: dict[str, object] = {}

    class FakeAutoTokenizer:
        @staticmethod
        def from_pretrained(model_name: str, *, use_fast: bool) -> FakeFastTokenizer:
            call.update(model_name=model_name, use_fast=use_fast)
            return tokenizer

    fake_transformers = ModuleType("transformers")
    fake_transformers.AutoTokenizer = FakeAutoTokenizer  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "transformers", fake_transformers)

    adapter = HuggingFaceOffsetTokenizer.from_pretrained()

    assert call == {
        "model_name": "sentence-transformers/all-MiniLM-L6-v2",
        "use_fast": True,
    }
    assert adapter.token_spans("text") == (TokenSpan(0, 4),)
