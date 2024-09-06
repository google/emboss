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

"""Tests for front_end.type_check."""

import unittest
from compiler.front_end import glue
from compiler.front_end import type_check
from compiler.util import error
from compiler.util import ir_data_utils
from compiler.util import test_util


class TypeAnnotationTest(unittest.TestCase):

    def _make_ir(self, emb_text):
        ir, unused_debug_info, errors = glue.parse_emboss_file(
            "m.emb",
            test_util.dict_file_reader({"m.emb": emb_text}),
            stop_before_step="annotate_types",
        )
        assert not errors, errors
        return ir

    def test_adds_integer_constant_type(self):
        ir = self._make_ir(
            "struct Foo:\n" "  0 [+1]     UInt      x\n" "  1 [+1]     UInt:8[]  y\n"
        )
        self.assertEqual([], type_check.annotate_types(ir))
        expression = ir.module[0].type[0].structure.field[1].location.size
        self.assertEqual(expression.type.WhichOneof("type"), "integer")

    def test_adds_boolean_constant_type(self):
        ir = self._make_ir(
            "struct Foo:\n" "  0 [+1]     UInt      x\n" "  1 [+true]  UInt:8[]  y\n"
        )
        self.assertEqual(
            [],
            error.filter_errors(type_check.annotate_types(ir)),
            ir_data_utils.IrDataSerializer(ir).to_json(indent=2),
        )
        expression = ir.module[0].type[0].structure.field[1].location.size
        self.assertEqual(expression.type.WhichOneof("type"), "boolean")

    def test_adds_enum_constant_type(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  0 [+Enum.VALUE]  UInt  x\n"
            "enum Enum:\n"
            "  VALUE = 1\n"
        )
        self.assertEqual([], error.filter_errors(type_check.annotate_types(ir)))
        expression = ir.module[0].type[0].structure.field[0].location.size
        self.assertEqual(expression.type.WhichOneof("type"), "enumeration")
        enum_type_name = expression.type.enumeration.name.canonical_name
        self.assertEqual(enum_type_name.module_file, "m.emb")
        self.assertEqual(enum_type_name.object_path[0], "Enum")

    def test_adds_enum_field_type(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  0 [+1]  Enum  x\n"
            "  1 [+x]  UInt  y\n"
            "enum Enum:\n"
            "  VALUE = 1\n"
        )
        self.assertEqual([], error.filter_errors(type_check.annotate_types(ir)))
        expression = ir.module[0].type[0].structure.field[1].location.size
        self.assertEqual(expression.type.WhichOneof("type"), "enumeration")
        enum_type_name = expression.type.enumeration.name.canonical_name
        self.assertEqual(enum_type_name.module_file, "m.emb")
        self.assertEqual(enum_type_name.object_path[0], "Enum")

    def test_adds_integer_operation_types(self):
        ir = self._make_ir(
            "struct Foo:\n" "  0 [+1]     UInt      x\n" "  1 [+1+1]   UInt:8[]  y\n"
        )
        self.assertEqual([], type_check.annotate_types(ir))
        expression = ir.module[0].type[0].structure.field[1].location.size
        self.assertEqual(expression.type.WhichOneof("type"), "integer")
        self.assertEqual(expression.function.args[0].type.WhichOneof("type"), "integer")
        self.assertEqual(expression.function.args[1].type.WhichOneof("type"), "integer")

    def test_adds_enum_operation_type(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  0 [+1]                   UInt      x\n"
            "  1 [+Enum.VAL==Enum.VAL]  UInt:8[]  y\n"
            "enum Enum:\n"
            "  VAL = 1\n"
        )
        self.assertEqual([], error.filter_errors(type_check.annotate_types(ir)))
        expression = ir.module[0].type[0].structure.field[1].location.size
        self.assertEqual(expression.type.WhichOneof("type"), "boolean")
        self.assertEqual(
            expression.function.args[0].type.WhichOneof("type"), "enumeration"
        )
        self.assertEqual(
            expression.function.args[1].type.WhichOneof("type"), "enumeration"
        )

    def test_adds_enum_comparison_operation_type(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  0 [+1]                   UInt      x\n"
            "  1 [+Enum.VAL>=Enum.VAL]  UInt:8[]  y\n"
            "enum Enum:\n"
            "  VAL = 1\n"
        )
        self.assertEqual([], error.filter_errors(type_check.annotate_types(ir)))
        expression = ir.module[0].type[0].structure.field[1].location.size
        self.assertEqual(expression.type.WhichOneof("type"), "boolean")
        self.assertEqual(
            expression.function.args[0].type.WhichOneof("type"), "enumeration"
        )
        self.assertEqual(
            expression.function.args[1].type.WhichOneof("type"), "enumeration"
        )

    def test_adds_integer_field_type(self):
        ir = self._make_ir(
            "struct Foo:\n" "  0 [+1]     UInt      x\n" "  1 [+x]     UInt:8[]  y\n"
        )
        self.assertEqual([], type_check.annotate_types(ir))
        expression = ir.module[0].type[0].structure.field[1].location.size
        self.assertEqual(expression.type.WhichOneof("type"), "integer")

    def test_adds_opaque_field_type(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  0 [+1]     Bar       x\n"
            "  1 [+x]     UInt:8[]  y\n"
            "struct Bar:\n"
            "  0 [+1]     UInt    z\n"
        )
        self.assertEqual([], error.filter_errors(type_check.annotate_types(ir)))
        expression = ir.module[0].type[0].structure.field[1].location.size
        self.assertEqual(expression.type.WhichOneof("type"), "opaque")

    def test_adds_opaque_field_type_for_array(self):
        ir = self._make_ir(
            "struct Foo:\n" "  0 [+1]     UInt:8[]  x\n" "  1 [+x]     UInt:8[]  y\n"
        )
        self.assertEqual([], error.filter_errors(type_check.annotate_types(ir)))
        expression = ir.module[0].type[0].structure.field[1].location.size
        self.assertEqual(expression.type.WhichOneof("type"), "opaque")

    def test_error_on_bad_plus_operand_types(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  0 [+1]       UInt      x\n"
            "  1 [+1+true]  UInt:8[]  y\n"
        )
        expression = ir.module[0].type[0].structure.field[1].location.size
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        expression.function.args[1].source_location,
                        "Right argument of operator '+' must be an integer.",
                    )
                ]
            ],
            error.filter_errors(type_check.annotate_types(ir)),
        )

    def test_error_on_bad_minus_operand_types(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  0 [+1]       UInt      x\n"
            "  1 [+1-true]  UInt:8[]  y\n"
        )
        expression = ir.module[0].type[0].structure.field[1].location.size
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        expression.function.args[1].source_location,
                        "Right argument of operator '-' must be an integer.",
                    )
                ]
            ],
            error.filter_errors(type_check.annotate_types(ir)),
        )

    def test_error_on_bad_times_operand_types(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  0 [+1]       UInt      x\n"
            "  1 [+1*true]  UInt:8[]  y\n"
        )
        expression = ir.module[0].type[0].structure.field[1].location.size
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        expression.function.args[1].source_location,
                        "Right argument of operator '*' must be an integer.",
                    )
                ]
            ],
            error.filter_errors(type_check.annotate_types(ir)),
        )

    def test_error_on_bad_equality_left_operand(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  0 [+1]       UInt:8[]  x\n"
            "  1 [+x==x]    UInt:8[]  y\n"
        )
        expression = ir.module[0].type[0].structure.field[1].location.size
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        expression.function.args[0].source_location,
                        "Left argument of operator '==' must be an integer, "
                        "boolean, or enum.",
                    )
                ]
            ],
            error.filter_errors(type_check.annotate_types(ir)),
        )

    def test_error_on_bad_equality_right_operand(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  0 [+1]       UInt:8[]  x\n"
            "  1 [+1==x]    UInt:8[]  y\n"
        )
        expression = ir.module[0].type[0].structure.field[1].location.size
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        expression.function.args[1].source_location,
                        "Right argument of operator '==' must be an integer, "
                        "boolean, or enum.",
                    )
                ]
            ],
            error.filter_errors(type_check.annotate_types(ir)),
        )

    def test_error_on_equality_mismatched_operands_int_bool(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  0 [+1]         UInt      x\n"
            "  1 [+1==true]   UInt:8[]  y\n"
        )
        expression = ir.module[0].type[0].structure.field[1].location.size
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        expression.source_location,
                        "Both arguments of operator '==' must have the same " "type.",
                    )
                ]
            ],
            error.filter_errors(type_check.annotate_types(ir)),
        )

    def test_error_on_mismatched_comparison_operands(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  0 [+1]           UInt:8    x\n"
            "  1 [+x>=Bar.BAR]  UInt:8[]  y\n"
            "enum Bar:\n"
            "  BAR = 1\n"
        )
        expression = ir.module[0].type[0].structure.field[1].location.size
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        expression.source_location,
                        "Both arguments of operator '>=' must have the same " "type.",
                    )
                ]
            ],
            error.filter_errors(type_check.annotate_types(ir)),
        )

    def test_error_on_equality_mismatched_operands_bool_int(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  0 [+1]         UInt      x\n"
            "  1 [+true!=1]   UInt:8[]  y\n"
        )
        expression = ir.module[0].type[0].structure.field[1].location.size
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        expression.source_location,
                        "Both arguments of operator '!=' must have the same " "type.",
                    )
                ]
            ],
            error.filter_errors(type_check.annotate_types(ir)),
        )

    def test_error_on_equality_mismatched_operands_enum_enum(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  0 [+1]                 UInt      x\n"
            "  1 [+Bar.BAR==Baz.BAZ]  UInt:8[]  y\n"
            "enum Bar:\n"
            "  BAR = 1\n"
            "enum Baz:\n"
            "  BAZ = 1\n"
        )
        expression = ir.module[0].type[0].structure.field[1].location.size
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        expression.source_location,
                        "Both arguments of operator '==' must have the same " "type.",
                    )
                ]
            ],
            error.filter_errors(type_check.annotate_types(ir)),
        )

    def test_error_on_bad_choice_condition_operand(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  0 [+1]          UInt:8[]  x\n"
            "  1 [+5 ? 0 : 1]  UInt:8[]  y\n"
        )
        expression = ir.module[0].type[0].structure.field[1].location.size
        condition_arg = expression.function.args[0]
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        condition_arg.source_location,
                        "Condition of operator '?:' must be a boolean.",
                    )
                ]
            ],
            error.filter_errors(type_check.annotate_types(ir)),
        )

    def test_error_on_bad_choice_if_true_operand(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  0 [+1]             UInt:8[]  x\n"
            "  1 [+true ? x : x]  UInt:8[]  y\n"
        )
        expression = ir.module[0].type[0].structure.field[1].location.size
        if_true_arg = expression.function.args[1]
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        if_true_arg.source_location,
                        "If-true clause of operator '?:' must be an integer, "
                        "boolean, or enum.",
                    )
                ]
            ],
            error.filter_errors(type_check.annotate_types(ir)),
        )

    def test_choice_of_bools(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  0 [+1]                    UInt:8[]  x\n"
            "  1 [+true ? true : false]  UInt:8[]  y\n"
        )
        expression = ir.module[0].type[0].structure.field[1].location.size
        self.assertEqual([], error.filter_errors(type_check.annotate_types(ir)))
        self.assertEqual("boolean", expression.type.WhichOneof("type"))

    def test_choice_of_integers(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  0 [+1]               UInt:8[]  x\n"
            "  1 [+true ? 0 : 100]  UInt:8[]  y\n"
        )
        expression = ir.module[0].type[0].structure.field[1].location.size
        self.assertEqual([], type_check.annotate_types(ir))
        self.assertEqual("integer", expression.type.WhichOneof("type"))

    def test_choice_of_enums(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  0 [+1]                     enum      xx:\n"
            "    XX = 1\n"
            "    YY = 1\n"
            "  1 [+true ? Xx.XX : Xx.YY]  UInt:8[]  y\n"
        )
        expression = ir.module[0].type[0].structure.field[1].location.size
        self.assertEqual([], error.filter_errors(type_check.annotate_types(ir)))
        self.assertEqual("enumeration", expression.type.WhichOneof("type"))
        self.assertFalse(expression.type.enumeration.HasField("value"))
        self.assertEqual(
            "m.emb", expression.type.enumeration.name.canonical_name.module_file
        )
        self.assertEqual(
            "Foo", expression.type.enumeration.name.canonical_name.object_path[0]
        )
        self.assertEqual(
            "Xx", expression.type.enumeration.name.canonical_name.object_path[1]
        )

    def test_error_on_bad_choice_mismatched_operands(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  0 [+1]                UInt:8[]  x\n"
            "  1 [+true ? 0 : true]  UInt:8[]  y\n"
        )
        expression = ir.module[0].type[0].structure.field[1].location.size
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        expression.source_location,
                        "The if-true and if-false clauses of operator '?:' must "
                        "have the same type.",
                    )
                ]
            ],
            error.filter_errors(type_check.annotate_types(ir)),
        )

    def test_error_on_bad_choice_mismatched_enum_operands(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  0 [+1]                         UInt:8[]  x\n"
            "  1 [+true ? Baz.BAZ : Bar.BAR]  UInt:8[]  y\n"
            "enum Bar:\n"
            "  BAR = 1\n"
            "enum Baz:\n"
            "  BAZ = 1\n"
        )
        expression = ir.module[0].type[0].structure.field[1].location.size
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        expression.source_location,
                        "The if-true and if-false clauses of operator '?:' must "
                        "have the same type.",
                    )
                ]
            ],
            error.filter_errors(type_check.annotate_types(ir)),
        )

    def test_error_on_bad_left_operand_type(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  0 [+1]       UInt      x\n"
            "  1 [+true+1]  UInt:8[]  y\n"
        )
        expression = ir.module[0].type[0].structure.field[1].location.size
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        expression.function.args[0].source_location,
                        "Left argument of operator '+' must be an integer.",
                    )
                ]
            ],
            error.filter_errors(type_check.annotate_types(ir)),
        )

    def test_error_on_opaque_operand_type(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  0 [+1]       UInt:8[]  x\n"
            "  1 [+x+1]     UInt:8[]  y\n"
        )
        expression = ir.module[0].type[0].structure.field[1].location.size
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        expression.function.args[0].source_location,
                        "Left argument of operator '+' must be an integer.",
                    )
                ]
            ],
            error.filter_errors(type_check.annotate_types(ir)),
        )

    def test_error_on_bad_left_comparison_operand_type(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  0 [+1]       UInt      x\n"
            "  1 [+true<1]  UInt:8[]  y\n"
        )
        expression = ir.module[0].type[0].structure.field[1].location.size
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        expression.function.args[0].source_location,
                        "Left argument of operator '<' must be an integer or enum.",
                    )
                ]
            ],
            error.filter_errors(type_check.annotate_types(ir)),
        )

    def test_error_on_bad_right_comparison_operand_type(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  0 [+1]        UInt      x\n"
            "  1 [+1>=true]  UInt:8[]  y\n"
        )
        expression = ir.module[0].type[0].structure.field[1].location.size
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        expression.function.args[1].source_location,
                        "Right argument of operator '>=' must be an integer or enum.",
                    )
                ]
            ],
            error.filter_errors(type_check.annotate_types(ir)),
        )

    def test_error_on_bad_boolean_operand_type(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  0 [+1]       UInt      x\n"
            "  1 [+1&&true]  UInt:8[]  y\n"
        )
        expression = ir.module[0].type[0].structure.field[1].location.size
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        expression.function.args[0].source_location,
                        "Left argument of operator '&&' must be a boolean.",
                    )
                ]
            ],
            error.filter_errors(type_check.annotate_types(ir)),
        )

    def test_max_return_type(self):
        ir = self._make_ir("struct Foo:\n" "  $max(1, 2, 3) [+1]  UInt:8[]  x\n")
        expression = ir.module[0].type[0].structure.field[0].location.start
        self.assertEqual([], type_check.annotate_types(ir))
        self.assertEqual("integer", expression.type.WhichOneof("type"))

    def test_error_on_bad_max_argument(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  $max(Bar.XX) [+1]  UInt:8[]  x\n"
            "enum Bar:\n"
            "  XX = 0\n"
        )
        expression = ir.module[0].type[0].structure.field[0].location.start
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        expression.function.args[0].source_location,
                        "Argument 0 of function '$max' must be an integer.",
                    )
                ]
            ],
            error.filter_errors(type_check.annotate_types(ir)),
        )

    def test_error_on_no_max_argument(self):
        ir = self._make_ir("struct Foo:\n" "  $max() [+1]  UInt:8[]  x\n")
        expression = ir.module[0].type[0].structure.field[0].location.start
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        expression.source_location,
                        "Function '$max' requires at least 1 argument.",
                    )
                ]
            ],
            error.filter_errors(type_check.annotate_types(ir)),
        )

    def test_upper_bound_return_type(self):
        ir = self._make_ir("struct Foo:\n" "  $upper_bound(3) [+1]  UInt:8[]  x\n")
        expression = ir.module[0].type[0].structure.field[0].location.start
        self.assertEqual([], type_check.annotate_types(ir))
        self.assertEqual("integer", expression.type.WhichOneof("type"))

    def test_upper_bound_too_few_arguments(self):
        ir = self._make_ir("struct Foo:\n" "  $upper_bound() [+1]  UInt:8[]  x\n")
        expression = ir.module[0].type[0].structure.field[0].location.start
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        expression.source_location,
                        "Function '$upper_bound' requires exactly 1 argument.",
                    )
                ]
            ],
            error.filter_errors(type_check.annotate_types(ir)),
        )

    def test_upper_bound_too_many_arguments(self):
        ir = self._make_ir("struct Foo:\n" "  $upper_bound(1, 2) [+1]  UInt:8[]  x\n")
        expression = ir.module[0].type[0].structure.field[0].location.start
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        expression.source_location,
                        "Function '$upper_bound' requires exactly 1 argument.",
                    )
                ]
            ],
            error.filter_errors(type_check.annotate_types(ir)),
        )

    def test_upper_bound_wrong_argument_type(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  $upper_bound(Bar.XX) [+1]  UInt:8[]  x\n"
            "enum Bar:\n"
            "  XX = 0\n"
        )
        expression = ir.module[0].type[0].structure.field[0].location.start
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        expression.function.args[0].source_location,
                        "Argument 0 of function '$upper_bound' must be an integer.",
                    )
                ]
            ],
            error.filter_errors(type_check.annotate_types(ir)),
        )

    def test_lower_bound_return_type(self):
        ir = self._make_ir("struct Foo:\n" "  $lower_bound(3) [+1]  UInt:8[]  x\n")
        expression = ir.module[0].type[0].structure.field[0].location.start
        self.assertEqual([], type_check.annotate_types(ir))
        self.assertEqual("integer", expression.type.WhichOneof("type"))

    def test_lower_bound_too_few_arguments(self):
        ir = self._make_ir("struct Foo:\n" "  $lower_bound() [+1]  UInt:8[]  x\n")
        expression = ir.module[0].type[0].structure.field[0].location.start
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        expression.source_location,
                        "Function '$lower_bound' requires exactly 1 argument.",
                    )
                ]
            ],
            error.filter_errors(type_check.annotate_types(ir)),
        )

    def test_lower_bound_too_many_arguments(self):
        ir = self._make_ir("struct Foo:\n" "  $lower_bound(1, 2) [+1]  UInt:8[]  x\n")
        expression = ir.module[0].type[0].structure.field[0].location.start
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        expression.source_location,
                        "Function '$lower_bound' requires exactly 1 argument.",
                    )
                ]
            ],
            error.filter_errors(type_check.annotate_types(ir)),
        )

    def test_lower_bound_wrong_argument_type(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  $lower_bound(Bar.XX) [+1]  UInt:8[]  x\n"
            "enum Bar:\n"
            "  XX = 0\n"
        )
        expression = ir.module[0].type[0].structure.field[0].location.start
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        expression.function.args[0].source_location,
                        "Argument 0 of function '$lower_bound' must be an integer.",
                    )
                ]
            ],
            error.filter_errors(type_check.annotate_types(ir)),
        )

    def test_error_static_reference_to_physical_field(self):
        ir = self._make_ir("struct Foo:\n" "  0 [+1]  UInt  x\n" "  let y = Foo.x\n")
        static_ref = ir.module[0].type[0].structure.field[1].read_transform
        physical_field = ir.module[0].type[0].structure.field[0]
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        static_ref.source_location,
                        "Static references to physical fields are not allowed.",
                    ),
                    error.note(
                        "m.emb",
                        physical_field.source_location,
                        "x is a physical field.",
                    ),
                ]
            ],
            type_check.annotate_types(ir),
        )

    def test_error_on_non_field_argument_to_has(self):
        ir = self._make_ir(
            "struct Foo:\n" "  if $present(0):\n" "    0 [+1]  UInt  x\n"
        )
        expression = ir.module[0].type[0].structure.field[0].existence_condition
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        expression.function.args[0].source_location,
                        "Argument 0 of function '$present' must be a field.",
                    )
                ]
            ],
            error.filter_errors(type_check.annotate_types(ir)),
        )

    def test_error_on_no_argument_has(self):
        ir = self._make_ir("struct Foo:\n" "  if $present():\n" "    0 [+1]  UInt  x\n")
        expression = ir.module[0].type[0].structure.field[0].existence_condition
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        expression.source_location,
                        "Function '$present' requires exactly 1 argument.",
                    )
                ]
            ],
            error.filter_errors(type_check.annotate_types(ir)),
        )

    def test_error_on_too_many_argument_has(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  if $present(y, y):\n"
            "    0 [+1]  UInt  x\n"
            "  1 [+1]  UInt  y\n"
        )
        expression = ir.module[0].type[0].structure.field[0].existence_condition
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        expression.source_location,
                        "Function '$present' requires exactly 1 argument.",
                    )
                ]
            ],
            error.filter_errors(type_check.annotate_types(ir)),
        )

    def test_checks_that_parameters_are_atomic_types(self):
        ir = self._make_ir("struct Foo(y: UInt:8[1]):\n" "  0 [+1]  UInt  x\n")
        error_parameter = ir.module[0].type[0].runtime_parameter[0]
        error_location = error_parameter.physical_type_alias.source_location
        self.assertEqual(
            [[error.error("m.emb", error_location, "Parameters cannot be arrays.")]],
            error.filter_errors(type_check.annotate_types(ir)),
        )


