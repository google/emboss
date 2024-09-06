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

"""Tests for glue."""

import pkgutil
import unittest

from compiler.front_end import glue
from compiler.util import error
from compiler.util import ir_data
from compiler.util import ir_data_utils
from compiler.util import parser_types
from compiler.util import test_util

_location = parser_types.make_location

_ROOT_PACKAGE = "testdata.golden"
_GOLDEN_PATH = ""

_SPAN_SE_LOG_FILE_PATH = _GOLDEN_PATH + "span_se_log_file_status.emb"
_SPAN_SE_LOG_FILE_EMB = pkgutil.get_data(_ROOT_PACKAGE, _SPAN_SE_LOG_FILE_PATH).decode(
    encoding="UTF-8"
)
_SPAN_SE_LOG_FILE_READER = test_util.dict_file_reader(
    {_SPAN_SE_LOG_FILE_PATH: _SPAN_SE_LOG_FILE_EMB}
)
_SPAN_SE_LOG_FILE_IR = ir_data_utils.IrDataSerializer.from_json(
    ir_data.Module,
    pkgutil.get_data(
        _ROOT_PACKAGE, _GOLDEN_PATH + "span_se_log_file_status.ir.txt"
    ).decode(encoding="UTF-8"),
)
_SPAN_SE_LOG_FILE_PARSE_TREE_TEXT = pkgutil.get_data(
    _ROOT_PACKAGE, _GOLDEN_PATH + "span_se_log_file_status.parse_tree.txt"
).decode(encoding="UTF-8")
_SPAN_SE_LOG_FILE_TOKENIZATION_TEXT = pkgutil.get_data(
    _ROOT_PACKAGE, _GOLDEN_PATH + "span_se_log_file_status.tokens.txt"
).decode(encoding="UTF-8")


