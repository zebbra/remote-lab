FROM python:3.11 AS builder

WORKDIR /app

RUN pip install poetry

COPY . .

RUN poetry --project .make_scripts/mkdocs-documentation/ install

# We need the .git repository to get authors and last-modified dates
# but it is excluded in most .dockerignore files so we need to add it as a build context parameter
COPY --from=git . .git 

RUN make doc-build

FROM nginxinc/nginx-unprivileged:1.19

COPY --from=builder /app/site /usr/share/nginx/html