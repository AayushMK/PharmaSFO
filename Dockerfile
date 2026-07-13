FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency files first for caching
COPY pyproject.toml uv.lock ./

# Install exactly what the lockfile pins — a stale lock fails the build rather
# than silently resolving different versions than were tested locally.
RUN uv sync --frozen --no-dev

# Copy project
COPY . .

# Bake static files into the image — collectstatic needs no DB, so it can't fail at boot
RUN uv run python manage.py collectstatic --noinput

EXPOSE 8000

# Production entrypoint. Compose overrides this with runserver for local dev.
# Railway supplies $PORT; migrations run here because the DB is only reachable at runtime.
CMD ["sh", "-c", "uv run python manage.py migrate --noinput && uv run gunicorn PharmaSFO.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 3 --timeout 60 --access-logfile -"]
