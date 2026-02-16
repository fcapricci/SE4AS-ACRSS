FROM python:3.11-slim

WORKDIR /app

# Copia requirements dal path corretto
COPY analyzer/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copia codice
COPY analyzer/src ./src
COPY analyzer/config ./config

# Copia handlers condiviso
COPY handlers ./handlers

ENV PYTHONPATH=/app

CMD ["python", "src/main.py"]
