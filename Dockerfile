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

FROM python:3.11-slim as svc-intake
WORKDIR /app
ENV PORT=8080
# Set PYTHONPATH so Python can find the 'models' module from the root
ENV PYTHONPATH="/app"

# Copy the virtual environment with all dependencies installed
COPY --from=builder /opt/venv /opt/venv
# Copy the entire application source code
COPY --from=builder /app .

# Activate the venv
ENV PATH="/opt/venv/bin:$PATH"
EXPOSE ${PORT}
CMD exec gunicorn --bind "0.0.0.0:${PORT}" "svc_intake.app:app"


FROM python:3.11-slim as svc-structure-processor
WORKDIR /app
ENV PORT=8080
# Set PYTHONPATH so Python can find the 'models' module from the root
ENV PYTHONPATH="/app"

# Copy the virtual environment with all dependencies installed
COPY --from=builder /opt/venv /opt/venv
# Copy the entire application source code
COPY --from=builder /app .

# Activate the venv
ENV PATH="/opt/venv/bin:$PATH"
EXPOSE ${PORT}
CMD exec gunicorn --bind "0.0.0.0:${PORT}" "svc_structure_processor.app:app"


FROM python:3.11-slim as svc-guardian-processor
WORKDIR /app
ENV PORT=8080
# Set PYTHONPATH so Python can find the 'models' module from the root
ENV PYTHONPATH="/app"

# Copy the virtual environment with all dependencies installed
COPY --from=builder /opt/venv /opt/venv
# Copy the entire application source code
COPY --from=builder /app .

# Activate the venv
ENV PATH="/opt/venv/bin:$PATH"
EXPOSE ${PORT}
CMD exec gunicorn --bind "0.0.0.0:${PORT}" "svc_guardian_processor.app:app"

FROM python:3.11-slim as svc-customer-lookup

RUN apt-get update && apt-get install -y libpq-dev gcc

WORKDIR /app
ENV PORT=8080
# Set PYTHONPATH so Python can find the 'models' module from the root
ENV PYTHONPATH="/app"

# Copy the virtual environment with all dependencies installed
COPY --from=builder /opt/venv /opt/venv
# Copy the entire application source code
COPY --from=builder /app .

# Activate the venv
ENV PATH="/opt/venv/bin:$PATH"
EXPOSE ${PORT}
CMD exec gunicorn --bind "0.0.0.0:${PORT}" "svc_customer_lookup.app:app"


FROM python:3.11-slim as svc-router
WORKDIR /app
ENV PORT=8080
# Set PYTHONPATH so Python can find the 'models' module from the root
ENV PYTHONPATH="/app"

# Copy the virtual environment with all dependencies installed
COPY --from=builder /opt/venv /opt/venv
# Copy the entire application source code
COPY --from=builder /app .

# Activate the venv
ENV PATH="/opt/venv/bin:$PATH"
EXPOSE ${PORT}
CMD exec gunicorn --bind "0.0.0.0:${PORT}" "svc_router.app:app"

FROM python:3.11-slim as svc-finance-responder
WORKDIR /app
ENV PORT=8080
# Set PYTHONPATH so Python can find the 'models' module from the root
ENV PYTHONPATH="/app"

# Copy the virtual environment with all dependencies installed
COPY --from=builder /opt/venv /opt/venv
# Copy the entire application source code
COPY --from=builder /app .

# Activate the venv
ENV PATH="/opt/venv/bin:$PATH"
EXPOSE ${PORT}
# Use gevent worker for better handling of concurrent SSE connections
CMD exec gunicorn --worker-class gevent --workers 1 --timeout 0 --bind "0.0.0.0:${PORT}" "svc_finance_responder.app:app"

FROM python:3.11-slim as ui-observer
WORKDIR /app
ENV PORT=8080
# Set PYTHONPATH so Python can find the 'models' module from the root
ENV PYTHONPATH="/app"

# Copy the virtual environment with all dependencies installed
COPY --from=builder /opt/venv /opt/venv
# Copy the entire application source code
COPY --from=builder /app .

# Activate the venv
ENV PATH="/opt/venv/bin:$PATH"
EXPOSE ${PORT}
CMD exec gunicorn --worker-class gevent --workers 1 --timeout 0 --bind "0.0.0.0:${PORT}" "ui_observer.app:app"


FROM postgres:16.4 as db-customer
COPY --from=builder /app/db_customer/schema.sql /docker-entrypoint-initdb.d/100-schema.sql
COPY --from=builder /app/db_customer/data.sql   /docker-entrypoint-initdb.d/200-data.sql
