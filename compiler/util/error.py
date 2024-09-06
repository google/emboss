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

"""Error and warning message support for Emboss.

This module exports the error, warn, and note functions, which return a _Message
representing the error, warning, or note, respectively.  The format method of
the returned object can be used to render the message with source code snippets.

Throughout Emboss, messages are passed around as lists of lists of _Messages.
Each inner list represents a group of messages which should either all be
printed, or not printed; i.e., an error message and associated informational
messages.  For example, to indicate both a duplicate definition error and a
warning that a field is a reserved word, one might return:

    return [
        [
            error.error(file_name, location, "Duplicate definition),
            error.note(original_file_name, original_location,
                       "Original definition"),
        ],
        [
            error.warn(file_name, location, "Field name is a C reserved word.")
        ],
    ]
"""

from compiler.util import ir_data_utils
from compiler.util import parser_types

# Error levels; represented by the strings that will be included in messages.
ERROR = "error"
WARNING = "warning"
NOTE = "note"

# Colors; represented by the terminal escape sequences used to switch to them.
# These work out-of-the-box on Unix derivatives (Linux, *BSD, Mac OS X), and
# work on Windows using colorify.
BLACK = "\033[0;30m"
RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[0;33m"
BLUE = "\033[0;34m"
MAGENTA = "\033[0;35m"
CYAN = "\033[0;36m"
WHITE = "\033[0;37m"
BRIGHT_BLACK = "\033[0;1;30m"
BRIGHT_RED = "\033[0;1;31m"
BRIGHT_GREEN = "\033[0;1;32m"
BRIGHT_YELLOW = "\033[0;1;33m"
BRIGHT_BLUE = "\033[0;1;34m"
BRIGHT_MAGENTA = "\033[0;1;35m"
BRIGHT_CYAN = "\033[0;1;36m"
BRIGHT_WHITE = "\033[0;1;37m"
BOLD = "\033[0;1m"
RESET = "\033[0m"


def _copy(location):
    location = ir_data_utils.copy(location)
    if not location:
        location = parser_types.make_location((0, 0), (0, 0))
    return location


def error(source_file, location, message):
    """Returns an object representing an error message."""
    return _Message(source_file, _copy(location), ERROR, message)


def warn(source_file, location, message):
    """Returns an object representing a warning."""
    return _Message(source_file, _copy(location), WARNING, message)


def note(source_file, location, message):
    """Returns and object representing an informational note."""
    return _Message(source_file, _copy(location), NOTE, message)


class _Message(object):
    """_Message holds a human-readable message."""

    __slots__ = ("location", "source_file", "severity", "message")

    def __init__(self, source_file, location, severity, message):
        self.location = location
        self.source_file = source_file
        self.severity = severity
        self.message = message

    def format(self, source_code):
        """Formats the _Message for display.

        Arguments:
          source_code: A dict of file names to source texts.  This is used to
            render source snippets.

        Returns:
          A list of tuples.

          The first element of each tuple is an escape sequence used to put a Unix
          terminal into a particular color mode.  For use in non-Unix-terminal
          output, the string will match one of the color names exported by this
          module.

          The second element is a string containing text to show to the user.

          The text will not end with a newline character, nor will it include a
          RESET color element.

          To show non-colorized output, simply write the second element of each
          tuple, then a newline at the end.

          To show colorized output, write both the first and second element of each
          tuple, then a newline at the end.  Before exiting to the operating system,
          a RESET sequence should be emitted.
        """
        # TODO(bolms): Figure out how to get Vim, Emacs, etc. to parse Emboss error
        #     messages.
        severity_colors = {
            ERROR: (BRIGHT_RED, BOLD),
            WARNING: (BRIGHT_MAGENTA, BOLD),
            NOTE: (BRIGHT_BLACK, WHITE),
        }

        result = []
        if self.location.is_synthetic:
            pos = "[compiler bug]"
        else:
            pos = parser_types.format_position(self.location.start)
        source_name = self.source_file or "[prelude]"
        if not self.location.is_synthetic and self.source_file in source_code:
            source_lines = source_code[self.source_file].splitlines()
            source_line = source_lines[self.location.start.line - 1]
        else:
            source_line = ""
        lines = self.message.splitlines()
        for i in range(len(lines)):
            line = lines[i]
            # This is a little awkward, but we want to suppress the final newline in
            # the message.  This newline is final if and only if it is the last line
            # of the message and there is no source snippet.
            if i != len(lines) - 1 or source_line:
                line += "\n"
            result.append((BOLD, "{}:{}: ".format(source_name, pos)))
            if i == 0:
                severity = self.severity
            else:
                severity = NOTE
            result.append((severity_colors[severity][0], "{}: ".format(severity)))
            result.append((severity_colors[severity][1], line))
        if source_line:
            result.append((WHITE, source_line + "\n"))
            indicator_indent = " " * (self.location.start.column - 1)
            if self.location.start.line == self.location.end.line:
                indicator_caret = "^" * max(
                    1, self.location.end.column - self.location.start.column
                )
            else:
                indicator_caret = "^"
            result.append((BRIGHT_GREEN, indicator_indent + indicator_caret))
        return result

    def __repr__(self):
        return (
            "Message({source_file!r}, make_location(({start_line!r}, "
            "{start_column!r}), ({end_line!r}, {end_column!r}), "
            "{is_synthetic!r}), {severity!r}, {message!r})"
        ).format(
            source_file=self.source_file,
            start_line=self.location.start.line,
            start_column=self.location.start.column,
            end_line=self.location.end.line,
            end_column=self.location.end.column,
            is_synthetic=self.location.is_synthetic,
            severity=self.severity,
            message=self.message,
        )

    def __eq__(self, other):
        return (
            self.__class__ == other.__class__
            and self.location == other.location
            and self.source_file == other.source_file
            and self.severity == other.severity
            and self.message == other.message
        )

    def __ne__(self, other):
        return not self == other


def split_errors(errors):
    """Splits errors into (user_errors, synthetic_errors).

    Arguments:
        errors: A list of lists of _Message, which is a list of bundles of
            associated messages.

    Returns:
        (user_errors, synthetic_errors), where both user_errors and
        synthetic_errors are lists of lists of _Message.  synthetic_errors will
        contain all bundles that reference any synthetic source_location, and
        user_errors will contain the rest.

        The intent is that user_errors can be shown to end users, while
        synthetic_errors should generally be suppressed.
    """
    synthetic_errors = []
    user_errors = []
    for error_block in errors:
        if any(message.location.is_synthetic for message in error_block):
            synthetic_errors.append(error_block)
        else:
            user_errors.append(error_block)
    return user_errors, synthetic_errors


def filter_errors(errors):
    """Returns the non-synthetic errors from `errors`."""
    return split_errors(errors)[0]


def format_errors(errors, source_codes, use_color=False):
    """Formats error messages with source code snippets."""
    result = []
    for error_group in errors:
        assert error_group, "Found empty error_group!"
        for message in error_group:
            if use_color:
                result.append(
                    "".join(e[0] + e[1] + RESET for e in message.format(source_codes))
                )
            else:
                result.append("".join(e[1] for e in message.format(source_codes)))
    return "\n".join(result)


def make_error_from_parse_error(file_name, parse_error):
    return [
        error(
            file_name,
            parse_error.token.source_location,
            "{code}\n"
            "Found {text!r} ({symbol}), expected {expected}.".format(
                code=parse_error.code or "Syntax error",
                text=parse_error.token.text,
                symbol=parse_error.token.symbol,
                expected=", ".join(parse_error.expected_tokens),
            ),
        )
    ]
