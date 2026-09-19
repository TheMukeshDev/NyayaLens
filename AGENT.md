# NyayaLens Agent Rules

## 1. Canonical Project Root

The repository root is the only canonical project root.

Never create another NyayaLens project inside the repository.

Never create:
- nyayalens/nyayalens/
- frontend/frontend/
- backend/backend/
- docs/docs/

## 2. Documentation First

Before implementing a feature, inspect the relevant files under docs/.

Documentation is the source of truth.

Do not invent requirements.

## 3. No Repeated Autonomous Loops

Never repeatedly modify the same file in an uncontrolled
build -> error -> edit -> build loop.

After two failed attempts:
STOP.

Report:
- command executed
- exact error
- affected file
- likely cause
- proposed fix

Wait for approval if the root cause is architectural,
environmental, dependency-related, or ambiguous.

## 4. No Duplicate Implementations

Before creating a file, search the repository for an existing
file serving the same purpose.

Do not create duplicate:
- models
- APIs
- services
- components
- configuration
- database migrations

## 5. No Fake Implementations

Do not create fake AI responses,
mock production behavior,
hardcoded legal answers,
fake citations,
or fake database results unless explicitly requested
for testing.

## 6. Website Only

NyayaLens is a web application.

Stack:
- Next.js
- React
- TypeScript
- Tailwind CSS
- FastAPI
- PostgreSQL
- pgvector

Do not introduce Flutter,
React Native,
mobile applications,
or unrelated frameworks.

## 7. Database Safety

Never delete or recreate the database automatically.

Never delete PostgreSQL data directories automatically.

Never run destructive migrations without explicit approval.

## 8. Verification

After each implementation step:

1. Run the smallest relevant validation.
2. Report the result.
3. Fix only the identified issue.
4. Do not continue to unrelated phases.

## 9. Stop Conditions

STOP and ask for approval when:

- duplicate project roots are discovered
- architecture conflicts exist
- documentation conflicts exist
- database configuration is ambiguous
- multiple implementations exist
- destructive cleanup is required
- credentials/secrets are encountered
- build errors cannot be confidently explained