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

"""Tests for emboss.front_end.symbol_resolver."""

import unittest
from compiler.front_end import glue
from compiler.front_end import symbol_resolver
from compiler.util import error
from compiler.util import test_util

_HAPPY_EMB = """
struct Foo:
  0 [+4]  UInt    uint_field
  4 [+4]  Bar     bar_field
  8 [+16] UInt[4] array_field

struct Bar:
  0 [+4]  Qux     bar

enum Qux:
  ABC = 1
  DEF = 2

struct FieldRef:
  n-4      [+n]       UInt:8[n]       data
  offset-4 [+offset]  UInt:8[offset]  data2
  0        [+4]       UInt            offset (n)

struct VoidLength:
  0 [+10]  UInt:8[]  ten_bytes

enum Quux:
  ABC = 1
  DEF = ABC

struct UsesParameter(x: UInt:8):
  0 [+x]   UInt:8[]  block
"""


class ResolveSymbolsTest(unittest.TestCase):
    """Tests for symbol_resolver.resolve_symbols()."""

    def _construct_ir_multiple(self, file_dict, primary_emb_name):
        ir, unused_debug_info, errors = glue.parse_emboss_file(
            primary_emb_name,
            test_util.dict_file_reader(file_dict),
            stop_before_step="resolve_symbols",
        )
        assert not errors
        return ir

    def _construct_ir(self, emb_text, name="happy.emb"):
        return self._construct_ir_multiple({name: emb_text}, name)

    def test_struct_field_atomic_type_resolution(self):
        ir = self._construct_ir(_HAPPY_EMB)
        self.assertEqual([], symbol_resolver.resolve_symbols(ir))
        struct_ir = ir.module[0].type[0].structure
        atomic_field1_reference = struct_ir.field[0].type.atomic_type.reference
        self.assertEqual(atomic_field1_reference.canonical_name.object_path, ["UInt"])
        self.assertEqual(atomic_field1_reference.canonical_name.module_file, "")
        atomic_field2_reference = struct_ir.field[1].type.atomic_type.reference
        self.assertEqual(atomic_field2_reference.canonical_name.object_path, ["Bar"])
        self.assertEqual(
            atomic_field2_reference.canonical_name.module_file, "happy.emb"
        )

    def test_struct_field_enum_type_resolution(self):
        ir = self._construct_ir(_HAPPY_EMB)
        self.assertEqual([], symbol_resolver.resolve_symbols(ir))
        struct_ir = ir.module[0].type[1].structure
        atomic_field_reference = struct_ir.field[0].type.atomic_type.reference
        self.assertEqual(atomic_field_reference.canonical_name.object_path, ["Qux"])
        self.assertEqual(atomic_field_reference.canonical_name.module_file, "happy.emb")

    def test_struct_field_array_type_resolution(self):
        ir = self._construct_ir(_HAPPY_EMB)
        self.assertEqual([], symbol_resolver.resolve_symbols(ir))
        array_field_type = ir.module[0].type[0].structure.field[2].type.array_type
        array_field_reference = array_field_type.base_type.atomic_type.reference
        self.assertEqual(array_field_reference.canonical_name.object_path, ["UInt"])
        self.assertEqual(array_field_reference.canonical_name.module_file, "")

    def test_inner_type_resolution(self):
        ir = self._construct_ir(_HAPPY_EMB)
        self.assertEqual([], symbol_resolver.resolve_symbols(ir))
        array_field_type = ir.module[0].type[0].structure.field[2].type.array_type
        array_field_reference = array_field_type.base_type.atomic_type.reference
        self.assertEqual(array_field_reference.canonical_name.object_path, ["UInt"])
        self.assertEqual(array_field_reference.canonical_name.module_file, "")

    def test_struct_field_resolution_in_expression_in_location(self):
        ir = self._construct_ir(_HAPPY_EMB)
        self.assertEqual([], symbol_resolver.resolve_symbols(ir))
        struct_ir = ir.module[0].type[3].structure
        field0_loc = struct_ir.field[0].location
        abbreviation_reference = field0_loc.size.field_reference.path[0]
        self.assertEqual(
            abbreviation_reference.canonical_name.object_path, ["FieldRef", "offset"]
        )
        self.assertEqual(abbreviation_reference.canonical_name.module_file, "happy.emb")
        field0_start_left = field0_loc.start.function.args[0]
        nested_abbreviation_reference = field0_start_left.field_reference.path[0]
        self.assertEqual(
            nested_abbreviation_reference.canonical_name.object_path,
            ["FieldRef", "offset"],
        )
        self.assertEqual(
            nested_abbreviation_reference.canonical_name.module_file, "happy.emb"
        )
        field1_loc = struct_ir.field[1].location
        direct_reference = field1_loc.size.field_reference.path[0]
        self.assertEqual(
            direct_reference.canonical_name.object_path, ["FieldRef", "offset"]
        )
        self.assertEqual(direct_reference.canonical_name.module_file, "happy.emb")
        field1_start_left = field1_loc.start.function.args[0]
        nested_direct_reference = field1_start_left.field_reference.path[0]
        self.assertEqual(
            nested_direct_reference.canonical_name.object_path, ["FieldRef", "offset"]
        )
        self.assertEqual(
            nested_direct_reference.canonical_name.module_file, "happy.emb"
        )

    def test_struct_field_resolution_in_expression_in_array_length(self):
        ir = self._construct_ir(_HAPPY_EMB)
        self.assertEqual([], symbol_resolver.resolve_symbols(ir))
        struct_ir = ir.module[0].type[3].structure
        field0_array_type = struct_ir.field[0].type.array_type
        field0_array_element_count = field0_array_type.element_count
        abbreviation_reference = field0_array_element_count.field_reference.path[0]
        self.assertEqual(
            abbreviation_reference.canonical_name.object_path, ["FieldRef", "offset"]
        )
        self.assertEqual(abbreviation_reference.canonical_name.module_file, "happy.emb")
        field1_array_type = struct_ir.field[1].type.array_type
        direct_reference = field1_array_type.element_count.field_reference.path[0]
        self.assertEqual(
            direct_reference.canonical_name.object_path, ["FieldRef", "offset"]
        )
        self.assertEqual(direct_reference.canonical_name.module_file, "happy.emb")

    def test_struct_parameter_resolution(self):
        ir = self._construct_ir(_HAPPY_EMB)
        self.assertEqual([], symbol_resolver.resolve_symbols(ir))
        struct_ir = ir.module[0].type[6].structure
        size_ir = struct_ir.field[0].location.size
        self.assertTrue(size_ir.HasField("field_reference"))
        self.assertEqual(
            size_ir.field_reference.path[0].canonical_name.object_path,
            ["UsesParameter", "x"],
        )

    def test_enum_value_resolution_in_expression_in_enum_field(self):
        ir = self._construct_ir(_HAPPY_EMB)
        self.assertEqual([], symbol_resolver.resolve_symbols(ir))
        enum_ir = ir.module[0].type[5].enumeration
        value_reference = enum_ir.value[1].value.constant_reference
        self.assertEqual(value_reference.canonical_name.object_path, ["Quux", "ABC"])
        self.assertEqual(value_reference.canonical_name.module_file, "happy.emb")

    def test_symbol_resolution_in_expression_in_void_array_length(self):
        ir = self._construct_ir(_HAPPY_EMB)
        self.assertEqual([], symbol_resolver.resolve_symbols(ir))
        struct_ir = ir.module[0].type[4].structure
        array_type = struct_ir.field[0].type.array_type
        # The symbol resolver should ignore void fields.
        self.assertEqual("automatic", array_type.WhichOneof("size"))

    def test_name_definitions_have_correct_canonical_names(self):
        ir = self._construct_ir(_HAPPY_EMB)
        self.assertEqual([], symbol_resolver.resolve_symbols(ir))
        foo_name = ir.module[0].type[0].name
        self.assertEqual(foo_name.canonical_name.object_path, ["Foo"])
        self.assertEqual(foo_name.canonical_name.module_file, "happy.emb")
        uint_field_name = ir.module[0].type[0].structure.field[0].name
        self.assertEqual(
            uint_field_name.canonical_name.object_path, ["Foo", "uint_field"]
        )
        self.assertEqual(uint_field_name.canonical_name.module_file, "happy.emb")
        foo_name = ir.module[0].type[2].name
        self.assertEqual(foo_name.canonical_name.object_path, ["Qux"])
        self.assertEqual(foo_name.canonical_name.module_file, "happy.emb")

    def test_duplicate_type_name(self):
        ir = self._construct_ir(
            "struct Foo:\n"
            "  0 [+4]  UInt  field\n"
            "struct Foo:\n"
            "  0 [+4]  UInt  bar\n",
            "duplicate_type.emb",
        )
        errors = error.filter_errors(symbol_resolver.resolve_symbols(ir))
        self.assertEqual(
            [
                [
                    error.error(
                        "duplicate_type.emb",
                        ir.module[0].type[1].name.source_location,
                        "Duplicate name 'Foo'",
                    ),
                    error.note(
                        "duplicate_type.emb",
                        ir.module[0].type[0].name.source_location,
                        "Original definition",
                    ),
                ]
            ],
            errors,
        )

    def test_duplicate_field_name_in_struct(self):
        ir = self._construct_ir(
            "struct Foo:\n" "  0 [+4]  UInt  field\n" "  4 [+4]  UInt  field\n",
            "duplicate_field.emb",
        )
        errors = error.filter_errors(symbol_resolver.resolve_symbols(ir))
        struct = ir.module[0].type[0].structure
        self.assertEqual(
            [
                [
                    error.error(
                        "duplicate_field.emb",
                        struct.field[1].name.source_location,
                        "Duplicate name 'field'",
                    ),
                    error.note(
                        "duplicate_field.emb",
                        struct.field[0].name.source_location,
                        "Original definition",
                    ),
                ]
            ],
            errors,
        )

    def test_duplicate_abbreviation_in_struct(self):
        ir = self._construct_ir(
            "struct Foo:\n"
            "  0 [+4]  UInt  field1 (f)\n"
            "  4 [+4]  UInt  field2 (f)\n",
            "duplicate_field.emb",
        )
        errors = error.filter_errors(symbol_resolver.resolve_symbols(ir))
        struct = ir.module[0].type[0].structure
        self.assertEqual(
            [
                [
                    error.error(
                        "duplicate_field.emb",
                        struct.field[1].abbreviation.source_location,
                        "Duplicate name 'f'",
                    ),
                    error.note(
                        "duplicate_field.emb",
                        struct.field[0].abbreviation.source_location,
                        "Original definition",
                    ),
                ]
            ],
            errors,
        )

    def test_abbreviation_duplicates_field_name_in_struct(self):
        ir = self._construct_ir(
            "struct Foo:\n"
            "  0 [+4]  UInt  field\n"
            "  4 [+4]  UInt  field2 (field)\n",
            "duplicate_field.emb",
        )
        errors = error.filter_errors(symbol_resolver.resolve_symbols(ir))
        struct = ir.module[0].type[0].structure
        self.assertEqual(
            [
                [
                    error.error(
                        "duplicate_field.emb",
                        struct.field[1].abbreviation.source_location,
                        "Duplicate name 'field'",
                    ),
                    error.note(
                        "duplicate_field.emb",
                        struct.field[0].name.source_location,
                        "Original definition",
                    ),
                ]
            ],
            errors,
        )

    def test_field_name_duplicates_abbreviation_in_struct(self):
        ir = self._construct_ir(
            "struct Foo:\n"
            "  0 [+4]  UInt  field (field2)\n"
            "  4 [+4]  UInt  field2\n",
            "duplicate_field.emb",
        )
        errors = error.filter_errors(symbol_resolver.resolve_symbols(ir))
        struct = ir.module[0].type[0].structure
        self.assertEqual(
            [
                [
                    error.error(
                        "duplicate_field.emb",
                        struct.field[1].name.source_location,
                        "Duplicate name 'field2'",
                    ),
                    error.note(
                        "duplicate_field.emb",
                        struct.field[0].abbreviation.source_location,
                        "Original definition",
                    ),
                ]
            ],
            errors,
        )

    def test_duplicate_value_name_in_enum(self):
        ir = self._construct_ir(
            "enum Foo:\n" "  BAR = 1\n" "  BAR = 1\n", "duplicate_enum.emb"
        )
        errors = error.filter_errors(symbol_resolver.resolve_symbols(ir))
        self.assertEqual(
            [
                [
                    error.error(
                        "duplicate_enum.emb",
                        ir.module[0].type[0].enumeration.value[1].name.source_location,
                        "Duplicate name 'BAR'",
                    ),
                    error.note(
                        "duplicate_enum.emb",
                        ir.module[0].type[0].enumeration.value[0].name.source_location,
                        "Original definition",
                    ),
                ]
            ],
            errors,
        )

    def test_ambiguous_name(self):
        # struct UInt will be ambiguous with the external UInt in the prelude.
        ir = self._construct_ir(
            "struct UInt:\n"
            "  0 [+4]  Int:8[4]  field\n"
            "struct Foo:\n"
            "  0 [+4]  UInt  bar\n",
            "ambiguous.emb",
        )
        errors = error.filter_errors(symbol_resolver.resolve_symbols(ir))
        # Find the UInt definition in the prelude.
        for type_ir in ir.module[1].type:
            if type_ir.name.name.text == "UInt":
                prelude_uint = type_ir
                break
        ambiguous_type_ir = ir.module[0].type[1].structure.field[0].type.atomic_type
        self.assertEqual(
            [
                [
                    error.error(
                        "ambiguous.emb",
                        ambiguous_type_ir.reference.source_name[0].source_location,
                        "Ambiguous name 'UInt'",
                    ),
                    error.note(
                        "", prelude_uint.name.source_location, "Possible resolution"
                    ),
                    error.note(
                        "ambiguous.emb",
                        ir.module[0].type[0].name.source_location,
                        "Possible resolution",
                    ),
                ]
            ],
            errors,
        )

    def test_missing_name(self):
        ir = self._construct_ir("struct Foo:\n" "  0 [+4]  Bar  field\n", "missing.emb")
        errors = error.filter_errors(symbol_resolver.resolve_symbols(ir))
        missing_type_ir = ir.module[0].type[0].structure.field[0].type.atomic_type
        self.assertEqual(
            [
                [
                    error.error(
                        "missing.emb",
                        missing_type_ir.reference.source_name[0].source_location,
                        "No candidate for 'Bar'",
                    )
                ]
            ],
            errors,
        )

    def test_missing_leading_name(self):
        ir = self._construct_ir(
            "struct Foo:\n" "  0 [+Num.FOUR]  UInt  field\n", "missing.emb"
        )
        errors = error.filter_errors(symbol_resolver.resolve_symbols(ir))
        missing_expr_ir = ir.module[0].type[0].structure.field[0].location.size
        self.assertEqual(
            [
                [
                    error.error(
                        "missing.emb",
                        missing_expr_ir.constant_reference.source_name[
                            0
                        ].source_location,
                        "No candidate for 'Num'",
                    )
                ]
            ],
            errors,
        )

    def test_missing_trailing_name(self):
        ir = self._construct_ir(
            "struct Foo:\n"
            "  0 [+Num.FOUR]  UInt  field\n"
            "enum Num:\n"
            "  THREE = 3\n",
            "missing.emb",
        )
        errors = error.filter_errors(symbol_resolver.resolve_symbols(ir))
        missing_expr_ir = ir.module[0].type[0].structure.field[0].location.size
        self.assertEqual(
            [
                [
                    error.error(
                        "missing.emb",
                        missing_expr_ir.constant_reference.source_name[
                            1
                        ].source_location,
                        "No candidate for 'FOUR'",
                    )
                ]
            ],
            errors,
        )

    def test_missing_middle_name(self):
        ir = self._construct_ir(
            "struct Foo:\n"
            "  0 [+Num.NaN.FOUR]  UInt  field\n"
            "enum Num:\n"
            "  FOUR = 4\n",
            "missing.emb",
        )
        errors = error.filter_errors(symbol_resolver.resolve_symbols(ir))
        missing_expr_ir = ir.module[0].type[0].structure.field[0].location.size
        self.assertEqual(
            [
                [
                    error.error(
                        "missing.emb",
                        missing_expr_ir.constant_reference.source_name[
                            1
                        ].source_location,
                        "No candidate for 'NaN'",
                    )
                ]
            ],
            errors,
        )

    def test_inner_resolution(self):
        ir = self._construct_ir(
            "struct OuterStruct:\n"
            "\n"
            "  struct InnerStruct2:\n"
            "    0 [+1]  InnerStruct.InnerEnum  inner_enum\n"
            "\n"
            "  struct InnerStruct:\n"
            "    enum InnerEnum:\n"
            "      ONE = 1\n"
            "\n"
            "    0 [+1]  InnerEnum  inner_enum\n"
            "\n"
            "  0 [+InnerStruct.InnerEnum.ONE]  InnerStruct.InnerEnum  inner_enum\n",
            "nested.emb",
        )
        errors = symbol_resolver.resolve_symbols(ir)
        self.assertFalse(errors)
        outer_struct = ir.module[0].type[0]
        inner_struct = outer_struct.subtype[1]
        inner_struct_2 = outer_struct.subtype[0]
        inner_enum = inner_struct.subtype[0]
        self.assertEqual(
            ["OuterStruct", "InnerStruct"],
            list(inner_struct.name.canonical_name.object_path),
        )
        self.assertEqual(
            ["OuterStruct", "InnerStruct", "InnerEnum"],
            list(inner_enum.name.canonical_name.object_path),
        )
        self.assertEqual(
            ["OuterStruct", "InnerStruct2"],
            list(inner_struct_2.name.canonical_name.object_path),
        )
        outer_field = outer_struct.structure.field[0]
        outer_field_end_ref = outer_field.location.size.constant_reference
        self.assertEqual(
            ["OuterStruct", "InnerStruct", "InnerEnum", "ONE"],
            list(outer_field_end_ref.canonical_name.object_path),
        )
        self.assertEqual(
            ["OuterStruct", "InnerStruct", "InnerEnum"],
            list(outer_field.type.atomic_type.reference.canonical_name.object_path),
        )
        inner_field_2_type = inner_struct_2.structure.field[0].type.atomic_type
        self.assertEqual(
            ["OuterStruct", "InnerStruct", "InnerEnum"],
            list(inner_field_2_type.reference.canonical_name.object_path),
        )

    def test_resolution_against_anonymous_bits(self):
        ir = self._construct_ir(
            "struct Struct:\n"
            "  0 [+1]  bits:\n"
            "    7 [+1]  Flag  last_packet\n"
            "    5 [+2]  enum  inline_inner_enum:\n"
            "      AA = 0\n"
            "      BB = 1\n"
            "      CC = 2\n"
            "      DD = 3\n"
            "    0 [+5]  UInt  header_size (h)\n"
            "  0 [+h]  UInt:8[]  header_bytes\n"
            "\n"
            "struct Struct2:\n"
            "  0 [+1]  Struct.InlineInnerEnum  value\n",
            "anonymity.emb",
        )
        errors = symbol_resolver.resolve_symbols(ir)
        self.assertFalse(errors)
        struct1 = ir.module[0].type[0]
        struct1_bits_field = struct1.structure.field[0]
        struct1_bits_field_type = struct1_bits_field.type.atomic_type.reference
        struct1_byte_field = struct1.structure.field[4]
        inner_bits = struct1.subtype[0]
        inner_enum = struct1.subtype[1]
        self.assertTrue(inner_bits.HasField("structure"))
        self.assertTrue(inner_enum.HasField("enumeration"))
        self.assertTrue(inner_bits.name.is_anonymous)
        self.assertFalse(inner_enum.name.is_anonymous)
        self.assertEqual(
            ["Struct", "InlineInnerEnum"],
            list(inner_enum.name.canonical_name.object_path),
        )
        self.assertEqual(
            ["Struct", "InlineInnerEnum", "AA"],
            list(inner_enum.enumeration.value[0].name.canonical_name.object_path),
        )
        self.assertEqual(
            list(inner_bits.name.canonical_name.object_path),
            list(struct1_bits_field_type.canonical_name.object_path),
        )
        self.assertEqual(2, len(inner_bits.name.canonical_name.object_path))
        self.assertEqual(
            ["Struct", "header_size"],
            list(
                struct1_byte_field.location.size.field_reference.path[
                    0
                ].canonical_name.object_path
            ),
        )

    def test_duplicate_name_in_different_inline_bits(self):
        ir = self._construct_ir(
            "struct Struct:\n"
            "  0 [+1]  bits:\n"
            "    7 [+1]  Flag  a\n"
            "  1 [+1]  bits:\n"
            "    0 [+1]  Flag  a\n",
            "duplicate_in_anon.emb",
        )
        errors = error.filter_errors(symbol_resolver.resolve_symbols(ir))
        supertype = ir.module[0].type[0]
        self.assertEqual(
            [
                [
                    error.error(
                        "duplicate_in_anon.emb",
                        supertype.structure.field[3].name.source_location,
                        "Duplicate name 'a'",
                    ),
                    error.note(
                        "duplicate_in_anon.emb",
                        supertype.structure.field[1].name.source_location,
                        "Original definition",
                    ),
                ]
            ],
            errors,
        )

    def test_duplicate_name_in_same_inline_bits(self):
        ir = self._construct_ir(
            "struct Struct:\n"
            "  0 [+1]  bits:\n"
            "    7 [+1]  Flag  a\n"
            "    0 [+1]  Flag  a\n",
            "duplicate_in_anon.emb",
        )
        errors = symbol_resolver.resolve_symbols(ir)
        supertype = ir.module[0].type[0]
        self.assertEqual(
            [
                [
                    error.error(
                        "duplicate_in_anon.emb",
                        supertype.structure.field[2].name.source_location,
                        "Duplicate name 'a'",
                    ),
                    error.note(
                        "duplicate_in_anon.emb",
                        supertype.structure.field[1].name.source_location,
                        "Original definition",
                    ),
                ]
            ],
            error.filter_errors(errors),
        )

    def test_import_type_resolution(self):
        importer = 'import "ed.emb" as ed\n' "struct Ff:\n" "  0 [+1]  ed.Gg  gg\n"
        imported = "struct Gg:\n" "  0 [+1]  UInt  qq\n"
        ir = self._construct_ir_multiple(
            {"ed.emb": imported, "er.emb": importer}, "er.emb"
        )
        errors = symbol_resolver.resolve_symbols(ir)
        self.assertEqual([], errors)

    def test_duplicate_import_name(self):
        importer = (
            'import "ed.emb" as ed\n'
            'import "ed.emb" as ed\n'
            "struct Ff:\n"
            "  0 [+1]  ed.Gg  gg\n"
        )
        imported = "struct Gg:\n" "  0 [+1]  UInt  qq\n"
        ir = self._construct_ir_multiple(
            {"ed.emb": imported, "er.emb": importer}, "er.emb"
        )
        errors = symbol_resolver.resolve_symbols(ir)
        # Note: the error is on import[2] duplicating import[1] because the implicit
        # prelude import is import[0].
        self.assertEqual(
            [
                [
                    error.error(
                        "er.emb",
                        ir.module[0].foreign_import[2].local_name.source_location,
                        "Duplicate name 'ed'",
                    ),
                    error.note(
                        "er.emb",
                        ir.module[0].foreign_import[1].local_name.source_location,
                        "Original definition",
                    ),
                ]
            ],
            errors,
        )

    def test_import_enum_resolution(self):
        importer = (
            'import "ed.emb" as ed\n'
            "struct Ff:\n"
            "  if ed.Gg.GG == ed.Gg.GG:\n"
            "    0 [+1]  UInt  gg\n"
        )
        imported = "enum Gg:\n" "  GG = 0\n"
        ir = self._construct_ir_multiple(
            {"ed.emb": imported, "er.emb": importer}, "er.emb"
        )
        errors = symbol_resolver.resolve_symbols(ir)
        self.assertEqual([], errors)

    def test_that_double_import_names_are_syntactically_invalid(self):
        # There are currently no checks in resolve_symbols that it is not possible
        # to get to symbols imported by another module, because it is syntactically
        # invalid.  This may change in the future, in which case this test should be
        # fixed by adding an explicit check to resolve_symbols and checking the
        # error message here.
        importer = 'import "ed.emb" as ed\n' "struct Ff:\n" "  0 [+1]  ed.ed2.Gg  gg\n"
        imported = 'import "ed2.emb" as ed2\n'
        imported2 = "struct Gg:\n" "  0 [+1]  UInt  qq\n"
        unused_ir, unused_debug_info, errors = glue.parse_emboss_file(
            "er.emb",
            test_util.dict_file_reader(
                {"ed.emb": imported, "ed2.emb": imported2, "er.emb": importer}
            ),
            stop_before_step="resolve_symbols",
        )
        assert errors

    def test_no_error_when_inline_name_aliases_outer_name(self):
        # The inline enum's complete type should be Foo.Foo.  During parsing, the
        # name is set to just "Foo", but symbol resolution should a) select the
        # correct Foo, and b) not complain that multiple Foos could match.
        ir = self._construct_ir(
            "struct Foo:\n" "  0 [+1]  enum  foo:\n" "    BAR = 0\n"
        )
        errors = symbol_resolver.resolve_symbols(ir)
        self.assertEqual([], errors)
        field = ir.module[0].type[0].structure.field[0]
        self.assertEqual(
            ["Foo", "Foo"],
            list(field.type.atomic_type.reference.canonical_name.object_path),
        )

    def test_no_error_when_inline_name_in_anonymous_bits_aliases_outer_name(self):
        # There is an extra layer of complexity when an inline type appears inside
        # of an inline bits.
        ir = self._construct_ir(
            "struct Foo:\n"
            "  0 [+1]  bits:\n"
            "    0 [+4]  enum  foo:\n"
            "      BAR = 0\n"
        )
        errors = symbol_resolver.resolve_symbols(ir)
        self.assertEqual([], error.filter_errors(errors))
        field = ir.module[0].type[0].subtype[0].structure.field[0]
        self.assertEqual(
            ["Foo", "Foo"],
            list(field.type.atomic_type.reference.canonical_name.object_path),
        )


