FROM python:3.11 AS builder

WORKDIR /app

RUN pip install uv && apt-get update && apt-get install -y --no-install-recommends make git

COPY . .
COPY --from=git . .git

RUN git config --global --add safe.directory /app

RUN make doc-build

FROM nginxinc/nginx-unprivileged:1.19

COPY --from=builder /app/site /usr/share/nginx/html