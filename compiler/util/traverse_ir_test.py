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

"""Tests for util.traverse_ir."""

import collections

import unittest

from compiler.util import ir_data
from compiler.util import ir_data_utils
from compiler.util import traverse_ir

_EXAMPLE_IR = ir_data_utils.IrDataSerializer.from_json(
    ir_data.EmbossIr,
    """{
"module": [
  {
    "type": [
      {
        "structure": {
          "field": [
            {
              "location": {
                "start": { "constant": { "value": "0" } },
                "size": { "constant": { "value": "8" } }
              },
              "type": {
                "atomic_type": {
                  "reference": {
                    "canonical_name": {
                      "module_file": "",
                      "object_path": ["UInt"]
                    }
                  }
                }
              },
              "name": { "name": { "text": "field1" } }
            },
            {
              "location": {
                "start": { "constant": { "value": "8" } },
                "size": { "constant": { "value": "16" } }
              },
              "type": {
                "array_type": {
                  "base_type": {
                    "atomic_type": {
                      "reference": {
                        "canonical_name": {
                          "module_file": "",
                          "object_path": ["UInt"]
                        }
                      }
                    }
                  },
                  "element_count": { "constant": { "value": "8" } }
                }
              },
              "name": { "name": { "text": "field2" } }
            }
          ]
        },
        "name": { "name": { "text": "Foo" } },
        "subtype": [
          {
            "structure": {
              "field": [
                {
                  "location": {
                    "start": { "constant": { "value": "24" } },
                    "size": { "constant": { "value": "32" } }
                  },
                  "type": {
                    "atomic_type": {
                      "reference": {
                        "canonical_name": {
                          "module_file": "",
                          "object_path": ["UInt"]
                        }
                      }
                    }
                  },
                  "name": { "name": { "text": "bar_field1" } }
                },
                {
                  "location": {
                    "start": { "constant": { "value": "32" } },
                    "size": { "constant": { "value": "320" } }
                  },
                  "type": {
                    "array_type": {
                      "base_type": {
                        "array_type": {
                          "base_type": {
                            "atomic_type": {
                              "reference": {
                                "canonical_name": {
                                  "module_file": "",
                                  "object_path": ["UInt"]
                                }
                              }
                            }
                          },
                          "element_count": { "constant": { "value": "16" } }
                        }
                      },
                      "automatic": { }
                    }
                  },
                  "name": { "name": { "text": "bar_field2" } }
                }
              ]
            },
            "name": { "name": { "text": "Bar" } }
          }
        ]
      },
      {
        "enumeration": {
          "value": [
            {
              "name": { "name": { "text": "ONE" } },
              "value": { "constant": { "value": "1" } }
            },
            {
              "name": { "name": { "text": "TWO" } },
              "value": {
                "function": {
                  "function": "ADDITION",
                  "args": [
                    { "constant": { "value": "1" } },
                    { "constant": { "value": "1" } }
                  ],
                  "function_name": { "text": "+" }
                }
              }
            }
          ]
        },
        "name": { "name": { "text": "Bar" } }
      }
    ],
    "source_file_name": "t.emb"
  },
  {
    "type": [
      {
        "external": { },
        "name": {
          "name": { "text": "UInt" },
          "canonical_name": { "module_file": "", "object_path": ["UInt"] }
        },
        "attribute": [
          {
            "name": { "text": "statically_sized" },
            "value": { "expression": { "boolean_constant": { "value": true } } }
          },
          {
            "name": { "text": "size_in_bits" },
            "value": { "expression": { "constant": { "value": "64" } } }
          }
        ]
      }
    ],
    "source_file_name": ""
  }
]
}""",
)


def _count_entries(sequence):
    counts = collections.Counter()
    for entry in sequence:
        counts[entry] += 1
    return counts


def _record_constant(constant, constant_list):
    constant_list.append(int(constant.value))


def _record_field_name_and_constant(constant, constant_list, field):
    constant_list.append((field.name.name.text, int(constant.value)))


def _record_file_name_and_constant(constant, constant_list, source_file_name):
    constant_list.append((source_file_name, int(constant.value)))


def _record_location_parameter_and_constant(constant, constant_list, location=None):
    constant_list.append((location, int(constant.value)))


def _record_kind_and_constant(constant, constant_list, type_definition):
    if type_definition.HasField("enumeration"):
        constant_list.append(("enumeration", int(constant.value)))
    elif type_definition.HasField("structure"):
        constant_list.append(("structure", int(constant.value)))
    elif type_definition.HasField("external"):
        constant_list.append(("external", int(constant.value)))
    else:
        assert False, "Shouldn't be here."


