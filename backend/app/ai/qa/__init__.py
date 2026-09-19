"""Document-grounded Q&A (docs/04_AI/AI-Architecture.md §10, FR-005).

The answer-generating orchestrator: retrieval -> evidence selection -> prompt
-> schema-validated LLM -> answer/citation validation. See
:mod:`app.ai.qa.service` for the full pipeline and its honesty rules.
"""