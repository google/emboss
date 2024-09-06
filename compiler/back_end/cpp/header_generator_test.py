# Copyright 2023 Google LLC
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

"""Tests for attribute_checker.py."""

import unittest
from compiler.back_end.cpp import header_generator
from compiler.front_end import glue
from compiler.util import error
from compiler.util import ir_data
from compiler.util import ir_data_utils
from compiler.util import test_util


def _make_ir_from_emb(emb_text, name="m.emb"):
    ir, unused_debug_info, errors = glue.parse_emboss_file(
        name, test_util.dict_file_reader({name: emb_text})
    )
    assert not errors
    return ir


class NormalizeIrTest(unittest.TestCase):

    def test_accepts_string_attribute(self):
        ir = _make_ir_from_emb('[(cpp) namespace: "foo"]\n')
        self.assertEqual([], header_generator.generate_header(ir)[1])

    def test_rejects_wrong_type_for_string_attribute(self):
        ir = _make_ir_from_emb("[(cpp) namespace: 9]\n")
        attr = ir.module[0].attribute[0]
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        attr.value.source_location,
                        "Attribute '(cpp) namespace' must have a string value.",
                    )
                ]
            ],
            header_generator.generate_header(ir)[1],
        )

    def test_rejects_emboss_internal_attribute_with_back_end_specifier(self):
        ir = _make_ir_from_emb('[(cpp) byte_order: "LittleEndian"]\n')
        attr = ir.module[0].attribute[0]
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        attr.name.source_location,
                        "Unknown attribute '(cpp) byte_order' on module 'm.emb'.",
                    )
                ]
            ],
            header_generator.generate_header(ir)[1],
        )

    def test_accepts_enum_case(self):
        mod_ir = _make_ir_from_emb('[(cpp) $default enum_case: "kCamelCase"]')
        self.assertEqual([], header_generator.generate_header(mod_ir)[1])
        enum_ir = _make_ir_from_emb(
            "enum Foo:\n"
            '  [(cpp) $default enum_case: "kCamelCase"]\n'
            "  BAR = 1\n"
            "  BAZ = 2\n"
        )
        self.assertEqual([], header_generator.generate_header(enum_ir)[1])
        enum_value_ir = _make_ir_from_emb(
            "enum Foo:\n"
            '  BAR = 1  [(cpp) enum_case: "kCamelCase"]\n'
            "  BAZ = 2\n"
            '    [(cpp) enum_case: "kCamelCase"]\n'
        )
        self.assertEqual([], header_generator.generate_header(enum_value_ir)[1])
        enum_in_struct_ir = _make_ir_from_emb(
            "struct Outer:\n"
            '  [(cpp) $default enum_case: "kCamelCase"]\n'
            "  enum Inner:\n"
            "    BAR = 1\n"
            "    BAZ = 2\n"
        )
        self.assertEqual([], header_generator.generate_header(enum_in_struct_ir)[1])
        enum_in_bits_ir = _make_ir_from_emb(
            "bits Outer:\n"
            '  [(cpp) $default enum_case: "kCamelCase"]\n'
            "  enum Inner:\n"
            "    BAR = 1\n"
            "    BAZ = 2\n"
        )
        self.assertEqual([], header_generator.generate_header(enum_in_bits_ir)[1])
        enum_ir = _make_ir_from_emb(
            "enum Foo:\n"
            '  [(cpp) $default enum_case: "SHOUTY_CASE,"]\n'
            "  BAR = 1\n"
            "  BAZ = 2\n"
        )
        self.assertEqual([], header_generator.generate_header(enum_ir)[1])
        enum_ir = _make_ir_from_emb(
            "enum Foo:\n"
            '  [(cpp) $default enum_case: "SHOUTY_CASE   ,kCamelCase"]\n'
            "  BAR = 1\n"
            "  BAZ = 2\n"
        )
        self.assertEqual([], header_generator.generate_header(enum_ir)[1])

    def test_rejects_bad_enum_case_at_start(self):
        ir = _make_ir_from_emb(
            "enum Foo:\n"
            '  [(cpp) $default enum_case: "SHORTY_CASE, kCamelCase"]\n'
            "  BAR = 1\n"
            "  BAZ = 2\n"
        )
        attr = ir.module[0].type[0].attribute[0]

        bad_case_source_location = ir_data.Location()
        bad_case_source_location = ir_data_utils.builder(bad_case_source_location)
        bad_case_source_location.CopyFrom(attr.value.source_location)
        # Location of SHORTY_CASE in the attribute line.
        bad_case_source_location.start.column = 30
        bad_case_source_location.end.column = 41

        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        bad_case_source_location,
                        'Unsupported enum case "SHORTY_CASE", '
                        "supported cases are: SHOUTY_CASE, kCamelCase.",
                    )
                ]
            ],
            header_generator.generate_header(ir)[1],
        )

    def test_rejects_bad_enum_case_in_middle(self):
        ir = _make_ir_from_emb(
            "enum Foo:\n"
            '  [(cpp) $default enum_case: "SHOUTY_CASE, bad_CASE, kCamelCase"]\n'
            "  BAR = 1\n"
            "  BAZ = 2\n"
        )
        attr = ir.module[0].type[0].attribute[0]

        bad_case_source_location = ir_data.Location()
        bad_case_source_location = ir_data_utils.builder(bad_case_source_location)
        bad_case_source_location.CopyFrom(attr.value.source_location)
        # Location of bad_CASE in the attribute line.
        bad_case_source_location.start.column = 43
        bad_case_source_location.end.column = 51

        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        bad_case_source_location,
                        'Unsupported enum case "bad_CASE", '
                        "supported cases are: SHOUTY_CASE, kCamelCase.",
                    )
                ]
            ],
            header_generator.generate_header(ir)[1],
        )

    def test_rejects_bad_enum_case_at_end(self):
        ir = _make_ir_from_emb(
            "enum Foo:\n"
            '  [(cpp) $default enum_case: "SHOUTY_CASE, kCamelCase, BAD_case"]\n'
            "  BAR = 1\n"
            "  BAZ = 2\n"
        )
        attr = ir.module[0].type[0].attribute[0]

        bad_case_source_location = ir_data.Location()
        bad_case_source_location = ir_data_utils.builder(bad_case_source_location)
        bad_case_source_location.CopyFrom(attr.value.source_location)
        # Location of BAD_case in the attribute line.
        bad_case_source_location.start.column = 55
        bad_case_source_location.end.column = 63

        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        bad_case_source_location,
                        'Unsupported enum case "BAD_case", '
                        "supported cases are: SHOUTY_CASE, kCamelCase.",
                    )
                ]
            ],
            header_generator.generate_header(ir)[1],
        )

    def test_rejects_duplicate_enum_case(self):
        ir = _make_ir_from_emb(
            "enum Foo:\n"
            '  [(cpp) $default enum_case: "SHOUTY_CASE, SHOUTY_CASE"]\n'
            "  BAR = 1\n"
            "  BAZ = 2\n"
        )
        attr = ir.module[0].type[0].attribute[0]

        bad_case_source_location = ir_data.Location()
        bad_case_source_location = ir_data_utils.builder(bad_case_source_location)
        bad_case_source_location.CopyFrom(attr.value.source_location)
        # Location of the second SHOUTY_CASE in the attribute line.
        bad_case_source_location.start.column = 43
        bad_case_source_location.end.column = 54

        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        bad_case_source_location,
                        'Duplicate enum case "SHOUTY_CASE".',
                    )
                ]
            ],
            header_generator.generate_header(ir)[1],
        )

    def test_rejects_empty_enum_case(self):
        # Double comma
        ir = _make_ir_from_emb(
            "enum Foo:\n"
            '  [(cpp) $default enum_case: "SHOUTY_CASE,, kCamelCase"]\n'
            "  BAR = 1\n"
            "  BAZ = 2\n"
        )
        attr = ir.module[0].type[0].attribute[0]

        bad_case_source_location = ir_data.Location()
        bad_case_source_location = ir_data_utils.builder(bad_case_source_location)
        bad_case_source_location.CopyFrom(attr.value.source_location)
        # Location of excess comma.
        bad_case_source_location.start.column = 42
        bad_case_source_location.end.column = 42

        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        bad_case_source_location,
                        "Empty enum case (or excess comma).",
                    )
                ]
            ],
            header_generator.generate_header(ir)[1],
        )

        # Leading comma
        ir = _make_ir_from_emb(
            "enum Foo:\n"
            '  [(cpp) $default enum_case: ", SHOUTY_CASE, kCamelCase"]\n'
            "  BAR = 1\n"
            "  BAZ = 2\n"
        )

        bad_case_source_location.start.column = 30
        bad_case_source_location.end.column = 30

        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        bad_case_source_location,
                        "Empty enum case (or excess comma).",
                    )
                ]
            ],
            header_generator.generate_header(ir)[1],
        )

        # Excess trailing comma
        ir = _make_ir_from_emb(
            "enum Foo:\n"
            '  [(cpp) $default enum_case: "SHOUTY_CASE, kCamelCase,,"]\n'
            "  BAR = 1\n"
            "  BAZ = 2\n"
        )

        bad_case_source_location.start.column = 54
        bad_case_source_location.end.column = 54

        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        bad_case_source_location,
                        "Empty enum case (or excess comma).",
                    )
                ]
            ],
            header_generator.generate_header(ir)[1],
        )

        # Whitespace enum case
        ir = _make_ir_from_emb(
            "enum Foo:\n"
            '  [(cpp) $default enum_case: "SHOUTY_CASE,   , kCamelCase"]\n'
            "  BAR = 1\n"
            "  BAZ = 2\n"
        )

        bad_case_source_location.start.column = 45
        bad_case_source_location.end.column = 45

        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        bad_case_source_location,
                        "Empty enum case (or excess comma).",
                    )
                ]
            ],
            header_generator.generate_header(ir)[1],
        )

        # Empty enum_case string
        ir = _make_ir_from_emb(
            "enum Foo:\n"
            '  [(cpp) $default enum_case: ""]\n'
            "  BAR = 1\n"
            "  BAZ = 2\n"
        )

        bad_case_source_location.start.column = 30
        bad_case_source_location.end.column = 30

        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        bad_case_source_location,
                        "Empty enum case (or excess comma).",
                    )
                ]
            ],
            header_generator.generate_header(ir)[1],
        )

        # Whitespace enum_case string
        ir = _make_ir_from_emb(
            "enum Foo:\n"
            '  [(cpp) $default enum_case: "     "]\n'
            "  BAR = 1\n"
            "  BAZ = 2\n"
        )

        bad_case_source_location.start.column = 35
        bad_case_source_location.end.column = 35

        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        bad_case_source_location,
                        "Empty enum case (or excess comma).",
                    )
                ]
            ],
            header_generator.generate_header(ir)[1],
        )

        # One-character whitespace enum_case string
        ir = _make_ir_from_emb(
            "enum Foo:\n"
            '  [(cpp) $default enum_case: " "]\n'
            "  BAR = 1\n"
            "  BAZ = 2\n"
        )

        bad_case_source_location.start.column = 31
        bad_case_source_location.end.column = 31

        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        bad_case_source_location,
                        "Empty enum case (or excess comma).",
                    )
                ]
            ],
            header_generator.generate_header(ir)[1],
        )

    def test_accepts_namespace(self):
        for test in [
            '[(cpp) namespace: "basic"]\n',
            '[(cpp) namespace: "multiple::components"]\n',
            '[(cpp) namespace: "::absolute"]\n',
            '[(cpp) namespace: "::fully::qualified"]\n',
            '[(cpp) namespace: "CAN::Be::cAPITAL"]\n',
            '[(cpp) namespace: "trailingNumbers54321"]\n',
            '[(cpp) namespace: "containing4321numbers"]\n',
            '[(cpp) namespace: "can_have_underscores"]\n',
            '[(cpp) namespace: "_initial_underscore"]\n',
            '[(cpp) namespace: "_initial::_underscore"]\n',
            '[(cpp) namespace: "::_initial::_underscore"]\n',
            '[(cpp) namespace: "trailing_underscore_"]\n',
            '[(cpp) namespace: "trailing_::underscore_"]\n',
            '[(cpp) namespace: "::trailing_::underscore_"]\n',
            '[(cpp) namespace: " spaces "]\n',
            '[(cpp) namespace: "with :: spaces"]\n',
            '[(cpp) namespace: "   ::fully:: qualified :: with::spaces"]\n',
        ]:
            ir = _make_ir_from_emb(test)
            self.assertEqual([], header_generator.generate_header(ir)[1])

    def test_rejects_non_namespace_strings(self):
        for test in [
            '[(cpp) namespace: "5th::avenue"]\n',
            '[(cpp) namespace: "can\'t::have::apostrophe"]\n',
            '[(cpp) namespace: "cannot-have-dash"]\n',
            '[(cpp) namespace: "no/slashes"]\n',
            '[(cpp) namespace: "no\\\\slashes"]\n',
            '[(cpp) namespace: "apostrophes*are*rejected"]\n',
            '[(cpp) namespace: "avoid.dot"]\n',
            '[(cpp) namespace: "does5+5"]\n',
            '[(cpp) namespace: "=10"]\n',
            '[(cpp) namespace: "?"]\n',
            '[(cpp) namespace: "reject::spaces in::components"]\n',
            '[(cpp) namespace: "totally::valid::but::extra         +"]\n',
            '[(cpp) namespace: "totally::valid::but::extra         ::?"]\n',
            '[(cpp) namespace: "< totally::valid::but::extra"]\n',
            '[(cpp) namespace: "< ::totally::valid::but::extra"]\n',
            '[(cpp) namespace: "::totally::valid::but::extra::"]\n',
            '[(cpp) namespace: ":::extra::colon"]\n',
            '[(cpp) namespace: "::extra:::colon"]\n',
        ]:
            ir = _make_ir_from_emb(test)
            attr = ir.module[0].attribute[0]
            self.assertEqual(
                [
                    [
                        error.error(
                            "m.emb",
                            attr.value.source_location,
                            "Invalid namespace, must be a valid C++ namespace, such "
                            'as "abc", "abc::def", or "::abc::def::ghi" (ISO/IEC '
                            "14882:2017 enclosing-namespace-specifier).",
                        )
                    ]
                ],
                header_generator.generate_header(ir)[1],
            )

    def test_rejects_empty_namespace(self):
        for test in [
            '[(cpp) namespace: ""]\n',
            '[(cpp) namespace: " "]\n',
            '[(cpp) namespace: "    "]\n',
        ]:
            ir = _make_ir_from_emb(test)
            attr = ir.module[0].attribute[0]
            self.assertEqual(
                [
                    [
                        error.error(
                            "m.emb",
                            attr.value.source_location,
                            "Empty namespace value is not allowed.",
                        )
                    ]
                ],
                header_generator.generate_header(ir)[1],
            )

    def test_rejects_global_namespace(self):
        for test in [
            '[(cpp) namespace: "::"]\n',
            '[(cpp) namespace: "  ::"]\n',
            '[(cpp) namespace: ":: "]\n',
            '[(cpp) namespace: " ::  "]\n',
        ]:
            ir = _make_ir_from_emb(test)
            attr = ir.module[0].attribute[0]
            self.assertEqual(
                [
                    [
                        error.error(
                            "m.emb",
                            attr.value.source_location,
                            "Global namespace is not allowed.",
                        )
                    ]
                ],
                header_generator.generate_header(ir)[1],
            )

    def test_rejects_reserved_namespace(self):
        for test, expected in [
            # Only component
            ('[(cpp) namespace: "class"]\n', "class"),
            # Only component, fully qualified name
            ('[(cpp) namespace: "::const"]\n', "const"),
            # First component
            ('[(cpp) namespace: "if::valid"]\n', "if"),
            # First component, fully qualified name
            ('[(cpp) namespace: "::auto::pilot"]\n', "auto"),
            # Last component
            ('[(cpp) namespace: "make::do"]\n', "do"),
            # Middle component
            ('[(cpp) namespace: "our::new::product"]\n', "new"),
        ]:
            ir = _make_ir_from_emb(test)
            attr = ir.module[0].attribute[0]

            self.assertEqual(
                [
                    [
                        error.error(
                            "m.emb",
                            attr.value.source_location,
                            f'Reserved word "{expected}" is not allowed '
                            f"as a namespace component.",
                        )
                    ]
                ],
                header_generator.generate_header(ir)[1],
            )


if __name__ == "__main__":
    unittest.main()
