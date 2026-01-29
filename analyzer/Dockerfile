FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY analyzer.py .
COPY mqtt_handler.py .
COPY influx_handler.py .
COPY main.py .
CMD ["python", "main.py"]
