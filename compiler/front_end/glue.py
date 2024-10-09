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

"""Main driver for the Emboss front-end.

The parse_emboss_file function performs a complete parse of the specified file,
and returns an IR or formatted error message.
"""

import collections
import sys

from compiler.front_end import attribute_checker
from compiler.front_end import constraints
from compiler.front_end import dependency_checker
from compiler.front_end import expression_bounds
from compiler.front_end import lr1
from compiler.front_end import module_ir
from compiler.front_end import parser
from compiler.front_end import symbol_resolver
from compiler.front_end import synthetics
from compiler.front_end import tokenizer
from compiler.front_end import type_check
from compiler.front_end import write_inference
from compiler.util import error
from compiler.util import ir_data
from compiler.util import ir_data_utils
from compiler.util import parser_types
from compiler.util import resources

_IrDebugInfo = collections.namedtuple("IrDebugInfo", ["ir", "debug_info", "errors"])


class DebugInfo(object):
    """Debug information about Emboss parsing."""

    __slots__ = "modules"

    def __init__(self):
        self.modules = {}

    def __eq__(self, other):
        return self.modules == other.modules

    def __ne__(self, other):
        return not self == other


class ModuleDebugInfo(object):
    """Debug information about the parse of a single file.

    Attributes:
      file_name: The name of the file from which this module came.
      tokens: The tokenization of this module's source text.
      parse_tree: The raw parse tree for this module.
      ir: The intermediate representation of this module, before additional
          processing such as symbol resolution.
      used_productions: The set of grammar productions used when parsing this
          module.
      source_code: The source text of the module.
    """

    __slots__ = (
        "file_name",
        "tokens",
        "parse_tree",
        "ir",
        "used_productions",
        "source_code",
    )

    def __init__(self, file_name):
        self.file_name = file_name
        self.tokens = None
        self.parse_tree = None
        self.ir = None
        self.used_productions = None
        self.source_code = None

    def __eq__(self, other):
        return (
            self.file_name == other.file_name
            and self.tokens == other.tokens
            and self.parse_tree == other.parse_tree
            and self.ir == other.ir
            and self.used_productions == other.used_productions
            and self.source_code == other.source_code
        )

    def __ne__(self, other):
        return not self == other

    def format_tokenization(self):
        """Renders self.tokens in a human-readable format."""
        return "\n".join([str(token) for token in self.tokens])

    def format_parse_tree(self, parse_tree=None, indent=""):
        """Renders self.parse_tree in a human-readable format."""
        if parse_tree is None:
            parse_tree = self.parse_tree
        result = []
        if isinstance(parse_tree, lr1.Reduction):
            result.append(indent + parse_tree.symbol)
            if parse_tree.children:
                result.append(":\n")
                for child in parse_tree.children:
                    result.append(self.format_parse_tree(child, indent + "  "))
            else:
                result.append("\n")
        else:
            result.append("{}{}\n".format(indent, parse_tree))
        return "".join(result)

    def format_module_ir(self):
        """Renders self.ir in a human-readable format."""
        return ir_data_utils.IrDataSerializer(self.ir).to_json(indent=2)


def format_production_set(productions):
    """Renders a set of productions in a human-readable format."""
    return "\n".join([str(production) for production in sorted(productions)])


_cached_modules = {}


def parse_module_text(source_code, file_name):
    """Parses the text of a module, returning a module-level IR.

    Arguments:
      source_code: The text of the module to parse.
      file_name: The name of the module's source file (will be included in the
          resulting IR).

    Returns:
      A module-level intermediate representation (IR), prior to import and symbol
      resolution, and a corresponding ModuleDebugInfo, for debugging the parser.

    Raises:
      FrontEndFailure: An error occurred while parsing the module.  str(error)
          will give a human-readable error message.
    """
    # This is strictly an optimization to speed up tests, mostly by avoiding the
    # need to re-parse the prelude for every test .emb.
    if (source_code, file_name) in _cached_modules:
        debug_info = _cached_modules[source_code, file_name]
        ir = ir_data_utils.copy(debug_info.ir)
    else:
        debug_info = ModuleDebugInfo(file_name)
        debug_info.source_code = source_code
        tokens, errors = tokenizer.tokenize(source_code, file_name)
        if errors:
            return _IrDebugInfo(None, debug_info, errors)
        debug_info.tokens = tokens
        parse_result = parser.parse_module(tokens)
        if parse_result.error:
            return _IrDebugInfo(
                None,
                debug_info,
                [error.make_error_from_parse_error(file_name, parse_result.error)],
            )
        debug_info.parse_tree = parse_result.parse_tree
        used_productions = set()
        ir = module_ir.build_ir(parse_result.parse_tree, used_productions)
        ir.source_text = source_code
        debug_info.used_productions = used_productions
        debug_info.ir = ir_data_utils.copy(ir)
        _cached_modules[source_code, file_name] = debug_info
    ir.source_file_name = file_name
    return _IrDebugInfo(ir, debug_info, [])


