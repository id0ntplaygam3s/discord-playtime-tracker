# Discord Game Playtime Tracker

Self-hosted Discord activity and playtime tracker for private communities.

It combines:
- Automatically tracked Discord activity sessions
- Historical/manual playtime entries
- Immutable manual adjustments

Totals are derived from source records and remain auditable.

## Legal Documents
- Terms of Service: [TERMS_OF_SERVICE.md](TERMS_OF_SERVICE.md)
- Privacy Policy: [PRIVACY_POLICY.md](PRIVACY_POLICY.md)

## 1. What This Tracks
- Discord observed activity sessions (`playing` presence events)
- Per-user and per-game playtime totals
- Currently active sessions
- Historical/manual playtime (for pre-tracker hours)
- Manual positive/negative adjustments
- Audit log entries for admin changes

## 2. Important Discord Limitations
- Discord activity is not an authoritative global playtime source like Steam.
- Historical Discord playtime cannot be reconstructed unless this tracker already captured it.
- Some activity may be hidden or unavailable depending on Discord privacy settings/intents/outages.
- Bot downtime can create missing observed time.
- Missing time is never faked; use manual adjustments for corrections.

## 3. Architecture
- Backend: FastAPI, SQLAlchemy, Alembic, discord.py
- Database: PostgreSQL
- Frontend: React + TypeScript + Vite + Recharts
- Deployment: Docker Compose

## 4. Repository Layout
- `backend/`: API, bot, services, models, migrations, tests
- `frontend/`: Dashboard SPA
- `docker-compose.yml`: default public-image deployment
- `docker-compose.build.yml`: local source build override
- `docker-compose.hub.yml`: optional explicit public-image compose
- `docker-compose.truenas.yml`: TrueNAS-style deployment using `config/.env` and bind-mounted postgres data
- `.env.example`: environment template

## 5. Prerequisites
- Linux server/VPS (recommended) with Docker Engine + Compose plugin
- Discord bot token and guild ID
- Private access path (for example Tailscale)

## 6. Discord Bot Setup
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

How to find `VITE_GUILD_ID` for the current dashboard build:
1. Start the stack once so guild data is seeded.
2. Run:

```bash
docker compose exec postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "select id, discord_guild_id, name from guilds;"
```

3. Set `VITE_GUILD_ID` to the `id` column (internal DB id, usually `1` for a first install), not the Discord snowflake.

## 7. Environment Variables
Copy and edit:

```bash
cp .env.example .env
```

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

## 8. Default Self-Host: Pull Public Images (Recommended)
This is the default deployment path.

1. Clone and enter project:

```bash
git clone <your-fork-or-repo-url>
cd discord-game-tracker
```

2. Create `.env` from `.env.example` and fill values.

3. Pull and start:

```bash
docker compose pull
docker compose up -d
```

4. Check service status:

```bash
docker compose ps
```

5. Check health:

```bash
curl -fsS http://localhost:${WEB_PORT}/api/health
```

6. Run migrations (safe and idempotent):

```bash
docker compose exec backend alembic upgrade head
```

7. Open dashboard:
- `http://SERVER-IP:${WEB_PORT}`

### 8.1 TrueNAS-style deployment
If your app data lives under a dataset path and you want `env_file` + host bind mounts, use:

```bash
docker compose -f docker-compose.truenas.yml --env-file ./config/.env pull
docker compose -f docker-compose.truenas.yml --env-file ./config/.env up -d
```

The provided compose file expects:
- `./config/.env`
- `./postgres_data` directory for PostgreSQL persistence

## 9. First Login Flow
On login page:
- `Continue as Guest` gives immediate read-only viewer access.
- `Admin Sign In` uses `ADMIN_USERNAME` and `ADMIN_PASSWORD`.

Admin-only pages are hidden/blocked for viewer sessions.

## 10. Steam Profile Imports
Steam imports are optional and admin-only.

### 10.1 Configure
Set in `.env`:

```env
STEAM_API_KEY=your_steam_web_api_key
```

Restart backend if changed:

```bash
docker compose up -d
```

### 10.2 Use In UI
Go to `Imports` page.
1. Select Discord user.
2. Enter Steam profile URL, vanity name, or SteamID64.
3. Click `Preview Steam Games`.
4. Review detected games and playtime minutes.
5. Click `Import From Steam`.

Behavior:
- Imported Steam data is stored in `manual_playtime` with source `imported`.
- No fake activity sessions are created.
- Optional replace mode soft-deletes prior Steam imports from the same Steam profile tag before writing new records.

## 11. CSV Imports (Historical Data)
CSV header:

```csv
Discord User,Game,Hours,Minutes,Source,Note
John,Minecraft,1240,0,historical,Existing stats
```

Flow:
1. Preview
2. Validation report
3. Confirm import
4. Transactional write with audit

## 12. API Summary
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

## 13. Manual Build From Source (Alternative)
Use this only if you want to build local images from source instead of pulling published images.

```bash
docker compose -f docker-compose.yml -f docker-compose.build.yml up -d --build
```

This keeps the same runtime config but replaces prebuilt images with local builds.

### Maintainer-only: publish to Docker Hub
Publishing images is for maintainers/release automation, not end users.

```bash
docker build -t <dockerhub-user>/discord-game-tracker-backend:<tag> ./backend
docker build -t <dockerhub-user>/discord-game-tracker-frontend:<tag> ./frontend
docker push <dockerhub-user>/discord-game-tracker-backend:<tag>
docker push <dockerhub-user>/discord-game-tracker-frontend:<tag>
```

## 14. Tailscale Deployment Model
Recommended access model:
- Linux server
- Docker Compose stack
- Frontend on `WEB_PORT`
- Tailscale private network access

Do not expose PostgreSQL publicly.
Use Tailscale ACLs to restrict dashboard access.

## 15. Backups and Restore
Backup:

```bash
docker compose exec postgres pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > backup.sql
```

Restore:

```bash
docker compose exec -T postgres psql -U "$POSTGRES_USER" "$POSTGRES_DB" < backup.sql
```

## 16. Upgrade Procedure
```bash
git pull
docker compose pull
docker compose up -d
docker compose exec backend alembic upgrade head
```

For manual source-build deployment:
```bash
docker compose -f docker-compose.yml -f docker-compose.build.yml up -d --build
```

## 17. Development and Tests
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

## 18. Troubleshooting
- `401 login`: verify `ADMIN_USERNAME`/`ADMIN_PASSWORD` and `SECRET_KEY`.
- No live sessions: verify bot intents and Discord activity visibility.
- Steam import fails: verify `STEAM_API_KEY` and profile visibility/identifier.
- Empty dashboard or "Failed to load dashboard data": verify `VITE_GUILD_ID` is the internal DB guild id (query `guilds.id`) and not the Discord server ID.
- Postgres error `could not determine data type of parameter $4`: update backend image to a version that includes typed casts for optional `from/to` filters, then recreate backend.

## 19. Privacy
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

## 20. Release Checklist
- `pytest -q` passes
- `npm run lint` passes
- `npm run build` passes
- `docker compose build` passes
- `docker compose up -d` healthy
- `/api/health` returns OK
- Guest and admin auth flows both work
