FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
# Verify Jinja2 is available; fail the build early if not present
RUN python - <<'PY'
import importlib, sys
try:
    importlib.import_module('jinja2')
    print('JINJA2_OK')
except Exception as e:
    print('JINJA2_MISSING:', e)
    sys.exit(1)
PY

COPY src ./src
COPY data ./data

EXPOSE 8000

CMD ["uvicorn", "src.rag.server:app", "--host", "0.0.0.0", "--port", "8000"]
