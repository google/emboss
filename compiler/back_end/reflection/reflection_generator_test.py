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

"""Tests for the reflection generator."""

import json
import unittest

from compiler.back_end.reflection import reflection_generator
from compiler.front_end import glue
from compiler.util import test_util

_PREAMBLE = '[$default byte_order: "LittleEndian"]\n'


def _reflect(emb_text, name="m.emb"):
    """Reflects `emb_text` with a default byte order prepended."""
    return _reflect_files({name: _PREAMBLE + emb_text}, name)


def _reflect_files(files, name="m.emb"):
    """Reflects `files[name]`, returning the parsed JSON of its one module."""
    ir, _, errors = glue.parse_emboss_file(name, test_util.dict_file_reader(files))
    assert not errors, errors
    text, errors = reflection_generator.generate_reflection(ir)
    assert not errors, errors
    return json.loads(text)["modules"][0]


def _types(module):
    return {
        type_reflection["name"]: type_reflection for type_reflection in module["types"]
    }


def _fields(type_reflection):
    return {field["name"]: field for field in type_reflection["fields"]}


def _virtuals(type_reflection):
    return {virtual["name"]: virtual for virtual in type_reflection["virtuals"]}


class ModuleTest(unittest.TestCase):

    def test_reports_source_file_and_documentation(self):
        module = _reflect_files(
            {"m.emb": "-- Module docs.\n\nstruct Foo:\n  0 [+1]  UInt  x\n"}
        )
        self.assertEqual("m.emb", module["source_file_name"])
        self.assertEqual("Module docs.", module["documentation"])

    def test_reports_only_the_main_module(self):
        module = _reflect_files(
            {
                "m.emb": 'import "other.emb" as other\n\nstruct Foo:\n  0 [+1]  UInt  x\n',
                "other.emb": "struct Other:\n  0 [+1]  UInt  y\n",
            }
        )
        self.assertEqual("m.emb", module["source_file_name"])
        self.assertEqual(["Foo"], [t["name"] for t in module["types"]])

    def test_output_is_valid_json_ending_in_a_newline(self):
        ir, _, errors = glue.parse_emboss_file(
            "m.emb",
            test_util.dict_file_reader({"m.emb": "struct Foo:\n  0 [+1]  UInt  x\n"}),
        )
        assert not errors, errors
        text, _ = reflection_generator.generate_reflection(ir)
        self.assertTrue(text.endswith("\n"))
        json.loads(text)


class TypeTest(unittest.TestCase):

    def test_reports_kind_and_canonical_name(self):
        types = _types(
            _reflect(
                "struct Foo:\n"
                "  enum Inner:\n"
                "    AAA = 1\n"
                "  0 [+1]  Bar  bar\n"
                "\n"
                "bits Bar:\n"
                "  0 [+8]  UInt  f\n"
            )
        )
        self.assertEqual("struct", types["Foo"]["kind"])
        self.assertEqual("bits", types["Bar"]["kind"])
        self.assertEqual("enum", types["Inner"]["kind"])
        self.assertEqual(
            {"module_file": "m.emb", "object_path": ["Foo", "Inner"]},
            types["Inner"]["canonical_name"],
        )

    def test_reports_fixed_bit_size(self):
        types = _types(
            _reflect("struct Foo:\n  0 [+4]  UInt  x\n\nbits Bar:\n  0 [+3]  UInt  y\n")
        )
        self.assertEqual(32, types["Foo"]["bit_size"])
        self.assertEqual(3, types["Bar"]["bit_size"])

    def test_reports_size_bounds_of_a_dynamically_sized_structure(self):
        # A dynamically-sized structure has no one size, but the compiler knows
        # the range, and that is what a consumer can use instead.
        types = _types(
            _reflect(
                "struct Foo:\n"
                "  0 [+1]     UInt      size\n"
                "  1 [+size]  UInt:8[]  payload\n"
            )
        )
        self.assertIsNone(types["Foo"]["bit_size"])
        self.assertEqual(8, types["Foo"]["min_bit_size"])
        self.assertEqual(2048, types["Foo"]["max_bit_size"])

    def test_reports_equal_size_bounds_for_a_fixed_size_structure(self):
        types = _types(_reflect("struct Foo:\n  0 [+4]  UInt  x\n"))
        self.assertEqual(
            (32, 32, 32),
            (
                types["Foo"]["bit_size"],
                types["Foo"]["min_bit_size"],
                types["Foo"]["max_bit_size"],
            ),
        )

    def test_reports_no_bit_size_for_a_dynamically_sized_structure(self):
        types = _types(
            _reflect(
                "struct Foo:\n"
                "  0 [+1]           UInt     size\n"
                "  1 [+size]        UInt:8[]  payload\n"
            )
        )
        self.assertIsNone(types["Foo"]["bit_size"])

    def test_reports_type_documentation_and_requires(self):
        types = _types(
            _reflect(
                "struct Foo:\n"
                "  -- Docs for Foo.\n"
                "  [requires: x == 1]\n"
                "  0 [+1]  UInt  x\n"
            )
        )
        self.assertEqual("Docs for Foo.", types["Foo"]["documentation"])
        self.assertEqual(["x == 1"], types["Foo"]["requires"])


