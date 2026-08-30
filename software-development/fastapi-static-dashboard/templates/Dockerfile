# Dockerfile — FastAPI production image
FROM python:3.13-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e ".[dev]"

# Copy application code
COPY src/ ./src/
COPY ui/ ./ui/
COPY domains/ ./domains/

# Set PYTHONPATH so 'src' is importable inside the container
ENV PYTHONPATH=/app
ENV PORT=8000

EXPOSE 8000

CMD ["python3", "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
