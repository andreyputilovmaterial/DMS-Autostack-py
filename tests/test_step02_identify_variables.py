"""Tests for ``mdd-autostk-identify-variables`` (step 02).

Covers the algorithm-version dispatch: ``v1`` (default) runs and produces a
valid variable/category spec, and ``v2`` is an explicit placeholder that fails
with a clear message.

Like ``test_done_program.py``, these drive the real launcher via a subprocess so
the three-way import and dispatch paths are exercised end to end.
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "src" / "launcher.py"
FIXTURE = ROOT / "tests" / "fixtures" / "a1_v3.mdd.json"

# The six brand categories a1_v3 is designed to surface (see tests/fixtures/README.md).
EXPECTED_BRAND_CATEGORIES = {"nike", "tesla", "cocacola", "select", "yesstream", "nostream"}


def _run_identify_variables(algorithm_ver=None):
    """Run the step-02 program against the primary fixture, return (proc, out_path)."""
    tmpdir = tempfile.TemporaryDirectory()
    out_path = Path(tmpdir.name) / "step02_out.json"
    cmd = [
        sys.executable, str(LAUNCHER),
        "--program", "mdd-autostk-identify-variables",
        "--inp-mdd-scheme", str(FIXTURE),
        "--output-filename", str(out_path),
    ]
    if algorithm_ver is not None:
        cmd += ["--config-algorithm-ver", algorithm_ver]
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    return proc, out_path, tmpdir


class TestIdentifyVariablesDispatch(unittest.TestCase):
    def test_v1_is_default_and_writes_result(self):
        proc, out_path, tmpdir = _run_identify_variables()
        try:
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)
            self.assertTrue(out_path.is_file(), "expected result file to be written")
            result = json.loads(out_path.read_text(encoding="utf-8"))
            for key in ("variables", "categories", "algorithm_ver"):
                self.assertIn(key, result)
            self.assertEqual(result["algorithm_ver"], "v1")
        finally:
            tmpdir.cleanup()

    def test_explicit_v1_works(self):
        proc, out_path, tmpdir = _run_identify_variables(algorithm_ver="v1")
        try:
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)
            result = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(result["algorithm_ver"], "v1")
        finally:
            tmpdir.cleanup()

    def test_v2_is_placeholder(self):
        proc, out_path, tmpdir = _run_identify_variables(algorithm_ver="v2")
        try:
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("not implemented", proc.stderr)
        finally:
            tmpdir.cleanup()

    def test_a1_v3_selects_expected_brands(self):
        proc, out_path, tmpdir = _run_identify_variables(algorithm_ver="v1")
        try:
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)
            result = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(set(result["categories"]), EXPECTED_BRAND_CATEGORIES)
        finally:
            tmpdir.cleanup()


if __name__ == "__main__":
    unittest.main()
