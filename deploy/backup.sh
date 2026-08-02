#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

project_dir="${OCEANCLOUDS_PROJECT_DIR:-/opt/oceanclouds-erp}"
backup_root="${OCEANCLOUDS_BACKUP_DIR:-/var/backups/oceanclouds-erp}"
retention_days="${OCEANCLOUDS_BACKUP_RETENTION_DAYS:-14}"

if [ "$project_dir" != "/opt/oceanclouds-erp" ]; then
    echo "Refusing unexpected project directory: $project_dir" >&2
    exit 1
fi
if [ "$backup_root" != "/var/backups/oceanclouds-erp" ]; then
    echo "Refusing unexpected backup directory: $backup_root" >&2
    exit 1
fi

mkdir -p "$backup_root"
exec 9>"$backup_root/.backup.lock"
flock -n 9 || {
    echo "Another OceanClouds backup is already running." >&2
    exit 1
}

cd "$project_dir"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
temporary="$backup_root/.tmp-$stamp"
destination="$backup_root/$stamp"
mkdir -p "$temporary"

cleanup() {
    if [ -d "$temporary" ]; then
        rm -rf -- "$temporary"
    fi
}
trap cleanup EXIT

db_user="$(docker compose exec -T db printenv POSTGRES_USER | tr -d '\r')"
db_name="$(docker compose exec -T db printenv POSTGRES_DB | tr -d '\r')"

docker compose exec -T db \
    pg_dump -U "$db_user" -d "$db_name" -Fc --no-owner --no-acl \
    > "$temporary/postgres.dump"
docker compose exec -T db pg_restore --list \
    < "$temporary/postgres.dump" >/dev/null

docker compose exec -T web tar -C /app/media -czf - . \
    > "$temporary/media.tar.gz"
tar -tzf "$temporary/media.tar.gz" >/dev/null

(
    cd "$temporary"
    sha256sum postgres.dump media.tar.gz > SHA256SUMS
)

mv "$temporary" "$destination"
trap - EXIT

find "$backup_root" \
    -mindepth 1 \
    -maxdepth 1 \
    -type d \
    -name '20??????T??????Z' \
    -mtime "+$retention_days" \
    -print \
    -exec rm -rf -- {} +

echo "Backup completed: $destination"
