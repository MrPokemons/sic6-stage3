FROM python:3.11-slim AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc

COPY requirements.txt .

RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt


FROM python:3.11-slim AS production

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc && \
    apt-get install libgomp1

COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt .

RUN pip install --no-cache /wheels/* && \
    rm -rf /wheels

COPY . .

EXPOSE 80

CMD ["python", "app.py"]
