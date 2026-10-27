import hashlib
import json
from contextlib import contextmanager
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from construction_inventory import asset_row, inventory


class InventoryTest(unittest.TestCase):
    def test_ready_missing_and_stale_exports_are_distinct(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); source=root/'asset.glb'; source.write_bytes(b'known bytes')
            row={'id':'Prop_Test','file':'asset.glb','sha256':hashlib.sha256(source.read_bytes()).hexdigest()}
            self.assertEqual(asset_row(row,root)['status'],'Hash matched')
            source.write_bytes(b'changed')
            self.assertEqual(asset_row(row,root)['status'],'Hash mismatch')
            source.unlink()
            self.assertEqual(asset_row(row,root)['status'],'Missing')

    def test_manifest_cannot_escape_root_or_forge_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            with self.assertRaises(ValueError):asset_row({'id':'x','file':'../outside','sha256':'0'*64},root)
            with self.assertRaises(ValueError):asset_row({'id':'x','file':'inside','sha256':'not a hash'},root)


class InventoryReportTest(unittest.TestCase):
    # Independent protocol fixtures: never take realm names/paths from REALMS.
    REALM_LAYOUT = (
        ('GALLERY-CITY', 'gallery', 'gallery-buildout', 'WORLD_V1 / GALLERY style'),
        ('PARCELS', 'parcels', 'parcels-buildout', 'WORLD_V1 / PARCELS style'),
        ('BRICKS', 'bricks', 'bricks-buildout', 'WORLD_V1 / BRICKS style'),
        ('LABYRINTH', 'labyrinth', 'labyrinth-full', 'LABYRINTH style / separate Maze API'),
        ('PORTAL', 'portal', 'portal-buildout', 'Retro data API; no chunk-provider entry'),
        ('OCEAN', 'ocean', 'ocean-vessels-2', 'Optional OCEAN_V1; separate bounded chunk host'),
    )
    SESSION_IDS = ['WORLD-ZERO', 'GALLERY-CITY', 'PARCELS', 'BRICKS',
                   'LABYRINTH', 'PORTAL', 'OCEAN']
    MATCHED_COUNTS = {'GALLERY-CITY': 1, 'PARCELS': 2, 'BRICKS': 3,
                      'LABYRINTH': 4, 'PORTAL': 5, 'OCEAN': 6}
    HEAD = '0123456789abcdef0123456789abcdef01234567'
    STYLE_PATH = 'daedalus-core/src/main/java/com/daedalus/world/WorldStyle.java'
    SESSION_PATH = ('engines/unreal/DaedalusLink/Source/DaedalusLink/Public/'
                    'DaedalusRealmSessionCore.h')
    STYLE_BYTES = (b'enum WorldStyle {\n    SKY_ISLANDS(true, 0),\n'
                   b'    GALLERY(false, 0),\n    PARCELS(true, 0),\n'
                   b'    BRICKS(false, 0),\n    LABYRINTH(true, 0),\n'
                   b'    RETRO(false, 0),\n    OCEAN(true, 0);\n}\n')

    @staticmethod
    def sha(data):
        return hashlib.sha256(data).hexdigest()

    def write(self, path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def session_bytes(self, names):
        return ''.join('    {"' + name + '", false},\n' for name in names).encode('ascii')

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='synthetic-inventory-contract-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.repo = self.root / 'repo'
        self.deliveries = self.root / 'deliveries'
        self.write(self.repo / self.STYLE_PATH, self.STYLE_BYTES)
        self.write(self.repo / self.SESSION_PATH, self.session_bytes(self.SESSION_IDS))
        self.write(self.repo / 'docs/production/BASE-LAYER.md', b'Synthetic source reference.\n')
        self.payloads = {}
        self.manifests = {}
        self.raw_manifests = {}
        self.rows = {}
        for realm, stem, folder, _ in self.REALM_LAYOUT:
            payloads = {name: (realm + ': synthetic ' + name + ' export\n').encode('ascii')
                        for name in ('matched', 'missing', 'approved', 'changed')}
            self.payloads[realm] = payloads
            filename = 'manifest.json' if realm == 'OCEAN' else 'production-manifest.json'
            self.manifests[realm] = self.repo / 'data/art' / stem / filename
            # Repeated IDs ACROSS realms are valid; duplicates within one are not.
            self.rows[realm] = [
                {'id': 'shared-part', 'file': 'structures/shared.glb',
                 'sha256': self.sha(payloads['matched']), 'triangles': 12, 'role': 'wall'},
                {'id': 'missing-part', 'file': 'structures/not-exported.glb',
                 'sha256': self.sha(payloads['missing']), 'triangles': 99, 'role': 'door'},
                {'id': 'changed-part', 'file': 'kit.glb', 'sha256': self.sha(payloads['approved'])},
            ]
            for number in range(1, self.MATCHED_COUNTS[realm]):
                relative = 'structures/extra-' + str(number) + '.glb'
                self.rows[realm].append({'id': 'extra-' + str(number), 'file': relative,
                                         'sha256': self.sha(payloads['matched'])})
                self.write(self.deliveries / folder / relative, payloads['matched'])
            self.write_manifest(realm, self.rows[realm])
            self.write(self.deliveries / folder / 'structures/shared.glb', payloads['matched'])
            self.write(self.deliveries / folder / 'kit.glb', payloads['changed'])

    def write_manifest(self, realm, rows):
        value = {'synthetic_fixture': 'Ocean wrapper metadata', 'assets': rows} if realm == 'OCEAN' else rows
        raw = json.dumps(value, sort_keys=True, indent=2).encode('utf-8') + b'\n'
        self.write(self.manifests[realm], raw)
        self.raw_manifests[realm] = raw

    def snapshot(self):
        result = {}
        for path in self.root.rglob('*'):
            stat = path.stat()
            result[str(path.relative_to(self.root))] = (
                path.read_bytes() if path.is_file() else None, stat.st_mtime_ns)
        return result

    @contextmanager
    def git_head(self, error=None):
        before = self.snapshot()
        # This is the only mock: hashing, parsing and report assembly remain real.
        with patch('construction_inventory.subprocess.check_output',
                   return_value='\n' + self.HEAD + '\n', side_effect=error) as lookup:
            try:
                yield lookup
            finally:
                self.assertEqual(self.snapshot(), before, 'inventory changed its input tree')

    def assert_git_lookup(self, lookup):
        lookup.assert_called_once_with(['git', 'rev-parse', 'HEAD'], cwd=self.repo, text=True)

    def expected_assets(self, realm, folder):
        payloads = self.payloads[realm]
        cases = [
            ('shared-part', 'structures/shared.glb', self.sha(payloads['matched']),
             self.sha(payloads['matched']), 'Hash matched', 12, 'wall', 'structures'),
            ('missing-part', 'structures/not-exported.glb', self.sha(payloads['missing']),
             None, 'Missing', 99, 'door', 'structures'),
            ('changed-part', 'kit.glb', self.sha(payloads['approved']),
             self.sha(payloads['changed']), 'Hash mismatch', None, '', 'vessel-kit'),
        ]
        for number in range(1, self.MATCHED_COUNTS[realm]):
            cases.append(('extra-' + str(number), 'structures/extra-' + str(number) + '.glb',
                          self.sha(payloads['matched']), self.sha(payloads['matched']),
                          'Hash matched', None, '', 'structures'))
        return [dict(id=identifier, group=group,
                     file=str((self.deliveries / folder / relative).resolve()),
                     triangles=triangles, expected_sha256=expected, actual_sha256=actual,
                     status=status, role=role,
                     runtime_acceptance='Not established by file inventory')
                for identifier, relative, expected, actual, status, triangles, role, group in cases]

    def expected_report(self, empty=False):
        realms = {'WORLD-ZERO': {
            'terrain_source': 'WORLD_V1 / SKY_ISLANDS; actual mounted provider is runtime configuration',
            'reuse': 'Existing 14 team sublevels; inspect current saved editor state before changing them',
            'source_reference': str(self.repo / 'docs/production/BASE-LAYER.md'),
            'asset_census': 'Team island assets are outside the six inspected production manifests',
        }}
        for realm, _, folder, terrain in self.REALM_LAYOUT:
            realms[realm] = {
                'manifest': str(self.manifests[realm]),
                'manifest_sha256': self.sha(self.raw_manifests[realm]),
                'delivery_root': str(self.deliveries / folder), 'terrain_source': terrain,
                'status_counts': {} if empty else {'Hash matched': self.MATCHED_COUNTS[realm],
                                                   'Missing': 1, 'Hash mismatch': 1},
                'group_counts': {} if empty else {'structures': self.MATCHED_COUNTS[realm] + 1,
                                                  'vessel-kit': 1},
                'assets': [] if empty else self.expected_assets(realm, folder),
            }
        return {
            'source_head': self.HEAD,
            'scope': 'Exact local file availability and hashes, not import, collision, possession, Play or hosting proof',
            'reuse_tools': [str(self.repo / 'engines/unreal/DaedalusLink/Content/Python' / name)
                            for name in ('daedalus_realm_ground.py', 'daedalus_plots.py',
                                         'daedalus_land_grid.py')],
            'operator_constraints': 'Current editor lease, RAM guard, current level assertion, bounded import/save batches',
            'source_world_style_ready': {'SKY_ISLANDS': True, 'GALLERY': False, 'PARCELS': True,
                                         'BRICKS': False, 'LABYRINTH': True, 'RETRO': False, 'OCEAN': True},
            'native_session_ids': self.SESSION_IDS,
            'capability_source_sha256': {
                str(Path(self.STYLE_PATH)): self.sha(self.STYLE_BYTES),
                str(Path(self.SESSION_PATH)): self.sha(self.session_bytes(self.SESSION_IDS)),
            },
            'mounted_hosts_verified': False, 'realms': realms,
        }

    def test_complete_report_has_exact_schema_provenance_hashes_and_totals(self):
        self.assertEqual(len({self.sha(raw) for raw in self.raw_manifests.values()}), 6)
        self.assertEqual(len({self.sha(data['matched']) for data in self.payloads.values()}), 6)
        with self.git_head() as lookup:
            report = inventory(self.repo, self.deliveries)
        self.assert_git_lookup(lookup)
        self.assertEqual(report, self.expected_report())
        self.assertEqual(json.loads(json.dumps(report)), self.expected_report())
        self.assertIs(report['mounted_hosts_verified'], False)
        self.assertTrue(all(type(value) is bool for value in report['source_world_style_ready'].values()))
        inspected = [report['realms'][realm] for realm, _, _, _ in self.REALM_LAYOUT]
        self.assertEqual(sum(len(realm['assets']) for realm in inspected), 33)
        self.assertEqual(sum(realm['status_counts'].get('Hash matched', 0) for realm in inspected), 21)
        for status in ('Missing', 'Hash mismatch'):
            self.assertEqual(sum(realm['status_counts'].get(status, 0) for realm in inspected), 6)
        self.assertEqual(sum(realm['group_counts'].get('structures', 0) for realm in inspected), 27)
        self.assertEqual(sum(realm['group_counts'].get('vessel-kit', 0) for realm in inspected), 6)
        self.assertNotIn('assets', report['realms']['WORLD-ZERO'])

    def test_empty_manifests_keep_all_realms_without_inventing_world_zero_census(self):
        for realm, _, _, _ in self.REALM_LAYOUT:
            self.write_manifest(realm, [])
        with self.git_head() as lookup:
            report = inventory(self.repo, self.deliveries)
        self.assert_git_lookup(lookup)
        self.assertEqual(report, self.expected_report(empty=True))
        self.assertIs(report['mounted_hosts_verified'], False)

    def test_native_roster_missing_or_unexpected_realm_is_refused(self):
        for names in (self.SESSION_IDS[:-1], self.SESSION_IDS + ['UNEXPECTED-REALM']):
            with self.subTest(roster=names):
                self.write(self.repo / self.SESSION_PATH, self.session_bytes(names))
                with self.git_head() as lookup:
                    with self.assertRaisesRegex(ValueError, 'Native realm roster changed'):
                        inventory(self.repo, self.deliveries)
                lookup.assert_not_called()

    def test_duplicate_ids_are_refused_within_each_realm_including_ocean(self):
        for realm, _, _, _ in self.REALM_LAYOUT:
            with self.subTest(realm=realm):
                self.write_manifest(realm, self.rows[realm] + [dict(self.rows[realm][0])])
                try:
                    with self.git_head() as lookup:
                        with self.assertRaisesRegex(ValueError, 'Duplicate IDs in realm manifest: ' + realm):
                            inventory(self.repo, self.deliveries)
                    lookup.assert_not_called()
                finally:
                    self.write_manifest(realm, self.rows[realm])

    def test_missing_manifest_is_fatal_rather_than_a_partial_report(self):
        for realm, _, _, _ in self.REALM_LAYOUT:
            with self.subTest(realm=realm):
                original = self.manifests[realm].read_bytes()
                self.manifests[realm].unlink()
                try:
                    with self.git_head() as lookup:
                        with self.assertRaises(FileNotFoundError) as raised:
                            inventory(self.repo, self.deliveries)
                    self.assertEqual(raised.exception.filename, str(self.manifests[realm]))
                    lookup.assert_not_called()
                finally:
                    self.manifests[realm].write_bytes(original)

    def test_malformed_json_and_missing_ocean_assets_are_not_silently_skipped(self):
        for realm, raw, error in (('PORTAL', b'{', json.JSONDecodeError),
                                  ('OCEAN', b'{"synthetic_fixture": true}', KeyError)):
            with self.subTest(realm=realm):
                original = self.manifests[realm].read_bytes()
                self.manifests[realm].write_bytes(raw)
                try:
                    with self.git_head() as lookup:
                        with self.assertRaises(error):
                            inventory(self.repo, self.deliveries)
                    lookup.assert_not_called()
                finally:
                    self.manifests[realm].write_bytes(original)

    def test_asset_path_and_hash_validation_propagate_to_report_boundary(self):
        for update, message in (({'file': '../outside.glb'}, 'Manifest file leaves delivery root'),
                                ({'sha256': 'not-a-hash'}, 'Invalid expected SHA256')):
            with self.subTest(update=update):
                rows = [dict(row) for row in self.rows['GALLERY-CITY']]
                rows[0].update(update)
                self.write_manifest('GALLERY-CITY', rows)
                with self.git_head() as lookup:
                    with self.assertRaisesRegex(ValueError, message):
                        inventory(self.repo, self.deliveries)
                lookup.assert_not_called()

    def test_git_lookup_failure_propagates_without_fabricated_source_provenance(self):
        error = subprocess.CalledProcessError(128, ['git', 'rev-parse', 'HEAD'],
                                             stderr='Synthetic Git lookup failure')
        with self.git_head(error=error) as lookup:
            with self.assertRaises(subprocess.CalledProcessError) as raised:
                inventory(self.repo, self.deliveries)
        self.assertIs(raised.exception, error)
        self.assert_git_lookup(lookup)


if __name__=='__main__':unittest.main()
