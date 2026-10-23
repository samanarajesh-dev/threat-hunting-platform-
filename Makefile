.PHONY: up down logs seed test fmt
up:        ## build and start everything
	docker compose up -d --build
down:
	docker compose down
logs:
	docker compose logs -f backend
seed:      ## load demo events + watchlist, then retro-hunt so the dashboard fills up
	docker compose exec backend python -m scripts.seed_data
test:      ## backend unit tests (no Docker needed)
	cd backend && python -m venv .venv && . .venv/bin/activate && pip install -q -r requirements-dev.txt && python -m pytest -q
