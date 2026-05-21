# Copyright 2026 Google LLC
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

"""Tests for the Wireshark/Lua dissector generator."""

import unittest

from compiler.back_end.lua import dissector_generator
from compiler.front_end import glue
from compiler.util import test_util


def _make_ir(emb_text, name="m.emb"):
    ir, _, errors = glue.parse_emboss_file(
        name, test_util.dict_file_reader({name: emb_text})
    )
    assert not errors, errors
    return ir


def _generate(emb_text, name="m.emb"):
    return dissector_generator.generate_dissector(_make_ir(emb_text, name))


class SanitizeIdentifierTest(unittest.TestCase):
    sanitize = staticmethod(dissector_generator._sanitize_lua_identifier)

    def test_passes_through_simple(self):
        self.assertEqual("foo_bar", self.sanitize("foo_bar"))
        self.assertEqual("Foo123", self.sanitize("Foo123"))

    def test_replaces_special_chars(self):
        self.assertEqual("foo_bar_baz", self.sanitize("foo-bar.baz"))
        self.assertEqual("a_b_c_d", self.sanitize("a:b:c:d"))

    def test_leading_digit(self):
        self.assertEqual("_123abc", self.sanitize("123abc"))

    def test_reserved_word(self):
        self.assertEqual("end_", self.sanitize("end"))
        self.assertEqual("local_", self.sanitize("local"))

    def test_empty(self):
        self.assertEqual("_", self.sanitize(""))


class IntegerWidthMappingTest(unittest.TestCase):
    map_fn = staticmethod(dissector_generator._wireshark_int_type)

    def test_unsigned(self):
        self.assertEqual("uint8", self.map_fn("UInt", 8))
        self.assertEqual("uint16", self.map_fn("UInt", 16))
        self.assertEqual("uint16", self.map_fn("UInt", 12))  # round up
        self.assertEqual("uint32", self.map_fn("UInt", 24))
        self.assertEqual("uint32", self.map_fn("UInt", 32))
        self.assertEqual("uint64", self.map_fn("UInt", 40))
        self.assertEqual("uint64", self.map_fn("UInt", 64))

    def test_signed(self):
        self.assertEqual("int8", self.map_fn("Int", 8))
        self.assertEqual("int16", self.map_fn("Int", 16))
        self.assertEqual("int32", self.map_fn("Int", 32))
        self.assertEqual("int64", self.map_fn("Int", 64))


class ParseRegisterOnTest(unittest.TestCase):
    parse = staticmethod(dissector_generator._parse_register_on)

    def test_single(self):
        regs, err = self.parse("udp.port == 12345")
        self.assertIsNone(err)
        self.assertEqual([("udp.port", 12345)], regs)

    def test_multiple_with_or(self):
        regs, err = self.parse("udp.port == 12345 or tcp.port == 80")
        self.assertIsNone(err)
        self.assertEqual([("udp.port", 12345), ("tcp.port", 80)], regs)

    def test_multiple_with_double_pipe(self):
        regs, err = self.parse("udp.port == 53 || tcp.port == 53")
        self.assertIsNone(err)
        self.assertEqual([("udp.port", 53), ("tcp.port", 53)], regs)

    def test_hex_pattern(self):
        regs, err = self.parse("ethertype == 0x88AB")
        self.assertIsNone(err)
        self.assertEqual([("ethertype", 0x88AB)], regs)

    def test_rejects_garbage(self):
        regs, err = self.parse("garbage")
        self.assertEqual([], regs)
        self.assertIn("register_on", err)

    def test_rejects_empty(self):
        regs, err = self.parse("")
        self.assertEqual([], regs)
        self.assertIn("register_on", err)


class EnumValuesTableTest(unittest.TestCase):

    def test_emits_value_strings(self):
        text, errors = _generate(
            "[expected_back_ends: \"cpp, wireshark\"]\n"
            "enum Kind:\n"
            "  ZERO = 0\n"
            "  ONE  = 1\n"
        )
        self.assertEqual([], errors)
        self.assertIn("local Kind_VALUES = {", text)
        self.assertIn('[0] = "ZERO",', text)
        self.assertIn('[1] = "ONE",', text)


class FilterCompositionTest(unittest.TestCase):

    def test_default_filter_uses_struct_and_field_names(self):
        text, errors = _generate(
            "[expected_back_ends: \"cpp, wireshark\"]\n"
            "[$default byte_order: \"LittleEndian\"]\n"
            "struct Foo:\n"
            "  0 [+4]  UInt  bar\n"
        )
        self.assertEqual([], errors)
        self.assertIn('ProtoField.uint32("m.Foo.bar", "bar")', text)

    def test_struct_filter_override(self):
        text, errors = _generate(
            "[expected_back_ends: \"cpp, wireshark\"]\n"
            "[$default byte_order: \"LittleEndian\"]\n"
            "[(wireshark) protocol: \"p\"]\n"
            "struct Foo:\n"
            "  [(wireshark) filter: \"frob\"]\n"
            "  0 [+4]  UInt  bar\n"
        )
        self.assertEqual([], errors)
        self.assertIn('ProtoField.uint32("p.frob.bar", "bar")', text)

    def test_field_filter_override(self):
        text, errors = _generate(
            "[expected_back_ends: \"cpp, wireshark\"]\n"
            "[$default byte_order: \"LittleEndian\"]\n"
            "[(wireshark) protocol: \"p\"]\n"
            "struct Foo:\n"
            "  0 [+4]  UInt  bar\n"
            "    [(wireshark) filter: \"baz\"]\n"
        )
        self.assertEqual([], errors)
        self.assertIn('ProtoField.uint32("p.Foo.baz", "bar")', text)


