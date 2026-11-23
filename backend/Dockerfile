FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-eng tesseract-ocr-kan fonts-noto-core fonts-dejavu-core poppler-utils libglib2.0-0 libgl1 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
COPY backend/requirements-lock.txt backend/requirements-lock.txt
RUN pip install --no-cache-dir -r backend/requirements.txt -c backend/requirements-lock.txt
COPY backend backend
COPY docs docs
ENV PYTHONPATH=/app/backend DATA_DIR=/app/data
RUN useradd --uid 10001 --create-home formflow && mkdir -p /app/data && chown -R formflow:formflow /app
USER formflow
CMD ["sh", "-c", "alembic -c backend/alembic.ini upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --no-access-log"]
