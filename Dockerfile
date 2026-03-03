FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend
COPY backend/ ./backend/

# Copy frontend
COPY frontend/ ./frontend/

# Create static mount
RUN mkdir -p /app/static

WORKDIR /app/backend

# Run with frontend serving
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
