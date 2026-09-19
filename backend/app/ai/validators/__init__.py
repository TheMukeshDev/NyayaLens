"""Backend validators: proof-based checks that never trust the model.

Validators verify model output against the backend's own persisted data before
anything is presented to the user (AI-Architecture.md §13). Today this means
citation validation; answer/content validators can be added alongside the
feature that needs them.
"""