def parse_module(file_name, file_reader):
    """Parses a module, returning a module-level IR.

    Arguments:
      file_name: The name of the module's source file.
      file_reader: A callable that returns either:
          (file_contents, None) or
          (None, list_of_error_detail_strings)

    Returns:
      (ir, debug_info, errors), where ir is a module-level intermediate
      representation (IR), debug_info is a ModuleDebugInfo containing the
      tokenization, parse tree, and original source text of all modules, and
      errors is a list of tokenization or parse errors.  If errors is not an empty
      list, ir will be None.

    Raises:
      FrontEndFailure: An error occurred while reading or parsing the module.
          str(error) will give a human-readable error message.
    """
    source_code, errors = file_reader(file_name)
    if errors:
        location = parser_types.make_location((1, 1), (1, 1))
        return (
            None,
            None,
            [
                [error.error(file_name, location, "Unable to read file.")]
                + [error.note(file_name, location, e) for e in errors]
            ],
        )
    return parse_module_text(source_code, file_name)


def get_prelude():
    """Returns the module IR and debug info of the Emboss Prelude."""
    return parse_module_text(resources.load("compiler.front_end", "prelude.emb"), "")


def parse_emboss_file(file_name, file_reader, stop_before_step=None):
    """Fully parses an .emb, and returns an IR suitable for passing to a back end.

    parse_emboss_file is a convenience function which calls only_parse_emboss_file
    and process_ir.

    Arguments:
      file_name: The name of the module's source file.
      file_reader: A callable that returns the contents of files, or raises
          IOError.
      stop_before_step: If set, parse_emboss_file will stop normalizing the IR
          just before the specified step.  This parameter should be None for
          non-test code.

    Returns:
      (ir, debug_info, errors), where ir is a complete IR, ready for consumption
      by an Emboss back end, debug_info is a DebugInfo containing the
      tokenization, parse tree, and original source text of all modules, and
      errors is a list of tokenization or parse errors.  If errors is not an empty
      list, ir will be None.
    """
    ir, debug_info, errors = only_parse_emboss_file(file_name, file_reader)
    if errors:
        return _IrDebugInfo(None, debug_info, errors)
    ir, errors = process_ir(ir, stop_before_step)
    if errors:
        return _IrDebugInfo(None, debug_info, errors)
    return _IrDebugInfo(ir, debug_info, errors)


def only_parse_emboss_file(file_name, file_reader):
    """Parses an .emb, and returns an IR suitable for process_ir.

    only_parse_emboss_file parses the given file and all of its transitive
    imports, and returns a first-stage intermediate representation, which can be
    passed to process_ir.

    Arguments:
      file_name: The name of the module's source file.
      file_reader: A callable that returns the contents of files, or raises
          IOError.

    Returns:
      (ir, debug_info, errors), where ir is an intermediate representation (IR),
      debug_info is a DebugInfo containing the tokenization, parse tree, and
      original source text of all modules, and errors is a list of tokenization or
      parse errors.  If errors is not an empty list, ir will be None.
    """
    file_queue = [file_name]
    files = {file_name}
    debug_info = DebugInfo()
    ir = ir_data.EmbossIr(module=[])
    while file_queue:
        file_to_parse = file_queue[0]
        del file_queue[0]
        if file_to_parse:
            module, module_debug_info, errors = parse_module(file_to_parse, file_reader)
        else:
            module, module_debug_info, errors = get_prelude()
        if module_debug_info:
            debug_info.modules[file_to_parse] = module_debug_info
        if errors:
            return _IrDebugInfo(None, debug_info, errors)
        ir.module.extend([module])  # Proto supports extend but not append here.
        for import_ in module.foreign_import:
            if import_.file_name.text not in files:
                file_queue.append(import_.file_name.text)
                files.add(import_.file_name.text)
    return _IrDebugInfo(ir, debug_info, [])


