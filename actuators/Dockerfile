FROM python:alpine3.23

WORKDIR /usr/src/app

COPY actuators/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY actuators/src .
COPY handlers/mqtt_handler.py handlers/mqtt_handler.py

CMD [ "python", "main.py" ]