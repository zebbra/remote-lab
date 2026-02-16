FROM python:3.11 AS builder

WORKDIR /app

RUN pip install uv

COPY . .

RUN uv sync --project .make_scripts/mkdocs-documentation/
RUN uv run --project .make_scripts/mkdocs-documentation/ mkdocs build

FROM nginxinc/nginx-unprivileged:1.19

COPY --from=builder /app/site /usr/share/nginx/html