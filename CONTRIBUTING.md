# Contributing to ResearchOS

Thank you for improving ResearchOS.

## Before opening a change

1. Keep customer-facing work centered on Mission, Evidence, Human Review, Delivery, and Workspace knowledge.
2. Do not add credentials, local databases, uploaded research files, vector indexes, generated embeddings, or Demo passwords to Git.
3. Preserve Workspace isolation, role boundaries, Evidence-first behavior, and Human Review for consequential decisions.
4. Keep generated data under ignored local storage such as `work/` or the isolated Demo environment.

## Verification

Run the checks appropriate to the change:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -q
node --check frontend/app.js
node --check frontend/service-worker.js
git diff --check
```

## Pull requests

Explain the customer outcome, identify any security or data-boundary impact, and include validation results. Do not mix a product change with an unreviewed corpus, local database, or deployment secret.

## Security reports

Do not disclose security vulnerabilities through public issues. Follow the repository's [security policy](SECURITY.md) instead.
