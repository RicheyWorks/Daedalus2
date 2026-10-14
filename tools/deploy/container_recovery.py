"""Prove stopped-world backup recovery using only newly created containers and volumes."""
import argparse
import base64
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import time
import urllib.error
import urllib.request
from container_smoke import ROOT, docker, request, start_server


def token_for(key):
    def encode(value):
        return base64.urlsafe_b64encode(json.dumps(value, separators=(',', ':')).encode()).decode().rstrip('=')
    now = int(time.time())
    unsigned = encode({'alg': 'HS256', 'typ': 'JWT'}) + '.' + encode(
        {'iss': 'recovery-smoke', 'sub': 'recovery-smoke-user', 'iat': now, 'exp': now + 600})
    return unsigned + '.' + base64.urlsafe_b64encode(hmac.new(key, unsigned.encode(), hashlib.sha256).digest()).decode().rstrip('=')


def write(base, token, method, path, value):
    req = urllib.request.Request(base + path, json.dumps(value).encode(), method=method,
        headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token})
    with urllib.request.urlopen(req, timeout=30) as response:
        if response.status != 200:
            raise RuntimeError('Mutation refused: ' + path)
        return json.load(response)


def read(base, token, path):
    status, body = request(base + path, token)
    if status != 200:
        raise RuntimeError('Read refused: ' + path)
    return json.loads(body)


