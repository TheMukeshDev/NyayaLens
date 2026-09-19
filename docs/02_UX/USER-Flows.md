# NyayaLens — User Flows

---

# 1. Global Flow

```text
Landing Page
     ↓
Signup / Login
     ↓
Dashboard
     ↓
Upload Document
     ↓
Processing
     ↓
Document Overview
     ↓
┌─────────────┬─────────────┬──────────────┐
│   Summary   │   Clauses   │   Attention  │
└─────────────┴─────────────┴──────────────┘
                     ↓
                    Ask
                     ↓
                  Citation
                     ↓
                 Compare
                     ↓
                Action Center
                     ↓
                   Report
```

---

# 2. New User Flow

```text
Landing
 ↓
View Product Value
 ↓
Create Account
 ↓
Dashboard
 ↓
Upload First Document
```

The first-use experience should minimize unnecessary configuration.

---

# 3. Login Flow

```text
Login
 ↓
Enter Email
 ↓
Enter Password
 ↓
Validate
 ├── Invalid → Error
 └── Valid → Dashboard
```

---

# 4. Upload Flow

```text
Upload Page
 ↓
Select File
 ↓
Client Validation
 ↓
Upload
 ↓
Server Validation
 ↓
Malware Scan
 ↓
Private Storage
 ↓
Create Processing Job
 ↓
Processing Screen
```

---

# 5. Processing Flow

```text
PROCESSING

Validating
   ↓
Extracting text
   ↓
Detecting sections
   ↓
Detecting clauses
   ↓
Creating chunks
   ↓
Generating embeddings
   ↓
Running analysis
   ↓
READY
```

If processing fails:

```text
FAILED
 ↓
Explain Problem
 ↓
Retry
```

---

# 6. Document Overview Flow

After processing:

```text
Document Overview
        ↓
┌──────────────────────────────┐
│ Summary                      │
│ Key Terms                    │
│ Attention Items              │
│ Clause Explorer              │
│ Ask AI                       │
│ Compare                      │
│ Action Center                │
└──────────────────────────────┘
```

---

# 7. Summary Flow

```text
Document
 ↓
Summary
 ↓
Key Information
 ↓
Important Clauses
 ↓
Attention Items
```

---

# 8. Clause Explorer Flow

```text
Clause Explorer
 ↓
Search / Filter
 ↓
Select Clause
 ↓
Original Text
 ↓
Plain-Language Explanation
 ↓
Source Page
```

---

# 9. Attention Flow

```text
Attention Analysis
 ↓
List Attention Items
 ↓
Select Item
 ↓
Explanation
 ↓
Source Clause
 ↓
Suggested Next Step
```

Example:

```text
HIGH ATTENTION
Termination Notice

The agreement specifies a 90-day notice period.

Source:
Section 8
Page 6

Suggested next step:
Confirm whether this period applies during probation.
```

---

# 10. Q&A Flow

```text
Ask Question
 ↓
Authenticate User
 ↓
Identify Document
 ↓
Embed Query
 ↓
Retrieve Relevant Chunks
 ↓
Filter by User + Document
 ↓
Build Evidence Context
 ↓
LLM
 ↓
Validate Answer
 ↓
Validate Citations
 ↓
Return Answer
```

---

# 11. Insufficient Evidence Flow

```text
User Question
 ↓
Retrieval
 ↓
Evidence insufficient
 ↓
Do NOT fabricate answer
 ↓
Explain limitation
 ↓
Suggest relevant document sections
```

Example:

```text
I couldn't find enough information in this document
to answer that confidently.

You may want to review Sections 7 and 8
or discuss this question with a qualified professional.
```

---

# 12. Comparison Flow

```text
Compare
 ↓
Select Document A
 ↓
Select Document B
 ↓
Start Comparison
 ↓
Section Matching
 ↓
Clause Matching
 ↓
Change Detection
 ↓
Importance Classification
 ↓
Comparison Results
```

Results:

```text
Added
Removed
Modified
Unchanged
```

---

# 13. Action Center Flow

```text
Analysis
 ↓
Attention Items
 ↓
Generate Actions
 ↓
Review Actions
 ↓
Mark TODO
 ↓
IN PROGRESS
 ↓
COMPLETED
```

---

# 14. Professional Question Flow

```text
Attention Item
 ↓
Generate Question
 ↓
Review Question
 ↓
Save
 ↓
Use in Professional Consultation
```

---

# 15. Report Flow

```text
Document
 ↓
Generate Report
 ↓
Collect Analysis
 ↓
Collect Attention Items
 ↓
Collect Citations
 ↓
Collect Actions
 ↓
Generate PDF
 ↓
Private Storage
 ↓
Download/View
```

---

# 16. Delete Document Flow

```text
Document
 ↓
Delete
 ↓
Confirmation
 ↓
Soft Delete
 ↓
Cleanup Job
 ↓
Remove Stored File
 ↓
Remove Derived Data
```

---

# 17. Error Flow

All major errors should follow:

```text
Error
 ↓
Explain Clearly
 ↓
Provide Next Action
```

Never expose:

* Stack traces
* SQL errors
* Server paths
* Internal model prompts
* API credentials

---

# 18. Critical Demo Flow

For the PromptWars demonstration:

```text
Landing
 ↓
Login
 ↓
Dashboard
 ↓
Upload Employment Agreement V1
 ↓
Processing
 ↓
Summary
 ↓
Clause Explorer
 ↓
Attention Analysis
 ↓
Ask:
"What happens if I leave the company?"
 ↓
Grounded Answer
 ↓
Citation → Section 8 / Page 6
 ↓
Upload Employment Agreement V2
 ↓
Compare
 ↓
Notice Period:
30 days → 90 days
 ↓
Action Center
 ↓
Generate Professional Questions
```

This is the primary end-to-end product demonstration.

---

# 19. Navigation Model

Persistent authenticated navigation:

```text
Dashboard
Documents
Compare
Actions
Reports
Settings
Privacy
```

Document-specific navigation:

```text
Overview
Summary
Clauses
Attention
Ask
Actions
```

---

# 20. Mobile Web Flow

NyayaLens is a website, but the interface must remain responsive.

On small screens:

```text
Sidebar
 ↓
Collapsible Navigation
```

Complex document views should use:

* Stacked sections
* Horizontal scrolling only where necessary
* Responsive tables/cards
* Large touch targets

No native mobile application is required for MVP.
