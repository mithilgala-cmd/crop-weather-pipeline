FROM python:3.10-slim

# Set workdir
WORKDIR /app

# Copy requirements and install
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy dashboard code
COPY dashboard ./dashboard
COPY models ./models
COPY data ./data

EXPOSE 8501

ENV DUCKDB_PATH=/app/data/crop_weather.duckdb

CMD ["streamlit", "run", "dashboard/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
