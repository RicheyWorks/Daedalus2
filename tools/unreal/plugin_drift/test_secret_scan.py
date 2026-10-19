"""Offline tests for secret_scan. Fake secrets are assembled at runtime so this file never trips the scanner."""
import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import secret_scan as ss  # noqa: E402

FAKE = "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8"


def write(root, rel, text):
    full = os.path.join(root, *rel.split("/"))
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as fh:
        fh.write(text)


class SecretScanTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def rules(self, rel):
        return {r for _, _, r in ss.scan_paths(self.root, [rel])}

    def test_clean_source(self):
        write(self.root, "Source/A.cpp", "int main() { return 0; }\n")
        self.assertEqual(ss.scan_paths(self.root, ["Source/A.cpp"]), [])

    def test_content_rules(self):
        cases = {
            "pk.txt": "-----BEGIN RSA " + "PRIVATE KEY-----",
            "c.txt": "key " + "crsr_" + FAKE,
            "g.txt": "ghp" + "_" + FAKE,
            "b.txt": "Authorization: Bear" + "er " + FAKE,
            "w.txt": "https://hooks.slack" + ".com/services/T000/B000/" + FAKE,
            "s.json": '{"api_key": "' + FAKE + '"}',
            "u.ps1": "C:" + "\\Users\\someone\\tokens\\relay-" + "webhook.json",
        }
        expect = {"pk.txt": "private-key-block", "c.txt": "cursor-key", "g.txt": "github-token",
                  "b.txt": "bearer-literal", "w.txt": "webhook-url", "s.json": "secret-assignment",
                  "u.ps1": "user-path-credential"}
        for rel, text in cases.items():
            write(self.root, rel, text + "\n")
            self.assertIn(expect[rel], self.rules(rel), rel)

    def test_forbidden_names_and_dirs(self):
        for rel in (".env", "x.pem", "a/b.key", "link/relay-webhook.json", "Saved/Logs/x.log",
                    "Plugins/P/Intermediate/a.txt", "Binaries/Win64/x.txt"):
            write(self.root, rel, "harmless\n")
            self.assertTrue(any(r.startswith("forbidden") for r in self.rules(rel)), rel)

    def test_example_files_allowed(self):
        write(self.root, ".env.example", "TOKEN=\n")
        self.assertEqual(self.rules(".env.example"), set())

    def test_output_never_contains_value(self):
        write(self.root, "leak.txt", "token = '" + FAKE + "'\n")
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = ss.main(["--root", self.root, "leak.txt"])
        self.assertEqual(rc, 1)
        self.assertNotIn(FAKE, buf.getvalue())
        self.assertIn("leak.txt:1 secret-assignment", buf.getvalue())

    def test_env_var_reference_is_clean(self):
        write(self.root, "k.cpp", 'FString T = FPlatformMisc::GetEnvironmentVariable(TEXT("DAEDALUS_KENNEL_TOKEN"));\n')
        self.assertEqual(self.rules("k.cpp"), set())


if __name__ == "__main__":
    unittest.main()
