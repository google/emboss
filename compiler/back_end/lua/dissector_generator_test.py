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
    """Value-name tables are keyed by the raw field value, per field width."""

    _EMB = (
        '[expected_back_ends: "cpp, wireshark"]\n'
        '[$default byte_order: "BigEndian"]\n'
        "enum Kind:\n"
        "  WIDGET   = 0\n"
        "  LARGE    = 2000\n"
        "  DUP      = LARGE\n"
        "  MAX32BIT = 4294967295\n"
        "  MAX64BIT = 18446744073709551615\n"
        "enum Unused:\n"
        "  NOT_USED = 1\n"
        "struct Xs:\n"
        "  0 [+1]  Kind  k8\n"
        "  1 [+4]  Kind  k32\n"
        "  5 [+8]  Kind  k64\n"
    )

    def test_one_table_per_width_holding_the_values_that_fit(self):
        text, errors = _generate(self._EMB)
        self.assertEqual([], errors)
        self.assertIn(
            "local enums = {}\n" 'enums.Kind_8 = {\n  [0] = "WIDGET",\n}\n', text
        )
        self.assertIn(
            "enums.Kind_32 = {\n"
            '  [0] = "WIDGET",\n'
            '  [2000] = "LARGE",\n'
            '  [4294967295] = "MAX32BIT",\n'
            "}\n",
            text,
        )
        self.assertIn(
            'ProtoField.uint8("emboss_m.Xs.k8", "k8", base.DEC, enums.Kind_8)', text
        )
        self.assertIn(
            'ProtoField.uint32("emboss_m.Xs.k32", "k32", base.DEC, enums.Kind_32)', text
        )

    def test_duplicate_values_keep_the_first_name(self):
        text, errors = _generate(self._EMB)
        self.assertEqual([], errors)
        self.assertNotIn("DUP", text)

    def test_values_of_2_to_the_63_and_above_are_hex_literals(self):
        # A decimal literal that large becomes a float in Lua and matches no
        # integer field value.
        text, errors = _generate(self._EMB)
        self.assertEqual([], errors)
        self.assertIn('  [0xFFFFFFFFFFFFFFFF] = "MAX64BIT",\n}\n', text)
        self.assertNotIn("18446744073709551615", text)

    def test_unused_enums_get_no_table(self):
        text, errors = _generate(self._EMB)
        self.assertEqual([], errors)
        self.assertNotIn("enums.Unused", text)

    def test_negative_values_are_keyed_by_their_encoding(self):
        text, errors = _generate(
            '[expected_back_ends: "cpp, wireshark"]\n'
            '[$default byte_order: "BigEndian"]\n'
            "enum Sgn:\n"
            "  [is_signed: true]\n"
            "  NEG  = -1\n"
            "  ZERO = 0\n"
            "enum Small:\n"
            "  [is_signed: true]\n"
            "  [maximum_bits: 8]\n"
            "  MINUS_ONE = -1\n"
            "struct Xs:\n"
            "  0 [+1]  Sgn    s8\n"
            "  1 [+8]  Sgn    s64\n"
            "  9 [+1]  Small  sm8\n"
        )
        self.assertEqual([], errors)
        # -1 in a 64-bit enum is 0xFF..FF, which a one-byte field can't hold
        # (the C++ back end reads 0xFF as 255 there, matching no name either).
        self.assertIn('enums.Sgn_8 = {\n  [0] = "ZERO",\n}\n', text)
        self.assertIn(
            'enums.Sgn_64 = {\n  [0xFFFFFFFFFFFFFFFF] = "NEG",\n  [0] = "ZERO",\n}\n',
            text,
        )
        self.assertIn('enums.Small_8 = {\n  [255] = "MINUS_ONE",\n}\n', text)

    def test_enum_with_no_value_fitting_the_width_gets_no_valuestring(self):
        text, errors = _generate(
            '[expected_back_ends: "cpp, wireshark"]\n'
            '[$default byte_order: "BigEndian"]\n'
            "enum Big:\n"
            "  HUGE = 70000\n"
            "struct Xs:\n"
            "  0 [+1]  Big  b\n"
        )
        self.assertEqual([], errors)
        self.assertNotIn("enums", text)
        self.assertIn('ProtoField.uint8("emboss_m.Xs.b", "b")', text)

    def test_enum_in_bits_uses_the_bit_fields_width(self):
        text, errors = _generate(self._EMB + "  13 [+1]  bits:\n    0 [+4]  Kind  k4\n")
        self.assertEqual([], errors)
        self.assertIn('enums.Kind_4 = {\n  [0] = "WIDGET",\n}\n', text)
        self.assertIn(
            'ProtoField.uint8("emboss_m.Xs.k4", "k4", base.DEC, enums.Kind_4, 0x0F)',
            text,
        )


