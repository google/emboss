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

"""Tests for front_end.synthetics."""

import unittest
from compiler.front_end import glue
from compiler.front_end import synthetics
from compiler.util import error
from compiler.util import ir_data
from compiler.util import test_util


class SyntheticsTest(unittest.TestCase):

    def _find_attribute(self, field, name):
        result = None
        for attribute in field.attribute:
            if attribute.name.text == name:
                self.assertIsNone(result)
                result = attribute
        self.assertIsNotNone(result)
        return result

    def _make_ir(self, emb_text):
        ir, unused_debug_info, errors = glue.parse_emboss_file(
            "m.emb",
            test_util.dict_file_reader({"m.emb": emb_text}),
            stop_before_step="desugar",
        )
        assert not errors, errors
        return ir

    def test_nothing_to_do(self):
        ir = self._make_ir(
            "struct Foo:\n" "  0 [+1]     UInt      x\n" "  1 [+1]     UInt:8[]  y\n"
        )
        self.assertEqual([], synthetics.desugar(ir))

    def test_adds_anonymous_bits_fields(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  0 [+1]  bits:\n"
            "    0 [+4]  Bar   bar\n"
            "    4 [+4]  UInt  uint\n"
            "  1 [+1]  bits:\n"
            "    0 [+4]  Bits  nested_bits\n"
            "enum Bar:\n"
            "  BAR = 0\n"
            "bits Bits:\n"
            "  0 [+4]  UInt  uint\n"
        )
        self.assertEqual([], synthetics.desugar(ir))
        structure = ir.module[0].type[0].structure
        # The first field should be the anonymous bits structure.
        self.assertTrue(structure.field[0].HasField("location"))
        # Then the aliases generated for those structures.
        self.assertEqual("bar", structure.field[1].name.name.text)
        self.assertEqual("uint", structure.field[2].name.name.text)
        # Then the second anonymous bits.
        self.assertTrue(structure.field[3].HasField("location"))
        # Then the alias from the second anonymous bits.
        self.assertEqual("nested_bits", structure.field[4].name.name.text)

    def test_adds_correct_existence_condition(self):
        ir = self._make_ir(
            "struct Foo:\n" "  0 [+1]  bits:\n" "    0 [+4]  UInt  bar\n"
        )
        self.assertEqual([], synthetics.desugar(ir))
        bits_field = ir.module[0].type[0].structure.field[0]
        alias_field = ir.module[0].type[0].structure.field[1]
        self.assertEqual("bar", alias_field.name.name.text)
        self.assertEqual(
            bits_field.name.name.text,
            alias_field.existence_condition.function.args[0]
            .function.args[0]
            .field_reference.path[0]
            .source_name[-1]
            .text,
        )
        self.assertEqual(
            bits_field.name.name.text,
            alias_field.existence_condition.function.args[1]
            .function.args[0]
            .field_reference.path[0]
            .source_name[-1]
            .text,
        )
        self.assertEqual(
            "bar",
            alias_field.existence_condition.function.args[1]
            .function.args[0]
            .field_reference.path[1]
            .source_name[-1]
            .text,
        )
        self.assertEqual(
            ir_data.FunctionMapping.PRESENCE,
            alias_field.existence_condition.function.args[0].function.function,
        )
        self.assertEqual(
            ir_data.FunctionMapping.PRESENCE,
            alias_field.existence_condition.function.args[1].function.function,
        )
        self.assertEqual(
            ir_data.FunctionMapping.AND,
            alias_field.existence_condition.function.function,
        )

    def test_adds_correct_read_transform(self):
        ir = self._make_ir(
            "struct Foo:\n" "  0 [+1]  bits:\n" "    0 [+4]  UInt  bar\n"
        )
        self.assertEqual([], synthetics.desugar(ir))
        bits_field = ir.module[0].type[0].structure.field[0]
        alias_field = ir.module[0].type[0].structure.field[1]
        self.assertEqual("bar", alias_field.name.name.text)
        self.assertEqual(
            bits_field.name.name.text,
            alias_field.read_transform.field_reference.path[0].source_name[-1].text,
        )
        self.assertEqual(
            "bar",
            alias_field.read_transform.field_reference.path[1].source_name[-1].text,
        )

    def test_adds_correct_abbreviation(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  0 [+1]  bits:\n"
            "    0 [+4]  UInt  bar\n"
            "    4 [+4]  UInt  baz (qux)\n"
        )
        self.assertEqual([], synthetics.desugar(ir))
        bar_alias = ir.module[0].type[0].structure.field[1]
        baz_alias = ir.module[0].type[0].structure.field[2]
        self.assertFalse(bar_alias.HasField("abbreviation"))
        self.assertEqual("qux", baz_alias.abbreviation.text)

    def test_anonymous_bits_sets_correct_is_synthetic(self):
        ir = self._make_ir(
            "struct Foo:\n" "  0 [+1]  bits:\n" "    0 [+4]  UInt  bar (b)\n"
        )
        self.assertEqual([], synthetics.desugar(ir))
        bits_field = ir.module[0].type[0].subtype[0].structure.field[0]
        alias_field = ir.module[0].type[0].structure.field[1]
        self.assertFalse(alias_field.name.source_location.is_synthetic)
        self.assertTrue(alias_field.HasField("abbreviation"))
        self.assertFalse(alias_field.abbreviation.source_location.is_synthetic)
        self.assertTrue(alias_field.HasField("read_transform"))
        read_alias = alias_field.read_transform
        self.assertTrue(read_alias.source_location.is_synthetic)
        self.assertTrue(read_alias.field_reference.path[0].source_location.is_synthetic)
        alias_condition = alias_field.existence_condition
        self.assertTrue(alias_condition.source_location.is_synthetic)
        self.assertTrue(alias_condition.function.args[0].source_location.is_synthetic)
        self.assertTrue(bits_field.name.source_location.is_synthetic)
        self.assertTrue(bits_field.name.name.source_location.is_synthetic)
        self.assertTrue(bits_field.abbreviation.source_location.is_synthetic)

    def test_adds_text_output_skip_attribute_to_anonymous_bits(self):
        ir = self._make_ir(
            "struct Foo:\n" "  0 [+1]  bits:\n" "    0 [+4]  UInt  bar (b)\n"
        )
        self.assertEqual([], synthetics.desugar(ir))
        bits_field = ir.module[0].type[0].structure.field[0]
        text_output_attribute = self._find_attribute(bits_field, "text_output")
        self.assertEqual("Skip", text_output_attribute.value.string_constant.text)

    def test_skip_attribute_is_marked_as_synthetic(self):
        ir = self._make_ir(
            "struct Foo:\n" "  0 [+1]  bits:\n" "    0 [+4]  UInt  bar\n"
        )
        self.assertEqual([], synthetics.desugar(ir))
        bits_field = ir.module[0].type[0].structure.field[0]
        attribute = self._find_attribute(bits_field, "text_output")
        self.assertTrue(attribute.source_location.is_synthetic)
        self.assertTrue(attribute.name.source_location.is_synthetic)
        self.assertTrue(attribute.value.source_location.is_synthetic)
        self.assertTrue(attribute.value.string_constant.source_location.is_synthetic)

    def test_adds_size_in_bytes(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  1 [+l]  UInt:8[]  bytes\n"
            "  0 [+1]  UInt      length (l)\n"
        )
        self.assertEqual([], synthetics.desugar(ir))
        structure = ir.module[0].type[0].structure
        size_in_bytes_field = structure.field[2]
        max_size_in_bytes_field = structure.field[3]
        min_size_in_bytes_field = structure.field[4]
        self.assertEqual("$size_in_bytes", size_in_bytes_field.name.name.text)
        self.assertEqual(
            ir_data.FunctionMapping.MAXIMUM,
            size_in_bytes_field.read_transform.function.function,
        )
        self.assertEqual("$max_size_in_bytes", max_size_in_bytes_field.name.name.text)
        self.assertEqual(
            ir_data.FunctionMapping.UPPER_BOUND,
            max_size_in_bytes_field.read_transform.function.function,
        )
        self.assertEqual("$min_size_in_bytes", min_size_in_bytes_field.name.name.text)
        self.assertEqual(
            ir_data.FunctionMapping.LOWER_BOUND,
            min_size_in_bytes_field.read_transform.function.function,
        )
        # The correctness of $size_in_bytes et al are tested much further down
        # stream, in tests of the generated C++ code.

    def test_adds_size_in_bits(self):
        ir = self._make_ir("bits Foo:\n" "  1 [+9]  UInt  hi\n" "  0 [+1]  Flag  lo\n")
        self.assertEqual([], synthetics.desugar(ir))
        structure = ir.module[0].type[0].structure
        size_in_bits_field = structure.field[2]
        max_size_in_bits_field = structure.field[3]
        min_size_in_bits_field = structure.field[4]
        self.assertEqual("$size_in_bits", size_in_bits_field.name.name.text)
        self.assertEqual(
            ir_data.FunctionMapping.MAXIMUM,
            size_in_bits_field.read_transform.function.function,
        )
        self.assertEqual("$max_size_in_bits", max_size_in_bits_field.name.name.text)
        self.assertEqual(
            ir_data.FunctionMapping.UPPER_BOUND,
            max_size_in_bits_field.read_transform.function.function,
        )
        self.assertEqual("$min_size_in_bits", min_size_in_bits_field.name.name.text)
        self.assertEqual(
            ir_data.FunctionMapping.LOWER_BOUND,
            min_size_in_bits_field.read_transform.function.function,
        )
        # The correctness of $size_in_bits et al are tested much further down
        # stream, in tests of the generated C++ code.

    def test_adds_text_output_skip_attribute_to_size_in_bytes(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  1 [+l]  UInt:8[]  bytes\n"
            "  0 [+1]  UInt      length (l)\n"
        )
        self.assertEqual([], synthetics.desugar(ir))
        size_in_bytes_field = ir.module[0].type[0].structure.field[2]
        self.assertEqual("$size_in_bytes", size_in_bytes_field.name.name.text)
        text_output_attribute = self._find_attribute(size_in_bytes_field, "text_output")
        self.assertEqual("Skip", text_output_attribute.value.string_constant.text)

    def test_replaces_next(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  1     [+2]  UInt:8[]  a\n"
            "  $next [+4]  UInt      b\n"
            "  $next [+1]  UInt      c\n"
        )
        self.assertEqual([], synthetics.desugar(ir))
        offset_of_b = ir.module[0].type[0].structure.field[1].location.start
        self.assertTrue(offset_of_b.HasField("function"))
        self.assertEqual(
            offset_of_b.function.function, ir_data.FunctionMapping.ADDITION
        )
        self.assertEqual(offset_of_b.function.args[0].constant.value, "1")
        self.assertEqual(offset_of_b.function.args[1].constant.value, "2")
        offset_of_c = ir.module[0].type[0].structure.field[2].location.start
        self.assertEqual(
            offset_of_c.function.args[0].function.args[0].constant.value, "1"
        )
        self.assertEqual(
            offset_of_c.function.args[0].function.args[1].constant.value, "2"
        )
        self.assertEqual(offset_of_c.function.args[1].constant.value, "4")

    def test_next_in_first_field(self):
        ir = self._make_ir(
            "struct Foo:\n" "  $next [+2]  UInt:8[]  a\n" "  $next [+4]  UInt      b\n"
        )
        struct = ir.module[0].type[0].structure
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        struct.field[0].location.start.source_location,
                        "`$next` may not be used in the first physical field of "
                        + "a structure; perhaps you meant `0`?",
                    ),
                ]
            ],
            synthetics.desugar(ir),
        )

    def test_next_in_size(self):
        ir = self._make_ir(
            "struct Foo:\n" "  0 [+2]      UInt:8[]  a\n" "  1 [+$next]  UInt      b\n"
        )
        struct = ir.module[0].type[0].structure
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        struct.field[1].location.size.source_location,
                        "`$next` may only be used in the start expression of a "
                        + "physical field.",
                    ),
                ]
            ],
            synthetics.desugar(ir),
        )


if __name__ == "__main__":
    unittest.main()