class ResolveFieldReferencesTest(unittest.TestCase):
    """Tests for symbol_resolver.resolve_field_references()."""

    def _construct_ir_multiple(self, file_dict, primary_emb_name):
        ir, unused_debug_info, errors = glue.parse_emboss_file(
            primary_emb_name,
            test_util.dict_file_reader(file_dict),
            stop_before_step="resolve_field_references",
        )
        assert not errors
        return ir

    def _construct_ir(self, emb_text, name="happy.emb"):
        return self._construct_ir_multiple({name: emb_text}, name)

    def test_subfield_resolution(self):
        ir = self._construct_ir(
            "struct Ff:\n"
            "  0 [+1]      Gg        gg\n"
            "  1 [+gg.qq]  UInt:8[]  data\n"
            "struct Gg:\n"
            "  0 [+1]      UInt    qq\n",
            "subfield.emb",
        )
        errors = symbol_resolver.resolve_field_references(ir)
        self.assertFalse(errors)
        ff = ir.module[0].type[0]
        location_end_path = ff.structure.field[1].location.size.field_reference.path
        self.assertEqual(
            ["Ff", "gg"], list(location_end_path[0].canonical_name.object_path)
        )
        self.assertEqual(
            ["Gg", "qq"], list(location_end_path[1].canonical_name.object_path)
        )

    def test_aliased_subfield_resolution(self):
        ir = self._construct_ir(
            "struct Ff:\n"
            "  0 [+1]      Gg        real_gg\n"
            "  1 [+gg.qq]  UInt:8[]  data\n"
            "  let gg = real_gg\n"
            "struct Gg:\n"
            "  0 [+1]      UInt    real_qq\n"
            "  let qq = real_qq",
            "subfield.emb",
        )
        errors = symbol_resolver.resolve_field_references(ir)
        self.assertFalse(errors)
        ff = ir.module[0].type[0]
        location_end_path = ff.structure.field[1].location.size.field_reference.path
        self.assertEqual(
            ["Ff", "gg"], list(location_end_path[0].canonical_name.object_path)
        )
        self.assertEqual(
            ["Gg", "qq"], list(location_end_path[1].canonical_name.object_path)
        )

    def test_aliased_aliased_subfield_resolution(self):
        ir = self._construct_ir(
            "struct Ff:\n"
            "  0 [+1]      Gg        really_real_gg\n"
            "  1 [+gg.qq]  UInt:8[]  data\n"
            "  let gg = real_gg\n"
            "  let real_gg = really_real_gg\n"
            "struct Gg:\n"
            "  0 [+1]      UInt    qq\n",
            "subfield.emb",
        )
        errors = symbol_resolver.resolve_field_references(ir)
        self.assertFalse(errors)
        ff = ir.module[0].type[0]
        location_end_path = ff.structure.field[1].location.size.field_reference.path
        self.assertEqual(
            ["Ff", "gg"], list(location_end_path[0].canonical_name.object_path)
        )
        self.assertEqual(
            ["Gg", "qq"], list(location_end_path[1].canonical_name.object_path)
        )

    def test_subfield_resolution_fails(self):
        ir = self._construct_ir(
            "struct Ff:\n"
            "  0 [+1]      Gg        gg\n"
            "  1 [+gg.rr]  UInt:8[]  data\n"
            "struct Gg:\n"
            "  0 [+1]      UInt    qq\n",
            "subfield.emb",
        )
        errors = error.filter_errors(symbol_resolver.resolve_field_references(ir))
        self.assertEqual(
            [
                [
                    error.error(
                        "subfield.emb",
                        ir.module[0]
                        .type[0]
                        .structure.field[1]
                        .location.size.field_reference.path[1]
                        .source_name[0]
                        .source_location,
                        "No candidate for 'rr'",
                    )
                ]
            ],
            errors,
        )

    def test_subfield_resolution_failure_shortcuts_further_resolution(self):
        ir = self._construct_ir(
            "struct Ff:\n"
            "  0 [+1]         Gg        gg\n"
            "  1 [+gg.rr.qq]  UInt:8[]  data\n"
            "struct Gg:\n"
            "  0 [+1]         UInt    qq\n",
            "subfield.emb",
        )
        errors = error.filter_errors(symbol_resolver.resolve_field_references(ir))
        self.assertEqual(
            [
                [
                    error.error(
                        "subfield.emb",
                        ir.module[0]
                        .type[0]
                        .structure.field[1]
                        .location.size.field_reference.path[1]
                        .source_name[0]
                        .source_location,
                        "No candidate for 'rr'",
                    )
                ]
            ],
            errors,
        )

    def test_subfield_resolution_failure_with_aliased_name(self):
        ir = self._construct_ir(
            "struct Ff:\n"
            "  0 [+1]      Gg        gg\n"
            "  1 [+gg.gg]  UInt:8[]  data\n"
            "struct Gg:\n"
            "  0 [+1]      UInt    qq\n",
            "subfield.emb",
        )
        errors = error.filter_errors(symbol_resolver.resolve_field_references(ir))
        self.assertEqual(
            [
                [
                    error.error(
                        "subfield.emb",
                        ir.module[0]
                        .type[0]
                        .structure.field[1]
                        .location.size.field_reference.path[1]
                        .source_name[0]
                        .source_location,
                        "No candidate for 'gg'",
                    )
                ]
            ],
            errors,
        )

    def test_subfield_resolution_failure_with_array(self):
        ir = self._construct_ir(
            "struct Ff:\n"
            "  0 [+1]      Gg[1]     gg\n"
            "  1 [+gg.qq]  UInt:8[]  data\n"
            "struct Gg:\n"
            "  0 [+1]      UInt    qq\n",
            "subfield.emb",
        )
        errors = error.filter_errors(symbol_resolver.resolve_field_references(ir))
        self.assertEqual(
            [
                [
                    error.error(
                        "subfield.emb",
                        ir.module[0]
                        .type[0]
                        .structure.field[1]
                        .location.size.field_reference.path[0]
                        .source_name[0]
                        .source_location,
                        "Cannot access member of array 'gg'",
                    )
                ]
            ],
            errors,
        )

    def test_subfield_resolution_failure_with_int(self):
        ir = self._construct_ir(
            "struct Ff:\n"
            "  0 [+1]      UInt      gg_source\n"
            "  1 [+gg.qq]  UInt:8[]  data\n"
            "  let gg = gg_source + 1\n",
            "subfield.emb",
        )
        errors = error.filter_errors(symbol_resolver.resolve_field_references(ir))
        error_field = ir.module[0].type[0].structure.field[1]
        error_reference = error_field.location.size.field_reference
        error_location = error_reference.path[0].source_name[0].source_location
        self.assertEqual(
            [
                [
                    error.error(
                        "subfield.emb",
                        error_location,
                        "Cannot access member of noncomposite field 'gg'",
                    )
                ]
            ],
            errors,
        )

    def test_subfield_resolution_failure_with_int_no_cascade(self):
        ir = self._construct_ir(
            "struct Ff:\n"
            "  0 [+1]    UInt      gg_source\n"
            "  1 [+qqx]  UInt:8[]  data\n"
            "  let gg = gg_source + 1\n"
            "  let yy = gg.no_field\n"
            "  let qqx = yy.x\n"
            "  let qqy = yy.y\n",
            "subfield.emb",
        )
        errors = error.filter_errors(symbol_resolver.resolve_field_references(ir))
        error_field = ir.module[0].type[0].structure.field[3]
        error_reference = error_field.read_transform.field_reference
        error_location = error_reference.path[0].source_name[0].source_location
        self.assertEqual(
            [
                [
                    error.error(
                        "subfield.emb",
                        error_location,
                        "Cannot access member of noncomposite field 'gg'",
                    )
                ]
            ],
            errors,
        )

    def test_subfield_resolution_failure_with_abbreviation(self):
        ir = self._construct_ir(
            "struct Ff:\n"
            "  0 [+1]     Gg        gg\n"
            "  1 [+gg.q]  UInt:8[]  data\n"
            "struct Gg:\n"
            "  0 [+1]     UInt    qq (q)\n",
            "subfield.emb",
        )
        errors = error.filter_errors(symbol_resolver.resolve_field_references(ir))
        self.assertEqual(
            [
                # TODO(bolms): Make the error message clearer, in this case.
                [
                    error.error(
                        "subfield.emb",
                        ir.module[0]
                        .type[0]
                        .structure.field[1]
                        .location.size.field_reference.path[1]
                        .source_name[0]
                        .source_location,
                        "No candidate for 'q'",
                    )
                ]
            ],
            errors,
        )


if __name__ == "__main__":
    unittest.main()