class FilterCompositionTest(unittest.TestCase):

    def test_default_filter_uses_struct_and_field_names(self):
        text, errors = _generate(
            '[expected_back_ends: "cpp, wireshark"]\n'
            '[$default byte_order: "LittleEndian"]\n'
            "struct Foo:\n"
            "  0 [+4]  UInt  bar\n"
        )
        self.assertEqual([], errors)
        self.assertIn('ProtoField.uint32("emboss_m.Foo.bar", "bar")', text)

    def test_module_filter_override_replaces_root(self):
        text, errors = _generate(
            '[expected_back_ends: "cpp, wireshark"]\n'
            '[$default byte_order: "LittleEndian"]\n'
            '[(wireshark) protocol: "p"]\n'
            '[(wireshark) filter: "modf"]\n'
            "struct Foo:\n"
            "  0 [+4]  UInt  bar\n"
        )
        self.assertEqual([], errors)
        self.assertIn('ProtoField.uint32("modf.Foo.bar", "bar")', text)
        # The protocol itself keeps its own name.
        self.assertIn('local p_proto = Proto("p", "p (Emboss)")', text)

    def test_struct_filter_override(self):
        text, errors = _generate(
            '[expected_back_ends: "cpp, wireshark"]\n'
            '[$default byte_order: "LittleEndian"]\n'
            '[(wireshark) protocol: "p"]\n'
            "struct Foo:\n"
            '  [(wireshark) filter: "frob"]\n'
            "  0 [+4]  UInt  bar\n"
        )
        self.assertEqual([], errors)
        self.assertIn('ProtoField.uint32("p.frob.bar", "bar")', text)

    def test_field_filter_override(self):
        text, errors = _generate(
            '[expected_back_ends: "cpp, wireshark"]\n'
            '[$default byte_order: "LittleEndian"]\n'
            '[(wireshark) protocol: "p"]\n'
            "struct Foo:\n"
            "  0 [+4]  UInt  bar\n"
            '    [(wireshark) filter: "baz"]\n'
        )
        self.assertEqual([], errors)
        self.assertIn('ProtoField.uint32("p.Foo.baz", "bar")', text)


class DocumentationTest(unittest.TestCase):

    def test_double_dash_doc_appears_in_description(self):
        text, errors = _generate(
            '[expected_back_ends: "cpp, wireshark"]\n'
            '[$default byte_order: "LittleEndian"]\n'
            "struct Foo:\n"
            "  0 [+4]  UInt  bar\n"
            "    -- The bar value.\n"
        )
        self.assertEqual([], errors)
        self.assertIn('"The bar value."', text)

    def test_hash_comment_does_not_appear(self):
        text, errors = _generate(
            '[expected_back_ends: "cpp, wireshark"]\n'
            '[$default byte_order: "LittleEndian"]\n'
            "struct Foo:\n"
            "  # This is a hash comment, not documentation.\n"
            "  0 [+4]  UInt  bar\n"
        )
        self.assertEqual([], errors)
        self.assertNotIn("hash comment", text)


class AttributeValidationTest(unittest.TestCase):

    def test_rejects_unknown_wireshark_attribute(self):
        text, errors = _generate(
            '[expected_back_ends: "cpp, wireshark"]\n' '[(wireshark) bogus: "x"]\n'
        )
        self.assertEqual("", text)
        self.assertTrue(errors)
        joined = "\n".join(msg.message for sublist in errors for msg in sublist)
        self.assertIn("Unknown attribute", joined)

    def test_rejects_wrong_type_for_protocol(self):
        text, errors = _generate(
            '[expected_back_ends: "cpp, wireshark"]\n' "[(wireshark) protocol: 5]\n"
        )
        self.assertEqual("", text)
        self.assertTrue(errors)

    def test_rejects_invalid_register_on(self):
        text, errors = _generate(
            '[expected_back_ends: "cpp, wireshark"]\n'
            '[(wireshark) register_on: "garbage"]\n'
            "struct Foo:\n"
            "  0 [+1]  UInt  x\n"
        )
        self.assertEqual("", text)
        joined = "\n".join(msg.message for sublist in errors for msg in sublist)
        self.assertIn("register_on", joined)

    def test_rejects_unknown_root(self):
        text, errors = _generate(
            '[expected_back_ends: "cpp, wireshark"]\n'
            '[(wireshark) root: "DoesNotExist"]\n'
            "struct Foo:\n"
            "  0 [+1]  UInt  x\n"
        )
        self.assertEqual("", text)
        joined = "\n".join(msg.message for sublist in errors for msg in sublist)
        self.assertIn("DoesNotExist", joined)


