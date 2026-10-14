"""Real Git snapshot regressions; fixtures are fresh and never touch a developer repo."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import full_plugin_host


class SnapshotTest(unittest.TestCase):
    def setUp(self):
        self.base=Path(tempfile.mkdtemp(prefix='daedalus-snapshot-'))
        self.repo=self.base/'repo';self.repo.mkdir()
        self.git('init','-b','codex/snapshot-fixture')
        self.git('config','user.name','Snapshot Fixture')
        self.git('config','user.email','fixture@example.invalid')
        self.git('config','core.autocrlf','false')
        self.prefix='engines/unreal/DaedalusLink/'
        self.plugin=self.repo/self.prefix;self.plugin.mkdir(parents=True)
        (self.plugin/'DaedalusLink.uplugin').write_bytes(b'{"FileVersion":3}')
        self.payload=b'\x00binary\n\nnext\xff\x00\r\n'
        (self.plugin/'binary.dat').write_bytes(self.payload)
        (self.plugin/'empty.dat').write_bytes(b'')
        self.git('add','.')
        self.git('commit','-m','fixture')

    def git(self,*args):
        return subprocess.check_output(['git',*args],cwd=self.repo,stderr=subprocess.DEVNULL).decode().strip()

    def test_binary_empty_and_fresh_destination_refusal(self):
        host=self.base/'host';full_plugin_host.snapshot(self.repo,host)
        manifest=json.loads((host/'source-manifest.json').read_text())
        self.assertEqual(manifest['tracked_file_count'],3)
        target=host/'Plugins/DaedalusLink'
        self.assertEqual((target/'binary.dat').read_bytes(),self.payload)
        self.assertEqual((target/'empty.dat').read_bytes(),b'')
        self.assertEqual(manifest['files'][self.prefix+'binary.dat'],hashlib.sha256(self.payload).hexdigest())
        before=(host/'source-manifest.json').read_bytes()
        with self.assertRaises(ValueError):full_plugin_host.snapshot(self.repo,host)
        self.assertEqual((host/'source-manifest.json').read_bytes(),before)

    def test_commit_advance_after_checks_cannot_change_pinned_bytes(self):
        original=self.git('rev-parse','HEAD');read=full_plugin_host.read_blobs
        def advance(repo,entries):
            (self.plugin/'binary.dat').write_bytes(b'later bytes')
            self.git('add','.')
            self.git('commit','-m','later concurrent commit')
            return read(repo,entries)
        host=self.base/'host'
        with patch.object(full_plugin_host,'read_blobs',advance):full_plugin_host.snapshot(self.repo,host)
        manifest=json.loads((host/'source-manifest.json').read_text())
        self.assertEqual(manifest['source_head'],original)
        self.assertNotEqual(self.git('rev-parse','HEAD'),original)
        self.assertEqual((host/'Plugins/DaedalusLink/binary.dat').read_bytes(),self.payload)

    def test_missing_git_object_is_rejected(self):
        with self.assertRaises(ValueError):
            list(full_plugin_host.read_blobs(self.repo,[('missing','0'*40)]))


if __name__=='__main__':unittest.main()
