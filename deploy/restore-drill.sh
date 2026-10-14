#!/bin/sh
# SPDX-License-Identifier: MIT
# Prove the newest backup restores: start a throwaway server on it (no TLS, no ports published), wait for health,
# and check every world in the backup is served. Touches nothing live. Run weekly. Usage: ./restore-drill.sh
set -eu
latest=$(ls -1t backups/daedalus-*.tar.gz 2>/dev/null | head -1)
[ -n "$latest" ] || { echo "no backups yet" >&2; exit 2; }
command -v python3 >/dev/null || { echo "python3 is required for restore verification" >&2; exit 2; }
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
work=$(mktemp -d)
python3 "$script_dir/restore_manifest.py" manifest "$latest" "$work/expected.json" || {
  rm -f "$work/expected.json"; rmdir "$work"; exit 2;
}
image=daedalus-server:${DAEDALUS_VERSION:-local}
vol=daedalus-drill-$$
name=daedalus-drill-$$
cleanup() {
  docker rm -f "$name" >/dev/null 2>&1 || true
  docker volume rm "$vol" >/dev/null 2>&1 || true
  rm -f "$work/expected.json" "$work/response.http"
  rmdir "$work"
}
trap cleanup EXIT
docker volume create "$vol" >/dev/null
docker run --rm -v "$vol:/dst" -v "$PWD/backups:/in:ro" alpine:3.20 \
  /bin/sh -c "mkdir -p /dst/x && tar -C /dst/x -xzf /in/$(basename "$latest") && mv /dst/x/worlds/* /dst/ 2>/dev/null; rm -rf /dst/x; ls /dst"
# hand the files to the image's own daedalus user, whatever its uid
docker run --rm --user root --entrypoint chown -v "$vol:/var/daedalus" "$image" -R daedalus:daedalus /var/daedalus
docker run -d --name "$name" -v "$vol:/var/daedalus" -e SPRING_PROFILES_ACTIVE=dev "$image" >/dev/null
for i in $(seq 1 60); do
  if docker exec "$name" bash -c 'exec 3<>/dev/tcp/127.0.0.1/8080 && printf "GET /api/v1/worlds HTTP/1.0\r\nHost: localhost\r\n\r\n" >&3 && cat <&3' >"$work/response.http" 2>/dev/null; then
    python3 "$script_dir/restore_manifest.py" verify "$work/expected.json" "$work/response.http" || exit 1
    echo "drill: $latest restored and every saved world is served"
    exit 0
  fi
  sleep 3
done
echo "drill FAILED: server never answered" >&2
docker logs --tail 50 "$name" >&2
exit 1
