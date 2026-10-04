FROM python:3.13-slim
WORKDIR /workspace
COPY apps/api/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY apps/api apps/api
COPY migrations migrations
COPY alembic.ini .
COPY services services
CMD ["python", "-m", "uvicorn", "app.main:app", "--app-dir", "apps/api", "--host", "0.0.0.0", "--port", "8000"]
