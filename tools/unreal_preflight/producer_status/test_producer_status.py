# SPDX-License-Identifier: MIT
import datetime as dt
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import producer_status as ps  # noqa: E402

START = "2026-10-26T18:40:05.6119407Z"


def make(d: Path, n=3, failure=False):
    (d / "launch.json").write_text(json.dumps({"pid": 4242, "start": START}), encoding="utf-8")
    rows = [{"milestone": "CHUNK_SAVED", "chunk": 199 + i, "saved_counts": {"skull": 2090 + 10 * i, "toter": 2090 + 10 * i},
             "next_index": 2091 + 10 * i} for i in range(n)]
    (d / "stdout.log").write_text("noise\n" + "\n".join(json.dumps(r) for r in rows) + "\n{bad\n", encoding="utf-8")
    t = ps.parse_time(START).timestamp() + n * 600   # 10 min per chunk
    os.utime(d / "stdout.log", (t, t))
    if failure:
        (d / "sub").mkdir()
        (d / "sub" / "failure.json").write_text("{}")


def status(d, locks=None, ram=6.0, alive=True, **kw):
    now = ps.parse_time(START) + dt.timedelta(minutes=35)
    return ps.build_status(d, None, "http://x", 10000, 3.0, now=now, alive=lambda p: alive,
                           ram=lambda: ram, locks=lambda b: locks, **kw)


class T(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_seven_digit_fraction(self):
        self.assertEqual(ps.parse_time(START).microsecond, 611940)

    def test_healthy(self):
        make(self.d)
        st = status(self.d, locks={"unreal": {"holder": "b", "age_s": 60, "left_s": 9000}})
        self.assertEqual(st["last_chunk"], 201)
        self.assertEqual(st["next_index"], 2111)
        self.assertEqual(st["pace_min_per_chunk"], 10.0)
        self.assertEqual(st["last_save_age_min"], 5.0)
        self.assertEqual(st["eta_h_to_target"], round((10000 - 2110) / 10 * 10 / 60, 1))
        self.assertEqual(st["attention"], [])
        self.assertIn("OK", ps.render(st))

    def test_attention(self):
        make(self.d, failure=True)
        st = status(self.d, locks={"unreal": {"holder": "b", "age_s": 1, "left_s": 30}}, ram=2.0, alive=False)
        a = "; ".join(st["attention"])
        for s in ("pid not running", "failure.json", "RAM", "lease unreal"):
            self.assertIn(s, a)
        self.assertIn("ATTENTION", ps.render(st))

    def test_broker_down_and_empty_log(self):
        make(self.d, n=0)
        st = status(self.d, locks=None)
        self.assertIsNone(st["locks"])
        self.assertNotIn("last_chunk", st)
        self.assertIn("broker unreachable", ps.render(st))

    def test_main_bad_dir(self):
        self.assertEqual(ps.main(["--launch-dir", str(self.d / "nope")]), 2)

    def test_pid_alive_self(self):
        self.assertTrue(ps.pid_alive(os.getpid()))
        self.assertFalse(ps.pid_alive(0))


if __name__ == "__main__":
    unittest.main()
