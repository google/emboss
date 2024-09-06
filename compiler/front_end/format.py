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

"""Formatter for Emboss source files.

This program formats an Emboss source file given on the command line.
"""

from __future__ import absolute_import
from __future__ import print_function

import argparse
import os
import sys

from compiler.front_end import format_emb
from compiler.front_end import parser
from compiler.front_end import tokenizer
from compiler.util import error


def _parse_command_line(argv):
    """Parses the given command-line arguments."""
    argparser = argparse.ArgumentParser(
        description="Emboss compiler front end.", prog=argv[0]
    )
    argparser.add_argument(
        "input_file", type=str, nargs="+", help=".emb file to compile."
    )
    argparser.add_argument(
        "--no-check-result",
        default=True,
        action="store_false",
        dest="check_result",
        help="Verify that the resulting formatted text "
        "contains only whitespace changes.",
    )
    argparser.add_argument(
        "--debug-show-line-types",
        default=False,
        help="Show the computed type of each line.",
    )
    argparser.add_argument(
        "--no-edit-in-place",
        default=True,
        action="store_false",
        dest="edit_in_place",
        help="Write the formatted text back to the input " "file.",
    )
    argparser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="Number of spaces to use for each level of " "indentation.",
    )
    argparser.add_argument(
        "--color-output",
        default="if-tty",
        choices=["always", "never", "if-tty", "auto"],
        help="Print error messages using color.  'auto' is a " "synonym for 'if-tty'.",
    )
    return argparser.parse_args(argv[1:])


def _print_errors(errors, source_codes, flags):
    use_color = flags.color_output == "always" or (
        flags.color_output in ("auto", "if-tty") and os.isatty(sys.stderr.fileno())
    )
    print(error.format_errors(errors, source_codes, use_color), file=sys.stderr)


def main(argv=()):
    flags = _parse_command_line(argv)

    if not flags.edit_in_place and len(flags.input_file) > 1:
        print(
            "Multiple files may only be formatted without --no-edit-in-place.",
            file=sys.stderr,
        )
        return 1

    if flags.edit_in_place and flags.debug_show_line_types:
        print(
            "The flag --debug-show-line-types requires --no-edit-in-place.",
            file=sys.stderr,
        )
        return 1

    for file_name in flags.input_file:
        with open(file_name) as f:
            source_code = f.read()

        tokens, errors = tokenizer.tokenize(source_code, file_name)
        if errors:
            _print_errors(errors, {file_name: source_code}, flags)
            continue

        parse_result = parser.parse_module(tokens)
        if parse_result.error:
            _print_errors(
                [error.make_error_from_parse_error(file_name, parse_result.error)],
                {file_name: source_code},
                flags,
            )
            continue

        formatted_text = format_emb.format_emboss_parse_tree(
            parse_result.parse_tree,
            format_emb.Config(
                show_line_types=flags.debug_show_line_types, indent_width=flags.indent
            ),
        )

        if flags.check_result and not flags.debug_show_line_types:
            errors = format_emb.sanity_check_format_result(formatted_text, source_code)
            if errors:
                for e in errors:
                    print(e, file=sys.stderr)
                continue

        if flags.edit_in_place:
            with open(file_name, "w") as f:
                f.write(formatted_text)
        else:
            sys.stdout.write(formatted_text)

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
