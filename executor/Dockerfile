FROM python:alpine3.23

WORKDIR /usr/src/app

COPY executor/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY executor/src .
COPY handlers/mqtt_handler.py handlers/mqtt_handler.py

CMD ["python", "main.py"]