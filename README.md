# Discord Game Playtime Tracker

Self-hosted Discord activity and playtime tracker for private communities.

Track game activity your bot can observe in Discord, combine it with historical/manual records, and keep all totals auditable through source records and admin audit logs.

## Table of Contents
- [What It Does](#what-it-does)
- [Quick Install (Recommended)](#quick-install-recommended)
- [Prerequisites](#prerequisites)
- [Discord Bot Setup](#discord-bot-setup)
- [Environment Variables](#environment-variables)
- [First Login](#first-login)
- [Usage: Imports](#usage-imports)
- [Operations](#operations)
- [Technical Reference](#technical-reference)
- [Troubleshooting](#troubleshooting)
- [Privacy and Legal](#privacy-and-legal)

## What It Does
- Tracks Discord observed activity sessions from `playing` presence events
- Shows per-user and per-game playtime totals
- Shows currently active sessions
- Supports historical/manual playtime (for pre-tracker hours)
- Supports manual positive/negative adjustments
- Writes audit log entries for admin changes

Tracker behavior highlights:
- Bot accounts are ignored for tracking and session logging.
- On startup, all non-bot guild members are synchronized (including offline members) so user lists are complete.

Important limitations:
- Discord activity is not an authoritative global playtime source like Steam.
- Historical Discord playtime cannot be reconstructed unless this tracker already captured it.
- Some activity may be hidden or unavailable depending on Discord privacy settings/intents/outages.
- Bot downtime can create missing observed time.
- Missing time is never faked; use manual adjustments for corrections.

## Quick Install (Recommended)
This is the fastest path for most users and pulls public images.

1. Clone and enter project:

```bash
git clone <your-fork-or-repo-url>
cd discord-game-tracker
```

2. Copy environment template and fill required values:

```bash
cp .env.example .env
```

3. Pull and start:

```bash
docker compose pull
docker compose up -d
```

4. Run migrations (safe and idempotent):

```bash
docker compose exec backend alembic upgrade head
```

5. Check health:

```bash
curl -fsS http://localhost:${WEB_PORT}/api/health
```

6. Open dashboard:
- `http://SERVER-IP:${WEB_PORT}`

If you only wanted install steps, you can stop here.

## Prerequisites
- Linux server/VPS (recommended) with Docker Engine + Compose plugin
- Discord bot token and guild ID
- Private access path (for example Tailscale)

## Discord Bot Setup
1. Open Discord Developer Portal.
2. Create a new application.
3. Add a Bot user.
4. Enable intents:
- Server Members Intent
- Presence Intent
5. Invite bot to your guild with minimum needed scope and permission:
- Scope: `bot`
- Permission: `View Channels`

This app does not read messages, DMs, or voice content.

How to find `DISCORD_GUILD_ID`:
1. In Discord, open `User Settings -> Advanced` and enable Developer Mode.
2. Right-click your server icon.
3. Click `Copy Server ID`.

For Discord app verification/profile setup, publish these two files to public URLs (for example GitHub Pages or raw files in your public repository) and paste those URLs into Discord Developer Portal fields:
- Terms of Service URL
- Privacy Policy URL

## Environment Variables
Required for normal operation:
- `DISCORD_BOT_TOKEN`
- `DISCORD_GUILD_ID`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_DB`
- `DATABASE_URL`
- `ADMIN_USERNAME`
- `ADMIN_PASSWORD`
- `SECRET_KEY`
- `WEB_PORT`
- `TIMEZONE`

Optional:
- `STEAM_API_KEY` (required only for Steam profile imports)
- `SESSION_RETENTION_DAYS`
- `RETENTION_CHECK_INTERVAL_MINUTES`
- `CORS_ALLOW_ORIGINS`
- `APP_VERSION`
- `ACCESS_TOKEN_EXPIRE_MINUTES`
- `DOCKERHUB_NAMESPACE` (defaults to `id0ntplaygam3s`)
- `APP_IMAGE_TAG` (defaults to `latest`)

`VITE_GUILD_ID` note:
- Set `VITE_GUILD_ID` to the internal DB guild id (`guilds.id`), not the Discord snowflake.
- If set to `0`, the API falls back to the configured Discord guild's internal id automatically.

How to query it after first start:

```bash
docker compose exec postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "select id, discord_guild_id, name from guilds;"
```

## First Login
On login page:
- `Continue as Guest` gives immediate read-only viewer access.
- `Admin Sign In` uses `ADMIN_USERNAME` and `ADMIN_PASSWORD`.

Admin-only pages are hidden/blocked for viewer sessions.

User cleanup:
- Admins can delete users from the Users page.
- Deleting a user removes associated tracked sessions/manual records/adjustments via database cascade.

## Usage: Imports
### Steam Profile Imports
Steam imports are optional and admin-only.

Configure in `.env`:

```env
STEAM_API_KEY=your_steam_web_api_key
```

Restart backend if changed:

```bash
docker compose up -d
```

Use in UI (`Imports` page):
1. Select Discord user.
2. Enter Steam profile URL, vanity name, or SteamID64.
3. Click `Preview Steam Games`.
4. Review detected games and playtime minutes.
5. Click `Import From Steam`.

Behavior:
- Imported Steam data is stored in `manual_playtime` with source `imported`.
- No fake activity sessions are created.
- Optional replace mode soft-deletes prior Steam imports from the same Steam profile tag before writing new records.

### CSV Imports (Historical Data)
CSV header:

```csv
Discord User,Game,Hours,Minutes,Source,Note
John,Minecraft,1240,0,historical,Existing stats
```

Preferred header for safer matching:

```csv
Discord User ID,Discord User,Game,Hours,Minutes,Source,Note
155149108183695360,John,Minecraft,1240,0,historical,Existing stats
```

When `Discord User ID` is provided, import matching uses Discord IDs first (recommended), then falls back to name matching only when ID is missing.

Flow:
1. Preview
2. Validation report
3. Confirm import
4. Transactional write with audit

## Operations
### Check Services
```bash
docker compose ps
```

### Backups and Restore
Backup:

```bash
docker compose exec postgres pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > backup.sql
```

Restore:

```bash
docker compose exec -T postgres psql -U "$POSTGRES_USER" "$POSTGRES_DB" < backup.sql
```

### Upgrade Procedure
```bash
git pull
docker compose pull
docker compose up -d
docker compose exec backend alembic upgrade head
```

## Technical Reference
### Architecture
- Backend: FastAPI, SQLAlchemy, Alembic, discord.py
- Database: PostgreSQL
- Frontend: React + TypeScript + Vite + Recharts
- Deployment: Docker Compose

### Repository Layout
- `backend/`: API, bot, services, models, migrations, tests
- `frontend/`: Dashboard SPA
- `docker-compose.yml`: default public-image deployment
- `docker-compose.build.yml`: local source build override
- `docker-compose.hub.yml`: optional explicit public-image compose
- `docker-compose.truenas.yml`: TrueNAS-style deployment using `config/.env` and bind-mounted postgres data
- `.env.example`: environment template

### API Summary
- `GET /api/health`
- `POST /api/auth/login`
- `POST /api/auth/guest`
- `GET /api/auth/me`
- `GET /api/system/status`
- `GET /api/stats/overview`
- `GET /api/stats/games`
- `GET /api/stats/users`
- `GET /api/stats/daily`
- `GET /api/stats/weekly`
- `GET /api/stats/monthly`
- `GET /api/activity/recent`
- `GET /api/activity/active`
- `GET /api/users/{user_id}`
- `GET /api/users/{user_id}/games`
- `GET /api/users/{user_id}/sessions`
- `GET /api/games/{game_id}`
- `GET /api/games/{game_id}/users`
- `GET /api/games/{game_id}/sessions`
- `POST /api/management/steam/preview`
- `POST /api/management/steam/import`

OpenAPI docs:
- `/docs`

### Alternative Deployments
Manual build from source:

```bash
docker compose -f docker-compose.yml -f docker-compose.build.yml up -d --build
```

TrueNAS-style deployment:

```bash
docker compose -f docker-compose.truenas.yml --env-file ./config/.env pull
docker compose -f docker-compose.truenas.yml --env-file ./config/.env up -d
```

The TrueNAS compose file expects:
- `./config/.env`
- `./postgres_data` directory for PostgreSQL persistence

Maintainer-only publish flow:

```bash
docker build -t <dockerhub-user>/discord-game-tracker-backend:<tag> ./backend
docker build -t <dockerhub-user>/discord-game-tracker-frontend:<tag> ./frontend
docker push <dockerhub-user>/discord-game-tracker-backend:<tag>
docker push <dockerhub-user>/discord-game-tracker-frontend:<tag>
```

### Tailscale Deployment Model
Recommended access model:
- Linux server
- Docker Compose stack
- Frontend on `WEB_PORT`
- Tailscale private network access

Do not expose PostgreSQL publicly.
Use Tailscale ACLs to restrict dashboard access.

### Development and Tests
Backend tests:

```bash
cd backend
pytest -q
```

Frontend checks:

```bash
cd frontend
npm run lint
npm run build
```

### Release Checklist
- `pytest -q` passes
- `npm run lint` passes
- `npm run build` passes
- `docker compose build` passes
- `docker compose up -d` healthy
- `/api/health` returns OK
- Guest and admin auth flows both work

## Troubleshooting
- `401 login`: verify `ADMIN_USERNAME`/`ADMIN_PASSWORD` and `SECRET_KEY`.
- No live sessions: verify bot intents and Discord activity visibility.
- Steam import fails: verify `STEAM_API_KEY` and profile visibility/identifier.
- Empty dashboard or "Failed to load dashboard data": verify `VITE_GUILD_ID` is the internal DB guild id (query `guilds.id`) and not the Discord server ID. If `VITE_GUILD_ID=0`, the backend auto-resolves to the configured guild.
- Postgres error `could not determine data type of parameter $4`: update backend image to a version that includes typed casts for optional `from/to` filters, then recreate backend.

## Privacy and Legal
Stored:
- Guild ID/name
- Discord user ID/username/display name/avatar URL
- Game names and app IDs
- Session timestamps
- Manual playtime and adjustments
- Audit logs

Not stored:
- Message contents
- DMs
- Voice audio

Legal documents:
- Terms of Service: [TERMS_OF_SERVICE.md](TERMS_OF_SERVICE.md)
- Privacy Policy: [PRIVACY_POLICY.md](PRIVACY_POLICY.md)
