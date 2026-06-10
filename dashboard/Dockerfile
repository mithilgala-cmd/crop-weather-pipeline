FROM python:3.10-slim

# Set workdir
WORKDIR /app

# Copy requirements and install
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy source folders
COPY dashboard ./dashboard
COPY backend ./backend
COPY frontend ./frontend
COPY models ./models
COPY scripts ./scripts
COPY db ./db
COPY data ./data

EXPOSE 8000

ENV DUCKDB_PATH=/app/data/crop_weather.duckdb

# Run the FastAPI server via uvicorn
CMD ["python", "-m", "uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
