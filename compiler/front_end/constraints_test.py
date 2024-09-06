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

"""Tests for constraints.py."""

import unittest
from compiler.front_end import attributes
from compiler.front_end import constraints
from compiler.front_end import glue
from compiler.util import error
from compiler.util import ir_data_utils
from compiler.util import ir_util
from compiler.util import test_util


def _make_ir_from_emb(emb_text, name="m.emb"):
    ir, unused_debug_info, errors = glue.parse_emboss_file(
        name,
        test_util.dict_file_reader({name: emb_text}),
        stop_before_step="check_constraints",
    )
    assert not errors, repr(errors)
    return ir


class ConstraintsTest(unittest.TestCase):
    """Tests constraints.check_constraints and helpers."""

    def test_error_on_missing_inner_array_size(self):
        ir = _make_ir_from_emb("struct Foo:\n" "  0 [+1]  UInt:8[][1]  one_byte\n")
        # There is a latent issue here where the source location reported in this
        # error is using a default value of 0:0. An issue is filed at
        # https://github.com/google/emboss/issues/153 for further investigation.
        # In the meantime we use `ir_data_utils.reader` to mimic this legacy
        # behavior.
        error_array = ir_data_utils.reader(
            ir.module[0].type[0].structure.field[0].type.array_type
        )
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        error_array.base_type.array_type.element_count.source_location,
                        "Array dimensions can only be omitted for the outermost dimension.",
                    )
                ]
            ],
            error.filter_errors(constraints.check_constraints(ir)),
        )

    def test_no_error_on_ok_array_size(self):
        ir = _make_ir_from_emb("struct Foo:\n" "  0 [+1]  UInt:8[1][1]  one_byte\n")
        self.assertEqual([], constraints.check_constraints(ir))

    def test_no_error_on_ok_missing_outer_array_size(self):
        ir = _make_ir_from_emb("struct Foo:\n" "  0 [+1]  UInt:8[1][]  one_byte\n")
        self.assertEqual([], constraints.check_constraints(ir))

    def test_no_error_on_dynamically_sized_struct_in_dynamically_sized_field(self):
        ir = _make_ir_from_emb(
            "struct Foo:\n"
            "  0 [+1]     UInt  size\n"
            "  1 [+size]  Bar   bar\n"
            "struct Bar:\n"
            "  0 [+1]     UInt      size\n"
            "  1 [+size]  UInt:8[]  payload\n"
        )
        self.assertEqual([], constraints.check_constraints(ir))

    def test_no_error_on_dynamically_sized_struct_in_statically_sized_field(self):
        ir = _make_ir_from_emb(
            "struct Foo:\n"
            "  0 [+10]  Bar   bar\n"
            "struct Bar:\n"
            "  0 [+1]     UInt      size\n"
            "  1 [+size]  UInt:8[]  payload\n"
        )
        self.assertEqual([], constraints.check_constraints(ir))

    def test_no_error_non_fixed_size_outer_array_dimension(self):
        ir = _make_ir_from_emb(
            "struct Foo:\n"
            "  0 [+1]     UInt               size\n"
            "  1 [+size]  UInt:8[1][size-1]  one_byte\n"
        )
        self.assertEqual([], constraints.check_constraints(ir))

    def test_error_non_fixed_size_inner_array_dimension(self):
        ir = _make_ir_from_emb(
            "struct Foo:\n"
            "  0 [+1]     UInt               size\n"
            "  1 [+size]  UInt:8[size-1][1]  one_byte\n"
        )
        error_array = ir.module[0].type[0].structure.field[1].type.array_type
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        error_array.base_type.array_type.element_count.source_location,
                        "Inner array dimensions must be constant.",
                    )
                ]
            ],
            error.filter_errors(constraints.check_constraints(ir)),
        )

    def test_error_non_constant_inner_array_dimensions(self):
        ir = _make_ir_from_emb(
            "struct Foo:\n"
            "  0 [+1]  Bar[1]  one_byte\n"
            # There is no dynamically-sized byte-oriented type in
            # the Prelude, so this test has to make its own.
            "external Bar:\n"
            "  [is_integer: true]\n"
            "  [addressable_unit_size: 8]\n"
        )
        error_array = ir.module[0].type[0].structure.field[0].type.array_type
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        error_array.base_type.atomic_type.source_location,
                        "Array elements must be fixed size.",
                    )
                ]
            ],
            error.filter_errors(constraints.check_constraints(ir)),
        )

    def test_error_dynamically_sized_array_elements(self):
        ir = _make_ir_from_emb(
            '[$default byte_order: "LittleEndian"]\n'
            "struct Foo:\n"
            "  0 [+1]  Bar[1]  bar\n"
            "struct Bar:\n"
            "  0 [+1]     UInt      size\n"
            "  1 [+size]  UInt:8[]  payload\n"
        )
        error_array = ir.module[0].type[0].structure.field[0].type.array_type
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        error_array.base_type.atomic_type.source_location,
                        "Array elements must be fixed size.",
                    )
                ]
            ],
            error.filter_errors(constraints.check_constraints(ir)),
        )

    def test_field_too_small_for_type(self):
        ir = _make_ir_from_emb(
            '[$default byte_order: "LittleEndian"]\n'
            "struct Foo:\n"
            "  0 [+1]  Bar  bar\n"
            "struct Bar:\n"
            "  0 [+2]  UInt  value\n"
        )
        error_type = ir.module[0].type[0].structure.field[0].type
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        error_type.source_location,
                        "Fixed-size type 'Bar' cannot be placed in field of size 8 bits; "
                        "requires 16 bits.",
                    )
                ]
            ],
            error.filter_errors(constraints.check_constraints(ir)),
        )

    def test_dynamically_sized_field_always_too_small_for_type(self):
        ir = _make_ir_from_emb(
            '[$default byte_order: "LittleEndian"]\n'
            "struct Foo:\n"
            "  0 [+1]  bits:\n"
            "    0 [+1]  UInt  x\n"
            "  0 [+x]  Bar  bar\n"
            "struct Bar:\n"
            "  0 [+2]  UInt  value\n"
        )
        error_type = ir.module[0].type[0].structure.field[2].type
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        error_type.source_location,
                        "Field of maximum size 8 bits cannot hold fixed-size type 'Bar', "
                        "which requires 16 bits.",
                    )
                ]
            ],
            error.filter_errors(constraints.check_constraints(ir)),
        )

    def test_struct_field_too_big_for_type(self):
        ir = _make_ir_from_emb(
            "struct Foo:\n"
            "  0 [+2]  Byte  double_byte\n"
            "struct Byte:\n"
            "  0 [+1]  UInt  b\n"
        )
        error_type = ir.module[0].type[0].structure.field[0].type
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        error_type.source_location,
                        "Fixed-size type 'Byte' cannot be placed in field of size 16 bits; "
                        "requires 8 bits.",
                    )
                ]
            ],
            error.filter_errors(constraints.check_constraints(ir)),
        )

    def test_bits_field_too_big_for_type(self):
        ir = _make_ir_from_emb(
            "struct Foo:\n"
            "  0 [+9]  UInt  uint72\n"
            '    [byte_order: "LittleEndian"]\n'
        )
        error_field = ir.module[0].type[0].structure.field[0]
        uint_type = ir_util.find_object(error_field.type.atomic_type.reference, ir)
        uint_requirements = ir_util.get_attribute(
            uint_type.attribute, attributes.STATIC_REQUIREMENTS
        )
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        error_field.source_location,
                        "Requirements of UInt not met.",
                    ),
                    error.note(
                        "",
                        uint_requirements.source_location,
                        "Requirements specified here.",
                    ),
                ]
            ],
            error.filter_errors(constraints.check_constraints(ir)),
        )

    def test_field_type_not_allowed_in_bits(self):
        ir = _make_ir_from_emb(
            '[$default byte_order: "LittleEndian"]\n'
            "bits Foo:\n"
            "  0 [+16]  Bar  bar\n"
            "external Bar:\n"
            "  [addressable_unit_size: 8]\n"
        )
        error_type = ir.module[0].type[0].structure.field[0].type
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        error_type.source_location,
                        "Byte-oriented type 'Bar' cannot be used in a bits field.",
                    )
                ]
            ],
            error.filter_errors(constraints.check_constraints(ir)),
        )

    def test_arrays_allowed_in_bits(self):
        ir = _make_ir_from_emb("bits Foo:\n" "  0 [+16]  Flag[16]  bar\n")
        self.assertEqual([], constraints.check_constraints(ir))

    def test_oversized_anonymous_bit_field(self):
        ir = _make_ir_from_emb(
            '[$default byte_order: "LittleEndian"]\n'
            "struct Foo:\n"
            "  0 [+4]  bits:\n"
            "    0 [+8]  UInt  field\n"
        )
        self.assertEqual([], constraints.check_constraints(ir))

    def test_undersized_anonymous_bit_field(self):
        ir = _make_ir_from_emb(
            '[$default byte_order: "LittleEndian"]\n'
            "struct Foo:\n"
            "  0 [+1]  bits:\n"
            "    0 [+32]  UInt  field\n"
        )
        error_type = ir.module[0].type[0].structure.field[0].type
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        error_type.source_location,
                        "Fixed-size anonymous type cannot be placed in field of size 8 "
                        "bits; requires 32 bits.",
                    )
                ]
            ],
            error.filter_errors(constraints.check_constraints(ir)),
        )

    def test_reserved_field_name(self):
        ir = _make_ir_from_emb(
            '[$default byte_order: "LittleEndian"]\n'
            "struct Foo:\n"
            "  0 [+8]  UInt  restrict\n"
        )
        error_name = ir.module[0].type[0].structure.field[0].name.name
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        error_name.source_location,
                        "C reserved word may not be used as a field name.",
                    )
                ]
            ],
            error.filter_errors(constraints.check_constraints(ir)),
        )

    def test_reserved_type_name(self):
        ir = _make_ir_from_emb("struct False:\n" "  0 [+1]  UInt  foo\n")
        error_name = ir.module[0].type[0].name.name
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        error_name.source_location,
                        "Python 3 reserved word may not be used as a type name.",
                    )
                ]
            ],
            error.filter_errors(constraints.check_constraints(ir)),
        )

    def test_reserved_enum_name(self):
        ir = _make_ir_from_emb("enum Foo:\n" "  NULL = 1\n")
        error_name = ir.module[0].type[0].enumeration.value[0].name.name
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        error_name.source_location,
                        "C reserved word may not be used as an enum name.",
                    )
                ]
            ],
            error.filter_errors(constraints.check_constraints(ir)),
        )

    def test_bits_type_in_struct_array(self):
        ir = _make_ir_from_emb(
            '[$default byte_order: "LittleEndian"]\n'
            "struct Foo:\n"
            "  0 [+10]  UInt:8[10]  array\n"
        )
        self.assertEqual([], constraints.check_constraints(ir))

    def test_bits_type_in_bits_array(self):
        ir = _make_ir_from_emb("bits Foo:\n" "  0 [+10]  UInt:8[10]  array\n")
        self.assertEqual([], constraints.check_constraints(ir))

    def test_explicit_size_too_small(self):
        ir = _make_ir_from_emb("bits Foo:\n" "  0 [+0]  UInt:0  zero_bit\n")
        error_field = ir.module[0].type[0].structure.field[0]
        uint_type = ir_util.find_object(error_field.type.atomic_type.reference, ir)
        uint_requirements = ir_util.get_attribute(
            uint_type.attribute, attributes.STATIC_REQUIREMENTS
        )
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        error_field.source_location,
                        "Requirements of UInt not met.",
                    ),
                    error.note(
                        "",
                        uint_requirements.source_location,
                        "Requirements specified here.",
                    ),
                ]
            ],
            error.filter_errors(constraints.check_constraints(ir)),
        )

    def test_explicit_enumeration_size_too_small(self):
        ir = _make_ir_from_emb(
            '[$default byte_order: "BigEndian"]\n'
            "bits Foo:\n"
            "  0 [+0]  Bar:0  zero_bit\n"
            "enum Bar:\n"
            "  BAZ = 0\n"
        )
        error_type = ir.module[0].type[0].structure.field[0].type
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        error_type.source_location,
                        "Enumeration type 'Bar' cannot be 0 bits; type 'Bar' "
                        "must be between 1 and 64 bits, inclusive.",
                    ),
                ]
            ],
            error.filter_errors(constraints.check_constraints(ir)),
        )

    def test_explicit_size_too_big_for_field(self):
        ir = _make_ir_from_emb("bits Foo:\n" "  0 [+8]  UInt:32  thirty_two_bit\n")
        error_type = ir.module[0].type[0].structure.field[0].type
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        error_type.source_location,
                        "Fixed-size type 'UInt:32' cannot be placed in field of size 8 "
                        "bits; requires 32 bits.",
                    )
                ]
            ],
            error.filter_errors(constraints.check_constraints(ir)),
        )

    def test_explicit_size_too_small_for_field(self):
        ir = _make_ir_from_emb("bits Foo:\n" "  0 [+64]  UInt:32  thirty_two_bit\n")
        error_type = ir.module[0].type[0].structure.field[0].type
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        error_type.source_location,
                        "Fixed-size type 'UInt:32' cannot be placed in field of "
                        "size 64 bits; requires 32 bits.",
                    )
                ]
            ],
            error.filter_errors(constraints.check_constraints(ir)),
        )

    def test_explicit_size_too_big(self):
        ir = _make_ir_from_emb(
            "struct Foo:\n"
            "  0 [+16]  UInt:128  one_twenty_eight_bit\n"
            '    [byte_order: "LittleEndian"]\n'
        )
        error_field = ir.module[0].type[0].structure.field[0]
        uint_type = ir_util.find_object(error_field.type.atomic_type.reference, ir)
        uint_requirements = ir_util.get_attribute(
            uint_type.attribute, attributes.STATIC_REQUIREMENTS
        )
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        error_field.source_location,
                        "Requirements of UInt not met.",
                    ),
                    error.note(
                        "",
                        uint_requirements.source_location,
                        "Requirements specified here.",
                    ),
                ]
            ],
            error.filter_errors(constraints.check_constraints(ir)),
        )

    def test_explicit_enumeration_size_too_big(self):
        ir = _make_ir_from_emb(
            '[$default byte_order: "BigEndian"]\n'
            "struct Foo:\n"
            "  0 [+9]  Bar  seventy_two_bit\n"
            "enum Bar:\n"
            "  BAZ = 0\n"
        )
        error_type = ir.module[0].type[0].structure.field[0].type
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        error_type.source_location,
                        "Enumeration type 'Bar' cannot be 72 bits; type 'Bar' "
                        + "must be between 1 and 64 bits, inclusive.",
                    ),
                ]
            ],
            error.filter_errors(constraints.check_constraints(ir)),
        )

    def test_explicit_enumeration_size_too_big_for_small_enum(self):
        ir = _make_ir_from_emb(
            '[$default byte_order: "BigEndian"]\n'
            "struct Foo:\n"
            "  0 [+8]  Bar  sixty_four_bit\n"
            "enum Bar:\n"
            "  [maximum_bits: 63]\n"
            "  BAZ = 0\n"
        )
        error_type = ir.module[0].type[0].structure.field[0].type
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        error_type.source_location,
                        "Enumeration type 'Bar' cannot be 64 bits; type 'Bar' "
                        + "must be between 1 and 63 bits, inclusive.",
                    ),
                ]
            ],
            error.filter_errors(constraints.check_constraints(ir)),
        )

    def test_explicit_size_on_fixed_size_type(self):
        ir = _make_ir_from_emb(
            "struct Foo:\n"
            "  0 [+1]  Byte:8  one_byte\n"
            "struct Byte:\n"
            "  0 [+1]  UInt  b\n"
        )
        self.assertEqual([], constraints.check_constraints(ir))

    def test_explicit_size_too_small_on_fixed_size_type(self):
        ir = _make_ir_from_emb(
            "struct Foo:\n"
            "  0 [+0]  Byte:0  null_byte\n"
            "struct Byte:\n"
            "  0 [+1]  UInt  b\n"
        )
        error_type = ir.module[0].type[0].structure.field[0].type
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        error_type.size_in_bits.source_location,
                        "Explicit size of 0 bits does not match fixed size (8 bits) of "
                        "type 'Byte'.",
                    ),
                    error.note(
                        "m.emb",
                        ir.module[0].type[1].source_location,
                        "Size specified here.",
                    ),
                ]
            ],
            error.filter_errors(constraints.check_constraints(ir)),
        )

    def test_explicit_size_too_big_on_fixed_size_type(self):
        ir = _make_ir_from_emb(
            "struct Foo:\n"
            "  0 [+2]  Byte:16  double_byte\n"
            "struct Byte:\n"
            "  0 [+1]  UInt  b\n"
        )
        error_type = ir.module[0].type[0].structure.field[0].type
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        error_type.size_in_bits.source_location,
                        "Explicit size of 16 bits does not match fixed size (8 bits) of "
                        "type 'Byte'.",
                    ),
                    error.note(
                        "m.emb",
                        ir.module[0].type[1].source_location,
                        "Size specified here.",
                    ),
                ]
            ],
            error.filter_errors(constraints.check_constraints(ir)),
        )

    def test_explicit_size_ignored_on_variable_size_type(self):
        ir = _make_ir_from_emb(
            '[$default byte_order: "LittleEndian"]\n'
            "struct Foo:\n"
            "  0 [+1]  UInt      n\n"
            "  1 [+n]  UInt:8[]  d\n"
            "struct Bar:\n"
            "  0 [+10]  Foo:80  foo\n"
        )
        self.assertEqual([], constraints.check_constraints(ir))

    def test_fixed_size_type_in_dynamically_sized_field(self):
        ir = _make_ir_from_emb(
            "struct Foo:\n"
            "  0 [+1]    UInt  bar\n"
            "  0 [+bar]  Byte  one_byte\n"
            "struct Byte:\n"
            "  0 [+1]  UInt  b\n"
        )
        self.assertEqual([], constraints.check_constraints(ir))

    def test_enum_in_dynamically_sized_field(self):
        ir = _make_ir_from_emb(
            '[$default byte_order: "BigEndian"]\n'
            "struct Foo:\n"
            "  0 [+1]    UInt  bar\n"
            "  0 [+bar]  Baz   baz\n"
            "enum Baz:\n"
            "  QUX = 0\n"
        )
        error_type = ir.module[0].type[0].structure.field[1].type
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        error_type.source_location,
                        "Enumeration type 'Baz' cannot be placed in a "
                        "dynamically-sized field.",
                    )
                ]
            ],
            error.filter_errors(constraints.check_constraints(ir)),
        )

    def test_enum_value_too_high(self):
        ir = _make_ir_from_emb(
            '[$default byte_order: "LittleEndian"]\n'
            "enum Foo:\n"
            "  HIGH = 0x1_0000_0000_0000_0000\n"
        )
        error_value = ir.module[0].type[0].enumeration.value[0].value
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        error_value.source_location,
                        # TODO(bolms): Try to print numbers like 2**64 in hex?  (I.e., if a
                        # number is a round number in hex, but not in decimal, print in
                        # hex?)
                        "Value 18446744073709551616 is out of range for 64-bit unsigned "
                        + "enumeration.",
                    )
                ]
            ],
            constraints.check_constraints(ir),
        )

    def test_enum_value_too_low(self):
        ir = _make_ir_from_emb(
            '[$default byte_order: "LittleEndian"]\n'
            "enum Foo:\n"
            "  LOW = -0x8000_0000_0000_0001\n"
        )
        error_value = ir.module[0].type[0].enumeration.value[0].value
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        error_value.source_location,
                        "Value -9223372036854775809 is out of range for 64-bit signed "
                        + "enumeration.",
                    )
                ]
            ],
            constraints.check_constraints(ir),
        )

    def test_enum_value_too_wide(self):
        ir = _make_ir_from_emb(
            '[$default byte_order: "LittleEndian"]\n'
            "enum Foo:\n"
            "  LOW = -1\n"
            "  HIGH = 0x8000_0000_0000_0000\n"
        )
        error_value = ir.module[0].type[0].enumeration.value[1].value
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        error_value.source_location,
                        "Value 9223372036854775808 is out of range for 64-bit signed "
                        + "enumeration.",
                    )
                ]
            ],
            error.filter_errors(constraints.check_constraints(ir)),
        )

    def test_enum_value_too_wide_unsigned_error_message(self):
        ir = _make_ir_from_emb(
            '[$default byte_order: "LittleEndian"]\n'
            "enum Foo:\n"
            "  LOW = -2\n"
            "  LOW2 = -1\n"
            "  HIGH = 0x8000_0000_0000_0000\n"
        )
        error_value = ir.module[0].type[0].enumeration.value[2].value
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        error_value.source_location,
                        "Value 9223372036854775808 is out of range for 64-bit signed "
                        + "enumeration.",
                    )
                ]
            ],
            error.filter_errors(constraints.check_constraints(ir)),
        )

    def test_enum_value_too_wide_small_size_error_message(self):
        ir = _make_ir_from_emb(
            '[$default byte_order: "LittleEndian"]\n'
            "enum Foo:\n"
            "  [maximum_bits: 8]\n"
            "  HIGH = 0x100\n"
        )
        error_value = ir.module[0].type[0].enumeration.value[0].value
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        error_value.source_location,
                        "Value 256 is out of range for 8-bit unsigned enumeration.",
                    )
                ]
            ],
            error.filter_errors(constraints.check_constraints(ir)),
        )

    def test_enum_value_too_wide_small_size_signed_error_message(self):
        ir = _make_ir_from_emb(
            '[$default byte_order: "LittleEndian"]\n'
            "enum Foo:\n"
            "  [maximum_bits: 8]\n"
            "  [is_signed: true]\n"
            "  HIGH = 0x80\n"
        )
        error_value = ir.module[0].type[0].enumeration.value[0].value
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        error_value.source_location,
                        "Value 128 is out of range for 8-bit signed enumeration.",
                    )
                ]
            ],
            error.filter_errors(constraints.check_constraints(ir)),
        )

    def test_enum_value_too_wide_multiple(self):
        ir = _make_ir_from_emb(
            '[$default byte_order: "LittleEndian"]\n'
            "enum Foo:\n"
            "  LOW = -2\n"
            "  LOW2 = -1\n"
            "  HIGH = 0x8000_0000_0000_0000\n"
            "  HIGH2 = 0x8000_0000_0000_0001\n"
        )
        error_value = ir.module[0].type[0].enumeration.value[2].value
        error_value2 = ir.module[0].type[0].enumeration.value[3].value
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        error_value.source_location,
                        "Value 9223372036854775808 is out of range for 64-bit signed "
                        + "enumeration.",
                    )
                ],
                [
                    error.error(
                        "m.emb",
                        error_value2.source_location,
                        "Value 9223372036854775809 is out of range for 64-bit signed "
                        + "enumeration.",
                    )
                ],
            ],
            error.filter_errors(constraints.check_constraints(ir)),
        )

    def test_enum_value_too_wide_multiple_signed_error_message(self):
        ir = _make_ir_from_emb(
            '[$default byte_order: "LittleEndian"]\n'
            "enum Foo:\n"
            "  LOW = -3\n"
            "  LOW2 = -2\n"
            "  LOW3 = -1\n"
            "  HIGH = 0x8000_0000_0000_0000\n"
            "  HIGH2 = 0x8000_0000_0000_0001\n"
        )
        error_value = ir.module[0].type[0].enumeration.value[3].value
        error_value2 = ir.module[0].type[0].enumeration.value[4].value
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        error_value.source_location,
                        "Value 9223372036854775808 is out of range for 64-bit signed "
                        "enumeration.",
                    )
                ],
                [
                    error.error(
                        "m.emb",
                        error_value2.source_location,
                        "Value 9223372036854775809 is out of range for 64-bit signed "
                        "enumeration.",
                    )
                ],
            ],
            error.filter_errors(constraints.check_constraints(ir)),
        )

    def test_enum_value_mixed_error_message(self):
        ir = _make_ir_from_emb(
            '[$default byte_order: "LittleEndian"]\n'
            "enum Foo:\n"
            "  LOW = -1\n"
            "  HIGH = 0x8000_0000_0000_0000\n"
            "  HIGH2 = 0x1_0000_0000_0000_0000\n"
        )
        error_value1 = ir.module[0].type[0].enumeration.value[1].value
        error_value2 = ir.module[0].type[0].enumeration.value[2].value
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        error_value1.source_location,
                        "Value 9223372036854775808 is out of range for 64-bit signed "
                        + "enumeration.",
                    )
                ],
                [
                    error.error(
                        "m.emb",
                        error_value2.source_location,
                        "Value 18446744073709551616 is out of range for 64-bit signed "
                        + "enumeration.",
                    )
                ],
            ],
            error.filter_errors(constraints.check_constraints(ir)),
        )

    def test_enum_value_explicitly_signed_error_message(self):
        ir = _make_ir_from_emb(
            '[$default byte_order: "LittleEndian"]\n'
            "enum Foo:\n"
            "  [is_signed: true]\n"
            "  HIGH = 0x8000_0000_0000_0000\n"
            "  HIGH2 = 0x1_0000_0000_0000_0000\n"
        )
        error_value0 = ir.module[0].type[0].enumeration.value[0].value
        error_value1 = ir.module[0].type[0].enumeration.value[1].value
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        error_value0.source_location,
                        "Value 9223372036854775808 is out of range for 64-bit signed "
                        + "enumeration.",
                    )
                ],
                [
                    error.error(
                        "m.emb",
                        error_value1.source_location,
                        "Value 18446744073709551616 is out of range for 64-bit signed "
                        + "enumeration.",
                    )
                ],
            ],
            error.filter_errors(constraints.check_constraints(ir)),
        )

    def test_enum_value_explicitly_unsigned_error_message(self):
        ir = _make_ir_from_emb(
            '[$default byte_order: "LittleEndian"]\n'
            "enum Foo:\n"
            "  [is_signed: false]\n"
            "  LOW = -1\n"
            "  HIGH = 0x8000_0000_0000_0000\n"
            "  HIGH2 = 0x1_0000_0000_0000_0000\n"
        )
        error_value0 = ir.module[0].type[0].enumeration.value[0].value
        error_value2 = ir.module[0].type[0].enumeration.value[2].value
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        error_value0.source_location,
                        "Value -1 is out of range for 64-bit unsigned enumeration.",
                    )
                ],
                [
                    error.error(
                        "m.emb",
                        error_value2.source_location,
                        "Value 18446744073709551616 is out of range for 64-bit unsigned "
                        + "enumeration.",
                    )
                ],
            ],
            error.filter_errors(constraints.check_constraints(ir)),
        )

    def test_explicit_non_byte_size_array_element(self):
        ir = _make_ir_from_emb(
            '[$default byte_order: "LittleEndian"]\n'
            "struct Foo:\n"
            "  0 [+2]  UInt:4[4]  nibbles\n"
        )
        error_type = ir.module[0].type[0].structure.field[0].type.array_type
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        error_type.base_type.source_location,
                        "Array elements in structs must have sizes which are a multiple of "
                        "8 bits.",
                    )
                ]
            ],
            error.filter_errors(constraints.check_constraints(ir)),
        )

    def test_implicit_non_byte_size_array_element(self):
        ir = _make_ir_from_emb(
            '[$default byte_order: "LittleEndian"]\n'
            "bits Nibble:\n"
            "  0 [+4]  UInt  nibble\n"
            "struct Foo:\n"
            "  0 [+2]  Nibble[4]  nibbles\n"
        )
        error_type = ir.module[0].type[1].structure.field[0].type.array_type
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        error_type.base_type.source_location,
                        "Array elements in structs must have sizes which are a multiple of "
                        "8 bits.",
                    )
                ]
            ],
            error.filter_errors(constraints.check_constraints(ir)),
        )

    def test_bits_must_be_fixed_size(self):
        ir = _make_ir_from_emb(
            "bits Dynamic:\n"
            "  0 [+3]      UInt       x\n"
            "  3 [+3 * x]  UInt:3[x]  a\n"
        )
        error_type = ir.module[0].type[0]
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        error_type.source_location,
                        "`bits` types must be fixed size.",
                    )
                ]
            ],
            error.filter_errors(constraints.check_constraints(ir)),
        )

    def test_bits_must_be_small(self):
        ir = _make_ir_from_emb(
            "bits Big:\n" "  0  [+64]  UInt  x\n" "  64 [+1]   UInt  y\n"
        )
        error_type = ir.module[0].type[0]
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        error_type.source_location,
                        "`bits` types must be 64 bits or smaller.",
                    )
                ]
            ],
            error.filter_errors(constraints.check_constraints(ir)),
        )

    def test_constant_expressions_must_be_small(self):
        ir = _make_ir_from_emb(
            '[$default byte_order: "LittleEndian"]\n'
            "struct Foo:\n"
            "  0  [+8]   UInt  x\n"
            "  if x < 0x1_0000_0000_0000_0000:\n"
            "    8 [+1]   UInt  y\n"
        )
        condition = ir.module[0].type[0].structure.field[1].existence_condition
        error_location = condition.function.args[1].source_location
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        error_location,
                        "Constant value {} of expression cannot fit in a 64-bit signed or "
                        "unsigned integer.".format(2**64),
                    )
                ]
            ],
            error.filter_errors(constraints.check_constraints(ir)),
        )

    def test_variable_expression_out_of_range_for_uint64(self):
        ir = _make_ir_from_emb(
            '[$default byte_order: "LittleEndian"]\n'
            "struct Foo:\n"
            "  0  [+8]   UInt  x\n"
            "  if x + 1 < 0xffff_ffff_ffff_ffff:\n"
            "    8 [+1]   UInt  y\n"
        )
        condition = ir.module[0].type[0].structure.field[1].existence_condition
        error_location = condition.function.args[0].source_location
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        error_location,
                        "Potential range of expression is {} to {}, which cannot fit in a "
                        "64-bit signed or unsigned integer.".format(1, 2**64),
                    )
                ]
            ],
            error.filter_errors(constraints.check_constraints(ir)),
        )

    def test_variable_expression_out_of_range_for_int64(self):
        ir = _make_ir_from_emb(
            '[$default byte_order: "LittleEndian"]\n'
            "struct Foo:\n"
            "  0  [+8]   UInt  x\n"
            "  if x - 0x8000_0000_0000_0001 < 0:\n"
            "    8 [+1]   UInt  y\n"
        )
        condition = ir.module[0].type[0].structure.field[1].existence_condition
        error_location = condition.function.args[0].source_location
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        error_location,
                        "Potential range of expression is {} to {}, which cannot fit in a "
                        "64-bit signed or unsigned integer.".format(
                            -(2**63) - 1, 2**63 - 2
                        ),
                    )
                ]
            ],
            error.filter_errors(constraints.check_constraints(ir)),
        )

    def test_requires_expression_out_of_range_for_uint64(self):
        ir = _make_ir_from_emb(
            '[$default byte_order: "LittleEndian"]\n'
            "struct Foo:\n"
            "  0  [+8]   UInt  x\n"
            "    [requires: this * 2 < 0x1_0000]\n"
        )
        attribute_list = ir.module[0].type[0].structure.field[0].attribute
        error_arg = attribute_list[0].value.expression.function.args[0]
        error_location = error_arg.source_location
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        error_location,
                        "Potential range of expression is {} to {}, which cannot fit "
                        "in a 64-bit signed or unsigned integer.".format(0, 2**65 - 2),
                    )
                ]
            ],
            error.filter_errors(constraints.check_constraints(ir)),
        )

    def test_arguments_require_different_signedness_64_bits(self):
        ir = _make_ir_from_emb(
            '[$default byte_order: "LittleEndian"]\n'
            "struct Foo:\n"
            "  0 [+1]    UInt  x\n"
            # Left side requires uint64, right side requires int64.
            "  if (x + 0x8000_0000_0000_0000) + (x - 0x7fff_ffff_ffff_ffff) < 10:\n"
            "    1 [+1]  UInt  y\n"
        )
        condition = ir.module[0].type[0].structure.field[1].existence_condition
        error_expression = condition.function.args[0]
        error_location = error_expression.source_location
        arg0_location = error_expression.function.args[0].source_location
        arg1_location = error_expression.function.args[1].source_location
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        error_location,
                        "Either all arguments to '+' and its result must fit in a 64-bit "
                        "unsigned integer, or all must fit in a 64-bit signed integer.",
                    ),
                    error.note(
                        "m.emb", arg0_location, "Requires unsigned 64-bit integer."
                    ),
                    error.note(
                        "m.emb", arg1_location, "Requires signed 64-bit integer."
                    ),
                ]
            ],
            error.filter_errors(constraints.check_constraints(ir)),
        )

    def test_return_value_requires_different_signedness_from_arguments(self):
        ir = _make_ir_from_emb(
            '[$default byte_order: "LittleEndian"]\n'
            "struct Foo:\n"
            "  0 [+1]    UInt  x\n"
            # Both arguments require uint64; result fits in int64.
            "  if (x + 0x7fff_ffff_ffff_ffff) - 0x8000_0000_0000_0000 < 10:\n"
            "    1 [+1]  UInt  y\n"
        )
        condition = ir.module[0].type[0].structure.field[1].existence_condition
        error_expression = condition.function.args[0]
        error_location = error_expression.source_location
        arg0_location = error_expression.function.args[0].source_location
        arg1_location = error_expression.function.args[1].source_location
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        error_location,
                        "Either all arguments to '-' and its result must fit in a 64-bit "
                        "unsigned integer, or all must fit in a 64-bit signed integer.",
                    ),
                    error.note(
                        "m.emb", arg0_location, "Requires unsigned 64-bit integer."
                    ),
                    error.note(
                        "m.emb", arg1_location, "Requires unsigned 64-bit integer."
                    ),
                    error.note(
                        "m.emb", error_location, "Requires signed 64-bit integer."
                    ),
                ]
            ],
            error.filter_errors(constraints.check_constraints(ir)),
        )

    def test_return_value_requires_different_signedness_from_one_argument(self):
        ir = _make_ir_from_emb(
            '[$default byte_order: "LittleEndian"]\n'
            "struct Foo:\n"
            "  0 [+1]    UInt  x\n"
            # One argument requires uint64; result fits in int64.
            "  if (x + 0x7fff_ffff_ffff_fff0) - 0x7fff_ffff_ffff_ffff < 10:\n"
            "    1 [+1]  UInt  y\n"
        )
        condition = ir.module[0].type[0].structure.field[1].existence_condition
        error_expression = condition.function.args[0]
        error_location = error_expression.source_location
        arg0_location = error_expression.function.args[0].source_location
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        error_location,
                        "Either all arguments to '-' and its result must fit in a 64-bit "
                        "unsigned integer, or all must fit in a 64-bit signed integer.",
                    ),
                    error.note(
                        "m.emb", arg0_location, "Requires unsigned 64-bit integer."
                    ),
                    error.note(
                        "m.emb", error_location, "Requires signed 64-bit integer."
                    ),
                ]
            ],
            error.filter_errors(constraints.check_constraints(ir)),
        )

    def test_checks_constancy_of_constant_references(self):
        ir = _make_ir_from_emb(
            "struct Foo:\n" "  0 [+1]  UInt  x\n" "  let y = x\n" "  let z = Foo.y\n"
        )
        error_expression = ir.module[0].type[0].structure.field[2].read_transform
        error_location = error_expression.source_location
        note_field = ir.module[0].type[0].structure.field[1]
        note_location = note_field.source_location
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        error_location,
                        "Static references must refer to constants.",
                    ),
                    error.note("m.emb", note_location, "y is not constant."),
                ]
            ],
            error.filter_errors(constraints.check_constraints(ir)),
        )

    def test_checks_for_explicit_size_on_parameters(self):
        ir = _make_ir_from_emb("struct Foo(y: UInt):\n" "  0 [+1]  UInt  x\n")
        error_parameter = ir.module[0].type[0].runtime_parameter[0]
        error_location = error_parameter.physical_type_alias.source_location
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        error_location,
                        "Integer range of parameter must not be unbounded; it "
                        "must fit in a 64-bit signed or unsigned integer.",
                    )
                ]
            ],
            error.filter_errors(constraints.check_constraints(ir)),
        )

    def test_checks_for_correct_explicit_size_on_parameters(self):
        ir = _make_ir_from_emb("struct Foo(y: UInt:300):\n" "  0 [+1]  UInt  x\n")
        error_parameter = ir.module[0].type[0].runtime_parameter[0]
        error_location = error_parameter.physical_type_alias.source_location
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        error_location,
                        "Potential range of parameter is 0 to {}, which cannot "
                        "fit in a 64-bit signed or unsigned integer.".format(
                            2**300 - 1
                        ),
                    )
                ]
            ],
            error.filter_errors(constraints.check_constraints(ir)),
        )

    def test_checks_for_explicit_enum_size_on_parameters(self):
        ir = _make_ir_from_emb(
            "struct Foo(y: Bar:8):\n" "  0 [+1]  UInt  x\n" "enum Bar:\n" "  QUX = 1\n"
        )
        error_parameter = ir.module[0].type[0].runtime_parameter[0]
        error_size = error_parameter.physical_type_alias.size_in_bits
        error_location = error_size.source_location
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        error_location,
                        "Parameters with enum type may not have explicit size.",
                    )
                ]
            ],
            error.filter_errors(constraints.check_constraints(ir)),
        )


if __name__ == "__main__":
    unittest.main()
