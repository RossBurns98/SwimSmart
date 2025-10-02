# Dockerfile
FROM python:3.12-slim

# system deps for psycopg2 (client libs)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# safer defaults
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# workdir
WORKDIR /app

# copy project
COPY . /app

# install your package in editable mode (uses pyproject.toml)
RUN pip install -e .

# expose API port
EXPOSE 8000

# uvicorn entry
CMD ["uvicorn", "swimsmart.api.main:create_app", "--host", "0.0.0.0", "--port", "8000", "--factory"]
