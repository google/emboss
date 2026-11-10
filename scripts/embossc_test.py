#!/usr/bin/env python3

# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for the `embossc` driver's back end selection.

`embossc` runs the front end in-process and dispatches on `--generate`.  These
tests drive it as a subprocess, the way a user does, and check that each back
end lands its output in the right place.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest


def _repo_root():
    """Returns the directory holding `embossc`.

    Under Bazel this is the runfiles root, where `//:embossc` and the
    `compiler/` tree from the back end binaries' runfiles sit side by side.
    Run directly, it is the repository root.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(here)


_ROOT = _repo_root()
_EMBOSSC = os.path.join(_ROOT, "embossc")
_TEST_EMB = os.path.join("testdata", "enum.emb")


def _subprocess_env():
    """An environment in which `compiler` and its pip deps are importable.

    Under Bazel the test's own `sys.path` is the only place that knows where
    the runfiles and pip packages live, and `PYTHONSAFEPATH` (set by
    rules_python) keeps a child process from adding its script directory back.
    Hand both down explicitly.
    """
    env = dict(os.environ)
    entries = [_ROOT] + [p for p in sys.path if p]
    if env.get("PYTHONPATH"):
        entries.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(entries)
    env.pop("PYTHONSAFEPATH", None)
    return env


def _run(args, cwd=_ROOT):
    return subprocess.run(
        [sys.executable, _EMBOSSC] + args,
        cwd=cwd,
        env=_subprocess_env(),
        capture_output=True,
        text=True,
    )


class EmbosscBackEndSelectionTest(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.out_dir = self._tmp.name
        self.addCleanup(self._tmp.cleanup)

    def _common_args(self):
        return [
            "--import-dir=.",
            "--import-dir=testdata",
            "--output-path=" + self.out_dir,
        ]

    def test_cc_back_end_is_the_default(self):
        result = _run(self._common_args() + ["--output-file=out.h", _TEST_EMB])
        self.assertEqual(result.returncode, 0, result.stderr)
        with open(os.path.join(self.out_dir, "out.h")) as f:
            header = f.read()
        self.assertIn("#ifndef TESTDATA_ENUM_EMB_H_", header)

    def test_cc_back_end_when_named_explicitly(self):
        result = _run(
            ["--generate", "cc"]
            + self._common_args()
            + ["--output-file=out.h", _TEST_EMB]
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        with open(os.path.join(self.out_dir, "out.h")) as f:
            self.assertIn("#ifndef TESTDATA_ENUM_EMB_H_", f.read())

    def test_ir_back_end_emits_parseable_json(self):
        result = _run(
            ["--generate", "ir"]
            + self._common_args()
            + ["--output-file=out.ir", _TEST_EMB]
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        with open(os.path.join(self.out_dir, "out.ir")) as f:
            ir = json.load(f)
        self.assertIn("module", ir)
        source_files = [m.get("source_file_name") for m in ir["module"]]
        self.assertIn(_TEST_EMB, source_files)

    def test_ir_back_end_matches_the_front_end_byte_for_byte(self):
        """`--generate ir` must be the same IR the Bazel rules feed back ends."""
        result = _run(
            ["--generate", "ir"]
            + self._common_args()
            + ["--output-file=out.ir", _TEST_EMB]
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        front_end_path = os.path.join(self.out_dir, "front_end.ir")
        front_end = subprocess.run(
            [
                sys.executable,
                "-m",
                "compiler.front_end.emboss_front_end",
                "--import-dir=.",
                "--import-dir=testdata",
                "--output-file=" + front_end_path,
                _TEST_EMB,
            ],
            cwd=_ROOT,
            env=_subprocess_env(),
            capture_output=True,
            text=True,
        )
        self.assertEqual(front_end.returncode, 0, front_end.stderr)
        with open(os.path.join(self.out_dir, "out.ir")) as f:
            from_embossc = f.read()
        with open(front_end_path) as f:
            from_front_end = f.read()
        self.assertEqual(from_embossc, from_front_end)

    def test_default_output_file_name_follows_the_back_end(self):
        for back_end, suffix in (("cc", ".h"), ("ir", ".ir")):
            with self.subTest(back_end=back_end):
                result = _run(
                    [
                        "--generate",
                        back_end,
                        "--import-dir=.",
                        "--import-dir=testdata",
                        "--output-path=" + self.out_dir,
                        _TEST_EMB,
                    ]
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue(
                    os.path.exists(os.path.join(self.out_dir, _TEST_EMB + suffix))
                )

    def test_multi_character_output_path_is_not_truncated(self):
        """`--output-path` used to be indexed as a list, so only '.' survived."""
        nested = os.path.join(self.out_dir, "nested", "deeper")
        result = _run(
            [
                "--generate",
                "ir",
                "--import-dir=.",
                "--import-dir=testdata",
                "--output-path=" + nested,
                "--output-file=out.ir",
                _TEST_EMB,
            ]
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(os.path.exists(os.path.join(nested, "out.ir")))

    def test_unknown_back_end_is_rejected(self):
        result = _run(["--generate", "nonesuch"] + self._common_args() + [_TEST_EMB])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--generate", result.stderr)


if __name__ == "__main__":
    unittest.main()