class FrontEndGlueTest(unittest.TestCase):
    """Tests for front_end.glue."""

    def test_parse_module(self):
        # parse_module(file) should return the same thing as
        # parse_module_text(text), assuming file can be read.
        main_module, debug_info, errors = glue.parse_module(
            _SPAN_SE_LOG_FILE_PATH, _SPAN_SE_LOG_FILE_READER
        )
        main_module2, debug_info2, errors2 = glue.parse_module_text(
            _SPAN_SE_LOG_FILE_EMB, _SPAN_SE_LOG_FILE_PATH
        )
        self.assertEqual([], errors)
        self.assertEqual([], errors2)
        self.assertEqual(main_module, main_module2)
        self.assertEqual(debug_info, debug_info2)

    def test_parse_module_no_such_file(self):
        file_name = "nonexistent.emb"
        ir, debug_info, errors = glue.parse_emboss_file(
            file_name, test_util.dict_file_reader({})
        )
        self.assertEqual(
            [
                [
                    error.error(
                        "nonexistent.emb",
                        _location((1, 1), (1, 1)),
                        "Unable to read file.",
                    ),
                    error.note(
                        "nonexistent.emb",
                        _location((1, 1), (1, 1)),
                        "File 'nonexistent.emb' not found.",
                    ),
                ]
            ],
            errors,
        )
        self.assertFalse(file_name in debug_info.modules)
        self.assertFalse(ir)

    def test_parse_module_tokenization_error(self):
        file_name = "tokens.emb"
        ir, debug_info, errors = glue.parse_emboss_file(
            file_name, test_util.dict_file_reader({file_name: "@"})
        )
        self.assertTrue(debug_info.modules[file_name].source_code)
        self.assertTrue(errors)
        self.assertEqual("Unrecognized token", errors[0][0].message)
        self.assertFalse(ir)

    def test_parse_module_indentation_error(self):
        file_name = "indent.emb"
        ir, debug_info, errors = glue.parse_emboss_file(
            file_name,
            test_util.dict_file_reader(
                {file_name: "struct Foo:\n" "  1 [+1] Int x\n" " 2 [+1] Int y\n"}
            ),
        )
        self.assertTrue(debug_info.modules[file_name].source_code)
        self.assertTrue(errors)
        self.assertEqual("Bad indentation", errors[0][0].message)
        self.assertFalse(ir)

    def test_parse_module_parse_error(self):
        file_name = "parse.emb"
        ir, debug_info, errors = glue.parse_emboss_file(
            file_name,
            test_util.dict_file_reader(
                {file_name: "struct foo:\n" "  1 [+1] Int x\n" "  3 [+1] Int y\n"}
            ),
        )
        self.assertTrue(debug_info.modules[file_name].source_code)
        self.assertEqual(
            [
                [
                    error.error(
                        file_name,
                        _location((1, 8), (1, 11)),
                        "A type name must be CamelCase.\n"
                        "Found 'foo' (SnakeWord), expected CamelWord.",
                    )
                ]
            ],
            errors,
        )
        self.assertFalse(ir)

    def test_parse_error(self):
        file_name = "parse.emb"
        ir, debug_info, errors = glue.parse_emboss_file(
            file_name,
            test_util.dict_file_reader(
                {file_name: "struct foo:\n" "  1 [+1]  Int  x\n" "  2 [+1]  Int  y\n"}
            ),
        )
        self.assertTrue(debug_info.modules[file_name].source_code)
        self.assertEqual(
            [
                [
                    error.error(
                        file_name,
                        _location((1, 8), (1, 11)),
                        "A type name must be CamelCase.\n"
                        "Found 'foo' (SnakeWord), expected CamelWord.",
                    )
                ]
            ],
            errors,
        )
        self.assertFalse(ir)

    def test_circular_dependency_error(self):
        file_name = "cycle.emb"
        ir, debug_info, errors = glue.parse_emboss_file(
            file_name,
            test_util.dict_file_reader(
                {file_name: "struct Foo:\n" "  0 [+field1]  UInt  field1\n"}
            ),
        )
        self.assertTrue(debug_info.modules[file_name].source_code)
        self.assertTrue(errors)
        self.assertEqual("Dependency cycle\nfield1", errors[0][0].message)
        self.assertFalse(ir)

    def test_ir_from_parse_module(self):
        log_file_path_ir = ir_data_utils.copy(_SPAN_SE_LOG_FILE_IR)
        log_file_path_ir.source_file_name = _SPAN_SE_LOG_FILE_PATH
        self.assertEqual(
            log_file_path_ir,
            glue.parse_module(_SPAN_SE_LOG_FILE_PATH, _SPAN_SE_LOG_FILE_READER).ir,
        )

    def test_debug_info_from_parse_module(self):
        debug_info = glue.parse_module(
            _SPAN_SE_LOG_FILE_PATH, _SPAN_SE_LOG_FILE_READER
        ).debug_info
        self.maxDiff = 200000  # pylint:disable=invalid-name
        self.assertEqual(
            _SPAN_SE_LOG_FILE_TOKENIZATION_TEXT.strip(),
            debug_info.format_tokenization().strip(),
        )
        self.assertEqual(
            _SPAN_SE_LOG_FILE_PARSE_TREE_TEXT.strip(),
            debug_info.format_parse_tree().strip(),
        )
        self.assertEqual(_SPAN_SE_LOG_FILE_IR, debug_info.ir)
        self.assertEqual(
            ir_data_utils.IrDataSerializer(_SPAN_SE_LOG_FILE_IR).to_json(indent=2),
            debug_info.format_module_ir(),
        )

    def test_parse_emboss_file(self):
        # parse_emboss_file calls parse_module, wraps its results, and calls
        # symbol_resolver.resolve_symbols() on the resulting IR.
        ir, debug_info, errors = glue.parse_emboss_file(
            _SPAN_SE_LOG_FILE_PATH, _SPAN_SE_LOG_FILE_READER
        )
        module_ir, module_debug_info, module_errors = glue.parse_module(
            _SPAN_SE_LOG_FILE_PATH, _SPAN_SE_LOG_FILE_READER
        )
        self.assertEqual([], errors)
        self.assertEqual([], module_errors)
        self.assertTrue(test_util.proto_is_superset(ir.module[0], module_ir))
        self.assertEqual(module_debug_info, debug_info.modules[_SPAN_SE_LOG_FILE_PATH])
        self.assertEqual(2, len(debug_info.modules))
        self.assertEqual(2, len(ir.module))
        self.assertEqual(_SPAN_SE_LOG_FILE_PATH, ir.module[0].source_file_name)
        self.assertEqual("", ir.module[1].source_file_name)

    def test_synthetic_error(self):
        file_name = "missing_byte_order_attribute.emb"
        ir, unused_debug_info, errors = glue.only_parse_emboss_file(
            file_name,
            test_util.dict_file_reader(
                {file_name: "struct Foo:\n" "  0 [+8]  UInt  field\n"}
            ),
        )
        self.assertFalse(errors)
        # Artificially mark the first field as is_synthetic.
        first_field = ir.module[0].type[0].structure.field[0]
        first_field.source_location.is_synthetic = True
        ir, errors = glue.process_ir(ir, None)
        self.assertTrue(errors)
        self.assertEqual(
            "Attribute 'byte_order' required on field which is byte "
            "order dependent.",
            errors[0][0].message,
        )
        self.assertTrue(errors[0][0].location.is_synthetic)
        self.assertFalse(ir)

    def test_suppressed_synthetic_error(self):
        file_name = "triplicate_symbol.emb"
        ir, unused_debug_info, errors = glue.only_parse_emboss_file(
            file_name,
            test_util.dict_file_reader(
                {
                    file_name: "struct Foo:\n"
                    "  0 [+1]  UInt  field\n"
                    "  1 [+1]  UInt  field\n"
                    "  2 [+1]  UInt  field\n"
                }
            ),
        )
        self.assertFalse(errors)
        # Artificially mark the name of the second field as is_synthetic.
        second_field = ir.module[0].type[0].structure.field[1]
        second_field.name.source_location.is_synthetic = True
        second_field.name.name.source_location.is_synthetic = True
        ir, errors = glue.process_ir(ir, None)
        self.assertEqual(1, len(errors))
        self.assertEqual("Duplicate name 'field'", errors[0][0].message)
        self.assertFalse(errors[0][0].location.is_synthetic)
        self.assertFalse(errors[0][1].location.is_synthetic)
        self.assertFalse(ir)


