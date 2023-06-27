# Copyright 2023 Google LLC
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

"""Tests for attribute_checker.py."""

import unittest
from compiler.back_end.cpp import header_generator
from compiler.front_end import glue
from compiler.util import error
from compiler.util import ir_pb2
from compiler.util import test_util

def _make_ir_from_emb(emb_text, name="m.emb"):
  ir, unused_debug_info, errors = glue.parse_emboss_file(
      name,
      test_util.dict_file_reader({name: emb_text}))
  assert not errors
  return ir


class NormalizeIrTest(unittest.TestCase):

  def test_accepts_string_attribute(self):
    ir = _make_ir_from_emb('[(cpp) namespace: "foo"]\n')
    self.assertEqual([], header_generator.generate_header(ir)[1])

  def test_rejects_wrong_type_for_string_attribute(self):
    ir = _make_ir_from_emb("[(cpp) namespace: 9]\n")
    attr = ir.module[0].attribute[0]
    self.assertEqual([[
        error.error("m.emb", attr.value.source_location,
                    "Attribute '(cpp) namespace' must have a string value.")
    ]], header_generator.generate_header(ir)[1])

  def test_rejects_emboss_internal_attribute_with_back_end_specifier(self):
    ir = _make_ir_from_emb('[(cpp) byte_order: "LittleEndian"]\n')
    attr = ir.module[0].attribute[0]
    self.assertEqual([[
        error.error("m.emb", attr.name.source_location,
                    "Unknown attribute '(cpp) byte_order' on module 'm.emb'.")
    ]], header_generator.generate_header(ir)[1])

  def test_accepts_enum_case(self):
    mod_ir = _make_ir_from_emb('[(cpp) $default enum_case: "kCamelCase"]')
    self.assertEqual([], header_generator.generate_header(mod_ir)[1])
    enum_ir = _make_ir_from_emb('enum Foo:\n'
                                '  [(cpp) $default enum_case: "kCamelCase"]\n'
                                '  BAR = 1\n'
                                '  BAZ = 2\n')
    self.assertEqual([], header_generator.generate_header(enum_ir)[1])
    enum_value_ir = _make_ir_from_emb('enum Foo:\n'
                                      '  BAR = 1  [(cpp) enum_case: "kCamelCase"]\n'
                                      '  BAZ = 2\n'
                                      '    [(cpp) enum_case: "kCamelCase"]\n')
    self.assertEqual([], header_generator.generate_header(enum_value_ir)[1])
    enum_in_struct_ir = _make_ir_from_emb('struct Outer:\n'
                                          '  [(cpp) $default enum_case: "kCamelCase"]\n'
                                          '  enum Inner:\n'
                                          '    BAR = 1\n'
                                          '    BAZ = 2\n')
    self.assertEqual([], header_generator.generate_header(enum_in_struct_ir)[1])
    enum_in_bits_ir = _make_ir_from_emb('bits Outer:\n'
                                        '  [(cpp) $default enum_case: "kCamelCase"]\n'
                                        '  enum Inner:\n'
                                        '    BAR = 1\n'
                                        '    BAZ = 2\n')
    self.assertEqual([], header_generator.generate_header(enum_in_bits_ir)[1])
    enum_ir = _make_ir_from_emb('enum Foo:\n'
                                '  [(cpp) $default enum_case: "SHOUTY_CASE,"]\n'
                                '  BAR = 1\n'
                                '  BAZ = 2\n')
    self.assertEqual([], header_generator.generate_header(enum_ir)[1])
    enum_ir = _make_ir_from_emb('enum Foo:\n'
                                '  [(cpp) $default enum_case: "SHOUTY_CASE   ,kCamelCase"]\n'
                                '  BAR = 1\n'
                                '  BAZ = 2\n')
    self.assertEqual([], header_generator.generate_header(enum_ir)[1])

  def test_rejects_bad_enum_case_at_start(self):
    ir = _make_ir_from_emb('enum Foo:\n'
                           '  [(cpp) $default enum_case: "SHORTY_CASE, kCamelCase"]\n'
                           '  BAR = 1\n'
                           '  BAZ = 2\n')
    attr = ir.module[0].type[0].attribute[0]

    bad_case_source_location = ir_pb2.Location()
    bad_case_source_location.CopyFrom(attr.value.source_location)
    # Location of SHORTY_CASE in the attribute line.
    bad_case_source_location.start.column = 30
    bad_case_source_location.end.column = 41

    self.assertEqual([[
        error.error("m.emb", bad_case_source_location,
                    'Unsupported enum case "SHORTY_CASE", '
                    'supported cases are: SHOUTY_CASE, kCamelCase.')
    ]], header_generator.generate_header(ir)[1])

  def test_rejects_bad_enum_case_in_middle(self):
    ir = _make_ir_from_emb('enum Foo:\n'
                           '  [(cpp) $default enum_case: "SHOUTY_CASE, bad_CASE, kCamelCase"]\n'
                           '  BAR = 1\n'
                           '  BAZ = 2\n')
    attr = ir.module[0].type[0].attribute[0]

    bad_case_source_location = ir_pb2.Location()
    bad_case_source_location.CopyFrom(attr.value.source_location)
    # Location of bad_CASE in the attribute line.
    bad_case_source_location.start.column = 43
    bad_case_source_location.end.column = 51

    self.assertEqual([[
        error.error("m.emb", bad_case_source_location,
                    'Unsupported enum case "bad_CASE", '
                    'supported cases are: SHOUTY_CASE, kCamelCase.')
    ]], header_generator.generate_header(ir)[1])

  def test_rejects_bad_enum_case_at_end(self):
    ir = _make_ir_from_emb('enum Foo:\n'
                           '  [(cpp) $default enum_case: "SHOUTY_CASE, kCamelCase, BAD_case"]\n'
                           '  BAR = 1\n'
                           '  BAZ = 2\n')
    attr = ir.module[0].type[0].attribute[0]

    bad_case_source_location = ir_pb2.Location()
    bad_case_source_location.CopyFrom(attr.value.source_location)
    # Location of BAD_case in the attribute line.
    bad_case_source_location.start.column = 55
    bad_case_source_location.end.column = 63

    self.assertEqual([[
        error.error("m.emb", bad_case_source_location,
                    'Unsupported enum case "BAD_case", '
                    'supported cases are: SHOUTY_CASE, kCamelCase.')
    ]], header_generator.generate_header(ir)[1])

  def test_rejects_duplicate_enum_case(self):
    ir = _make_ir_from_emb('enum Foo:\n'
                           '  [(cpp) $default enum_case: "SHOUTY_CASE, SHOUTY_CASE"]\n'
                           '  BAR = 1\n'
                           '  BAZ = 2\n')
    attr = ir.module[0].type[0].attribute[0]

    bad_case_source_location = ir_pb2.Location()
    bad_case_source_location.CopyFrom(attr.value.source_location)
    # Location of the second SHOUTY_CASE in the attribute line.
    bad_case_source_location.start.column = 43
    bad_case_source_location.end.column = 54

    self.assertEqual([[
        error.error("m.emb", bad_case_source_location,
                    'Duplicate enum case "SHOUTY_CASE".')
    ]], header_generator.generate_header(ir)[1])


  def test_rejects_empty_enum_case(self):
    # Double comma
    ir = _make_ir_from_emb('enum Foo:\n'
                           '  [(cpp) $default enum_case: "SHOUTY_CASE,, kCamelCase"]\n'
                           '  BAR = 1\n'
                           '  BAZ = 2\n')
    attr = ir.module[0].type[0].attribute[0]

    bad_case_source_location = ir_pb2.Location()
    bad_case_source_location.CopyFrom(attr.value.source_location)
    # Location excess comma.
    bad_case_source_location.start.column = 42
    bad_case_source_location.end.column = 42

    self.assertEqual([[
        error.error("m.emb", bad_case_source_location,
                    'Empty enum case (excess comma).')
    ]], header_generator.generate_header(ir)[1])

    # Leading comma
    ir = _make_ir_from_emb('enum Foo:\n'
                           '  [(cpp) $default enum_case: ", SHOUTY_CASE, kCamelCase"]\n'
                           '  BAR = 1\n'
                           '  BAZ = 2\n')

    bad_case_source_location.start.column = 30
    bad_case_source_location.end.column = 30

    self.assertEqual([[
        error.error("m.emb", bad_case_source_location,
                    'Empty enum case (excess comma).')
    ]], header_generator.generate_header(ir)[1])

    # Excess trailing comma
    ir = _make_ir_from_emb('enum Foo:\n'
                           '  [(cpp) $default enum_case: "SHOUTY_CASE, kCamelCase,,"]\n'
                           '  BAR = 1\n'
                           '  BAZ = 2\n')

    bad_case_source_location.start.column = 54
    bad_case_source_location.end.column = 54

    self.assertEqual([[
        error.error("m.emb", bad_case_source_location,
                    'Empty enum case (excess comma).')
    ]], header_generator.generate_header(ir)[1])

    # Whitespace enum case
    ir = _make_ir_from_emb('enum Foo:\n'
                           '  [(cpp) $default enum_case: "SHOUTY_CASE,   , kCamelCase"]\n'
                           '  BAR = 1\n'
                           '  BAZ = 2\n')

    bad_case_source_location.start.column = 45
    bad_case_source_location.end.column = 45

    self.assertEqual([[
        error.error("m.emb", bad_case_source_location,
                    'Empty enum case (excess comma).')
    ]], header_generator.generate_header(ir)[1])


if __name__ == "__main__":
    unittest.main()
