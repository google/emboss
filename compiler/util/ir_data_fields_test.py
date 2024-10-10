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

"""Tests for util.ir_data_fields."""

import dataclasses
import enum
import sys
from typing import Optional
import unittest

from compiler.util import ir_data
from compiler.util import ir_data_fields


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


@dataclasses.dataclass
class NestedClass(ir_data.Message):
    """Used for testing data field helpers."""

    one_union_class: Optional[ClassWithUnion] = None
    two_union_class: Optional[ClassWithTwoUnions] = None


@dataclasses.dataclass
class ListCopyTestClass(ir_data.Message):
    """Used to test behavior or extending a sequence."""

    non_union_field: int = 0
    seq_field: list[int] = ir_data_fields.list_field(int)


@dataclasses.dataclass
class OneofFieldTest(ir_data.Message):
    """Basic test class for oneof fields."""

    int_field_1: Optional[int] = ir_data_fields.oneof_field("type_1")
    int_field_2: Optional[int] = ir_data_fields.oneof_field("type_1")
    normal_field: bool = True


class OneOfTest(unittest.TestCase):
    """Tests for the various oneof field helpers."""

    def test_field_attribute(self):
        """Test the `oneof_field` helper."""
        test_field = ir_data_fields.oneof_field("type_1")
        self.assertIsNotNone(test_field)
        self.assertTrue(test_field.init)
        self.assertIsInstance(test_field.default, ir_data_fields.OneOfField)
        self.assertEqual(test_field.metadata.get("oneof"), "type_1")

    def test_init_default(self):
        """Test creating an instance with default fields."""
        one_of_field_test = OneofFieldTest()
        self.assertIsNone(one_of_field_test.int_field_1)
        self.assertIsNone(one_of_field_test.int_field_2)
        self.assertTrue(one_of_field_test.normal_field)

    def test_init(self):
        """Test creating an instance with non-default fields."""
        one_of_field_test = OneofFieldTest(int_field_1=10, normal_field=False)
        self.assertEqual(one_of_field_test.int_field_1, 10)
        self.assertIsNone(one_of_field_test.int_field_2)
        self.assertFalse(one_of_field_test.normal_field)

    def test_set_oneof_field(self):
        """Tests setting oneof fields causes others in the group to be unset."""
        one_of_field_test = OneofFieldTest()
        one_of_field_test.int_field_1 = 10
        self.assertEqual(one_of_field_test.int_field_1, 10)
        self.assertIsNone(one_of_field_test.int_field_2)
        one_of_field_test.int_field_2 = 20
        self.assertIsNone(one_of_field_test.int_field_1)
        self.assertEqual(one_of_field_test.int_field_2, 20)

        # Do it again
        one_of_field_test.int_field_1 = 10
        self.assertEqual(one_of_field_test.int_field_1, 10)
        self.assertIsNone(one_of_field_test.int_field_2)
        one_of_field_test.int_field_2 = 20
        self.assertIsNone(one_of_field_test.int_field_1)
        self.assertEqual(one_of_field_test.int_field_2, 20)

        # Now create a new instance and make sure changes to it are not
        # reflected on the original object.
        one_of_field_test_2 = OneofFieldTest()
        one_of_field_test_2.int_field_1 = 1000
        self.assertEqual(one_of_field_test_2.int_field_1, 1000)
        self.assertIsNone(one_of_field_test_2.int_field_2)
        self.assertIsNone(one_of_field_test.int_field_1)
        self.assertEqual(one_of_field_test.int_field_2, 20)

    def test_set_to_none(self):
        """Tests explicitly setting a oneof field to None."""
        one_of_field_test = OneofFieldTest(int_field_1=10, normal_field=False)
        self.assertEqual(one_of_field_test.int_field_1, 10)
        self.assertIsNone(one_of_field_test.int_field_2)
        self.assertFalse(one_of_field_test.normal_field)

        # Clear the set fields
        one_of_field_test.int_field_1 = None
        self.assertIsNone(one_of_field_test.int_field_1)
        self.assertIsNone(one_of_field_test.int_field_2)
        self.assertFalse(one_of_field_test.normal_field)

        # Set another field
        one_of_field_test.int_field_2 = 200
        self.assertIsNone(one_of_field_test.int_field_1)
        self.assertEqual(one_of_field_test.int_field_2, 200)
        self.assertFalse(one_of_field_test.normal_field)

        # Clear the already unset field
        one_of_field_test.int_field_1 = None
        self.assertIsNone(one_of_field_test.int_field_1)
        self.assertEqual(one_of_field_test.int_field_2, 200)
        self.assertFalse(one_of_field_test.normal_field)

    def test_oneof_specs(self):
        """Tests the `oneof_field_specs` filter."""
        expected = {
            "int_field_1": ir_data_fields.make_field_spec(
                "int_field_1", int, ir_data_fields.FieldContainer.OPTIONAL, "type_1"
            ),
            "int_field_2": ir_data_fields.make_field_spec(
                "int_field_2", int, ir_data_fields.FieldContainer.OPTIONAL, "type_1"
            ),
        }
        actual = ir_data_fields.IrDataclassSpecs.get_specs(
            OneofFieldTest
        ).oneof_field_specs
        self.assertDictEqual(actual, expected)

    def test_oneof_mappings(self):
        """Tests the `oneof_mappings` function."""
        expected = (("int_field_1", "type_1"), ("int_field_2", "type_1"))
        actual = ir_data_fields.IrDataclassSpecs.get_specs(
            OneofFieldTest
        ).oneof_mappings
        self.assertTupleEqual(actual, expected)