def process_ir(ir, stop_before_step):
    """Turns a first-stage IR into a fully-processed IR.

    process_ir performs all of the semantic processing steps on `ir`: resolving
    symbols, checking dependencies, adding type annotations, normalizing
    attributes, etc.  process_ir is generally meant to be called with the result
    of parse_emboss_file(), but in theory could be called with a first-stage
    intermediate representation (IR) from another source.

    Arguments:
      ir: The IR to process.  This structure will be modified during processing.
      stop_before_step: If set, process_ir will stop normalizing the IR just
          before the specified step.  This parameter should be None for non-test
          code.

    Returns:
      (ir, errors), where ir is a complete IR, ready for consumption by an Emboss
      back end, and errors is a list of compilation errors.  If errors is not an
      empty list, ir will be None.
    """
    passes = (
        synthetics.desugar,
        symbol_resolver.resolve_symbols,
        dependency_checker.find_dependency_cycles,
        dependency_checker.set_dependency_order,
        symbol_resolver.resolve_field_references,
        type_check.annotate_types,
        type_check.check_types,
        expression_bounds.compute_constants,
        attribute_checker.normalize_and_verify,
        constraints.check_constraints,
        write_inference.set_write_methods,
    )
    valid_step_names = [f.__name__ for f in passes]
    assert stop_before_step in [None] + valid_step_names, (
        f"Bad value '{stop_before_step}' for stop_before_step.  Valid values: "
        + " ".join(valid_step_names)
    )
    # Some parts of the IR are synthesized from "natural" parts of the IR, before
    # the natural parts have been fully error checked.  Because of this, the
    # synthesized parts can have errors; in a couple of cases, they can have
    # errors that show up in an earlier pass than the errors in the natural parts
    # of the IR.  As an example:
    #
    #     struct Foo:
    #       0 [+1]  bits:
    #         0 [+1]  Flag  flag
    #       1 [+flag]  UInt:8  field
    #
    # In this case, the use of `flag` as the size of `field` is incorrect, because
    # `flag` is a boolean, but the size of a field must be an integer.
    #
    # Type checking occurs in two passes: in the first pass, expressions are
    # checked for internal consistency.  In the second pass, expression types are
    # checked against their location.  The use of `flag` would be caught in the
    # second pass.
    #
    # However, the generated_fields pass will synthesize a $size_in_bytes virtual
    # field that would look like:
    #
    #     struct Foo:
    #       0 [+1]  bits:
    #         0 [+1]  Flag  flag
    #       1 [+flag]  UInt:8  field
    #       let $size_in_bytes = $max(true ? 0 + 1 : 0, true ? 1 + flag : 0)
    #
    # Since `1 + flag` is not internally consistent, this type error would be
    # caught in the first pass, and the user would see a very strange error
    # message that "the right-hand argument of operator `+` must be an integer."
    #
    # In order to avoid showing these kinds of errors to the user, we defer any
    # errors in synthetic parts of the IR.  Unless there is a compiler bug, those
    # errors will show up as errors in the natural parts of the IR, which should
    # be much more comprehensible to end users.
    #
    # If, for some reason, there is an error in the synthetic IR, but no error in
    # the natural IR, the synthetic errors will be shown.  In this case, the
    # formatting for the synthetic errors will show '[compiler bug]' for the
    # error location, which (hopefully) will provide the end user with a cue that
    # the error is a compiler bug.
    deferred_errors = []
    for function in passes:
        if stop_before_step == function.__name__:
            return (ir, [])
        errors, hidden_errors = error.split_errors(function(ir))
        if errors:
            return (None, errors)
        deferred_errors.extend(hidden_errors)

    if deferred_errors:
        return (None, deferred_errors)

    assert stop_before_step is None, "Bad value for stop_before_step."
    return (ir, [])