class ByteOrderTest(unittest.TestCase):

    def test_reports_the_unanimous_byte_order(self):
        types = _types(_reflect("struct Foo:\n  0 [+2]  UInt  x\n  2 [+2]  UInt  y\n"))
        self.assertEqual("LittleEndian", types["Foo"]["byte_order"])
        self.assertEqual("LittleEndian", _fields(types["Foo"])["x"]["byte_order"])

    def test_reports_no_structure_byte_order_when_fields_disagree(self):
        # Mixed byte order is legal Emboss, so this must not be an error: the
        # structure reports None and each field reports its own order.
        types = _types(
            _reflect(
                "struct Foo:\n"
                "  0 [+2]  UInt  x\n"
                "  2 [+2]  UInt  y\n"
                '    [byte_order: "BigEndian"]\n'
            )
        )
        self.assertIsNone(types["Foo"]["byte_order"])
        fields = _fields(types["Foo"])
        self.assertEqual("LittleEndian", fields["x"]["byte_order"])
        self.assertEqual("BigEndian", fields["y"]["byte_order"])


class PhysicalFieldTest(unittest.TestCase):

    def test_reports_offsets_and_sizes_in_bits(self):
        fields = _fields(
            _types(_reflect("struct Foo:\n  0 [+1]  UInt  x\n  1 [+4]  UInt  y\n"))[
                "Foo"
            ]
        )
        self.assertEqual((0, 8), (fields["x"]["bit_offset"], fields["x"]["bit_size"]))
        self.assertEqual((8, 32), (fields["y"]["bit_offset"], fields["y"]["bit_size"]))

    def test_reports_bit_offsets_within_a_bits(self):
        fields = _fields(
            _types(_reflect("bits Foo:\n  0 [+1]  Flag  x\n  1 [+3]  UInt  y\n"))["Foo"]
        )
        self.assertEqual((0, 1), (fields["x"]["bit_offset"], fields["x"]["bit_size"]))
        self.assertEqual((1, 3), (fields["y"]["bit_offset"], fields["y"]["bit_size"]))

    def test_reports_the_bit_size_of_an_explicitly_sized_type(self):
        fields = _fields(_types(_reflect("struct Foo:\n  0 [+3]  UInt:24  x\n"))["Foo"])
        self.assertEqual(24, fields["x"]["bit_size"])

    def test_reports_offsets_relative_to_the_containing_named_type(self):
        types = _types(
            _reflect(
                "struct Outer:\n"
                "  0 [+4]  UInt   pad\n"
                "  4 [+4]  Inner  inner\n"
                "\n"
                "struct Inner:\n"
                "  0 [+4]  UInt  x\n"
            )
        )
        # `inner` stays one field; `Inner.x` is at 0 within `Inner`, not at 32.
        self.assertEqual(32, _fields(types["Outer"])["inner"]["bit_offset"])
        self.assertEqual(0, _fields(types["Inner"])["x"]["bit_offset"])
        self.assertNotIn("x", _fields(types["Outer"]))

    def test_reports_abbreviations(self):
        fields = _fields(
            _types(_reflect("struct Foo:\n  0 [+1]  UInt  x (a)\n"))["Foo"]
        )
        self.assertEqual("a", fields["x"]["abbreviation"])

    def test_reports_arrays(self):
        fields = _fields(
            _types(
                _reflect(
                    "struct Foo:\n"
                    "  0 [+4]  UInt:8[4]  fixed\n"
                    "  4 [+4]  UInt:8[]   automatic\n"
                )
            )["Foo"]
        )
        self.assertEqual(
            (True, 4),
            (fields["fixed"]["is_array"], fields["fixed"]["array_element_count"]),
        )
        self.assertEqual(
            (True, None),
            (
                fields["automatic"]["is_array"],
                fields["automatic"]["array_element_count"],
            ),
        )
        self.assertEqual("UInt", fields["fixed"]["type_name"])

    def test_reports_documentation_and_requires(self):
        fields = _fields(
            _types(
                _reflect(
                    "struct Foo:\n"
                    "  0 [+1]  UInt  x\n"
                    "    -- Docs for x.\n"
                    "    [requires: 1 <= this <= 5]\n"
                )
            )["Foo"]
        )
        self.assertEqual("Docs for x.", fields["x"]["documentation"])
        self.assertEqual(["1 <= this && this <= 5"], fields["x"]["requires"])


