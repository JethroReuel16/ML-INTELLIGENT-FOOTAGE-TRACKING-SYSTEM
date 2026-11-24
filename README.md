# ML Footage Tracking System

Search CCTV and video footage for objects using a reference image, a text
description, or both — then review ranked evidence at the exact moment each
candidate appears.

| Part | Path | Stack |
| --- | --- | --- |
| Web console | [`frontend/`](frontend/README.md) | Next.js 16, React 19, Tailwind 4 |
| API | [`backend/`](backend/README.md) | FastAPI, SQLAlchemy, Alembic, PostgreSQL |
| ML engine | `ml-engene/` | YOLOE / YOLO11 detection, ByteTrack, DINOv2 similarity |

## Quick start (Docker)

```bash
cp .env.example .env          # set POSTGRES_PASSWORD
docker compose up -d --build
```

- Web console: http://localhost:3000
- Create the first account (self-registration is off in production):
  `docker compose exec backend python /app/backend/manage.py create-user --email you@example.org --name "Your Name"`
- API: http://localhost:8000 (`/health`, `/health/ready`)

The first search downloads model weights (~1 GB) and is slower than later ones.

## Production checklist

1. Put both services behind HTTPS; set `COOKIE_SECURE=true`,
   `PUBLIC_WEB_URL`, `PUBLIC_API_URL` (and `COOKIE_DOMAIN` if they use
   different subdomains).
2. Use a strong `POSTGRES_PASSWORD`; back up the `db-data` volume.
3. Persist and back up the `backend-data` volume (uploads, evidence, models).
4. Raise upload size and read timeouts on the reverse proxy (searches are
   synchronous and can take minutes).
5. Set `ALLOWED_SOURCE_ROOTS` to the folders local video sources may read.

See the component READMEs for local development and configuration details.
