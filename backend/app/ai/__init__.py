"""AI orchestration.

Implements the retrieval and generation layers
(docs/04_AI/AI-Architecture.md, docs/04_AI/RAG-Architecture.md):

* ``embeddings`` — provider abstraction, pgvector persistence and the chunk
  indexing service (chunk -> embedding -> vector storage).
* ``llm`` — provider-independent LLM abstraction (OpenAI-compatible chat
  completions) with timeout, retry, rate limit, structured output and safe
  error handling; never fabricates output.
* ``prompts`` — versioned, safety-hardened prompts (summary, clause
  extraction, attention analysis, Q&A, comparison, action) that separate
  instructions from untrusted document data and support abstention.
* ``rag`` — ownership-scoped similarity search, reranking, evidence
  threshold, context building and query processing (no answer generation).
* ``validators`` — backend proof-based checks on model output: citation
  existence, document/ownership membership and section/page metadata.
* ``qa`` — the document-grounded Q&A orchestrator: retrieval -> evidence
  selection -> prompt -> schema-validated LLM -> answer/citation validation.
"""