class RegisterOnEmissionTest(unittest.TestCase):

    def test_emits_each_table(self):
        text, errors = _generate(
            '[expected_back_ends: "cpp, wireshark"]\n'
            '[$default byte_order: "BigEndian"]\n'
            '[(wireshark) register_on: "udp.port == 12345 or tcp.port == 12345"]\n'
            "struct Foo:\n"
            "  0 [+1]  UInt  x\n"
        )
        self.assertEqual([], errors)
        self.assertIn('DissectorTable.get("udp.port"):add(12345, emboss_m_proto)', text)
        self.assertIn('DissectorTable.get("tcp.port"):add(12345, emboss_m_proto)', text)


class ProtocolNameTest(unittest.TestCase):

    def test_default_name_is_prefixed_basename(self):
        # Unprefixed basenames such as `data`, `udp` or `frame` collide with
        # Wireshark's built-in protocols and make the script fail to load.
        text, errors = _generate(
            '[expected_back_ends: "cpp, wireshark"]\n'
            '[$default byte_order: "BigEndian"]\n'
            "struct Pkt:\n"
            "  0 [+1]  UInt  x\n",
            name="data.emb",
        )
        self.assertEqual([], errors)
        self.assertIn(
            'local emboss_data_proto = Proto("emboss_data", "emboss_data (Emboss)")',
            text,
        )
        self.assertIn('ProtoField.uint8("emboss_data.Pkt.x", "x")', text)
        self.assertIn('pinfo.cols.protocol = "EMBOSS_DATA"', text)

    def test_protocol_attribute_is_used_verbatim(self):
        text, errors = _generate(
            '[expected_back_ends: "cpp, wireshark"]\n'
            '[$default byte_order: "BigEndian"]\n'
            '[(wireshark) protocol: "myproto"]\n'
            "struct Pkt:\n"
            "  0 [+1]  UInt  x\n",
            name="data.emb",
        )
        self.assertEqual([], errors)
        self.assertIn('Proto("myproto", "myproto (Emboss)")', text)
        self.assertNotIn("emboss_data", text)


class RootSelectionTest(unittest.TestCase):

    def test_uses_first_struct_by_default(self):
        text, errors = _generate(
            '[expected_back_ends: "cpp, wireshark"]\n'
            '[$default byte_order: "LittleEndian"]\n'
            "struct First:\n"
            "  0 [+1]  UInt  a\n"
            "struct Second:\n"
            "  0 [+1]  UInt  b\n"
        )
        self.assertEqual([], errors)
        self.assertIn("dissect.First(buffer, pinfo, tree, 0)", text)

    def test_root_override(self):
        text, errors = _generate(
            '[expected_back_ends: "cpp, wireshark"]\n'
            '[$default byte_order: "LittleEndian"]\n'
            '[(wireshark) root: "Second"]\n'
            "struct First:\n"
            "  0 [+1]  UInt  a\n"
            "struct Second:\n"
            "  0 [+1]  UInt  b\n"
        )
        self.assertEqual([], errors)
        self.assertIn("dissect.Second(buffer, pinfo, tree, 0)", text)


class NestedStructTest(unittest.TestCase):

    def test_recurses_into_nested_struct(self):
        text, errors = _generate(
            '[expected_back_ends: "cpp, wireshark"]\n'
            '[$default byte_order: "LittleEndian"]\n'
            "struct Inner:\n"
            "  0 [+1]  UInt  i\n"
            "struct Outer:\n"
            "  0 [+1]  Inner  inner\n"
            "  1 [+1]  UInt   tail\n"
        )
        self.assertEqual([], errors)
        self.assertIn("dissect.Inner(buffer, pinfo, subtree, offset + 0)", text)


