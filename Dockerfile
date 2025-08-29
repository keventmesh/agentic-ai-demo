FROM python:3.11-slim AS builder

RUN apt-get update && apt-get install -y libpq-dev gcc

# Set the working directory
WORKDIR /app

# Create a single, shared virtual environment
RUN python -m venv /opt/venv

# Activate the venv for subsequent RUN commands
ENV PATH="/opt/venv/bin:$PATH"

# Copy the file that defines the project and its dependencies
COPY pyproject.toml .

# Install all dependencies from pyproject.toml into the venv
RUN pip install --no-cache-dir .

# Copy the rest of the source code
COPY . .

# --- Final Image Targets ---

# --- Base image for all Python services ---
FROM python:3.11-slim as python-service-base
WORKDIR /app
ENV PORT=8080
# Set PYTHONPATH so Python can find the 'models' module from the root
ENV PYTHONPATH="/app"

# Create a non-root user and group
# The UID 1001 is a common choice for non-root users in OpenShift
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid 1001 --shell /bin/bash --create-home appuser

# Copy the virtual environment with all dependencies installed
COPY --from=builder /opt/venv /opt/venv
# Copy the entire application source code
COPY --from=builder /app .

# Change ownership of the app directory and venv to the new non-root user
RUN chown -R appuser:appgroup /app && \
    chown -R appuser:appgroup /opt/venv

# Activate the venv
ENV PATH="/opt/venv/bin:$PATH"

# Switch to the non-root user
USER 1001

EXPOSE ${PORT}


# --- Service-specific final stages ---

FROM python-service-base as svc-intake
CMD exec  gunicorn --bind "0.0.0.0:${PORT}" "svc_intake.app:app"

FROM python-service-base as svc-structure-processor
CMD exec gunicorn --bind "0.0.0.0:${PORT}" "svc_structure_processor.app:app"

FROM python-service-base as svc-guardian-processor
CMD exec gunicorn --bind "0.0.0.0:${PORT}" "svc_guardian_processor.app:app"

FROM python-service-base as svc-customer-lookup
# This service needs libpq-dev for psycopg2, install it before changing user
USER root
RUN apt-get update && apt-get install -y libpq-dev && rm -rf /var/lib/apt/lists/*
USER 1001
CMD exec gunicorn --bind "0.0.0.0:${PORT}" "svc_customer_lookup.app:app"

FROM python-service-base as svc-router
CMD exec gunicorn --bind "0.0.0.0:${PORT}" "svc_router.app:app"

FROM python-service-base as svc-finance-responder
CMD exec gunicorn --worker-class gevent --workers 1 --timeout 0 --bind "0.0.0.0:${PORT}" "svc_finance_responder.app:app"

FROM python-service-base as ui-observer
CMD exec gunicorn --worker-class gevent --workers 1 --timeout 0 --bind "0.0.0.0:${PORT}" "ui_observer.app:app"

# The Postgres image
FROM postgres:16.4 as db-customer
COPY --from=builder /app/db_customer/schema.sql /docker-entrypoint-initdb.d/100-schema.sql
COPY --from=builder /app/db_customer/data.sql   /docker-entrypoint-initdb.d/200-data.sql
