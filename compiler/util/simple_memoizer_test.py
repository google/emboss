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

"""Tests for simple_memoizer."""

import unittest
from compiler.util import simple_memoizer


class SimpleMemoizerTest(unittest.TestCase):

    def test_memoized_function_returns_same_values(self):
        @simple_memoizer.memoize
        def add_one(n):
            return n + 1

        for i in range(100):
            self.assertEqual(i + 1, add_one(i))

    def test_memoized_function_is_only_called_once(self):
        arguments = []

        @simple_memoizer.memoize
        def add_one_and_add_argument_to_list(n):
            arguments.append(n)
            return n + 1

        self.assertEqual(1, add_one_and_add_argument_to_list(0))
        self.assertEqual([0], arguments)
        self.assertEqual(1, add_one_and_add_argument_to_list(0))
        self.assertEqual([0], arguments)

    def test_memoized_function_with_multiple_arguments(self):
        arguments = []

        @simple_memoizer.memoize
        def sum_arguments_and_add_arguments_to_list(n, m, o):
            arguments.append((n, m, o))
            return n + m + o

        self.assertEqual(3, sum_arguments_and_add_arguments_to_list(0, 1, 2))
        self.assertEqual([(0, 1, 2)], arguments)
        self.assertEqual(3, sum_arguments_and_add_arguments_to_list(0, 1, 2))
        self.assertEqual([(0, 1, 2)], arguments)
        self.assertEqual(3, sum_arguments_and_add_arguments_to_list(2, 1, 0))
        self.assertEqual([(0, 1, 2), (2, 1, 0)], arguments)

    def test_memoized_function_with_no_arguments(self):
        arguments = []

        @simple_memoizer.memoize
        def return_one_and_add_empty_tuple_to_list():
            arguments.append(())
            return 1

        self.assertEqual(1, return_one_and_add_empty_tuple_to_list())
        self.assertEqual([()], arguments)
        self.assertEqual(1, return_one_and_add_empty_tuple_to_list())
        self.assertEqual([()], arguments)


if __name__ == "__main__":
    unittest.main()