class BitsTest(unittest.TestCase):
    """`bits` are read LSB-first from the enclosing field, in its byte order."""

    _TWO_BYTE_ORDERS = (
        '[expected_back_ends: "cpp, wireshark"]\n'
        '[$default byte_order: "LittleEndian"]\n'
        "struct Le:\n"
        "  0 [+2]  bits:\n"
        "    0  [+4]  UInt  lo\n"
        "    4  [+4]  UInt  mid\n"
        "    15 [+1]  Flag  top\n"
        "struct Be:\n"
        '  [$default byte_order: "BigEndian"]\n'
        "  0 [+2]  bits:\n"
        "    0  [+4]  UInt  lo\n"
        "    15 [+1]  Flag  top\n"
    )

    def test_masks_count_from_least_significant_bit(self):
        text, errors = _generate(self._TWO_BYTE_ORDERS)
        self.assertEqual([], errors)
        # Bit 0 is the lowest-order bit of the 16-bit container integer, so
        # `0 [+4]` is 0x000F, not 0xF000.
        self.assertIn(
            'ProtoField.uint16("emboss_m.Le.lo", "lo", base.DEC, nil, 0x000F)', text
        )
        self.assertIn(
            'ProtoField.uint16("emboss_m.Le.mid", "mid", base.DEC, nil, 0x00F0)',
            text,
        )
        self.assertIn(
            'ProtoField.bool("emboss_m.Le.top", "top", 16, nil, 0x8000)', text
        )

    def test_byte_order_comes_from_enclosing_field(self):
        text, errors = _generate(self._TWO_BYTE_ORDERS)
        self.assertEqual([], errors)
        self.assertRegex(
            text,
            r"dissect\.Le_EmbossReservedAnonymousField\d+\(buffer, pinfo, subtree, "
            r"offset \+ 0, true\)",
        )
        self.assertRegex(
            text,
            r"dissect\.Be_EmbossReservedAnonymousField\d+\(buffer, pinfo, subtree, "
            r"offset \+ 0, false\)",
        )
        # The anonymous bits' fields go straight into the parent's subtree,
        # using add_le or add according to the parameter.
        self.assertRegex(
            text,
            r"function dissect\.Le_EmbossReservedAnonymousField\d+\(buffer, pinfo, "
            r"tree, offset, little_endian\)\n"
            r"  local range = buffer\(offset, 2\)\n"
            r"  local add = little_endian and tree\.add_le or tree\.add\n"
            r'  add\(tree, f\["Le\.lo"\], range\)\n',
        )

    def test_container_is_the_enclosing_field_not_the_bits_extent(self):
        # `0 [+8] UInt x` inside a 4-byte big-endian field is the low byte of
        # a 32-bit integer, i.e. the fourth byte on the wire.
        text, errors = _generate(
            '[expected_back_ends: "cpp, wireshark"]\n'
            '[$default byte_order: "BigEndian"]\n'
            "struct Pkt:\n"
            "  0 [+4]  bits:\n"
            "    0 [+8]  UInt  x\n"
        )
        self.assertEqual([], errors)
        self.assertIn(
            'ProtoField.uint32("emboss_m.Pkt.x", "x", base.DEC, nil, 0x000000FF)',
            text,
        )
        self.assertIn("local range = buffer(offset, 4)", text)

    def test_wide_container_uses_uint64_and_full_width_mask(self):
        text, errors = _generate(
            '[expected_back_ends: "cpp, wireshark"]\n'
            '[$default byte_order: "LittleEndian"]\n'
            "struct Wide:\n"
            "  0 [+5]  bits:\n"
            "    4 [+32]  UInt  wide\n"
        )
        self.assertEqual([], errors)
        self.assertIn(
            'ProtoField.uint64("emboss_m.Wide.wide", "wide", base.DEC, nil, '
            "0x0FFFFFFFF0)",
            text,
        )

    def test_named_bits_get_a_subtree_and_runtime_byte_order(self):
        text, errors = _generate(
            '[expected_back_ends: "cpp, wireshark"]\n'
            '[$default byte_order: "LittleEndian"]\n'
            "bits Flags:\n"
            "  0 [+1]  Flag  a\n"
            "  1 [+7]  UInt  rest\n"
            "struct Pkt:\n"
            "  0 [+1]  Flags     flags\n"
            "  1 [+2]  Flags[2]  more\n"
        )
        self.assertEqual([], errors)
        self.assertIn('ProtoField.bool("emboss_m.Flags.a", "a", 8, nil, 0x01)', text)
        self.assertIn(
            "function dissect.Flags(buffer, pinfo, tree, offset, little_endian)\n"
            '  local subtree = tree:add(emboss_m_proto, buffer(offset, 1), "Flags")\n'
            "  local range = buffer(offset, 1)\n"
            "  local add = little_endian and subtree.add_le or subtree.add\n"
            '  add(subtree, f["Flags.a"], range)\n',
            text,
        )
        self.assertIn("dissect.Flags(buffer, pinfo, subtree, offset + 0, true)", text)
        self.assertIn(
            "dissect.Flags(buffer, pinfo, subtree, offset + 1 + i * 1, true)", text
        )

    def test_nested_bits_are_flattened_into_the_container(self):
        text, errors = _generate(
            '[expected_back_ends: "cpp, wireshark"]\n'
            '[$default byte_order: "BigEndian"]\n'
            "bits Inner:\n"
            "  0 [+2]  UInt  v\n"
            "bits Outer:\n"
            "  0 [+4]  UInt   lo\n"
            "  4 [+2]  Inner  inner\n"
            "  6 [+2]  UInt   hi\n"
            "struct Pkt:\n"
            "  0 [+1]  Outer  outer\n"
        )
        self.assertEqual([], errors)
        self.assertIn(
            'ProtoField.uint8("emboss_m.Outer.inner.v", "v", base.DEC, nil, 0x30)',
            text,
        )
        self.assertIn('add(subtree, f["Outer.inner.v"], range)', text)
        # Inner is only ever nested, so its own dissector reads a 1-byte
        # container.
        self.assertIn(
            "function dissect.Inner(buffer, pinfo, tree, offset, little_endian)\n"
            '  local subtree = tree:add(emboss_m_proto, buffer(offset, 1), "Inner")\n',
            text,
        )

    def test_bits_cannot_be_root(self):
        text, errors = _generate(
            '[expected_back_ends: "cpp, wireshark"]\n'
            "bits Flags:\n"
            "  0 [+1]  Flag  a\n"
            "  1 [+7]  UInt  rest\n"
            "struct Pkt:\n"
            "  0 [+1]  Flags  flags\n"
        )
        self.assertEqual([], errors)
        self.assertIn("dissect.Pkt(buffer, pinfo, tree, 0)", text)


