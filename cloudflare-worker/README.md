# Arete Cloudflare Worker (D1 Backend)

This Worker stores session telemetry and serves developer-only player directory and CSV export endpoints.

## Endpoints
- `POST /api/v1/runs`
- `GET /api/v1/dev/players` (admin token required)
- `GET /api/v1/dev/players/:id/runs` (admin token required)
- `GET /api/v1/dev/players/:id/export.csv` (admin token required)
- `GET /health`

## Setup
1. `cd cloudflare-worker`
2. `npm ci`
3. `npx wrangler d1 create arete-telemetry`
4. Copy returned `database_id` into `wrangler.toml` under `[[d1_databases]]`.
5. `npm run d1:migrate`
6. Generate a random token:
   `node -e "console.log(require('crypto').randomBytes(32).toString('base64'))"`
7. `npx wrangler secret put ADMIN_TOKEN` — paste the token. **Save it in your password manager first**; Cloudflare will not show it to you again.
8. Generate a separate client key:
   `node -e "console.log(require('crypto').randomBytes(32).toString('base64'))"`
9. `npx wrangler secret put CLIENT_KEY` — paste the client key. Save this value for the app's `cloud_config.json`.
10. `npm run typecheck`
11. `npm run deploy`
12. `POST /api/v1/runs` is already rate-limited in Worker code through the `RUNS_LIMITER` binding in `wrangler.toml` (default: 30 requests per minute per IP). Adjust that binding if you need a different threshold.

## App Configuration
In `areteDemo/cloud_config.json` (copy from `cloud_config.example.json`):
- `api_base_url`: Worker URL
- `client_key`: same value as the Worker `CLIENT_KEY` secret
- `require_cloud`: set `true` to disable local fallback

The **admin token is not stored in this file.** The app ignores `admin_token` entries in `cloud_config.json`. Developers enter it once through the in-app "Cloud Connection" banner on the Player Directory screen; the app stores it in the OS credential vault (Windows DPAPI / macOS Keychain) so it is never on disk in plaintext or bundled into the distributed `.exe`.

## Production Environment
- `DB`: D1 binding configured in `wrangler.toml`.
- `ADMIN_TOKEN`: Worker secret set with `npx wrangler secret put ADMIN_TOKEN`.
- `CLIENT_KEY`: Worker secret set with `npx wrangler secret put CLIENT_KEY`.
- `database_id`: real D1 database id in `wrangler.toml`.
- `api_base_url`: app config value pointing to the deployed Worker URL.
- `client_key`: app config value matching the Worker `CLIENT_KEY` secret.
- `require_cloud`: app config value; set `true` when sponsor deployments must not save local-only data.
- `timeout_seconds`: optional app config value; defaults to 12 seconds.

## Hardening notes
- Admin and client keys compared in constant time.
- `POST /api/v1/runs` rejects requests if `CLIENT_KEY` is missing or the app does not send the matching `X-Client-Key` header.
- `POST /api/v1/runs` is rate-limited in Worker code to 30 requests per minute per IP by default.
- `POST /api/v1/runs` caps body at 16 KB, validates player emails, and stores only bounded known fields from hit IDs / quiz answers.
- CORS headers are not emitted — the Worker is consumed by a desktop client, not a browser.
- Error messages are generic; real errors go to `console.error` (visible via `wrangler tail` / observability).
