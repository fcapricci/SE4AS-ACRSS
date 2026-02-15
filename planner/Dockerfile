FROM python:3.11-slim

WORKDIR /usr/src/app

COPY planner/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY planner/src .

COPY handlers/mqtt_handler.py handlers/mqtt_handler.py

CMD ["python", "main.py"]