# Security Policy

## Reporting a Vulnerability

Security issues must not be reported through public issues.

For the hackathon/MVP phase, report directly to the project maintainers.

When confident the issue is a vulnerability, include:

- A description of the issue
- The affected component and version
- Steps to reproduce
- Suggested impact and any proposed fix

You should receive an acknowledgement within 72 hours.

## Supported Versions

| Version | Status          |
|---------|-----------------|
| main    | Active development (not production) |

## Security Design (summary)

See `docs/05_SECURITY/SECURITY-Architecture.md` for the canonical architecture. Key rules:

- Every data query is scoped to the authenticated user (`document.owner_id == current_user.id`).
- Uploaded files are treated as untrusted: size, MIME and structure validation on upload; document text is only ever used inside the processing pipeline. **Malware scanning is NOT yet implemented** — do not rely on the uploader as an antivirus boundary.
- Document objects are never permanently public; use short-lived signed URLs.
- Secrets never enter the repository; only `.env.example` is committed.
- Logs must not contain legal document content, passwords, tokens, or API keys.
- CORS is restricted to the deployed frontend domain in production.
- AI responses must be source-grounded and citation-validated.

## Reporting an emergency

If the issue involves exposed credentials or a live data breach, contact the maintainers immediately and rotate affected secrets before continuing.