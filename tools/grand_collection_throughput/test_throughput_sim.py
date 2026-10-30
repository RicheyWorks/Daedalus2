# SPDX-License-Identifier: MIT
import datetime as dt
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import throughput_sim as ts  # noqa: E402

T0 = dt.datetime(2026, 10, 27, 0, 0, 0, tzinfo=dt.timezone.utc)


def row(n, k, drift=0.0, gap=1.0):
    return {"chunk": n, "blender": 50.0, "pre": 140.0 + drift * k, "import": 60.0, "validate": 280.0 + drift * k,
            "post": 140.0, "gap": gap}


def flat(n=30):
    return [row(200 + i, i) for i in range(n)]


class Model(unittest.TestCase):
    def test_fit_flat_and_drift(self):
        m = ts.model(flat())
        self.assertAlmostEqual(m["pre"]["start"], 140.0)
        self.assertAlmostEqual(m["pre"]["drift"], 0.0)
        m2 = ts.model([row(200 + i, i, drift=2.0) for i in range(30)])
        self.assertAlmostEqual(m2["validate"]["drift"], 2.0, places=3)

    def test_latest_session_used(self):
        rows = [row(100 + i, i, drift=5.0) for i in range(10)]
        rows[-1]["gap"] = 40000.0
        rows += flat(10)
        m = ts.model(rows)
        self.assertEqual(m["_session"]["first"], 200)
        self.assertAlmostEqual(m["pre"]["drift"], 0.0)

    def test_baseline_hours(self):
        m = ts.model(flat())
        r = ts.project(m, 2400, 10000, 10, {})
        self.assertEqual(r["chunks"], 760)
        self.assertAlmostEqual(r["hours"], round(760 * 671 / 3600, 1))

    def test_pipeline_hides_blender(self):
        m = ts.model(flat())
        self.assertAlmostEqual(ts.chunk_seconds(m, 0, {"pipeline_blender": True}, 10), 621.0)

    def test_chunk_size_20_halves_chunks_and_amortizes_fixed(self):
        m = ts.model(flat())
        r10 = ts.project(m, 2400, 10000, 10, {})
        r20 = ts.project(m, 2400, 10000, 10, {"per_kind": 20})
        self.assertEqual(r20["chunks"], 380)
        self.assertLess(r20["hours"], r10["hours"])
        self.assertGreater(r20["hours"], r10["hours"] / 2)

    def test_relaunch_beats_drift(self):
        m = ts.model([row(200 + i, i, drift=3.0) for i in range(30)])
        none = ts.project(m, 2400, 10000, 10, {})
        n, best = ts.best_interval(m, 2400, 10000, 10, {}, 300.0)
        self.assertLess(best["hours"], none["hours"])
        self.assertGreater(best["relaunches"], 0)

    def test_every_option_runs(self):
        res = ts.simulate([row(200 + i, i, drift=1.0) for i in range(30)], 2400, 10000)
        self.assertEqual(len(res), len(ts.OPTIONS))
        self.assertTrue(all(r["hours"] > 0 for r in res))
        self.assertIn("| option |", ts.to_md(ts.model(flat()), res, 2400, 10000))

    def test_done_target(self):
        self.assertEqual(ts.project(ts.model(flat()), 10000, 10000, 10, {})["hours"], 0.0)


class Extract(unittest.TestCase):
    def test_extract_from_files_and_log(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            camp, cont = d / "camp", d / "content"

            def touch(p, t, text="x"):
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(text)
                os.utime(p, (t.timestamp(), t.timestamp()))
            log = []
            for i, n in enumerate((5, 6)):
                b = T0 + dt.timedelta(seconds=700 * i)
                touch(camp / "SourceJobs" / f"Chunk{n:04d}" / "start.json", b, json.dumps({"utc": b.isoformat().replace("+00:00", "Z")}))
                touch(camp / "SourceJobs" / f"Chunk{n:04d}" / "terminal.json", b + dt.timedelta(seconds=50))
                touch(cont / f"R18_C{n:04d}" / "a.uasset", b + dt.timedelta(seconds=200))
                touch(cont / f"R18_C{n:04d}" / "L.umap", b + dt.timedelta(seconds=260))
                touch(camp / "CatalogChunks" / f"Chunk{n:04d}.catalog-staging.csv", b + dt.timedelta(seconds=699))
                for sec, cat in ((190, "LogInterchangeImport"), (560, "AssetCheck")):
                    t = b + dt.timedelta(seconds=sec)
                    log.append(t.strftime("[%Y.%m.%d-%H.%M.%S:000][  1]") + cat + ": x")
            (d / "ue.log").write_text("\n".join(log) + "\nnoise\n")
            rows = ts.extract(camp, cont, ts.read_log(d / "ue.log"), 5, 7)
            self.assertEqual([r["chunk"] for r in rows], [5, 6])
            r = rows[0]
            self.assertEqual((r["blender"], r["pre"], r["import"], r["validate"], r["post"], r["gap"]),
                             (50.0, 140.0, 60.0, 300.0, 139.0, 1.0))
            self.assertIsNone(rows[1]["gap"])
            out = d / "s.json"
            self.assertEqual(ts.main(["extract", "--campaign", str(camp), "--content", str(cont), "--log", str(d / "ue.log"),
                                      "--from", "5", "--to", "6", "--out", str(out)]), 0)


if __name__ == "__main__":
    unittest.main()