class BcdTest(unittest.TestCase):
    """`Bcd` fields are decoded by the emitted add_bcd helper."""

    _EMB = (
        '[expected_back_ends: "cpp, wireshark"]\n'
        '[$default byte_order: "BigEndian"]\n'
        "struct Msg:\n"
        "  0 [+1]    Bcd        n\n"
        "  1 [+2]    Bcd        plain\n"
        '    [byte_order: "LittleEndian"]\n'
        "  3 [+n]    UInt:8[n]  data\n"
        "  3+n [+2]  Bcd:8[2]   pair\n"
        "  if n == 1:\n"
        "    5+n [+1]  UInt     one\n"
    )

    def test_helper_is_emitted_once_and_only_when_needed(self):
        text, errors = _generate(self._EMB)
        self.assertEqual([], errors)
        self.assertEqual(1, text.count("local function add_bcd("))
        text, errors = _generate(
            '[expected_back_ends: "cpp, wireshark"]\n'
            '[$default byte_order: "BigEndian"]\n'
            "struct Msg:\n"
            "  0 [+1]  UInt  x\n"
        )
        self.assertEqual([], errors)
        self.assertNotIn("add_bcd", text)

    def test_fields_are_added_through_the_helper(self):
        text, errors = _generate(self._EMB)
        self.assertEqual([], errors)
        # The ProtoField stays an unsigned integer (so it can be filtered on);
        # the helper passes the decoded value explicitly.
        self.assertIn(
            'f["Msg.plain"] = ProtoField.uint16("emboss_m.Msg.plain", "plain")', text
        )
        self.assertIn(
            'add_bcd(subtree, f["Msg.plain"], buffer(offset + 1, 2), true)', text
        )
        self.assertIn(
            'add_bcd(subtree, f["Msg.pair"], buffer(offset + (3 + val_Msg_n) + '
            "i * 1, 1), false)",
            text,
        )

    def test_referenced_value_comes_from_the_helper_and_is_nil_guarded(self):
        text, errors = _generate(self._EMB)
        self.assertEqual([], errors)
        self.assertIn(
            'local val_Msg_n = add_bcd(subtree, f["Msg.n"], buffer(offset + 0, 1), '
            "false)",
            text,
        )
        self.assertNotIn("buffer(offset + 0, 1):uint()", text)
        # add_bcd returns nil for an invalid encoding, so every field that
        # depends on the value is dissected only when it decoded.
        self.assertIn(
            "if val_Msg_n ~= nil then\n"
            "    -- array field data (val_Msg_n elements)\n"
            "    for i = 0, val_Msg_n - 1 do\n",
            text,
        )
        self.assertIn("if val_Msg_n ~= nil and (val_Msg_n == 1) then", text)


