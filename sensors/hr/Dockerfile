FROM python:3.11-slim

WORKDIR /app
COPY hr_sim.py .

RUN pip install paho-mqtt

ENV PYTHONUNBUFFERED=1

CMD ["python","-u", "hr_sim.py"]
