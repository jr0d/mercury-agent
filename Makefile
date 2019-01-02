VIRTUALENV = virtualenv --python=python3.6
VENV = .venv
VENV_ACTIVATE = . $(VENV)/bin/activate

HERE = $(shell pwd)
PIP_CONFIG_FILE ?= $(HERE)/pip.conf
PIP_INSTALL = PIP_CONFIG_FILE="$(PIP_CONFIG_FILE)" pip3 install

TOX = PIP_CONFIG_FILE="$(PIP_CONFIG_FILE)" tox

.DEFAULT_GOAL := help

DOCKERFILE=Dockerfile
IMAGE_NAME=local/mercury-agent
COMPOSE_FILE=docker-compose.yml
PROJECT_NAME=mercury-agent

DC_FLAGS=-f $(COMPOSE_FILE) -p $(PROJECT_NAME)

$(VENV):
	$(VIRTUALENV) $(VENV)

setup: $(VENV) ## Install/upgrade project and development requirements in virtual environment.
	$(VENV_ACTIVATE); $(PIP_INSTALL) -r requirements.txt

setup-tests: $(VENV) ## Install/upgrade test requirements in virtual environment.
	$(VENV_ACTIVATE); $(PIP_INSTALL) -r test-requirements.txt


clean:  ## Removes the virtual environment and tox folder
	rm -rf $(VENV)
	rm -rf .tox

test:  ## Run unit tests
	$(PIP_INSTALL) -U pip
	$(PIP_INSTALL) tox
	$(TOX)

venv: $(VENV) ## Create Python virtual environment.

build: ## Build mercury-agent image
	docker build -t $(IMAGE_NAME) -f $(DOCKERFILE) .

up:  ## Up mercury-agent
	docker-compose $(DC_FLAGS) up -d

down: ## Down mercury-agent
	docker-compose $(DC_FLAGS) down

start: ## Start mercury-agent
	docker-compose $(DC_FLAGS) start

kill: ## Kill mercury-agent
	docker-compose $(DC_FLAGS) kill

logs: ## Tail all logs
	docker-compose $(DC_FLAGS) logs -f

ps: ## docker-compose ps
	docker-compose $(DC_FLAGS) ps

bash: ## open bash shell
	docker-compose $(DC_FLAGS) exec mercury_agent bash

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) |  awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
