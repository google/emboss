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

"""Conversions between snake-, camel-, and shouty-case names."""

import enum


class Case(str, enum.Enum):
    SNAKE = "snake_case"
    SHOUTY = "SHOUTY_CASE"
    CAMEL = "CamelCase"
    K_CAMEL = "kCamelCase"


# Map of (from, to) cases to their conversion function. Initially only contains
# identity case conversions, additional conversions are added with the
# _case_conversion decorator.
_case_conversions = {(case.value, case.value): lambda x: x for case in Case}


def _case_conversion(case_from, case_to):
    """Decorator to dynamically dispatch case conversions at runtime."""

    def _func(f):
        _case_conversions[case_from, case_to] = f
        return f

    return _func


@_case_conversion(Case.SNAKE, Case.CAMEL)
@_case_conversion(Case.SHOUTY, Case.CAMEL)
def snake_to_camel(name):
    """Convert from snake_case to CamelCase. Also works from SHOUTY_CASE."""
    return "".join(word.capitalize() for word in name.split("_"))


@_case_conversion(Case.CAMEL, Case.K_CAMEL)
def camel_to_k_camel(name):
    """Convert from CamelCase to kCamelCase."""
    return "k" + name


@_case_conversion(Case.SNAKE, Case.K_CAMEL)
@_case_conversion(Case.SHOUTY, Case.K_CAMEL)
def snake_to_k_camel(name):
    """Converts from snake_case to kCamelCase. Also works from SHOUTY_CASE."""
    return camel_to_k_camel(snake_to_camel(name))


def convert_case(case_from, case_to, value):
    """Converts cases based on runtime case values.

    Note: Cases can be strings or enum values.

    Arguments:
        case_from: the name of the original case
        case_to: the name of the desired case
        value: the value to convert

    Returns:
        `value` converted from `case_from` to `case_to`.
    """
    return _case_conversions[case_from, case_to](value)


def is_case_conversion_supported(case_from, case_to):
    """Determines if a case conversion would be supported."""
    return (case_from, case_to) in _case_conversions
