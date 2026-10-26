#!/bin/sh
# SPDX-License-Identifier: MIT
# Print fresh secrets as .env lines: ./gen-secrets.sh >> .env
# The admin password is printed once to stderr and stored only as a bcrypt hash. Needs openssl and docker
# (caddy hash-password makes the bcrypt hash).
set -eu
rand() { openssl rand -base64 "$1" | tr -d '\n/+=' | cut -c1-"$2"; }
admin=$(rand 24 24)
hash=$(docker run --rm caddy:2.8-alpine caddy hash-password --plaintext "$admin")
echo "REDIS_PASSWORD=$(rand 32 40)"
echo "DAEDALUS_JWT_SECRET=$(rand 64 64)"
# $ in a bcrypt hash must be doubled for docker compose .env interpolation
echo "DAEDALUS_ADMIN_PASSWORD_BCRYPT=$(printf '%s' "$hash" | sed 's/\$/$$/g')"
echo "admin password (save it in your password manager, it is not stored anywhere): $admin" >&2
