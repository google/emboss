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

"""Attributes in the C++ backend and associated metadata."""

from enum import Enum
from compiler.util import attribute_util


class Attribute(str, Enum):
    """Attributes available in the C++ backend."""

    NAMESPACE = "namespace"
    ENUM_CASE = "enum_case"


# Types associated with C++ backend attributes.
TYPES = {
    Attribute.NAMESPACE: attribute_util.STRING,
    Attribute.ENUM_CASE: attribute_util.STRING,
}


class Scope(set, Enum):
    """Allowed scopes for C++ backend attributes.

    Each entry is a set of (Attribute, default?) tuples, the first value being
    the attribute itself, the second value being a boolean value indicating
    whether the attribute is allowed to be defaulted in that scope."""

    BITS = {
        # Bits may contain an enum definition.
        (Attribute.ENUM_CASE, True)
    }
    ENUM = {
        (Attribute.ENUM_CASE, True),
    }
    ENUM_VALUE = {
        (Attribute.ENUM_CASE, False),
    }
    MODULE = (
        {
            (Attribute.NAMESPACE, False),
            (Attribute.ENUM_CASE, True),
        },
    )
    STRUCT = {
        # Struct may contain an enum definition.
        (Attribute.ENUM_CASE, True),
    }
