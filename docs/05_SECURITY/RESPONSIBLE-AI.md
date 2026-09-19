# NyayaLens — Responsible AI

## 1. Purpose

NyayaLens uses generative AI to help users understand legal documents.

Because legal information can influence important decisions, the system must prioritize:

* Accuracy
* Grounding
* Transparency
* User control
* Uncertainty
* Accessibility
* Human review

## 2. Product Boundary

NyayaLens is **not an AI lawyer**.

It does not:

* Represent users
* Create an attorney-client relationship
* Guarantee legal outcomes
* Determine whether a user will win a case
* Replace a qualified legal professional

It provides document analysis and general information.

## 3. Grounded Answers

Whenever possible, answers should be grounded in the uploaded document.

Example:

```text
Question
   ↓
Retrieve evidence
   ↓
Generate answer
   ↓
Validate evidence
   ↓
Attach citations
```

If evidence is insufficient, the system should say so.

## 4. Evidence States

Responses use explicit evidence states:

### DOCUMENT-GROUNDED

The answer is supported by retrieved document evidence.

### GENERAL-INFORMATION

The response is general information and is not directly established by the document.

### INSUFFICIENT-EVIDENCE

The available evidence is insufficient to provide a reliable answer.

## 5. No Fabricated Citations

The system must never intentionally generate citations that do not correspond to source material.

Backend validation is required.

## 6. Uncertainty

Avoid absolute language when the evidence does not justify it.

Avoid:

> This contract is definitely illegal.

Prefer:

> This clause may require professional review because the document contains X, but NyayaLens cannot determine legal validity.

## 7. Attention Analysis

NyayaLens should use:

**Areas Requiring Attention**

instead of presenting an unsupported legal-risk score.

Examples:

* Unusually long notice period
* Broad confidentiality language
* Missing information
* Ambiguous obligation
* Financial term requiring review

These are review signals, not legal conclusions.

## 8. Human Oversight

The system should recommend professional review when:

* The issue is high consequence
* Evidence is ambiguous
* The user asks for jurisdiction-specific legal interpretation
* The document contains conflicting provisions
* The model has insufficient evidence
* The user asks for litigation strategy

## 9. Prompt Injection

Document text is untrusted.

AI instructions must explicitly prevent document content from overriding system instructions.

## 10. Bias

Potential bias can occur in:

* Classification
* Summarization
* Language generation
* Translation
* Attention analysis

Evaluation should therefore include documents with different:

* Writing styles
* Document structures
* Languages where supported
* Complexity levels

## 11. Accessibility

AI-generated explanations should be:

* Plain-language where possible
* Structured with headings
* Concise
* Screen-reader friendly
* Free of unnecessary legal jargon

The user should be able to request a simpler explanation.

## 12. Transparency

AI-generated content must be visibly identified.

Example:

```text
AI-assisted analysis
Source: Employment Agreement — Page 6
```

## 13. User Control

Users remain responsible for deciding what action to take.

NyayaLens should help users prepare for professional discussion rather than make decisions for them.

## 14. Evaluation

AI quality should be evaluated using:

* Grounding accuracy
* Citation accuracy
* Retrieval recall
* Hallucination rate
* Abstention quality
* Clause extraction accuracy
* Comparison accuracy
* Action recommendation usefulness

## 15. Failure Behavior

When the system cannot confidently answer:

```text
I couldn't find enough evidence in this document to answer that reliably.
```

It should not invent an answer.

## 16. Responsible AI Checklist

* [ ] Legal disclaimer visible
* [ ] AI output labeled
* [ ] Document-grounded Q&A implemented
* [ ] Citation validation implemented
* [ ] Insufficient-evidence state implemented
* [ ] Prompt injection defense implemented
* [ ] No unsupported legal conclusions
* [ ] Professional-review recommendations implemented
* [ ] Plain-language explanations available
* [ ] AI evaluation dataset created
* [ ] Hallucination tests implemented
* [ ] Accessibility tested