class IrDataFieldsTest(unittest.TestCase):
    """Tests misc methods in ir_data_fields."""

    def assertEmpty(self, obj):
        self.assertEqual(len(obj), 0, msg=f"{obj} is not empty.")

    def assertLen(self, obj, length):
        self.assertEqual(len(obj), length, msg=f"{obj} has length {len(obj)}.")

    def assertEmpty(self, obj):
        self.assertEqual(len(obj), 0, msg=f"{obj} is not empty.")

    def assertLen(self, obj, length):
        self.assertEqual(len(obj), length, msg=f"{obj} has length {len(obj)}.")

    def test_copy(self):
        """Tests copying a data class works as expected."""
        union = ClassWithTwoUnions(
            opaque=Opaque(), boolean=True, non_union_field=10, seq_field=[1, 2, 3]
        )
        nested_class = NestedClass(two_union_class=union)
        nested_class_copy = ir_data_fields.copy(nested_class)
        self.assertIsNotNone(nested_class_copy)
        self.assertIsNot(nested_class, nested_class_copy)
        self.assertEqual(nested_class_copy, nested_class)

        empty_copy = ir_data_fields.copy(None)
        self.assertIsNone(empty_copy)

    def test_copy_values_list(self):
        """Tests that CopyValuesList copies values."""
        data_list = ir_data_fields.CopyValuesList(ListCopyTestClass)
        self.assertEmpty(data_list)

        list_test = ListCopyTestClass(non_union_field=2, seq_field=[5, 6, 7])
        list_tests = [ir_data_fields.copy(list_test) for _ in range(4)]
        data_list.extend(list_tests)
        self.assertLen(data_list, 4)
        for i in data_list:
            self.assertEqual(i, list_test)

    def test_list_param_is_copied(self):
        """Test that lists passed to constructors are converted to CopyValuesList."""
        seq_field = [5, 6, 7]
        list_test = ListCopyTestClass(non_union_field=2, seq_field=seq_field)
        self.assertLen(list_test.seq_field, len(seq_field))
        self.assertIsNot(list_test.seq_field, seq_field)
        self.assertEqual(list_test.seq_field, seq_field)
        self.assertIsInstance(list_test.seq_field, ir_data_fields.CopyValuesList)

    def test_copy_oneof(self):
        """Tests copying an IR data class that has oneof fields."""
        oneof_test = OneofFieldTest()
        oneof_test.int_field_1 = 10
        oneof_test.normal_field = False
        self.assertEqual(oneof_test.int_field_1, 10)
        self.assertEqual(oneof_test.normal_field, False)

        oneof_copy = ir_data_fields.copy(oneof_test)
        self.assertIsNotNone(oneof_copy)
        self.assertEqual(oneof_copy.int_field_1, 10)
        self.assertIsNone(oneof_copy.int_field_2)
        self.assertEqual(oneof_copy.normal_field, False)

        oneof_copy.int_field_2 = 100
        self.assertEqual(oneof_copy.int_field_2, 100)
        self.assertIsNone(oneof_copy.int_field_1)
        self.assertEqual(oneof_test.int_field_1, 10)
        self.assertEqual(oneof_test.normal_field, False)


ir_data_fields.cache_message_specs(
    sys.modules[OneofFieldTest.__module__], ir_data.Message
)

if __name__ == "__main__":
    unittest.main()
