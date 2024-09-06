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

"""Tests for ...emboss.front_end.write_inference."""

import unittest
from compiler.front_end import glue
from compiler.front_end import write_inference
from compiler.util import ir_data
from compiler.util import test_util


class WriteInferenceTest(unittest.TestCase):

    def _make_ir(self, emb_text):
        ir, unused_debug_info, errors = glue.parse_emboss_file(
            "m.emb",
            test_util.dict_file_reader({"m.emb": emb_text}),
            stop_before_step="set_write_methods",
        )
        assert not errors, errors
        return ir

    def test_adds_physical_write_method(self):
        ir = self._make_ir("struct Foo:\n" "  0 [+1]  UInt  x\n")
        self.assertEqual([], write_inference.set_write_methods(ir))
        self.assertTrue(ir.module[0].type[0].structure.field[0].write_method.physical)

    def test_adds_read_only_write_method_to_non_alias_virtual(self):
        ir = self._make_ir("struct Foo:\n" "  let x = 5\n")
        self.assertEqual([], write_inference.set_write_methods(ir))
        self.assertTrue(ir.module[0].type[0].structure.field[0].write_method.read_only)

    def test_adds_alias_write_method_to_alias_of_physical_field(self):
        ir = self._make_ir("struct Foo:\n" "  let x = y\n" "  0 [+1]  UInt  y\n")
        self.assertEqual([], write_inference.set_write_methods(ir))
        field = ir.module[0].type[0].structure.field[0]
        self.assertTrue(field.write_method.HasField("alias"))
        self.assertEqual(
            "y", field.write_method.alias.path[0].canonical_name.object_path[-1]
        )

    def test_adds_alias_write_method_to_alias_of_alias_of_physical_field(self):
        ir = self._make_ir(
            "struct Foo:\n" "  let x = z\n" "  let z = y\n" "  0 [+1]  UInt  y\n"
        )
        self.assertEqual([], write_inference.set_write_methods(ir))
        field = ir.module[0].type[0].structure.field[0]
        self.assertTrue(field.write_method.HasField("alias"))
        self.assertEqual(
            "z", field.write_method.alias.path[0].canonical_name.object_path[-1]
        )

    def test_adds_read_only_write_method_to_alias_of_read_only(self):
        ir = self._make_ir("struct Foo:\n" "  let x = y\n" "  let y = 5\n")
        self.assertEqual([], write_inference.set_write_methods(ir))
        field = ir.module[0].type[0].structure.field[0]
        self.assertTrue(field.write_method.read_only)

    def test_adds_read_only_write_method_to_alias_of_alias_of_read_only(self):
        ir = self._make_ir(
            "struct Foo:\n" "  let x = z\n" "  let z = y\n" "  let y = 5\n"
        )
        self.assertEqual([], write_inference.set_write_methods(ir))
        field = ir.module[0].type[0].structure.field[0]
        self.assertTrue(field.write_method.read_only)

    def test_adds_read_only_write_method_to_alias_of_parameter(self):
        ir = self._make_ir("struct Foo(x: UInt:8):\n" "  let y = x\n")
        self.assertEqual([], write_inference.set_write_methods(ir))
        field = ir.module[0].type[0].structure.field[0]
        self.assertTrue(field.write_method.read_only)

    def test_adds_transform_write_method_to_base_value_field(self):
        ir = self._make_ir("struct Foo:\n" "  0 [+1]  UInt  x\n" "  let y = x + 50\n")
        self.assertEqual([], write_inference.set_write_methods(ir))
        field = ir.module[0].type[0].structure.field[1]
        transform = field.write_method.transform
        self.assertTrue(transform)
        self.assertEqual(
            "x", transform.destination.path[0].canonical_name.object_path[-1]
        )
        self.assertEqual(
            ir_data.FunctionMapping.SUBTRACTION,
            transform.function_body.function.function,
        )
        arg0, arg1 = transform.function_body.function.args
        self.assertEqual(
            "$logical_value", arg0.builtin_reference.canonical_name.object_path[0]
        )
        self.assertEqual("50", arg1.constant.value)

    def test_adds_transform_write_method_to_negative_base_value_field(self):
        ir = self._make_ir("struct Foo:\n" "  0 [+1]  UInt  x\n" "  let y = x - 50\n")
        self.assertEqual([], write_inference.set_write_methods(ir))
        field = ir.module[0].type[0].structure.field[1]
        transform = field.write_method.transform
        self.assertTrue(transform)
        self.assertEqual(
            "x", transform.destination.path[0].canonical_name.object_path[-1]
        )
        self.assertEqual(
            ir_data.FunctionMapping.ADDITION, transform.function_body.function.function
        )
        arg0, arg1 = transform.function_body.function.args
        self.assertEqual(
            "$logical_value", arg0.builtin_reference.canonical_name.object_path[0]
        )
        self.assertEqual("50", arg1.constant.value)

    def test_adds_transform_write_method_to_reversed_base_value_field(self):
        ir = self._make_ir("struct Foo:\n" "  0 [+1]  UInt  x\n" "  let y = 50 + x\n")
        self.assertEqual([], write_inference.set_write_methods(ir))
        field = ir.module[0].type[0].structure.field[1]
        transform = field.write_method.transform
        self.assertTrue(transform)
        self.assertEqual(
            "x", transform.destination.path[0].canonical_name.object_path[-1]
        )
        self.assertEqual(
            ir_data.FunctionMapping.SUBTRACTION,
            transform.function_body.function.function,
        )
        arg0, arg1 = transform.function_body.function.args
        self.assertEqual(
            "$logical_value", arg0.builtin_reference.canonical_name.object_path[0]
        )
        self.assertEqual("50", arg1.constant.value)

    def test_adds_transform_write_method_to_reversed_negative_base_value_field(self):
        ir = self._make_ir("struct Foo:\n" "  0 [+1]  UInt  x\n" "  let y = 50 - x\n")
        self.assertEqual([], write_inference.set_write_methods(ir))
        field = ir.module[0].type[0].structure.field[1]
        transform = field.write_method.transform
        self.assertTrue(transform)
        self.assertEqual(
            "x", transform.destination.path[0].canonical_name.object_path[-1]
        )
        self.assertEqual(
            ir_data.FunctionMapping.SUBTRACTION,
            transform.function_body.function.function,
        )
        arg0, arg1 = transform.function_body.function.args
        self.assertEqual("50", arg0.constant.value)
        self.assertEqual(
            "$logical_value", arg1.builtin_reference.canonical_name.object_path[0]
        )

    def test_adds_transform_write_method_to_nested_invertible_field(self):
        ir = self._make_ir(
            "struct Foo:\n" "  0 [+1]  UInt  x\n" "  let y = 30 + (50 - x)\n"
        )
        self.assertEqual([], write_inference.set_write_methods(ir))
        field = ir.module[0].type[0].structure.field[1]
        transform = field.write_method.transform
        self.assertTrue(transform)
        self.assertEqual(
            "x", transform.destination.path[0].canonical_name.object_path[-1]
        )
        self.assertEqual(
            ir_data.FunctionMapping.SUBTRACTION,
            transform.function_body.function.function,
        )
        arg0, arg1 = transform.function_body.function.args
        self.assertEqual("50", arg0.constant.value)
        self.assertEqual(ir_data.FunctionMapping.SUBTRACTION, arg1.function.function)
        arg10, arg11 = arg1.function.args
        self.assertEqual(
            "$logical_value", arg10.builtin_reference.canonical_name.object_path[0]
        )
        self.assertEqual("30", arg11.constant.value)

    def test_does_not_add_transform_write_method_for_parameter_target(self):
        ir = self._make_ir("struct Foo(x: UInt:8):\n" "  let y = 50 + x\n")
        self.assertEqual([], write_inference.set_write_methods(ir))
        field = ir.module[0].type[0].structure.field[0]
        self.assertEqual("read_only", field.write_method.WhichOneof("method"))

    def test_adds_transform_write_method_with_complex_auxiliary_subexpression(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  0 [+1]  UInt  x\n"
            "  let y = x - $max(Foo.$size_in_bytes, Foo.z)\n"
            "  let z = 500\n"
        )
        self.assertEqual([], write_inference.set_write_methods(ir))
        field = ir.module[0].type[0].structure.field[1]
        transform = field.write_method.transform
        self.assertTrue(transform)
        self.assertEqual(
            "x", transform.destination.path[0].canonical_name.object_path[-1]
        )
        self.assertEqual(
            ir_data.FunctionMapping.ADDITION, transform.function_body.function.function
        )
        args = transform.function_body.function.args
        self.assertEqual(
            "$logical_value", args[0].builtin_reference.canonical_name.object_path[0]
        )
        self.assertEqual(field.read_transform.function.args[1], args[1])


if __name__ == "__main__":
    unittest.main()
