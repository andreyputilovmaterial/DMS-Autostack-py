"""Tests for ``mdd-autostk-identify-variables`` (step 02).

Covers the algorithm-version dispatch: ``v1`` (default) produces a single
variable/category spec, and ``v2`` produces multiple candidate groups ranked
best-first. Both are driven through the real launcher via a subprocess so the
three-way import and dispatch paths are exercised end to end.

``v2`` is additionally exercised directly (no subprocess) to verify that it is
**name-invariant**: renaming a category must not change the result.
"""

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
LAUNCHER = SRC / "launcher.py"
FIXTURE = ROOT / "tests" / "fixtures" / "a1_v3.mdd.json"

# Make the ``src`` package importable for the direct ``v2`` name-invariance test.
sys.path.insert(0, str(SRC))

from program_step02_identify_variables.adapters import mdd_fields
from program_step02_identify_variables.algorithms.v2 import find_variables_stack as v2

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

    def test_v2_returns_candidates(self):
        proc, out_path, tmpdir = _run_identify_variables(algorithm_ver="v2")
        try:
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)
            result = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(result["algorithm_ver"], "v2")
            candidates = result["candidates"]
            self.assertGreaterEqual(len(candidates), 2, "expected multiple candidates")
            # first candidate is the best match and mirrors the legacy fields
            self.assertEqual(candidates[0]["categories"], result["categories"])
            self.assertEqual(candidates[0]["variables"], result["variables"])
            # candidates are ranked best-first
            scores = [c["score"] for c in candidates]
            self.assertEqual(scores, sorted(scores, reverse=True))
            # every candidate is a valid group (>=2 categories, >=2 questions)
            for candidate in candidates:
                self.assertGreaterEqual(len(candidate["categories"]), 2)
                self.assertGreaterEqual(len(candidate["variables"]), 2)
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


class TestV2NameInvariance(unittest.TestCase):
    @staticmethod
    def _build_model():
        data = json.loads(FIXTURE.read_text(encoding="utf-8"))
        fields = [s for s in data["sections"] if s["name"] == "fields"][0]["content"]
        return mdd_fields.build_model(fields)

    def test_v2_no_special_category_names(self):
        # Every category gets the same neutral weight regardless of spelling.
        for name in ("none", "noneofthese", "noneofabove", "noneabove", "none67",
                     "other", "prefernotsay", "nike", "yes", "no", "_1", "1"):
            self.assertEqual(v2._category_quality(name, []), 1.0)

    def test_v2_is_name_invariant(self):
        questions, categories = self._build_model()
        baseline = v2.find_variables_to_stack(questions, categories, {"algorithm_ver": "v2"})

        renamed_questions = copy.deepcopy(questions)
        renamed_categories = copy.deepcopy(categories)
        # Replace every display name with its (lowercase) key: structure is
        # untouched, only spelling changes.
        for key in renamed_categories:
            renamed_categories[key]["name"] = key
        for key in renamed_questions:
            renamed_questions[key]["name"] = key

        renamed = v2.find_variables_to_stack(
            renamed_questions, renamed_categories, {"algorithm_ver": "v2"}
        )

        self.assertEqual(len(baseline["candidates"]), len(renamed["candidates"]))
        for original, renamed_candidate in zip(baseline["candidates"], renamed["candidates"]):
            self.assertEqual(original["score"], renamed_candidate["score"])
            self.assertEqual(
                {c.lower() for c in original["categories"]},
                set(renamed_candidate["categories"]),
            )
            self.assertEqual(
                {v.lower() for v in original["variables"]},
                set(renamed_candidate["variables"]),
            )


if __name__ == "__main__":
    unittest.main()
