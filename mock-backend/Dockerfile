FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    fastapi==0.115.12 \
    "uvicorn[standard]==0.34.2" \
    prometheus-client==0.21.1 \
    pydantic==2.11.4

COPY mock_app /app/mock_app

EXPOSE 8000

CMD ["uvicorn", "mock_app.main:app", "--host", "0.0.0.0", "--port", "8000"]
