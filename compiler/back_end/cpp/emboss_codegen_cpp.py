# Copyright 2019 Google LLC
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

"""Emboss C++ code generator.

This is a driver program that reads IR, feeds it to header_generator, and prints
the result.
"""

from __future__ import print_function

import sys

from compiler.back_end.cpp import header_generator
from compiler.util import ir_pb2


def main(argv):
  del argv  # Unused.
  ir = ir_pb2.EmbossIr.from_json(sys.stdin.read())
  print(header_generator.generate_header(ir))
  return 0


if __name__ == '__main__':
  sys.exit(main(sys.argv))
