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

"""Emboss Wireshark Lua dissector code generator.

This is a driver program that reads IR, feeds it to dissector_generator, and
writes the resulting Lua source to stdout or a file.
"""

import argparse
import os
import sys

from compiler.back_end.lua import dissector_generator
from compiler.util import error
from compiler.util import ir_data
from compiler.util import ir_data_utils


def _parse_command_line(argv):
    parser = argparse.ArgumentParser(
        description="Emboss compiler Wireshark/Lua back end.", prog=argv[0]
    )
    parser.add_argument(
        "--input-file", type=str, help=".emb.ir file to compile."
    )
    parser.add_argument(
        "--output-file",
        type=str,
        help=(
            "Write Lua source to file.  If not specified, write to stdout."
        ),
    )
    parser.add_argument(
        "--color-output",
        default="if_tty",
        choices=["always", "never", "if_tty", "auto"],
        help="Print error messages using color.  'auto' is a synonym for 'if_tty'.",
    )
    return parser.parse_args(argv[1:])


def _show_errors(errors, ir, color_output):
    """Prints errors with source-code snippets, matching the C++ backend."""
    source_codes = {}
    for module in ir.module:
        source_codes[module.source_file_name] = module.source_text
    use_color = color_output == "always" or (
        color_output in ("auto", "if_tty") and os.isatty(sys.stderr.fileno())
    )
    print(error.format_errors(errors, source_codes, use_color), file=sys.stderr)


def main(flags):
    if flags.input_file:
        with open(flags.input_file) as f:
            ir = ir_data_utils.IrDataSerializer.from_json(ir_data.EmbossIr, f.read())
    else:
        ir = ir_data_utils.IrDataSerializer.from_json(
            ir_data.EmbossIr, sys.stdin.read()
        )
    text, errors = dissector_generator.generate_dissector(ir)
    if errors:
        _show_errors(errors, ir, flags.color_output)
        return 1
    if flags.output_file:
        with open(flags.output_file, "w") as f:
            f.write(text)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(_parse_command_line(sys.argv)))
