# AI Engine Service: FastAPI + LangGraph StateGraph + Vector RAG + MCP
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for PyMuPDF and numerical routines
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code and reference docs
COPY app/ ./app/
COPY scripts/ ./scripts/
COPY company-docs/ ./company-docs/

# Environment configurations
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PORT=8000
ENV HF_HUB_OFFLINE=1

EXPOSE 8000

# Start Uvicorn server
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
