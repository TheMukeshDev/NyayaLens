# NyayaLens — Test Plan

## 1. Objective

The test plan verifies that NyayaLens is:

* Functional
* Secure
* Accessible
* Reliable
* Grounded in source documents
* Resistant to hallucination and prompt injection
* Suitable for hackathon evaluation

## 2. Testing Layers

```text
                 E2E Tests
                    ↑
          Integration Tests
                    ↑
              Unit Tests
                    ↑
       AI Evaluation Dataset
```

## 3. Functional Testing

Test:

* Registration
* Login
* Logout
* Upload
* Processing
* Document overview
* Summary
* Clause extraction
* Attention analysis
* Q&A
* Citations
* Comparison
* Action center
* Reports
* Deletion

## 4. Security Testing

High-priority tests:

* Unauthorized document access
* IDOR
* Cross-user RAG leakage
* Malicious file upload
* Prompt injection
* XSS
* SQL injection
* Rate-limit bypass
* Token/session abuse
* CORS configuration
* Secret exposure

## 5. Accessibility Testing

Test against WCAG-oriented practices.

### Keyboard

* All controls reachable
* Visible focus
* Logical tab order
* No keyboard traps

### Screen Readers

* Semantic headings
* Accessible labels
* Form descriptions
* Meaningful button names
* Status announcements

### Visual

* Sufficient contrast
* No color-only meaning
* Readable font sizes
* Clear error messages
* Responsive layouts

### Interaction

* Large click targets
* Clear loading states
* Clear success/error states

## 6. AI Testing

Measure:

### Retrieval

* Recall@K
* Precision@K
* Evidence relevance

### Generation

* Grounding
* Completeness
* Hallucination rate

### Citations

* Citation validity
* Citation coverage
* Page/section correctness

### Abstention

Test whether the system refuses to answer when evidence is insufficient.

## 7. Performance Testing

Measure:

* Initial page load
* API response time
* Upload time
* Document processing time
* RAG latency
* AI generation latency
* Comparison latency

## 8. Reliability Testing

Test:

* AI provider timeout
* OCR failure
* Corrupted PDF
* Empty document
* Very large document
* Database unavailable
* Storage unavailable
* Duplicate upload
* Network interruption

## 9. Regression Testing

Every major release should rerun:

```text
Authentication
Upload
Processing
Summary
Q&A
Citation
Comparison
Action Center
Security
Accessibility
```

## 10. Definition of Done

A feature is complete when:

* Functional tests pass
* Security requirements pass
* Accessibility checks pass
* Error states work
* Mobile/responsive behavior works
* No secrets are exposed
* AI output is validated
* Relevant E2E flow passes

## 11. CI Pipeline

Recommended:

```text
Git Push
   ↓
Lint
   ↓
Type Check
   ↓
Unit Tests
   ↓
Backend Tests
   ↓
Security Checks
   ↓
Build
   ↓
E2E Tests
   ↓
Deploy
```

## 12. Hackathon Release Gate

Before submission:

* [ ] Public GitHub repository
* [ ] Working deployed website
* [ ] Demo account or signup works
* [ ] Sample document works
* [ ] AI Q&A works
* [ ] Citations work
* [ ] Comparison works
* [ ] Security controls work
* [ ] Accessibility checked
* [ ] README complete
* [ ] Architecture documented
* [ ] No secrets committed
