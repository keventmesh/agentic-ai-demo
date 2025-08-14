# Makefile
ENV_FILE ?= .env

# Reusable check snippet
CHECK_ENV = \
	@if [ ! -f $(ENV_FILE) ]; then \
		echo "❌ $(ENV_FILE) not found. Please create it first."; \
		exit 1; \
	fi

build:
	$(CHECK_ENV)
	@set -a; \
	source $(ENV_FILE); \
	set +a; \
	echo "🚀 Building images..."; \
	skaffold build --default-repo="$$IMAGE_REGISTRY" --tag="$$IMAGE_TAG" --push

render:
	$(CHECK_ENV)
	@set -a; \
	source $(ENV_FILE); \
	set +a; \
	echo "📦 Rendering manifests..."; \
	skaffold render --default-repo="$$IMAGE_REGISTRY" --tag="$$IMAGE_TAG" | envsubst

deploy:
	$(CHECK_ENV)
	@set -a; \
	source $(ENV_FILE); \
	set +a; \
	echo "📦 Deploying manifests..."; \
	skaffold render --default-repo="$$IMAGE_REGISTRY" --tag="$$IMAGE_TAG" | envsubst | kubectl apply -f -

clean:
	@echo "🧹 Cleaning up..."; \
	skaffold delete

.PHONY: build deploy
