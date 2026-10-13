#!/bin/sh
# SPDX-License-Identifier: MIT
# One backup: <dst>/daedalus-<UTC time>.tar.gz of <src>/worlds and <src>/redis, then drop ones older than
# BACKUP_KEEP_DAYS. World files are saved atomically (temp file, then rename; ADR-064), so each file in the tar is a
# whole save. Usage: backup.sh <src> <dst>   (the compose 'backup' service runs it on a timer)
set -eu
src=${1:?src dir}
dst=${2:?backup dir}
keep=${BACKUP_KEEP_DAYS:-14}
mkdir -p "$dst"
stamp=$(date -u +%Y%m%d-%H%M%S)
tmp="$dst/.daedalus-$stamp.tar.gz.part"
tar -C "$src" -czf "$tmp" --exclude='*.tmp' worlds redis
# a backup that can't be listed is not a backup
tar -tzf "$tmp" >/dev/null
mv "$tmp" "$dst/daedalus-$stamp.tar.gz"
find "$dst" -name 'daedalus-*.tar.gz' -type f -mtime +"$keep" -delete
echo "backup $dst/daedalus-$stamp.tar.gz $(du -h "$dst/daedalus-$stamp.tar.gz" | cut -f1)"
