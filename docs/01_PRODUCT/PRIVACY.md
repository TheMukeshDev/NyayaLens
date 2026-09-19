# NyayaLens — Privacy

## 1. Privacy Objective

NyayaLens may process contracts, notices, agreements and other documents containing personal or confidential information.

The product therefore follows a privacy-by-design approach.

## 2. Data Categories

NyayaLens may process:

### Account Data

* Name
* Email
* Authentication information
* Account preferences

### Document Data

* Uploaded files
* Extracted text
* Document metadata
* Sections
* Clauses
* Entities
* Dates
* Financial values

### AI Interaction Data

* Questions
* AI responses
* Citations
* Analysis results

### Technical Data

* IP/security metadata where required
* Request IDs
* Browser/device information where necessary
* Performance metrics

## 3. Data Minimization

Only information necessary to provide the service should be collected.

NyayaLens should avoid collecting unrelated personal information.

## 4. Document Privacy

Uploaded documents should be private by default.

A user's document must not be accessible to another user.

Documents should not be publicly indexed.

Public Supabase Storage buckets must not be used for private legal documents.

## 5. AI Provider Boundary

If external AI services are used, the application should send only the information required for the requested operation.

The exact retention and training policies of each AI provider must be reviewed before production deployment.

NyayaLens should not claim that external providers never retain submitted data unless that is verified from the provider's current terms.

## 6. User Control

Users should be able to:

* View documents
* Delete documents
* Review generated analyses
* Delete conversations where supported
* Manage account settings
* Understand how their data is processed

## 7. Retention

MVP retention policy should be explicit.

Example configurable policy:

```text
Active documents
→ retained until user deletes them

Deleted documents
→ removed from application storage

Temporary processing files
→ automatically removed after processing
```

The actual production retention period must be documented before launch.

## 8. Temporary Files

Temporary files created during:

* OCR
* extraction
* conversion
* report generation

should be deleted after they are no longer required.

## 9. Analytics

Analytics should avoid capturing legal document content.

Do not send full document text to general analytics systems.

Use privacy-conscious event data such as:

```text
document_uploaded
analysis_completed
comparison_created
report_generated
```

## 10. Error Reporting

Error-monitoring systems must be configured to prevent accidental collection of:

* Full legal documents
* Passwords
* Authentication tokens
* API keys
* Private prompts
* Sensitive extracted text

## 11. Privacy UI

The application should provide a visible Privacy/Security page explaining:

* What data is collected
* Why it is processed
* Where it is stored
* How AI is used
* How users delete documents
* Important limitations

## 12. Privacy by Design

Privacy decisions should be considered during architecture rather than after development.

```text
Collect less
      ↓
Store privately
      ↓
Limit access
      ↓
Process only when needed
      ↓
Delete when no longer required
```

## 13. Legal Disclaimer

NyayaLens should clearly communicate:

> NyayaLens provides AI-assisted legal information and document analysis. It is not a lawyer, law firm, legal representative, or substitute for professional legal advice.

Users should be encouraged to consult a qualified legal professional for important decisions.

## 14. Privacy Checklist

* [ ] Documents private by default
* [ ] User ownership enforced
* [ ] Temporary files deleted
* [ ] Logs sanitized
* [ ] External AI data handling reviewed
* [ ] Retention policy documented
* [ ] Delete functionality implemented
* [ ] Privacy page available
* [ ] Analytics minimized
* [ ] Error monitoring sanitized
* [ ] Security controls documented
