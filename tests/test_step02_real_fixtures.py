"""Tests for step-02 against the real (gitignored) sensitive fixtures.

These fixtures live under ``tests-real-sensitive-data/`` and are **not** committed
(real client MDD reports). The tests skip automatically when the files are absent,
so they cost nothing on a fresh clone / CI and only run where the data is present.

Expected semantics (see ``tests-real-sensitive-data/README.md``):

- ``a2_v1.mdd.json`` — no known stacking answer: it only needs to run cleanly and
  produce a valid spec (smoke test); no specific categories are asserted.
- ``a3_v1.mdd.json`` — must stack on *both* brands and TCGs in parallel. The two
  stub lists are mostly the same brands but not 1:1 (``MagicGathering`` in brands
  maps to ``MagicGatheringArena`` + ``MagicGatheringTTCG`` in TCGs), so there is no
  single best choice: the ranked candidates must surface both lists.
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
LAUNCHER = SRC / "launcher.py"
REAL_DATA_DIR = ROOT / "tests-real-sensitive-data"

A2_FIXTURE = REAL_DATA_DIR / "a2_v1.mdd.json"
A3_FIXTURE = REAL_DATA_DIR / "a3_v1.mdd.json"

# Distinguishing stubs between the two parallel lists in a3 (brands vs TCGs).
A3_BRAND_STUB = "magicgathering"
A3_TCG_STUBS = {"magicgatheringarena", "magicgatheringttcg"}


def _run_identify_variables(fixture, algorithm_ver="v2"):
    """Run the step-02 program against ``fixture``, return (proc, out_path, tmpdir)."""
    tmpdir = tempfile.TemporaryDirectory()
    out_path = Path(tmpdir.name) / "step02_out.json"
    cmd = [
        sys.executable, str(LAUNCHER),
        "--program", "mdd-autostk-identify-variables",
        "--inp-mdd-scheme", str(fixture),
        "--output-filename", str(out_path),
        "--config-algorithm-ver", algorithm_ver,
    ]
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    return proc, out_path, tmpdir


@unittest.skipUnless(A2_FIXTURE.is_file(), "real sensitive fixture a2 not present")
class TestA2RealFixtureSmoke(unittest.TestCase):
    def test_runs_and_writes_valid_spec(self):
        proc, out_path, tmpdir = _run_identify_variables(A2_FIXTURE)
        try:
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)
            self.assertTrue(out_path.is_file(), "expected result file to be written")
            result = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(result["algorithm_ver"], "v2")
            for key in ("variables", "categories", "candidates"):
                self.assertIn(key, result)
            # No category assertion here: for a2 there is no known "correct"
            # stacking target (see tests-real-sensitive-data/README.md).
        finally:
            tmpdir.cleanup()


@unittest.skipUnless(A3_FIXTURE.is_file(), "real sensitive fixture a3 not present")
class TestA3RealFixtureParallelStacks(unittest.TestCase):
    def test_surfaces_both_brand_and_tcg_stacks(self):
        proc, out_path, tmpdir = _run_identify_variables(A3_FIXTURE)
        try:
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)
            result = json.loads(out_path.read_text(encoding="utf-8"))
            candidates = result["candidates"]
            self.assertGreaterEqual(len(candidates), 2, "expected multiple candidates")

            brand_candidates = [
                c for c in candidates
                if A3_BRAND_STUB in c["categories"]
                and not (A3_TCG_STUBS & set(c["categories"]))
            ]
            tcg_candidates = [
                c for c in candidates
                if (A3_TCG_STUBS & set(c["categories"]))
                and A3_BRAND_STUB not in c["categories"]
            ]

            self.assertTrue(brand_candidates, "expected a brand-only stack candidate")
            self.assertTrue(tcg_candidates, "expected a TCG-only stack candidate")
        finally:
            tmpdir.cleanup()


if __name__ == "__main__":
    unittest.main()