class TraverseIrTest(unittest.TestCase):

    def test_filter_on_type(self):
        constants = []
        traverse_ir.fast_traverse_ir_top_down(
            _EXAMPLE_IR,
            [ir_data.NumericConstant],
            _record_constant,
            parameters={"constant_list": constants},
        )
        self.assertEqual(
            _count_entries([0, 8, 8, 8, 16, 24, 32, 16, 32, 320, 1, 1, 1, 64]),
            _count_entries(constants),
        )

    def test_filter_on_type_in_type(self):
        constants = []
        traverse_ir.fast_traverse_ir_top_down(
            _EXAMPLE_IR,
            [ir_data.Function, ir_data.Expression, ir_data.NumericConstant],
            _record_constant,
            parameters={"constant_list": constants},
        )
        self.assertEqual([1, 1], constants)

    def test_filter_on_type_star_type(self):
        struct_constants = []
        traverse_ir.fast_traverse_ir_top_down(
            _EXAMPLE_IR,
            [ir_data.Structure, ir_data.NumericConstant],
            _record_constant,
            parameters={"constant_list": struct_constants},
        )
        self.assertEqual(
            _count_entries([0, 8, 8, 8, 16, 24, 32, 16, 32, 320]),
            _count_entries(struct_constants),
        )
        enum_constants = []
        traverse_ir.fast_traverse_ir_top_down(
            _EXAMPLE_IR,
            [ir_data.Enum, ir_data.NumericConstant],
            _record_constant,
            parameters={"constant_list": enum_constants},
        )
        self.assertEqual(_count_entries([1, 1, 1]), _count_entries(enum_constants))

    def test_filter_on_not_type(self):
        notstruct_constants = []
        traverse_ir.fast_traverse_ir_top_down(
            _EXAMPLE_IR,
            [ir_data.NumericConstant],
            _record_constant,
            skip_descendants_of=(ir_data.Structure,),
            parameters={"constant_list": notstruct_constants},
        )
        self.assertEqual(
            _count_entries([1, 1, 1, 64]), _count_entries(notstruct_constants)
        )

    def test_field_is_populated(self):
        constants = []
        traverse_ir.fast_traverse_ir_top_down(
            _EXAMPLE_IR,
            [ir_data.Field, ir_data.NumericConstant],
            _record_field_name_and_constant,
            parameters={"constant_list": constants},
        )
        self.assertEqual(
            _count_entries(
                [
                    ("field1", 0),
                    ("field1", 8),
                    ("field2", 8),
                    ("field2", 8),
                    ("field2", 16),
                    ("bar_field1", 24),
                    ("bar_field1", 32),
                    ("bar_field2", 16),
                    ("bar_field2", 32),
                    ("bar_field2", 320),
                ]
            ),
            _count_entries(constants),
        )

    def test_file_name_is_populated(self):
        constants = []
        traverse_ir.fast_traverse_ir_top_down(
            _EXAMPLE_IR,
            [ir_data.NumericConstant],
            _record_file_name_and_constant,
            parameters={"constant_list": constants},
        )
        self.assertEqual(
            _count_entries(
                [
                    ("t.emb", 0),
                    ("t.emb", 8),
                    ("t.emb", 8),
                    ("t.emb", 8),
                    ("t.emb", 16),
                    ("t.emb", 24),
                    ("t.emb", 32),
                    ("t.emb", 16),
                    ("t.emb", 32),
                    ("t.emb", 320),
                    ("t.emb", 1),
                    ("t.emb", 1),
                    ("t.emb", 1),
                    ("", 64),
                ]
            ),
            _count_entries(constants),
        )

    def test_type_definition_is_populated(self):
        constants = []
        traverse_ir.fast_traverse_ir_top_down(
            _EXAMPLE_IR,
            [ir_data.NumericConstant],
            _record_kind_and_constant,
            parameters={"constant_list": constants},
        )
        self.assertEqual(
            _count_entries(
                [
                    ("structure", 0),
                    ("structure", 8),
                    ("structure", 8),
                    ("structure", 8),
                    ("structure", 16),
                    ("structure", 24),
                    ("structure", 32),
                    ("structure", 16),
                    ("structure", 32),
                    ("structure", 320),
                    ("enumeration", 1),
                    ("enumeration", 1),
                    ("enumeration", 1),
                    ("external", 64),
                ]
            ),
            _count_entries(constants),
        )

    def test_keyword_args_dict_in_action(self):
        call_counts = {"populated": 0, "not": 0}

        def check_field_is_populated(node, **kwargs):
            del node  # Unused.
            self.assertTrue(kwargs["field"])
            call_counts["populated"] += 1

        def check_field_is_not_populated(node, **kwargs):
            del node  # Unused.
            self.assertFalse("field" in kwargs)
            call_counts["not"] += 1

        traverse_ir.fast_traverse_ir_top_down(
            _EXAMPLE_IR, [ir_data.Field, ir_data.Type], check_field_is_populated
        )
        self.assertEqual(7, call_counts["populated"])

        traverse_ir.fast_traverse_ir_top_down(
            _EXAMPLE_IR, [ir_data.Enum, ir_data.EnumValue], check_field_is_not_populated
        )
        self.assertEqual(2, call_counts["not"])

    def test_pass_only_to_sub_nodes(self):
        constants = []

        def pass_location_down(field):
            return {
                "location": (
                    int(field.location.start.constant.value),
                    int(field.location.size.constant.value),
                )
            }

        traverse_ir.fast_traverse_ir_top_down(
            _EXAMPLE_IR,
            [ir_data.NumericConstant],
            _record_location_parameter_and_constant,
            incidental_actions={ir_data.Field: pass_location_down},
            parameters={"constant_list": constants, "location": None},
        )
        self.assertEqual(
            _count_entries(
                [
                    ((0, 8), 0),
                    ((0, 8), 8),
                    ((8, 16), 8),
                    ((8, 16), 8),
                    ((8, 16), 16),
                    ((24, 32), 24),
                    ((24, 32), 32),
                    ((32, 320), 16),
                    ((32, 320), 32),
                    ((32, 320), 320),
                    (None, 1),
                    (None, 1),
                    (None, 1),
                    (None, 64),
                ]
            ),
            _count_entries(constants),
        )


if __name__ == "__main__":
    unittest.main()