def identities(response):
    rows = response.get('worlds')
    if not isinstance(rows, list) or not rows:
        raise ValueError('Missing restored worlds')
    result = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get('id'), str) or row['id'] in result:
            raise ValueError('Invalid or duplicate restored world')
        result[row['id']] = {key: row[key] for key in ('id', 'style', 'seed', 'title')}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        raise ValueError('Recovery output must be fresh, never reuse an existing backup directory')
    output.mkdir(parents=True)
    suffix = secrets.token_hex(8)
    containers = ['d2-recovery-source-' + suffix, 'd2-recovery-target-' + suffix]
    volumes = ['d2-recovery-source-' + suffix, 'd2-recovery-target-' + suffix]
    if volumes[0] == volumes[1]:
        raise ValueError('Recovery needs distinct volumes')
    key = secrets.token_bytes(32)
    secret = base64.b64encode(key).decode()
    environment = os.environ.copy()
    environment.update(DAEDALUS_JWT_SECRET=secret,
        DAEDALUS_ADMIN_PASSWORD_BCRYPT='$2a$10$7EqJtq98hPqEX7fNZaFWoOhi5B0h6C1JcqIcnLmVjKobXAB9Zwmqu')
    started = time.monotonic()

    def capture(name, label):
        logs = docker('logs', name, check=False)
        (output / (label + '.log')).write_text((logs.stdout + logs.stderr).replace(secret, '[redacted]'))

    def start(index):
        return start_server(args.image, containers[index], environment,
                            volume=volumes[index], issuer='recovery-smoke')

    try:
        for volume in volumes:
            docker('volume', 'create', volume)
        base = start(0)
        token = token_for(key)
        for id_, style, seed, title in [('restore-gallery', 'GALLERY', 42, 'Recovery Gallery'),
                                         ('restore-parcels', 'PARCELS', -77, 'Recovery Parcels')]:
            result = write(base, token, 'POST', '/api/v1/worlds',
                {'id': id_, 'style': style, 'seed': seed, 'title': title})
            if result.get('result') != 'CREATED':
                raise RuntimeError('Fixture world was not created: ' + id_)
        edits = {'world-zero': {'position': [2048, 100, 2048], 'type': 'CRYSTAL'}}
        claims = []
        for id_, route, field, type_ in [('restore-gallery', 'gallery', 'parcels', 'GLASS'),
                                          ('restore-parcels', 'plots', 'plots', 'WOOD')]:
            plot = read(base, token, '/api/v1/world/' + id_ + '/' + route)[field][0]
            claim = write(base, token, 'POST', '/api/v1/world/' + id_ + '/islands/' + str(plot['n']) + '/claim', {})
            if claim.get('result') != 'CLAIMED' or claim.get('owner') != 'recovery-smoke-user':
                raise RuntimeError('Fixture plot claim was refused: ' + id_)
            edits[id_] = {'position': [plot['minX'] + 1, plot['height'] - 1, plot['minZ'] + 1], 'type': type_}
            claims.append({'world': id_, 'route': route, 'field': field, 'plot': plot['n'], 'owner': claim['owner']})
        for id_, edit in edits.items():
            x, y, z = edit['position']
            result = write(base, token, 'PUT', '/api/v1/world/' + id_ + '/block',
                {'x': x, 'y': y, 'z': z, 'type': edit['type']})
            if result.get('result') != 'PLACED' or result.get('type') != edit['type']:
                raise RuntimeError('Fixture edit did not persist: ' + id_)
        before = identities(read(base, token, '/api/v1/worlds'))
        capture(containers[0], 'source')
        docker('stop', '--time', '20', containers[0])
        # Invoke the actual production backup script on a stopped synthetic world volume.
        docker('run', '--rm', '--volume', volumes[0] + ':/src/worlds:ro',
            '--tmpfs', '/src/redis', '--volume', str(output) + ':/backups',
            '--volume', str(ROOT / 'deploy/backup.sh') + ':/backup.sh:ro',
            'alpine:3.20', '/bin/sh', '/backup.sh', '/src', '/backups')
        archives = list(output.glob('daedalus-*.tar.gz'))
        if len(archives) != 1:
            raise RuntimeError('Expected exactly one newly created backup')
        archive = archives[0]
        # The archive writes worlds/... into the distinct target volume mounted at /dst/worlds.
        docker('run', '--rm', '--volume', volumes[1] + ':/dst/worlds', '--tmpfs', '/dst/redis',
            '--volume', str(output) + ':/backups:ro', 'alpine:3.20', '/bin/sh', '-c',
            'tar -C /dst -xzf "/backups/$1"', 'restore-fixture', archive.name)
        restored = start(1)
        after = identities(read(restored, token, '/api/v1/worlds'))
        if after != before:
            raise RuntimeError('Restored world metadata differs from the source')
        checks = []
        for id_, edit in edits.items():
            x, y, z = edit['position']
            row = read(restored, token, '/api/v1/world/' + id_ + '/block?x=' + str(x) + '&y=' + str(y) + '&z=' + str(z))
            if row.get('type') != edit['type']:
                raise RuntimeError('Restored saved block differs: ' + id_)
            checks.append({'world': id_, **edit})
        for claim in claims:
            plots = read(restored, token, '/api/v1/world/' + claim['world'] + '/' + claim['route'])[claim['field']]
            matches = [row for row in plots if row['n'] == claim['plot']]
            if len(matches) != 1 or matches[0].get('owner') != claim['owner']:
                raise RuntimeError('Restored plot claim differs: ' + claim['world'])
        proof = {'schema': 1, 'worlds': list(after.values()), 'savedBlocks': checks, 'savedClaims': claims,
            'backupSha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
            'sourceStoppedBeforeBackup': True, 'distinctRecoveryVolume': True,
            'image': docker('inspect', '--format', '{{.Image}}', containers[1]).stdout.strip(),
            'seconds': round(time.monotonic() - started, 3),
            'scope': 'Actual backup.sh and separate-volume container restore of synthetic worlds/edits; no live writes or Redis recovery claim'}
        (output / 'proof.json').write_text(json.dumps(proof, indent=2) + '\n')
        print('CONTAINER_RECOVERY_PASS', len(after), 'world identities and', len(checks), 'saved block edits')
    finally:
        try:
            capture(containers[1], 'restored')
        finally:
            for name in containers:
                docker('rm', '--force', '--volumes', name, check=False)
            for volume in volumes:
                docker('volume', 'rm', volume, check=False)


if __name__ == '__main__':
    main()
