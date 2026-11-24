# ML Footage Tracking System — Frontend

Web console for searching CCTV and video footage for objects using a reference
image, a text description, or both, and reviewing the ranked evidence.

Built with Next.js 16 (App Router), React 19 and Tailwind CSS v4. It talks to
the FastAPI backend in `../backend` using cookie-based sessions.

## Pages

| Route | Purpose |
| --- | --- |
| `/login`, `/register` | Sign in / create an account (public) |
| `/dashboard` | Overview, recent searches, quick actions |
| `/searches/new` | Run a search on an uploaded video, one source or several sources |
| `/searches/results/[id]` | Candidates for one search, plus search and footage details |
| `/searches/evidence/[id]?rank=N` | Evidence viewer: footage player, timeline, scores |
| `/searches/multi-results/[id]` | Combined ranking across several sources |
| `/history` | Every past search, with filtering and sorting |
| `/sources` | Register, test, edit and delete video sources |

Every route except `/login` and `/register` requires a session; the app shell
(`components/AppChrome.tsx`) checks it once and redirects to
`/login?next=…` when it has expired.

## Project layout

```
app/                 Routes (one folder per page)
components/ui.tsx    Shared UI kit: Button, Card, Badge, Field, Alert, Modal, states
components/search.tsx  Search-specific pieces (status badges, score bars, history rows)
components/AppChrome.tsx  App shell, navigation and auth guard (useAuth)
lib/format.ts        Number / time / date formatting
lib/useResource.ts   Data-loading hook with reload and stale-response protection
services/api.ts      Typed client for the backend API
app/globals.css      Design tokens (colours, fonts) exposed as Tailwind utilities
```

Use the design tokens (`bg-surface`, `text-fg`, `text-muted`, `border-line`,
`text-accent`, …) and the UI kit rather than raw Tailwind colours, so the theme
stays consistent.

## Configuration

Copy `.env.example` to `.env.local` and set:

| Variable | Description |
| --- | --- |
| `NEXT_PUBLIC_API_URL` | Backend base URL, e.g. `https://api.example.org`. **Embedded at build time**: rebuild after changing it. |

The backend must list the frontend's origin in its CORS settings. Session
cookies are `SameSite=Lax`, so in production serve the frontend and API from the
same site (for example `app.example.org` + `api.example.org`, or one domain
behind a reverse proxy) over HTTPS.

## Development

```bash
npm install
npm run dev        # http://localhost:3000
npm run lint
npm run build
```

## Production

### Node

```bash
npm ci
NEXT_PUBLIC_API_URL=https://api.example.org npm run build
cp -r public .next/standalone/ && cp -r .next/static .next/standalone/.next/
PORT=3000 node .next/standalone/server.js
```

### Docker

```bash
docker build --build-arg NEXT_PUBLIC_API_URL=https://api.example.org -t mlft-frontend .
docker run -p 3000:3000 mlft-frontend
```
