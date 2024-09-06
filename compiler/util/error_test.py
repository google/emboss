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

"""Tests for util.error."""

import unittest

from compiler.util import error
from compiler.util import parser_types


class MessageTest(unittest.TestCase):
    """Tests for _Message, as returned by error, warn, and note."""

    def test_error(self):
        error_message = error.error(
            "foo.emb", parser_types.make_location((3, 4), (3, 6)), "Bad thing"
        )
        self.assertEqual("foo.emb", error_message.source_file)
        self.assertEqual(error.ERROR, error_message.severity)
        self.assertEqual(
            parser_types.make_location((3, 4), (3, 6)), error_message.location
        )
        self.assertEqual("Bad thing", error_message.message)
        sourceless_format = error_message.format({})
        sourced_format = error_message.format({"foo.emb": "\n\nabcdefghijklm"})
        self.assertEqual(
            "foo.emb:3:4: error: Bad thing", "".join([x[1] for x in sourceless_format])
        )
        self.assertEqual(
            [
                (error.BOLD, "foo.emb:3:4: "),  # Location
                (error.BRIGHT_RED, "error: "),  # Severity
                (error.BOLD, "Bad thing"),  # Message
            ],
            sourceless_format,
        )
        self.assertEqual(
            "foo.emb:3:4: error: Bad thing\n" "abcdefghijklm\n" "   ^^",
            "".join([x[1] for x in sourced_format]),
        )
        self.assertEqual(
            [
                (error.BOLD, "foo.emb:3:4: "),  # Location
                (error.BRIGHT_RED, "error: "),  # Severity
                (error.BOLD, "Bad thing\n"),  # Message
                (error.WHITE, "abcdefghijklm\n"),  # Source snippet
                (error.BRIGHT_GREEN, "   ^^"),  # Error column indicator
            ],
            sourced_format,
        )

    def test_synthetic_error(self):
        error_message = error.error(
            "foo.emb", parser_types.make_location((3, 4), (3, 6), True), "Bad thing"
        )
        sourceless_format = error_message.format({})
        sourced_format = error_message.format({"foo.emb": "\n\nabcdefghijklm"})
        self.assertEqual(
            "foo.emb:[compiler bug]: error: Bad thing",
            "".join([x[1] for x in sourceless_format]),
        )
        self.assertEqual(
            [
                (error.BOLD, "foo.emb:[compiler bug]: "),  # Location
                (error.BRIGHT_RED, "error: "),  # Severity
                (error.BOLD, "Bad thing"),  # Message
            ],
            sourceless_format,
        )
        self.assertEqual(
            "foo.emb:[compiler bug]: error: Bad thing",
            "".join([x[1] for x in sourced_format]),
        )
        self.assertEqual(
            [
                (error.BOLD, "foo.emb:[compiler bug]: "),  # Location
                (error.BRIGHT_RED, "error: "),  # Severity
                (error.BOLD, "Bad thing"),  # Message
            ],
            sourced_format,
        )

    def test_prelude_as_file_name(self):
        error_message = error.error(
            "", parser_types.make_location((3, 4), (3, 6)), "Bad thing"
        )
        self.assertEqual("", error_message.source_file)
        self.assertEqual(error.ERROR, error_message.severity)
        self.assertEqual(
            parser_types.make_location((3, 4), (3, 6)), error_message.location
        )
        self.assertEqual("Bad thing", error_message.message)
        sourceless_format = error_message.format({})
        sourced_format = error_message.format({"": "\n\nabcdefghijklm"})
        self.assertEqual(
            "[prelude]:3:4: error: Bad thing",
            "".join([x[1] for x in sourceless_format]),
        )
        self.assertEqual(
            [
                (error.BOLD, "[prelude]:3:4: "),  # Location
                (error.BRIGHT_RED, "error: "),  # Severity
                (error.BOLD, "Bad thing"),  # Message
            ],
            sourceless_format,
        )
        self.assertEqual(
            "[prelude]:3:4: error: Bad thing\n" "abcdefghijklm\n" "   ^^",
            "".join([x[1] for x in sourced_format]),
        )
        self.assertEqual(
            [
                (error.BOLD, "[prelude]:3:4: "),  # Location
                (error.BRIGHT_RED, "error: "),  # Severity
                (error.BOLD, "Bad thing\n"),  # Message
                (error.WHITE, "abcdefghijklm\n"),  # Source snippet
                (error.BRIGHT_GREEN, "   ^^"),  # Error column indicator
            ],
            sourced_format,
        )

    def test_multiline_error_source(self):
        error_message = error.error(
            "foo.emb", parser_types.make_location((3, 4), (4, 6)), "Bad thing"
        )
        self.assertEqual("foo.emb", error_message.source_file)
        self.assertEqual(error.ERROR, error_message.severity)
        self.assertEqual(
            parser_types.make_location((3, 4), (4, 6)), error_message.location
        )
        self.assertEqual("Bad thing", error_message.message)
        sourceless_format = error_message.format({})
        sourced_format = error_message.format(
            {"foo.emb": "\n\nabcdefghijklm\nnopqrstuv"}
        )
        self.assertEqual(
            "foo.emb:3:4: error: Bad thing", "".join([x[1] for x in sourceless_format])
        )
        self.assertEqual(
            [
                (error.BOLD, "foo.emb:3:4: "),  # Location
                (error.BRIGHT_RED, "error: "),  # Severity
                (error.BOLD, "Bad thing"),  # Message
            ],
            sourceless_format,
        )
        self.assertEqual(
            "foo.emb:3:4: error: Bad thing\n" "abcdefghijklm\n" "   ^",
            "".join([x[1] for x in sourced_format]),
        )
        self.assertEqual(
            [
                (error.BOLD, "foo.emb:3:4: "),  # Location
                (error.BRIGHT_RED, "error: "),  # Severity
                (error.BOLD, "Bad thing\n"),  # Message
                (error.WHITE, "abcdefghijklm\n"),  # Source snippet
                (error.BRIGHT_GREEN, "   ^"),  # Error column indicator
            ],
            sourced_format,
        )

    def test_multiline_error(self):
        error_message = error.error(
            "foo.emb",
            parser_types.make_location((3, 4), (3, 6)),
            "Bad thing\nSome explanation\nMore explanation",
        )
        self.assertEqual("foo.emb", error_message.source_file)
        self.assertEqual(error.ERROR, error_message.severity)
        self.assertEqual(
            parser_types.make_location((3, 4), (3, 6)), error_message.location
        )
        self.assertEqual(
            "Bad thing\nSome explanation\nMore explanation", error_message.message
        )
        sourceless_format = error_message.format({})
        sourced_format = error_message.format(
            {"foo.emb": "\n\nabcdefghijklm\nnopqrstuv"}
        )
        self.assertEqual(
            "foo.emb:3:4: error: Bad thing\n"
            "foo.emb:3:4: note: Some explanation\n"
            "foo.emb:3:4: note: More explanation",
            "".join([x[1] for x in sourceless_format]),
        )
        self.assertEqual(
            [
                (error.BOLD, "foo.emb:3:4: "),  # Location
                (error.BRIGHT_RED, "error: "),  # Severity
                (error.BOLD, "Bad thing\n"),  # Message
                (error.BOLD, "foo.emb:3:4: "),  # Location, line 2
                (error.BRIGHT_BLACK, "note: "),  # "Note" severity, line 2
                (error.WHITE, "Some explanation\n"),  # Message, line 2
                (error.BOLD, "foo.emb:3:4: "),  # Location, line 3
                (error.BRIGHT_BLACK, "note: "),  # "Note" severity, line 3
                (error.WHITE, "More explanation"),  # Message, line 3
            ],
            sourceless_format,
        )
        self.assertEqual(
            "foo.emb:3:4: error: Bad thing\n"
            "foo.emb:3:4: note: Some explanation\n"
            "foo.emb:3:4: note: More explanation\n"
            "abcdefghijklm\n"
            "   ^^",
            "".join([x[1] for x in sourced_format]),
        )
        self.assertEqual(
            [
                (error.BOLD, "foo.emb:3:4: "),  # Location
                (error.BRIGHT_RED, "error: "),  # Severity
                (error.BOLD, "Bad thing\n"),  # Message
                (error.BOLD, "foo.emb:3:4: "),  # Location, line 2
                (error.BRIGHT_BLACK, "note: "),  # "Note" severity, line 2
                (error.WHITE, "Some explanation\n"),  # Message, line 2
                (error.BOLD, "foo.emb:3:4: "),  # Location, line 3
                (error.BRIGHT_BLACK, "note: "),  # "Note" severity, line 3
                (error.WHITE, "More explanation\n"),  # Message, line 3
                (error.WHITE, "abcdefghijklm\n"),  # Source snippet
                (error.BRIGHT_GREEN, "   ^^"),  # Column indicator
            ],
            sourced_format,
        )

    def test_warn(self):
        warning_message = error.warn(
            "foo.emb", parser_types.make_location((3, 4), (3, 6)), "Not good thing"
        )
        self.assertEqual("foo.emb", warning_message.source_file)
        self.assertEqual(error.WARNING, warning_message.severity)
        self.assertEqual(
            parser_types.make_location((3, 4), (3, 6)), warning_message.location
        )
        self.assertEqual("Not good thing", warning_message.message)
        sourced_format = warning_message.format({"foo.emb": "\n\nabcdefghijklm"})
        self.assertEqual(
            "foo.emb:3:4: warning: Not good thing\n" "abcdefghijklm\n" "   ^^",
            "".join([x[1] for x in sourced_format]),
        )
        self.assertEqual(
            [
                (error.BOLD, "foo.emb:3:4: "),  # Location
                (error.BRIGHT_MAGENTA, "warning: "),  # Severity
                (error.BOLD, "Not good thing\n"),  # Message
                (error.WHITE, "abcdefghijklm\n"),  # Source snippet
                (error.BRIGHT_GREEN, "   ^^"),  # Column indicator
            ],
            sourced_format,
        )

    def test_note(self):
        note_message = error.note(
            "foo.emb", parser_types.make_location((3, 4), (3, 6)), "OK thing"
        )
        self.assertEqual("foo.emb", note_message.source_file)
        self.assertEqual(error.NOTE, note_message.severity)
        self.assertEqual(
            parser_types.make_location((3, 4), (3, 6)), note_message.location
        )
        self.assertEqual("OK thing", note_message.message)
        sourced_format = note_message.format({"foo.emb": "\n\nabcdefghijklm"})
        self.assertEqual(
            "foo.emb:3:4: note: OK thing\n" "abcdefghijklm\n" "   ^^",
            "".join([x[1] for x in sourced_format]),
        )
        self.assertEqual(
            [
                (error.BOLD, "foo.emb:3:4: "),  # Location
                (error.BRIGHT_BLACK, "note: "),  # Severity
                (error.WHITE, "OK thing\n"),  # Message
                (error.WHITE, "abcdefghijklm\n"),  # Source snippet
                (error.BRIGHT_GREEN, "   ^^"),  # Column indicator
            ],
            sourced_format,
        )

    def test_equality(self):
        note_message = error.note(
            "foo.emb", parser_types.make_location((3, 4), (3, 6)), "thing"
        )
        self.assertEqual(
            note_message,
            error.note("foo.emb", parser_types.make_location((3, 4), (3, 6)), "thing"),
        )
        self.assertNotEqual(
            note_message,
            error.warn("foo.emb", parser_types.make_location((3, 4), (3, 6)), "thing"),
        )
        self.assertNotEqual(
            note_message,
            error.note("foo2.emb", parser_types.make_location((3, 4), (3, 6)), "thing"),
        )
        self.assertNotEqual(
            note_message,
            error.note("foo.emb", parser_types.make_location((2, 4), (3, 6)), "thing"),
        )
        self.assertNotEqual(
            note_message,
            error.note("foo.emb", parser_types.make_location((3, 4), (3, 6)), "thing2"),
        )


