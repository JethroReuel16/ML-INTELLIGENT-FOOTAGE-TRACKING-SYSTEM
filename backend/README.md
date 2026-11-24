# ML Footage Tracking System — Backend API

FastAPI service that runs image- and text-guided object searches over uploaded
videos, CCTV/RTSP streams, HTTP video URLs and file shares, and stores the
results, evidence and video sources in PostgreSQL. The ML pipeline lives in
`../ml-engene` and is imported in-process.

## Requirements

- Python 3.14 (tested) — 3.12+ should work
- PostgreSQL 14+ (tested on 18)
- ~4 GB RAM for the CPU models; a CUDA GPU is optional

## Local setup

```bash
cd backend
python -m venv ../.venv && ../.venv/Scripts/activate      # Windows
pip install --extra-index-url https://download.pytorch.org/whl/cpu -r requirements-dev.txt
cp .env.example .env            # then fill in the DB_* values
alembic upgrade head            # create the schema (see "Existing databases")
uvicorn main:app --reload       # http://127.0.0.1:8000  (docs at /docs)
```

The first search downloads the YOLOE weights and DINOv2 (~1 GB) into the
working directory and the Hugging Face cache, so it is slower than later ones.

### Existing databases (created before migrations)

Databases created by hand before Alembic was added already have the full
schema. Mark them as up to date **once**, instead of upgrading:

```bash
alembic stamp 0001
```

After that, `alembic upgrade head` applies future migrations normally.

## Configuration

All settings are environment variables (or `backend/.env`); see
[`.env.example`](.env.example). The important ones for production:

| Variable | Purpose |
| --- | --- |
| `APP_ENV=production` | Secure cookies by default, `/docs` hidden |
| `DATABASE_URL` or `DB_*` | PostgreSQL connection |
| `CORS_ORIGINS` | Exact frontend origin(s), comma-separated |
| `COOKIE_SECURE`, `COOKIE_DOMAIN`, `COOKIE_SAMESITE` | Session cookie |
| `STORAGE_DIR` | Persistent folder for uploads, results and evidence |
| `ALLOWED_SOURCE_ROOTS` | Folders "local"/"network" sources may read (required for file sources in production) |
| `ALLOW_REGISTRATION` | Self sign-up; **off by default in production** |
| `ALLOW_LOOPBACK_SOURCES` | Sources on this machine (127.0.0.1); off by default in production |
| `FORWARDED_ALLOW_IPS` | Docker only: proxy IPs trusted for `X-Forwarded-For` (default `127.0.0.1`) |
| `MAX_VIDEO_UPLOAD_MB` | Upload limit (default 2048) |
| `DETECTOR_DEVICE` | `cpu`, `cuda`, … |

## Accounts

In production self-registration is off. Create and manage investigator
accounts from the server:

```bash
python manage.py create-user --email ana@example.org --name "Ana Phiri"   # prompts for the password
python manage.py list-users
python manage.py set-active --email ana@example.org --inactive            # also signs them out
# Docker:
docker compose exec backend python /app/backend/manage.py create-user --email ... --name ...
```

## Security model

- Every data endpoint is scoped to the signed-in user.
- Video sources: file paths only inside `ALLOWED_SOURCE_ROOTS`; network
  sources may never target cloud-metadata / link-local addresses (redirects
  are re-checked); loopback is refused in production. Private LAN cameras
  are allowed.
- State-changing requests from browser origins outside `CORS_ORIGINS` are
  refused; uploads over the limit are rejected from their declared size.
- Sign-in is throttled per IP + email and takes the same time whether or not
  the account exists.

## API overview

| Method | Path | |
| --- | --- | --- |
| POST | `/api/auth/register`, `/login`, `/logout` · GET `/me` | Cookie sessions (throttled sign-in) |
| POST | `/api/search` | Search an uploaded video (`high_detail=true` finds small objects, ~3× slower) |
| POST | `/api/search/source` · `/multi-source` | Search one / several registered sources |
| GET | `/api/search` | Search history (with the source each search used) |
| GET | `/api/search/{id}` · `/summary` | Result |
| DELETE | `/api/search/{id}` | Delete a search, its evidence and its stored footage |
| GET | `/api/search/{id}/evidence/{file}` | Evidence image |
| GET | `/api/search/{id}/video` | Original footage (HTTP Range supported) |
| GET | `/api/search/multi` · `/multi/{id}` | List / open multi-source searches |
| GET/POST | `/api/sources` · PATCH/DELETE `/api/sources/{id}` · POST `/{id}/test` | Video sources |
| GET | `/health` (liveness) · `/health/ready` (database) | Health checks |

Every data endpoint is scoped to the signed-in user.

## Tests

```bash
pytest
```

The suite runs the real app against PostgreSQL using session-private
temporary tables (`pg_temp`), so it never reads or modifies existing data, and
replaces the ML pipeline with a fast fake. It needs only the normal DB
credentials — no permission to create databases.

## Deployment

### Docker (recommended)

From the repository root:

```bash
cp .env.example .env        # set POSTGRES_PASSWORD and public URLs
docker compose up -d --build
```

The backend container runs `alembic upgrade head` on start, keeps uploads,
results and model weights on the `/data` volume, and runs as a non-root user.
Mount the folder containing footage for "local" sources at `/footage`.

### Bare metal

```bash
APP_ENV=production alembic upgrade head
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1 --proxy-headers
```

Notes for production:

- **Serve over HTTPS** behind a reverse proxy (nginx, Caddy, Traefik) and set
  `COOKIE_SECURE=true`. Serve the frontend and API from the same site (e.g.
  `app.example.org` + `api.example.org` with `COOKIE_DOMAIN=.example.org`).
- **Allow large uploads and long requests** at the proxy: searches are
  synchronous and can take several minutes (`client_max_body_size 2g;
  proxy_read_timeout 900s;` in nginx).
- **Use one worker per process.** Each worker loads the models into memory and
  searches run one at a time per worker; scale out with more containers.
- **Plan disk space.** Every search keeps its footage under
  `STORAGE_DIR/uploads` so it can be replayed in the evidence viewer. Prune old
  folders on a schedule if storage is limited.
