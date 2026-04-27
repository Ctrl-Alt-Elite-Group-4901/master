# Arete

Arete is a packaged Kivy game where players run through a side-scrolling jumper experience, answer reflection questions, and optionally sync completed run data to a Cloudflare D1 backend for sponsor/developer review.

## For Players

The intended way to run the project is simple:

1. Open the packaged `Arete` folder.
2. Double-click `Arete.exe`.
3. Play the game.

Do not move `Arete.exe` out of its folder. The app expects its bundled files, images, and optional cloud config to stay next to it. The local `arete.db` file is created automatically on first launch and should not be included in Git or in a fresh release zip.

Fresh installs start with the built-in default reflection questions. If an authorized owner later changes questions in developer mode, the app saves those edits locally on that device for future runs.

If cloud sync is enabled, the release folder should include:

```text
Arete/
  Arete.exe
  cloud_config.json
  _internal/
```

The `cloud_config.json` file is not committed to Git because it can contain the run-upload client key.

## For Developers

Use these steps only if you are running from source or rebuilding the packaged app.

### Run From Source

1. Open PowerShell.
2. Go to the source app folder:
   ```powershell
   cd <your-clone>/areteDemo
   ```
3. Install dependencies:
   ```powershell
   python -m pip install -r requirements.txt
   ```
4. Start the app:
   ```powershell
   python main.py
   ```

### Build The Exe

From the `areteDemo` folder:

```powershell
pyinstaller areteDemo.spec
```

Or run the Windows build helper, which installs pinned requirements before packaging:

```powershell
.\build.bat
```

PyInstaller recreates `dist/Arete`. After the build finishes, copy the real cloud config into the built folder if cloud sync is needed:

```powershell
Copy-Item .\cloud_config.json .\dist\Arete\cloud_config.json
```

Then distribute the full folder:

```text
areteDemo/dist/Arete/
```

Do not copy `arete.db` into the release folder. The app creates a clean local database when the player first runs it.

### Release Packaging Checklist

- Include `Arete.exe`, `_internal/`, and `cloud_config.json` only when cloud sync is enabled.
- Do not include `arete.db`, `exports/`, `build/`, `__pycache__/`, `reflection_questions.local.json`, or local log files.
- Use a fresh `cloud_config.json` copied from `cloud_config.example.json`; never add `admin_token`.
- Build from pinned Python requirements and use the checked-in `cloudflare-worker/package-lock.json` for Worker installs.

## Cloud Backend

The Cloudflare Worker backend stores completed run telemetry in D1 and supports developer-only player directory, run history, and CSV export.

Endpoints:

- `POST /api/v1/runs`
- `GET /api/v1/dev/players`
- `GET /api/v1/dev/players/:id/runs`
- `GET /api/v1/dev/players/:id/export.csv`

### Deploy Worker

1. Install Node.js 20+.
2. In terminal:
   ```powershell
   cd cloudflare-worker
   npm ci
   ```
3. Create the D1 database:
   ```powershell
   npx wrangler d1 create arete-telemetry
   ```
4. Copy the returned `database_id` into `cloudflare-worker/wrangler.toml`.
5. Apply the schema:
   ```powershell
   npm run d1:migrate
   ```
6. Generate and save an admin token:
   ```powershell
   node -e "console.log(require('crypto').randomBytes(32).toString('base64'))"
   npx wrangler secret put ADMIN_TOKEN
   ```
7. Generate and save a separate client key:
   ```powershell
   node -e "console.log(require('crypto').randomBytes(32).toString('base64'))"
   npx wrangler secret put CLIENT_KEY
   ```
8. Deploy:
   ```powershell
   npm run typecheck
   npm run deploy
   ```
9. `POST /api/v1/runs` is already rate-limited in Worker code through the `RUNS_LIMITER` binding in `cloudflare-worker/wrangler.toml` (default: 30 requests per minute per IP). Adjust that binding if you need a different threshold.

### App Cloud Config

Copy `areteDemo/cloud_config.example.json` to `areteDemo/cloud_config.json` and fill in:

- `api_base_url`: deployed Worker URL
- `client_key`: same value as the Worker `CLIENT_KEY` secret
- `require_cloud`: `true` to fail instead of saving locally when cloud upload is unavailable

Do not put the admin token in `cloud_config.json`. The app ignores `admin_token` entries in this file; developers enter the token in-app through the Player Directory cloud connection banner.

### Production Environment Checklist

Cloudflare Worker production values:

- `DB`: D1 binding configured by `wrangler.toml`.
- `ADMIN_TOKEN`: Worker secret set with `npx wrangler secret put ADMIN_TOKEN`.
- `CLIENT_KEY`: Worker secret set with `npx wrangler secret put CLIENT_KEY`.
- `database_id`: real D1 database id in `cloudflare-worker/wrangler.toml`.
- `RUNS_LIMITER`: built-in Worker rate limit binding for `POST /api/v1/runs` (default: 30 requests per minute per IP).

Desktop app cloud config and optional env overrides:

- `api_base_url` or `ARETE_API_BASE_URL`: deployed Worker URL.
- `client_key` or `ARETE_API_CLIENT_KEY`: same value as the Worker `CLIENT_KEY` secret.
- `require_cloud` or `ARETE_API_REQUIRE_CLOUD`: use `true` for sponsor deployments that must not silently fall back to local-only storage.
- `timeout_seconds` or `ARETE_API_TIMEOUT_SECONDS`: optional request timeout; defaults to 12 seconds.
- `ARETE_API_ADMIN_TOKEN`: optional developer-only fallback. Preferred production flow is entering the admin token in-app so it is stored in the OS credential vault.

## Developer Mode

Developer mode is entered from the login screen using a blank email and the configured developer password.

Developer mode can:

- open the Player Directory
- connect to the cloud backend using the admin token
- view cloud player runs
- export cloud CSV reports

The Player Directory is cloud-only. It does not read local SQLite player data.
Reflection-question edits are local-only: a fresh install starts from the built-in defaults, and later editor saves affect only future runs on that same device.
