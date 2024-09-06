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

"""Tests for dependency_checker.py."""

import unittest
from compiler.front_end import dependency_checker
from compiler.front_end import glue
from compiler.util import error
from compiler.util import test_util


def _parse_snippet(emb_file):
    ir, unused_debug_info, errors = glue.parse_emboss_file(
        "m.emb",
        test_util.dict_file_reader({"m.emb": emb_file}),
        stop_before_step="find_dependency_cycles",
    )
    assert not errors
    return ir


def _find_dependencies_for_snippet(emb_file):
    ir, unused_debug_info, errors = glue.parse_emboss_file(
        "m.emb",
        test_util.dict_file_reader({"m.emb": emb_file}),
        stop_before_step="set_dependency_order",
    )
    assert not errors, errors
    return ir


class DependencyCheckerTest(unittest.TestCase):

    def test_error_on_simple_field_cycle(self):
        ir = _parse_snippet(
            "struct Foo:\n"
            "  0 [+field2]  UInt  field1\n"
            "  0 [+field1]  UInt  field2\n"
        )
        struct = ir.module[0].type[0].structure
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        struct.field[0].source_location,
                        "Dependency cycle\nfield1",
                    ),
                    error.note("m.emb", struct.field[1].source_location, "field2"),
                ]
            ],
            dependency_checker.find_dependency_cycles(ir),
        )

    def test_error_on_self_cycle(self):
        ir = _parse_snippet("struct Foo:\n" "  0 [+field1]  UInt  field1\n")
        struct = ir.module[0].type[0].structure
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        struct.field[0].source_location,
                        "Dependency cycle\nfield1",
                    )
                ]
            ],
            dependency_checker.find_dependency_cycles(ir),
        )

    def test_error_on_triple_field_cycle(self):
        ir = _parse_snippet(
            "struct Foo:\n"
            "  0 [+field2]  UInt  field1\n"
            "  0 [+field3]  UInt  field2\n"
            "  0 [+field1]  UInt  field3\n"
        )
        struct = ir.module[0].type[0].structure
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        struct.field[0].source_location,
                        "Dependency cycle\nfield1",
                    ),
                    error.note("m.emb", struct.field[1].source_location, "field2"),
                    error.note("m.emb", struct.field[2].source_location, "field3"),
                ]
            ],
            dependency_checker.find_dependency_cycles(ir),
        )

    def test_error_on_complex_field_cycle(self):
        ir = _parse_snippet(
            "struct Foo:\n"
            "  0 [+field2]         UInt  field1\n"
            "  0 [+field3+field4]  UInt  field2\n"
            "  0 [+field1]         UInt  field3\n"
            "  0 [+field2]         UInt  field4\n"
        )
        struct = ir.module[0].type[0].structure
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        struct.field[0].source_location,
                        "Dependency cycle\nfield1",
                    ),
                    error.note("m.emb", struct.field[1].source_location, "field2"),
                    error.note("m.emb", struct.field[2].source_location, "field3"),
                    error.note("m.emb", struct.field[3].source_location, "field4"),
                ]
            ],
            dependency_checker.find_dependency_cycles(ir),
        )

    def test_error_on_simple_enum_value_cycle(self):
        ir = _parse_snippet("enum Foo:\n" "  XX = YY\n" "  YY = XX\n")
        enum = ir.module[0].type[0].enumeration
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb", enum.value[0].source_location, "Dependency cycle\nXX"
                    ),
                    error.note("m.emb", enum.value[1].source_location, "YY"),
                ]
            ],
            dependency_checker.find_dependency_cycles(ir),
        )

    def test_no_error_on_no_cycle(self):
        ir = _parse_snippet("enum Foo:\n" "  XX = 0\n" "  YY = XX\n")
        self.assertEqual([], dependency_checker.find_dependency_cycles(ir))

    def test_error_on_cycle_nested(self):
        ir = _parse_snippet(
            "struct Foo:\n"
            "  struct Bar:\n"
            "    0 [+field2]  UInt  field1\n"
            "    0 [+field1]  UInt  field2\n"
            "  0 [+1]  UInt  field\n"
        )
        struct = ir.module[0].type[0].subtype[0].structure
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        struct.field[0].source_location,
                        "Dependency cycle\nfield1",
                    ),
                    error.note("m.emb", struct.field[1].source_location, "field2"),
                ]
            ],
            dependency_checker.find_dependency_cycles(ir),
        )

    def test_error_on_import_cycle(self):
        ir, unused_debug_info, errors = glue.parse_emboss_file(
            "m.emb",
            test_util.dict_file_reader(
                {"m.emb": 'import "n.emb" as n\n', "n.emb": 'import "m.emb" as m\n'}
            ),
            stop_before_step="find_dependency_cycles",
        )
        assert not errors
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        ir.module[0].source_location,
                        "Import dependency cycle\nm.emb",
                    ),
                    error.note("n.emb", ir.module[2].source_location, "n.emb"),
                ]
            ],
            dependency_checker.find_dependency_cycles(ir),
        )

    def test_error_on_import_cycle_and_field_cycle(self):
        ir, unused_debug_info, errors = glue.parse_emboss_file(
            "m.emb",
            test_util.dict_file_reader(
                {
                    "m.emb": 'import "n.emb" as n\n'
                    "struct Foo:\n"
                    "  0 [+field1]  UInt  field1\n",
                    "n.emb": 'import "m.emb" as m\n',
                }
            ),
            stop_before_step="find_dependency_cycles",
        )
        assert not errors
        struct = ir.module[0].type[0].structure
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        ir.module[0].source_location,
                        "Import dependency cycle\nm.emb",
                    ),
                    error.note("n.emb", ir.module[2].source_location, "n.emb"),
                ],
                [
                    error.error(
                        "m.emb",
                        struct.field[0].source_location,
                        "Dependency cycle\nfield1",
                    )
                ],
            ],
            dependency_checker.find_dependency_cycles(ir),
        )

    def test_error_on_field_existence_self_cycle(self):
        ir = _parse_snippet("struct Foo:\n" "  if x == 1:\n" "    0 [+1]  UInt  x\n")
        struct = ir.module[0].type[0].structure
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb", struct.field[0].source_location, "Dependency cycle\nx"
                    )
                ]
            ],
            dependency_checker.find_dependency_cycles(ir),
        )

    def test_error_on_field_existence_cycle(self):
        ir = _parse_snippet(
            "struct Foo:\n"
            "  if y == 1:\n"
            "    0 [+1]  UInt  x\n"
            "  if x == 0:\n"
            "    1 [+1]  UInt  y\n"
        )
        struct = ir.module[0].type[0].structure
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb", struct.field[0].source_location, "Dependency cycle\nx"
                    ),
                    error.note("m.emb", struct.field[1].source_location, "y"),
                ]
            ],
            dependency_checker.find_dependency_cycles(ir),
        )

    def test_error_on_virtual_field_cycle(self):
        ir = _parse_snippet("struct Foo:\n" "  let x = y\n" "  let y = x\n")
        struct = ir.module[0].type[0].structure
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb", struct.field[0].source_location, "Dependency cycle\nx"
                    ),
                    error.note("m.emb", struct.field[1].source_location, "y"),
                ]
            ],
            dependency_checker.find_dependency_cycles(ir),
        )

    def test_error_on_virtual_non_virtual_field_cycle(self):
        ir = _parse_snippet("struct Foo:\n" "  let x = y\n" "  x [+4]  UInt  y\n")
        struct = ir.module[0].type[0].structure
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb", struct.field[0].source_location, "Dependency cycle\nx"
                    ),
                    error.note("m.emb", struct.field[1].source_location, "y"),
                ]
            ],
            dependency_checker.find_dependency_cycles(ir),
        )

    def test_error_on_non_virtual_virtual_field_cycle(self):
        ir = _parse_snippet("struct Foo:\n" "  y [+4]  UInt  x\n" "  let y = x\n")
        struct = ir.module[0].type[0].structure
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb", struct.field[0].source_location, "Dependency cycle\nx"
                    ),
                    error.note("m.emb", struct.field[1].source_location, "y"),
                ]
            ],
            dependency_checker.find_dependency_cycles(ir),
        )

    def test_error_on_cycle_involving_subfield(self):
        ir = _parse_snippet(
            "struct Bar:\n"
            "  foo_b.x [+4]  Foo  foo_a\n"
            "  foo_a.x [+4]  Foo  foo_b\n"
            "struct Foo:\n"
            "  0 [+4]  UInt  x\n"
        )
        struct = ir.module[0].type[0].structure
        self.assertEqual(
            [
                [
                    error.error(
                        "m.emb",
                        struct.field[0].source_location,
                        "Dependency cycle\nfoo_a",
                    ),
                    error.note("m.emb", struct.field[1].source_location, "foo_b"),
                ]
            ],
            dependency_checker.find_dependency_cycles(ir),
        )

    def test_dependency_ordering_with_no_dependencies(self):
        ir = _find_dependencies_for_snippet(
            "struct Foo:\n" "  0 [+4]  UInt  a\n" "  4 [+4]  UInt  b\n"
        )
        self.assertEqual([], dependency_checker.set_dependency_order(ir))
        struct = ir.module[0].type[0].structure
        self.assertEqual([0, 1], struct.fields_in_dependency_order[:2])

    def test_dependency_ordering_with_dependency_in_order(self):
        ir = _find_dependencies_for_snippet(
            "struct Foo:\n" "  0 [+4]  UInt  a\n" "  a [+4]  UInt  b\n"
        )
        self.assertEqual([], dependency_checker.set_dependency_order(ir))
        struct = ir.module[0].type[0].structure
        self.assertEqual([0, 1], struct.fields_in_dependency_order[:2])

    def test_dependency_ordering_with_dependency_in_reverse_order(self):
        ir = _find_dependencies_for_snippet(
            "struct Foo:\n" "  b [+4]  UInt  a\n" "  0 [+4]  UInt  b\n"
        )
        self.assertEqual([], dependency_checker.set_dependency_order(ir))
        struct = ir.module[0].type[0].structure
        self.assertEqual([1, 0], struct.fields_in_dependency_order[:2])

    def test_dependency_ordering_with_extra_fields(self):
        ir = _find_dependencies_for_snippet(
            "struct Foo:\n"
            "  d [+4]   UInt  a\n"
            "  4 [+4]   UInt  b\n"
            "  8 [+4]   UInt  c\n"
            "  12 [+4]  UInt  d\n"
        )
        self.assertEqual([], dependency_checker.set_dependency_order(ir))
        struct = ir.module[0].type[0].structure
        self.assertEqual([1, 2, 3, 0], struct.fields_in_dependency_order[:4])

    def test_dependency_ordering_scrambled(self):
        ir = _find_dependencies_for_snippet(
            "struct Foo:\n"
            "  d [+4]   UInt  a\n"
            "  c [+4]   UInt  b\n"
            "  a [+4]   UInt  c\n"
            "  12 [+4]  UInt  d\n"
        )
        self.assertEqual([], dependency_checker.set_dependency_order(ir))
        struct = ir.module[0].type[0].structure
        self.assertEqual([3, 0, 2, 1], struct.fields_in_dependency_order[:4])

    def test_dependency_ordering_multiple_dependents(self):
        ir = _find_dependencies_for_snippet(
            "struct Foo:\n"
            "  d [+4]   UInt  a\n"
            "  d [+4]   UInt  b\n"
            "  d [+4]   UInt  c\n"
            "  12 [+4]  UInt  d\n"
        )
        self.assertEqual([], dependency_checker.set_dependency_order(ir))
        struct = ir.module[0].type[0].structure
        self.assertEqual([3, 0, 1, 2], struct.fields_in_dependency_order[:4])

    def test_dependency_ordering_multiple_dependencies(self):
        ir = _find_dependencies_for_snippet(
            "struct Foo:\n"
            "  b+c [+4]  UInt  a\n"
            "  4 [+4]    UInt  b\n"
            "  8 [+4]    UInt  c\n"
            "  a [+4]    UInt  d\n"
        )
        self.assertEqual([], dependency_checker.set_dependency_order(ir))
        struct = ir.module[0].type[0].structure
        self.assertEqual([1, 2, 0, 3], struct.fields_in_dependency_order[:4])

    def test_dependency_ordering_with_parameter(self):
        ir = _find_dependencies_for_snippet(
            "struct Foo:\n"
            "  0 [+1]  Bar(x)  b\n"
            "  1 [+1]  UInt    x\n"
            "struct Bar(x: UInt:8):\n"
            "  x [+1]  UInt    y\n"
        )
        self.assertEqual([], dependency_checker.set_dependency_order(ir))
        struct = ir.module[0].type[0].structure
        self.assertEqual([1, 0], struct.fields_in_dependency_order[:2])

    def test_dependency_ordering_with_local_parameter(self):
        ir = _find_dependencies_for_snippet(
            "struct Foo(x: Int:13):\n" "  0 [+x]  Int  b\n"
        )
        self.assertEqual([], dependency_checker.set_dependency_order(ir))
        struct = ir.module[0].type[0].structure
        self.assertEqual([0], struct.fields_in_dependency_order[:1])


if __name__ == "__main__":
    unittest.main()
