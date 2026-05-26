.PHONY: up down api sync logs db-shell build frontend install

up:
	docker compose up -d postgres redis
	@echo "Postgres :5432 · Redis :6379"

api:
	docker compose up -d api
	@echo "API running at http://localhost:8000"
	@echo "Docs at     http://localhost:8000/docs"

down:
	docker compose down

build:
	docker compose build api ingestion

sync:
	docker compose --profile sync run --rm ingestion

logs:
	docker compose logs -f api

db-shell:
	docker compose exec postgres psql -U ironman -d ironman

import-hevy:
	docker compose run --rm \
		-v "$(CSV):/tmp/workouts.csv" \
		api python scripts/import_hevy_csv.py /tmp/workouts.csv

auth:
	docker compose run --rm -it ingestion python scripts/garmin_auth.py

install:
	cd frontend && npm install

frontend:
	cd frontend && npm run dev
