# Growth Atlas contribution guide

## Product boundary

- Growth Atlas V2 is a personal decision system, not a therapist and not an autonomous decision maker.
- Preserve user agency: AI output is a reviewable draft until the user confirms it.
- Keep facts, user judgments, assumptions, predictions, and unknowns distinguishable.
- Never expose service-role keys or AI provider keys to the frontend.

## Sources of truth

- Current product direction: `PRODUCT_PIVOT.md`
- MVP acceptance scope: `MVP_SPEC.md`
- Runtime architecture: `ARCHITECTURE.md`
- AI behavior contract: `AI_CONVERSATION.md`
- V2 database contract: `supabase/V2_DATABASE.md` and ordered migrations
- The Word files under `docs/knowledge_base/` are background knowledge. When they disagree with executable code, migrations, or the files above, stop and surface the conflict instead of guessing.

## Working rules

- Inspect `git status` first and preserve unrelated or unfinished work.
- Prefer the smallest change that can be independently verified.
- Database changes are additive migrations; never rewrite an applied migration.
- Keep authorization checks close to data access and maintain user ownership/RLS boundaries.
- Add or update tests for behavior changes. A task is complete only when relevant checks pass.
- Do not call external AI or Supabase services in unit tests; inject or mock boundaries.

## Verification

Run the repository check from the project root:

```powershell
.\scripts\check.ps1
```

For focused work:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check app tests

cd ..\frontend
pnpm run check
```

If the backend virtual environment is missing or broken, recreate it by following `backend/README.md`; do not claim backend verification passed.
