FROM python:3.11-slim AS builder

# Set the working directory
WORKDIR /app

# Create a single, shared virtual environment
RUN python -m venv /opt/venv

# Activate the venv for subsequent RUN commands
ENV PATH="/opt/venv/bin:$PATH"

# Copy and install all common dependencies into the shared venv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire source code for all services
COPY . .

# --- Final Image Targets ---

FROM python:3.11-slim as svc-intake

WORKDIR /app
ENV PORT=8080

# Copy the shared virtual environment from the builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy the source code for ONLY the svc-intake
COPY --from=builder /app/svc-intake/ .

# Activate the venv in the final image so the CMD can find gunicorn
ENV PATH="/opt/venv/bin:$PATH"

EXPOSE ${PORT}
CMD ["gunicorn", "--bind", "0.0.0.0:${PORT}", "app:app"]