class StringTest(unittest.TestCase):
    """Tests for strings."""

    # These strings are a fixed part of the API.

    def test_color_strings(self):
        self.assertEqual("\033[0;30m", error.BLACK)
        self.assertEqual("\033[0;31m", error.RED)
        self.assertEqual("\033[0;32m", error.GREEN)
        self.assertEqual("\033[0;33m", error.YELLOW)
        self.assertEqual("\033[0;34m", error.BLUE)
        self.assertEqual("\033[0;35m", error.MAGENTA)
        self.assertEqual("\033[0;36m", error.CYAN)
        self.assertEqual("\033[0;37m", error.WHITE)
        self.assertEqual("\033[0;1;30m", error.BRIGHT_BLACK)
        self.assertEqual("\033[0;1;31m", error.BRIGHT_RED)
        self.assertEqual("\033[0;1;32m", error.BRIGHT_GREEN)
        self.assertEqual("\033[0;1;33m", error.BRIGHT_YELLOW)
        self.assertEqual("\033[0;1;34m", error.BRIGHT_BLUE)
        self.assertEqual("\033[0;1;35m", error.BRIGHT_MAGENTA)
        self.assertEqual("\033[0;1;36m", error.BRIGHT_CYAN)
        self.assertEqual("\033[0;1;37m", error.BRIGHT_WHITE)
        self.assertEqual("\033[0;1m", error.BOLD)
        self.assertEqual("\033[0m", error.RESET)

    def test_error_strings(self):
        self.assertEqual("error", error.ERROR)
        self.assertEqual("warning", error.WARNING)
        self.assertEqual("note", error.NOTE)


