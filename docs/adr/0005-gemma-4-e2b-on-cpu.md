# ADR 0005: Gemma 4 E2B, 4-bit, on CPU

**Status:** accepted

**Context.** Triage runs on every incident, so the model must be cheap and private. A GPU is not
available for this project.

**Decision.** Gemma 4 E2B in the official quantization-aware Q4_0 GGUF, through llama-cpp-python on 8
CPU threads, greedy decoding, pinned by revision and SHA-256. A plain JSON-in-text tool protocol.

**Consequences.** A hybrid answer takes seconds on a laptop-class CPU. Larger models would likely do
better as free agents; they are not measured here.
