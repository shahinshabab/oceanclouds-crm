# Docker deployment

The stack contains Django/Gunicorn, PostgreSQL, and Nginx. PostgreSQL data,
uploaded media, and collected static files are stored in named Docker volumes.

## Configure

Copy `.env.example` to `.env` and replace both placeholder secrets. Generate a
Django secret with:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

For production, keep `DJANGO_DEBUG=False`, use the public hostname in
`DJANGO_ALLOWED_HOSTS`, and include its full HTTPS origin in
`DJANGO_CSRF_TRUSTED_ORIGINS`.

## Start

```bash
docker compose config
docker compose build
docker compose up -d
docker compose ps
curl http://127.0.0.1:8080/healthz
```

The web entrypoint waits for the healthy PostgreSQL dependency through Compose,
runs Django migrations, collects static files, and starts Gunicorn. Container
Nginx listens only on `127.0.0.1:8080` by default so the server's TLS-enabled
host Nginx can proxy to it without a port conflict.

Example host Nginx proxy target:

```nginx
location / {
    proxy_pass http://127.0.0.1:8080;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

For the test server, `deploy/test.oceanclouds.in.nginx.conf` is the HTTP host
configuration used before Certbot adds the HTTPS listener and redirect.

## Persistent data

- `oceanclouds-erp_postgres_data`: PostgreSQL data
- `oceanclouds-erp_media_data`: user uploads
- `oceanclouds-erp_static_data`: collected Django static files

Do not use `docker compose down --volumes` in production; it removes the named
data volumes. Back up PostgreSQL with `pg_dump` and back up the media volume
before upgrades.
