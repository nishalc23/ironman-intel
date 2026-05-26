.PHONY: up down sync logs db-shell build

up:
	docker compose up -d postgres redis
	@echo "Postgres running on :5432 — Redis on :6379"

down:
	docker compose down

build:
	docker compose build ingestion

sync:
	docker compose run --rm ingestion

logs:
	docker compose logs -f

db-shell:
	docker compose exec postgres psql -U ironman -d ironman
