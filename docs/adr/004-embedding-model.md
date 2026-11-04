# ADR 004: Select an initial local embedding model

- **Status:** Accepted as an initial baseline
- **Date:** 2026-11-04

## Context

Phase 2 needs a local English embedding model whose tokenizer can provide character offsets. NeuralNotes needs those offsets to keep chunk text and later citations tied to the original document. Model quality, retrieval quality, and latency have not yet been evaluated on the project corpus.

## Decision

Start with `sentence-transformers/all-MiniLM-L6-v2` through Sentence Transformers. Pin `sentence-transformers==6.2.0` in the optional `embeddings` dependency group so the base application does not install PyTorch and model dependencies unless requested.

Use provisional fixed-size chunk defaults of 100 tokens with 20 tokens of overlap. The model card documents a 128-token training sequence and 384-dimensional embeddings. The smaller initial chunk leaves room for later input formatting and avoids using the model's full sequence budget by default. These values are initial engineering defaults; Phase 5 must compare embedding and chunking variants using the evaluation harness before a final choice.

## Consequences

- The tokenizer adapter must use a fast tokenizer and offset mappings so chunks retain character positions. It will remain lazily loaded behind the existing tokenizer protocol.
- The model is English-focused and may not be suitable for multilingual documents.
- Sentence Transformers and PyTorch increase installation size, so they stay optional. CPU inference is the portability baseline; CUDA acceleration depends on the installed PyTorch build and local driver.
- This decision does not claim the model is the most accurate, fastest, or best choice for the project. Phase 5 will compare at least two models on the development set and confirm the selected configuration on the held-out test set.

## Sources

- [all-MiniLM-L6-v2 model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)
- [Sentence Transformers installation guide](https://sbert.net/docs/installation.html)
- [Sentence Transformers 6.2.0 on PyPI](https://pypi.org/project/sentence-transformers/6.2.0/)
- [Hugging Face tokenizer offset mapping documentation](https://huggingface.co/docs/transformers/main_classes/tokenizer)
