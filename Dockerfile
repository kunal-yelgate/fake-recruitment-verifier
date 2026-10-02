FROM python:3.12-slim
WORKDIR /app/backend
COPY backend/requirements.txt requirements.txt
COPY backend/requirements.lock requirements.lock
RUN pip install --no-cache-dir --require-hashes --only-binary=:all: -r requirements.lock
COPY backend .
RUN useradd --create-home --uid 10001 app && chown -R app:app /app/backend
USER app
EXPOSE 8000
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port \"${PORT:-8000}\""]