class FloatTest(unittest.TestCase):

    def test_float_fields_take_no_base_or_mask(self):
        text, errors = _generate(
            '[expected_back_ends: "cpp, wireshark"]\n'
            '[$default byte_order: "BigEndian"]\n'
            "struct Flt:\n"
            "  0 [+4]  Float  x\n"
            "    -- The x value.\n"
            "  4 [+8]  Float  y\n"
        )
        self.assertEqual([], errors)
        # `ProtoField.float(abbr, name, valuestring, desc)`: a base argument
        # in the third position makes Wireshark reject the field.
        self.assertIn(
            'ProtoField.float("emboss_m.Flt.x", "x", nil, "The x value.")', text
        )
        self.assertIn('ProtoField.double("emboss_m.Flt.y", "y")', text)


_FM = dissector_generator.ir_data.FunctionMapping


def _const_expr(value):
    return dissector_generator.ir_data.Expression(
        constant=dissector_generator.ir_data.NumericConstant(value=str(value))
    )


def _bool_expr(value):
    return dissector_generator.ir_data.Expression(
        boolean_constant=dissector_generator.ir_data.BooleanConstant(value=value)
    )


def _field_ref_expr(*object_path):
    return dissector_generator.ir_data.Expression(
        field_reference=dissector_generator.ir_data.FieldReference(
            path=[
                dissector_generator.ir_data.Reference(
                    canonical_name=dissector_generator.ir_data.CanonicalName(
                        module_file="m.emb", object_path=list(object_path)
                    )
                )
            ]
        )
    )


def _fn_expr(mapping, *args):
    return dissector_generator.ir_data.Expression(
        function=dissector_generator.ir_data.Function(function=mapping, args=list(args))
    )


class ExpressionTranslationTest(unittest.TestCase):
    """Unit tests for the Emboss-expression -> Lua translator."""

    @staticmethod
    def _resolve(field_reference):
        path = list(field_reference.path[0].canonical_name.object_path)
        return "val_x" if path == ["M", "x"] else None

    def _translate(self, expression):
        return dissector_generator._translate_expression(expression, self._resolve)

    def test_numeric_constant(self):
        self.assertEqual("7", self._translate(_const_expr(7)))

    def test_boolean_constant(self):
        self.assertEqual("true", self._translate(_bool_expr(True)))
        self.assertEqual("false", self._translate(_bool_expr(False)))

    def test_resolved_field_reference(self):
        self.assertEqual("val_x", self._translate(_field_ref_expr("M", "x")))

    def test_unresolved_field_reference(self):
        self.assertIsNone(self._translate(_field_ref_expr("M", "other")))

    def test_equality(self):
        self.assertEqual(
            "(val_x == 3)",
            self._translate(
                _fn_expr(_FM.EQUALITY, _field_ref_expr("M", "x"), _const_expr(3))
            ),
        )

    def test_inequality_uses_lua_operator(self):
        self.assertEqual(
            "(val_x ~= 0)",
            self._translate(
                _fn_expr(_FM.INEQUALITY, _field_ref_expr("M", "x"), _const_expr(0))
            ),
        )

    def test_comparison_and_logical_operators(self):
        expr = _fn_expr(
            _FM.AND,
            _fn_expr(_FM.LESS, _field_ref_expr("M", "x"), _const_expr(10)),
            _fn_expr(_FM.GREATER_OR_EQUAL, _field_ref_expr("M", "x"), _const_expr(2)),
        )
        self.assertEqual("((val_x < 10) and (val_x >= 2))", self._translate(expr))

    def test_arithmetic(self):
        expr = _fn_expr(_FM.ADDITION, _field_ref_expr("M", "x"), _const_expr(1))
        self.assertEqual("(val_x + 1)", self._translate(expr))

    def test_maximum_maps_to_math_max(self):
        expr = _fn_expr(_FM.MAXIMUM, _field_ref_expr("M", "x"), _const_expr(1))
        self.assertEqual("math.max(val_x, 1)", self._translate(expr))

    def test_unsupported_choice_returns_none(self):
        expr = _fn_expr(
            _FM.CHOICE, _field_ref_expr("M", "x"), _const_expr(1), _const_expr(2)
        )
        self.assertIsNone(self._translate(expr))

    def test_unresolved_subexpression_propagates_none(self):
        expr = _fn_expr(_FM.EQUALITY, _field_ref_expr("M", "other"), _const_expr(1))
        self.assertIsNone(self._translate(expr))


