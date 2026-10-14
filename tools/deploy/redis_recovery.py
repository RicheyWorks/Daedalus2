"""Verify configured authenticated Redis reads and stopped backup recovery in disposable fixtures."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import secrets
import time
from container_smoke import ROOT, docker, start_server
from container_recovery import read, write, token_for


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        raise ValueError('Redis recovery output must be fresh')
    output.mkdir(parents=True)
    suffix = secrets.token_hex(8)
    network = 'd2-redis-recovery-' + suffix
    servers = ['d2-redis-app-source-' + suffix, 'd2-redis-app-target-' + suffix]
    caches = ['d2-redis-source-' + suffix, 'd2-redis-target-' + suffix]
    worlds = ['d2-redis-world-source-' + suffix, 'd2-redis-world-target-' + suffix]
    stores = ['d2-redis-data-source-' + suffix, 'd2-redis-data-target-' + suffix]
    key = secrets.token_bytes(32)
    jwt_secret = base64.b64encode(key).decode()
    password = secrets.token_hex(32)
    environment = os.environ.copy()
    environment.update(DAEDALUS_JWT_SECRET=jwt_secret,
        DAEDALUS_ADMIN_PASSWORD_BCRYPT='$2a$10$7EqJtq98hPqEX7fNZaFWoOhi5B0h6C1JcqIcnLmVjKobXAB9Zwmqu',
        REDIS_PASSWORD=password, REDISCLI_AUTH=password, REDIS_PORT='6388')
    started = time.monotonic()

    def command(index, *parts):
        return docker('exec', '--env', 'REDISCLI_AUTH', caches[index],
                      'redis-cli', '-p', '6388', '--raw', *parts, env=environment).stdout.strip()

    def start_cache(index):
        docker('run', '--detach', '--rm', '--name', caches[index], '--network', network,
            '--network-alias', 'redis-' + str(index), '--volume', stores[index] + ':/data',
            '--env', 'REDIS_PASSWORD', 'redis:7.4-alpine', '/bin/sh', '-c',
            'exec redis-server --port 6388 --appendonly yes --appendfsync always --requirepass "$REDIS_PASSWORD"',
            env=environment)
        deadline = time.monotonic() + 30
        while True:
            probe = docker('exec', '--env', 'REDISCLI_AUTH', caches[index],
                          'redis-cli', '-p', '6388', '--raw', 'PING', env=environment, check=False)
            if probe.returncode == 0 and probe.stdout.strip() == 'PONG':
                break
            if time.monotonic() > deadline:
                raise RuntimeError('Redis fixture did not become ready')
            time.sleep(.25)
        no_auth = docker('exec', caches[index], 'redis-cli', '-p', '6388', 'PING', check=False)
        if 'NOAUTH' not in no_auth.stdout + no_auth.stderr:
            raise RuntimeError('Redis authentication was not enforced')

    def start_app(index):
        settings = dict(environment, REDIS_HOST='redis-' + str(index))
        return start_server(args.image, servers[index], settings, volume=worlds[index],
                            network=network, redis=True, issuer='recovery-smoke')

    try:
        docker('network', 'create', network)
        for volume in worlds + stores:
            docker('volume', 'create', volume)
        start_cache(0)
        session = '43ea0c92-5127-45db-afb2-c8db2b4f4168'
        entry = {'@class': 'com.daedalus.model.LeaderboardEntry', 'sessionId': session, 'mazeId': None,
            'playerName': 'redis-recovery-fixture', 'score': 4242, 'moveCount': 7, 'elapsedMs': 1234,
            'mazeGeneratorId': 'recursive-backtracker', 'achievedAt': '2026-10-14T00:00:00Z'}
        if command(0, 'ZADD', 'daedalus:leaderboard:global', '4242', json.dumps(entry)) != '1':
            raise RuntimeError('Synthetic leaderboard seed failed')
        if command(0, 'SET', 'daedalus:recovery:ttl', 'restore-me', 'EX', '600') != 'OK':
            raise RuntimeError('Synthetic expiring value failed')
        token = token_for(key)
        source = start_app(0)
        before = read(source, token, '/api/v1/leaderboard?n=10')
        if len(before) != 1 or before[0].get('sessionId') != session or before[0].get('score') != 4242:
            raise RuntimeError('Application did not read the typed Redis leaderboard')
        placed = write(source, token, 'PUT', '/api/v1/world/world-zero/block',
                       {'x': 2048, 'y': 100, 'z': 2048, 'type': 'CRYSTAL'})
        if placed.get('result') != 'PLACED':
            raise RuntimeError('Synthetic world edit refused')
        docker('stop', '--time', '20', servers[0])
        docker('stop', '--time', '20', caches[0])
        docker('run', '--rm', '--volume', worlds[0] + ':/src/worlds:ro',
            '--volume', stores[0] + ':/src/redis:ro', '--volume', str(output) + ':/backups',
            '--volume', str(ROOT / 'deploy/backup.sh') + ':/backup.sh:ro',
            'alpine:3.20', '/bin/sh', '/backup.sh', '/src', '/backups')
        archives = list(output.glob('daedalus-*.tar.gz'))
        if len(archives) != 1:
            raise RuntimeError('Expected one new Redis/world backup')
        archive = archives[0]
        docker('run', '--rm', '--volume', worlds[1] + ':/dst/worlds',
            '--volume', stores[1] + ':/dst/redis', '--volume', str(output) + ':/backups:ro',
            'alpine:3.20', '/bin/sh', '-c', 'tar -C /dst -xzf "/backups/$1"', 'redis-restore', archive.name)
        start_cache(1)
        if command(1, 'GET', 'daedalus:recovery:ttl') != 'restore-me':
            raise RuntimeError('Redis expiring value did not survive recovery')
        ttl = int(command(1, 'TTL', 'daedalus:recovery:ttl'))
        if not 0 < ttl <= 600:
            raise RuntimeError('Redis expiration was lost')
        restored = start_app(1)
        after = read(restored, token, '/api/v1/leaderboard?n=10')
        if after != before:
            raise RuntimeError('Application leaderboard differs after Redis recovery')
        block = read(restored, token, '/api/v1/world/world-zero/block?x=2048&y=100&z=2048')
        if block.get('type') != 'CRYSTAL':
            raise RuntimeError('World edit did not survive the same backup')
        proof = {'schema': 1, 'configuredHostnames': ['redis-0', 'redis-1'], 'configuredPort': 6388,
            'serverImage': docker('inspect', '--format', '{{.Image}}', servers[1]).stdout.strip(),
            'redisImage': docker('inspect', '--format', '{{.Image}}', caches[1]).stdout.strip(),
            'redisAuthenticationEnforced': True, 'typedLeaderboardReadBeforeAndAfter': True,
            'leaderboardSession': session, 'score': 4242, 'expiringValueRestored': True, 'remainingTtlSeconds': ttl,
            'worldBlockRestored': 'CRYSTAL', 'sourceServicesStoppedBeforeBackup': True,
            'distinctRedisAndWorldVolumes': True, 'backupSha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
            'seconds': round(time.monotonic() - started, 3),
            'scope': 'Actual authenticated Redis AOF/world recovery of synthetic data; no live backup consistency or production deployment'}
        (output / 'proof.json').write_text(json.dumps(proof, indent=2) + '\n')
        print('REDIS_RECOVERY_PASS configured host/auth, typed application reads, expiration and world edit')
    finally:
        for name in servers + caches:
            logs = docker('logs', name, check=False)
            redacted = (logs.stdout + logs.stderr).replace(jwt_secret, '[redacted]').replace(password, '[redacted]')
            (output / (name + '.log')).write_text(redacted)
            docker('rm', '--force', '--volumes', name, check=False)
        for volume in worlds + stores:
            docker('volume', 'rm', volume, check=False)
        docker('network', 'rm', network, check=False)


if __name__ == '__main__':
    main()
