FROM python:3.11-slim

WORKDIR /app

COPY managed_resources/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY handlers ./handlers


COPY managed_resources/actuators ./actuators

COPY managed_resources .

ENV PYTHONPATH=/app

CMD ["python", "main.py"]