class ConditionalFieldTest(unittest.TestCase):

    def test_wraps_conditional_field_in_if(self):
        text, errors = _generate(
            '[expected_back_ends: "cpp, wireshark"]\n'
            '[$default byte_order: "BigEndian"]\n'
            "struct Msg:\n"
            "  0 [+1]  UInt  a\n"
            "  if a == 1:\n"
            "    1 [+1]  UInt  b\n"
        )
        self.assertEqual([], errors)
        self.assertIn("local val_Msg_a = buffer(offset + 0, 1):uint()", text)
        # The conditional read is nested under the translated `if`.
        self.assertIn(
            '  if (val_Msg_a == 1) then\n    subtree:add(f["Msg.b"], '
            "buffer(offset + 1, 1))\n  end",
            text,
        )

    def test_no_value_capture_without_reference(self):
        text, errors = _generate(
            '[expected_back_ends: "cpp, wireshark"]\n'
            '[$default byte_order: "BigEndian"]\n'
            "struct Msg:\n"
            "  0 [+1]  UInt  a\n"
            "  1 [+1]  UInt  b\n"
        )
        self.assertEqual([], errors)
        self.assertNotIn("local val_", text)

    def test_little_endian_capture_uses_le_reader(self):
        text, errors = _generate(
            '[expected_back_ends: "cpp, wireshark"]\n'
            '[$default byte_order: "LittleEndian"]\n'
            "struct Msg:\n"
            "  0 [+2]  UInt  a\n"
            "  if a == 1:\n"
            "    2 [+1]  UInt  b\n"
        )
        self.assertEqual([], errors)
        self.assertIn("local val_Msg_a = buffer(offset + 0, 2):le_uint()", text)

    def test_condition_on_wide_field_is_skipped(self):
        # A reference to an 8-byte field can't be captured as a Lua number, so
        # the dependent field is skipped rather than mistranslated.
        text, errors = _generate(
            '[expected_back_ends: "cpp, wireshark"]\n'
            '[$default byte_order: "BigEndian"]\n'
            "struct Msg:\n"
            "  0 [+8]  UInt  big\n"
            "  if big == 1:\n"
            "    8 [+1]  UInt  b\n"
        )
        self.assertEqual([], errors)
        self.assertIn("-- skipped conditional field b (unsupported condition)", text)


class VariableLengthArrayTest(unittest.TestCase):

    def test_dynamic_count_loop(self):
        text, errors = _generate(
            '[expected_back_ends: "cpp, wireshark"]\n'
            '[$default byte_order: "BigEndian"]\n'
            "struct Msg:\n"
            "  0 [+1]      UInt       n\n"
            "  1 [+n]      UInt:8[n]  data\n"
        )
        self.assertEqual([], errors)
        self.assertIn("local val_Msg_n = buffer(offset + 0, 1):uint()", text)
        self.assertIn("for i = 0, val_Msg_n - 1 do", text)
        self.assertIn('subtree:add(f["Msg.data"], buffer(offset + 1 + i * 1, 1))', text)

    def test_auto_sized_array_skipped(self):
        text, errors = _generate(
            '[expected_back_ends: "cpp, wireshark"]\n'
            '[$default byte_order: "BigEndian"]\n'
            "struct Msg:\n"
            "  0 [+1]  UInt       n\n"
            "  1 [+n]  UInt:8[]   data\n"
        )
        self.assertEqual([], errors)
        self.assertIn("-- skipped auto-sized array field data", text)


if __name__ == "__main__":
    unittest.main()
