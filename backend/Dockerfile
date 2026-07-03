# Archer backend image.
# Build context is ./backend (see docker-compose*.yml and the CI build step).

FROM python:3.12-slim

# Copy the uv binary from Astral's official image (no pip install of uv needed).
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Let uv install into a project venv and never try to manage Python itself.
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

# Dependency layer: copy only the lockfiles first so this layer is cached
# and re-used whenever app code changes but dependencies do not.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Application code.
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini

# Install the project itself into the venv now that its code is present.
RUN uv sync --frozen --no-dev

# Put the venv on PATH so `uvicorn`/`alembic` resolve without `uv run`.
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
