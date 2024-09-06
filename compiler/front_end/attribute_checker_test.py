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

"""Tests for attribute_checker.py."""

import unittest
from compiler.front_end import attribute_checker
from compiler.front_end import glue
from compiler.util import error
from compiler.util import ir_data
from compiler.util import ir_util
from compiler.util import test_util

# These are not shared with attribute_checker.py because their values are part
# of the contract with back ends.
_BYTE_ORDER = "byte_order"
_FIXED_SIZE = "fixed_size_in_bits"
_IS_SIGNED = "is_signed"
_MAX_BITS = "maximum_bits"


def _make_ir_from_emb(emb_text, name="m.emb"):
    ir, unused_debug_info, errors = glue.parse_emboss_file(
        name,
        test_util.dict_file_reader({name: emb_text}),
        stop_before_step="normalize_and_verify",
    )
    assert not errors
    return ir


class NormalizeIrTest(unittest.TestCase):

    def test_rejects_may_be_used_as_integer(self):
        enum_ir = _make_ir_from_emb(
            "enum Foo:\n" "  [may_be_used_as_integer: false]\n" "  VALUE = 1\n"
        )
        enum_type_ir = enum_ir.module[0].type[0]
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        enum_type_ir.attribute[0].name.source_location,
                        "Unknown attribute 'may_be_used_as_integer' on enum 'Foo'.",
                    )
                ]
            ],
            attribute_checker.normalize_and_verify(enum_ir),
        )

    def test_adds_fixed_size_attribute_to_struct(self):
        # field2 is intentionally after field3, in order to trigger certain code
        # paths in attribute_checker.py.
        struct_ir = _make_ir_from_emb(
            '[$default byte_order: "LittleEndian"]\n'
            "struct Foo:\n"
            "  0 [+2]  UInt  field1\n"
            "  4 [+4]  UInt  field2\n"
            "  2 [+2]  UInt  field3\n"
        )
        self.assertEqual([], attribute_checker.normalize_and_verify(struct_ir))
        size_attr = ir_util.get_attribute(
            struct_ir.module[0].type[0].attribute, _FIXED_SIZE
        )
        self.assertEqual(64, ir_util.constant_value(size_attr.expression))
        self.assertEqual(
            struct_ir.module[0].type[0].source_location, size_attr.source_location
        )

    def test_adds_fixed_size_attribute_to_struct_with_virtual_field(self):
        struct_ir = _make_ir_from_emb(
            '[$default byte_order: "LittleEndian"]\n'
            "struct Foo:\n"
            "  0 [+2]  UInt  field1\n"
            "  let field2 = field1\n"
            "  2 [+2]  UInt  field3\n"
        )
        self.assertEqual([], attribute_checker.normalize_and_verify(struct_ir))
        size_attr = ir_util.get_attribute(
            struct_ir.module[0].type[0].attribute, _FIXED_SIZE
        )
        self.assertEqual(32, ir_util.constant_value(size_attr.expression))
        self.assertEqual(
            struct_ir.module[0].type[0].source_location, size_attr.source_location
        )

    def test_adds_fixed_size_attribute_to_anonymous_bits(self):
        struct_ir = _make_ir_from_emb(
            '[$default byte_order: "LittleEndian"]\n'
            "struct Foo:\n"
            "  0 [+4]  bits:\n"
            "    0 [+8]  UInt  field\n"
        )
        self.assertEqual([], attribute_checker.normalize_and_verify(struct_ir))
        size_attr = ir_util.get_attribute(
            struct_ir.module[0].type[0].attribute, _FIXED_SIZE
        )
        self.assertEqual(32, ir_util.constant_value(size_attr.expression))
        bits_size_attr = ir_util.get_attribute(
            struct_ir.module[0].type[0].subtype[0].attribute, _FIXED_SIZE
        )
        self.assertEqual(8, ir_util.constant_value(bits_size_attr.expression))
        self.assertEqual(
            struct_ir.module[0].type[0].source_location, size_attr.source_location
        )

    def test_does_not_add_fixed_size_attribute_to_variable_size_struct(self):
        struct_ir = _make_ir_from_emb(
            '[$default byte_order: "LittleEndian"]\n'
            "struct Foo:\n"
            "  0 [+4]  UInt      n\n"
            "  4 [+n]  UInt:8[]  payload\n"
        )
        self.assertEqual([], attribute_checker.normalize_and_verify(struct_ir))
        self.assertIsNone(
            ir_util.get_attribute(struct_ir.module[0].type[0].attribute, _FIXED_SIZE)
        )

    def test_accepts_correct_fixed_size_and_size_attributes_on_struct(self):
        struct_ir = _make_ir_from_emb(
            '[$default byte_order: "LittleEndian"]\n'
            "struct Foo:\n"
            "  [fixed_size_in_bits: 64]\n"
            "  0 [+2]  UInt  field1\n"
            "  2 [+2]  UInt  field2\n"
            "  4 [+4]  UInt  field3\n"
        )
        self.assertEqual([], attribute_checker.normalize_and_verify(struct_ir))
        size_attr = ir_util.get_attribute(
            struct_ir.module[0].type[0].attribute, _FIXED_SIZE
        )
        self.assertTrue(size_attr)
        self.assertEqual(64, ir_util.constant_value(size_attr.expression))

    def test_accepts_correct_size_attribute_on_struct(self):
        struct_ir = _make_ir_from_emb(
            '[$default byte_order: "LittleEndian"]\n'
            "struct Foo:\n"
            "  [fixed_size_in_bits: 64]\n"
            "  0 [+2]  UInt  field1\n"
            "  4 [+4]  UInt  field3\n"
        )
        self.assertEqual([], attribute_checker.normalize_and_verify(struct_ir))
        size_attr = ir_util.get_attribute(
            struct_ir.module[0].type[0].attribute, _FIXED_SIZE
        )
        self.assertTrue(size_attr.expression)
        self.assertEqual(64, ir_util.constant_value(size_attr.expression))

    def test_rejects_incorrect_fixed_size_attribute_on_variable_size_struct(self):
        struct_ir = _make_ir_from_emb(
            '[$default byte_order: "LittleEndian"]\n'
            "struct Foo:\n"
            "  [fixed_size_in_bits: 8]\n"
            "  0 [+4]  UInt      n\n"
            "  4 [+n]  UInt:8[]  payload\n"
        )
        struct_type_ir = struct_ir.module[0].type[0]
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        struct_type_ir.attribute[0].value.source_location,
                        "Struct is marked as fixed size, but contains variable-location "
                        "fields.",
                    )
                ]
            ],
            attribute_checker.normalize_and_verify(struct_ir),
        )

    def test_rejects_size_attribute_with_wrong_large_value_on_struct(self):
        struct_ir = _make_ir_from_emb(
            '[$default byte_order: "LittleEndian"]\n'
            "struct Foo:\n"
            "  [fixed_size_in_bits: 80]\n"
            "  0 [+2]  UInt  field1\n"
            "  2 [+2]  UInt  field2\n"
            "  4 [+4]  UInt  field3\n"
        )
        struct_type_ir = struct_ir.module[0].type[0]
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        struct_type_ir.attribute[0].value.source_location,
                        "Struct is 64 bits, but is marked as 80 bits.",
                    )
                ]
            ],
            attribute_checker.normalize_and_verify(struct_ir),
        )

    def test_rejects_size_attribute_with_wrong_small_value_on_struct(self):
        struct_ir = _make_ir_from_emb(
            '[$default byte_order: "LittleEndian"]\n'
            "struct Foo:\n"
            "  [fixed_size_in_bits: 40]\n"
            "  0 [+2]  UInt  field1\n"
            "  2 [+2]  UInt  field2\n"
            "  4 [+4]  UInt  field3\n"
        )
        struct_type_ir = struct_ir.module[0].type[0]
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        struct_type_ir.attribute[0].value.source_location,
                        "Struct is 64 bits, but is marked as 40 bits.",
                    )
                ]
            ],
            attribute_checker.normalize_and_verify(struct_ir),
        )

    def test_accepts_variable_size_external(self):
        external_ir = _make_ir_from_emb(
            "external Foo:\n" "  [addressable_unit_size: 1]\n"
        )
        self.assertEqual([], attribute_checker.normalize_and_verify(external_ir))

    def test_accepts_fixed_size_external(self):
        external_ir = _make_ir_from_emb(
            "external Foo:\n"
            "  [fixed_size_in_bits: 32]\n"
            "  [addressable_unit_size: 1]\n"
        )
        self.assertEqual([], attribute_checker.normalize_and_verify(external_ir))

    def test_rejects_external_with_no_addressable_unit_size_attribute(self):
        external_ir = _make_ir_from_emb("external Foo:\n" "  [is_integer: false]\n")
        external_type_ir = external_ir.module[0].type[0]
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        external_type_ir.source_location,
                        "Expected 'addressable_unit_size' attribute for external type.",
                    )
                ]
            ],
            attribute_checker.normalize_and_verify(external_ir),
        )

    def test_rejects_is_integer_with_non_constant_value(self):
        external_ir = _make_ir_from_emb(
            "external Foo:\n"
            "  [is_integer: $static_size_in_bits == 1]\n"
            "  [addressable_unit_size: 1]\n"
        )
        external_type_ir = external_ir.module[0].type[0]
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        external_type_ir.attribute[0].value.source_location,
                        "Attribute 'is_integer' must have a constant boolean value.",
                    )
                ]
            ],
            attribute_checker.normalize_and_verify(external_ir),
        )

    def test_rejects_addressable_unit_size_with_non_constant_value(self):
        external_ir = _make_ir_from_emb(
            "external Foo:\n"
            "  [is_integer: true]\n"
            "  [addressable_unit_size: $static_size_in_bits]\n"
        )
        external_type_ir = external_ir.module[0].type[0]
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        external_type_ir.attribute[1].value.source_location,
                        "Attribute 'addressable_unit_size' must have a constant value.",
                    )
                ]
            ],
            attribute_checker.normalize_and_verify(external_ir),
        )

    def test_rejects_external_with_wrong_addressable_unit_size_attribute(self):
        external_ir = _make_ir_from_emb(
            "external Foo:\n" "  [addressable_unit_size: 4]\n"
        )
        external_type_ir = external_ir.module[0].type[0]
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        external_type_ir.source_location,
                        "Only values '1' (bit) and '8' (byte) are allowed for the "
                        "'addressable_unit_size' attribute",
                    )
                ]
            ],
            attribute_checker.normalize_and_verify(external_ir),
        )

    def test_rejects_duplicate_attribute(self):
        ir = _make_ir_from_emb(
            "external Foo:\n" "  [is_integer: true]\n" "  [is_integer: true]\n"
        )
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        ir.module[0].type[0].attribute[1].source_location,
                        "Duplicate attribute 'is_integer'.",
                    ),
                    error.note(
                        "m.emb",
                        ir.module[0].type[0].attribute[0].source_location,
                        "Original attribute",
                    ),
                ]
            ],
            attribute_checker.normalize_and_verify(ir),
        )

    def test_rejects_duplicate_default_attribute(self):
        ir = _make_ir_from_emb(
            '[$default byte_order: "LittleEndian"]\n'
            '[$default byte_order: "LittleEndian"]\n'
        )
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        ir.module[0].attribute[1].source_location,
                        "Duplicate attribute 'byte_order'.",
                    ),
                    error.note(
                        "m.emb",
                        ir.module[0].attribute[0].source_location,
                        "Original attribute",
                    ),
                ]
            ],
            attribute_checker.normalize_and_verify(ir),
        )

    def test_rejects_unknown_attribute(self):
        ir = _make_ir_from_emb("[gibberish: true]\n")
        attr = ir.module[0].attribute[0]
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        attr.name.source_location,
                        "Unknown attribute 'gibberish' on module 'm.emb'.",
                    )
                ]
            ],
            attribute_checker.normalize_and_verify(ir),
        )

    def test_rejects_non_constant_attribute(self):
        ir = _make_ir_from_emb(
            '[$default byte_order: "LittleEndian"]\n'
            "struct Foo:\n"
            "  [fixed_size_in_bits: field1]\n"
            "  0 [+2]  UInt  field1\n"
        )
        attr = ir.module[0].type[0].attribute[0]
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        attr.value.source_location,
                        "Attribute 'fixed_size_in_bits' must have a constant value.",
                    )
                ]
            ],
            attribute_checker.normalize_and_verify(ir),
        )

    def test_rejects_attribute_missing_required_back_end_specifier(self):
        ir = _make_ir_from_emb('[namespace: "abc"]\n')
        attr = ir.module[0].attribute[0]
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        attr.name.source_location,
                        "Unknown attribute 'namespace' on module 'm.emb'.",
                    )
                ]
            ],
            attribute_checker.normalize_and_verify(ir),
        )

    def test_accepts_attribute_with_default_known_back_end_specifier(self):
        ir = _make_ir_from_emb('[(cpp) namespace: "abc"]\n')
        self.assertEqual([], attribute_checker.normalize_and_verify(ir))

    def test_rejects_attribute_with_specified_back_end_specifier(self):
        ir = _make_ir_from_emb(
            '[(c) namespace: "abc"]\n' '[expected_back_ends: "c, cpp"]\n'
        )
        self.assertEqual([], attribute_checker.normalize_and_verify(ir))

    def test_rejects_cpp_backend_attribute_when_not_in_expected_back_ends(self):
        ir = _make_ir_from_emb(
            '[(cpp) namespace: "abc"]\n' '[expected_back_ends: "c"]\n'
        )
        attr = ir.module[0].attribute[0]
        self.maxDiff = 200000
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        attr.back_end.source_location,
                        "Back end specifier 'cpp' does not match any expected back end "
                        "specifier for this file: 'c'.  Add or update the "
                        "'[expected_back_ends: \"c, cpp\"]' attribute at the file level if "
                        "this back end specifier is intentional.",
                    )
                ]
            ],
            attribute_checker.normalize_and_verify(ir),
        )

    def test_rejects_expected_back_ends_with_bad_back_end(self):
        ir = _make_ir_from_emb('[expected_back_ends: "c++"]\n')
        attr = ir.module[0].attribute[0]
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        attr.value.source_location,
                        "Attribute 'expected_back_ends' must be a comma-delimited list of "
                        'back end specifiers (like "cpp, proto")), not "c++".',
                    )
                ]
            ],
            attribute_checker.normalize_and_verify(ir),
        )

    def test_rejects_expected_back_ends_with_no_comma(self):
        ir = _make_ir_from_emb('[expected_back_ends: "cpp z"]\n')
        attr = ir.module[0].attribute[0]
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        attr.value.source_location,
                        "Attribute 'expected_back_ends' must be a comma-delimited list of "
                        'back end specifiers (like "cpp, proto")), not "cpp z".',
                    )
                ]
            ],
            attribute_checker.normalize_and_verify(ir),
        )

    def test_rejects_expected_back_ends_with_extra_commas(self):
        ir = _make_ir_from_emb('[expected_back_ends: "cpp,,z"]\n')
        attr = ir.module[0].attribute[0]
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        attr.value.source_location,
                        "Attribute 'expected_back_ends' must be a comma-delimited list of "
                        'back end specifiers (like "cpp, proto")), not "cpp,,z".',
                    )
                ]
            ],
            attribute_checker.normalize_and_verify(ir),
        )

    def test_accepts_empty_expected_back_ends(self):
        ir = _make_ir_from_emb('[expected_back_ends: ""]\n')
        self.assertEqual([], attribute_checker.normalize_and_verify(ir))

    def test_adds_byte_order_attributes_from_default(self):
        ir = _make_ir_from_emb(
            '[$default byte_order: "BigEndian"]\n'
            "struct Foo:\n"
            "  0 [+2]  UInt  bar\n"
            "  2 [+2]  UInt  baz\n"
            '    [byte_order: "LittleEndian"]\n'
        )
        self.assertEqual([], attribute_checker.normalize_and_verify(ir))
        byte_order_attr = ir_util.get_attribute(
            ir.module[0].type[0].structure.field[0].attribute, _BYTE_ORDER
        )
        self.assertTrue(byte_order_attr.HasField("string_constant"))
        self.assertEqual("BigEndian", byte_order_attr.string_constant.text)
        byte_order_attr = ir_util.get_attribute(
            ir.module[0].type[0].structure.field[1].attribute, _BYTE_ORDER
        )
        self.assertTrue(byte_order_attr.HasField("string_constant"))
        self.assertEqual("LittleEndian", byte_order_attr.string_constant.text)

    def test_adds_null_byte_order_attributes(self):
        ir = _make_ir_from_emb(
            "struct Foo:\n"
            "  0 [+1]  UInt      bar\n"
            "  1 [+1]  UInt      baz\n"
            '    [byte_order: "LittleEndian"]\n'
            "  2 [+2]  UInt:8[]  baseball\n"
            "  4 [+2]  UInt:8[]  bat\n"
            '    [byte_order: "LittleEndian"]\n'
        )
        self.assertEqual([], attribute_checker.normalize_and_verify(ir))
        structure = ir.module[0].type[0].structure
        byte_order_attr = ir_util.get_attribute(
            structure.field[0].attribute, _BYTE_ORDER
        )
        self.assertTrue(byte_order_attr.HasField("string_constant"))
        self.assertEqual("Null", byte_order_attr.string_constant.text)
        self.assertEqual(
            structure.field[0].source_location, byte_order_attr.source_location
        )
        byte_order_attr = ir_util.get_attribute(
            structure.field[1].attribute, _BYTE_ORDER
        )
        self.assertTrue(byte_order_attr.HasField("string_constant"))
        self.assertEqual("LittleEndian", byte_order_attr.string_constant.text)
        byte_order_attr = ir_util.get_attribute(
            structure.field[2].attribute, _BYTE_ORDER
        )
        self.assertTrue(byte_order_attr.HasField("string_constant"))
        self.assertEqual("Null", byte_order_attr.string_constant.text)
        self.assertEqual(
            structure.field[2].source_location, byte_order_attr.source_location
        )
        byte_order_attr = ir_util.get_attribute(
            structure.field[3].attribute, _BYTE_ORDER
        )
        self.assertTrue(byte_order_attr.HasField("string_constant"))
        self.assertEqual("LittleEndian", byte_order_attr.string_constant.text)

    def test_disallows_default_byte_order_on_field(self):
        ir = _make_ir_from_emb(
            '[$default byte_order: "LittleEndian"]\n'
            "struct Foo:\n"
            "  0 [+2]  UInt  bar\n"
            '    [$default byte_order: "LittleEndian"]\n'
        )
        default_byte_order = ir.module[0].type[0].structure.field[0].attribute[0]
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        default_byte_order.name.source_location,
                        "Attribute 'byte_order' may not be defaulted on struct field 'bar'.",
                    )
                ]
            ],
            attribute_checker.normalize_and_verify(ir),
        )

    def test_disallows_default_byte_order_on_bits(self):
        ir = _make_ir_from_emb(
            "bits Foo:\n"
            '  [$default byte_order: "LittleEndian"]\n'
            "  0 [+2]  UInt  bar\n"
        )
        default_byte_order = ir.module[0].type[0].attribute[0]
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        default_byte_order.name.source_location,
                        "Attribute 'byte_order' may not be defaulted on bits 'Foo'.",
                    )
                ]
            ],
            attribute_checker.normalize_and_verify(ir),
        )

    def test_disallows_default_byte_order_on_enum(self):
        ir = _make_ir_from_emb(
            "enum Foo:\n" '  [$default byte_order: "LittleEndian"]\n' "  BAR = 1\n"
        )
        default_byte_order = ir.module[0].type[0].attribute[0]
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        default_byte_order.name.source_location,
                        "Attribute 'byte_order' may not be defaulted on enum 'Foo'.",
                    )
                ]
            ],
            attribute_checker.normalize_and_verify(ir),
        )

    def test_adds_byte_order_from_scoped_default(self):
        ir = _make_ir_from_emb(
            '[$default byte_order: "LittleEndian"]\n'
            "struct Foo:\n"
            '  [$default byte_order: "BigEndian"]\n'
            "  0 [+2]  UInt  bar\n"
        )
        self.assertEqual([], attribute_checker.normalize_and_verify(ir))
        byte_order_attr = ir_util.get_attribute(
            ir.module[0].type[0].structure.field[0].attribute, _BYTE_ORDER
        )
        self.assertTrue(byte_order_attr.HasField("string_constant"))
        self.assertEqual("BigEndian", byte_order_attr.string_constant.text)

    def test_disallows_unknown_byte_order(self):
        ir = _make_ir_from_emb(
            "struct Foo:\n" "  0 [+2]  UInt  bar\n" '    [byte_order: "NoEndian"]\n'
        )
        byte_order = ir.module[0].type[0].structure.field[0].attribute[0]
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        byte_order.value.source_location,
                        "Attribute 'byte_order' must be 'BigEndian' or 'LittleEndian' or "
                        "'Null'.",
                    )
                ]
            ],
            attribute_checker.normalize_and_verify(ir),
        )

    def test_disallows_unknown_default_byte_order(self):
        ir = _make_ir_from_emb('[$default byte_order: "NoEndian"]\n')
        default_byte_order = ir.module[0].attribute[0]
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        default_byte_order.value.source_location,
                        "Attribute 'byte_order' must be 'BigEndian' or 'LittleEndian' or "
                        "'Null'.",
                    )
                ]
            ],
            attribute_checker.normalize_and_verify(ir),
        )

    def test_disallows_byte_order_on_non_byte_order_dependent_fields(self):
        ir = _make_ir_from_emb(
            "struct Foo:\n"
            '  [$default byte_order: "LittleEndian"]\n'
            "  0 [+2]  UInt  uint\n"
            "struct Bar:\n"
            "  0 [+2]  Foo  foo\n"
            '    [byte_order: "LittleEndian"]\n'
        )
        byte_order = ir.module[0].type[1].structure.field[0].attribute[0]
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        byte_order.value.source_location,
                        "Attribute 'byte_order' not allowed on field which is not byte "
                        "order dependent.",
                    )
                ]
            ],
            attribute_checker.normalize_and_verify(ir),
        )

    def test_disallows_byte_order_on_virtual_field(self):
        ir = _make_ir_from_emb(
            "struct Foo:\n" "  let x = 10\n" '    [byte_order: "LittleEndian"]\n'
        )
        byte_order = ir.module[0].type[0].structure.field[0].attribute[0]
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        byte_order.name.source_location,
                        "Unknown attribute 'byte_order' on virtual struct field 'x'.",
                    )
                ]
            ],
            attribute_checker.normalize_and_verify(ir),
        )

    def test_disallows_null_byte_order_on_multibyte_fields(self):
        ir = _make_ir_from_emb(
            "struct Foo:\n" "  0 [+2]  UInt  uint\n" '    [byte_order: "Null"]\n'
        )
        byte_order = ir.module[0].type[0].structure.field[0].attribute[0]
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        byte_order.value.source_location,
                        "Attribute 'byte_order' may only be 'Null' for one-byte fields.",
                    )
                ]
            ],
            attribute_checker.normalize_and_verify(ir),
        )

    def test_disallows_null_byte_order_on_multibyte_array_elements(self):
        ir = _make_ir_from_emb(
            "struct Foo:\n" "  0 [+4]  UInt:16[]  uint\n" '    [byte_order: "Null"]\n'
        )
        byte_order = ir.module[0].type[0].structure.field[0].attribute[0]
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        byte_order.value.source_location,
                        "Attribute 'byte_order' may only be 'Null' for one-byte fields.",
                    )
                ]
            ],
            attribute_checker.normalize_and_verify(ir),
        )

    def test_requires_byte_order_on_byte_order_dependent_fields(self):
        ir = _make_ir_from_emb("struct Foo:\n" "  0 [+2]  UInt  uint\n")
        field = ir.module[0].type[0].structure.field[0]
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        field.source_location,
                        "Attribute 'byte_order' required on field which is byte order "
                        "dependent.",
                    )
                ]
            ],
            attribute_checker.normalize_and_verify(ir),
        )

    def test_disallows_unknown_text_output_attribute(self):
        ir = _make_ir_from_emb(
            "struct Foo:\n" "  0 [+2]  UInt  bar\n" '    [text_output: "None"]\n'
        )
        byte_order = ir.module[0].type[0].structure.field[0].attribute[0]
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        byte_order.value.source_location,
                        "Attribute 'text_output' must be 'Emit' or 'Skip'.",
                    )
                ]
            ],
            attribute_checker.normalize_and_verify(ir),
        )

    def test_disallows_non_string_text_output_attribute(self):
        ir = _make_ir_from_emb(
            "struct Foo:\n" "  0 [+2]  UInt  bar\n" "    [text_output: 0]\n"
        )
        byte_order = ir.module[0].type[0].structure.field[0].attribute[0]
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        byte_order.value.source_location,
                        "Attribute 'text_output' must be 'Emit' or 'Skip'.",
                    )
                ]
            ],
            attribute_checker.normalize_and_verify(ir),
        )

    def test_allows_skip_text_output_attribute_on_physical_field(self):
        ir = _make_ir_from_emb(
            "struct Foo:\n" "  0 [+1]  UInt  bar\n" '    [text_output: "Skip"]\n'
        )
        self.assertEqual([], attribute_checker.normalize_and_verify(ir))

    def test_allows_skip_text_output_attribute_on_virtual_field(self):
        ir = _make_ir_from_emb(
            "struct Foo:\n" "  let x = 10\n" '    [text_output: "Skip"]\n'
        )
        self.assertEqual([], attribute_checker.normalize_and_verify(ir))

    def test_allows_emit_text_output_attribute_on_physical_field(self):
        ir = _make_ir_from_emb(
            "struct Foo:\n" "  0 [+1]  UInt  bar\n" '    [text_output: "Emit"]\n'
        )
        self.assertEqual([], attribute_checker.normalize_and_verify(ir))

    def test_adds_bit_addressable_unit_to_external(self):
        external_ir = _make_ir_from_emb(
            "external Foo:\n" "  [addressable_unit_size: 1]\n"
        )
        self.assertEqual([], attribute_checker.normalize_and_verify(external_ir))
        self.assertEqual(
            ir_data.AddressableUnit.BIT, external_ir.module[0].type[0].addressable_unit
        )

    def test_adds_byte_addressable_unit_to_external(self):
        external_ir = _make_ir_from_emb(
            "external Foo:\n" "  [addressable_unit_size: 8]\n"
        )
        self.assertEqual([], attribute_checker.normalize_and_verify(external_ir))
        self.assertEqual(
            ir_data.AddressableUnit.BYTE, external_ir.module[0].type[0].addressable_unit
        )

    def test_rejects_requires_using_array(self):
        ir = _make_ir_from_emb(
            "struct Foo:\n" "  0 [+4]  UInt:8[]  array\n" "    [requires: this]\n"
        )
        field_ir = ir.module[0].type[0].structure.field[0]
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        field_ir.attribute[0].value.source_location,
                        "Attribute 'requires' must have a boolean value.",
                    )
                ]
            ],
            attribute_checker.normalize_and_verify(ir),
        )

    def test_rejects_requires_on_array(self):
        ir = _make_ir_from_emb(
            "struct Foo:\n" "  0 [+4]  UInt:8[]  array\n" "    [requires: false]\n"
        )
        field_ir = ir.module[0].type[0].structure.field[0]
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        field_ir.attribute[0].value.source_location,
                        "Attribute 'requires' is only allowed on integer, "
                        "enumeration, or boolean fields, not arrays.",
                    ),
                    error.note("m.emb", field_ir.type.source_location, "Field type."),
                ]
            ],
            error.filter_errors(attribute_checker.normalize_and_verify(ir)),
        )

    def test_rejects_requires_on_struct(self):
        ir = _make_ir_from_emb(
            '[$default byte_order: "LittleEndian"]\n'
            "struct Foo:\n"
            "  0 [+4]  Bar  bar\n"
            "    [requires: false]\n"
            "struct Bar:\n"
            "  0 [+4]  UInt  uint\n"
        )
        field_ir = ir.module[0].type[0].structure.field[0]
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        field_ir.attribute[0].value.source_location,
                        "Attribute 'requires' is only allowed on integer, "
                        "enumeration, or boolean fields.",
                    )
                ]
            ],
            error.filter_errors(attribute_checker.normalize_and_verify(ir)),
        )

    def test_rejects_requires_on_float(self):
        ir = _make_ir_from_emb(
            '[$default byte_order: "LittleEndian"]\n'
            "struct Foo:\n"
            "  0 [+4]  Float  float\n"
            "    [requires: false]\n"
        )
        field_ir = ir.module[0].type[0].structure.field[0]
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        field_ir.attribute[0].value.source_location,
                        "Attribute 'requires' is only allowed on integer, "
                        "enumeration, or boolean fields.",
                    )
                ]
            ],
            error.filter_errors(attribute_checker.normalize_and_verify(ir)),
        )

    def test_adds_false_is_signed_attribute(self):
        ir = _make_ir_from_emb("enum Foo:\n" "  ZERO = 0\n")
        self.assertEqual([], attribute_checker.normalize_and_verify(ir))
        enum = ir.module[0].type[0]
        is_signed_attr = ir_util.get_attribute(enum.attribute, _IS_SIGNED)
        self.assertTrue(is_signed_attr.expression.HasField("boolean_constant"))
        self.assertFalse(is_signed_attr.expression.boolean_constant.value)

    def test_leaves_is_signed_attribute(self):
        ir = _make_ir_from_emb("enum Foo:\n" "  [is_signed: true]\n" "  ZERO = 0\n")
        self.assertEqual([], attribute_checker.normalize_and_verify(ir))
        enum = ir.module[0].type[0]
        is_signed_attr = ir_util.get_attribute(enum.attribute, _IS_SIGNED)
        self.assertTrue(is_signed_attr.expression.HasField("boolean_constant"))
        self.assertTrue(is_signed_attr.expression.boolean_constant.value)

    def test_adds_true_is_signed_attribute(self):
        ir = _make_ir_from_emb("enum Foo:\n" "  NEGATIVE_ONE = -1\n")
        self.assertEqual([], attribute_checker.normalize_and_verify(ir))
        enum = ir.module[0].type[0]
        is_signed_attr = ir_util.get_attribute(enum.attribute, _IS_SIGNED)
        self.assertTrue(is_signed_attr.expression.HasField("boolean_constant"))
        self.assertTrue(is_signed_attr.expression.boolean_constant.value)

    def test_adds_max_bits_attribute(self):
        ir = _make_ir_from_emb("enum Foo:\n" "  ZERO = 0\n")
        self.assertEqual([], attribute_checker.normalize_and_verify(ir))
        enum = ir.module[0].type[0]
        max_bits_attr = ir_util.get_attribute(enum.attribute, _MAX_BITS)
        self.assertTrue(max_bits_attr.expression.HasField("constant"))
        self.assertEqual("64", max_bits_attr.expression.constant.value)

    def test_leaves_max_bits_attribute(self):
        ir = _make_ir_from_emb("enum Foo:\n" "  [maximum_bits: 32]\n" "  ZERO = 0\n")
        self.assertEqual([], attribute_checker.normalize_and_verify(ir))
        enum = ir.module[0].type[0]
        max_bits_attr = ir_util.get_attribute(enum.attribute, _MAX_BITS)
        self.assertTrue(max_bits_attr.expression.HasField("constant"))
        self.assertEqual("32", max_bits_attr.expression.constant.value)

    def test_rejects_too_small_max_bits(self):
        ir = _make_ir_from_emb("enum Foo:\n" "  [maximum_bits: 0]\n" "  ZERO = 0\n")
        attribute_ir = ir.module[0].type[0].attribute[0]
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        attribute_ir.value.source_location,
                        "'maximum_bits' on an 'enum' must be between 1 and 64.",
                    )
                ]
            ],
            error.filter_errors(attribute_checker.normalize_and_verify(ir)),
        )

    def test_rejects_too_large_max_bits(self):
        ir = _make_ir_from_emb("enum Foo:\n" "  [maximum_bits: 65]\n" "  ZERO = 0\n")
        attribute_ir = ir.module[0].type[0].attribute[0]
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        attribute_ir.value.source_location,
                        "'maximum_bits' on an 'enum' must be between 1 and 64.",
                    )
                ]
            ],
            error.filter_errors(attribute_checker.normalize_and_verify(ir)),
        )

    def test_rejects_unknown_enum_value_attribute(self):
        ir = _make_ir_from_emb("enum Foo:\n" "  BAR = 0  \n" "    [bad_attr: true]\n")
        attribute_ir = ir.module[0].type[0].enumeration.value[0].attribute[0]
        self.assertNotEqual([], attribute_checker.normalize_and_verify(ir))
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        attribute_ir.name.source_location,
                        "Unknown attribute 'bad_attr' on enum value 'BAR'.",
                    )
                ]
            ],
            error.filter_errors(attribute_checker.normalize_and_verify(ir)),
        )


if __name__ == "__main__":
    unittest.main()