class SignednessTest(unittest.TestCase):

    def test_reports_signedness_of_prelude_integers(self):
        fields = _fields(
            _types(
                _reflect(
                    "struct Foo:\n"
                    "  0 [+1]  UInt  u\n"
                    "  1 [+1]  Int   i\n"
                    "  2 [+1]  Bcd   b\n"
                )
            )["Foo"]
        )
        self.assertFalse(fields["u"]["is_signed"])
        self.assertTrue(fields["i"]["is_signed"])
        self.assertFalse(fields["b"]["is_signed"])

    def test_reports_no_signedness_for_non_numeric_types(self):
        types = _types(
            _reflect(
                "struct Foo:\n"
                "  0 [+1]  Bar  bar\n"
                "\n"
                "bits Bar:\n"
                "  0 [+1]  Flag  f\n"
                "  1 [+7]  UInt  rest\n"
            )
        )
        self.assertIsNone(_fields(types["Foo"])["bar"]["is_signed"])
        self.assertIsNone(_fields(types["Bar"])["f"]["is_signed"])

    def test_reports_signedness_of_enums(self):
        # An enum with a negative member is signed; this is the case a
        # `type_name == "Int"` test would miss.
        types = _types(
            _reflect(
                "struct Foo:\n"
                "  0 [+1]  Signed    s\n"
                "  1 [+1]  Unsigned  u\n"
                "\n"
                "enum Signed:\n"
                "  NEGATIVE = -1\n"
                "\n"
                "enum Unsigned:\n"
                "  POSITIVE = 1\n"
            )
        )
        fields = _fields(types["Foo"])
        self.assertTrue(fields["s"]["is_signed"])
        self.assertFalse(fields["u"]["is_signed"])
        self.assertEqual("Signed", fields["s"]["enum_ref"])
        self.assertTrue(types["Signed"]["is_signed"])

    def test_reports_signedness_of_virtual_fields(self):
        virtuals = _virtuals(
            _types(
                _reflect(
                    "struct Foo:\n"
                    "  0 [+1]  UInt  x\n"
                    "  let plain = x + 1\n"
                    "  let negated = -1 - x\n"
                    "  let flagged = x == 1\n"
                )
            )["Foo"]
        )
        self.assertFalse(virtuals["plain"]["is_signed"])
        self.assertTrue(virtuals["negated"]["is_signed"])
        self.assertIsNone(virtuals["flagged"]["is_signed"])


class AnonymousBitsTest(unittest.TestCase):

    def test_lifts_anonymous_bits_fields_to_absolute_offsets(self):
        types = _types(
            _reflect(
                "struct Foo:\n"
                "  0 [+4]  bits:\n"
                "    0  [+1]  Flag  low\n"
                "    31 [+1]  Flag  top\n"
                "  4 [+1]  UInt  trailer\n"
            )
        )
        self.assertEqual(
            ["low", "top", "trailer"], [f["name"] for f in types["Foo"]["fields"]]
        )
        fields = _fields(types["Foo"])
        self.assertEqual(0, fields["low"]["bit_offset"])
        self.assertEqual(31, fields["top"]["bit_offset"])
        self.assertEqual(32, fields["trailer"]["bit_offset"])

    def test_does_not_report_the_anonymous_type_or_its_alias_virtuals(self):
        module = _reflect("struct Foo:\n" "  0 [+4]  bits:\n" "    0 [+1]  Flag  low\n")
        self.assertEqual(["Foo"], [t["name"] for t in module["types"]])
        self.assertEqual([], module["types"][0]["virtuals"])

    def test_conjoins_an_enclosing_existence_condition(self):
        types = _types(
            _reflect(
                "struct Foo:\n"
                "  0 [+1]  UInt  x\n"
                "  if x == 1:\n"
                "    4 [+4]  bits:\n"
                "      0 [+1]  Flag  low\n"
            )
        )
        self.assertEqual("x == 1", _fields(types["Foo"])["low"]["existence_condition"])


