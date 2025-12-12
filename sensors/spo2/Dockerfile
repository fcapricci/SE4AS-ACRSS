FROM python:3.11-slim

RUN apt-get update && apt-get install -y iputils-ping

WORKDIR /app
COPY spo2_sim.py .
RUN pip install paho-mqtt

CMD ["python", "-u", "spo2_sim.py"]

