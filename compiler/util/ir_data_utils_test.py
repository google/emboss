# Copyright 2024 Google LLC
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

"""Tests for util.ir_data_utils."""

import dataclasses
import enum
import sys
from typing import Optional
import unittest
from compiler.util import expression_parser
from compiler.util import ir_data
from compiler.util import ir_data_fields
from compiler.util import ir_data_utils


class TestEnum(enum.Enum):
    """Used to test python Enum handling."""

    UNKNOWN = 0
    VALUE_1 = 1
    VALUE_2 = 2


@dataclasses.dataclass
class Opaque(ir_data.Message):
    """Used for testing data field helpers."""


@dataclasses.dataclass
class ClassWithUnion(ir_data.Message):
    """Used for testing data field helpers."""

    opaque: Optional[Opaque] = ir_data_fields.oneof_field("type")
    integer: Optional[int] = ir_data_fields.oneof_field("type")
    boolean: Optional[bool] = ir_data_fields.oneof_field("type")
    enumeration: Optional[TestEnum] = ir_data_fields.oneof_field("type")
    non_union_field: int = 0


@dataclasses.dataclass
class ClassWithTwoUnions(ir_data.Message):
    """Used for testing data field helpers."""

    opaque: Optional[Opaque] = ir_data_fields.oneof_field("type_1")
    integer: Optional[int] = ir_data_fields.oneof_field("type_1")
    boolean: Optional[bool] = ir_data_fields.oneof_field("type_2")
    enumeration: Optional[TestEnum] = ir_data_fields.oneof_field("type_2")
    non_union_field: int = 0
    seq_field: list[int] = ir_data_fields.list_field(int)