class TypeCheckTest(unittest.TestCase):

    def _make_ir(self, emb_text):
        ir, unused_debug_info, errors = glue.parse_emboss_file(
            "m.emb",
            test_util.dict_file_reader({"m.emb": emb_text}),
            stop_before_step="check_types",
        )
        assert not errors, errors
        return ir

    def test_error_on_opaque_type_in_field_start(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  0 [+1]       UInt:8[]  x\n"
            "  x [+10]      UInt:8[]  y\n"
        )
        expression = ir.module[0].type[0].structure.field[1].location.start
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        expression.source_location,
                        "Start of field must be an integer.",
                    )
                ]
            ],
            type_check.check_types(ir),
        )

    def test_error_on_boolean_type_in_field_start(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  0 [+1]       UInt:8[]  x\n"
            "  true [+10]   UInt:8[]  y\n"
        )
        expression = ir.module[0].type[0].structure.field[1].location.start
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        expression.source_location,
                        "Start of field must be an integer.",
                    )
                ]
            ],
            type_check.check_types(ir),
        )

    def test_error_on_opaque_type_in_field_size(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  0 [+1]       UInt:8[]  x\n"
            "  1 [+x]       UInt:8[]  y\n"
        )
        expression = ir.module[0].type[0].structure.field[1].location.size
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        expression.source_location,
                        "Size of field must be an integer.",
                    )
                ]
            ],
            type_check.check_types(ir),
        )

    def test_error_on_boolean_type_in_field_size(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  0 [+1]       UInt:8[]  x\n"
            "  1 [+true]    UInt:8[]  y\n"
        )
        expression = ir.module[0].type[0].structure.field[1].location.size
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        expression.source_location,
                        "Size of field must be an integer.",
                    )
                ]
            ],
            type_check.check_types(ir),
        )

    def test_error_on_opaque_type_in_array_size(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  0 [+1]       UInt:8[]   x\n"
            "  1 [+9]       UInt:8[x]  y\n"
        )
        expression = (
            ir.module[0].type[0].structure.field[1].type.array_type.element_count
        )
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        expression.source_location,
                        "Array size must be an integer.",
                    )
                ]
            ],
            type_check.check_types(ir),
        )

    def test_error_on_boolean_type_in_array_size(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  0 [+1]       UInt:8[]      x\n"
            "  1 [+9]       UInt:8[true]  y\n"
        )
        expression = (
            ir.module[0].type[0].structure.field[1].type.array_type.element_count
        )
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        expression.source_location,
                        "Array size must be an integer.",
                    )
                ]
            ],
            type_check.check_types(ir),
        )

    def test_error_on_integer_type_in_existence_condition(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  0 [+1]       UInt:8[]  x\n"
            "  if 1:\n"
            "    1 [+9]     UInt:8[]  y\n"
        )
        expression = ir.module[0].type[0].structure.field[1].existence_condition
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        expression.source_location,
                        "Existence condition must be a boolean.",
                    )
                ]
            ],
            type_check.check_types(ir),
        )

    def test_error_on_non_integer_non_enum_parameter(self):
        ir = self._make_ir("struct Foo(f: Flag):\n" "  0 [+1]       UInt:8[]  x\n")
        parameter = ir.module[0].type[0].runtime_parameter[0]
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        parameter.physical_type_alias.source_location,
                        "Runtime parameters must be integer or enum.",
                    )
                ]
            ],
            type_check.check_types(ir),
        )

    def test_error_on_failure_to_pass_parameter(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  0 [+1]  Bar  b\n"
            "struct Bar(f: UInt:6):\n"
            "  0 [+1]       UInt:8[]  x\n"
        )
        type_ir = ir.module[0].type[0].structure.field[0].type
        bar = ir.module[0].type[1]
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        type_ir.source_location,
                        "Type Bar requires 1 parameter; 0 parameters given.",
                    ),
                    error.note("m.emb", bar.source_location, "Definition of type Bar."),
                ]
            ],
            type_check.check_types(ir),
        )

    def test_error_on_passing_unneeded_parameter(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  0 [+1]  Bar(1)  b\n"
            "struct Bar:\n"
            "  0 [+1]       UInt:8[]  x\n"
        )
        type_ir = ir.module[0].type[0].structure.field[0].type
        bar = ir.module[0].type[1]
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        type_ir.source_location,
                        "Type Bar requires 0 parameters; 1 parameter given.",
                    ),
                    error.note("m.emb", bar.source_location, "Definition of type Bar."),
                ]
            ],
            type_check.check_types(ir),
        )

    def test_error_on_passing_wrong_parameter_type(self):
        ir = self._make_ir(
            "struct Foo:\n"
            "  0 [+1]  Bar(1)  b\n"
            "enum Baz:\n"
            "  QUX = 1\n"
            "struct Bar(n: Baz):\n"
            "  0 [+1]       UInt:8[]  x\n"
        )
        type_ir = ir.module[0].type[0].structure.field[0].type
        usage_parameter_ir = type_ir.atomic_type.runtime_parameter[0]
        source_parameter_ir = ir.module[0].type[2].runtime_parameter[0]
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        usage_parameter_ir.source_location,
                        "Parameter 0 of type Bar must be Baz, not integer.",
                    ),
                    error.note(
                        "m.emb",
                        source_parameter_ir.source_location,
                        "Parameter 0 of Bar.",
                    ),
                ]
            ],
            type_check.check_types(ir),
        )


if __name__ == "__main__":
    unittest.main()
