FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV VIRTUAL_ENV=/opt/venv

WORKDIR /app

RUN apt-get update \
  && apt-get install -y --no-install-recommends build-essential \
  && python -m venv "${VIRTUAL_ENV}" \
  && rm -rf /var/lib/apt/lists/*

ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"

COPY pyproject.toml ./
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./

RUN pip install --upgrade pip \
  && pip install .

FROM python:3.12-slim AS runner

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"

WORKDIR /app

RUN useradd --create-home --shell /usr/sbin/nologin appuser

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /app /app

USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "from urllib.request import urlopen; urlopen('http://127.0.0.1:8000/api/v1/health').read()"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