class IrDataUtilsTest(unittest.TestCase):
    """Tests for the miscellaneous utility functions in ir_data_utils.py."""

    def test_field_specs(self):
        """Tests the `field_specs` method."""
        fields = ir_data_utils.field_specs(ir_data.TypeDefinition)
        self.assertIsNotNone(fields)
        expected_fields = (
            "external",
            "enumeration",
            "structure",
            "name",
            "attribute",
            "documentation",
            "subtype",
            "addressable_unit",
            "runtime_parameter",
            "source_location",
        )
        self.assertEqual(len(fields), len(expected_fields))
        field_names = fields.keys()
        for k in expected_fields:
            self.assertIn(k, field_names)

        # Try a sequence
        expected_field = ir_data_fields.make_field_spec(
            "attribute", ir_data.Attribute, ir_data_fields.FieldContainer.LIST, None
        )
        self.assertEqual(fields["attribute"], expected_field)

        # Try a scalar
        expected_field = ir_data_fields.make_field_spec(
            "addressable_unit",
            ir_data.AddressableUnit,
            ir_data_fields.FieldContainer.OPTIONAL,
            None,
        )
        self.assertEqual(fields["addressable_unit"], expected_field)

        # Try a IR data class
        expected_field = ir_data_fields.make_field_spec(
            "source_location",
            ir_data.Location,
            ir_data_fields.FieldContainer.OPTIONAL,
            None,
        )
        self.assertEqual(fields["source_location"], expected_field)

        # Try an oneof field
        expected_field = ir_data_fields.make_field_spec(
            "external",
            ir_data.External,
            ir_data_fields.FieldContainer.OPTIONAL,
            oneof="type",
        )
        self.assertEqual(fields["external"], expected_field)

        # Try non-optional scalar
        fields = ir_data_utils.field_specs(ir_data.Position)
        expected_field = ir_data_fields.make_field_spec(
            "line", int, ir_data_fields.FieldContainer.NONE, None
        )
        self.assertEqual(fields["line"], expected_field)

        fields = ir_data_utils.field_specs(ir_data.ArrayType)
        expected_field = ir_data_fields.make_field_spec(
            "base_type", ir_data.Type, ir_data_fields.FieldContainer.OPTIONAL, None
        )
        self.assertEqual(fields["base_type"], expected_field)

    def test_is_sequence(self):
        """Tests for the `FieldSpec.is_sequence` helper."""
        type_def = ir_data.TypeDefinition(
            attribute=[
                ir_data.Attribute(
                    value=ir_data.AttributeValue(expression=ir_data.Expression()),
                    name=ir_data.Word(text="phil"),
                ),
            ]
        )
        fields = ir_data_utils.field_specs(ir_data.TypeDefinition)
        # Test against a repeated field
        self.assertTrue(fields["attribute"].is_sequence)
        # Test against a nested IR data type
        self.assertFalse(fields["name"].is_sequence)
        # Test against a plain scalar type
        fields = ir_data_utils.field_specs(type_def.attribute[0])
        self.assertFalse(fields["is_default"].is_sequence)

    def test_is_dataclass(self):
        """Tests FieldSpec.is_dataclass against ir_data."""
        type_def = ir_data.TypeDefinition(
            attribute=[
                ir_data.Attribute(
                    value=ir_data.AttributeValue(expression=ir_data.Expression()),
                    name=ir_data.Word(text="phil"),
                ),
            ]
        )
        fields = ir_data_utils.field_specs(ir_data.TypeDefinition)
        # Test against a repeated field that holds IR data structs
        self.assertTrue(fields["attribute"].is_dataclass)
        # Test against a nested IR data type
        self.assertTrue(fields["name"].is_dataclass)
        # Test against a plain scalar type
        fields = ir_data_utils.field_specs(type_def.attribute[0])
        self.assertFalse(fields["is_default"].is_dataclass)
        # Test against a repeated field that holds scalars
        fields = ir_data_utils.field_specs(ir_data.Structure)
        self.assertFalse(fields["fields_in_dependency_order"].is_dataclass)

    def test_get_set_fields(self):
        """Tests that get set fields works."""
        type_def = ir_data.TypeDefinition(
            attribute=[
                ir_data.Attribute(
                    value=ir_data.AttributeValue(expression=ir_data.Expression()),
                    name=ir_data.Word(text="phil"),
                ),
            ]
        )
        set_fields = ir_data_utils.get_set_fields(type_def)
        expected_fields = set(
            ["attribute", "documentation", "subtype", "runtime_parameter"]
        )
        self.assertEqual(len(set_fields), len(expected_fields))
        found_fields = set()
        for k, v in set_fields:
            self.assertIn(k.name, expected_fields)
            found_fields.add(k.name)
            self.assertEqual(v, getattr(type_def, k.name))

        self.assertSetEqual(found_fields, expected_fields)

    def test_copy(self):
        """Tests the `copy` helper."""
        attribute = ir_data.Attribute(
            value=ir_data.AttributeValue(expression=ir_data.Expression()),
            name=ir_data.Word(text="phil"),
        )
        attribute_copy = ir_data_utils.copy(attribute)

        # Should be equivalent
        self.assertEqual(attribute, attribute_copy)
        # But not the same instance
        self.assertIsNot(attribute, attribute_copy)

        # Let's do a sequence
        type_def = ir_data.TypeDefinition(attribute=[attribute])
        type_def_copy = ir_data_utils.copy(type_def)

        # Should be equivalent
        self.assertEqual(type_def, type_def_copy)
        # But not the same instance
        self.assertIsNot(type_def, type_def_copy)
        self.assertIsNot(type_def.attribute, type_def_copy.attribute)

    def test_update(self):
        """Tests the `update` helper."""
        attribute_template = ir_data.Attribute(
            value=ir_data.AttributeValue(expression=ir_data.Expression()),
            name=ir_data.Word(text="phil"),
        )
        attribute = ir_data.Attribute(is_default=True)
        ir_data_utils.update(attribute, attribute_template)
        self.assertIsNotNone(attribute.value)
        self.assertIsNot(attribute.value, attribute_template.value)
        self.assertIsNotNone(attribute.name)
        self.assertIsNot(attribute.name, attribute_template.name)

        # Value not present in template should be untouched
        self.assertTrue(attribute.is_default)


