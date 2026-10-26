import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import brand  # noqa: E402


def dump(obj, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f)


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)
import cards  # noqa: E402
import shots  # noqa: E402

EP = os.path.join(HERE, "episodes", "recording-isle")


class VideoPipeline(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_episode_captions_cover_shotlist(self):
        ep = load(os.path.join(EP, "episode.json"))
        caps = [c for _, c, _ in shots.read_shots(os.path.join(EP, "shots.txt")) if c != "-"]
        self.assertEqual(len(caps), 11)
        self.assertEqual(sorted(set(caps) - set(ep["captions"])), [])

    def test_read_write_roundtrip(self):
        p = os.path.join(self.tmp, "s.txt")
        shots.write_shots(p, [("A", "a", None), ("B", "-", 2.5)])
        self.assertEqual(shots.read_shots(p), [("A", "a", None), ("B", "-", 2.5)])

    def test_cards(self):
        made = cards.build(load(os.path.join(EP, "episode.json")), self.tmp)
        self.assertEqual(len(made), 2 + 11 + 1)
        from PIL import Image
        self.assertEqual(Image.open(os.path.join(self.tmp, "title.png")).size, brand.VIDEO)
        self.assertEqual(Image.open(os.path.join(self.tmp, "thumb.png")).size, brand.THUMB)
        self.assertEqual(Image.open(os.path.join(self.tmp, "cap_spring.png")).mode, "RGBA")

    def test_prepare_mixes_real_and_placeholder(self):
        from PIL import Image
        real = os.path.join(self.tmp, "real", "YTM_Spring"); os.makedirs(real)
        for i in (5, 6, 7):
            Image.new("RGB", (64, 36)).save(os.path.join(real, "f.%04d.jpg" % i))
        sl, rep = shots.prepare(os.path.join(EP, "shots.txt"), os.path.join(self.tmp, "w"), os.path.join(self.tmp, "real"))
        self.assertEqual(rep["YTM_Spring"], "real:3")
        self.assertEqual(sum(v == "placeholder" for v in rep.values()), 10)
        self.assertEqual(shots.frames(os.path.join(self.tmp, "w", "YTM_Spring")), ["0000.jpg", "0001.jpg", "0002.jpg"])

    def test_stills_from_capture_manifest(self):
        from PIL import Image
        cap = os.path.join(self.tmp, "cap"); os.makedirs(cap)
        for v in ("overview", "garden"):
            Image.new("RGB", (64, 36)).save(os.path.join(cap, "ytm_island_%s.png" % v))
        dump({"schema": "capture/v1/manifest", "job": "ytm_island",
              "files": ["ytm_island_overview.png", "ytm_island_garden.png", "ytm_island_missing.png"]},
             os.path.join(cap, "manifest.json"))
        sl = shots.stills(os.path.join(cap, "manifest.json"), os.path.join(self.tmp, "w"), 2, {"garden": "garden"})
        self.assertEqual(sl, [("ytm_island_overview", "-", 2), ("ytm_island_garden", "garden", 2)])
        with self.assertRaises(ValueError):
            dump({"schema": "other"}, os.path.join(cap, "bad.json"))
            shots.stills(os.path.join(cap, "bad.json"), self.tmp)

    @unittest.skipUnless(os.name != "nt" and shutil.which("ffmpeg") and shutil.which("ffprobe") and shutil.which("bash"),
                         "needs ffmpeg + a POSIX bash (Windows bash.exe is WSL and cannot see these paths)")
    def test_assemble_end_to_end(self):
        ep = os.path.join(self.tmp, "ep"); os.makedirs(ep)
        dump({"title": ["t"], "captions": {"a": "caption a"}}, os.path.join(ep, "episode.json"))
        with open(os.path.join(ep, "shots.txt"), "w") as f:
            f.write("S1 a 1\nS2 - 1\n")
        out = os.path.join(self.tmp, "out.mp4")
        r = subprocess.run(["bash", os.path.join(HERE, "cut.sh"), ep, out], capture_output=True, text=True,
                           env=dict(os.environ, CARD_S="1"))
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        d = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", out]))
        self.assertAlmostEqual(d, 4.0, delta=0.5)
        self.assertTrue(os.path.exists(os.path.join(self.tmp, "out_thumb.png")))


if __name__ == "__main__":
    unittest.main()
