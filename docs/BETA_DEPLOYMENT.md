# Growth Atlas V2 Beta Deployment Runbook

## Release gate

A Beta release is allowed only when all four gates pass:

1. `scripts/check.ps1` passes locally or in CI.
2. Supabase migrations through `202607200004_context_builder_v2.sql` are applied in filename order.
3. The deployed health, readiness, HTTPS, frontend, and CORS checks pass.
4. The two-user RLS check and the full product journey are completed with dedicated Beta test accounts.

## Production environment

Backend variables:

| Variable | Production requirement |
| --- | --- |
| `APP_ENV` | `production` |
| `DEBUG` | `false` |
| `LOG_LEVEL` | `INFO` |
| `CORS_ALLOWED_ORIGINS` | Exact HTTPS frontend origin; no wildcard or localhost |
| `SUPABASE_URL` | HTTPS project URL |
| `SUPABASE_ANON_KEY` | Publishable/anon key; never service role |
| `KIMI_API_KEY` | Secret stored by the hosting platform |
| `KIMI_MODEL` | Tested Moonshot model identifier |
| `KIMI_BASE_URL` | HTTPS Moonshot endpoint |
| `AI_TIMEOUT_SECONDS` | `60` initially |
| `AI_OUTPUT_ATTEMPTS` | `2` initially |

Frontend build variables:

| Variable | Production requirement |
| --- | --- |
| `VITE_API_BASE_URL` | Deployed HTTPS API URL ending in `/api` |
| `VITE_SUPABASE_URL` | HTTPS project URL |
| `VITE_SUPABASE_ANON_KEY` | Publishable/anon key only |

Changing a `VITE_` value requires rebuilding the frontend. Never place Kimi keys, database credentials, or a Supabase service-role key in a `VITE_` variable.

## Deployment sequence

1. Back up the Supabase database and record the current release revision.
2. Apply migrations in filename order. Do not edit an already-applied migration.
3. Deploy the backend with the production variables above.
4. Confirm `/api/health` returns `200` and `/api/ready` returns `200` with `status: ready`. A missing or unsafe production setting makes readiness return `503`.
5. Build and deploy the frontend, with unknown paths/hash routes returning `index.html`.
6. Run:

   ```powershell
   .\scripts\verify_deployment.ps1 -ApiBaseUrl https://api.example.com/api -FrontendUrl https://app.example.com
   ```

7. Use two dedicated test users. Create an episode as user A, then run:

   ```powershell
   .\scripts\verify_rls.ps1 -ApiBaseUrl https://api.example.com/api -OwnerAccessToken <user-a-token> -OtherUserAccessToken <user-b-token> -OwnerEpisodeId <episode-id>
   ```

Tokens are command inputs only. Do not paste them into committed files or CI logs.

## Beta journey acceptance

Run once on desktop and once on a narrow mobile viewport:

- Register a new account and complete email verification.
- Create and confirm the Personal Decision Profile.
- Create a Decision Episode, save background, refresh, and verify restoration.
- Generate an AI Draft. Verify it contains goal, values, facts, uncertainty, constraints, options, risks, opportunity cost, reversibility, and recommendation.
- Edit the draft, confirm the user's final decision, and verify the AI recommendation remains separate.
- Create an Action Plan, update an action, and submit Feedback.
- Create a Memory Candidate, review it, confirm it, disable it, re-enable it, and verify deletion is available.
- Start a future decision and verify its Context Snapshot records the selected profile, confirmed memory, and relevant historical episode.
- Use browser Back/Forward and refresh on detail, review, execution, memory, and Growth Map routes.

Record the release revision, time, test user IDs, model name, and pass/fail result. Never record passwords, access tokens, API keys, draft contents, or personal decision data.

## Logs and incident checks

The backend emits one completion log per request with request ID, method, path, status, and duration. Error responses include the same `X-Request-ID`, while secrets and exception messages are excluded from client responses.

Alert on sustained `5xx`, readiness `503`, increased AI draft failures, and high request duration. Use request IDs to correlate reports. Do not log authorization headers, prompt contents, profile contents, memory contents, or provider keys.

## Rollback

Rollback the application revision first. V1 tables remain available as Legacy and are not deleted by V2 migrations. Database rollback must be a new reviewed migration; do not manually drop V2 tables during an incident. Disable AI draft generation at the deployment layer if the provider is unstable, while preserving existing episodes and drafts.
