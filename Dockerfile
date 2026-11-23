FROM node:22-bookworm-slim AS assets
WORKDIR /build
RUN npm install --ignore-scripts mermaid@10.9.3 katex@0.16.22 marked@15.0.12 dompurify@3.2.6 && mkdir /vendor && cp node_modules/mermaid/dist/mermaid.min.js node_modules/katex/dist/katex.min.* node_modules/marked/lib/marked.umd.js node_modules/dompurify/dist/purify.min.js /vendor/ && cp -r node_modules/katex/dist/fonts /vendor/
FROM python:3.11-slim-bookworm
ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends gcc libkrb5-dev krb5-user krb5-kdc krb5-admin-server openssl slapd ldap-utils && rm -rf /var/lib/apt/lists/*
WORKDIR /src
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
COPY --from=assets /vendor /src/vendor
COPY infra/krb5.conf /etc/krb5.conf

