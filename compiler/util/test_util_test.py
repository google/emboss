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

"""Tests for front_end.test_util."""

import unittest

from compiler.util import ir_data
from compiler.util import parser_types
from compiler.util import test_util


class ProtoIsSupersetTest(unittest.TestCase):
    """Tests for test_util.proto_is_superset."""

    def test_superset_extra_optional_field(self):
        self.assertEqual(
            (True, ""),
            test_util.proto_is_superset(
                ir_data.Structure(
                    field=[ir_data.Field()],
                    source_location=parser_types.parse_location("1:2-3:4"),
                ),
                ir_data.Structure(field=[ir_data.Field()]),
            ),
        )

    def test_superset_extra_repeated_field(self):
        self.assertEqual(
            (True, ""),
            test_util.proto_is_superset(
                ir_data.Structure(
                    field=[ir_data.Field(), ir_data.Field()],
                    source_location=parser_types.parse_location("1:2-3:4"),
                ),
                ir_data.Structure(field=[ir_data.Field()]),
            ),
        )

    def test_superset_missing_empty_repeated_field(self):
        self.assertEqual(
            (False, "field[0] missing"),
            test_util.proto_is_superset(
                ir_data.Structure(
                    field=[], source_location=parser_types.parse_location("1:2-3:4")
                ),
                ir_data.Structure(field=[ir_data.Field(), ir_data.Field()]),
            ),
        )

    def test_superset_missing_empty_optional_field(self):
        self.assertEqual(
            (False, "source_location missing"),
            test_util.proto_is_superset(
                ir_data.Structure(field=[]),
                ir_data.Structure(source_location=ir_data.Location()),
            ),
        )

    def test_array_element_differs(self):
        self.assertEqual(
            (False, "field[0].source_location.start.line differs: found 1, expected 2"),
            test_util.proto_is_superset(
                ir_data.Structure(
                    field=[
                        ir_data.Field(
                            source_location=parser_types.parse_location("1:2-3:4")
                        )
                    ]
                ),
                ir_data.Structure(
                    field=[
                        ir_data.Field(
                            source_location=parser_types.parse_location("2:2-3:4")
                        )
                    ]
                ),
            ),
        )

    def test_equal(self):
        self.assertEqual(
            (True, ""),
            test_util.proto_is_superset(
                parser_types.parse_location("1:2-3:4"),
                parser_types.parse_location("1:2-3:4"),
            ),
        )

    def test_superset_missing_optional_field(self):
        self.assertEqual(
            (False, "source_location missing"),
            test_util.proto_is_superset(
                ir_data.Structure(field=[ir_data.Field()]),
                ir_data.Structure(
                    field=[ir_data.Field()],
                    source_location=parser_types.parse_location("1:2-3:4"),
                ),
            ),
        )

    def test_optional_field_differs(self):
        self.assertEqual(
            (False, "end.line differs: found 4, expected 3"),
            test_util.proto_is_superset(
                parser_types.parse_location("1:2-4:4"),
                parser_types.parse_location("1:2-3:4"),
            ),
        )

    def test_non_message_repeated_field_equal(self):
        self.assertEqual(
            (True, ""),
            test_util.proto_is_superset(
                ir_data.CanonicalName(object_path=[]),
                ir_data.CanonicalName(object_path=[]),
            ),
        )

    def test_non_message_repeated_field_missing_element(self):
        self.assertEqual(
            (
                False,
                "object_path differs: found {none!r}, expected {a!r}".format(
                    none=[], a=["a"]
                ),
            ),
            test_util.proto_is_superset(
                ir_data.CanonicalName(object_path=[]),
                ir_data.CanonicalName(object_path=["a"]),
            ),
        )

    def test_non_message_repeated_field_element_differs(self):
        self.assertEqual(
            (
                False,
                "object_path differs: found {aa!r}, expected {ab!r}".format(
                    aa=["a", "a"], ab=["a", "b"]
                ),
            ),
            test_util.proto_is_superset(
                ir_data.CanonicalName(object_path=["a", "a"]),
                ir_data.CanonicalName(object_path=["a", "b"]),
            ),
        )

    def test_non_message_repeated_field_extra_element(self):
        # For repeated fields of int/bool/str values, the entire list is treated as
        # an atomic unit, and should be equal.
        self.assertEqual(
            (
                False,
                "object_path differs: found {!r}, expected {!r}".format(
                    ["a", "a"], ["a"]
                ),
            ),
            test_util.proto_is_superset(
                ir_data.CanonicalName(object_path=["a", "a"]),
                ir_data.CanonicalName(object_path=["a"]),
            ),
        )

    def test_non_message_repeated_field_no_expected_value(self):
        # When a repeated field is empty, it is the same as if it were entirely
        # missing -- there is no way to differentiate those two conditions.
        self.assertEqual(
            (True, ""),
            test_util.proto_is_superset(
                ir_data.CanonicalName(object_path=["a", "a"]),
                ir_data.CanonicalName(object_path=[]),
            ),
        )


class DictFileReaderTest(unittest.TestCase):
    """Tests for dict_file_reader."""

    def test_empty_dict(self):
        reader = test_util.dict_file_reader({})
        self.assertEqual((None, ["File 'anything' not found."]), reader("anything"))
        self.assertEqual((None, ["File '' not found."]), reader(""))

    def test_one_element_dict(self):
        reader = test_util.dict_file_reader({"m": "abc"})
        self.assertEqual((None, ["File 'not_there' not found."]), reader("not_there"))
        self.assertEqual((None, ["File '' not found."]), reader(""))
        self.assertEqual(("abc", None), reader("m"))

    def test_two_element_dict(self):
        reader = test_util.dict_file_reader({"m": "abc", "n": "def"})
        self.assertEqual((None, ["File 'not_there' not found."]), reader("not_there"))
        self.assertEqual((None, ["File '' not found."]), reader(""))
        self.assertEqual(("abc", None), reader("m"))
        self.assertEqual(("def", None), reader("n"))

    def test_dict_with_empty_key(self):
        reader = test_util.dict_file_reader({"m": "abc", "": "def"})
        self.assertEqual((None, ["File 'not_there' not found."]), reader("not_there"))
        self.assertEqual((None, ["File 'None' not found."]), reader(None))
        self.assertEqual(("abc", None), reader("m"))
        self.assertEqual(("def", None), reader(""))


if __name__ == "__main__":
    unittest.main()
