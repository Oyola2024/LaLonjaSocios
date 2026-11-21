FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-cache

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "uv run python src/manage.py migrate && uv run python src/manage.py runserver 0.0.0.0:8000"]
