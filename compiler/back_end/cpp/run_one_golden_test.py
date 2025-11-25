#!/usr/bin/env python3

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

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from one_golden_test import OneGoldenTest


def main(argv):
    if len(argv) < 5:
        print(
            f"Usage: {argv[0]} emboss_front_end emboss_compiler emb_file golden_file [include_dir...]"
        )
        return 1

    emboss_front_end = argv[1]
    emboss_compiler = argv[2]
    emb_file = argv[3]
    golden_file = argv[4]
    
    include_dirs = []
    compiler_flags = []
    for arg in argv[5:]:
        if arg.startswith("--import-dir="):
            include_dirs.append(arg[len("--import-dir="):])
        else:
            compiler_flags.append(arg)

    suite = unittest.TestSuite()
    suite.addTest(
        OneGoldenTest(
            emboss_front_end,
            emboss_compiler,
            emb_file,
            golden_file,
            include_dirs,
            compiler_flags,
        )
    )
    runner = unittest.TextTestRunner()
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