class VirtualFieldTest(unittest.TestCase):

    def test_reports_constant_lets(self):
        virtuals = _virtuals(
            _types(_reflect("struct Foo:\n  0 [+1]  UInt  x\n  let ten = 10\n"))["Foo"]
        )
        self.assertEqual(10, virtuals["ten"]["value"])
        self.assertEqual("10", virtuals["ten"]["value_expression"])
        self.assertTrue(virtuals["ten"]["is_read_only"])

    def test_reports_non_constant_lets_as_expressions(self):
        virtuals = _virtuals(
            _types(_reflect("struct Foo:\n  0 [+1]  UInt  x\n  let two_x = x * 2\n"))[
                "Foo"
            ]
        )
        self.assertIsNone(virtuals["two_x"]["value"])
        self.assertEqual("x * 2", virtuals["two_x"]["value_expression"])

    def test_skips_compiler_generated_virtuals(self):
        virtuals = _virtuals(
            _types(_reflect("struct Foo:\n  0 [+1]  UInt  x\n"))["Foo"]
        )
        self.assertEqual({}, virtuals)


class ConditionalAndDynamicTest(unittest.TestCase):

    def test_reports_existence_conditions(self):
        fields = _fields(
            _types(
                _reflect(
                    "struct Foo:\n"
                    "  0 [+1]  UInt  x\n"
                    "  if x == 1:\n"
                    "    1 [+1]  UInt  y\n"
                )
            )["Foo"]
        )
        self.assertEqual("true", fields["x"]["existence_condition"])
        self.assertEqual("x == 1", fields["y"]["existence_condition"])

    def test_reports_non_constant_placement_as_null_plus_an_expression(self):
        # A field after a variable-length field is normal, not an error: it is
        # reported with the Emboss expression that places it.
        fields = _fields(
            _types(
                _reflect(
                    "struct Foo:\n"
                    "  0     [+1]      UInt      size\n"
                    "  1     [+size]   UInt:8[]  payload\n"
                    "  1+size [+4]     UInt      crc\n"
                )
            )["Foo"]
        )
        self.assertIsNone(fields["payload"]["bit_size"])
        self.assertEqual("size", fields["payload"]["size_expression"])
        self.assertIsNone(fields["crc"]["bit_offset"])
        self.assertEqual("1 + size", fields["crc"]["offset_expression"])
        self.assertEqual(32, fields["crc"]["bit_size"])

    def test_reports_alignment_of_a_non_constant_offset(self):
        fields = _fields(
            _types(
                _reflect(
                    "struct Foo:\n"
                    "  0        [+1]     UInt      size\n"
                    "  1        [+size]  UInt:8[]  payload\n"
                    "  1+size   [+4]     UInt      crc\n"
                )
            )["Foo"]
        )
        # Nothing is known about `crc`'s byte offset, but it is byte-aligned.
        self.assertEqual({"modulus": 8, "remainder": 0}, fields["crc"]["alignment"])
        # A constant offset needs no alignment: `bit_offset` says everything.
        self.assertIsNone(fields["size"]["alignment"])


class EnumTest(unittest.TestCase):

    def test_reports_members_documentation_and_width(self):
        types = _types(
            _reflect(
                "enum Foo:\n"
                "  -- Docs for Foo.\n"
                "  [maximum_bits: 32]\n"
                "  ZERO = 0\n"
                "    -- Docs for ZERO.\n"
                "  BIG  = 1000\n"
            )
        )
        self.assertEqual("Docs for Foo.", types["Foo"]["documentation"])
        self.assertEqual(32, types["Foo"]["maximum_bits"])
        self.assertEqual(
            [
                {"name": "ZERO", "value": 0, "documentation": "Docs for ZERO."},
                {"name": "BIG", "value": 1000, "documentation": ""},
            ],
            types["Foo"]["members"],
        )


class ParameterTest(unittest.TestCase):

    def test_reports_runtime_parameters(self):
        types = _types(
            _reflect("struct Foo(n: UInt:8):\n" "  0 [+n]  UInt:8[]  payload\n")
        )
        self.assertEqual(
            [{"name": "n", "type": "integer", "physical_type_name": "UInt"}],
            types["Foo"]["parameters"],
        )


if __name__ == "__main__":
    unittest.main()
