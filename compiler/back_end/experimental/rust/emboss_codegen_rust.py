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

"""Emboss Rust code generator."""

import os
import sys
from typing import Literal

from compiler.util import error
from compiler.util import ir_data

ColorOutput = Literal["always", "never", "if_tty", "auto"]
Source = str
ErrorList = list[list[error._Message]]


def _show_errors(
    errors: ErrorList, ir: ir_data.EmbossIr, color_output: ColorOutput
) -> None:
    """Prints errors with source code snippets."""
    source_codes = {}
    for module in ir.module:
        source_codes[module.source_file_name] = module.source_text
    use_color = color_output == "always" or (
        color_output in ("auto", "if_tty") and os.isatty(sys.stderr.fileno())
    )
    print(error.format_errors(errors, source_codes, use_color), file=sys.stderr)


def generate_code_and_log_errors(
    ir: ir_data.EmbossIr, color_output: ColorOutput
) -> tuple[Source, ErrorList]:
    """Generates Rust source code and definitions for the provided Emboss IR."""
    errors = [[error.error(None, None, "Rust backend is not yet supported")]]
    if errors:
        _show_errors(errors, ir, color_output)
    return "", errors