class IrDataBuilderTest(unittest.TestCase):
    """Tests for IrDataBuilder."""

    def assertEmpty(self, obj):
        self.assertEqual(len(obj), 0, msg=f"{obj} is not empty.")

    def assertLen(self, obj, length):
        self.assertEqual(len(obj), length, msg=f"{obj} has length {len(obj)}.")

    def test_ir_data_builder(self):
        """Tests that basic builder chains work."""
        # We start with an empty type
        type_def = ir_data.TypeDefinition()
        self.assertFalse(type_def.HasField("name"))
        self.assertIsNone(type_def.name)

        # Now setup a builder
        builder = ir_data_utils.builder(type_def)

        # Assign to a sub-child
        builder.name.name = ir_data.Word(text="phil")

        # Verify the wrapped struct is updated
        self.assertIsNotNone(type_def.name)
        self.assertIsNotNone(type_def.name.name)
        self.assertIsNotNone(type_def.name.name.text)
        self.assertEqual(type_def.name.name.text, "phil")

    def test_ir_data_builder_bad_field(self):
        """Tests accessing an undefined field name fails."""
        type_def = ir_data.TypeDefinition()
        builder = ir_data_utils.builder(type_def)
        self.assertRaises(AttributeError, lambda: builder.foo)
        # Make sure it's not set on our IR data class either
        self.assertRaises(AttributeError, getattr, type_def, "foo")

    def test_ir_data_builder_sequence(self):
        """Tests that sequences are properly wrapped."""
        # We start with an empty type
        type_def = ir_data.TypeDefinition()
        self.assertTrue(type_def.HasField("attribute"))
        self.assertEmpty(type_def.attribute)

        # Now setup a builder
        builder = ir_data_utils.builder(type_def)

        # Assign to a sequence
        attribute = ir_data.Attribute(
            value=ir_data.AttributeValue(expression=ir_data.Expression()),
            name=ir_data.Word(text="phil"),
        )

        builder.attribute.append(attribute)
        self.assertEqual(builder.attribute, [attribute])
        self.assertTrue(type_def.HasField("attribute"))
        self.assertLen(type_def.attribute, 1)
        self.assertEqual(type_def.attribute[0], attribute)

        # Lets make it longer and then try iterating
        builder.attribute.append(attribute)
        self.assertLen(type_def.attribute, 2)
        for attr in builder.attribute:
            # Modify the attributes
            attr.name.text = "bob"

        # Make sure we can build up auto-default entries from a sequence item
        builder.attribute.append(ir_data.Attribute())
        builder.attribute[-1].value.expression = ir_data.Expression()
        builder.attribute[-1].name.text = "bob"

        # Create an attribute to compare against
        new_attribute = ir_data.Attribute(
            value=ir_data.AttributeValue(expression=ir_data.Expression()),
            name=ir_data.Word(text="bob"),
        )

        self.assertLen(type_def.attribute, 3)
        for attr in type_def.attribute:
            self.assertEqual(attr, new_attribute)

        # Make sure the list type is a CopyValuesList
        self.assertIsInstance(
            type_def.attribute,
            ir_data_fields.CopyValuesList,
            f"Instance is: {type(type_def.attribute)}",
        )

    def test_copy_from(self) -> None:
        """Tests that `CopyFrom` works."""
        location = ir_data.Location(
            start=ir_data.Position(line=1, column=1),
            end=ir_data.Position(line=1, column=2),
        )
        expression_ir = ir_data.Expression(source_location=location)
        template: ir_data.Expression = expression_parser.parse("x + y")
        expression = ir_data_utils.builder(expression_ir)
        expression.CopyFrom(template)
        self.assertIsNotNone(expression_ir.function)
        self.assertIsInstance(expression.function, ir_data_utils._IrDataBuilder)
        self.assertIsInstance(
            expression.function.args, ir_data_utils._IrDataSequenceBuilder
        )
        self.assertTrue(expression_ir.function.args)

    def test_copy_from_list(self):
        specs = ir_data_utils.field_specs(ir_data.Function)
        args_spec = specs["args"]
        self.assertTrue(args_spec.is_dataclass)
        template: ir_data.Expression = expression_parser.parse("x + y")
        self.assertIsNotNone(template)
        self.assertIsInstance(template, ir_data.Expression)
        self.assertIsInstance(template.function, ir_data.Function)
        self.assertIsInstance(template.function.args, ir_data_fields.CopyValuesList)

        location = ir_data.Location(
            start=ir_data.Position(line=1, column=1),
            end=ir_data.Position(line=1, column=2),
        )
        expression_ir = ir_data.Expression(source_location=location)
        self.assertIsInstance(expression_ir, ir_data.Expression)
        self.assertIsNone(expression_ir.function)

        expression_builder = ir_data_utils.builder(expression_ir)
        self.assertIsInstance(expression_builder, ir_data_utils._IrDataBuilder)
        expression_builder.CopyFrom(template)
        self.assertIsNotNone(expression_ir.function)
        self.assertIsInstance(expression_ir.function, ir_data.Function)
        self.assertIsNotNone(expression_ir.function.args)
        self.assertIsInstance(
            expression_ir.function.args, ir_data_fields.CopyValuesList
        )

        self.assertIsInstance(expression_builder, ir_data_utils._IrDataBuilder)
        self.assertIsInstance(expression_builder.function, ir_data_utils._IrDataBuilder)
        self.assertIsInstance(
            expression_builder.function.args, ir_data_utils._IrDataSequenceBuilder
        )

    def test_ir_data_builder_sequence_scalar(self):
        """Tests that sequences of scalars function properly."""
        # We start with an empty type
        structure = ir_data.Structure()

        # Now setup a builder
        builder = ir_data_utils.builder(structure)

        # Assign to a scalar sequence
        builder.fields_in_dependency_order.append(12)
        builder.fields_in_dependency_order.append(11)

        self.assertTrue(structure.HasField("fields_in_dependency_order"))
        self.assertLen(structure.fields_in_dependency_order, 2)
        self.assertEqual(structure.fields_in_dependency_order[0], 12)
        self.assertEqual(structure.fields_in_dependency_order[1], 11)
        self.assertEqual(builder.fields_in_dependency_order, [12, 11])

        new_structure = ir_data.Structure(fields_in_dependency_order=[12, 11])
        self.assertEqual(structure, new_structure)

    def test_ir_data_builder_oneof(self):
        value = ir_data.AttributeValue(
            expression=ir_data.Expression(boolean_constant=ir_data.BooleanConstant())
        )
        builder = ir_data_utils.builder(value)
        self.assertTrue(builder.HasField("expression"))
        self.assertFalse(builder.expression.boolean_constant.value)
        builder.expression.boolean_constant.value = True
        self.assertTrue(builder.expression.boolean_constant.value)
        self.assertTrue(value.expression.boolean_constant.value)

        bool_constant = value.expression.boolean_constant
        self.assertIsInstance(bool_constant, ir_data.BooleanConstant)


