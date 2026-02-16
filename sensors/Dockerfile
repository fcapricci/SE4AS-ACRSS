FROM python:3.11-slim

WORKDIR /app

COPY sensors/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY sensors/src ./src

CMD ["python", "src/sensors.py"]
