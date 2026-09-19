# NyayaLens — Test Cases

## 1. Authentication

| ID       | Test             | Expected            |
| -------- | ---------------- | ------------------- |
| AUTH-001 | Valid signup     | Account created     |
| AUTH-002 | Duplicate email  | Clear error         |
| AUTH-003 | Invalid email    | Validation error    |
| AUTH-004 | Valid login      | Dashboard opens     |
| AUTH-005 | Invalid password | Access denied       |
| AUTH-006 | Logout           | Session invalidated |

## 2. Authorization

| ID      | Test                                  | Expected       |
| ------- | ------------------------------------- | -------------- |
| SEC-001 | User requests own document            | Allowed        |
| SEC-002 | User requests another user's document | 403/404        |
| SEC-003 | Modify another user's document ID     | Denied         |
| SEC-004 | Retrieve another user's chunks        | No results     |
| SEC-005 | Access private storage URL            | Denied/expired |

## 3. Upload

| ID      | Test                   | Expected             |
| ------- | ---------------------- | -------------------- |
| DOC-001 | Upload valid PDF       | Accepted             |
| DOC-002 | Upload DOCX            | Accepted             |
| DOC-003 | Upload PNG             | Accepted             |
| DOC-004 | Unsupported executable | Rejected             |
| DOC-005 | Oversized file         | Rejected             |
| DOC-006 | Corrupted PDF          | Safe failure         |
| DOC-007 | Malicious file         | Rejected/quarantined |

## 4. Processing

| ID       | Test               | Expected           |
| -------- | ------------------ | ------------------ |
| PROC-001 | Normal PDF         | READY              |
| PROC-002 | Scanned PDF        | OCR executed       |
| PROC-003 | Empty PDF          | Processing failure |
| PROC-004 | Extraction timeout | FAILED + retry     |
| PROC-005 | Duplicate upload   | Safely handled     |

## 5. Summary

| ID      | Test                | Expected             |
| ------- | ------------------- | -------------------- |
| SUM-001 | Normal agreement    | Accurate summary     |
| SUM-002 | Long document       | Structured summary   |
| SUM-003 | Missing information | Explicitly indicated |
| SUM-004 | Ambiguous clause    | Uncertainty retained |

## 6. Clause Extraction

| ID         | Test                   | Expected       |
| ---------- | ---------------------- | -------------- |
| CLAUSE-001 | Termination clause     | Extracted      |
| CLAUSE-002 | Confidentiality clause | Extracted      |
| CLAUSE-003 | Payment clause         | Extracted      |
| CLAUSE-004 | No matching clause     | Not fabricated |

## 7. Q&A

| ID     | Test                      | Expected                  |
| ------ | ------------------------- | ------------------------- |
| QA-001 | Answer exists in document | Grounded answer           |
| QA-002 | Answer absent             | Insufficient evidence     |
| QA-003 | Exact clause question     | Correct citation          |
| QA-004 | Cross-section question    | Multiple valid citations  |
| QA-005 | Unrelated question        | General-information state |

## 8. Citation

| ID      | Test                    | Expected |
| ------- | ----------------------- | -------- |
| CIT-001 | Valid chunk citation    | Accepted |
| CIT-002 | Invalid chunk ID        | Rejected |
| CIT-003 | Wrong document citation | Rejected |
| CIT-004 | Wrong page metadata     | Flagged  |
| CIT-005 | Unauthorized chunk      | Rejected |

## 9. Prompt Injection

| ID     | Test                                | Expected                      |
| ------ | ----------------------------------- | ----------------------------- |
| PI-001 | Document says "ignore instructions" | Ignored                       |
| PI-002 | Document requests system prompt     | Refused                       |
| PI-003 | Document requests secrets           | Refused                       |
| PI-004 | Hidden malicious instruction        | Treated as untrusted text     |
| PI-005 | User attempts prompt extraction     | System instructions protected |

## 10. Comparison

| ID      | Test                   | Expected    |
| ------- | ---------------------- | ----------- |
| CMP-001 | Identical documents    | No changes  |
| CMP-002 | Added clause           | ADDED       |
| CMP-003 | Removed clause         | REMOVED     |
| CMP-004 | Modified clause        | MODIFIED    |
| CMP-005 | Changed financial term | Highlighted |

## 11. Action Center

| ID      | Test                      | Expected                       |
| ------- | ------------------------- | ------------------------------ |
| ACT-001 | Generate checklist        | Checklist created              |
| ACT-002 | Generate lawyer questions | Questions grounded in findings |
| ACT-003 | Missing evidence          | No fabricated action           |
| ACT-004 | High-attention item       | Review recommendation shown    |

## 12. Accessibility

| ID       | Test                 | Expected                  |
| -------- | -------------------- | ------------------------- |
| A11Y-001 | Keyboard navigation  | All controls reachable    |
| A11Y-002 | Focus visibility     | Focus clearly visible     |
| A11Y-003 | Screen reader labels | Meaningful labels         |
| A11Y-004 | Color-only status    | No color-only information |
| A11Y-005 | Form errors          | Clearly announced         |
| A11Y-006 | Mobile viewport      | Fully usable              |
| A11Y-007 | Text scaling         | Content remains usable    |

## 13. Security

| ID      | Test                         | Expected        |
| ------- | ---------------------------- | --------------- |
| SEC-010 | SQL injection payload        | Safely rejected |
| SEC-011 | XSS payload                  | Escaped         |
| SEC-012 | Missing authentication       | 401             |
| SEC-013 | Excessive AI requests        | Rate limited    |
| SEC-014 | Invalid JWT/session          | Denied          |
| SEC-015 | API key search in repository | None found      |

## 14. Reliability

| ID      | Test                 | Expected            |
| ------- | -------------------- | ------------------- |
| REL-001 | AI timeout           | Friendly failure    |
| REL-002 | OCR timeout          | Retry/failure state |
| REL-003 | Database timeout     | Safe error          |
| REL-004 | Storage unavailable  | No data corruption  |
| REL-005 | Network interruption | User can retry      |

## 15. Critical End-to-End Test

### E2E-001 — Complete User Journey

```text
Landing
 ↓
Signup
 ↓
Dashboard
 ↓
Upload Agreement
 ↓
Processing
 ↓
Document Overview
 ↓
Summary
 ↓
Clause Explorer
 ↓
Attention Analysis
 ↓
Ask Question
 ↓
Receive Grounded Answer
 ↓
Open Citation
 ↓
Upload Version 2
 ↓
Compare
 ↓
Generate Action Checklist
 ↓
Generate Professional Questions
 ↓
Export Report
```

Expected result:

The complete workflow succeeds without authorization, citation, accessibility or grounding failures.
