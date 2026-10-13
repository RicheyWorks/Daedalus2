#!/bin/sh
# SPDX-License-Identifier: MIT
# Put a backup back into the running stack's volumes. Stops the server first, keeps what was there as a
# pre-restore backup, then starts it again. Usage (from deploy/): ./restore.sh backups/daedalus-<stamp>.tar.gz
set -eu
archive=${1:?backup archive}
[ -f "$archive" ] || { echo "no such archive: $archive" >&2; exit 2; }
tar -tzf "$archive" | grep -q '^worlds/' || { echo "not a Daedalus backup (no worlds/)" >&2; exit 2; }
project=${COMPOSE_PROJECT_NAME:-daedalus}
docker compose stop server redis
# keep the current state first, whatever happens next
docker run --rm -v "${project}_worlds:/src/worlds:ro" -v "${project}_redis:/src/redis:ro" -v "$PWD/backups:/backups" \
  -v "$PWD/backup.sh:/backup.sh:ro" -e BACKUP_KEEP_DAYS=36500 alpine:3.20 /bin/sh /backup.sh /src /backups
docker run --rm -v "${project}_worlds:/dst/worlds" -v "${project}_redis:/dst/redis" -v "$(cd "$(dirname "$archive")" && pwd):/in:ro" \
  alpine:3.20 /bin/sh -c "rm -rf /dst/worlds/* /dst/redis/* && tar -C /dst -xzf /in/$(basename "$archive") && chown -R 999:999 /dst/redis"
docker compose start redis server
echo "restored $archive"
