FROM python:3.12-slim

WORKDIR /app
COPY README.md README.md
COPY backend/pyproject.toml backend/pyproject.toml
COPY backend/src backend/src
COPY backend/alembic.ini backend/alembic.ini
COPY backend/alembic backend/alembic

RUN pip install --no-cache-dir "./backend"

CMD ["uvicorn", "ledgermap.main:app", "--host", "0.0.0.0", "--port", "8000"]