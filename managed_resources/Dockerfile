FROM python:alpine3.23

WORKDIR /usr/src/app

COPY managed_resources/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY managed_resources/src .
COPY models/therapy.py models/therapy.py
COPY handlers/mqtt_handler.py handlers/mqtt_handler.py

CMD ["python", "main.py"]