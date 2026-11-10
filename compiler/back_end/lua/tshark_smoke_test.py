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

"""End-to-end smoke test: generate dissectors and run them under TShark.

This loads generated dissectors into a real Wireshark/TShark and checks that
synthetic packets decode as expected, covering the pieces that golden tests
can't: that the emitted Lua actually loads and that conditional fields,
variable-length arrays and `bits` behave correctly at dissection time.

It is skipped automatically when `tshark` / `text2pcap` aren't installed (for
example in the hermetic CI sandbox), so it adds real local coverage without
breaking environments that lack Wireshark.
"""

import os
import shutil
import subprocess
import tempfile
import unittest

from compiler.back_end.lua import dissector_generator
from compiler.front_end import glue
from compiler.util import test_util

_TSHARK = shutil.which("tshark")
_TEXT2PCAP = shutil.which("text2pcap")

# Each fixture is (UDP port the dissector registers on, Emboss source).  They
# are kept inline so the test is self-contained and needs no runfiles lookup.
_FIXTURES = {
    # Mirrors testdata/wireshark_dynamic.emb.
    "vproto": (
        13370,
        """\
[expected_back_ends: "cpp, wireshark"]
[$default byte_order: "BigEndian"]
[(wireshark) protocol: "vproto"]
[(wireshark) root: "Message"]
[(wireshark) register_on: "udp.port == 13370"]

enum MsgType:
  PING  = 0
  DATA  = 1
  ERROR = 2

struct Message:
  0 [+1]      MsgType        msg_type
  1 [+1]      UInt           count
  if msg_type == MsgType.ERROR:
    2 [+2]    UInt           error_code
  4 [+count]  UInt:8[count]  payload
""",
    ),
    # `bits` in little- and big-endian fields, and one wider than 32 bits.
    "bits": (
        13371,
        """\
[expected_back_ends: "cpp, wireshark"]
[$default byte_order: "LittleEndian"]
[(wireshark) protocol: "bitsproto"]
[(wireshark) root: "Both"]
[(wireshark) register_on: "udp.port == 13371"]

struct Le:
  0 [+2]  bits:
    0  [+4]  UInt  lo
    4  [+4]  UInt  mid
    15 [+1]  Flag  top

struct Be:
  [$default byte_order: "BigEndian"]
  0 [+2]  bits:
    0  [+4]  UInt  lo
    4  [+4]  UInt  mid
    15 [+1]  Flag  top

struct Wide:
  0 [+5]  bits:
    4 [+32]  UInt  wide

struct Both:
  0 [+2]  Le    le
  2 [+2]  Be    be
  4 [+5]  Wide  wide
""",
    ),
    # An anonymous `bits` narrower than the field holding it.
    "partial_bits": (
        13372,
        """\
[expected_back_ends: "cpp, wireshark"]
[$default byte_order: "BigEndian"]
[(wireshark) protocol: "partialproto"]
[(wireshark) register_on: "udp.port == 13372"]

struct Pkt:
  0 [+4]  bits:
    0 [+8]  UInt  x
""",
    ),
    # Packed BCD, including a BCD length that other fields depend on.
    "bcd": (
        13373,
        """\
[expected_back_ends: "cpp, wireshark"]
[$default byte_order: "BigEndian"]
[(wireshark) protocol: "bcdproto"]
[(wireshark) register_on: "udp.port == 13373"]

struct Bcdm:
  0 [+1]    Bcd        n
  1 [+1]    UInt       a
  if 0 < a < 5:
    2 [+1]  UInt       chained
  3 [+n]    UInt:8[n]  data
  3+n [+5]  Bcd        wide
  8+n [+2]  Bcd        le_val
    [byte_order: "LittleEndian"]
  10+n [+8]  Bcd       big
""",
    ),
    # Enum value names at several field widths, including values that only
    # fit wide fields and a signed enum.
    "enums": (
        13374,
        """\
[expected_back_ends: "cpp, wireshark"]
[$default byte_order: "BigEndian"]
[(wireshark) protocol: "enumsproto"]
[(wireshark) register_on: "udp.port == 13374"]

enum Kind:
  WIDGET   = 0
  LARGE    = 2000
  DUP      = LARGE
  MAX32BIT = 4294967295
  MAX64BIT = 18446744073709551615

enum Sgn:
  [is_signed: true]
  NEG  = -1
  ZERO = 0

struct Xs:
  0  [+1]  Kind  k8
  1  [+4]  Kind  k32
  5  [+8]  Kind  k64
  13 [+1]  Sgn   s8
  14 [+8]  Sgn   s64
""",
    ),
}


