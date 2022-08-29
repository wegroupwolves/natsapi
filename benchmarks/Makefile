##---------- Preliminaries ----------------------------------------------------
.POSIX:     # Get reliable POSIX behaviour
.SUFFIXES:  # Clear built-in inference rules

##---------- Variables --------------------------------------------------------
PREFIX = /usr/local  # Default installation directory

##---------- Build targets ----------------------------------------------------

help: ## Show this help message (default)
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

frontend-gateway: ## Run the frontend gateway
	poetry run uvicorn frontend-gateway:app --no-access-log --workers 1 --port 5000

backend-rest: ## Run the backend rest service
	poetry run uvicorn backend-rest:app --no-access-log --workers 1 --port 5001

backend-nats: ## Run the backend nats service
	poetry run python backend-nats.py

bench-rest: ## Run benchmarks for the rest to rest connection
	ab -n 1000 -c 100 http://localhost:5000/rest/index
	ab -p input.json -T application/json -c 100 -n 1000 http://localhost:5000/rest/sum

bench-nats: ## Run benchmarks for the nats to nats connection
	ab -n 1000 -c 100 http://localhost:5000/nats/index
	ab -p input.json -T application/json -c 100 -n 1000 http://localhost:5000/nats/sum

# cursor: 15 del
