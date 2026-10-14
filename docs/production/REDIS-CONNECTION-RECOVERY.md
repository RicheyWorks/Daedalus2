# Configured Redis connection and recovery

`RedisConfig` previously declared `new LettuceConnectionFactory()` without a
configuration. That replaced Spring Boot's configured factory and retained
localhost:6379 with no password. The production compose stack instead names a
`redis` service and sets a password. Memory fallback could hide failed Redis
operations, while health reported a broken connection.

The custom factory is removed. Boot's existing auto-configuration now binds the
connection, including host, port, username, password, database, timeout and TLS.
The opt-in `RedisConfig` still supplies the allowlisted JSON serializer and
custom RedisTemplate. The health-indicator binding and disabled mode remain
unchanged. See [Spring Boot Redis configuration](https://docs.spring.io/spring-boot/4.0/reference/data/nosql.html).

Context tests check nondefault connection properties and TLS without contacting
Redis. Full server reactor verification retains serializer refusal, fallback,
health, API and persistence coverage.

## Actual container acceptance

`tools/deploy/redis_recovery.py` uses a fresh private Docker network, two Redis
data volumes and two world volumes. Redis requires a generated password on a
nondefault port, with no Redis port published to the host. Anonymous PING must
be refused. The production server must become healthy and read a synthetic
typed leaderboard row through its real RedisTemplate and public API. The row
is seeded directly into Redis, so an empty in-memory fallback cannot pass.

Both source services stop before the actual `deploy/backup.sh` runs. Their
archive is extracted into different world and Redis volumes. A second Redis
and production server must retain the leaderboard row, a synthetic expiring
Redis value with a positive TTL, and the saved world block. The fixture reuses
the existing Docker/server/HTTP helpers. No production volumes or live restore
commands are used; fixture logs redact generated secrets.

```sh
python3 tools/deploy/redis_recovery.py --image daedalus-resource-smoke --output redis-proof
```

The output must be fresh. Successful execution writes image-independent
checked-state evidence, archive hash, timings and redacted logs. Actual
acceptance is the Linux image CI job and its `redis-recovery-proof` artifact,
not Python compilation or the context tests. The local Windows host has no
running Linux Docker daemon. Concurrent live-backup consistency, all replay
types, TLS transport against Redis, production failover and public deployment
remain separate acceptance requirements.
