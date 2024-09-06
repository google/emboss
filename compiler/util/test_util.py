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

"""Utilities for test code."""

from compiler.util import ir_data_utils


def proto_is_superset(proto, expected_values, path=""):
    """Returns true if every value in expected_values is set in proto.

    This is intended to be used in assertTrue in a unit test, like so:

        self.assertTrue(*proto_is_superset(proto, expected))

    Arguments:
      proto: The proto to check.
      expected_values: The reference proto.
      path: The path to the elements being compared.  Clients can generally leave
        this at default.

    Returns:
      A tuple; the first element is True if the fields set in proto are a strict
      superset of the fields set in expected_values.  The second element is an
      informational string specifying the path of a value found in expected_values
      but not in proto.

      Every atomic field that is set in expected_values must be set to the same
      value in proto; every message field set in expected_values must have a
      matching field in proto, such that proto_is_superset(proto.field,
      expected_values.field) is true.

      For repeated fields in expected_values, each element in the expected_values
      proto must have a corresponding element at the same index in proto; proto
      may have additional elements.
    """
    if path:
        path += "."
    for spec, expected_value in ir_data_utils.get_set_fields(expected_values):
        name = spec.name
        field_path = "{}{}".format(path, name)
        value = getattr(proto, name)
        if spec.is_dataclass:
            if spec.is_sequence:
                if len(expected_value) > len(value):
                    return False, "{}[{}] missing".format(
                        field_path, len(getattr(proto, name))
                    )
                for i in range(len(expected_value)):
                    result = proto_is_superset(
                        value[i], expected_value[i], "{}[{}]".format(field_path, i)
                    )
                    if not result[0]:
                        return result
            else:
                if expected_values.HasField(name) and not proto.HasField(name):
                    return False, "{} missing".format(field_path)
                result = proto_is_superset(value, expected_value, field_path)
                if not result[0]:
                    return result
        else:
            # Zero-length repeated fields and not-there repeated fields are "the
            # same."
            if expected_value != value and (
                not spec.is_sequence or len(expected_value)
            ):
                if spec.is_sequence:
                    return False, "{} differs: found {}, expected {}".format(
                        field_path, list(value), list(expected_value)
                    )
                else:
                    return False, "{} differs: found {}, expected {}".format(
                        field_path, value, expected_value
                    )
    return True, ""


def dict_file_reader(file_dict):
    """Returns a callable that retrieves entries from file_dict as files.

    This can be used to call glue.parse_emboss_file with file text declared
    inline.

    Arguments:
        file_dict: A dictionary from "file names" to "contents."

    Returns:
        A callable that can be passed to glue.parse_emboss_file in place of the
        "read" builtin.
    """

    def read(file_name):
        try:
            return file_dict[file_name], None
        except KeyError:
            return None, ["File '{}' not found.".format(file_name)]

    return read
