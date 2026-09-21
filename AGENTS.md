# Agent guide

Humanizer Framework is a communication library. Keep the boundary narrow.

## Source of truth

- `docs/REQUIREMENTS.md` defines behavior
- `docs/ARCHITECTURE.md` defines boundaries
- `src/humanizer_framework` is runtime code
- `tests` contains deterministic regression coverage

## Rules

- Do not move product-specific scraping, browser automation or ranking into this repository
- Do not add a giant universal prompt when a small composable policy will work
- Prefer deterministic code for measurable rules
- Keep provider SDKs optional
- Keep voice separate from factual context and business policy
- Keep prompt history and examples bounded
- Add a regression test for every conversation-quality bug that can be stated deterministically
- Do not hardcode fast-moving provider model catalogs

## Checks

```bash
python -m pytest
ruff check .
```
