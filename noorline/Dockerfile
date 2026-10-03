FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 NOORLINE_ENV=production NOORLINE_DB=/data/server.db
WORKDIR /app
COPY requirements-server.txt .
RUN pip install --no-cache-dir -r requirements-server.txt
COPY noorline ./noorline
COPY policies ./policies
RUN useradd -m app && mkdir -p /data && chown app /data
USER app
# Railway inyecta $PORT. El Volume montado en /data conserva la base SQLite.
CMD ["sh", "-c", "uvicorn --factory noorline.server:create_app --host 0.0.0.0 --port ${PORT:-8000}"]