class DebugInfoTest(unittest.TestCase):
    """Tests for DebugInfo and ModuleDebugInfo classes."""

    def test_debug_info_initialization(self):
        debug_info = glue.DebugInfo()
        self.assertEqual({}, debug_info.modules)

    def test_debug_info_invalid_attribute_set(self):
        debug_info = glue.DebugInfo()
        with self.assertRaises(AttributeError):
            debug_info.foo = "foo"

    def test_debug_info_equality(self):
        debug_info = glue.DebugInfo()
        debug_info2 = glue.DebugInfo()
        self.assertEqual(debug_info, debug_info2)
        debug_info.modules["foo"] = glue.ModuleDebugInfo("foo")
        self.assertNotEqual(debug_info, debug_info2)
        debug_info2.modules["foo"] = glue.ModuleDebugInfo("foo")
        self.assertEqual(debug_info, debug_info2)

    def test_module_debug_info_initialization(self):
        module_info = glue.ModuleDebugInfo("bar.emb")
        self.assertEqual("bar.emb", module_info.file_name)
        self.assertEqual(None, module_info.tokens)
        self.assertEqual(None, module_info.parse_tree)
        self.assertEqual(None, module_info.ir)
        self.assertEqual(None, module_info.used_productions)

    def test_module_debug_info_attribute_set(self):
        module_info = glue.ModuleDebugInfo("bar.emb")
        module_info.tokens = "a"
        module_info.parse_tree = "b"
        module_info.ir = "c"
        module_info.used_productions = "d"
        module_info.source_code = "e"
        self.assertEqual("a", module_info.tokens)
        self.assertEqual("b", module_info.parse_tree)
        self.assertEqual("c", module_info.ir)
        self.assertEqual("d", module_info.used_productions)
        self.assertEqual("e", module_info.source_code)

    def test_module_debug_info_bad_attribute_set(self):
        module_info = glue.ModuleDebugInfo("bar.emb")
        with self.assertRaises(AttributeError):
            module_info.foo = "foo"

    def test_module_debug_info_equality(self):
        module_info = glue.ModuleDebugInfo("foo")
        module_info2 = glue.ModuleDebugInfo("foo")
        module_info_bar = glue.ModuleDebugInfo("bar")
        self.assertEqual(module_info, module_info2)
        module_info_bar = glue.ModuleDebugInfo("bar")
        self.assertNotEqual(module_info, module_info_bar)
        module_info.tokens = []
        self.assertNotEqual(module_info, module_info2)
        module_info2.tokens = []
        self.assertEqual(module_info, module_info2)
        module_info.parse_tree = []
        self.assertNotEqual(module_info, module_info2)
        module_info2.parse_tree = []
        self.assertEqual(module_info, module_info2)
        module_info.ir = []
        self.assertNotEqual(module_info, module_info2)
        module_info2.ir = []
        self.assertEqual(module_info, module_info2)
        module_info.used_productions = []
        self.assertNotEqual(module_info, module_info2)
        module_info2.used_productions = []
        self.assertEqual(module_info, module_info2)


class TestFormatProductionSet(unittest.TestCase):
    """Tests for format_production_set."""

    def test_format_production_set(self):
        production_texts = ["A -> B", "B -> C", "A -> C", "C -> A"]
        productions = [parser_types.Production.parse(p) for p in production_texts]
        self.assertEqual(
            "\n".join(sorted(production_texts)),
            glue.format_production_set(set(productions)),
        )


if __name__ == "__main__":
    unittest.main()