class IrDataSerializerTest(unittest.TestCase):
    """Tests for IrDataSerializer."""

    def test_ir_data_serializer_to_dict(self):
        """Tests serialization with `IrDataSerializer.to_dict` with default settings."""
        attribute = ir_data.Attribute(
            value=ir_data.AttributeValue(expression=ir_data.Expression()),
            name=ir_data.Word(text="phil"),
        )

        serializer = ir_data_utils.IrDataSerializer(attribute)
        raw_dict = serializer.to_dict()
        expected = {
            "name": {"text": "phil", "source_location": None},
            "value": {
                "expression": {
                    "constant": None,
                    "constant_reference": None,
                    "function": None,
                    "field_reference": None,
                    "boolean_constant": None,
                    "builtin_reference": None,
                    "type": None,
                    "source_location": None,
                },
                "string_constant": None,
                "source_location": None,
            },
            "back_end": None,
            "is_default": None,
            "source_location": None,
        }
        self.assertDictEqual(raw_dict, expected)

    def test_ir_data_serializer_to_dict_exclude_none(self):
        """.Tests serialization with `IrDataSerializer.to_dict` when excluding None values"""
        attribute = ir_data.Attribute(
            value=ir_data.AttributeValue(expression=ir_data.Expression()),
            name=ir_data.Word(text="phil"),
        )
        serializer = ir_data_utils.IrDataSerializer(attribute)
        raw_dict = serializer.to_dict(exclude_none=True)
        expected = {"name": {"text": "phil"}, "value": {"expression": {}}}
        self.assertDictEqual(raw_dict, expected)

    def test_ir_data_serializer_to_dict_enum(self):
        """Tests that serialization of `enum.Enum` values works properly."""
        type_def = ir_data.TypeDefinition(addressable_unit=ir_data.AddressableUnit.BYTE)
        serializer = ir_data_utils.IrDataSerializer(type_def)
        raw_dict = serializer.to_dict(exclude_none=True)
        expected = {"addressable_unit": ir_data.AddressableUnit.BYTE}
        self.assertDictEqual(raw_dict, expected)

    def test_ir_data_serializer_from_dict(self):
        """Tests deserializing IR data from a serialized dict."""
        attribute = ir_data.Attribute(
            value=ir_data.AttributeValue(expression=ir_data.Expression()),
            name=ir_data.Word(text="phil"),
        )
        serializer = ir_data_utils.IrDataSerializer(attribute)
        raw_dict = serializer.to_dict(exclude_none=False)
        new_attribute = serializer.from_dict(ir_data.Attribute, raw_dict)
        self.assertEqual(attribute, new_attribute)

    def test_ir_data_serializer_from_dict_enum(self):
        """Tests that deserializing `enum.Enum` values works properly."""
        type_def = ir_data.TypeDefinition(addressable_unit=ir_data.AddressableUnit.BYTE)

        serializer = ir_data_utils.IrDataSerializer(type_def)
        raw_dict = serializer.to_dict(exclude_none=False)
        new_type_def = serializer.from_dict(ir_data.TypeDefinition, raw_dict)
        self.assertEqual(type_def, new_type_def)

    def test_ir_data_serializer_from_dict_enum_is_str(self):
        """Tests that deserializing `enum.Enum` values works properly when string constant is used."""
        type_def = ir_data.TypeDefinition(addressable_unit=ir_data.AddressableUnit.BYTE)
        raw_dict = {"addressable_unit": "BYTE"}
        serializer = ir_data_utils.IrDataSerializer(type_def)
        new_type_def = serializer.from_dict(ir_data.TypeDefinition, raw_dict)
        self.assertEqual(type_def, new_type_def)

    def test_ir_data_serializer_from_dict_exclude_none(self):
        """Tests that deserializing from a dict that excluded None values works properly."""
        attribute = ir_data.Attribute(
            value=ir_data.AttributeValue(expression=ir_data.Expression()),
            name=ir_data.Word(text="phil"),
        )

        serializer = ir_data_utils.IrDataSerializer(attribute)
        raw_dict = serializer.to_dict(exclude_none=True)
        new_attribute = ir_data_utils.IrDataSerializer.from_dict(
            ir_data.Attribute, raw_dict
        )
        self.assertEqual(attribute, new_attribute)

    def test_from_dict_list(self):
        function_args = [
            {
                "constant": {
                    "value": "0",
                    "source_location": {
                        "start": {"line": 421, "column": 3},
                        "end": {"line": 421, "column": 4},
                        "is_synthetic": False,
                    },
                },
                "type": {
                    "integer": {
                        "modulus": "infinity",
                        "modular_value": "0",
                        "minimum_value": "0",
                        "maximum_value": "0",
                    }
                },
                "source_location": {
                    "start": {"line": 421, "column": 3},
                    "end": {"line": 421, "column": 4},
                    "is_synthetic": False,
                },
            },
            {
                "constant": {
                    "value": "1",
                    "source_location": {
                        "start": {"line": 421, "column": 11},
                        "end": {"line": 421, "column": 12},
                        "is_synthetic": False,
                    },
                },
                "type": {
                    "integer": {
                        "modulus": "infinity",
                        "modular_value": "1",
                        "minimum_value": "1",
                        "maximum_value": "1",
                    }
                },
                "source_location": {
                    "start": {"line": 421, "column": 11},
                    "end": {"line": 421, "column": 12},
                    "is_synthetic": False,
                },
            },
        ]
        function_data = {"args": function_args}
        func = ir_data_utils.IrDataSerializer.from_dict(ir_data.Function, function_data)
        self.assertIsNotNone(func)

    def test_ir_data_serializer_copy_from_dict(self):
        """Tests that updating an IR data struct from a dict works properly."""
        attribute = ir_data.Attribute(
            value=ir_data.AttributeValue(expression=ir_data.Expression()),
            name=ir_data.Word(text="phil"),
        )
        serializer = ir_data_utils.IrDataSerializer(attribute)
        raw_dict = serializer.to_dict(exclude_none=False)

        new_attribute = ir_data.Attribute()
        new_serializer = ir_data_utils.IrDataSerializer(new_attribute)
        new_serializer.copy_from_dict(raw_dict)
        self.assertEqual(attribute, new_attribute)