class SplitErrorsTest(unittest.TestCase):

    def test_split_errors(self):
        user_error = [
            error.error(
                "foo.emb", parser_types.make_location((1, 2), (3, 4)), "Bad thing"
            ),
            error.note(
                "foo.emb",
                parser_types.make_location((3, 4), (5, 6)),
                "Note: bad thing referrent",
            ),
        ]
        user_error_2 = [
            error.error(
                "foo.emb", parser_types.make_location((8, 9), (10, 11)), "Bad thing"
            ),
            error.note(
                "foo.emb",
                parser_types.make_location((10, 11), (12, 13)),
                "Note: bad thing referrent",
            ),
        ]
        synthetic_error = [
            error.error(
                "foo.emb", parser_types.make_location((1, 2), (3, 4)), "Bad thing"
            ),
            error.note(
                "foo.emb",
                parser_types.make_location((3, 4), (5, 6), True),
                "Note: bad thing referrent",
            ),
        ]
        synthetic_error_2 = [
            error.error(
                "foo.emb",
                parser_types.make_location((8, 9), (10, 11), True),
                "Bad thing",
            ),
            error.note(
                "foo.emb",
                parser_types.make_location((10, 11), (12, 13)),
                "Note: bad thing referrent",
            ),
        ]
        user_errors, synthetic_errors = error.split_errors(
            [user_error, synthetic_error]
        )
        self.assertEqual([user_error], user_errors)
        self.assertEqual([synthetic_error], synthetic_errors)
        user_errors, synthetic_errors = error.split_errors(
            [synthetic_error, user_error]
        )
        self.assertEqual([user_error], user_errors)
        self.assertEqual([synthetic_error], synthetic_errors)
        user_errors, synthetic_errors = error.split_errors(
            [synthetic_error, user_error, synthetic_error_2, user_error_2]
        )
        self.assertEqual([user_error, user_error_2], user_errors)
        self.assertEqual([synthetic_error, synthetic_error_2], synthetic_errors)

    def test_filter_errors(self):
        user_error = [
            error.error(
                "foo.emb", parser_types.make_location((1, 2), (3, 4)), "Bad thing"
            ),
            error.note(
                "foo.emb",
                parser_types.make_location((3, 4), (5, 6)),
                "Note: bad thing referrent",
            ),
        ]
        synthetic_error = [
            error.error(
                "foo.emb", parser_types.make_location((1, 2), (3, 4)), "Bad thing"
            ),
            error.note(
                "foo.emb",
                parser_types.make_location((3, 4), (5, 6), True),
                "Note: bad thing referrent",
            ),
        ]
        synthetic_error_2 = [
            error.error(
                "foo.emb",
                parser_types.make_location((8, 9), (10, 11), True),
                "Bad thing",
            ),
            error.note(
                "foo.emb",
                parser_types.make_location((10, 11), (12, 13)),
                "Note: bad thing referrent",
            ),
        ]
        self.assertEqual(
            [user_error],
            error.filter_errors([synthetic_error, user_error, synthetic_error_2]),
        )


class FormatErrorsTest(unittest.TestCase):

    def test_format_errors(self):
        errors = [
            [error.note("foo.emb", parser_types.make_location((3, 4), (3, 6)), "note")]
        ]
        sources = {"foo.emb": "x\ny\nz  bcd\nq\n"}
        self.assertEqual(
            "foo.emb:3:4: note: note\n" "z  bcd\n" "   ^^",
            error.format_errors(errors, sources),
        )
        bold = error.BOLD
        reset = error.RESET
        white = error.WHITE
        bright_black = error.BRIGHT_BLACK
        bright_green = error.BRIGHT_GREEN
        self.assertEqual(
            bold
            + "foo.emb:3:4: "
            + reset
            + bright_black
            + "note: "
            + reset
            + white
            + "note\n"
            + reset
            + white
            + "z  bcd\n"
            + reset
            + bright_green
            + "   ^^"
            + reset,
            error.format_errors(errors, sources, use_color=True),
        )


if __name__ == "__main__":
    unittest.main()