class DocumentationTest(unittest.TestCase):

    def test_double_dash_doc_appears_in_description(self):
        text, errors = _generate(
            "[expected_back_ends: \"cpp, wireshark\"]\n"
            "[$default byte_order: \"LittleEndian\"]\n"
            "struct Foo:\n"
            "  0 [+4]  UInt  bar\n"
            "    -- The bar value.\n"
        )
        self.assertEqual([], errors)
        self.assertIn('"The bar value."', text)

    def test_hash_comment_does_not_appear(self):
        text, errors = _generate(
            "[expected_back_ends: \"cpp, wireshark\"]\n"
            "[$default byte_order: \"LittleEndian\"]\n"
            "struct Foo:\n"
            "  # This is a hash comment, not documentation.\n"
            "  0 [+4]  UInt  bar\n"
        )
        self.assertEqual([], errors)
        self.assertNotIn("hash comment", text)


class AttributeValidationTest(unittest.TestCase):

    def test_rejects_unknown_wireshark_attribute(self):
        text, errors = _generate(
            "[expected_back_ends: \"cpp, wireshark\"]\n"
            "[(wireshark) bogus: \"x\"]\n"
        )
        self.assertEqual("", text)
        self.assertTrue(errors)
        joined = "\n".join(
            msg.message for sublist in errors for msg in sublist
        )
        self.assertIn("Unknown attribute", joined)

    def test_rejects_wrong_type_for_protocol(self):
        text, errors = _generate(
            "[expected_back_ends: \"cpp, wireshark\"]\n"
            "[(wireshark) protocol: 5]\n"
        )
        self.assertEqual("", text)
        self.assertTrue(errors)

    def test_rejects_invalid_register_on(self):
        text, errors = _generate(
            "[expected_back_ends: \"cpp, wireshark\"]\n"
            "[(wireshark) register_on: \"garbage\"]\n"
            "struct Foo:\n"
            "  0 [+1]  UInt  x\n"
        )
        self.assertEqual("", text)
        joined = "\n".join(
            msg.message for sublist in errors for msg in sublist
        )
        self.assertIn("register_on", joined)

    def test_rejects_unknown_root(self):
        text, errors = _generate(
            "[expected_back_ends: \"cpp, wireshark\"]\n"
            "[(wireshark) root: \"DoesNotExist\"]\n"
            "struct Foo:\n"
            "  0 [+1]  UInt  x\n"
        )
        self.assertEqual("", text)
        joined = "\n".join(
            msg.message for sublist in errors for msg in sublist
        )
        self.assertIn("DoesNotExist", joined)


class RegisterOnEmissionTest(unittest.TestCase):

    def test_emits_each_table(self):
        text, errors = _generate(
            "[expected_back_ends: \"cpp, wireshark\"]\n"
            "[$default byte_order: \"BigEndian\"]\n"
            "[(wireshark) register_on: \"udp.port == 12345 or tcp.port == 12345\"]\n"
            "struct Foo:\n"
            "  0 [+1]  UInt  x\n"
        )
        self.assertEqual([], errors)
        self.assertIn(
            'DissectorTable.get("udp.port"):add(12345, m_proto)', text
        )
        self.assertIn(
            'DissectorTable.get("tcp.port"):add(12345, m_proto)', text
        )


class RootSelectionTest(unittest.TestCase):

    def test_uses_first_struct_by_default(self):
        text, errors = _generate(
            "[expected_back_ends: \"cpp, wireshark\"]\n"
            "[$default byte_order: \"LittleEndian\"]\n"
            "struct First:\n"
            "  0 [+1]  UInt  a\n"
            "struct Second:\n"
            "  0 [+1]  UInt  b\n"
        )
        self.assertEqual([], errors)
        self.assertIn("dissect_First(buffer, pinfo, tree, 0)", text)

    def test_root_override(self):
        text, errors = _generate(
            "[expected_back_ends: \"cpp, wireshark\"]\n"
            "[$default byte_order: \"LittleEndian\"]\n"
            "[(wireshark) root: \"Second\"]\n"
            "struct First:\n"
            "  0 [+1]  UInt  a\n"
            "struct Second:\n"
            "  0 [+1]  UInt  b\n"
        )
        self.assertEqual([], errors)
        self.assertIn("dissect_Second(buffer, pinfo, tree, 0)", text)


class NestedStructTest(unittest.TestCase):

    def test_recurses_into_nested_struct(self):
        text, errors = _generate(
            "[expected_back_ends: \"cpp, wireshark\"]\n"
            "[$default byte_order: \"LittleEndian\"]\n"
            "struct Inner:\n"
            "  0 [+1]  UInt  i\n"
            "struct Outer:\n"
            "  0 [+1]  Inner  inner\n"
            "  1 [+1]  UInt   tail\n"
        )
        self.assertEqual([], errors)
        self.assertIn("dissect_Inner(buffer, pinfo, subtree, offset + 0)", text)


if __name__ == "__main__":
    unittest.main()