class ReadOnlyFieldCheckerTest(unittest.TestCase):
    """Tests the ReadOnlyFieldChecker."""

    def test_basic_wrapper(self):
        """Tests basic field checker actions."""
        union = ClassWithTwoUnions(opaque=Opaque(), boolean=True, non_union_field=10)
        field_checker = ir_data_utils.reader(union)

        # All accesses should return a wrapper object
        self.assertIsNotNone(field_checker.opaque)
        self.assertIsNotNone(field_checker.integer)
        self.assertIsNotNone(field_checker.boolean)
        self.assertIsNotNone(field_checker.enumeration)
        self.assertIsNotNone(field_checker.non_union_field)
        # Scalar field should pass through
        self.assertEqual(field_checker.non_union_field, 10)

        # Make sure HasField works
        self.assertTrue(field_checker.HasField("opaque"))
        self.assertFalse(field_checker.HasField("integer"))
        self.assertTrue(field_checker.HasField("boolean"))
        self.assertFalse(field_checker.HasField("enumeration"))
        self.assertTrue(field_checker.HasField("non_union_field"))

    def test_construct_from_field_checker(self):
        """Tests that constructing from another field checker works."""
        union = ClassWithTwoUnions(opaque=Opaque(), boolean=True, non_union_field=10)
        field_checker_orig = ir_data_utils.reader(union)
        field_checker = ir_data_utils.reader(field_checker_orig)
        self.assertIsNotNone(field_checker)
        self.assertEqual(field_checker.ir_or_spec, union)

        # All accesses should return a wrapper object
        self.assertIsNotNone(field_checker.opaque)
        self.assertIsNotNone(field_checker.integer)
        self.assertIsNotNone(field_checker.boolean)
        self.assertIsNotNone(field_checker.enumeration)
        self.assertIsNotNone(field_checker.non_union_field)
        # Scalar field should pass through
        self.assertEqual(field_checker.non_union_field, 10)

        # Make sure HasField works
        self.assertTrue(field_checker.HasField("opaque"))
        self.assertFalse(field_checker.HasField("integer"))
        self.assertTrue(field_checker.HasField("boolean"))
        self.assertFalse(field_checker.HasField("enumeration"))
        self.assertTrue(field_checker.HasField("non_union_field"))

    def test_read_only(self) -> None:
        """Tests that the read only wrapper really is read only."""
        union = ClassWithTwoUnions(opaque=Opaque(), boolean=True, non_union_field=10)
        field_checker = ir_data_utils.reader(union)

        def set_field():
            field_checker.opaque = None

        self.assertRaises(AttributeError, set_field)


ir_data_fields.cache_message_specs(
    sys.modules[ReadOnlyFieldCheckerTest.__module__], ir_data.Message
)

if __name__ == "__main__":
    unittest.main()
