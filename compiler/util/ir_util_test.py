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

"""Tests for util.ir_util."""

import unittest
from compiler.util import expression_parser
from compiler.util import ir_data
from compiler.util import ir_data_utils
from compiler.util import ir_util


def _parse_expression(text):
    return expression_parser.parse(text)


class IrUtilTest(unittest.TestCase):
    """Tests for the miscellaneous utility functions in ir_util.py."""

    def test_is_constant_integer(self):
        self.assertTrue(ir_util.is_constant(_parse_expression("6")))
        expression = _parse_expression("12")
        # The type information should be ignored for constants like this one.
        ir_data_utils.builder(expression).type.integer.CopyFrom(ir_data.IntegerType())
        self.assertTrue(ir_util.is_constant(expression))

    def test_is_constant_boolean(self):
        self.assertTrue(ir_util.is_constant(_parse_expression("true")))
        expression = _parse_expression("true")
        # The type information should be ignored for constants like this one.
        ir_data_utils.builder(expression).type.boolean.CopyFrom(ir_data.BooleanType())
        self.assertTrue(ir_util.is_constant(expression))

    def test_is_constant_enum(self):
        self.assertTrue(
            ir_util.is_constant(
                ir_data.Expression(
                    constant_reference=ir_data.Reference(),
                    type=ir_data.ExpressionType(
                        enumeration=ir_data.EnumType(value="12")
                    ),
                )
            )
        )

    def test_is_constant_integer_type(self):
        self.assertFalse(
            ir_util.is_constant_type(
                ir_data.ExpressionType(
                    integer=ir_data.IntegerType(
                        modulus="10",
                        modular_value="5",
                        minimum_value="-5",
                        maximum_value="15",
                    )
                )
            )
        )
        self.assertTrue(
            ir_util.is_constant_type(
                ir_data.ExpressionType(
                    integer=ir_data.IntegerType(
                        modulus="infinity",
                        modular_value="5",
                        minimum_value="5",
                        maximum_value="5",
                    )
                )
            )
        )

    def test_is_constant_boolean_type(self):
        self.assertFalse(
            ir_util.is_constant_type(
                ir_data.ExpressionType(boolean=ir_data.BooleanType())
            )
        )
        self.assertTrue(
            ir_util.is_constant_type(
                ir_data.ExpressionType(boolean=ir_data.BooleanType(value=True))
            )
        )
        self.assertTrue(
            ir_util.is_constant_type(
                ir_data.ExpressionType(boolean=ir_data.BooleanType(value=False))
            )
        )

    def test_is_constant_enumeration_type(self):
        self.assertFalse(
            ir_util.is_constant_type(
                ir_data.ExpressionType(enumeration=ir_data.EnumType())
            )
        )
        self.assertTrue(
            ir_util.is_constant_type(
                ir_data.ExpressionType(enumeration=ir_data.EnumType(value="0"))
            )
        )

    def test_is_constant_opaque_type(self):
        self.assertFalse(
            ir_util.is_constant_type(
                ir_data.ExpressionType(opaque=ir_data.OpaqueType())
            )
        )

    def test_constant_value_of_integer(self):
        self.assertEqual(6, ir_util.constant_value(_parse_expression("6")))

    def test_constant_value_of_none(self):
        self.assertIsNone(ir_util.constant_value(ir_data.Expression()))

    def test_constant_value_of_addition(self):
        self.assertEqual(6, ir_util.constant_value(_parse_expression("2+4")))

    def test_constant_value_of_subtraction(self):
        self.assertEqual(-2, ir_util.constant_value(_parse_expression("2-4")))

    def test_constant_value_of_multiplication(self):
        self.assertEqual(8, ir_util.constant_value(_parse_expression("2*4")))

    def test_constant_value_of_equality(self):
        self.assertFalse(ir_util.constant_value(_parse_expression("2 == 4")))

    def test_constant_value_of_inequality(self):
        self.assertTrue(ir_util.constant_value(_parse_expression("2 != 4")))

    def test_constant_value_of_less(self):
        self.assertTrue(ir_util.constant_value(_parse_expression("2 < 4")))

    def test_constant_value_of_less_or_equal(self):
        self.assertTrue(ir_util.constant_value(_parse_expression("2 <= 4")))

    def test_constant_value_of_greater(self):
        self.assertFalse(ir_util.constant_value(_parse_expression("2 > 4")))

    def test_constant_value_of_greater_or_equal(self):
        self.assertFalse(ir_util.constant_value(_parse_expression("2 >= 4")))

    def test_constant_value_of_and(self):
        self.assertFalse(ir_util.constant_value(_parse_expression("true && false")))
        self.assertTrue(ir_util.constant_value(_parse_expression("true && true")))

    def test_constant_value_of_or(self):
        self.assertTrue(ir_util.constant_value(_parse_expression("true || false")))
        self.assertFalse(ir_util.constant_value(_parse_expression("false || false")))

    def test_constant_value_of_choice(self):
        self.assertEqual(
            10, ir_util.constant_value(_parse_expression("false ? 20 : 10"))
        )
        self.assertEqual(
            20, ir_util.constant_value(_parse_expression("true ? 20 : 10"))
        )

    def test_constant_value_of_choice_with_unknown_other_branch(self):
        self.assertEqual(
            10, ir_util.constant_value(_parse_expression("false ? foo : 10"))
        )
        self.assertEqual(
            20, ir_util.constant_value(_parse_expression("true ? 20 : foo"))
        )

    def test_constant_value_of_maximum(self):
        self.assertEqual(10, ir_util.constant_value(_parse_expression("$max(5, 10)")))
        self.assertEqual(10, ir_util.constant_value(_parse_expression("$max(10)")))
        self.assertEqual(
            10, ir_util.constant_value(_parse_expression("$max(5, 9, 7, 10, 6, -100)"))
        )

    def test_constant_value_of_boolean(self):
        self.assertTrue(ir_util.constant_value(_parse_expression("true")))
        self.assertFalse(ir_util.constant_value(_parse_expression("false")))

    def test_constant_value_of_enum(self):
        self.assertEqual(
            12,
            ir_util.constant_value(
                ir_data.Expression(
                    constant_reference=ir_data.Reference(),
                    type=ir_data.ExpressionType(
                        enumeration=ir_data.EnumType(value="12")
                    ),
                )
            ),
        )

    def test_constant_value_of_integer_reference(self):
        self.assertEqual(
            12,
            ir_util.constant_value(
                ir_data.Expression(
                    constant_reference=ir_data.Reference(),
                    type=ir_data.ExpressionType(
                        integer=ir_data.IntegerType(
                            modulus="infinity", modular_value="12"
                        )
                    ),
                )
            ),
        )

    def test_constant_value_of_boolean_reference(self):
        self.assertTrue(
            ir_util.constant_value(
                ir_data.Expression(
                    constant_reference=ir_data.Reference(),
                    type=ir_data.ExpressionType(
                        boolean=ir_data.BooleanType(value=True)
                    ),
                )
            )
        )

    def test_constant_value_of_builtin_reference(self):
        self.assertEqual(
            12,
            ir_util.constant_value(
                ir_data.Expression(
                    builtin_reference=ir_data.Reference(
                        canonical_name=ir_data.CanonicalName(object_path=["$foo"])
                    )
                ),
                {"$foo": 12},
            ),
        )

    def test_constant_value_of_field_reference(self):
        self.assertIsNone(ir_util.constant_value(_parse_expression("foo")))

    def test_constant_value_of_missing_builtin_reference(self):
        self.assertIsNone(
            ir_util.constant_value(
                _parse_expression("$static_size_in_bits"), {"$bar": 12}
            )
        )

    def test_constant_value_of_present_builtin_reference(self):
        self.assertEqual(
            12,
            ir_util.constant_value(
                _parse_expression("$static_size_in_bits"), {"$static_size_in_bits": 12}
            ),
        )

    def test_constant_false_value_of_operator_and_with_missing_value(self):
        self.assertIs(
            False,
            ir_util.constant_value(_parse_expression("false && foo"), {"bar": 12}),
        )
        self.assertIs(
            False,
            ir_util.constant_value(_parse_expression("foo && false"), {"bar": 12}),
        )

    def test_constant_false_value_of_operator_and_known_value(self):
        self.assertTrue(
            ir_util.constant_value(
                _parse_expression("true && $is_statically_sized"),
                {"$is_statically_sized": True},
            )
        )

    def test_constant_none_value_of_operator_and_with_missing_value(self):
        self.assertIsNone(
            ir_util.constant_value(_parse_expression("true && foo"), {"bar": 12})
        )
        self.assertIsNone(
            ir_util.constant_value(_parse_expression("foo && true"), {"bar": 12})
        )

    def test_constant_false_value_of_operator_or_with_missing_value(self):
        self.assertTrue(
            ir_util.constant_value(_parse_expression("true || foo"), {"bar": 12})
        )
        self.assertTrue(
            ir_util.constant_value(_parse_expression("foo || true"), {"bar": 12})
        )

    def test_constant_none_value_of_operator_or_with_missing_value(self):
        self.assertIsNone(
            ir_util.constant_value(_parse_expression("foo || false"), {"bar": 12})
        )
        self.assertIsNone(
            ir_util.constant_value(_parse_expression("false || foo"), {"bar": 12})
        )

    def test_constant_value_of_operator_plus_with_missing_value(self):
        self.assertIsNone(
            ir_util.constant_value(_parse_expression("12 + foo"), {"bar": 12})
        )

    def test_is_array(self):
        self.assertTrue(ir_util.is_array(ir_data.Type(array_type=ir_data.ArrayType())))
        self.assertFalse(
            ir_util.is_array(ir_data.Type(atomic_type=ir_data.AtomicType()))
        )

    def test_get_attribute(self):
        type_def = ir_data.TypeDefinition(
            attribute=[
                ir_data.Attribute(
                    value=ir_data.AttributeValue(expression=ir_data.Expression()),
                    name=ir_data.Word(text="phil"),
                ),
                ir_data.Attribute(
                    value=ir_data.AttributeValue(expression=_parse_expression("false")),
                    name=ir_data.Word(text="bob"),
                    is_default=True,
                ),
                ir_data.Attribute(
                    value=ir_data.AttributeValue(expression=_parse_expression("true")),
                    name=ir_data.Word(text="bob"),
                ),
                ir_data.Attribute(
                    value=ir_data.AttributeValue(expression=_parse_expression("false")),
                    name=ir_data.Word(text="bob2"),
                ),
                ir_data.Attribute(
                    value=ir_data.AttributeValue(expression=_parse_expression("true")),
                    name=ir_data.Word(text="bob2"),
                    is_default=True,
                ),
                ir_data.Attribute(
                    value=ir_data.AttributeValue(expression=_parse_expression("false")),
                    name=ir_data.Word(text="bob3"),
                    is_default=True,
                ),
                ir_data.Attribute(
                    value=ir_data.AttributeValue(expression=_parse_expression("false")),
                    name=ir_data.Word(),
                ),
            ]
        )
        self.assertEqual(
            ir_data.AttributeValue(expression=_parse_expression("true")),
            ir_util.get_attribute(type_def.attribute, "bob"),
        )
        self.assertEqual(
            ir_data.AttributeValue(expression=_parse_expression("false")),
            ir_util.get_attribute(type_def.attribute, "bob2"),
        )
        self.assertEqual(None, ir_util.get_attribute(type_def.attribute, "Bob"))
        self.assertEqual(None, ir_util.get_attribute(type_def.attribute, "bob3"))

    def test_get_boolean_attribute(self):
        type_def = ir_data.TypeDefinition(
            attribute=[
                ir_data.Attribute(
                    value=ir_data.AttributeValue(expression=ir_data.Expression()),
                    name=ir_data.Word(text="phil"),
                ),
                ir_data.Attribute(
                    value=ir_data.AttributeValue(expression=_parse_expression("false")),
                    name=ir_data.Word(text="bob"),
                    is_default=True,
                ),
                ir_data.Attribute(
                    value=ir_data.AttributeValue(expression=_parse_expression("true")),
                    name=ir_data.Word(text="bob"),
                ),
                ir_data.Attribute(
                    value=ir_data.AttributeValue(expression=_parse_expression("false")),
                    name=ir_data.Word(text="bob2"),
                ),
                ir_data.Attribute(
                    value=ir_data.AttributeValue(expression=_parse_expression("true")),
                    name=ir_data.Word(text="bob2"),
                    is_default=True,
                ),
                ir_data.Attribute(
                    value=ir_data.AttributeValue(expression=_parse_expression("false")),
                    name=ir_data.Word(text="bob3"),
                    is_default=True,
                ),
                ir_data.Attribute(
                    value=ir_data.AttributeValue(expression=_parse_expression("false")),
                    name=ir_data.Word(),
                ),
            ]
        )
        self.assertTrue(ir_util.get_boolean_attribute(type_def.attribute, "bob"))
        self.assertTrue(
            ir_util.get_boolean_attribute(
                type_def.attribute, "bob", default_value=False
            )
        )
        self.assertFalse(ir_util.get_boolean_attribute(type_def.attribute, "bob2"))
        self.assertFalse(
            ir_util.get_boolean_attribute(
                type_def.attribute, "bob2", default_value=True
            )
        )
        self.assertIsNone(ir_util.get_boolean_attribute(type_def.attribute, "Bob"))
        self.assertTrue(
            ir_util.get_boolean_attribute(type_def.attribute, "Bob", default_value=True)
        )
        self.assertIsNone(ir_util.get_boolean_attribute(type_def.attribute, "bob3"))

    def test_get_integer_attribute(self):
        type_def = ir_data.TypeDefinition(
            attribute=[
                ir_data.Attribute(
                    value=ir_data.AttributeValue(
                        expression=ir_data.Expression(
                            type=ir_data.ExpressionType(integer=ir_data.IntegerType())
                        )
                    ),
                    name=ir_data.Word(text="phil"),
                ),
                ir_data.Attribute(
                    value=ir_data.AttributeValue(
                        expression=ir_data.Expression(
                            constant=ir_data.NumericConstant(value="20"),
                            type=ir_data.ExpressionType(
                                integer=ir_data.IntegerType(
                                    modular_value="20", modulus="infinity"
                                )
                            ),
                        )
                    ),
                    name=ir_data.Word(text="bob"),
                    is_default=True,
                ),
                ir_data.Attribute(
                    value=ir_data.AttributeValue(
                        expression=ir_data.Expression(
                            constant=ir_data.NumericConstant(value="10"),
                            type=ir_data.ExpressionType(
                                integer=ir_data.IntegerType(
                                    modular_value="10", modulus="infinity"
                                )
                            ),
                        )
                    ),
                    name=ir_data.Word(text="bob"),
                ),
                ir_data.Attribute(
                    value=ir_data.AttributeValue(
                        expression=ir_data.Expression(
                            constant=ir_data.NumericConstant(value="5"),
                            type=ir_data.ExpressionType(
                                integer=ir_data.IntegerType(
                                    modular_value="5", modulus="infinity"
                                )
                            ),
                        )
                    ),
                    name=ir_data.Word(text="bob2"),
                ),
                ir_data.Attribute(
                    value=ir_data.AttributeValue(
                        expression=ir_data.Expression(
                            constant=ir_data.NumericConstant(value="0"),
                            type=ir_data.ExpressionType(
                                integer=ir_data.IntegerType(
                                    modular_value="0", modulus="infinity"
                                )
                            ),
                        )
                    ),
                    name=ir_data.Word(text="bob2"),
                    is_default=True,
                ),
                ir_data.Attribute(
                    value=ir_data.AttributeValue(
                        expression=ir_data.Expression(
                            constant=ir_data.NumericConstant(value="30"),
                            type=ir_data.ExpressionType(
                                integer=ir_data.IntegerType(
                                    modular_value="30", modulus="infinity"
                                )
                            ),
                        )
                    ),
                    name=ir_data.Word(text="bob3"),
                    is_default=True,
                ),
                ir_data.Attribute(
                    value=ir_data.AttributeValue(
                        expression=ir_data.Expression(
                            function=ir_data.Function(
                                function=ir_data.FunctionMapping.ADDITION,
                                args=[
                                    ir_data.Expression(
                                        constant=ir_data.NumericConstant(value="100"),
                                        type=ir_data.ExpressionType(
                                            integer=ir_data.IntegerType(
                                                modular_value="100", modulus="infinity"
                                            )
                                        ),
                                    ),
                                    ir_data.Expression(
                                        constant=ir_data.NumericConstant(value="100"),
                                        type=ir_data.ExpressionType(
                                            integer=ir_data.IntegerType(
                                                modular_value="100", modulus="infinity"
                                            )
                                        ),
                                    ),
                                ],
                            ),
                            type=ir_data.ExpressionType(
                                integer=ir_data.IntegerType(
                                    modular_value="200", modulus="infinity"
                                )
                            ),
                        )
                    ),
                    name=ir_data.Word(text="bob4"),
                ),
                ir_data.Attribute(
                    value=ir_data.AttributeValue(
                        expression=ir_data.Expression(
                            constant=ir_data.NumericConstant(value="40"),
                            type=ir_data.ExpressionType(
                                integer=ir_data.IntegerType(
                                    modular_value="40", modulus="infinity"
                                )
                            ),
                        )
                    ),
                    name=ir_data.Word(),
                ),
            ]
        )
        self.assertEqual(10, ir_util.get_integer_attribute(type_def.attribute, "bob"))
        self.assertEqual(5, ir_util.get_integer_attribute(type_def.attribute, "bob2"))
        self.assertIsNone(ir_util.get_integer_attribute(type_def.attribute, "Bob"))
        self.assertEqual(
            10,
            ir_util.get_integer_attribute(type_def.attribute, "Bob", default_value=10),
        )
        self.assertIsNone(ir_util.get_integer_attribute(type_def.attribute, "bob3"))
        self.assertEqual(200, ir_util.get_integer_attribute(type_def.attribute, "bob4"))

    def test_get_duplicate_attribute(self):
        type_def = ir_data.TypeDefinition(
            attribute=[
                ir_data.Attribute(
                    value=ir_data.AttributeValue(expression=ir_data.Expression()),
                    name=ir_data.Word(text="phil"),
                ),
                ir_data.Attribute(
                    value=ir_data.AttributeValue(expression=_parse_expression("true")),
                    name=ir_data.Word(text="bob"),
                ),
                ir_data.Attribute(
                    value=ir_data.AttributeValue(expression=_parse_expression("false")),
                    name=ir_data.Word(text="bob"),
                ),
                ir_data.Attribute(
                    value=ir_data.AttributeValue(expression=_parse_expression("false")),
                    name=ir_data.Word(),
                ),
            ]
        )
        self.assertRaises(
            AssertionError, ir_util.get_attribute, type_def.attribute, "bob"
        )

    def test_find_object(self):
        ir = ir_data_utils.IrDataSerializer.from_json(
            ir_data.EmbossIr,
            """{
          "module": [
            {
              "type": [
                {
                  "structure": {
                    "field": [
                      {
                        "name": {
                          "name": { "text": "field" },
                          "canonical_name": {
                            "module_file": "test.emb",
                            "object_path": [ "Foo", "field" ]
                          }
                        }
                      }
                    ]
                  },
                  "name": {
                    "name": { "text": "Foo" },
                    "canonical_name": {
                      "module_file": "test.emb",
                      "object_path": [ "Foo" ]
                    }
                  },
                  "runtime_parameter": [
                    {
                      "name": {
                        "name": { "text": "parameter" },
                        "canonical_name": {
                          "module_file": "test.emb",
                          "object_path": [ "Foo", "parameter" ]
                        }
                      }
                    }
                  ]
                },
                {
                  "enumeration": {
                    "value": [
                      {
                        "name": {
                          "name": { "text": "QUX" },
                          "canonical_name": {
                            "module_file": "test.emb",
                            "object_path": [ "Bar", "QUX" ]
                          }
                        }
                      }
                    ]
                  },
                  "name": {
                    "name": { "text": "Bar" },
                    "canonical_name": {
                      "module_file": "test.emb",
                      "object_path": [ "Bar" ]
                    }
                  }
                }
              ],
              "source_file_name": "test.emb"
            },
            {
              "type": [
                {
                  "external": {},
                  "name": {
                    "name": { "text": "UInt" },
                    "canonical_name": {
                      "module_file": "",
                      "object_path": [ "UInt" ]
                    }
                  }
                }
              ],
              "source_file_name": ""
            }
          ]
        }""",
        )

        # Test that find_object works with any of its four "name" types.
        canonical_name_of_foo = ir_data.CanonicalName(
            module_file="test.emb", object_path=["Foo"]
        )
        self.assertEqual(
            ir.module[0].type[0],
            ir_util.find_object(
                ir_data.Reference(canonical_name=canonical_name_of_foo), ir
            ),
        )
        self.assertEqual(
            ir.module[0].type[0],
            ir_util.find_object(
                ir_data.NameDefinition(canonical_name=canonical_name_of_foo), ir
            ),
        )
        self.assertEqual(
            ir.module[0].type[0], ir_util.find_object(canonical_name_of_foo, ir)
        )
        self.assertEqual(
            ir.module[0].type[0], ir_util.find_object(("test.emb", "Foo"), ir)
        )

        # Test that find_object works with objects other than structs.
        self.assertEqual(
            ir.module[0].type[1], ir_util.find_object(("test.emb", "Bar"), ir)
        )
        self.assertEqual(ir.module[1].type[0], ir_util.find_object(("", "UInt"), ir))
        self.assertEqual(
            ir.module[0].type[0].structure.field[0],
            ir_util.find_object(("test.emb", "Foo", "field"), ir),
        )
        self.assertEqual(
            ir.module[0].type[0].runtime_parameter[0],
            ir_util.find_object(("test.emb", "Foo", "parameter"), ir),
        )
        self.assertEqual(
            ir.module[0].type[1].enumeration.value[0],
            ir_util.find_object(("test.emb", "Bar", "QUX"), ir),
        )
        self.assertEqual(ir.module[0], ir_util.find_object(("test.emb",), ir))
        self.assertEqual(ir.module[1], ir_util.find_object(("",), ir))

        # Test searching for non-present objects.
        self.assertIsNone(ir_util.find_object_or_none(("not_test.emb",), ir))
        self.assertIsNone(ir_util.find_object_or_none(("test.emb", "NotFoo"), ir))
        self.assertIsNone(
            ir_util.find_object_or_none(("test.emb", "Foo", "not_field"), ir)
        )
        self.assertIsNone(
            ir_util.find_object_or_none(("test.emb", "Foo", "field", "no_subfield"), ir)
        )
        self.assertIsNone(
            ir_util.find_object_or_none(("test.emb", "Bar", "NOT_QUX"), ir)
        )
        self.assertIsNone(
            ir_util.find_object_or_none(("test.emb", "Bar", "QUX", "no_subenum"), ir)
        )

        # Test that find_parent_object works with any of its four "name" types.
        self.assertEqual(
            ir.module[0],
            ir_util.find_parent_object(
                ir_data.Reference(canonical_name=canonical_name_of_foo), ir
            ),
        )
        self.assertEqual(
            ir.module[0],
            ir_util.find_parent_object(
                ir_data.NameDefinition(canonical_name=canonical_name_of_foo), ir
            ),
        )
        self.assertEqual(
            ir.module[0], ir_util.find_parent_object(canonical_name_of_foo, ir)
        )
        self.assertEqual(
            ir.module[0], ir_util.find_parent_object(("test.emb", "Foo"), ir)
        )

        # Test that find_parent_object works with objects other than structs.
        self.assertEqual(
            ir.module[0], ir_util.find_parent_object(("test.emb", "Bar"), ir)
        )
        self.assertEqual(ir.module[1], ir_util.find_parent_object(("", "UInt"), ir))
        self.assertEqual(
            ir.module[0].type[0],
            ir_util.find_parent_object(("test.emb", "Foo", "field"), ir),
        )
        self.assertEqual(
            ir.module[0].type[1],
            ir_util.find_parent_object(("test.emb", "Bar", "QUX"), ir),
        )

    def test_hashable_form_of_reference(self):
        self.assertEqual(
            ("t.emb", "Foo", "Bar"),
            ir_util.hashable_form_of_reference(
                ir_data.Reference(
                    canonical_name=ir_data.CanonicalName(
                        module_file="t.emb", object_path=["Foo", "Bar"]
                    )
                )
            ),
        )
        self.assertEqual(
            ("t.emb", "Foo", "Bar"),
            ir_util.hashable_form_of_reference(
                ir_data.NameDefinition(
                    canonical_name=ir_data.CanonicalName(
                        module_file="t.emb", object_path=["Foo", "Bar"]
                    )
                )
            ),
        )

    def test_get_base_type(self):
        array_type_ir = ir_data_utils.IrDataSerializer.from_json(
            ir_data.Type,
            """{
          "array_type": {
            "element_count": { "constant": { "value": "20" } },
            "base_type": {
              "array_type": {
                "element_count": { "constant": { "value": "10" } },
                "base_type": {
                  "atomic_type": {
                    "reference": { },
                    "source_location": { "start": { "line": 5 } }
                  }
                },
                "source_location": { "start": { "line": 4 } }
              }
            },
            "source_location": { "start": { "line": 3 } }
          }
        }""",
        )
        base_type_ir = array_type_ir.array_type.base_type.array_type.base_type
        self.assertEqual(base_type_ir, ir_util.get_base_type(array_type_ir))
        self.assertEqual(
            base_type_ir, ir_util.get_base_type(array_type_ir.array_type.base_type)
        )
        self.assertEqual(base_type_ir, ir_util.get_base_type(base_type_ir))

    def test_size_of_type_in_bits(self):
        ir = ir_data_utils.IrDataSerializer.from_json(
            ir_data.EmbossIr,
            """{
          "module": [{
            "type": [{
              "name": {
                "name": { "text": "Baz" },
                "canonical_name": {
                  "module_file": "s.emb",
                  "object_path": ["Baz"]
                }
              }
            }],
            "source_file_name": "s.emb"
          },
          {
            "type": [{
              "name": {
                "name": { "text": "UInt" },
                "canonical_name": {
                  "module_file": "",
                  "object_path": ["UInt"]
                }
              }
            },
            {
              "name": {
                "name": { "text": "Byte" },
                "canonical_name": {
                  "module_file": "",
                  "object_path": ["Byte"]
                }
              },
              "attribute": [{
                "name": { "text": "fixed_size_in_bits" },
                "value": {
                  "expression": {
                    "constant": { "value": "8" },
                    "type": {
                      "integer": { "modular_value": "8", "modulus": "infinity" }
                    }
                  }
                }
              }]
            }],
            "source_file_name": ""
          }]
        }""",
        )

        fixed_size_type = ir_data_utils.IrDataSerializer.from_json(
            ir_data.Type,
            """{
          "atomic_type": {
            "reference": {
              "canonical_name": { "module_file": "", "object_path": ["Byte"] }
             }
          }
        }""",
        )
        self.assertEqual(8, ir_util.fixed_size_of_type_in_bits(fixed_size_type, ir))

        explicit_size_type = ir_data_utils.IrDataSerializer.from_json(
            ir_data.Type,
            """{
          "atomic_type": {
            "reference": {
              "canonical_name": { "module_file": "", "object_path": ["UInt"] }
            }
          },
          "size_in_bits": {
            "constant": { "value": "32" },
            "type": {
              "integer": { "modular_value": "32", "modulus": "infinity" }
            }
          }
        }""",
        )
        self.assertEqual(32, ir_util.fixed_size_of_type_in_bits(explicit_size_type, ir))

        fixed_size_array = ir_data_utils.IrDataSerializer.from_json(
            ir_data.Type,
            """{
          "array_type": {
            "base_type": {
              "atomic_type": {
                "reference": {
                  "canonical_name": { "module_file": "", "object_path": ["Byte"] }
                }
              }
            },
            "element_count": {
              "constant": { "value": "5" },
              "type": {
                "integer": { "modular_value": "5", "modulus": "infinity" }
              }
            }
          }
        }""",
        )
        self.assertEqual(40, ir_util.fixed_size_of_type_in_bits(fixed_size_array, ir))

        fixed_size_2d_array = ir_data_utils.IrDataSerializer.from_json(
            ir_data.Type,
            """{
          "array_type": {
            "base_type": {
              "array_type": {
                "base_type": {
                  "atomic_type": {
                    "reference": {
                      "canonical_name": {
                        "module_file": "",
                        "object_path": ["Byte"]
                      }
                    }
                  }
                },
                "element_count": {
                  "constant": { "value": "5" },
                  "type": {
                    "integer": { "modular_value": "5", "modulus": "infinity" }
                  }
                }
              }
            },
            "element_count": {
              "constant": { "value": "2" },
              "type": {
                "integer": { "modular_value": "2", "modulus": "infinity" }
              }
            }
          }
        }""",
        )
        self.assertEqual(
            80, ir_util.fixed_size_of_type_in_bits(fixed_size_2d_array, ir)
        )

        automatic_size_array = ir_data_utils.IrDataSerializer.from_json(
            ir_data.Type,
            """{
          "array_type": {
            "base_type": {
              "array_type": {
                "base_type": {
                  "atomic_type": {
                    "reference": {
                      "canonical_name": {
                        "module_file": "",
                        "object_path": ["Byte"]
                      }
                    }
                  }
                },
                "element_count": {
                  "constant": { "value": "5" },
                  "type": {
                    "integer": { "modular_value": "5", "modulus": "infinity" }
                  }
                }
              }
            },
            "automatic": { }
          }
      }""",
        )
        self.assertIsNone(ir_util.fixed_size_of_type_in_bits(automatic_size_array, ir))

        variable_size_type = ir_data_utils.IrDataSerializer.from_json(
            ir_data.Type,
            """{
          "atomic_type": {
            "reference": {
              "canonical_name": { "module_file": "", "object_path": ["UInt"] }
            }
          }
        }""",
        )
        self.assertIsNone(ir_util.fixed_size_of_type_in_bits(variable_size_type, ir))

        no_size_type = ir_data_utils.IrDataSerializer.from_json(
            ir_data.Type,
            """{
          "atomic_type": {
            "reference": {
              "canonical_name": {
                "module_file": "s.emb",
                "object_path": ["Baz"]
              }
            }
          }
        }""",
        )
        self.assertIsNone(ir_util.fixed_size_of_type_in_bits(no_size_type, ir))

    def test_field_is_virtual(self):
        self.assertTrue(ir_util.field_is_virtual(ir_data.Field()))

    def test_field_is_not_virtual(self):
        self.assertFalse(
            ir_util.field_is_virtual(ir_data.Field(location=ir_data.FieldLocation()))
        )

    def test_field_is_read_only(self):
        self.assertTrue(
            ir_util.field_is_read_only(
                ir_data.Field(write_method=ir_data.WriteMethod(read_only=True))
            )
        )

    def test_field_is_not_read_only(self):
        self.assertFalse(
            ir_util.field_is_read_only(ir_data.Field(location=ir_data.FieldLocation()))
        )
        self.assertFalse(
            ir_util.field_is_read_only(
                ir_data.Field(write_method=ir_data.WriteMethod())
            )
        )


if __name__ == "__main__":
    unittest.main()
