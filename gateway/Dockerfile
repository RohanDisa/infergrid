FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    fastapi==0.115.12 \
    "uvicorn[standard]==0.34.2" \
    httpx==0.28.1 \
    pydantic==2.11.4 \
    pydantic-settings==2.9.1 \
    prometheus-client==0.21.1 \
    pyyaml==6.0.2

COPY app /app/app

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
