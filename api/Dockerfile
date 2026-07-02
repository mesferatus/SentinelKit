FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN addgroup --system sentinelkit \
    && adduser --system --ingroup sentinelkit sentinelkit

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=sentinelkit:sentinelkit . .

USER sentinelkit

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
