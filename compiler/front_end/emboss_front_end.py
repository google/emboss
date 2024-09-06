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

"""Emboss front end.

This is an internal tool, normally called by the "embossc" driver, rather than
directly by a user.  It parses a .emb file and its dependencies, and prints an
intermediate representation of the parse trees and symbol tables to stdout, or
prints various bits of debug info, depending on which flags are passed.
"""

from __future__ import print_function

import argparse
import os
from os import path
import sys

from compiler.front_end import glue
from compiler.front_end import module_ir
from compiler.util import error
from compiler.util import ir_data_utils


def _parse_command_line(argv):
    """Parses the given command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Emboss compiler front end.", prog=argv[0]
    )
    parser.add_argument("input_file", type=str, nargs=1, help=".emb file to compile.")
    parser.add_argument(
        "--debug-show-tokenization",
        action="store_true",
        help="Show the tokenization of the main input file.",
    )
    parser.add_argument(
        "--debug-show-parse-tree",
        action="store_true",
        help="Show the parse tree of the main input file.",
    )
    parser.add_argument(
        "--debug-show-module-ir",
        action="store_true",
        help="Show the module-level IR of the main input file "
        "before symbol resolution.",
    )
    parser.add_argument(
        "--debug-show-full-ir",
        action="store_true",
        help="Show the final IR of the main input file.",
    )
    parser.add_argument(
        "--debug-show-used-productions",
        action="store_true",
        help="Show all of the grammar productions used in "
        "parsing the main input file.",
    )
    parser.add_argument(
        "--debug-show-unused-productions",
        action="store_true",
        help="Show all of the grammar productions not used in "
        "parsing the main input file.",
    )
    parser.add_argument(
        "--output-ir-to-stdout",
        action="store_true",
        help="Dump serialized IR to stdout.",
    )
    parser.add_argument("--output-file", type=str, help="Write serialized IR to file.")
    parser.add_argument(
        "--no-debug-show-header-lines",
        dest="debug_show_header_lines",
        action="store_false",
        help="Print header lines before output if true.",
    )
    parser.add_argument(
        "--color-output",
        default="if_tty",
        choices=["always", "never", "if_tty", "auto"],
        help="Print error messages using color.  'auto' is a " "synonym for 'if_tty'.",
    )
    parser.add_argument(
        "--import-dir",
        "-I",
        dest="import_dirs",
        action="append",
        default=["."],
        help="A directory to use when searching for imported "
        "embs.  If no import_dirs are specified, the "
        "current directory will be used.",
    )
    return parser.parse_args(argv[1:])


def _show_errors(errors, ir, color_output):
    """Prints errors with source code snippets."""
    source_codes = {}
    if ir:
        for module in ir.module:
            source_codes[module.source_file_name] = module.source_text
    use_color = color_output == "always" or (
        color_output in ("auto", "if_tty") and os.isatty(sys.stderr.fileno())
    )
    print(error.format_errors(errors, source_codes, use_color), file=sys.stderr)


def _find_in_dirs_and_read(import_dirs):
    """Returns a function which will search import_dirs for a file."""

    def _find_and_read(file_name):
        """Searches import_dirs for file_name and returns the contents."""
        errors = []
        # *All* source files, including the one specified on the command line, will
        # be searched for in the import_dirs.  This may be surprising, especially if
        # the current directory is *not* an import_dir.
        # TODO(bolms): Determine if this is really the desired behavior.
        for import_dir in import_dirs:
            full_name = path.join(import_dir, file_name)
            try:
                with open(full_name) as f:
                    # As written, this follows the typical compiler convention of checking
                    # the include/import directories in the order specified by the user,
                    # and always reading the first matching file, even if other files
                    # might match in later directories.  This lets files shadow other
                    # files, which can be useful in some cases (to override things), but
                    # can also cause accidental shadowing, which can be tricky to fix.
                    #
                    # TODO(bolms): Check if any other files with the same name are in the
                    # import path, and give a warning or error?
                    return f.read(), None
            except IOError as e:
                errors.append(str(e))
        return None, errors + ["import path " + ":".join(import_dirs)]

    return _find_and_read


def parse_and_log_errors(input_file, import_dirs, color_output):
    """Fully parses an .emb and logs any errors.

    Arguments:
      input_file: The path of the module source file.
      import_dirs: Directories to search for imported dependencies.
      color_output: Used when logging errors: "always", "never", "if_tty", "auto"

    Returns:
      (ir, debug_info, errors)
    """
    ir, debug_info, errors = glue.parse_emboss_file(
        input_file, _find_in_dirs_and_read(import_dirs)
    )
    if errors:
        _show_errors(errors, ir, color_output)

    return (ir, debug_info, errors)


def main(flags):
    ir, debug_info, errors = parse_and_log_errors(
        flags.input_file[0], flags.import_dirs, flags.color_output
    )
    if errors:
        return 1
    main_module_debug_info = debug_info.modules[flags.input_file[0]]
    if flags.debug_show_tokenization:
        if flags.debug_show_header_lines:
            print("Tokenization:")
        print(main_module_debug_info.format_tokenization())
    if flags.debug_show_parse_tree:
        if flags.debug_show_header_lines:
            print("Parse Tree:")
        print(main_module_debug_info.format_parse_tree())
    if flags.debug_show_module_ir:
        if flags.debug_show_header_lines:
            print("Module IR:")
        print(main_module_debug_info.format_module_ir())
    if flags.debug_show_full_ir:
        if flags.debug_show_header_lines:
            print("Full IR:")
        print(str(ir))
    if flags.debug_show_used_productions:
        if flags.debug_show_header_lines:
            print("Used Productions:")
        print(glue.format_production_set(main_module_debug_info.used_productions))
    if flags.debug_show_unused_productions:
        if flags.debug_show_header_lines:
            print("Unused Productions:")
        print(
            glue.format_production_set(
                set(module_ir.PRODUCTIONS) - main_module_debug_info.used_productions
            )
        )
    if flags.output_ir_to_stdout:
        print(ir_data_utils.IrDataSerializer(ir).to_json())
    if flags.output_file:
        with open(flags.output_file, "w") as f:
            f.write(ir_data_utils.IrDataSerializer(ir).to_json())
    return 0


if __name__ == "__main__":
    sys.exit(main(_parse_command_line(sys.argv)))