def _generate_lua(name, emb_text):
    file_name = name + ".emb"
    ir, _, errors = glue.parse_emboss_file(
        file_name, test_util.dict_file_reader({file_name: emb_text})
    )
    assert not errors, errors
    text, gen_errors = dissector_generator.generate_dissector(ir)
    assert not gen_errors, gen_errors
    return text


@unittest.skipUnless(
    _TSHARK and _TEXT2PCAP, "tshark and text2pcap are required for this test"
)
class TsharkSmokeTest(unittest.TestCase):
    """Runs the generated dissectors against synthetic packets in TShark."""

    @classmethod
    def setUpClass(cls):
        # Under Bazel, TEST_TMPDIR is the sandbox's writable scratch space.
        tmp = tempfile.TemporaryDirectory(dir=os.environ.get("TEST_TMPDIR"))
        cls.addClassCleanup(tmp.cleanup)
        cls._dir = tmp.name
        cls._lua = {}
        for name, (_, emb_text) in _FIXTURES.items():
            cls._lua[name] = os.path.join(cls._dir, name + ".lua")
            with open(cls._lua[name], "w") as lua_file:
                lua_file.write(_generate_lua(name, emb_text))

    def _dissect(self, fixture, payload_bytes):
        """Sends `payload_bytes` over UDP to `fixture`'s port; returns the tree."""
        port = _FIXTURES[fixture][0]
        hex_path = os.path.join(self._dir, "packet.hex")
        with open(hex_path, "w") as hex_file:
            hex_file.write("000000 " + " ".join(payload_bytes) + "\n")
        pcap_path = os.path.join(self._dir, "packet.pcap")
        subprocess.run(
            [_TEXT2PCAP, "-u", "4444,{}".format(port), hex_path, pcap_path],
            check=True,
            capture_output=True,
        )
        result = subprocess.run(
            [
                _TSHARK,
                "-r",
                pcap_path,
                "-X",
                "lua_script:" + self._lua[fixture],
                "-V",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        # A broken script surfaces as a "Lua: Error ..." line on stderr.
        self.assertNotIn("Lua: Error", result.stderr)
        return result.stdout

    def test_data_message_has_variable_payload_and_no_error_code(self):
        # DATA, count=3, two padding bytes, then payload 0xAA 0xBB 0xCC.
        out = self._dissect("vproto", ["01", "03", "00", "00", "aa", "bb", "cc"])
        self.assertIn("msg_type: DATA (1)", out)
        self.assertIn("count: 3", out)
        self.assertIn("payload: 170", out)
        self.assertIn("payload: 187", out)
        self.assertIn("payload: 204", out)
        # The conditional error_code field must be absent for non-ERROR messages.
        self.assertNotIn("error_code", out)

    def test_error_message_has_error_code_and_no_payload(self):
        # ERROR, count=0, error_code=0x1234 (4660); the var-length payload loop
        # runs zero times.
        out = self._dissect("vproto", ["02", "00", "12", "34"])
        self.assertIn("msg_type: ERROR (2)", out)
        self.assertIn("count: 0", out)
        self.assertIn("error_code: 4660", out)
        self.assertNotIn("payload:", out)

    def test_bits_follow_the_enclosing_fields_byte_order(self):
        # The same two bytes, 0x21 0x83, read as 0x8321 little-endian and
        # 0x2183 big-endian; `wide` is bits 4..35 of the little-endian 40-bit
        # value 0x0000000010.  These are the values the C++ back end reads.
        out = self._dissect(
            "bits", ["21", "83", "21", "83", "10", "00", "00", "00", "00"]
        )
        self.assertIn(".... .... .... 0001 = lo: 1", out)
        self.assertIn(".... .... 0010 .... = mid: 2", out)
        self.assertIn("1... .... .... .... = top: True", out)
        self.assertIn(".... .... .... 0011 = lo: 3", out)
        self.assertIn(".... .... 1000 .... = mid: 8", out)
        self.assertIn("0... .... .... .... = top: False", out)
        self.assertIn("= wide: 1", out)

    def test_anonymous_bits_read_the_whole_enclosing_field(self):
        # Bit 0 of a 4-byte big-endian field is in its last byte.
        out = self._dissect("partial_bits", ["01", "02", "03", "04"])
        self.assertIn("= x: 4", out)

    def test_bcd_values_are_decoded(self):
        # n = 12 (0x12 in BCD), a = 3, chained = 5, twelve data bytes, then
        # the 5-byte BCD 1234567890 and the little-endian 2-byte BCD 1234.
        out = self._dissect(
            "bcd",
            ["12", "03", "05"]
            + ["{:02x}".format(i) for i in range(1, 13)]
            + ["12", "34", "56", "78", "90", "34", "12"]
            + ["98", "76", "54", "32", "10", "98", "76", "54"],
        )
        self.assertIn("n: 12", out)
        self.assertIn("a: 3", out)
        self.assertIn("chained: 5", out)
        self.assertEqual(12, out.count("data: "))
        self.assertIn("data: 12", out)
        self.assertIn("wide: 1234567890", out)
        self.assertIn("le_val: 1234", out)
        # Sixteen digits: more than a double holds exactly.
        self.assertIn("big: 9876543210987654", out)

    def test_invalid_bcd_is_flagged_and_dependents_are_skipped(self):
        # 0x1a is not valid BCD, so `n` is unknown: the fields whose position
        # or count depend on it are left out, while independent ones remain.
        out = self._dissect(
            "bcd",
            ["1a", "03", "05"]
            + ["{:02x}".format(i) for i in range(1, 13)]
            + ["12", "34", "56", "78", "90", "34", "12"]
            + ["98", "76", "54", "32", "10", "98", "76", "54"],
        )
        self.assertIn("n: 26 [invalid BCD]", out)
        self.assertIn("chained: 5", out)
        self.assertNotIn("data: ", out)
        self.assertNotIn("wide: ", out)
        self.assertNotIn("le_val: ", out)
        self.assertNotIn("big: ", out)

    def test_enum_names_match_the_values_the_cpp_back_end_reads(self):
        # k8 = 0, k32 = 2000, k64 = s8 = s64 = all ones.
        out = self._dissect(
            "enums",
            ["00", "00", "00", "07", "d0"] + ["ff"] * 8 + ["ff"] + ["ff"] * 8,
        )
        self.assertIn("k8: WIDGET (0)", out)
        # The first name for a duplicated value wins.
        self.assertIn("k32: LARGE (2000)", out)
        self.assertNotIn("DUP", out)
        self.assertIn("k64: MAX64BIT (18446744073709551615)", out)
        # A one-byte field reads 0xFF as 255, which is not -1.
        self.assertIn("s8: Unknown (255)", out)
        self.assertIn("s64: NEG (18446744073709551615)", out)

    def test_enum_values_too_wide_for_the_field_are_unknown(self):
        out = self._dissect("enums", ["ff"] * 5 + ["00"] * 8 + ["00"] + ["00"] * 8)
        self.assertIn("k8: Unknown (255)", out)
        self.assertIn("k32: MAX32BIT (4294967295)", out)
        self.assertIn("k64: WIDGET (0)", out)
        self.assertIn("s8: ZERO (0)", out)
        self.assertIn("s64: ZERO (0)", out)


if __name__ == "__main__":
    unittest.main()
