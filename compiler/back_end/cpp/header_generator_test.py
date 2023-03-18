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
from compiler.util import ir_util


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
    ]], attribute_checker.normalize_and_verify(ir))
