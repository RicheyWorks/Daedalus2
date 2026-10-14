"""Run a disposable local production container and verify its real runtime resource/HTTP contracts."""
import argparse
import base64
import hashlib
import hmac
import io
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import time
import urllib.error
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/inventory'))
from packaged_server_smoke import request


def docker(*args, env=None, check=True):
    return subprocess.run(['docker', *args], env=env, check=check, capture_output=True,
                          text=True, timeout=60)


def start_server(image, name, environment, *, volume=None, network=None, redis=False, issuer='container-smoke'):
    args = ['run', '--detach', '--rm', '--name', name, '--publish', '127.0.0.1:0:8080']
    if volume:
        args += ['--volume', volume + ':/var/daedalus']
    if network:
        args += ['--network', network]
    args += ['--env', 'SPRING_PROFILES_ACTIVE=prod', '--env', 'DAEDALUS_JWT_SECRET',
             '--env', 'DAEDALUS_ADMIN_PASSWORD_BCRYPT']
    if redis:
        for key in ('REDIS_HOST', 'REDIS_PORT', 'REDIS_PASSWORD'):
            args += ['--env', key]
    args += [image, '--daedalus.redis.enabled=' + str(redis).lower(),
             '--daedalus.plugins.scan-on-startup=false', '--daedalus.security.jwt.issuer=' + issuer]
    docker(*args, env=environment)
    port = int(docker('port', name, '8080/tcp').stdout.strip().rsplit(':', 1)[1])
    base = 'http://127.0.0.1:' + str(port)
    deadline = time.monotonic() + 120
    while True:
        if docker('inspect', '--format', '{{.State.Running}}', name).stdout.strip() != 'true':
            raise RuntimeError('Container exited before becoming healthy')
        try:
            if request(base + '/actuator/health')[0] == 200:
                return base
        except (OSError, urllib.error.URLError):
            pass
        if time.monotonic() > deadline:
            raise RuntimeError('Container startup timed out')
        time.sleep(.5)


def check_jar(jar, root=ROOT):
    fixtures = sorted((root / 'engines/unreal/DaedalusLink/Content/Inventory').glob('*.dic'))
    if not fixtures:
        raise ValueError('No source catalogs')
    hashes = {}
    with zipfile.ZipFile(jar) as boot:
        cores = [n for n in boot.namelist() if n.startswith('BOOT-INF/lib/daedalus-core-') and n.endswith('.jar')]
        if len(cores) != 1:
            raise ValueError('Missing or ambiguous packaged core')
        with zipfile.ZipFile(io.BytesIO(boot.read(cores[0]))) as core:
            for source in fixtures:
                data = core.read('inventory/' + source.name)
                if data != source.read_bytes():
                    raise ValueError('Catalog differs from source: ' + source.name)
                hashes[source.name] = hashlib.sha256(data).hexdigest()
        tonic = boot.read('BOOT-INF/classes/kennel/tonics.json')
        if tonic != (root / 'tools/islands/kennel-isle/tonics.json').read_bytes():
            raise ValueError('Packaged tonic book differs from source')
        hashes['kennel/tonics.json'] = hashlib.sha256(tonic).hexdigest()
    return fixtures, hashes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    name = 'daedalus-resource-smoke-' + secrets.token_hex(8)
    key = secrets.token_bytes(32)
    secret = base64.b64encode(key).decode()
    environment = os.environ.copy()
    environment.update(DAEDALUS_JWT_SECRET=secret,
        DAEDALUS_ADMIN_PASSWORD_BCRYPT='$2a$10$7EqJtq98hPqEX7fNZaFWoOhi5B0h6C1JcqIcnLmVjKobXAB9Zwmqu')
    started = time.monotonic()
    try:
        base = start_server(args.image, name, environment)
        with tempfile.TemporaryDirectory() as directory:
            jar = Path(directory) / 'app.jar'
            docker('cp', name + ':/app/app.jar', str(jar))
            fixtures, hashes = check_jar(jar)
            jar_hash = hashlib.sha256(jar.read_bytes()).hexdigest()
        def encoded(value):
            return base64.urlsafe_b64encode(json.dumps(value, separators=(',', ':')).encode()).decode().rstrip('=')
        now = int(time.time())
        unsigned = encoded({'alg': 'HS256', 'typ': 'JWT'}) + '.' + encoded(
            {'iss': 'container-smoke', 'sub': 'container-smoke-user', 'iat': now, 'exp': now + 120})
        token = unsigned + '.' + base64.urlsafe_b64encode(hmac.new(key, unsigned.encode(), hashlib.sha256).digest()).decode().rstrip('=')
        results = []
        for fixture in fixtures:
            url = base + '/api/v1/inventory/' + fixture.stem + '/catalog'
            if request(url)[0] not in (401, 403):
                raise RuntimeError('Anonymous catalog read unexpectedly allowed')
            status, body = request(url, token)
            catalog = json.loads(body)
            if status != 200 or catalog.get('realm') != fixture.stem.upper() or not catalog.get('items'):
                raise RuntimeError('Authenticated catalog failed: ' + fixture.name)
            results.append({'realm': fixture.stem, 'status': status, 'definitions': len(catalog['items'])})
        if request(base + '/api/v1/inventory/missing/catalog', token)[0] != 404:
            raise RuntimeError('Missing catalog did not return 404')
        proof = {'schema': 1, 'image': docker('inspect', '--format', '{{.Image}}', name).stdout.strip(),
                 'jarSha256': jar_hash, 'resourceHashes': hashes, 'http': results,
                 'productionProfile': True, 'anonymousRefused': True, 'unknownRealm404': True,
                 'seconds': round(time.monotonic() - started, 3),
                 'scope': 'Disposable local image startup and resources; no public deployment, Redis or Unreal gameplay proof'}
        (args.output / 'proof.json').write_text(json.dumps(proof, indent=2) + '\n')
        print('CONTAINER_SMOKE_PASS', len(fixtures), 'catalogs, tonic bytes, prod boot and authenticated HTTP')
    finally:
        logs = docker('logs', name, check=False)
        text = (logs.stdout + logs.stderr).replace(secret, '[redacted]')
        (args.output / 'server.log').write_text(text)
        docker('rm', '--force', '--volumes', name, check=False)


if __name__ == '__main__':
    main()
