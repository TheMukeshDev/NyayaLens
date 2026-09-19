# NyayaLens — Success Metrics

---

# 1. Purpose

Success metrics measure whether NyayaLens is:

* Useful
* Accurate
* Grounded
* Secure
* Accessible
* Reliable
* Efficient

Metrics are divided into product, AI, security, performance, accessibility, and adoption categories.

---

# 2. North Star Metric

## Successful Grounded Review

A **Successful Grounded Review** occurs when a user:

```text
Uploads a document
        ↓
Receives analysis
        ↓
Views key information
        ↓
Asks a question
        ↓
Receives a supported answer
        ↓
Can locate the cited source
```

This represents the core NyayaLens value proposition.

---

# 3. Product Metrics

## 3.1 Document Processing Success Rate

```text
Successful Processing
--------------------- × 100
Total Processing Jobs
```

Target:

```text
≥ 95%
```

---

## 3.2 Time to First Useful Result

Measure the time from successful upload to availability of the first useful analysis.

Target for typical demo documents:

```text
< 60 seconds
```

Exact production target should be refined based on document size and infrastructure.

---

## 3.3 Q&A Completion Rate

Percentage of document questions that receive a usable response.

Target:

```text
≥ 90%
```

---

## 3.4 Citation Availability

Percentage of document-grounded answers containing valid source citations.

Target:

```text
≥ 95%
```

---

# 4. AI Quality Metrics

## 4.1 Retrieval Relevance

Measure whether retrieved chunks actually support the user's question.

Target:

```text
High relevance on evaluation dataset
```

---

## 4.2 Citation Accuracy

Percentage of citations that genuinely support the generated statement.

Target:

```text
≥ 95%
```

---

## 4.3 Unsupported Claim Rate

Measure statements that cannot be supported by retrieved evidence.

Target:

```text
As low as possible
```

Critical unsupported claims should be treated as high-severity failures.

---

## 4.4 Hallucination Rate

Measure AI statements that introduce unsupported information.

Target:

```text
< 5% on controlled evaluation dataset
```

For critical document facts, the target should be stricter.

---

## 4.5 Abstention Quality

Measure whether the system correctly says:

```text
"I couldn't find enough information in this document."
```

when evidence is insufficient.

A good system should not maximize answer rate at the expense of grounding.

---

# 5. Comparison Metrics

## 5.1 Change Detection Accuracy

Measure whether added, removed, and modified clauses are correctly detected.

Target:

```text
≥ 90% on evaluation dataset
```

---

## 5.2 Important Change Recall

Measure how often meaningful changes are surfaced.

Target:

```text
≥ 90%
```

---

# 6. Security Metrics

## 6.1 Cross-User Access

Target:

```text
0 unauthorized document accesses
```

This is a critical security invariant.

---

## 6.2 Secret Exposure

Target:

```text
0 secrets committed to repository
```

---

## 6.3 Sensitive Logging

Target:

```text
0 full legal documents in application logs
```

---

## 6.4 Prompt Injection Resistance

Test whether malicious instructions embedded inside documents can manipulate the AI system.

Target:

```text
No critical successful prompt-injection paths
```

---

# 7. Accessibility Metrics

Track:

* Keyboard navigation success
* Focus visibility
* Form-label coverage
* Semantic HTML
* Color contrast
* Screen-reader compatibility

Target:

```text
No critical accessibility blockers in MVP
```

---

# 8. Performance Metrics

Measure:

### Frontend

* Initial page load
* Time to interactive
* API latency
* Dashboard rendering

### Backend

* API response time
* Database query latency
* Document-processing time
* Vector retrieval time

Target:

```text
Normal API requests:
< 500 ms where practical

Vector retrieval:
< 1 second where practical
```

AI generation will naturally have higher latency.

---

# 9. Reliability Metrics

### Failed Jobs

Track document-processing failures.

### Retry Success

Track how many failed jobs succeed after retry.

### API Error Rate

Track server errors.

Target:

```text
< 1% application error rate under normal conditions
```

---

# 10. User Experience Metrics

Measure:

* Upload completion
* Analysis completion
* Q&A usage
* Citation clicks
* Comparison usage
* Action completion

Useful funnel:

```text
Signup
 ↓
Upload
 ↓
Ready
 ↓
View Analysis
 ↓
Ask Question
 ↓
Open Citation
 ↓
Compare
 ↓
Create Action
```

---

# 11. Evaluation Dataset

Maintain a controlled dataset containing representative:

* Employment agreements
* Rental agreements
* NDAs
* Service contracts
* Vendor agreements
* Policies

Each evaluation document should have manually verified expected information.

---

# 12. PromptWars Evaluation Alignment

| Evaluation Area   | Key Metric                              |
| ----------------- | --------------------------------------- |
| Security          | Unauthorized access = 0                 |
| Accessibility     | No critical blockers                    |
| Problem Alignment | Successful grounded review              |
| Code Quality      | Lint/type/test pass rate                |
| Efficiency        | Processing/API latency                  |
| Testing           | Automated test coverage + AI evaluation |

---

# 13. MVP Success Threshold

The MVP is ready for final submission when:

```text
✓ Core workflow works
✓ Documents process successfully
✓ Q&A is document-grounded
✓ Citations are valid
✓ Comparison works
✓ User isolation is verified
✓ Prompt-injection defenses tested
✓ Accessibility reviewed
✓ Automated tests pass
✓ Deployment works
✓ README is complete
```

---

# 14. Metric Philosophy

NyayaLens should not optimize for:

```text
"AI answers every question."
```

It should optimize for:

```text
"AI gives useful answers when evidence exists
and safely communicates uncertainty when evidence does not."
```

That distinction is central to a trustworthy legal-assistance product.
