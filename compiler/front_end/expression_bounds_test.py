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

"""Tests for expression_bounds."""

import unittest
from compiler.front_end import expression_bounds
from compiler.front_end import glue
from compiler.util import test_util


class ComputeConstantsTest(unittest.TestCase):

    def _make_ir(self, emb_text):
        ir, unused_debug_info, errors = glue.parse_emboss_file(
            "m.emb",
            test_util.dict_file_reader({"m.emb": emb_text}),
            stop_before_step="compute_constants",
        )
        assert not errors, errors
        return ir

    def test_constant_integer(self):
        ir = self._make_ir("struct Foo:\n" "  10 [+1]  UInt  x\n")
        self.assertEqual([], expression_bounds.compute_constants(ir))
        start = ir.module[0].type[0].structure.field[0].location.start
        self.assertEqual("10", start.type.integer.minimum_value)
        self.assertEqual("10", start.type.integer.maximum_value)
        self.assertEqual("10", start.type.integer.modular_value)
        self.assertEqual("infinity", start.type.integer.modulus)

    def test_boolean_constant(self):
        ir = self._make_ir("struct Foo:\n" "  if true:\n" "    0 [+1]  UInt  x\n")
        self.assertEqual([], expression_bounds.compute_constants(ir))
        expression = ir.module[0].type[0].structure.field[0].existence_condition
        self.assertTrue(expression.type.boolean.HasField("value"))
        self.assertTrue(expression.type.boolean.value)

    def test_constant_equality(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  if 5 == 5:\n"
            "    0 [+1]  UInt  x\n"
            "  if 5 == 6:\n"
            "    0 [+1]  UInt  y\n"
        )
        self.assertEqual([], expression_bounds.compute_constants(ir))
        structure = ir.module[0].type[0].structure
        true_condition = structure.field[0].existence_condition
        false_condition = structure.field[1].existence_condition
        self.assertTrue(true_condition.type.boolean.HasField("value"))
        self.assertTrue(true_condition.type.boolean.value)
        self.assertTrue(false_condition.type.boolean.HasField("value"))
        self.assertFalse(false_condition.type.boolean.value)

    def test_constant_inequality(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  if 5 != 5:\n"
            "    0 [+1]  UInt  x\n"
            "  if 5 != 6:\n"
            "    0 [+1]  UInt  y\n"
        )
        self.assertEqual([], expression_bounds.compute_constants(ir))
        structure = ir.module[0].type[0].structure
        false_condition = structure.field[0].existence_condition
        true_condition = structure.field[1].existence_condition
        self.assertTrue(false_condition.type.boolean.HasField("value"))
        self.assertFalse(false_condition.type.boolean.value)
        self.assertTrue(true_condition.type.boolean.HasField("value"))
        self.assertTrue(true_condition.type.boolean.value)

    def test_constant_less_than(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  if 5 < 4:\n"
            "    0 [+1]  UInt  x\n"
            "  if 5 < 5:\n"
            "    0 [+1]  UInt  y\n"
            "  if 5 < 6:\n"
            "    0 [+1]  UInt  z\n"
        )
        self.assertEqual([], expression_bounds.compute_constants(ir))
        structure = ir.module[0].type[0].structure
        greater_than_condition = structure.field[0].existence_condition
        equal_condition = structure.field[1].existence_condition
        less_than_condition = structure.field[2].existence_condition
        self.assertTrue(greater_than_condition.type.boolean.HasField("value"))
        self.assertFalse(greater_than_condition.type.boolean.value)
        self.assertTrue(equal_condition.type.boolean.HasField("value"))
        self.assertFalse(equal_condition.type.boolean.value)
        self.assertTrue(less_than_condition.type.boolean.HasField("value"))
        self.assertTrue(less_than_condition.type.boolean.value)

    def test_constant_less_than_or_equal(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  if 5 <= 4:\n"
            "    0 [+1]  UInt  x\n"
            "  if 5 <= 5:\n"
            "    0 [+1]  UInt  y\n"
            "  if 5 <= 6:\n"
            "    0 [+1]  UInt  z\n"
        )
        self.assertEqual([], expression_bounds.compute_constants(ir))
        structure = ir.module[0].type[0].structure
        greater_than_condition = structure.field[0].existence_condition
        equal_condition = structure.field[1].existence_condition
        less_than_condition = structure.field[2].existence_condition
        self.assertTrue(greater_than_condition.type.boolean.HasField("value"))
        self.assertFalse(greater_than_condition.type.boolean.value)
        self.assertTrue(equal_condition.type.boolean.HasField("value"))
        self.assertTrue(equal_condition.type.boolean.value)
        self.assertTrue(less_than_condition.type.boolean.HasField("value"))
        self.assertTrue(less_than_condition.type.boolean.value)

    def test_constant_greater_than(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  if 5 > 4:\n"
            "    0 [+1]  UInt  x\n"
            "  if 5 > 5:\n"
            "    0 [+1]  UInt  y\n"
            "  if 5 > 6:\n"
            "    0 [+1]  UInt  z\n"
        )
        self.assertEqual([], expression_bounds.compute_constants(ir))
        structure = ir.module[0].type[0].structure
        greater_than_condition = structure.field[0].existence_condition
        equal_condition = structure.field[1].existence_condition
        less_than_condition = structure.field[2].existence_condition
        self.assertTrue(greater_than_condition.type.boolean.HasField("value"))
        self.assertTrue(greater_than_condition.type.boolean.value)
        self.assertTrue(equal_condition.type.boolean.HasField("value"))
        self.assertFalse(equal_condition.type.boolean.value)
        self.assertTrue(less_than_condition.type.boolean.HasField("value"))
        self.assertFalse(less_than_condition.type.boolean.value)

    def test_constant_greater_than_or_equal(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  if 5 >= 4:\n"
            "    0 [+1]  UInt  x\n"
            "  if 5 >= 5:\n"
            "    0 [+1]  UInt  y\n"
            "  if 5 >= 6:\n"
            "    0 [+1]  UInt  z\n"
        )
        self.assertEqual([], expression_bounds.compute_constants(ir))
        structure = ir.module[0].type[0].structure
        greater_than_condition = structure.field[0].existence_condition
        equal_condition = structure.field[1].existence_condition
        less_than_condition = structure.field[2].existence_condition
        self.assertTrue(greater_than_condition.type.boolean.HasField("value"))
        self.assertTrue(greater_than_condition.type.boolean.value)
        self.assertTrue(equal_condition.type.boolean.HasField("value"))
        self.assertTrue(equal_condition.type.boolean.value)
        self.assertTrue(less_than_condition.type.boolean.HasField("value"))
        self.assertFalse(less_than_condition.type.boolean.value)

    def test_constant_and(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  if false && false:\n"
            "    0 [+1]  UInt  x\n"
            "  if true && false:\n"
            "    0 [+1]  UInt  y\n"
            "  if false && true:\n"
            "    0 [+1]  UInt  z\n"
            "  if true && true:\n"
            "    0 [+1]  UInt  w\n"
        )
        self.assertEqual([], expression_bounds.compute_constants(ir))
        structure = ir.module[0].type[0].structure
        false_false_condition = structure.field[0].existence_condition
        true_false_condition = structure.field[1].existence_condition
        false_true_condition = structure.field[2].existence_condition
        true_true_condition = structure.field[3].existence_condition
        self.assertTrue(false_false_condition.type.boolean.HasField("value"))
        self.assertFalse(false_false_condition.type.boolean.value)
        self.assertTrue(true_false_condition.type.boolean.HasField("value"))
        self.assertFalse(true_false_condition.type.boolean.value)
        self.assertTrue(false_true_condition.type.boolean.HasField("value"))
        self.assertFalse(false_true_condition.type.boolean.value)
        self.assertTrue(true_true_condition.type.boolean.HasField("value"))
        self.assertTrue(true_true_condition.type.boolean.value)

    def test_constant_or(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  if false || false:\n"
            "    0 [+1]  UInt  x\n"
            "  if true || false:\n"
            "    0 [+1]  UInt  y\n"
            "  if false || true:\n"
            "    0 [+1]  UInt  z\n"
            "  if true || true:\n"
            "    0 [+1]  UInt  w\n"
        )
        self.assertEqual([], expression_bounds.compute_constants(ir))
        structure = ir.module[0].type[0].structure
        false_false_condition = structure.field[0].existence_condition
        true_false_condition = structure.field[1].existence_condition
        false_true_condition = structure.field[2].existence_condition
        true_true_condition = structure.field[3].existence_condition
        self.assertTrue(false_false_condition.type.boolean.HasField("value"))
        self.assertFalse(false_false_condition.type.boolean.value)
        self.assertTrue(true_false_condition.type.boolean.HasField("value"))
        self.assertTrue(true_false_condition.type.boolean.value)
        self.assertTrue(false_true_condition.type.boolean.HasField("value"))
        self.assertTrue(false_true_condition.type.boolean.value)
        self.assertTrue(true_true_condition.type.boolean.HasField("value"))
        self.assertTrue(true_true_condition.type.boolean.value)

    def test_enum_constant(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  if Bar.QUX == Bar.QUX:\n"
            "    0 [+1]  Bar  x\n"
            "enum Bar:\n"
            "  QUX = 12\n"
        )
        self.assertEqual([], expression_bounds.compute_constants(ir))
        condition = ir.module[0].type[0].structure.field[0].existence_condition
        left = condition.function.args[0]
        self.assertEqual("12", left.type.enumeration.value)

    def test_non_constant_field_reference(self):
        ir = self._make_ir("struct Foo:\n" "  y [+1]  UInt  x\n" "  0 [+1]  UInt  y\n")
        self.assertEqual([], expression_bounds.compute_constants(ir))
        start = ir.module[0].type[0].structure.field[0].location.start
        self.assertEqual("0", start.type.integer.minimum_value)
        self.assertEqual("255", start.type.integer.maximum_value)
        self.assertEqual("0", start.type.integer.modular_value)
        self.assertEqual("1", start.type.integer.modulus)

    def test_field_reference_bounds_are_uncomputable(self):
        # Variable-sized UInt/Int/Bcd should not cause an error here: they are
        # handled in the constraints pass.
        ir = self._make_ir(
            "struct Foo:\n"
            "  0 [+1]  UInt  x\n"
            "  0 [+x]  UInt  y\n"
            "  y [+1]  UInt  z\n"
        )
        self.assertEqual([], expression_bounds.compute_constants(ir))

    def test_field_references_references_bounds_are_uncomputable(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  0 [+1]  UInt  x\n"
            "  0 [+x]  UInt  y\n"
            "  0 [+y]  UInt  z\n"
            "  z [+1]  UInt  q\n"
        )
        self.assertEqual([], expression_bounds.compute_constants(ir))

    def test_non_constant_equality(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  if 5 == y:\n"
            "    0 [+1]  UInt  x\n"
            "  0 [+1]  UInt  y\n"
        )
        self.assertEqual([], expression_bounds.compute_constants(ir))
        structure = ir.module[0].type[0].structure
        condition = structure.field[0].existence_condition
        self.assertFalse(condition.type.boolean.HasField("value"))

    def test_constant_addition(self):
        ir = self._make_ir("struct Foo:\n" "  7+5 [+1]  UInt  x\n")
        self.assertEqual([], expression_bounds.compute_constants(ir))
        start = ir.module[0].type[0].structure.field[0].location.start
        self.assertEqual("12", start.type.integer.minimum_value)
        self.assertEqual("12", start.type.integer.maximum_value)
        self.assertEqual("12", start.type.integer.modular_value)
        self.assertEqual("infinity", start.type.integer.modulus)
        self.assertEqual("7", start.function.args[0].type.integer.minimum_value)
        self.assertEqual("7", start.function.args[0].type.integer.maximum_value)
        self.assertEqual("7", start.function.args[0].type.integer.modular_value)
        self.assertEqual("infinity", start.type.integer.modulus)
        self.assertEqual("5", start.function.args[1].type.integer.minimum_value)
        self.assertEqual("5", start.function.args[1].type.integer.maximum_value)
        self.assertEqual("5", start.function.args[1].type.integer.modular_value)
        self.assertEqual("infinity", start.type.integer.modulus)

    def test_constant_subtraction(self):
        ir = self._make_ir("struct Foo:\n" "  7-5 [+1]  UInt  x\n")
        self.assertEqual([], expression_bounds.compute_constants(ir))
        start = ir.module[0].type[0].structure.field[0].location.start
        self.assertEqual("2", start.type.integer.minimum_value)
        self.assertEqual("2", start.type.integer.maximum_value)
        self.assertEqual("2", start.type.integer.modular_value)
        self.assertEqual("infinity", start.type.integer.modulus)
        self.assertEqual("7", start.function.args[0].type.integer.minimum_value)
        self.assertEqual("7", start.function.args[0].type.integer.maximum_value)
        self.assertEqual("7", start.function.args[0].type.integer.modular_value)
        self.assertEqual("infinity", start.type.integer.modulus)
        self.assertEqual("5", start.function.args[1].type.integer.minimum_value)
        self.assertEqual("5", start.function.args[1].type.integer.maximum_value)
        self.assertEqual("5", start.function.args[1].type.integer.modular_value)
        self.assertEqual("infinity", start.type.integer.modulus)

    def test_constant_multiplication(self):
        ir = self._make_ir("struct Foo:\n" "  7*5 [+1]  UInt  x\n")
        self.assertEqual([], expression_bounds.compute_constants(ir))
        start = ir.module[0].type[0].structure.field[0].location.start
        self.assertEqual("35", start.type.integer.minimum_value)
        self.assertEqual("35", start.type.integer.maximum_value)
        self.assertEqual("35", start.type.integer.modular_value)
        self.assertEqual("infinity", start.type.integer.modulus)
        self.assertEqual("7", start.function.args[0].type.integer.minimum_value)
        self.assertEqual("7", start.function.args[0].type.integer.maximum_value)
        self.assertEqual("7", start.function.args[0].type.integer.modular_value)
        self.assertEqual("infinity", start.type.integer.modulus)
        self.assertEqual("5", start.function.args[1].type.integer.minimum_value)
        self.assertEqual("5", start.function.args[1].type.integer.maximum_value)
        self.assertEqual("5", start.function.args[1].type.integer.modular_value)
        self.assertEqual("infinity", start.type.integer.modulus)

    def test_nested_constant_expression(self):
        ir = self._make_ir(
            "struct Foo:\n" "  if 7*(3+1) == 28:\n" "    0 [+1]  UInt  x\n"
        )
        self.assertEqual([], expression_bounds.compute_constants(ir))
        condition = ir.module[0].type[0].structure.field[0].existence_condition
        self.assertTrue(condition.type.boolean.value)
        condition_left = condition.function.args[0]
        self.assertEqual("28", condition_left.type.integer.minimum_value)
        self.assertEqual("28", condition_left.type.integer.maximum_value)
        self.assertEqual("28", condition_left.type.integer.modular_value)
        self.assertEqual("infinity", condition_left.type.integer.modulus)
        condition_left_left = condition_left.function.args[0]
        self.assertEqual("7", condition_left_left.type.integer.minimum_value)
        self.assertEqual("7", condition_left_left.type.integer.maximum_value)
        self.assertEqual("7", condition_left_left.type.integer.modular_value)
        self.assertEqual("infinity", condition_left_left.type.integer.modulus)
        condition_left_right = condition_left.function.args[1]
        self.assertEqual("4", condition_left_right.type.integer.minimum_value)
        self.assertEqual("4", condition_left_right.type.integer.maximum_value)
        self.assertEqual("4", condition_left_right.type.integer.modular_value)
        self.assertEqual("infinity", condition_left_right.type.integer.modulus)
        condition_left_right_left = condition_left_right.function.args[0]
        self.assertEqual("3", condition_left_right_left.type.integer.minimum_value)
        self.assertEqual("3", condition_left_right_left.type.integer.maximum_value)
        self.assertEqual("3", condition_left_right_left.type.integer.modular_value)
        self.assertEqual("infinity", condition_left_right_left.type.integer.modulus)
        condition_left_right_right = condition_left_right.function.args[1]
        self.assertEqual("1", condition_left_right_right.type.integer.minimum_value)
        self.assertEqual("1", condition_left_right_right.type.integer.maximum_value)
        self.assertEqual("1", condition_left_right_right.type.integer.modular_value)
        self.assertEqual("infinity", condition_left_right_right.type.integer.modulus)

    def test_constant_plus_non_constant(self):
        ir = self._make_ir(
            "struct Foo:\n" "  0       [+1]  UInt  x\n" "  5+(4*x) [+1]  UInt  y\n"
        )
        self.assertEqual([], expression_bounds.compute_constants(ir))
        y_start = ir.module[0].type[0].structure.field[1].location.start
        self.assertEqual("4", y_start.type.integer.modulus)
        self.assertEqual("1", y_start.type.integer.modular_value)
        self.assertEqual("5", y_start.type.integer.minimum_value)
        self.assertEqual("1025", y_start.type.integer.maximum_value)

    def test_constant_minus_non_constant(self):
        ir = self._make_ir(
            "struct Foo:\n" "  0       [+1]  UInt  x\n" "  5-(4*x) [+1]  UInt  y\n"
        )
        self.assertEqual([], expression_bounds.compute_constants(ir))
        y_start = ir.module[0].type[0].structure.field[1].location.start
        self.assertEqual("4", y_start.type.integer.modulus)
        self.assertEqual("1", y_start.type.integer.modular_value)
        self.assertEqual("-1015", y_start.type.integer.minimum_value)
        self.assertEqual("5", y_start.type.integer.maximum_value)

    def test_non_constant_minus_constant(self):
        ir = self._make_ir(
            "struct Foo:\n" "  0       [+1]  UInt  x\n" "  (4*x)-5 [+1]  UInt  y\n"
        )
        self.assertEqual([], expression_bounds.compute_constants(ir))
        y_start = ir.module[0].type[0].structure.field[1].location.start
        self.assertEqual(str((4 * 0) - 5), y_start.type.integer.minimum_value)
        self.assertEqual(str((4 * 255) - 5), y_start.type.integer.maximum_value)
        self.assertEqual("4", y_start.type.integer.modulus)
        self.assertEqual("3", y_start.type.integer.modular_value)

    def test_non_constant_plus_non_constant(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  0             [+1]  UInt  x\n"
            "  1             [+1]  UInt  y\n"
            "  (4*x)+(6*y+3) [+1]  UInt  z\n"
        )
        self.assertEqual([], expression_bounds.compute_constants(ir))
        z_start = ir.module[0].type[0].structure.field[2].location.start
        self.assertEqual("3", z_start.type.integer.minimum_value)
        self.assertEqual(str(4 * 255 + 6 * 255 + 3), z_start.type.integer.maximum_value)
        self.assertEqual("2", z_start.type.integer.modulus)
        self.assertEqual("1", z_start.type.integer.modular_value)

    def test_non_constant_minus_non_constant(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  0            [+1]  UInt  x\n"
            "  1            [+1]  UInt  y\n"
            "  (x*3)-(y*3)  [+1]  UInt  z\n"
        )
        self.assertEqual([], expression_bounds.compute_constants(ir))
        z_start = ir.module[0].type[0].structure.field[2].location.start
        self.assertEqual("3", z_start.type.integer.modulus)
        self.assertEqual("0", z_start.type.integer.modular_value)
        self.assertEqual(str(-3 * 255), z_start.type.integer.minimum_value)
        self.assertEqual(str(3 * 255), z_start.type.integer.maximum_value)

    def test_non_constant_times_constant(self):
        ir = self._make_ir(
            "struct Foo:\n" "  0         [+1]  UInt  x\n" "  (4*x+1)*5 [+1]  UInt  y\n"
        )
        self.assertEqual([], expression_bounds.compute_constants(ir))
        y_start = ir.module[0].type[0].structure.field[1].location.start
        self.assertEqual("20", y_start.type.integer.modulus)
        self.assertEqual("5", y_start.type.integer.modular_value)
        self.assertEqual("5", y_start.type.integer.minimum_value)
        self.assertEqual(str((4 * 255 + 1) * 5), y_start.type.integer.maximum_value)

    def test_non_constant_times_negative_constant(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  0          [+1]  UInt  x\n"
            "  (4*x+1)*-5 [+1]  UInt  y\n"
        )
        self.assertEqual([], expression_bounds.compute_constants(ir))
        y_start = ir.module[0].type[0].structure.field[1].location.start
        self.assertEqual("20", y_start.type.integer.modulus)
        self.assertEqual("15", y_start.type.integer.modular_value)
        self.assertEqual(str((4 * 255 + 1) * -5), y_start.type.integer.minimum_value)
        self.assertEqual("-5", y_start.type.integer.maximum_value)

    def test_non_constant_times_zero(self):
        ir = self._make_ir(
            "struct Foo:\n" "  0         [+1]  UInt  x\n" "  (4*x+1)*0 [+1]  UInt  y\n"
        )
        self.assertEqual([], expression_bounds.compute_constants(ir))
        y_start = ir.module[0].type[0].structure.field[1].location.start
        self.assertEqual("infinity", y_start.type.integer.modulus)
        self.assertEqual("0", y_start.type.integer.modular_value)
        self.assertEqual("0", y_start.type.integer.minimum_value)
        self.assertEqual("0", y_start.type.integer.maximum_value)

    def test_non_constant_times_non_constant_shared_modulus(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  0               [+1]  UInt  x\n"
            "  1               [+1]  UInt  y\n"
            "  (4*x+3)*(4*y+3) [+1]  UInt  z\n"
        )
        self.assertEqual([], expression_bounds.compute_constants(ir))
        z_start = ir.module[0].type[0].structure.field[2].location.start
        self.assertEqual("4", z_start.type.integer.modulus)
        self.assertEqual("1", z_start.type.integer.modular_value)
        self.assertEqual("9", z_start.type.integer.minimum_value)
        self.assertEqual(str((4 * 255 + 3) ** 2), z_start.type.integer.maximum_value)

    def test_non_constant_times_non_constant_congruent_to_zero(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  0           [+1]  UInt  x\n"
            "  1           [+1]  UInt  y\n"
            "  (4*x)*(4*y) [+1]  UInt  z\n"
        )
        self.assertEqual([], expression_bounds.compute_constants(ir))
        z_start = ir.module[0].type[0].structure.field[2].location.start
        self.assertEqual("16", z_start.type.integer.modulus)
        self.assertEqual("0", z_start.type.integer.modular_value)
        self.assertEqual("0", z_start.type.integer.minimum_value)
        self.assertEqual(str((4 * 255) ** 2), z_start.type.integer.maximum_value)

    def test_non_constant_times_non_constant_partially_shared_modulus(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  0               [+1]  UInt  x\n"
            "  1               [+1]  UInt  y\n"
            "  (4*x+3)*(8*y+3) [+1]  UInt  z\n"
        )
        self.assertEqual([], expression_bounds.compute_constants(ir))
        z_start = ir.module[0].type[0].structure.field[2].location.start
        self.assertEqual("4", z_start.type.integer.modulus)
        self.assertEqual("1", z_start.type.integer.modular_value)
        self.assertEqual("9", z_start.type.integer.minimum_value)
        self.assertEqual(
            str((4 * 255 + 3) * (8 * 255 + 3)), z_start.type.integer.maximum_value
        )

    def test_non_constant_times_non_constant_full_complexity(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  0                  [+1]  UInt  x\n"
            "  1                  [+1]  UInt  y\n"
            "  (12*x+9)*(40*y+15) [+1]  UInt  z\n"
        )
        self.assertEqual([], expression_bounds.compute_constants(ir))
        z_start = ir.module[0].type[0].structure.field[2].location.start
        self.assertEqual("60", z_start.type.integer.modulus)
        self.assertEqual("15", z_start.type.integer.modular_value)
        self.assertEqual(str(9 * 15), z_start.type.integer.minimum_value)
        self.assertEqual(
            str((12 * 255 + 9) * (40 * 255 + 15)), z_start.type.integer.maximum_value
        )

    def test_signed_non_constant_times_signed_non_constant_full_complexity(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  0                  [+1]  Int  x\n"
            "  1                  [+1]  Int  y\n"
            "  (12*x+9)*(40*y+15) [+1]  Int  z\n"
        )
        self.assertEqual([], expression_bounds.compute_constants(ir))
        z_start = ir.module[0].type[0].structure.field[2].location.start
        self.assertEqual("60", z_start.type.integer.modulus)
        self.assertEqual("15", z_start.type.integer.modular_value)
        # Max x/min y is slightly lower than min x/max y (-7825965 vs -7780065).
        self.assertEqual(
            str((12 * 127 + 9) * (40 * -128 + 15)), z_start.type.integer.minimum_value
        )
        # Max x/max y is slightly higher than min x/min y (7810635 vs 7795335).
        self.assertEqual(
            str((12 * 127 + 9) * (40 * 127 + 15)), z_start.type.integer.maximum_value
        )

    def test_non_constant_times_non_constant_flipped_min_max(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  0             [+1]  UInt  x\n"
            "  1             [+1]  UInt  y\n"
            "  (-x*3)*(y*3)  [+1]  UInt  z\n"
        )
        self.assertEqual([], expression_bounds.compute_constants(ir))
        z_start = ir.module[0].type[0].structure.field[2].location.start
        self.assertEqual("9", z_start.type.integer.modulus)
        self.assertEqual("0", z_start.type.integer.modular_value)
        self.assertEqual(str(-((3 * 255) ** 2)), z_start.type.integer.minimum_value)
        self.assertEqual("0", z_start.type.integer.maximum_value)

    # Currently, only `$static_size_in_bits` has an infinite bound, so all of the
    # examples below use `$static_size_in_bits`.  Unfortunately, this also means
    # that these tests rely on the fact that Emboss doesn't try to do any term
    # rewriting or smart correlation between the arguments of various operators:
    # for example, several tests rely on `$static_size_in_bits -
    # $static_size_in_bits` having the range `-infinity` to `infinity`, when a
    # trivial term rewrite would turn that expression into `0`.
    #
    # Unbounded expressions are only allowed at compile-time anyway, so these
    # tests cover some fairly unlikely uses of the Emboss expression language.
    def test_unbounded_plus_constant(self):
        ir = self._make_ir(
            "external Foo:\n" "  [requires: $static_size_in_bits + 2 > 0]\n"
        )
        self.assertEqual([], expression_bounds.compute_constants(ir))
        expr = ir.module[0].type[0].attribute[0].value.expression.function.args[0]
        self.assertEqual("1", expr.type.integer.modulus)
        self.assertEqual("0", expr.type.integer.modular_value)
        self.assertEqual("2", expr.type.integer.minimum_value)
        self.assertEqual("infinity", expr.type.integer.maximum_value)

    def test_negative_unbounded_plus_constant(self):
        ir = self._make_ir(
            "external Foo:\n" "  [requires: -$static_size_in_bits + 2 > 0]\n"
        )
        self.assertEqual([], expression_bounds.compute_constants(ir))
        expr = ir.module[0].type[0].attribute[0].value.expression.function.args[0]
        self.assertEqual("1", expr.type.integer.modulus)
        self.assertEqual("0", expr.type.integer.modular_value)
        self.assertEqual("-infinity", expr.type.integer.minimum_value)
        self.assertEqual("2", expr.type.integer.maximum_value)

    def test_negative_unbounded_plus_unbounded(self):
        ir = self._make_ir(
            "external Foo:\n"
            "  [requires: -$static_size_in_bits + $static_size_in_bits > 0]\n"
        )
        self.assertEqual([], expression_bounds.compute_constants(ir))
        expr = ir.module[0].type[0].attribute[0].value.expression.function.args[0]
        self.assertEqual("1", expr.type.integer.modulus)
        self.assertEqual("0", expr.type.integer.modular_value)
        self.assertEqual("-infinity", expr.type.integer.minimum_value)
        self.assertEqual("infinity", expr.type.integer.maximum_value)

    def test_unbounded_minus_unbounded(self):
        ir = self._make_ir(
            "external Foo:\n"
            "  [requires: $static_size_in_bits - $static_size_in_bits > 0]\n"
        )
        self.assertEqual([], expression_bounds.compute_constants(ir))
        expr = ir.module[0].type[0].attribute[0].value.expression.function.args[0]
        self.assertEqual("1", expr.type.integer.modulus)
        self.assertEqual("0", expr.type.integer.modular_value)
        self.assertEqual("-infinity", expr.type.integer.minimum_value)
        self.assertEqual("infinity", expr.type.integer.maximum_value)

    def test_unbounded_minus_negative_unbounded(self):
        ir = self._make_ir(
            "external Foo:\n"
            "  [requires: $static_size_in_bits - -$static_size_in_bits > 0]\n"
        )
        self.assertEqual([], expression_bounds.compute_constants(ir))
        expr = ir.module[0].type[0].attribute[0].value.expression.function.args[0]
        self.assertEqual("1", expr.type.integer.modulus)
        self.assertEqual("0", expr.type.integer.modular_value)
        self.assertEqual("0", expr.type.integer.minimum_value)
        self.assertEqual("infinity", expr.type.integer.maximum_value)

    def test_unbounded_times_constant(self):
        ir = self._make_ir(
            "external Foo:\n" "  [requires: ($static_size_in_bits + 1) * 2 > 0]\n"
        )
        self.assertEqual([], expression_bounds.compute_constants(ir))
        expr = ir.module[0].type[0].attribute[0].value.expression.function.args[0]
        self.assertEqual("2", expr.type.integer.modulus)
        self.assertEqual("0", expr.type.integer.modular_value)
        self.assertEqual("2", expr.type.integer.minimum_value)
        self.assertEqual("infinity", expr.type.integer.maximum_value)

    def test_unbounded_times_negative_constant(self):
        ir = self._make_ir(
            "external Foo:\n" "  [requires: ($static_size_in_bits + 1) * -2 > 0]\n"
        )
        self.assertEqual([], expression_bounds.compute_constants(ir))
        expr = ir.module[0].type[0].attribute[0].value.expression.function.args[0]
        self.assertEqual("2", expr.type.integer.modulus)
        self.assertEqual("0", expr.type.integer.modular_value)
        self.assertEqual("-infinity", expr.type.integer.minimum_value)
        self.assertEqual("-2", expr.type.integer.maximum_value)

    def test_unbounded_times_negative_zero(self):
        ir = self._make_ir(
            "external Foo:\n" "  [requires: ($static_size_in_bits + 1) * 0 > 0]\n"
        )
        self.assertEqual([], expression_bounds.compute_constants(ir))
        expr = ir.module[0].type[0].attribute[0].value.expression.function.args[0]
        self.assertEqual("infinity", expr.type.integer.modulus)
        self.assertEqual("0", expr.type.integer.modular_value)
        self.assertEqual("0", expr.type.integer.minimum_value)
        self.assertEqual("0", expr.type.integer.maximum_value)

    def test_negative_unbounded_times_constant(self):
        ir = self._make_ir(
            "external Foo:\n" "  [requires: (-$static_size_in_bits + 1) * 2 > 0]\n"
        )
        self.assertEqual([], expression_bounds.compute_constants(ir))
        expr = ir.module[0].type[0].attribute[0].value.expression.function.args[0]
        self.assertEqual("2", expr.type.integer.modulus)
        self.assertEqual("0", expr.type.integer.modular_value)
        self.assertEqual("-infinity", expr.type.integer.minimum_value)
        self.assertEqual("2", expr.type.integer.maximum_value)

    def test_double_unbounded_minus_unbounded(self):
        ir = self._make_ir(
            "external Foo:\n"
            "  [requires: 2 * $static_size_in_bits - $static_size_in_bits > 0]\n"
        )
        self.assertEqual([], expression_bounds.compute_constants(ir))
        expr = ir.module[0].type[0].attribute[0].value.expression.function.args[0]
        self.assertEqual("1", expr.type.integer.modulus)
        self.assertEqual("0", expr.type.integer.modular_value)
        self.assertEqual("-infinity", expr.type.integer.minimum_value)
        self.assertEqual("infinity", expr.type.integer.maximum_value)

    def test_double_unbounded_times_negative_unbounded(self):
        ir = self._make_ir(
            "external Foo:\n"
            "  [requires: 2 * $static_size_in_bits * -$static_size_in_bits > 0]\n"
        )
        self.assertEqual([], expression_bounds.compute_constants(ir))
        expr = ir.module[0].type[0].attribute[0].value.expression.function.args[0]
        self.assertEqual("2", expr.type.integer.modulus)
        self.assertEqual("0", expr.type.integer.modular_value)
        self.assertEqual("-infinity", expr.type.integer.minimum_value)
        self.assertEqual("0", expr.type.integer.maximum_value)

    def test_upper_bound_of_field(self):
        ir = self._make_ir(
            "struct Foo:\n" "  0 [+1]  Int  x\n" "  let u = $upper_bound(x)\n"
        )
        self.assertEqual([], expression_bounds.compute_constants(ir))
        u_type = ir.module[0].type[0].structure.field[1].read_transform.type
        self.assertEqual("infinity", u_type.integer.modulus)
        self.assertEqual("127", u_type.integer.maximum_value)
        self.assertEqual("127", u_type.integer.minimum_value)
        self.assertEqual("127", u_type.integer.modular_value)

    def test_lower_bound_of_field(self):
        ir = self._make_ir(
            "struct Foo:\n" "  0 [+1]  Int  x\n" "  let l = $lower_bound(x)\n"
        )
        self.assertEqual([], expression_bounds.compute_constants(ir))
        l_type = ir.module[0].type[0].structure.field[1].read_transform.type
        self.assertEqual("infinity", l_type.integer.modulus)
        self.assertEqual("-128", l_type.integer.maximum_value)
        self.assertEqual("-128", l_type.integer.minimum_value)
        self.assertEqual("-128", l_type.integer.modular_value)

    def test_upper_bound_of_max(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  0 [+1]  Int   x\n"
            "  1 [+1]  UInt  y\n"
            "  let u = $upper_bound($max(x, y))\n"
        )
        self.assertEqual([], expression_bounds.compute_constants(ir))
        u_type = ir.module[0].type[0].structure.field[2].read_transform.type
        self.assertEqual("infinity", u_type.integer.modulus)
        self.assertEqual("255", u_type.integer.maximum_value)
        self.assertEqual("255", u_type.integer.minimum_value)
        self.assertEqual("255", u_type.integer.modular_value)

    def test_lower_bound_of_max(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  0 [+1]  Int  x\n"
            "  1 [+1]  UInt  y\n"
            "  let l = $lower_bound($max(x, y))\n"
        )
        self.assertEqual([], expression_bounds.compute_constants(ir))
        l_type = ir.module[0].type[0].structure.field[2].read_transform.type
        self.assertEqual("infinity", l_type.integer.modulus)
        self.assertEqual("0", l_type.integer.maximum_value)
        self.assertEqual("0", l_type.integer.minimum_value)
        self.assertEqual("0", l_type.integer.modular_value)

    def test_double_unbounded_both_ends_times_negative_unbounded(self):
        ir = self._make_ir(
            "external Foo:\n"
            "  [requires: (2 * ($static_size_in_bits - $static_size_in_bits) + 1) "
            "             * -$static_size_in_bits > 0]\n"
        )
        self.assertEqual([], expression_bounds.compute_constants(ir))
        expr = ir.module[0].type[0].attribute[0].value.expression.function.args[0]
        self.assertEqual("1", expr.type.integer.modulus)
        self.assertEqual("0", expr.type.integer.modular_value)
        self.assertEqual("-infinity", expr.type.integer.minimum_value)
        self.assertEqual("infinity", expr.type.integer.maximum_value)

    def test_choice_two_non_constant_integers(self):
        cases = [
            # t % 12 == 7 and f % 20 == 15 ==> r % 4 == 3
            (12, 7, 20, 15, 4, 3, -128 * 20 + 15, 127 * 20 + 15),
            # t % 24 == 15 and f % 12 == 7 ==> r % 4 == 3
            (24, 15, 12, 7, 4, 3, -128 * 24 + 15, 127 * 24 + 15),
            # t % 20 == 15 and f % 20 == 10 ==> r % 5 == 0
            (20, 15, 20, 10, 5, 0, -128 * 20 + 10, 127 * 20 + 15),
            # t % 20 == 16 and f % 20 == 11 ==> r % 5 == 1
            (20, 16, 20, 11, 5, 1, -128 * 20 + 11, 127 * 20 + 16),
        ]
        for t_mod, t_val, f_mod, f_val, r_mod, r_val, r_min, r_max in cases:
            ir = self._make_ir(
                "struct Foo:\n"
                "  0 [+1]    UInt  x\n"
                "  1 [+1]    Int   y\n"
                "  if (x == 0 ? y * {} + {} : y * {} + {}) == 0:\n"
                "    1 [+1]  UInt  z\n".format(t_mod, t_val, f_mod, f_val)
            )
            self.assertEqual([], expression_bounds.compute_constants(ir))
            field = ir.module[0].type[0].structure.field[2]
            expr = field.existence_condition.function.args[0]
            self.assertEqual(str(r_mod), expr.type.integer.modulus)
            self.assertEqual(str(r_val), expr.type.integer.modular_value)
            self.assertEqual(str(r_min), expr.type.integer.minimum_value)
            self.assertEqual(str(r_max), expr.type.integer.maximum_value)

    def test_choice_one_non_constant_integer(self):
        cases = [
            # t == 35 and f % 20 == 15 ==> res % 20 == 15
            (35, 20, 15, 20, 15, -128 * 20 + 15, 127 * 20 + 15),
            # t == 200035 and f % 20 == 15 ==> res % 20 == 15
            (200035, 20, 15, 20, 15, -128 * 20 + 15, 200035),
            # t == 21 and f % 20 == 16 ==> res % 5 == 1
            (21, 20, 16, 5, 1, -128 * 20 + 16, 127 * 20 + 16),
        ]
        for t_val, f_mod, f_val, r_mod, r_val, r_min, r_max in cases:
            ir = self._make_ir(
                "struct Foo:\n"
                "  0 [+1]    UInt  x\n"
                "  1 [+1]    Int   y\n"
                "  if (x == 0 ? {0} : y * {1} + {2}) == 0:\n"
                "    1 [+1]  UInt  z\n"
                "  if (x == 0 ? y * {1} + {2} : {0}) == 0:\n"
                "    1 [+1]  UInt  q\n".format(t_val, f_mod, f_val)
            )
            self.assertEqual([], expression_bounds.compute_constants(ir))
            field_constant_true = ir.module[0].type[0].structure.field[2]
            constant_true = field_constant_true.existence_condition.function.args[0]
            field_constant_false = ir.module[0].type[0].structure.field[3]
            constant_false = field_constant_false.existence_condition.function.args[0]
            self.assertEqual(str(r_mod), constant_true.type.integer.modulus)
            self.assertEqual(str(r_val), constant_true.type.integer.modular_value)
            self.assertEqual(str(r_min), constant_true.type.integer.minimum_value)
            self.assertEqual(str(r_max), constant_true.type.integer.maximum_value)
            self.assertEqual(str(r_mod), constant_false.type.integer.modulus)
            self.assertEqual(str(r_val), constant_false.type.integer.modular_value)
            self.assertEqual(str(r_min), constant_false.type.integer.minimum_value)
            self.assertEqual(str(r_max), constant_false.type.integer.maximum_value)

    def test_choice_two_constant_integers(self):
        cases = [
            # t == 10 and f == 7 ==> res % 3 == 1
            (10, 7, 3, 1, 7, 10),
            # t == 4 and f == 4 ==> res == 4
            (4, 4, "infinity", 4, 4, 4),
        ]
        for t_val, f_val, r_mod, r_val, r_min, r_max in cases:
            ir = self._make_ir(
                "struct Foo:\n"
                "  0 [+1]    UInt  x\n"
                "  1 [+1]    Int   y\n"
                "  if (x == 0 ? {} : {}) == 0:\n"
                "    1 [+1]  UInt  z\n".format(t_val, f_val)
            )
            self.assertEqual([], expression_bounds.compute_constants(ir))
            field_constant_true = ir.module[0].type[0].structure.field[2]
            constant_true = field_constant_true.existence_condition.function.args[0]
            self.assertEqual(str(r_mod), constant_true.type.integer.modulus)
            self.assertEqual(str(r_val), constant_true.type.integer.modular_value)
            self.assertEqual(str(r_min), constant_true.type.integer.minimum_value)
            self.assertEqual(str(r_max), constant_true.type.integer.maximum_value)

    def test_constant_true_has(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  if $present(x):\n"
            "    1 [+1]  UInt  q\n"
            "  0 [+1]    UInt  x\n"
            "  if x > 10:\n"
            "    1 [+1]  Int   y\n"
            "  if false:\n"
            "    2 [+1]  Int   z\n"
        )
        self.assertEqual([], expression_bounds.compute_constants(ir))
        field = ir.module[0].type[0].structure.field[0]
        has_func = field.existence_condition
        self.assertTrue(has_func.type.boolean.value)

    def test_constant_false_has(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  if $present(z):\n"
            "    1 [+1]  UInt  q\n"
            "  0 [+1]    UInt  x\n"
            "  if x > 10:\n"
            "    1 [+1]  Int   y\n"
            "  if false:\n"
            "    2 [+1]  Int   z\n"
        )
        self.assertEqual([], expression_bounds.compute_constants(ir))
        field = ir.module[0].type[0].structure.field[0]
        has_func = field.existence_condition
        self.assertTrue(has_func.type.boolean.HasField("value"))
        self.assertFalse(has_func.type.boolean.value)

    def test_variable_has(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  if $present(y):\n"
            "    1 [+1]  UInt  q\n"
            "  0 [+1]    UInt  x\n"
            "  if x > 10:\n"
            "    1 [+1]  Int   y\n"
            "  if false:\n"
            "    2 [+1]  Int   z\n"
        )
        self.assertEqual([], expression_bounds.compute_constants(ir))
        field = ir.module[0].type[0].structure.field[0]
        has_func = field.existence_condition
        self.assertFalse(has_func.type.boolean.HasField("value"))

    def test_max_of_constants(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  0 [+1]    UInt  x\n"
            "  1 [+1]    Int   y\n"
            "  if $max(0, 1, 2) == 0:\n"
            "    1 [+1]  UInt  z\n"
        )
        self.assertEqual([], expression_bounds.compute_constants(ir))
        field = ir.module[0].type[0].structure.field[2]
        max_func = field.existence_condition.function.args[0]
        self.assertEqual("infinity", max_func.type.integer.modulus)
        self.assertEqual("2", max_func.type.integer.modular_value)
        self.assertEqual("2", max_func.type.integer.minimum_value)
        self.assertEqual("2", max_func.type.integer.maximum_value)

    def test_max_dominated_by_constant(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  0 [+1]    UInt  x\n"
            "  1 [+1]    Int   y\n"
            "  if $max(x, y, 255) == 0:\n"
            "    1 [+1]  UInt  z\n"
        )
        self.assertEqual([], expression_bounds.compute_constants(ir))
        field = ir.module[0].type[0].structure.field[2]
        max_func = field.existence_condition.function.args[0]
        self.assertEqual("infinity", max_func.type.integer.modulus)
        self.assertEqual("255", max_func.type.integer.modular_value)
        self.assertEqual("255", max_func.type.integer.minimum_value)
        self.assertEqual("255", max_func.type.integer.maximum_value)

    def test_max_of_variables(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  0 [+1]    UInt  x\n"
            "  1 [+1]    Int   y\n"
            "  if $max(x, y) == 0:\n"
            "    1 [+1]  UInt  z\n"
        )
        self.assertEqual([], expression_bounds.compute_constants(ir))
        field = ir.module[0].type[0].structure.field[2]
        max_func = field.existence_condition.function.args[0]
        self.assertEqual("1", max_func.type.integer.modulus)
        self.assertEqual("0", max_func.type.integer.modular_value)
        self.assertEqual("0", max_func.type.integer.minimum_value)
        self.assertEqual("255", max_func.type.integer.maximum_value)

    def test_max_of_variables_with_shared_modulus(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  0 [+1]    UInt  x\n"
            "  1 [+1]    Int   y\n"
            "  if $max(x * 8 + 5, y * 4 + 3) == 0:\n"
            "    1 [+1]  UInt  z\n"
        )
        self.assertEqual([], expression_bounds.compute_constants(ir))
        field = ir.module[0].type[0].structure.field[2]
        max_func = field.existence_condition.function.args[0]
        self.assertEqual("2", max_func.type.integer.modulus)
        self.assertEqual("1", max_func.type.integer.modular_value)
        self.assertEqual("5", max_func.type.integer.minimum_value)
        self.assertEqual("2045", max_func.type.integer.maximum_value)

    def test_max_of_three_variables(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  0 [+1]    UInt  x\n"
            "  1 [+1]    Int   y\n"
            "  2 [+2]    Int   z\n"
            "  if $max(x, y, z) == 0:\n"
            "    1 [+1]  UInt  q\n"
        )
        self.assertEqual([], expression_bounds.compute_constants(ir))
        field = ir.module[0].type[0].structure.field[3]
        max_func = field.existence_condition.function.args[0]
        self.assertEqual("1", max_func.type.integer.modulus)
        self.assertEqual("0", max_func.type.integer.modular_value)
        self.assertEqual("0", max_func.type.integer.minimum_value)
        self.assertEqual("32767", max_func.type.integer.maximum_value)

    def test_max_of_one_variable(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  0 [+1]    UInt  x\n"
            "  1 [+1]    Int   y\n"
            "  2 [+2]    Int   z\n"
            "  if $max(x * 2 + 3) == 0:\n"
            "    1 [+1]  UInt  q\n"
        )
        self.assertEqual([], expression_bounds.compute_constants(ir))
        field = ir.module[0].type[0].structure.field[3]
        max_func = field.existence_condition.function.args[0]
        self.assertEqual("2", max_func.type.integer.modulus)
        self.assertEqual("1", max_func.type.integer.modular_value)
        self.assertEqual("3", max_func.type.integer.minimum_value)
        self.assertEqual("513", max_func.type.integer.maximum_value)

    def test_max_of_one_variable_and_one_constant(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  0 [+1]    UInt  x\n"
            "  1 [+1]    Int   y\n"
            "  2 [+2]    Int   z\n"
            "  if $max(x * 2 + 3, 311) == 0:\n"
            "    1 [+1]  UInt  q\n"
        )
        self.assertEqual([], expression_bounds.compute_constants(ir))
        field = ir.module[0].type[0].structure.field[3]
        max_func = field.existence_condition.function.args[0]
        self.assertEqual("2", max_func.type.integer.modulus)
        self.assertEqual("1", max_func.type.integer.modular_value)
        self.assertEqual("311", max_func.type.integer.minimum_value)
        self.assertEqual("513", max_func.type.integer.maximum_value)

    def test_choice_non_integer_arguments(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  0 [+1]    UInt  x\n"
            "  if x == 0 ? false : true:\n"
            "    1 [+1]  UInt  y\n"
        )
        self.assertEqual([], expression_bounds.compute_constants(ir))
        expr = ir.module[0].type[0].structure.field[1].existence_condition
        self.assertEqual("boolean", expr.type.WhichOneof("type"))
        self.assertFalse(expr.type.boolean.HasField("value"))

    def test_uint_value_range_for_explicit_size(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  0 [+1]  UInt     x\n"
            "  1 [+x]  UInt:16  y\n"
            "  y [+1]  UInt     z\n"
        )
        self.assertEqual([], expression_bounds.compute_constants(ir))
        z_start = ir.module[0].type[0].structure.field[2].location.start
        self.assertEqual("1", z_start.type.integer.modulus)
        self.assertEqual("0", z_start.type.integer.modular_value)
        self.assertEqual("0", z_start.type.integer.minimum_value)
        self.assertEqual("65535", z_start.type.integer.maximum_value)

    def test_uint_value_ranges(self):
        cases = [
            (1, 1),
            (2, 3),
            (3, 7),
            (4, 15),
            (8, 255),
            (12, 4095),
            (15, 32767),
            (16, 65535),
            (32, 4294967295),
            (48, 281474976710655),
            (64, 18446744073709551615),
        ]
        for bits, upper in cases:
            ir = self._make_ir(
                "struct Foo:\n"
                "  0   [+8]   bits:\n"
                "    0 [+{}]  UInt  x\n"
                "  x   [+1]   UInt  z\n".format(bits)
            )
            self.assertEqual([], expression_bounds.compute_constants(ir))
            z_start = ir.module[0].type[0].structure.field[2].location.start
            self.assertEqual("1", z_start.type.integer.modulus)
            self.assertEqual("0", z_start.type.integer.modular_value)
            self.assertEqual("0", z_start.type.integer.minimum_value)
            self.assertEqual(str(upper), z_start.type.integer.maximum_value)

    def test_int_value_ranges(self):
        cases = [
            (1, -1, 0),
            (2, -2, 1),
            (3, -4, 3),
            (4, -8, 7),
            (8, -128, 127),
            (12, -2048, 2047),
            (15, -16384, 16383),
            (16, -32768, 32767),
            (32, -2147483648, 2147483647),
            (48, -140737488355328, 140737488355327),
            (64, -9223372036854775808, 9223372036854775807),
        ]
        for bits, lower, upper in cases:
            ir = self._make_ir(
                "struct Foo:\n"
                "  0   [+8]   bits:\n"
                "    0 [+{}]  Int   x\n"
                "  x   [+1]   UInt  z\n".format(bits)
            )
            self.assertEqual([], expression_bounds.compute_constants(ir))
            z_start = ir.module[0].type[0].structure.field[2].location.start
            self.assertEqual("1", z_start.type.integer.modulus)
            self.assertEqual("0", z_start.type.integer.modular_value)
            self.assertEqual(str(lower), z_start.type.integer.minimum_value)
            self.assertEqual(str(upper), z_start.type.integer.maximum_value)

    def test_bcd_value_ranges(self):
        cases = [
            (1, 1),
            (2, 3),
            (3, 7),
            (4, 9),
            (8, 99),
            (12, 999),
            (15, 7999),
            (16, 9999),
            (32, 99999999),
            (48, 999999999999),
            (64, 9999999999999999),
        ]
        for bits, upper in cases:
            ir = self._make_ir(
                "struct Foo:\n"
                "  0   [+8]   bits:\n"
                "    0 [+{}]  Bcd   x\n"
                "  x   [+1]   UInt  z\n".format(bits)
            )
            self.assertEqual([], expression_bounds.compute_constants(ir))
            z_start = ir.module[0].type[0].structure.field[2].location.start
            self.assertEqual("1", z_start.type.integer.modulus)
            self.assertEqual("0", z_start.type.integer.modular_value)
            self.assertEqual("0", z_start.type.integer.minimum_value)
            self.assertEqual(str(upper), z_start.type.integer.maximum_value)

    def test_virtual_field_bounds(self):
        ir = self._make_ir(
            "struct Foo:\n" "  0 [+1]  UInt     x\n" "  let y = x + 10\n"
        )
        self.assertEqual([], expression_bounds.compute_constants(ir))
        field_y = ir.module[0].type[0].structure.field[1]
        self.assertEqual("1", field_y.read_transform.type.integer.modulus)
        self.assertEqual("0", field_y.read_transform.type.integer.modular_value)
        self.assertEqual("10", field_y.read_transform.type.integer.minimum_value)
        self.assertEqual("265", field_y.read_transform.type.integer.maximum_value)

    def test_virtual_field_bounds_copied(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  let z = y + 100\n"
            "  let y = x + 10\n"
            "  0 [+1]  UInt     x\n"
        )
        self.assertEqual([], expression_bounds.compute_constants(ir))
        field_z = ir.module[0].type[0].structure.field[0]
        self.assertEqual("1", field_z.read_transform.type.integer.modulus)
        self.assertEqual("0", field_z.read_transform.type.integer.modular_value)
        self.assertEqual("110", field_z.read_transform.type.integer.minimum_value)
        self.assertEqual("365", field_z.read_transform.type.integer.maximum_value)
        y_reference = field_z.read_transform.function.args[0]
        self.assertEqual("1", y_reference.type.integer.modulus)
        self.assertEqual("0", y_reference.type.integer.modular_value)
        self.assertEqual("10", y_reference.type.integer.minimum_value)
        self.assertEqual("265", y_reference.type.integer.maximum_value)

    def test_constant_reference_to_virtual_bounds_copied(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  let ten = Bar.ten\n"
            "  let truth = Bar.truth\n"
            "struct Bar:\n"
            "  let ten = 10\n"
            "  let truth = true\n"
        )
        self.assertEqual([], expression_bounds.compute_constants(ir))
        field_ten = ir.module[0].type[0].structure.field[0]
        self.assertEqual("infinity", field_ten.read_transform.type.integer.modulus)
        self.assertEqual("10", field_ten.read_transform.type.integer.modular_value)
        self.assertEqual("10", field_ten.read_transform.type.integer.minimum_value)
        self.assertEqual("10", field_ten.read_transform.type.integer.maximum_value)
        field_truth = ir.module[0].type[0].structure.field[1]
        self.assertTrue(field_truth.read_transform.type.boolean.value)

    def test_forward_reference_to_reference_to_enum_correctly_calculated(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  let ten = Bar.TEN\n"
            "enum Bar:\n"
            "  TEN = TEN2\n"
            "  TEN2 = 5 + 5\n"
        )
        self.assertEqual([], expression_bounds.compute_constants(ir))
        field_ten = ir.module[0].type[0].structure.field[0]
        self.assertEqual("10", field_ten.read_transform.type.enumeration.value)


