##---------- Preliminaries ----------------------------------------------------
.POSIX:     # Get reliable POSIX behaviour
.SUFFIXES:  # Clear built-in inference rules

##---------- Variables --------------------------------------------------------
PREFIX = /usr/local  # Default installation directory
PYTEST_GENERAL_FLAGS := -vvvx --asyncio-mode=auto

##---------- Build targets ----------------------------------------------------

help: ## Show this help message (default)
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

test: ## Run tests
	poetry run coverage run --source=natsapi -m pytest $(PYTEST_GENERAL_FLAGS)
	poetry run coverage report -m --fail-under=85

testr: ## Run tests with entr
	find natsapi tests | entr -r poetry run pytest --disable-warnings -vvvx

lint: ## Lint checks
	poetry run ruff check .

format: ## Format checks
	poetry run black .

style: ## Style checks
	poetry run black --check .

static-check: ## Static code check
	semgrep -v --error --config=p/ci /drone/src

security: ## Run security check
	poetry export -f requirements.txt --without-hashes | sed 's/; .*//' > /tmp/req.txt
	sed -i '/^typing-extensions/d' /tmp/req.txt
	sed -i '/^anyio/d' /tmp/req.txt
	poetry run safety check -r /tmp/req.txt
	poetry run bandit -lll -r .
	poetry run vulture . --min-confidence 95

ci: lint format security test ## Run all
