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

"""End-to-end smoke test: generate a dissector and run it under TShark.

This loads a generated dissector into a real Wireshark/TShark and checks that
synthetic packets decode as expected, covering the pieces that golden tests
can't: that the emitted Lua actually loads and that conditional fields and
variable-length arrays behave correctly at dissection time.

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

# Mirrors testdata/wireshark_dynamic.emb; kept inline so the test is
# self-contained and needs no runfiles lookup.
_EMB = """\
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
"""


def _generate_lua():
    ir, _, errors = glue.parse_emboss_file(
        "vproto.emb", test_util.dict_file_reader({"vproto.emb": _EMB})
    )
    assert not errors, errors
    text, gen_errors = dissector_generator.generate_dissector(ir)
    assert not gen_errors, gen_errors
    return text


@unittest.skipUnless(
    _TSHARK and _TEXT2PCAP, "tshark and text2pcap are required for this test"
)
class TsharkSmokeTest(unittest.TestCase):
    """Runs the generated dissector against synthetic packets in TShark."""

    @classmethod
    def setUpClass(cls):
        cls._dir = tempfile.mkdtemp(prefix="emboss_lua_tshark_")
        cls._lua = os.path.join(cls._dir, "vproto.lua")
        with open(cls._lua, "w") as lua_file:
            lua_file.write(_generate_lua())

    def _dissect(self, payload_bytes):
        """Wraps `payload_bytes` in UDP (dest 13370) and returns TShark's tree."""
        hex_path = os.path.join(self._dir, "packet.hex")
        with open(hex_path, "w") as hex_file:
            hex_file.write("000000 " + " ".join(payload_bytes) + "\n")
        pcap_path = os.path.join(self._dir, "packet.pcap")
        subprocess.run(
            [_TEXT2PCAP, "-u", "4444,13370", hex_path, pcap_path],
            check=True,
            capture_output=True,
        )
        result = subprocess.run(
            [_TSHARK, "-r", pcap_path, "-X", "lua_script:" + self._lua, "-V"],
            check=True,
            capture_output=True,
            text=True,
        )
        # A broken script surfaces as a "Lua: Error ..." line on stderr.
        self.assertNotIn("Lua: Error", result.stderr)
        return result.stdout

    def test_data_message_has_variable_payload_and_no_error_code(self):
        # DATA, count=3, two padding bytes, then payload 0xAA 0xBB 0xCC.
        out = self._dissect(["01", "03", "00", "00", "aa", "bb", "cc"])
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
        out = self._dissect(["02", "00", "12", "34"])
        self.assertIn("msg_type: ERROR (2)", out)
        self.assertIn("count: 0", out)
        self.assertIn("error_code: 4660", out)
        self.assertNotIn("payload:", out)


if __name__ == "__main__":
    unittest.main()
