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

"""Attributes in the Wireshark/Lua backend and associated metadata."""

import enum

from compiler.util import attribute_util


BACK_END = "wireshark"


class Attribute(str, enum.Enum):
    """Attributes available in the Wireshark/Lua backend."""

    PROTOCOL = "protocol"
    FILTER = "filter"
    # When set on a module, the generated dissector auto-registers itself
    # against one or more Wireshark dissector tables at load time.  The value
    # is a Wireshark-display-filter-style string such as
    # `udp.port == 12345`, `tcp.port == 80 or udp.port == 80`, or
    # `ethertype == 0x88AB`.  Both `or` and `||` are accepted as separators
    # and integer patterns may be written in decimal or `0x`-prefixed hex.
    REGISTER_ON = "register_on"
    # The unqualified name of the struct to use as the root dispatch entry
    # for the top-level `<proto>.dissector` function.  If unset, the first
    # `struct` declared at module scope is used.
    ROOT = "root"


TYPES = {
    Attribute.PROTOCOL: attribute_util.STRING,
    Attribute.FILTER: attribute_util.STRING,
    Attribute.REGISTER_ON: attribute_util.STRING,
    Attribute.ROOT: attribute_util.STRING,
}


class Scope(set, enum.Enum):
    """Allowed scopes for Wireshark/Lua backend attributes.

    Each entry is a set of (Attribute, default?) tuples, the first value being
    the attribute itself, the second value being a boolean value indicating
    whether the attribute is allowed to be defaulted in that scope."""

    MODULE = {
        (Attribute.PROTOCOL, False),
        (Attribute.REGISTER_ON, False),
        (Attribute.ROOT, False),
    }
    STRUCT = {
        (Attribute.FILTER, False),
    }
    BITS = {
        (Attribute.FILTER, False),
    }
    STRUCT_PHYSICAL_FIELD = {
        (Attribute.FILTER, False),
    }
