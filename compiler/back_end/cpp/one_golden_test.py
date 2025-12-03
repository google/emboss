# Copyright 2025 Google LLC
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

import difflib
import os
import subprocess
import sys
import unittest


class OneGoldenTest(unittest.TestCase):
    def __init__(
        self,
        emboss_front_end,
        emboss_compiler,
        emb_file,
        golden_file,
        include_dirs=None,
        compiler_flags=None,
    ):
        super(OneGoldenTest, self).__init__("test_golden_file")
        self.emboss_front_end = emboss_front_end
        self.emboss_compiler = emboss_compiler
        self.emb_file = emb_file
        self.golden_file = golden_file
        self.include_dirs = include_dirs if include_dirs is not None else []
        self.compiler_flags = compiler_flags if compiler_flags is not None else []

    def test_golden_file(self):
        temp_dir = os.environ.get("TEST_TMPDIR", "")
        ir_path = os.path.join(temp_dir, "ir.json")
        output_path = os.path.join(temp_dir, os.path.basename(self.golden_file))

        front_end_args = [
            self.emboss_front_end,
            self.emb_file,
            "--output-file",
            ir_path,
        ]
        for include_dir in self.include_dirs:
            front_end_args.extend(["--import-dir", include_dir])

        process = subprocess.run(front_end_args, capture_output=True, text=True)
        self.assertEqual(
            process.returncode, 0, f"Front end failed with error:\n{process.stderr}"
        )

        compiler_args = [
            self.emboss_compiler,
            "--input-file",
            ir_path,
            "--output-file",
            output_path,
        ]
        compiler_args.extend(self.compiler_flags)

        process = subprocess.run(compiler_args, capture_output=True, text=True)

        self.assertEqual(
            process.returncode, 0, f"Compiler failed with error:\n{process.stderr}"
        )

        with open(output_path, "r") as f:
            generated_contents = f.read()

        with open(self.golden_file, "r") as f:
            golden_contents = f.read()

        self.assertMultiLineEqual(
            golden_contents,
            generated_contents,
            msg="Generated file does not match golden file. Diff:\n"
            + "".join(
                difflib.unified_diff(
                    golden_contents.splitlines(keepends=True),
                    generated_contents.splitlines(keepends=True),
                    fromfile=self.golden_file,
                    tofile="Generated C++ Header",
                )
            ),
        )


if __name__ == "__main__":
    # This script is not intended to be run directly.
    # It should be invoked by a test runner.
    pass
