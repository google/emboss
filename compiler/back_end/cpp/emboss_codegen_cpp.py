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

import argparse
import os
import sys

from compiler.back_end.cpp import header_generator
from compiler.util import error
from compiler.util import ir_pb2


def _parse_command_line(argv):
  """Parses the given command-line arguments."""
  parser = argparse.ArgumentParser(
          description="Emboss compiler C++ back end end.",
          prog=argv[0])
  parser.add_argument("--color-output",
                      default="if_tty",
                      choices=["always", "never", "if_tty", "auto"],
                      help="Print error messages using color.  'auto' is a "
                           "synonym for 'if_tty'.")
  return parser.parse_args(argv[1:])


def _show_errors(errors, ir, flags):
  """Prints errors with source code snippets."""
  source_codes = {}
  for module in ir.module:
    source_codes[module.source_file_name] = module.source_text
  use_color = (flags.color_output == "always" or
               (flags.color_output in ("auto", "if_tty") and
                os.isatty(sys.stderr.fileno())))
  print(error.format_errors(errors, source_codes, use_color), file=sys.stderr)


def main(flags):
  ir = ir_pb2.EmbossIr.from_json(sys.stdin.read())
  header, errors = header_generator.generate_header(ir)
  if errors:
    _show_errors(errors, ir, flags)
    return 1
  print(header)
  return 0


if __name__ == '__main__':
  sys.exit(main(_parse_command_line(sys.argv)))