class InfinityAugmentedArithmeticTest(unittest.TestCase):

    # TODO(bolms): Will there ever be any situations where all elements of the arg
    # to _min would be "infinity"?
    def test_min_of_infinities(self):
        self.assertEqual("infinity", expression_bounds._min(["infinity", "infinity"]))

    # TODO(bolms): Will there ever be any situations where all elements of the arg
    # to _max would be "-infinity"?
    def test_max_of_negative_infinities(self):
        self.assertEqual(
            "-infinity", expression_bounds._max(["-infinity", "-infinity"])
        )

    def test_shared_modular_value_of_identical_modulus_and_value(self):
        self.assertEqual(
            (10, 8), expression_bounds._shared_modular_value((10, 8), (10, 8))
        )

    def test_shared_modular_value_of_identical_modulus(self):
        self.assertEqual(
            (5, 3), expression_bounds._shared_modular_value((10, 8), (10, 3))
        )

    def test_shared_modular_value_of_identical_value(self):
        self.assertEqual(
            (6, 2), expression_bounds._shared_modular_value((18, 2), (12, 2))
        )

    def test_shared_modular_value_of_different_arguments(self):
        self.assertEqual(
            (7, 4), expression_bounds._shared_modular_value((21, 11), (14, 4))
        )

    def test_shared_modular_value_of_infinity_and_non(self):
        self.assertEqual(
            (7, 4), expression_bounds._shared_modular_value(("infinity", 25), (14, 4))
        )

    def test_shared_modular_value_of_infinity_and_infinity(self):
        self.assertEqual(
            (14, 5),
            expression_bounds._shared_modular_value(("infinity", 19), ("infinity", 5)),
        )

    def test_shared_modular_value_of_infinity_and_identical_value(self):
        self.assertEqual(
            ("infinity", 5),
            expression_bounds._shared_modular_value(("infinity", 5), ("infinity", 5)),
        )


if __name__ == "__main__":
    unittest.main()
