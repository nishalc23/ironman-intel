# Ironman Intel

**Live demo:** https://nishals-macbook-pro.tail396e25.ts.net *(online when my Mac is on)*

A personal Ironman triathlon training platform that syncs Garmin data, tracks gym sessions, and generates daily AI-powered training plans using Claude.

![Stack](https://img.shields.io/badge/stack-FastAPI%20%7C%20React%20%7C%20PostgreSQL%20%7C%20Docker-blue)

## What it does

- **Garmin sync** — pulls swim/bike/run activities from Garmin Connect automatically
- **Training load** — computes CTL (fitness), ATL (fatigue), and TSB (form) using exponential moving averages of daily TSS
- **AI training plan** — Claude reads your actual load numbers and gym history to write a personalized daily plan
- **Gym log** — log strength sessions with sets/reps/weight; import full history from Hevy CSV export
- **Upper/Lower split** — planner knows your split and enforces recovery rules (upper day → bike or run only, lower day → swim only)
- **Mobile access** — runs on your Mac, accessible anywhere via Tailscale

## Stack

| Layer | Tech |
|---|---|
| Frontend | React + Vite + Tailwind |
| Backend | FastAPI (Python) |
| Database | PostgreSQL 16 |
| Cache | Redis |
| AI | Claude Opus (Anthropic API) |
| Garmin | `garminconnect` + `garth` |
| Infra | Docker Compose |
| Mobile | Tailscale |

## Setup

### Prerequisites
- Docker Desktop
- Node.js 18+
- Anthropic API key (console.anthropic.com)
- Garmin Connect account

### 1. Clone and configure

```bash
git clone https://github.com/nishalc23/ironman-intel
cd ironman-intel
cp .env.example .env
```

Edit `.env`:
```
POSTGRES_PASSWORD=your_password
GARMIN_EMAIL=your@email.com
GARMIN_PASSWORD=your_garmin_password
ANTHROPIC_API_KEY=sk-ant-...
```

### 2. Start services

```bash
make up       # start Postgres + Redis
make build    # build API and ingestion images
make api      # start API on :8000
```

### 3. Authenticate with Garmin (one-time)

```bash
make auth
```

This saves OAuth tokens so future syncs never re-login (avoiding Garmin's rate limits).

### 4. Sync Garmin data

```bash
make sync
```

### 5. Import Hevy gym history (optional)

Export your workouts from the Hevy app as CSV, then:

```bash
make import-hevy CSV=/path/to/workouts.csv
```

### 6. Start the frontend

```bash
make install   # npm install (first time only)
make frontend  # starts Vite on :5173
```

Open `http://localhost:5173`

## Mobile access via Tailscale

1. Install Tailscale on your Mac and iPhone
2. Sign in with the same account on both
3. Open `http://<your-mac-tailscale-ip>:5173` on your phone

## Training concepts

**TSS** (Training Stress Score) — single number for workout difficulty. 1 hour at threshold = 100 TSS.

**CTL** (Chronic Training Load) — 42-day exponential moving average of daily TSS. Represents fitness.

**ATL** (Acute Training Load) — 7-day EMA of daily TSS. Represents fatigue.

**TSB** (Training Stress Balance) — CTL minus ATL. Represents form.
- TSB > 5: Fresh, race-ready
- TSB -10 to 5: Normal training
- TSB -10 to -30: Accumulating fatigue
- TSB < -30: Overtraining risk

## Daily workflow

1. Open the dashboard (or on your phone via Tailscale)
2. Toggle "Gym today" on or off
3. Hit **Generate Today's Plan** — Claude reads your CTL/ATL/TSB + last 14 days of training + your full exercise history and writes a plan specific to today
4. After training, log your gym session in the Gym Log section
5. Run `make sync` to pull new Garmin activities

## Makefile commands

```
make up           # start Postgres + Redis
make api          # start API
make build        # rebuild Docker images
make sync         # pull Garmin activities
make auth         # interactive Garmin auth (run once)
make import-hevy  # import Hevy CSV (CSV=/path/to/file)
make frontend     # start Vite dev server
make logs         # tail API logs
make db-shell     # psql into Postgres
make down         # stop everything
```
