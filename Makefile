SHELL := /bin/bash

COMPOSE ?= docker compose
INFISICAL ?= infisical
INFISICAL_DOMAIN ?= http://127.0.0.1:8079
export INFISICAL_DOMAIN

INFISICAL_ENV_PROD ?= prod
INFISICAL_ENV_STAGE ?= staging

INFISICAL_PATH_EVA_POSTGRES ?= /eva-postgres
INFISICAL_PATH_EVA_BACKEND ?= /backend-environmet

INFISICAL_PATHS = \
	--path=$(INFISICAL_PATH_EVA_POSTGRES) \
	--path=$(INFISICAL_PATH_EVA_BACKEND)

INFISICAL_RUN_PROD = $(INFISICAL) run --env=$(INFISICAL_ENV_PROD) $(INFISICAL_PATHS) --
INFISICAL_RUN_STAGE = $(INFISICAL) run --env=$(INFISICAL_ENV_STAGE) $(INFISICAL_PATHS) --

COMPOSE_PROD = $(COMPOSE) -f docker-compose.prod.yml
COMPOSE_STAGE = $(COMPOSE) -f docker-compose.stage.yml

.PHONY: start-prod stop-prod build-prod restart-prod logs-prod health-prod \
	prod-secrets-check prod-secrets-upload \
	start-stage stop-stage build-stage restart-stage logs-stage health-stage \
	stage-secrets-check stage-secrets-upload

# --- Production (tetrakomnet, Infisical env=prod) ---

start-prod: prod-secrets-check
	@docker network ls | grep -q tetrakomnet || docker network create tetrakomnet
	$(INFISICAL_RUN_PROD) $(COMPOSE_PROD) up -d --build

stop-prod:
	$(INFISICAL_RUN_PROD) $(COMPOSE_PROD) down

build-prod: prod-secrets-check
	$(INFISICAL_RUN_PROD) $(COMPOSE_PROD) build

restart-prod: stop-prod start-prod

logs-prod:
	$(COMPOSE_PROD) logs -f

health-prod:
	$(COMPOSE_PROD) exec -T eva-backend-prod curl -fsS http://127.0.0.1:8000/health

# --- Stage (tetrakomnet-stage, Infisical env=staging) ---

start-stage:
	@docker network ls | grep -q tetrakomnet-stage || docker network create tetrakomnet-stage
	$(INFISICAL_RUN_STAGE) $(COMPOSE_STAGE) up -d --build

stop-stage:
	$(INFISICAL_RUN_STAGE) $(COMPOSE_STAGE) down

build-stage: stage-secrets-check
	$(INFISICAL_RUN_STAGE) $(COMPOSE_STAGE) build

restart-stage: stop-stage start-stage

logs-stage:
	$(COMPOSE_STAGE) logs -f

health-stage:
	$(COMPOSE_STAGE) exec -T eva-backend-stage curl -fsS http://127.0.0.1:8000/health
