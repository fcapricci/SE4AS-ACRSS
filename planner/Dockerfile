FROM python:3.11-slim

WORKDIR /app

COPY planner/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY planner/src ./src
COPY handlers ./handlers

ENV PYTHONPATH=/app

CMD ["python", "src/main.py"]
