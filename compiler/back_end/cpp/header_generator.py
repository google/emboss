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

"""C++ header code generator.

Call generate_header(ir) to get the text of a C++ header file implementing View
classes for the ir.
"""

import collections
import re
from typing import NamedTuple

from compiler.back_end.cpp import attributes
from compiler.back_end.util import code_template
from compiler.util import attribute_util
from compiler.util import error
from compiler.util import ir_data
from compiler.util import ir_data_utils
from compiler.util import ir_util
from compiler.util import name_conversion
from compiler.util import resources
from compiler.util import traverse_ir

_TEMPLATES = code_template.parse_templates(
    resources.load("compiler.back_end.cpp", "generated_code_templates")
)

_CPP_RESERVED_WORDS = set(
    (
        # C keywords.  A few of these are not (yet) C++ keywords, but some compilers
        # accept the superset of C and C++, so we still want to avoid them.
        "asm",
        "auto",
        "break",
        "case",
        "char",
        "const",
        "continue",
        "default",
        "do",
        "double",
        "else",
        "enum",
        "extern",
        "float",
        "for",
        "fortran",
        "goto",
        "if",
        "inline",
        "int",
        "long",
        "register",
        "restrict",
        "return",
        "short",
        "signed",
        "sizeof",
        "static",
        "struct",
        "switch",
        "typedef",
        "union",
        "unsigned",
        "void",
        "volatile",
        "while",
        "_Alignas",
        "_Alignof",
        "_Atomic",
        "_Bool",
        "_Complex",
        "_Generic",
        "_Imaginary",
        "_Noreturn",
        "_Pragma",
        "_Static_assert",
        "_Thread_local",
        # The following are not technically reserved words, but collisions are
        # likely due to the standard macros.
        "complex",
        "imaginary",
        "noreturn",
        # C++ keywords that are not also C keywords.
        "alignas",
        "alignof",
        "and",
        "and_eq",
        "asm",
        "bitand",
        "bitor",
        "bool",
        "catch",
        "char16_t",
        "char32_t",
        "class",
        "compl",
        "concept",
        "constexpr",
        "const_cast",
        "decltype",
        "delete",
        "dynamic_cast",
        "explicit",
        "export",
        "false",
        "friend",
        "mutable",
        "namespace",
        "new",
        "noexcept",
        "not",
        "not_eq",
        "nullptr",
        "operator",
        "or",
        "or_eq",
        "private",
        "protected",
        "public",
        "reinterpret_cast",
        "requires",
        "static_assert",
        "static_cast",
        "template",
        "this",
        "thread_local",
        "throw",
        "true",
        "try",
        "typeid",
        "typename",
        "using",
        "virtual",
        "wchar_t",
        "xor",
        "xor_eq",
        # "NULL" is not a keyword, but is still very likely to cause problems if
        # used as a namespace name.
        "NULL",
    )
)

# The support namespace, as a C++ namespace prefix.  This namespace contains the
# Emboss C++ support classes.
_SUPPORT_NAMESPACE = "::emboss::support"

# Regex matching a C++ namespace component. Captures component name.
_NS_COMPONENT_RE = r"(?:^\s*|::)\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*(?=\s*$|::)"
# Regex matching a full C++ namespace (at least one namespace component).
_NS_RE = rf"^\s*(?:{_NS_COMPONENT_RE})+\s*$"
# Regex matching an empty C++ namespace.
_NS_EMPTY_RE = r"^\s*$"
# Regex matching only the global C++ namespace.
_NS_GLOBAL_RE = r"^\s*::\s*$"

# TODO(bolms): This should be a command-line flag.
_PRELUDE_INCLUDE_FILE = "runtime/cpp/emboss_prelude.h"
_ENUM_VIEW_INCLUDE_FILE = "runtime/cpp/emboss_enum_view.h"
_TEXT_UTIL_INCLUDE_FILE = "runtime/cpp/emboss_text_util.h"

# Cases allowed in the `enum_case` attribute.
_SUPPORTED_ENUM_CASES = ("SHOUTY_CASE", "kCamelCase")

# Verify that all supported enum cases have valid, implemented conversions.
for _enum_case in _SUPPORTED_ENUM_CASES:
    assert name_conversion.is_case_conversion_supported("SHOUTY_CASE", _enum_case)


class Config(NamedTuple):
    """Configuration for C++ header generation."""

    include_enum_traits: bool = True
    """Whether or not to include EnumTraits in the generated header."""


def _get_namespace_components(namespace):
    """Gets the components of a C++ namespace.

    Examples:
      "::some::name::detail" -> ["some", "name", "detail"]
      "product::name" -> ["product", "name"]
      "simple" -> ["simple"]

    Arguments:
      namespace: A string containing the namespace. May be fully-qualified.

    Returns:
      A list of strings, one per namespace component."""
    return re.findall(_NS_COMPONENT_RE, namespace)


def _get_module_namespace(module):
    """Returns the C++ namespace of the module, as a list of components.

    Arguments:
      module: The IR of an Emboss module whose namespace should be returned.

    Returns:
      A list of strings, one per namespace component.  This list can be formatted
      as appropriate by the caller.
    """
    namespace_attr = ir_util.get_attribute(module.attribute, "namespace")
    if namespace_attr and namespace_attr.string_constant.text:
        namespace = namespace_attr.string_constant.text
    else:
        namespace = "emboss_generated_code"
    return _get_namespace_components(namespace)


def _cpp_string_escape(string):
    return re.sub("['\"\\\\]", r"\\\0", string)


def _get_includes(module, config: Config):
    """Returns the appropriate #includes based on module's imports."""
    includes = []
    for import_ in module.foreign_import:
        if import_.file_name.text:
            includes.append(
                code_template.format_template(
                    _TEMPLATES.include,
                    file_name=_cpp_string_escape(import_.file_name.text + ".h"),
                )
            )
        else:
            includes.append(
                code_template.format_template(
                    _TEMPLATES.include,
                    file_name=_cpp_string_escape(_PRELUDE_INCLUDE_FILE),
                )
            )
            if config.include_enum_traits:
                includes.extend(
                    [
                        code_template.format_template(
                            _TEMPLATES.include, file_name=_cpp_string_escape(file_name)
                        )
                        for file_name in (
                            _ENUM_VIEW_INCLUDE_FILE,
                            _TEXT_UTIL_INCLUDE_FILE,
                        )
                    ]
                )
    return "".join(includes)


def _render_namespace_prefix(namespace):
    """Returns namespace rendered as a prefix, like ::foo::bar::baz."""
    return "".join(["::" + n for n in namespace])


def _render_integer(value):
    """Returns a C++ string representation of a constant integer."""
    integer_type = _cpp_integer_type_for_range(value, value)
    assert (
        integer_type
    ), "Bug: value should never be outside [-2**63, 2**64), " "got {}.".format(value)
    # C++ literals are always positive.  Negative constants are actually the
    # positive literal with the unary `-` operator applied.
    #
    # This means that C++ compilers for 2s-complement systems get finicky about
    # minimum integers: if you feed `-9223372036854775808` into GCC, with -Wall,
    # you get:
    #
    #     warning: integer constant is so large that it is unsigned
    #
    # and Clang gives:
    #
    #     warning: integer literal is too large to be represented in a signed
    #     integer type, interpreting as unsigned [-Wimplicitly-unsigned-literal]
    #
    # and MSVC:
    #
    #     warning C4146: unary minus operator applied to unsigned type, result
    #     still unsigned
    #
    # So, workaround #1: -(2**63) must be written `(-9223372036854775807 - 1)`.
    #
    # The next problem is that MSVC (but not Clang or GCC) will pick `unsigned`
    # as the type of a literal like `2147483648`.  As far as I can tell, this is a
    # violation of the C++11 standard, but it's possible that the final standard
    # has different rules.  (MSVC seems to treat decimal literals the way that the
    # standard says octal and hexadecimal literals should be treated.)
    #
    # Luckily, workaround #2: we can unconditionally append `LL` to all constants
    # to force them to be interpreted as `long long` (or `unsigned long long` for
    # `ULL`-suffixed constants), and then use a narrowing cast to the appropriate
    # type, without any warnings on any major compilers.
    #
    # TODO(bolms): This suffix computation is kind of a hack.
    suffix = "U" if "uint" in integer_type else ""
    if value == -(2**63):
        return "static_cast</**/{0}>({1}LL - 1)".format(integer_type, -(2**63 - 1))
    else:
        return "static_cast</**/{0}>({1}{2}LL)".format(integer_type, value, suffix)


def _maybe_type(wrapped_type):
    return "::emboss::support::Maybe</**/{}>".format(wrapped_type)


def _render_integer_for_expression(value):
    integer_type = _cpp_integer_type_for_range(value, value)
    return "{0}({1})".format(_maybe_type(integer_type), _render_integer(value))


def _wrap_in_namespace(body, namespace):
    """Returns the given body wrapped in the given namespace."""
    for component in reversed(namespace):
        body = (
            code_template.format_template(
                _TEMPLATES.namespace_wrap, component=component, body=body
            )
            + "\n"
        )
    return body


def _get_type_size(type_ir, ir):
    size = ir_util.fixed_size_of_type_in_bits(type_ir, ir)
    assert (
        size is not None
    ), "_get_type_size should only be called for constant-sized types."
    return size


def _offset_storage_adapter(buffer_type, alignment, static_offset):
    return "{}::template OffsetStorageType</**/{}, {}>".format(
        buffer_type, alignment, static_offset
    )


def _bytes_to_bits_convertor(buffer_type, byte_order, size):
    assert byte_order, "byte_order should not be empty."
    return "{}::BitBlock</**/{}::{}ByteOrderer<typename {}>, {}>".format(
        _SUPPORT_NAMESPACE, _SUPPORT_NAMESPACE, byte_order, buffer_type, size
    )


def _get_fully_qualified_namespace(name, ir):
    module = ir_util.find_object((name.module_file,), ir)
    namespace = _render_namespace_prefix(_get_module_namespace(module))
    return namespace + "".join(["::" + str(s) for s in name.object_path[:-1]])


def _get_unqualified_name(name):
    return name.object_path[-1]


def _get_fully_qualified_name(name, ir):
    return _get_fully_qualified_namespace(name, ir) + "::" + _get_unqualified_name(name)


def _get_adapted_cpp_buffer_type_for_field(
    type_definition, size_in_bits, buffer_type, byte_order, parent_addressable_unit
):
    """Returns the adapted C++ type information needed to construct a view."""
    if (
        parent_addressable_unit == ir_data.AddressableUnit.BYTE
        and type_definition.addressable_unit == ir_data.AddressableUnit.BIT
    ):
        assert byte_order
        return _bytes_to_bits_convertor(buffer_type, byte_order, size_in_bits)
    else:
        assert (
            parent_addressable_unit == type_definition.addressable_unit
        ), "Addressable unit mismatch: {} vs {}".format(
            parent_addressable_unit, type_definition.addressable_unit
        )
        return buffer_type


def _get_cpp_view_type_for_type_definition(
    type_definition,
    size,
    ir,
    buffer_type,
    byte_order,
    parent_addressable_unit,
    validator,
):
    """Returns the C++ type information needed to construct a view.

    Returns the C++ type for a view of the given Emboss TypeDefinition, and the
    C++ types of its parameters, if any.

    Arguments:
        type_definition: The ir_data.TypeDefinition whose view should be
            constructed.
        size: The size, in type_definition.addressable_units, of the instantiated
            type, or None if it is not known at compile time.
        ir: The complete IR.
        buffer_type: The C++ type to be used as the Storage parameter of the view
            (e.g., "ContiguousBuffer<...>").
        byte_order: For BIT types which are direct children of BYTE types,
            "LittleEndian", "BigEndian", or "None".  Otherwise, None.
        parent_addressable_unit: The addressable_unit_size of the structure
            containing this structure.
        validator: The name of the validator type to be injected into the view.

    Returns:
        A tuple of: the C++ view type and a (possibly-empty) list of the C++ types
        of Emboss parameters which must be passed to the view's constructor.
    """
    adapted_buffer_type = _get_adapted_cpp_buffer_type_for_field(
        type_definition, size, buffer_type, byte_order, parent_addressable_unit
    )
    if type_definition.has_field("external"):
        # Externals do not (yet) support runtime parameters.
        return (
            code_template.format_template(
                _TEMPLATES.external_view_type,
                namespace=_get_fully_qualified_namespace(
                    type_definition.name.canonical_name, ir
                ),
                name=_get_unqualified_name(type_definition.name.canonical_name),
                bits=size,
                validator=validator,
                buffer_type=adapted_buffer_type,
            ),
            [],
        )
    elif type_definition.has_field("structure"):
        parameter_types = []
        for parameter in type_definition.runtime_parameter:
            parameter_types.append(
                _cpp_basic_type_for_expression_type(parameter.type, ir)
            )
        return (
            code_template.format_template(
                _TEMPLATES.structure_view_type,
                namespace=_get_fully_qualified_namespace(
                    type_definition.name.canonical_name, ir
                ),
                name=_get_unqualified_name(type_definition.name.canonical_name),
                buffer_type=adapted_buffer_type,
            ),
            parameter_types,
        )
    elif type_definition.has_field("enumeration"):
        return (
            code_template.format_template(
                _TEMPLATES.enum_view_type,
                support_namespace=_SUPPORT_NAMESPACE,
                enum_type=_get_fully_qualified_name(
                    type_definition.name.canonical_name, ir
                ),
                bits=size,
                validator=validator,
                buffer_type=adapted_buffer_type,
            ),
            [],
        )
    else:
        assert False, "Unknown variety of type {}".format(type_definition)


def _get_cpp_view_type_for_physical_type(
    type_ir, size, byte_order, ir, buffer_type, parent_addressable_unit, validator
):
    """Returns the C++ type information needed to construct a field's view.

    Returns the C++ type of an ir_data.Type, and the C++ types of its parameters,
    if any.

    Arguments:
        type_ir: The ir_data.Type whose view should be constructed.
        size: The size, in type_definition.addressable_units, of the instantiated
            type, or None if it is not known at compile time.
        byte_order: For BIT types which are direct children of BYTE types,
            "LittleEndian", "BigEndian", or "None".  Otherwise, None.
        ir: The complete IR.
        buffer_type: The C++ type to be used as the Storage parameter of the view
            (e.g., "ContiguousBuffer<...>").
        parent_addressable_unit: The addressable_unit_size of the structure
            containing this type.
        validator: The name of the validator type to be injected into the view.

    Returns:
        A tuple of: the C++ type for a view of the given Emboss Type and a list of
        the C++ types of any parameters of the view type, which should be passed
        to the view's constructor.
    """
    if ir_util.is_array(type_ir):
        # An array view is parameterized by the element's view type.
        base_type = type_ir.array_type.base_type
        element_size_in_bits = _get_type_size(base_type, ir)
        assert (
            element_size_in_bits
        ), "TODO(bolms): Implement arrays of dynamically-sized elements."
        assert (
            element_size_in_bits % parent_addressable_unit == 0
        ), "Array elements must fall on byte boundaries."
        element_size = element_size_in_bits // parent_addressable_unit
        element_view_type, element_view_parameter_types, element_view_parameters = (
            _get_cpp_view_type_for_physical_type(
                base_type,
                element_size_in_bits,
                byte_order,
                ir,
                _offset_storage_adapter(buffer_type, element_size, 0),
                parent_addressable_unit,
                validator,
            )
        )
        return (
            code_template.format_template(
                _TEMPLATES.array_view_adapter,
                support_namespace=_SUPPORT_NAMESPACE,
                # TODO(bolms): The element size should be calculable from the field
                # size and array length.
                element_view_type=element_view_type,
                element_view_parameter_types="".join(
                    ", " + p for p in element_view_parameter_types
                ),
                element_size=element_size,
                addressable_unit_size=int(parent_addressable_unit),
                buffer_type=buffer_type,
            ),
            element_view_parameter_types,
            element_view_parameters,
        )
    else:
        assert type_ir.has_field("atomic_type")
        reference = type_ir.atomic_type.reference
        referenced_type = ir_util.find_object(reference, ir)
        if parent_addressable_unit > referenced_type.addressable_unit:
            assert byte_order, repr(type_ir)
        reader, parameter_types = _get_cpp_view_type_for_type_definition(
            referenced_type,
            size,
            ir,
            buffer_type,
            byte_order,
            parent_addressable_unit,
            validator,
        )
        return reader, parameter_types, list(type_ir.atomic_type.runtime_parameter)


def _render_variable(variable, prefix=""):
    """Renders a variable reference (e.g., `foo` or `foo.bar.baz`) in C++ code."""
    # A "variable" could be an immediate field or a subcomponent of an immediate
    # field.  For either case, in C++ it is valid to just use the last component
    # of the name; it is not necessary to qualify the method with the type.
    components = []
    for component in variable:
        components.append(_cpp_field_name(component[-1]) + "()")
    components[-1] = prefix + components[-1]
    return ".".join(components)


def _render_enum_value(enum_type, ir):
    cpp_enum_type = _get_fully_qualified_name(enum_type.name.canonical_name, ir)
    return "{}(static_cast</**/{}>({}))".format(
        _maybe_type(cpp_enum_type), cpp_enum_type, enum_type.value
    )


def _builtin_function_name(function):
    """Returns the C++ operator name corresponding to an Emboss operator."""
    functions = {
        ir_data.FunctionMapping.ADDITION: "Sum",
        ir_data.FunctionMapping.SUBTRACTION: "Difference",
        ir_data.FunctionMapping.MULTIPLICATION: "Product",
        ir_data.FunctionMapping.EQUALITY: "Equal",
        ir_data.FunctionMapping.INEQUALITY: "NotEqual",
        ir_data.FunctionMapping.AND: "And",
        ir_data.FunctionMapping.OR: "Or",
        ir_data.FunctionMapping.LESS: "LessThan",
        ir_data.FunctionMapping.LESS_OR_EQUAL: "LessThanOrEqual",
        ir_data.FunctionMapping.GREATER: "GreaterThan",
        ir_data.FunctionMapping.GREATER_OR_EQUAL: "GreaterThanOrEqual",
        ir_data.FunctionMapping.CHOICE: "Choice",
        ir_data.FunctionMapping.MAXIMUM: "Maximum",
    }
    return functions[function]


def _cpp_basic_type_for_expression_type(expression_type, ir):
    """Returns the C++ basic type (int32_t, bool, etc.) for an ExpressionType."""
    if expression_type.which_type == "integer":
        return _cpp_integer_type_for_range(
            int(expression_type.integer.minimum_value),
            int(expression_type.integer.maximum_value),
        )
    elif expression_type.which_type == "boolean":
        return "bool"
    elif expression_type.which_type == "enumeration":
        return _get_fully_qualified_name(
            expression_type.enumeration.name.canonical_name, ir
        )
    else:
        assert False, "Unknown expression type " + expression_type.which_type


def _cpp_basic_type_for_expression(expression, ir):
    """Returns the C++ basic type (int32_t, bool, etc.) for an Expression."""
    return _cpp_basic_type_for_expression_type(expression.type, ir)


def _cpp_integer_type_for_range(min_val, max_val):
    """Returns the appropriate C++ integer type to hold min_val up to max_val."""
    # The choice of int32_t, uint32_t, int64_t, then uint64_t is somewhat
    # arbitrary here, and might not be perfectly ideal.  I (bolms@) have chosen
    # this set of types to a) minimize the number of casts that occur in
    # arithmetic expressions, and b) favor 32-bit arithmetic, which is mostly
    # "cheapest" on current (2018) systems.  Signed integers are also preferred
    # over unsigned so that the C++ compiler can take advantage of undefined
    # overflow.
    for size in (32, 64):
        if min_val >= -(2 ** (size - 1)) and max_val <= 2 ** (size - 1) - 1:
            return "::std::int{}_t".format(size)
        elif min_val >= 0 and max_val <= 2**size - 1:
            return "::std::uint{}_t".format(size)
    return None


def _cpp_integer_type_for_enum(max_bits, is_signed):
    """Returns the appropriate C++ integer type to hold an enum."""
    # This is used to determine the `X` in `enum class : X`.
    #
    # Unlike _cpp_integer_type_for_range, the type chosen here is used for actual
    # storage.  Further, sizes smaller than 64 are explicitly chosen by a human
    # author, so take the smallest size that can hold the given number of bits.
    #
    # Technically, the C++ standard allows some of these sizes of integer to not
    # exist, and other sizes (say, int24_t) might exist, but in practice this set
    # is almost always available.  If you're compiling for some exotic DSP that
    # uses unusual int sizes, email emboss-dev@google.com.
    for size in (8, 16, 32, 64):
        if max_bits <= size:
            return "::std::{}int{}_t".format("" if is_signed else "u", size)
    assert False, f"Invalid value {max_bits} for maximum_bits"


def _render_builtin_operation(expression, ir, field_reader, subexpressions):
    """Renders a built-in operation (+, -, &&, etc.) into C++ code."""
    assert expression.function.function not in (
        ir_data.FunctionMapping.UPPER_BOUND,
        ir_data.FunctionMapping.LOWER_BOUND,
    ), "UPPER_BOUND and LOWER_BOUND should be constant."
    if expression.function.function == ir_data.FunctionMapping.PRESENCE:
        return field_reader.render_existence(
            expression.function.args[0], subexpressions
        )
    args = expression.function.args
    # `true && x` and `false || x` are exactly `x` under Emboss's Maybe<bool>
    # semantics; the constant operands come from existence conditions which
    # have been partially resolved at compile time.
    if expression.function.function == ir_data.FunctionMapping.AND:
        if _is_constant_true(args[0]):
            return _render_expression(
                args[1], ir, field_reader, subexpressions
            ).rendered
        if _is_constant_true(args[1]):
            return _render_expression(
                args[0], ir, field_reader, subexpressions
            ).rendered
    elif expression.function.function == ir_data.FunctionMapping.OR:
        if _is_constant_false(args[0]):
            return _render_expression(
                args[1], ir, field_reader, subexpressions
            ).rendered
        if _is_constant_false(args[1]):
            return _render_expression(
                args[0], ir, field_reader, subexpressions
            ).rendered
    rendered_args = [
        _render_expression(arg, ir, field_reader, subexpressions).rendered
        for arg in args
    ]
    minimum_integers = []
    maximum_integers = []
    enum_types = set()
    have_boolean_types = False
    for subexpression in [expression] + list(args):
        if subexpression.type.which_type == "integer":
            minimum_integers.append(int(subexpression.type.integer.minimum_value))
            maximum_integers.append(int(subexpression.type.integer.maximum_value))
        elif subexpression.type.which_type == "enumeration":
            enum_types.add(_cpp_basic_type_for_expression(subexpression, ir))
        elif subexpression.type.which_type == "boolean":
            have_boolean_types = True
    # At present, all Emboss functions other than `$has` take and return one of
    # the following:
    #
    #     integers
    #     integers and booleans
    #     a single enum type
    #     a single enum type and booleans
    #     booleans
    #
    # Really, the intermediate type is only necessary for integers, but it
    # simplifies the C++ somewhat if the appropriate enum/boolean type is provided
    # as "IntermediateT" -- it means that, e.g., the choice ("?:") operator does
    # not have to have two versions, one of which casts (some of) its arguments to
    # IntermediateT, and one of which does not.
    #
    # This is not a particularly robust scheme, but it works for all of the Emboss
    # functions I (bolms@) have written and am considering (division, modulus,
    # exponentiation, logical negation, bit shifts, bitwise and/or/xor, $min,
    # $floor, $ceil, $has).
    if minimum_integers and not enum_types:
        intermediate_type = _cpp_integer_type_for_range(
            min(minimum_integers), max(maximum_integers)
        )
    elif len(enum_types) == 1 and not minimum_integers:
        intermediate_type = list(enum_types)[0]
    else:
        assert have_boolean_types
        assert not enum_types
        assert not minimum_integers
        intermediate_type = "bool"
    arg_types = [_cpp_basic_type_for_expression(arg, ir) for arg in args]
    result_type = _cpp_basic_type_for_expression(expression, ir)
    function_variant = "</**/{}, {}, {}>".format(
        intermediate_type, result_type, ", ".join(arg_types)
    )
    return "::emboss::support::{}{}({})".format(
        _builtin_function_name(expression.function.function),
        function_variant,
        ", ".join(rendered_args),
    )


class _FieldRenderer(object):
    """Base class for rendering field reads."""

    def render_field_read_with_context(self, expression, ir, prefix, subexpressions):
        # The read is a single call, so there is no subexpression to share.
        del subexpressions  # Unused.
        field = prefix + _render_variable(
            ir_util.hashable_form_of_field_reference(expression.field_reference)
        )
        expression_cpp_type = _cpp_basic_type_for_expression(expression, ir)
        return "::emboss::support::MaybeStaticCast</**/{}>({}.OkAndUncheckedRead())".format(
            expression_cpp_type, field
        )

    def render_existence_with_context(self, expression, prefix, subexpressions):
        return "{1}{0}".format(
            _render_variable(
                ir_util.hashable_form_of_field_reference(expression.field_reference),
                "has_",
            ),
            prefix,
        )


class _DirectFieldRenderer(_FieldRenderer):
    """Renderer for fields read from inside a structure's View type."""

    def render_field(self, expression, ir, subexpressions):
        return self.render_field_read_with_context(expression, ir, "", subexpressions)

    def render_existence(self, expression, subexpressions):
        return self.render_existence_with_context(expression, "", subexpressions)


class _VirtualViewFieldRenderer(_FieldRenderer):
    """Renderer for field reads from inside a virtual field's View."""

    def render_existence(self, expression, subexpressions):
        return self.render_existence_with_context(expression, "view_.", subexpressions)

    def render_field(self, expression, ir, subexpressions):
        return self.render_field_read_with_context(
            expression, ir, "view_.", subexpressions
        )


class ExpressionScope(object):
    """Holder for subexpressions to be assigned to local variables, with scoping."""

    def __init__(self, prefix, parent=None):
        self._prefix = prefix
        self._parent = parent
        self._subexpr_to_name = {}
        self._index_to_subexpr = []
        self._depth = 0 if parent is None else parent._depth + 1

    def child(self):
        """Returns a new scope for a block nested inside this scope's block.

        Subexpressions already defined in this scope (or its ancestors) are
        reused by the child; new subexpressions are defined in the child.  The
        child's names cannot collide with any ancestor's, but sibling scopes
        (for sibling blocks) use the same names, so that blocks with identical
        contents render identically.
        """
        return ExpressionScope(
            "{}{}_".format(self._prefix, self._depth + 1), parent=self
        )

    def add(self, subexpr):
        # Check if expression exists in current or parent scopes
        scope = self
        while scope:
            if subexpr in scope._subexpr_to_name:
                return scope._subexpr_to_name[subexpr]
            scope = scope._parent

        # Not found, add to current scope
        self._index_to_subexpr.append(subexpr)
        self._subexpr_to_name[subexpr] = self._prefix + str(len(self._index_to_subexpr))
        return self._subexpr_to_name[subexpr]

    def mark(self):
        """Returns a token for discard_since()."""
        return len(self._index_to_subexpr)

    def discard_since(self, mark):
        """Removes the subexpressions added to this scope since `mark`.

        Used to drop a subexpression which turned out to have no users, so
        that the generated code does not define an unused variable.
        """
        for subexpr in self._index_to_subexpr[mark:]:
            del self._subexpr_to_name[subexpr]
        del self._index_to_subexpr[mark:]

    def subexprs(self):
        return [
            (self._subexpr_to_name[subexpr], subexpr)
            for subexpr in self._index_to_subexpr
        ]

    def definition_code(self, indent="      "):
        return "".join(
            [
                "{}const auto {} = {};\n".format(indent, name, subexpr)
                for name, subexpr in self.subexprs()
            ]
        )


_ExpressionResult = collections.namedtuple(
    "ExpressionResult", ["rendered", "is_constant"]
)


def _render_expression(expression, ir, field_reader=None, subexpressions=None):
    """Renders an expression into C++ code.

    Arguments:
        expression: The expression to render.
        ir: The IR in which to look up references.
        field_reader: An object with render_existence and render_field methods
            appropriate for the C++ context of the expression.
        subexpressions: A ExpressionScope in which to put subexpressions, or
            None if subexpressions should be inline.

    Returns:
        A tuple of (rendered_text, is_constant), where rendered_text is C++ code
        that can be emitted, and is_constant is True if the expression is a
        compile-time constant suitable for use in a C++11 constexpr context,
        otherwise False.
    """
    if field_reader is None:
        field_reader = _DirectFieldRenderer()

    # If the expression is constant, there are no guarantees that subexpressions
    # will fit into C++ types, or that operator arguments and return types can fit
    # in the same type: expressions like `-0x8000_0000_0000_0000` and
    # `0x1_0000_0000_0000_0000 - 1` can appear.
    if expression.type.which_type == "integer":
        if expression.type.integer.modulus == "infinity":
            return _ExpressionResult(
                _render_integer_for_expression(
                    int(expression.type.integer.modular_value)
                ),
                True,
            )
    elif expression.type.which_type == "boolean":
        if expression.type.boolean.has_field("value"):
            if expression.type.boolean.value:
                return _ExpressionResult(_maybe_type("bool") + "(true)", True)
            else:
                return _ExpressionResult(_maybe_type("bool") + "(false)", True)
    elif expression.type.which_type == "enumeration":
        if expression.type.enumeration.has_field("value"):
            return _ExpressionResult(
                _render_enum_value(expression.type.enumeration, ir), True
            )
    else:
        # There shouldn't be any "opaque" type expressions here.
        assert False, "Unhandled expression type {}".format(expression.type.which_type)

    result = None
    # Otherwise, render the operation.
    if expression.which_expression == "function":
        result = _render_builtin_operation(expression, ir, field_reader, subexpressions)
    elif expression.which_expression == "field_reference":
        result = field_reader.render_field(expression, ir, subexpressions)
    elif (
        expression.which_expression == "builtin_reference"
        and expression.builtin_reference.canonical_name.object_path[-1]
        == "$logical_value"
    ):
        return _ExpressionResult(
            _maybe_type("decltype(emboss_reserved_local_value)")
            + "(emboss_reserved_local_value)",
            False,
        )

    # Any of the constant expression types should have been handled in the
    # previous section.
    assert result is not None, "Unable to render expression {}".format(str(expression))

    if subexpressions is None:
        return _ExpressionResult(result, False)
    else:
        return _ExpressionResult(subexpressions.add(result), False)


def _render_existence_test(field, ir, subexpressions=None):
    return _render_expression(
        field.existence_condition, ir, subexpressions=subexpressions
    )


# Generated methods whose bodies evaluate Emboss expressions -- has_${field}(),
# the accessors of fields at non-constant locations, and the read methods of
# virtual fields -- are only forced inline (EMBOSS_ALWAYS_INLINE) when the code
# they pull in is bounded.  Forcing a method inline forces everything it calls
# that is also forced inline, so a chain like
#
#     let o1 = l1.length + 1
#     o1 [+1]  Length  l2
#     let o2 = o1 + l2.length + 1   # reads o1 twice: once directly, once
#     ...                           # through l2's location
#
# would otherwise inline 2**N copies of o1 into oN, and the compiler would run
# out of memory on real-world structures.  The analysis below follows
# references from one generated method into the next -- a conditional field's
# has_${field}(), a dynamically-located field's accessor, a virtual field's
# read -- and stops forcing after _MAX_FORCED_INLINE_DEPTH such hops, so that
# the forced-inline code reachable from any method is a bounded multiple of the
# size of the structure definition.
_MAX_FORCED_INLINE_DEPTH = 3


def _field_is_cheap_to_read(field, ir, depth):
    """Returns True if reading `field` inlines a bounded amount of code.

    `depth` is the number of generated methods already traversed to reach this
    field; see _MAX_FORCED_INLINE_DEPTH.
    """
    if ir_util.field_is_virtual(field):
        if _is_constant(field.read_transform):
            pass
        elif field.write_method.which_method == "alias":
            # The alias's accessor forwards to the aliased field's view.
            if not _field_reference_is_cheap_to_inline(
                field.write_method.alias.path, ir, depth
            ):
                return False
        elif depth >= _MAX_FORCED_INLINE_DEPTH:
            return False
        elif not _expression_is_cheap_to_inline(field.read_transform, ir, depth + 1):
            # Reading the virtual field runs its read method.
            return False
    else:
        start = field.location.start
        size = field.location.size
        if (
            ir_util.constant_value(start) is None
            or ir_util.constant_value(size) is None
        ):
            # The accessor evaluates the field's location.
            if depth >= _MAX_FORCED_INLINE_DEPTH:
                return False
            if not (
                _expression_is_cheap_to_inline(start, ir, depth + 1)
                and _expression_is_cheap_to_inline(size, ir, depth + 1)
            ):
                return False
        if field.type.has_field("atomic_type") and not all(
            _expression_is_cheap_to_inline(parameter, ir, depth + 1)
            for parameter in field.type.atomic_type.runtime_parameter
        ):
            # The accessor also evaluates the field's parameters.
            return False
    if not _is_constant_true(field.existence_condition):
        # Reading a conditional field runs its has_${field}().
        if depth >= _MAX_FORCED_INLINE_DEPTH:
            return False
        conjuncts = _existence_conjuncts(field.existence_condition, ir)
        if conjuncts and not all(
            _expression_is_cheap_to_inline(conjunct, ir, depth + 1)
            for conjunct in conjuncts
        ):
            return False
    return True


def _field_reference_is_cheap_to_inline(path, ir, depth):
    """Returns True if reading the referenced field inlines a bounded amount of code.

    Every field along the path (`a.b.c` reads `a`, then `b` within it, then
    `c`) must be cheap to read.
    """
    for segment in path:
        target = ir_util.find_object(segment, ir)
        if isinstance(target, ir_data.RuntimeParameter):
            continue
        if not isinstance(target, ir_data.Field):
            return False
        if not _field_is_cheap_to_read(target, ir, depth):
            return False
    return True


def _expression_is_cheap_to_inline(expression, ir, depth=0):
    """Returns True if evaluating `expression` inlines a bounded amount of code.

    See `_field_reference_is_cheap_to_inline` for the definition of "bounded".
    """
    if _is_constant(expression):
        return True
    if expression.which_expression == "field_reference":
        return _field_reference_is_cheap_to_inline(
            expression.field_reference.path, ir, depth
        )
    if expression.which_expression == "function":
        if expression.function.function == ir_data.FunctionMapping.PRESENCE:
            # `$present(x)` calls has_x(), which evaluates x's existence
            # condition.
            path = expression.function.args[0].field_reference.path
            target = ir_util.find_object(path[-1], ir)
            if len(path) != 1 or not isinstance(target, ir_data.Field):
                return False
            if _is_constant_true(target.existence_condition):
                return True
            if depth >= _MAX_FORCED_INLINE_DEPTH:
                return False
            return _expression_is_cheap_to_inline(
                target.existence_condition, ir, depth + 1
            )
        return all(
            _expression_is_cheap_to_inline(arg, ir, depth)
            for arg in expression.function.args
        )
    return True


def _inline_specifier(expressions, ir):
    """Returns the inline specifier for a method which evaluates `expressions`."""
    if all(
        _expression_is_cheap_to_inline(expression, ir) for expression in expressions
    ):
        return "EMBOSS_ALWAYS_INLINE"
    return "inline"


def _alignment_of_location(location):
    constraints = location.start.type.integer
    if constraints.modulus == "infinity":
        # The C++ templates use 0 as a sentinel value meaning infinity for
        # alignment.
        return 0, constraints.modular_value
    else:
        return constraints.modulus, constraints.modular_value


def _get_cpp_type_reader_of_field(
    field_ir, ir, buffer_type, validator, parent_addressable_unit
):
    """Returns the C++ view type for a field."""
    field_size = None
    if field_ir.type.has_field("size_in_bits"):
        field_size = ir_util.constant_value(field_ir.type.size_in_bits)
        assert field_size is not None
    elif ir_util.is_constant(field_ir.location.size):
        # TODO(bolms): Normalize the IR so that this clause is unnecessary.
        field_size = (
            ir_util.constant_value(field_ir.location.size) * parent_addressable_unit
        )
    byte_order_attr = ir_util.get_attribute(field_ir.attribute, "byte_order")
    if byte_order_attr:
        byte_order = byte_order_attr.string_constant.text
    else:
        byte_order = ""
    field_alignment, field_offset = _alignment_of_location(field_ir.location)
    return _get_cpp_view_type_for_physical_type(
        field_ir.type,
        field_size,
        byte_order,
        ir,
        _offset_storage_adapter(buffer_type, field_alignment, field_offset),
        parent_addressable_unit,
        validator,
    )


def _generate_structure_field_methods(
    enclosing_type_name, field_ir, ir, parent_addressable_unit
):
    if ir_util.field_is_virtual(field_ir):
        return _generate_structure_virtual_field_methods(
            enclosing_type_name, field_ir, ir
        )
    else:
        return _generate_structure_physical_field_methods(
            enclosing_type_name, field_ir, ir, parent_addressable_unit
        )


def _generate_custom_validator_expression_for(field_ir, ir):
    """Returns a validator expression for the given field, or None."""
    requires_attr = ir_util.get_attribute(field_ir.attribute, "requires")
    if requires_attr:

        class _ValidatorFieldReader(object):
            """A "FieldReader" that translates the current field to `value`."""

            def render_existence(self, expression, subexpressions):
                del expression  # Unused.
                assert False, "Shouldn't be here."

            def render_field(self, expression, ir, subexpressions):
                assert len(expression.field_reference.path) == 1
                assert (
                    expression.field_reference.path[0].canonical_name
                    == field_ir.name.canonical_name
                )
                expression_cpp_type = _cpp_basic_type_for_expression(expression, ir)
                return "{}(emboss_reserved_local_value)".format(
                    _maybe_type(expression_cpp_type)
                )

        validation_body = _render_expression(
            requires_attr.expression, ir, _ValidatorFieldReader()
        )
        return validation_body.rendered
    else:
        return None


def _generate_validator_expression_for(field_ir, ir):
    """Returns a validator expression for the given field."""
    result = _generate_custom_validator_expression_for(field_ir, ir)
    if result is None:
        return "::emboss::support::Maybe<bool>(true)"
    return result


def _generate_structure_virtual_field_methods(enclosing_type_name, field_ir, ir):
    """Generates C++ code for methods for a single virtual field.

    Arguments:
      enclosing_type_name: The text name of the enclosing type.
      field_ir: The IR for the field to generate methods for.
      ir: The full IR for the module.

    Returns:
      A tuple of ("", declarations, definitions).  The declarations can be
      inserted into the class definition for the enclosing type's View.  Any
      definitions should be placed after the class definition.  These are
      separated to satisfy C++'s declaration-before-use requirements.
    """
    if field_ir.write_method.which_method == "alias":
        return _generate_field_indirection(field_ir, enclosing_type_name, ir)

    read_subexpressions = ExpressionScope("emboss_reserved_local_subexpr_")
    read_value = _render_expression(
        field_ir.read_transform,
        ir,
        field_reader=_VirtualViewFieldRenderer(),
        subexpressions=read_subexpressions,
    )
    field_exists_subexpressions, field_exists_rendered = _generate_field_existence_body(
        field_ir, ir
    )
    field_exists_is_constant = _render_expression(
        field_ir.existence_condition, ir
    ).is_constant
    logical_type = _cpp_basic_type_for_expression(field_ir.read_transform, ir)

    if read_value.is_constant and field_exists_is_constant:
        assert not read_subexpressions.subexprs()
        declaration_template = (
            _TEMPLATES.structure_single_const_virtual_field_method_declarations
        )
        definition_template = (
            _TEMPLATES.structure_single_const_virtual_field_method_definitions
        )
        rendered_read_subexpressions = ""
        rendered_read_value = read_value.rendered
    else:
        declaration_template = (
            _TEMPLATES.structure_single_virtual_field_method_declarations
        )
        definition_template = (
            _TEMPLATES.structure_single_virtual_field_method_definitions
        )
        if field_ir.name.name.text in ("$size_in_bits", "$size_in_bytes"):
            rendered_read_subexpressions, rendered_read_value = (
                _generate_optimized_size_read(field_ir, logical_type, ir)
            )
        else:
            rendered_read_subexpressions = read_subexpressions.definition_code()
            rendered_read_value = read_value.rendered

    if field_ir.write_method.which_method == "transform":
        destination = _render_variable(
            ir_util.hashable_form_of_field_reference(
                field_ir.write_method.transform.destination
            )
        )
        transform = _render_expression(
            field_ir.write_method.transform.function_body,
            ir,
            field_reader=_VirtualViewFieldRenderer(),
        ).rendered
        write_methods = code_template.format_template(
            _TEMPLATES.structure_single_virtual_field_write_methods,
            logical_type=logical_type,
            destination=destination,
            transform=transform,
        )
    else:
        write_methods = ""

    name = field_ir.name.canonical_name.object_path[-1]
    if name.startswith("$"):
        name = _cpp_field_name(field_ir.name.name.text)
        virtual_view_type_name = "EmbossReservedDollarVirtual{}View".format(name)
    else:
        virtual_view_type_name = "EmbossReservedVirtual{}View".format(
            name_conversion.snake_to_camel(name)
        )
    assert logical_type, "Could not find appropriate C++ type for {}".format(
        field_ir.read_transform
    )
    if field_ir.read_transform.type.which_type == "integer":
        write_to_text_stream_function = "WriteIntegerViewToTextStream"
    elif field_ir.read_transform.type.which_type == "boolean":
        write_to_text_stream_function = "WriteBooleanViewToTextStream"
    elif field_ir.read_transform.type.which_type == "enumeration":
        write_to_text_stream_function = "WriteEnumViewToTextStream"
    else:
        assert False, "Unexpected read-only virtual field type {}".format(
            field_ir.read_transform.type.which_type
        )

    value_is_ok = _generate_validator_expression_for(field_ir, ir)
    # The read methods evaluate the read transform and, through Read()'s and
    # Ok()'s ValueIsOk(), the [requires] expression, if any.
    read_expressions = [field_ir.read_transform]
    requires_attr = ir_util.get_attribute(field_ir.attribute, "requires")
    if requires_attr is not None:
        read_expressions.append(requires_attr.expression)
    existence_conjuncts = _existence_conjuncts(field_ir.existence_condition, ir)
    declaration = code_template.format_template(
        declaration_template,
        visibility=_visibility_for_field(field_ir),
        name=name,
        virtual_view_type_name=virtual_view_type_name,
        logical_type=logical_type,
        read_subexpressions=rendered_read_subexpressions,
        read_value=rendered_read_value,
        write_to_text_stream_function=write_to_text_stream_function,
        parent_type=enclosing_type_name,
        write_methods=write_methods,
        value_is_ok=value_is_ok,
        inline=_inline_specifier(read_expressions, ir),
    )
    definition = code_template.format_template(
        definition_template,
        name=name,
        virtual_view_type_name=virtual_view_type_name,
        logical_type=logical_type,
        read_value=rendered_read_value,
        parent_type=enclosing_type_name,
        field_exists_subexpressions=field_exists_subexpressions,
        field_exists=field_exists_rendered,
        has_inline=_inline_specifier(existence_conjuncts or [], ir),
    )
    return "", declaration, definition


def _generate_validator_type_for(enclosing_type_name, field_ir, ir):
    """Returns a validator type name and definition for the given field."""
    result_expression = _generate_custom_validator_expression_for(field_ir, ir)
    if result_expression is None:
        return "::emboss::support::AllValuesAreOk", ""

    field_name = field_ir.name.canonical_name.object_path[-1]
    validator_type_name = "EmbossReservedValidatorFor{}".format(
        name_conversion.snake_to_camel(field_name)
    )
    qualified_validator_type_name = "{}::{}".format(
        enclosing_type_name, validator_type_name
    )

    validator_declaration = code_template.format_template(
        _TEMPLATES.structure_field_validator,
        name=validator_type_name,
        expression=result_expression,
    )
    validator_declaration = _wrap_in_namespace(
        validator_declaration, [enclosing_type_name]
    )
    return qualified_validator_type_name, validator_declaration


def _generate_structure_physical_field_methods(
    enclosing_type_name, field_ir, ir, parent_addressable_unit
):
    """Generates C++ code for methods for a single physical field.

    Arguments:
      enclosing_type_name: The text name of the enclosing type.
      field_ir: The IR for the field to generate methods for.
      ir: The full IR for the module.
      parent_addressable_unit: The addressable unit (BIT or BYTE) of the enclosing
          structure.

    Returns:
      A tuple of (declarations, definitions).  The declarations can be inserted
      into the class definition for the enclosing type's View.  Any definitions
      should be placed after the class definition.  These are separated to satisfy
      C++'s declaration-before-use requirements.
    """
    validator_type, validator_declaration = _generate_validator_type_for(
        enclosing_type_name, field_ir, ir
    )

    type_reader, unused_parameter_types, parameter_expressions = (
        _get_cpp_type_reader_of_field(
            field_ir, ir, "Storage", validator_type, parent_addressable_unit
        )
    )

    field_name = field_ir.name.canonical_name.object_path[-1]

    subexpressions = ExpressionScope("emboss_reserved_local_subexpr_")
    parameter_values = []
    parameter_known_checks = []
    for parameter in parameter_expressions:
        parameter_cpp_expr = _render_expression(
            parameter, ir, subexpressions=subexpressions
        )
        parameter_values.append(
            "{}.ValueOrDefault(), ".format(parameter_cpp_expr.rendered)
        )
        parameter_known_checks.append("{}.Known()".format(parameter_cpp_expr.rendered))
    parameter_subexpressions = subexpressions.definition_code("  ")

    field_exists_subexpressions, field_exists_rendered = _generate_field_existence_body(
        field_ir, ir
    )
    field_alignment, field_offset = _alignment_of_location(field_ir.location)
    declaration = code_template.format_template(
        _TEMPLATES.structure_single_field_method_declarations,
        type_reader=type_reader,
        visibility=_visibility_for_field(field_ir),
        name=field_name,
    )
    common_arguments = dict(
        parent_type=enclosing_type_name,
        name=field_name,
        type_reader=type_reader,
        alignment=field_alignment,
        static_offset=field_offset,
        field_exists_subexpressions=field_exists_subexpressions,
        field_exists=field_exists_rendered,
        parameter_values="".join(parameter_values),
        parameter_subexpressions=parameter_subexpressions,
        has_inline=_inline_specifier(
            _existence_conjuncts(field_ir.existence_condition, ir) or [], ir
        ),
    )
    constant_offset = ir_util.constant_value(field_ir.location.start)
    constant_size = ir_util.constant_value(field_ir.location.size)
    if (
        constant_offset is not None
        and constant_offset >= 0
        and constant_size is not None
        and constant_size >= 0
    ):
        # The field's location is known at compile time, so the only runtime
        # questions are whether the field is present and whether its
        # parameters (if any) are Known.
        conditions = list(parameter_known_checks)
        if not _is_constant_true(field_ir.existence_condition):
            conditions.append("has_{}().ValueOr(false)".format(field_name))
        if conditions:
            template = _TEMPLATES.conditional_constant_location_field_method_definitions
        else:
            template = (
                _TEMPLATES.unconditional_constant_location_field_method_definitions
            )
        definition = code_template.format_template(
            template,
            const_offset=_render_integer(constant_offset),
            const_size=_render_integer(constant_size),
            condition=" && ".join(conditions),
            inline=_inline_specifier(parameter_expressions, ir),
            **common_arguments,
        )
    else:
        first_size_and_offset_subexpr = len(subexpressions.subexprs())
        offset = _render_expression(
            field_ir.location.start, ir, subexpressions=subexpressions
        ).rendered
        size = _render_expression(
            field_ir.location.size, ir, subexpressions=subexpressions
        ).rendered
        size_and_offset_subexpressions = "".join(
            [
                "    const auto {} = {};\n".format(name, subexpr)
                for name, subexpr in subexpressions.subexprs()[
                    first_size_and_offset_subexpr:
                ]
            ]
        )
        definition = code_template.format_template(
            _TEMPLATES.structure_single_field_method_definitions,
            offset=offset,
            size=size,
            size_and_offset_subexpressions=size_and_offset_subexpressions,
            parameters_known="".join(
                "{} && ".format(check) for check in parameter_known_checks
            ),
            inline=_inline_specifier(
                [field_ir.location.start, field_ir.location.size]
                + list(parameter_expressions),
                ir,
            ),
            **common_arguments,
        )
    return validator_declaration, declaration, definition


def _render_size_method(fields, ir):
    """Renders the Size methods of a struct or bits, using the correct templates.

    Arguments:
      fields: The list of fields in the struct or bits.  This is used to find the
        $size_in_bits or $size_in_bytes virtual field.
      ir: The IR to which fields belong.

    Returns:
      A string representation of the Size methods, suitable for inclusion in an
      Emboss View class.
    """
    # The SizeInBytes(), SizeInBits(), and SizeIsKnown() methods just forward to
    # the generated IntrinsicSizeIn$_units_$() method, which returns a virtual
    # field with Read() and Ok() methods.
    #
    # TODO(bolms): Remove these shims, rename IntrinsicSizeIn$_units_$ to
    # SizeIn$_units_$, and update all callers to the new API.
    for field in fields:
        if field.name.name.text in ("$size_in_bits", "$size_in_bytes"):
            # If the read_transform and existence_condition are constant, then the
            # size is constexpr.
            if (
                _render_expression(field.read_transform, ir).is_constant
                and _render_expression(field.existence_condition, ir).is_constant
            ):
                template = _TEMPLATES.constant_structure_size_method
            else:
                template = _TEMPLATES.runtime_structure_size_method
            return code_template.format_template(
                template,
                units="Bits" if field.name.name.text == "$size_in_bits" else "Bytes",
            )
    assert False, "Expected a $size_in_bits or $size_in_bytes field."


def _visibility_for_field(field_ir):
    """Returns the C++ visibility for field_ir within its parent view."""
    # Generally, the Google style guide for hand-written C++ forbids having
    # multiple public: and private: sections, but trying to conform to that bit of
    # the style guide would make this file significantly more complex.
    #
    # Alias fields are generated as simple methods that forward directly to the
    # aliased field's method:
    #
    #     auto alias() const -> decltype(parent().child().aliased_subchild()) {
    #       return parent().child().aliased_subchild();
    #     }
    #
    # Figuring out the return type of `parent().child().aliased_subchild()` is
    # quite complex, since there are several levels of template indirection
    # involved.  It is much easier to just leave it up to the C++ compiler.
    #
    # Unfortunately, the C++ compiler will complain if `parent()` is not declared
    # before `alias()`.  If the `parent` field happens to be anonymous, the Google
    # style guide would put `parent()`'s declaration after `alias()`'s
    # declaration, which causes the C++ compiler to complain that `parent` is
    # unknown.
    #
    # The easy fix to this is just to declare `parent()` before `alias()`, and
    # explicitly mark `parent()` as `private` and `alias()` as `public`.
    #
    # Perhaps surprisingly, this limitation does not apply when `parent()`'s type
    # is not yet complete at the point where `alias()` is declared; I believe this
    # is because both `parent()` and `alias()` exist in a templated `class`, and
    # by the time `parent().child().aliased_subchild()` is actually resolved, the
    # compiler is instantiating the class and has the full definitions of all the
    # other classes available.
    if field_ir.name.is_anonymous:
        return "private"
    else:
        return "public"


def _generate_field_indirection(field_ir, parent_type_name, ir):
    """Renders a method which forwards to a field's view."""
    rendered_aliased_field = _render_variable(
        ir_util.hashable_form_of_field_reference(field_ir.write_method.alias)
    )
    field_exists_subexpressions, field_exists_rendered = _generate_field_existence_body(
        field_ir, ir
    )
    first_target = ir_util.find_object(field_ir.write_method.alias.path[0], ir)
    if _is_constant_true(field_ir.existence_condition) or (
        isinstance(first_target, ir_data.Field) and first_target.name.is_anonymous
    ):
        # The aliased field's own view already reflects the alias's existence
        # condition: the alias is either unconditional, or an alias into an
        # anonymous `bits` field, whose existence condition (the `&&` of the
        # anonymous field's and the aliased field's conditions) is exactly
        # what the chain of field methods checks.  Either way, there is no
        # need to check has_${name}() before forwarding.
        declaration_template = (
            _TEMPLATES.unconditional_structure_single_field_indirect_method_declarations
        )
    else:
        declaration_template = (
            _TEMPLATES.structure_single_field_indirect_method_declarations
        )
    declaration = code_template.format_template(
        declaration_template,
        aliased_field=rendered_aliased_field,
        visibility=_visibility_for_field(field_ir),
        parent_type=parent_type_name,
        name=field_ir.name.name.text,
    )
    definition = code_template.format_template(
        _TEMPLATES.struct_single_field_indirect_method_definitions,
        parent_type=parent_type_name,
        name=field_ir.name.name.text,
        aliased_field=rendered_aliased_field,
        field_exists_subexpressions=field_exists_subexpressions,
        field_exists=field_exists_rendered,
        has_inline=_inline_specifier(
            _existence_conjuncts(field_ir.existence_condition, ir) or [], ir
        ),
    )
    return "", declaration, definition


def _generate_subtype_definitions(type_ir, ir, config: Config):
    """Generates C++ code for subtypes of type_ir."""
    subtype_bodies = []
    subtype_forward_declarations = []
    subtype_method_definitions = []
    type_name = type_ir.name.name.text
    for subtype in type_ir.subtype:
        inner_defs = _generate_type_definition(subtype, ir, config)
        subtype_forward_declaration, subtype_body, subtype_methods = inner_defs
        subtype_forward_declarations.append(subtype_forward_declaration)
        subtype_bodies.append(subtype_body)
        subtype_method_definitions.append(subtype_methods)
    wrapped_forward_declarations = _wrap_in_namespace(
        "\n".join(subtype_forward_declarations), [type_name]
    )
    wrapped_bodies = _wrap_in_namespace("\n".join(subtype_bodies), [type_name])
    wrapped_method_definitions = _wrap_in_namespace(
        "\n".join(subtype_method_definitions), [type_name]
    )
    return (wrapped_bodies, wrapped_forward_declarations, wrapped_method_definitions)


def _cpp_field_name(name):
    """Returns the C++ name for the given field name."""
    if name.startswith("$"):
        dollar_field_names = {
            "$size_in_bits": "IntrinsicSizeInBits",
            "$size_in_bytes": "IntrinsicSizeInBytes",
            "$max_size_in_bits": "MaxSizeInBits",
            "$min_size_in_bits": "MinSizeInBits",
            "$max_size_in_bytes": "MaxSizeInBytes",
            "$min_size_in_bytes": "MinSizeInBytes",
        }
        return dollar_field_names[name]
    else:
        return name


# The rest of this section analyzes field existence conditions, so that Ok(),
# has_${field}(), and $size_in_bits/$size_in_bytes can:
#
#   * evaluate a condition that several fields share once, as an `if` or a
#     `switch`, instead of once per field;
#   * skip checks that provably cannot fail; and
#   * skip `Known()` tests on conditions that provably are Known().
#
# Everything here is conservative: when in doubt, the generated code falls
# back to evaluating the full Emboss expression with Maybe<> semantics.


def _is_constant_true(expression):
    """Returns True if `expression` is statically known to be `true`."""
    return (
        expression.type.which_type == "boolean"
        and expression.type.boolean.has_field("value")
        and expression.type.boolean.value
    )


def _is_constant_false(expression):
    """Returns True if `expression` is statically known to be `false`."""
    return (
        expression.type.which_type == "boolean"
        and expression.type.boolean.has_field("value")
        and not expression.type.boolean.value
    )


def _is_constant(expression):
    """Returns True if the front end found a static value for `expression`."""
    expression_type = expression.type
    if expression_type.which_type == "integer":
        return expression_type.integer.modulus == "infinity"
    if expression_type.which_type == "boolean":
        return expression_type.boolean.has_field("value")
    if expression_type.which_type == "enumeration":
        return expression_type.enumeration.has_field("value")
    return False


def _inline_condition_helpers(expression, ir):
    """Replaces boolean `let`s and `$present()` in a condition by their definitions.

    A pattern like

        let is_sync = message_type == MessageType.SYNC
        if is_sync:
          ...

    hides the comparison behind a field reference, and `$present(x)` (which
    the front end also synthesizes for aliases into anonymous `bits`) hides
    `x`'s existence condition behind a call to has_x().  Inlining the
    definitions lets the condition-tree code below see the underlying
    comparisons, so that it can route the field into a `switch` on
    `message_type` together with the fields which test `message_type`
    directly, and recognize when the condition is implied by an enclosing one.

    Only unconditional, `[requires]`-free boolean virtuals are inlined, so
    that the inlined expression has exactly the same Maybe<bool> value as
    reading the virtual field; `$present(x)` always has the same value as
    `x`'s existence condition.
    """
    if expression.which_expression == "field_reference":
        path = expression.field_reference.path
        if len(path) != 1:
            return expression
        target = ir_util.find_object(path[0], ir)
        if (
            isinstance(target, ir_data.Field)
            and ir_util.field_is_virtual(target)
            and target.read_transform.type.which_type == "boolean"
            and _is_constant_true(target.existence_condition)
            and ir_util.get_attribute(target.attribute, "requires") is None
        ):
            return _inline_condition_helpers(target.read_transform, ir)
        return expression
    if expression.which_expression != "function":
        return expression
    function = expression.function.function
    if function == ir_data.FunctionMapping.PRESENCE:
        path = expression.function.args[0].field_reference.path
        if len(path) != 1:
            return expression
        target = ir_util.find_object(path[0], ir)
        if not isinstance(target, ir_data.Field):
            return expression
        return _inline_condition_helpers(target.existence_condition, ir)
    if function in (ir_data.FunctionMapping.AND, ir_data.FunctionMapping.OR):
        result = ir_data_utils.copy(expression)
        del result.function.args[:]
        for arg in expression.function.args:
            result.function.args.append(_inline_condition_helpers(arg, ir))
        return result
    return expression


def _existence_conjuncts(condition, ir):
    """Splits an existence condition into its top-level `&&` conjuncts.

    Returns `[]` when `condition` is statically true and `None` when it is
    statically false; otherwise returns the (non-empty) list of conjuncts,
    after inlining boolean `let`s and `$present()` (see
    `_inline_condition_helpers`).

    Emboss's `&&` is symmetric and associative (a Known-false operand makes
    the result Known-false even if the other operand is not Known), so the
    Maybe<bool> value of the condition is the `&&` of the conjuncts in any
    order, and callers are free to regroup them.
    """
    condition = _inline_condition_helpers(condition, ir)
    if _is_constant_false(condition):
        return None
    if _is_constant_true(condition):
        return []
    if (
        condition.which_expression == "function"
        and condition.function.function == ir_data.FunctionMapping.AND
    ):
        conjuncts = []
        for arg in condition.function.args:
            sub_conjuncts = _existence_conjuncts(arg, ir)
            if sub_conjuncts is None:
                return None
            conjuncts.extend(sub_conjuncts)
        return conjuncts
    return [condition]


def _boolean_function_expression(function, args):
    """Returns a synthetic boolean `function(*args)` IR expression."""
    return ir_data.Expression(
        function=ir_data.Function(function=function, args=list(args)),
        type=ir_data.ExpressionType(boolean=ir_data.BooleanType()),
    )


def _and_expression(conjuncts):
    """Returns an IR expression for the Emboss `&&` of `conjuncts`."""
    assert conjuncts
    result = conjuncts[0]
    for conjunct in conjuncts[1:]:
        result = _boolean_function_expression(
            ir_data.FunctionMapping.AND, [result, conjunct]
        )
    return result


def _or_expression(disjuncts):
    """Returns an IR expression for the Emboss `||` of `disjuncts`."""
    assert disjuncts
    result = disjuncts[0]
    for disjunct in disjuncts[1:]:
        result = _boolean_function_expression(
            ir_data.FunctionMapping.OR, [result, disjunct]
        )
    return result


def _render_condition_key(expression, ir):
    """Renders `expression` without a scope, for use as a grouping key."""
    return _render_expression(expression, ir, subexpressions=None).rendered


def _is_equality_check(expression):
    return (
        expression.which_expression == "function"
        and expression.function.function == ir_data.FunctionMapping.EQUALITY
        and len(expression.function.args) == 2
    )


def _render_case_label(expression, ir):
    if expression.type.which_type == "integer":
        return _render_integer(int(expression.type.integer.modular_value))
    elif expression.type.which_type == "enumeration":
        # Need fully qualified enum type name
        enum_type = expression.type.enumeration
        cpp_enum_type = _get_fully_qualified_name(enum_type.name.canonical_name, ir)
        return "static_cast</**/{}>({})".format(cpp_enum_type, enum_type.value)
    else:
        assert False, "Unsupported switch case type"


def _case_sort_key(expression):
    """Returns the underlying integer value of a switch case expression.

    Used to sort case labels within a switch so the emitted C++ presents cases
    in monotonic order. Compilers (particularly the older GCCs in many
    embedded toolchains) are more likely to generate a dense jump table when
    cases are sorted.
    """
    if expression.type.which_type == "integer":
        return int(expression.type.integer.modular_value)
    elif expression.type.which_type == "enumeration":
        return int(expression.type.enumeration.value)
    else:
        assert False, "Unsupported switch case type"


def _get_switch_candidate(expression, ir):
    """Returns (discriminant_expr, case_value_expr) or (None, None)."""
    if not _is_equality_check(expression):
        return None, None

    arg0 = expression.function.args[0]
    arg1 = expression.function.args[1]

    # Check if args are integer or enumeration (ignore boolean for switch)
    if arg0.type.which_type not in ("integer", "enumeration"):
        return None, None

    res0 = _render_expression(arg0, ir, subexpressions=None)
    res1 = _render_expression(arg1, ir, subexpressions=None)

    if res0.is_constant and not res1.is_constant:
        return arg1, arg0
    if res1.is_constant and not res0.is_constant:
        return arg0, arg1

    return None, None


def _flatten_function(expression, function):
    """Flatten a binary function chain into a flat list of operands.

    Both `(a OP b) OP c` and `a OP (b OP c)` flatten to `[a, b, c]`.
    """
    if (
        expression.which_expression == "function"
        and expression.function.function == function
    ):
        out = []
        for arg in expression.function.args:
            out.extend(_flatten_function(arg, function))
        return out
    return [expression]


def _flatten_or(expression):
    return _flatten_function(expression, ir_data.FunctionMapping.OR)


def _flatten_and(expression):
    return _flatten_function(expression, ir_data.FunctionMapping.AND)


def _extract_switch_arms(expression, ir):
    """Decomposes `expression` into a list of switch arms.

    Returns either:
      * (discriminant_expr, [(case_value_expr, residual_conjuncts), ...])
        when the expression decomposes into a switch on a single
        discriminant. `residual_conjuncts` is an empty list when the arm
        is a bare equality on the discriminant; otherwise it is the list
        of additional IR sub-expressions (`AND`-conjuncts) that the arm
        must also satisfy. Case values are returned in encounter order;
        the caller is responsible for sorting/coalescing.
      * (None, None) when the expression doesn't decompose into a switch.

    Supported shapes:
      * `discrim == K`                         → one arm, no residual.
      * `discrim == K1 || discrim == K2 || …`  → one arm per Ki, no
        residual. Common for tagged unions where several tag values
        share a payload (`if tag == 0x10 || tag == 0x11: …`).
      * `discrim == K && other_predicate`      → one arm with residual
        `[other_predicate]`. Useful for nested guards like
        `if outer_flag && tag == K:`.
      * `(discrim == K1 || …) && other`        → multiple arms each
        carrying `[other]` as residual.
      * Disjunction whose disjuncts mix shapes: `(tag == 0 && a) ||
        (tag == 1 && b) || tag == 2` → three arms with respective
        residuals `[a]`, `[b]`, `[]`.

    Residuals are handled by the condition tree as additional conjuncts
    nested inside the arm, so the optimization stays sound for
    partially-Known residuals.
    """
    # Bare equality.
    discrim, case_val = _get_switch_candidate(expression, ir)
    if discrim is not None:
        return discrim, [(case_val, [])]

    # Conjunction: try each conjunct as the switch source; if exactly one
    # extracts, the others become the residual.
    if (
        expression.which_expression == "function"
        and expression.function.function == ir_data.FunctionMapping.AND
    ):
        conjuncts = _flatten_and(expression)
        for i, c in enumerate(conjuncts):
            sub = _extract_switch_arms(c, ir)
            if sub[0] is None:
                continue
            other_conjuncts = [conjuncts[j] for j in range(len(conjuncts)) if j != i]
            sub_discrim, sub_arms = sub
            merged = [
                (case_val, residual + other_conjuncts)
                for (case_val, residual) in sub_arms
            ]
            return sub_discrim, merged
        return None, None

    # Disjunction: each disjunct must independently extract a switch on
    # the same discriminant.
    if (
        expression.which_expression == "function"
        and expression.function.function == ir_data.FunctionMapping.OR
    ):
        disjuncts = _flatten_or(expression)
        common_discrim = None
        common_discrim_str = None
        all_arms = []
        for d in disjuncts:
            sub_discrim, sub_arms = _extract_switch_arms(d, ir)
            if sub_discrim is None:
                return None, None
            sub_discrim_str = _render_condition_key(sub_discrim, ir)
            if common_discrim_str is None:
                common_discrim = sub_discrim
                common_discrim_str = sub_discrim_str
            elif sub_discrim_str != common_discrim_str:
                # Disjuncts disagree on the discriminant; can't be one switch.
                return None, None
            all_arms.extend(sub_arms)
        return common_discrim, all_arms

    return None, None


# Functions whose result is Known() whenever all of their arguments are.
#
# `$present()` is deliberately absent: `$present(x)` is `has_x()`, which can
# be un-Known even though its argument is a plain field reference.  `&&` is
# handled specially in _expression_is_always_known().
_TOTAL_FUNCTIONS = frozenset(
    [
        ir_data.FunctionMapping.ADDITION,
        ir_data.FunctionMapping.SUBTRACTION,
        ir_data.FunctionMapping.MULTIPLICATION,
        ir_data.FunctionMapping.EQUALITY,
        ir_data.FunctionMapping.INEQUALITY,
        ir_data.FunctionMapping.OR,
        ir_data.FunctionMapping.LESS,
        ir_data.FunctionMapping.LESS_OR_EQUAL,
        ir_data.FunctionMapping.GREATER,
        ir_data.FunctionMapping.GREATER_OR_EQUAL,
        ir_data.FunctionMapping.CHOICE,
        ir_data.FunctionMapping.MAXIMUM,
        ir_data.FunctionMapping.UPPER_BOUND,
        ir_data.FunctionMapping.LOWER_BOUND,
    ]
)


class _EvaluationPoint(object):
    """What is known at a point in generated code where a condition is evaluated.

    Attributes:
        guards: A frozenset of rendered conjuncts (see `_render_condition_key`)
            which are Known-true at this point.
        fields_validated: True inside Ok(), after IsComplete() has passed and
            while the structure's fields are being checked in dependency
            order.  There, every present field is in bounds (because
            $size_in_bits/$size_in_bytes covers every present field) and
            reads as Known: either its own Ok() check has already passed, or
            that check was elided because the field cannot be anything but
            Ok().  False inside the $size_in_bits/$size_in_bytes virtual,
            which IsComplete() evaluates before anything is known about the
            backing storage.
        readable_end: When `fields_validated` is False, the number of
            addressable units at the start of the backing storage which are
            known to exist, because a condition which reads them has already
            tested Known.  Fields which end before this point are complete.
    """

    def __init__(self, guards=frozenset(), fields_validated=True, readable_end=0):
        self.guards = guards
        self.fields_validated = fields_validated
        self.readable_end = readable_end

    def assuming(self, ir, conjuncts=(), readable_end=0):
        """Returns the point reached once `conjuncts` are Known-true.

        `readable_end` is the number of units known to exist at that point.
        """
        return self.with_guards(
            [_render_condition_key(c, ir) for c in conjuncts], readable_end
        )

    def with_guards(self, rendered_conjuncts, readable_end=0):
        """As `assuming`, for conjuncts which are already rendered."""
        return _EvaluationPoint(
            self.guards | frozenset(rendered_conjuncts),
            self.fields_validated,
            max(self.readable_end, readable_end),
        )


def _condition_is_implied(condition, guards, ir):
    """Returns True if `condition` must be Known-true wherever `guards` hold.

    `guards` is a set of rendered conjuncts (see `_render_condition_key`)
    which are Known-true at the point of interest.  The check is purely
    syntactic: every conjunct of `condition` must be one of the guards.
    """
    conjuncts = _existence_conjuncts(condition, ir)
    if conjuncts is None:
        return False
    return all(_render_condition_key(c, ir) in guards for c in conjuncts)


def _field_end(field, ir):
    """Returns the end of `field`'s location, in its structure's units, or None.

    Aliases resolve to the location of the aliased field; other virtual fields
    and fields at non-constant locations have no end.
    """
    if ir_util.field_is_virtual(field):
        if field.write_method.which_method == "alias":
            return _reference_end(field.write_method.alias.path, ir)
        return None
    start = ir_util.constant_value(field.location.start)
    size = ir_util.constant_value(field.location.size)
    if start is None or size is None or start < 0 or size < 0:
        return None
    return start + size


def _reference_end(path, ir):
    """Returns how many units of the structure a field reference needs, or None.

    This is the end of the referenced field, relative to the structure whose
    field is the first element of `path`: a reference `a.b` constructs `b`'s
    view over `a`'s bytes, so `b` is complete iff the structure has `a.start +
    b.end` units.  A `bits` field nested in a `struct` is read as a whole, so
    the end of the enclosing `struct` field is used instead.
    """
    offset = 0
    units = None
    whole_end = None
    for index, segment in enumerate(path):
        field = ir_util.find_object(segment, ir)
        if isinstance(field, ir_data.RuntimeParameter):
            # Parameters are not read from the backing storage.
            return 0 if len(path) == 1 else None
        if not isinstance(field, ir_data.Field):
            return None
        parent_units = ir_util.find_parent_object(field.name, ir).addressable_unit
        if units is None:
            units = parent_units
        elif parent_units != units:
            return whole_end
        field_end = _field_end(field, ir)
        if field_end is None:
            return None
        whole_end = offset + field_end
        if index == len(path) - 1:
            return whole_end
        if ir_util.field_is_virtual(field):
            # Following a reference through an alias is not supported.
            return None
        offset += ir_util.constant_value(field.location.start)
    return whole_end


def _readable_end_if_known(expression, ir):
    """Returns how many units of the structure exist if `expression` is Known.

    A field read is only Known when the field is complete, so a Known
    expression proves that the backing storage extends at least as far as
    the end of the fields it must have read.  `&&` and `||` are Known as soon
    as one operand decides them, so they only prove what both operands prove.
    """
    if _is_constant(expression):
        return 0
    expression = _inline_condition_helpers(expression, ir)
    if expression.which_expression == "field_reference":
        path = expression.field_reference.path
        first = ir_util.find_object(path[0], ir)
        if not isinstance(first, ir_data.Field):
            return 0
        if (
            ir_util.field_is_virtual(first)
            and first.write_method.which_method != "alias"
        ):
            if len(path) != 1:
                return 0
            return _readable_end_if_known(first.read_transform, ir)
        return _reference_end(path, ir) or 0
    if expression.which_expression == "function":
        function = expression.function.function
        args = expression.function.args
        if function in (ir_data.FunctionMapping.AND, ir_data.FunctionMapping.OR):
            return min(_readable_end_if_known(arg, ir) for arg in args)
        if function == ir_data.FunctionMapping.CHOICE:
            condition, if_true, if_false = args
            return max(
                _readable_end_if_known(condition, ir),
                min(
                    _readable_end_if_known(if_true, ir),
                    _readable_end_if_known(if_false, ir),
                ),
            )
        if function in _TOTAL_FUNCTIONS:
            # Known iff every argument is Known.
            return max([_readable_end_if_known(arg, ir) for arg in args] + [0])
    return 0


def _readable_end_if_true(expression, ir):
    """Returns how many units of the structure exist if `expression` is Known-true.

    A Known-true `&&` has both operands Known-true, so it proves what either
    operand proves; a Known-true `||` only proves what both do.
    """
    expression = _inline_condition_helpers(expression, ir)
    if expression.which_expression == "function":
        function = expression.function.function
        args = expression.function.args
        if function == ir_data.FunctionMapping.AND:
            return max(_readable_end_if_true(arg, ir) for arg in args)
        if function == ir_data.FunctionMapping.OR:
            return min(_readable_end_if_true(arg, ir) for arg in args)
        if function == ir_data.FunctionMapping.CHOICE:
            condition, if_true, if_false = args
            return max(
                _readable_end_if_known(condition, ir),
                min(
                    _readable_end_if_true(if_true, ir),
                    _readable_end_if_true(if_false, ir),
                ),
            )
    return _readable_end_if_known(expression, ir)


def _field_value_is_always_ok(field, ir):
    """Returns True if a complete view of `field` is always Ok(), by type alone.

    Unlike `_field_is_always_ok_when_present`, this does not evaluate anything
    in the field's structure, so it can be applied to a field reached through
    a reference into a substructure.
    """
    if ir_util.get_attribute(field.attribute, "requires") is not None:
        return False
    if ir_util.field_is_virtual(field):
        if field.write_method.which_method != "alias":
            return False
        target = ir_util.find_object(field.write_method.alias.path[-1], ir)
        return isinstance(target, ir_data.Field) and _field_value_is_always_ok(
            target, ir
        )
    if not field.type.has_field("atomic_type") or (
        field.type.atomic_type.runtime_parameter
    ):
        return False
    size = ir_util.constant_value(field.location.size)
    if size is None:
        return False
    parent_type = ir_util.find_parent_object(field.name, ir)
    type_def = ir_util.find_object(field.type.atomic_type.reference, ir)
    return _type_is_always_ok_when_complete(
        type_def, size * parent_type.addressable_unit, ir, parameters_known=False
    )


def _expression_is_always_known(expression, ir, point):
    """Returns True if `expression` cannot evaluate to an un-Known() Maybe<>.

    The guarantee is relative to `point`, an `_EvaluationPoint`.  A field is
    considered present when its existence condition is implied by the point's
    guards; a present field reads as Known when the point's fields have been
    validated, or when the field ends within the point's `readable_end` and
    every one of its possible values is Ok().

    Operators other than `$present()` are total on Known operands; `&&`
    additionally only needs its right operand to be Known when its left
    operand is true, since a Known-false left operand already makes the
    result Known.
    """
    if _is_constant(expression):
        return True
    expression = _inline_condition_helpers(expression, ir)
    if expression.which_expression == "field_reference":
        path = expression.field_reference.path
        first = ir_util.find_object(path[0], ir)
        if isinstance(first, ir_data.RuntimeParameter):
            # A view with Ok() backing storage always has its parameters set.
            return True
        if not isinstance(first, ir_data.Field):
            return False
        if not _condition_is_implied(first.existence_condition, point.guards, ir):
            return False
        if (
            ir_util.field_is_virtual(first)
            and first.write_method.which_method != "alias"
        ):
            if len(path) != 1:
                return False
            if point.fields_validated:
                return True
            # The virtual's value is Known iff its definition is.
            return ir_util.get_attribute(
                first.attribute, "requires"
            ) is None and _expression_is_always_known(first.read_transform, ir, point)
        for segment in path[1:]:
            # The existence condition of a field nested inside a substructure
            # is expressed in terms of that substructure's fields, so only
            # unconditional nested fields are provably present.
            nested = ir_util.find_object(segment, ir)
            if not isinstance(nested, ir_data.Field) or not _is_constant_true(
                nested.existence_condition
            ):
                return False
        if point.fields_validated:
            return True
        end = _reference_end(path, ir)
        if end is None or end > point.readable_end:
            return False
        if len(path) == 1:
            return _field_is_always_ok_when_present(first, ir, point)
        last = ir_util.find_object(path[-1], ir)
        return _field_value_is_always_ok(last, ir)
    if expression.which_expression == "function":
        function = expression.function.function
        args = expression.function.args
        if function == ir_data.FunctionMapping.AND:
            left, right = args
            if not _expression_is_always_known(left, ir, point):
                return False
            left_conjuncts = _existence_conjuncts(left, ir)
            if left_conjuncts is None:
                # `false && anything` is Known-false.
                return True
            return _expression_is_always_known(
                right,
                ir,
                point.assuming(ir, left_conjuncts, _readable_end_if_true(left, ir)),
            )
        if function in _TOTAL_FUNCTIONS:
            return all(_expression_is_always_known(arg, ir, point) for arg in args)
        return False
    return False


def _type_is_always_ok_when_complete(type_def, field_bits, ir, parameters_known):
    """Returns True if a `field_bits`-bit view of `type_def` is Ok() when IsComplete().

    This is the case for the prelude's UInt, Int, Flag, and Float types, for
    enums (Emboss enums are open: any value is Ok()), and for structures
    without `[requires]` whose fields are all, recursively, Ok() whenever
    they are present.  Bcd (and any other external type) can reject bit
    patterns, so it never qualifies.
    """
    if type_def.has_field("external"):
        if type_def.name.canonical_name.module_file != "":
            # Not a prelude type; nothing is known about its Ok().
            return False
        name = type_def.name.name.text
        if name in ("UInt", "Int", "Flag"):
            return field_bits is not None and 1 <= field_bits <= 64
        if name == "Float":
            return field_bits in (32, 64)
        return False
    if type_def.has_field("enumeration"):
        maximum_bits = ir_util.get_integer_attribute(type_def.attribute, "maximum_bits")
        return (
            field_bits is not None
            and maximum_bits is not None
            and 1 <= field_bits <= maximum_bits
        )
    if type_def.has_field("structure"):
        if type_def.runtime_parameter and not parameters_known:
            return False
        if ir_util.get_attribute(type_def.attribute, "requires") is not None:
            return False
        fixed_size = ir_util.get_integer_attribute(
            type_def.attribute, "fixed_size_in_bits"
        )
        if fixed_size is None or fixed_size != field_bits:
            return False
        return all(
            _field_ok_check_is_redundant(field, ir)
            for field in type_def.structure.field
        )
    return False


def _field_is_always_ok_when_present(field, ir, point):
    """Returns True if `field.Ok()` cannot be false while `has_field()` is true.

    `point` is the `_EvaluationPoint` at which the field is read; its guards
    should include the field's own existence conjuncts.
    """
    if ir_util.get_attribute(field.attribute, "requires") is not None:
        return False
    if ir_util.field_is_virtual(field):
        # Aliases and other virtual fields are Ok() iff their value is Known.
        return _expression_is_always_known(field.read_transform, ir, point)
    # A physical field at a constant location is in bounds whenever it is
    # present and the structure IsComplete(), because $size_in_bits/bytes
    # includes the end of every present field.  It is then Ok() iff its
    # value is, which depends only on its type.
    constant_offset = ir_util.constant_value(field.location.start)
    constant_size = ir_util.constant_value(field.location.size)
    if (
        constant_offset is None
        or constant_offset < 0
        or constant_size is None
        or constant_size <= 0
    ):
        return False
    parent_type = ir_util.find_parent_object(field.name, ir)
    field_bits = constant_size * parent_type.addressable_unit
    if ir_util.is_array(field.type):
        element_type = field.type.array_type.base_type
        if ir_util.is_array(element_type) or not element_type.has_field("atomic_type"):
            return False
        if element_type.atomic_type.runtime_parameter:
            return False
        element_bits = ir_util.fixed_size_of_type_in_bits(element_type, ir)
        if (
            element_bits is None
            or element_bits <= 0
            or element_bits % parent_type.addressable_unit != 0
            or field_bits % element_bits != 0
        ):
            return False
        element_type_def = ir_util.find_object(element_type.atomic_type.reference, ir)
        return _type_is_always_ok_when_complete(
            element_type_def, element_bits, ir, parameters_known=False
        )
    if not field.type.has_field("atomic_type"):
        return False
    type_def = ir_util.find_object(field.type.atomic_type.reference, ir)
    # If any parameter value is un-Known, the field's view is null, and so
    # not Ok(), even though the field is present.
    parameters_known = all(
        _expression_is_always_known(parameter, ir, point)
        for parameter in field.type.atomic_type.runtime_parameter
    )
    return _type_is_always_ok_when_complete(type_def, field_bits, ir, parameters_known)


def _field_ok_check_is_redundant(field, ir):
    """Returns True if `field`'s check in its structure's Ok() can never fail.

    The per-field check is

        if (!has_field().Known()) return false;
        if (has_field().ValueOrDefault() && !field().Ok()) return false;

    which is a no-op when the existence condition is always Known() and the
    field is Ok() whenever it is present.
    """
    name = field.name.name.text
    if name in ("$size_in_bits", "$size_in_bytes"):
        # IsComplete() already requires the intrinsic size to be Ok().
        return True
    if name in (
        "$max_size_in_bits",
        "$min_size_in_bits",
        "$max_size_in_bytes",
        "$min_size_in_bytes",
    ):
        # Compile-time constants.
        return True
    if field.write_method.which_method == "alias":
        first_target = ir_util.find_object(field.write_method.alias.path[0], ir)
        if isinstance(first_target, ir_data.Field) and first_target.name.is_anonymous:
            # An alias into an anonymous `bits` field has nothing to check of
            # its own: the anonymous field's Ok() checks the aliased field,
            # and the alias's existence condition is Known whenever the
            # anonymous field is Ok().
            return True
    conjuncts = _existence_conjuncts(field.existence_condition, ir)
    if conjuncts is None:
        # The field is never present.
        return True
    return _expression_is_always_known(
        field.existence_condition, ir, _EvaluationPoint()
    ) and _field_is_always_ok_when_present(
        field, ir, _EvaluationPoint().assuming(ir, conjuncts)
    )


def _generate_field_existence_body(field_ir, ir):
    """Returns (statements, expression) for the body of has_${field}().

    The generated body is `${statements}  return ${expression};`.

    A condition with several conjuncts is evaluated one conjunct at a time, so
    that a Known-false conjunct short-circuits the remaining ones (which, in a
    tagged union, typically read fields that are not even present).  The
    result is the same as Emboss's symmetric `&&`: Known-false if any
    conjunct is Known-false, un-Known if any conjunct is un-Known, and
    Known-true otherwise.
    """
    conjuncts = _existence_conjuncts(field_ir.existence_condition, ir)
    if conjuncts is None:
        return "", "::emboss::support::Maybe<bool>(false)"
    if not conjuncts:
        return "", "::emboss::support::Maybe<bool>(true)"
    if len(conjuncts) == 1:
        scope = ExpressionScope("emboss_reserved_local_subexpr_")
        rendered = _render_expression(conjuncts[0], ir, subexpressions=scope).rendered
        return scope.definition_code("  "), rendered
    lines = ["  bool emboss_reserved_local_all_known = true;\n"]
    scope = None
    for index, conjunct in enumerate(conjuncts):
        # Each conjunct's subexpressions are defined just before the conjunct
        # is tested, so that they are only evaluated if no earlier conjunct
        # was Known-false.  Chaining the scopes lets later conjuncts reuse
        # earlier subexpressions.
        scope = ExpressionScope(
            "emboss_reserved_local_subexpr_{}_".format(index), parent=scope
        )
        rendered = _render_expression(conjunct, ir, subexpressions=scope).rendered
        lines.append(scope.definition_code("  "))
        lines.append(
            "  if (!{0}.ValueOr(true)) return ::emboss::support::Maybe<bool>(false);\n"
            "  if (!{0}.Known()) emboss_reserved_local_all_known = false;\n".format(
                rendered
            )
        )
    return (
        "".join(lines),
        "emboss_reserved_local_all_known ? ::emboss::support::Maybe<bool>(true)"
        " : ::emboss::support::Maybe<bool>()",
    )


# A payload (a field to check in Ok(), or a field end in $size_in_*) together
# with the conjuncts of its existence condition which have not been tested
# yet.
_ConditionItem = collections.namedtuple("ConditionItem", ["conjuncts", "payload"])


class _ConditionGroup(object):
    """A set of condition items which share a head conjunct.

    `kind` is "if" when the shared head is an arbitrary boolean expression
    (`guard`), or "switch" when the heads compare the discriminant expression
    `guard` against constants.  `items` are the original items, with all of
    their remaining conjuncts; `entries` (for "if") or `cases` (for "switch")
    hold the same payloads with the head conjunct removed.
    """

    def __init__(self, kind, guard):
        self.kind = kind
        self.guard = guard
        self.items = []
        # The head conjunct of each item, in the same order as `items`.
        self.heads = []
        self.entries = []
        self.cases = {}

    def all_entries(self):
        if self.kind == "if":
            return self.entries
        return [entry for case in self.cases.values() for entry in case.entries]


class _SwitchCase(object):
    """One case label of a "switch" _ConditionGroup."""

    def __init__(self, sort_key):
        self.sort_key = sort_key
        self.entries = []
        # Rendered conjuncts which are Known-true inside this case.
        self.implied = set()


def _group_condition_items(items, ir):
    """Partitions `items` by the conjunct which is most widely shared among them.

    For each item, one of its remaining conjuncts is chosen as the "head";
    items whose heads test the same thing form one group:

      * a "switch" group, when the heads compare one discriminant expression
        against constants (`tag == 1`, `tag == 2 || tag == 3`, ...);
      * an "if" group, when the heads are the same boolean expression.

    The head is chosen to maximize sharing: the conjunct whose group would
    contain the most items wins, with ties going to the earliest conjunct,
    which is usually the outermost condition in the Emboss source.  Groups
    are returned in order of first appearance.
    """
    classified = []
    key_counts = collections.Counter()
    for item in items:
        per_conjunct = []
        keys_in_item = set()
        for conjunct in item.conjuncts:
            discriminant, arms = _extract_switch_arms(conjunct, ir)
            if discriminant is not None:
                key = ("switch", _render_condition_key(discriminant, ir))
                per_conjunct.append((key, discriminant, arms))
            else:
                key = ("if", _render_condition_key(conjunct, ir))
                per_conjunct.append((key, conjunct, None))
            keys_in_item.add(key)
        key_counts.update(keys_in_item)
        classified.append(per_conjunct)

    groups = {}
    for item, per_conjunct in zip(items, classified):
        head_index = max(
            range(len(per_conjunct)),
            key=lambda i: (key_counts[per_conjunct[i][0]], -i),
        )
        key, guard, arms = per_conjunct[head_index]
        head = item.conjuncts[head_index]
        rest = item.conjuncts[:head_index] + item.conjuncts[head_index + 1 :]
        if key not in groups:
            groups[key] = _ConditionGroup(key[0], guard)
        group = groups[key]
        group.items.append(item)
        group.heads.append(head)
        if group.kind == "if":
            group.entries.append(_ConditionItem(rest, item.payload))
            continue
        # Inside `case K`, the head reduces to the `||` of the residuals of the
        # arms with case value K (every other arm is Known-false).
        arms_by_label = {}
        for case_value, residual in arms:
            label = _render_case_label(case_value, ir)
            if label not in group.cases:
                group.cases[label] = _SwitchCase(_case_sort_key(case_value))
            arms_by_label.setdefault(label, []).append((case_value, residual))
        for label, case_arms in arms_by_label.items():
            case = group.cases[label]
            residuals = [residual for _, residual in case_arms]
            if any(not residual for residual in residuals):
                remaining = []
                # Both the head conjunct and `discriminant == case_value` are
                # Known-true inside this case.
                case.implied.add(_render_condition_key(head, ir))
                case.implied.add(
                    _render_condition_key(
                        _boolean_function_expression(
                            ir_data.FunctionMapping.EQUALITY,
                            [guard, case_arms[0][0]],
                        ),
                        ir,
                    )
                )
            elif len(residuals) == 1:
                remaining = residuals[0]
            else:
                remaining = [
                    _or_expression(
                        [_and_expression(residual) for residual in residuals]
                    )
                ]
            case.entries.append(_ConditionItem(remaining + rest, item.payload))
    return list(groups.values())


class _ConditionTree(object):
    """Renders nested `if`/`switch` statements which test existence conditions.

    Given items tagged with the conjuncts of their existence conditions, the
    tree groups the items by shared conjuncts (see `_group_condition_items`)
    and emits one test per group, recursing into each group with the items'
    remaining conjuncts.  A payload is "reached" when all of its conjuncts
    have tested true.

    The generated code must agree with the straightforward evaluation of each
    payload's full condition using Maybe<bool> semantics, in which an
    un-Known conjunct does *not* necessarily make the condition un-Known:
    `unknown && false` is Known-false.  Testing one conjunct at a time is
    therefore only equivalent when, for each group,

      (1) the guard is provably Known (`_expression_is_always_known`), so
          that there is nothing to check; or
      (2) some item's condition is exactly the guard, so that an un-Known
          guard makes that item's whole condition un-Known, which is where
          the straightforward evaluation would also give up.

    Otherwise the tree falls back to testing each item's full remaining
    condition as a single expression.

    Each level of the tree is rendered relative to an `_EvaluationPoint`,
    which records what the enclosing tests have established (which conjuncts
    are Known-true, and how much of the backing storage is known to exist);
    this is what lets nested guards be recognized as provably Known.

    Subclasses define `unknown_statement`, which aborts the enclosing method
    when a condition turns out to be un-Known, `field_reader`, and
    `render_payloads()`.  `context` is an opaque value threaded from parents
    to children; `render_payloads()` may replace it for its siblings.
    """

    unknown_statement = None
    field_reader = None

    def __init__(self, ir):
        self.ir = ir

    def render_payloads(self, payloads, indent, scope, context):
        """Returns (statements, context) for payloads whose conditions hold."""
        raise NotImplementedError()

    def render_shortcut(self, entry, depth):
        """Returns statements for a lone, un-Known-able item, or None.

        Called before the generic rendering of a single-item group with no
        remaining conjuncts; the Ok() tree uses it to reuse has_${field}().
        """
        del entry, depth  # Unused by default.
        return None

    def render(self, items, point, scope, depth, indent, context):
        """Renders `items`; subexpressions are defined in `scope`."""
        immediate = [item.payload for item in items if not item.conjuncts]
        conditional = [item for item in items if item.conjuncts]
        statements, context = self.render_payloads(immediate, indent, scope, context)
        parts = [statements]
        for group in _group_condition_items(conditional, self.ir):
            parts.append(
                self._render_group(group, point, scope, depth, indent, context)
            )
        return "".join(parts)

    def _render_group(self, group, point, scope, depth, indent, context):
        guard_is_known = _expression_is_always_known(group.guard, self.ir, point)
        has_bare_item = any(not entry.conjuncts for entry in group.all_entries())
        if not guard_is_known and not has_bare_item:
            # Neither (1) nor (2) above holds; test each item's remaining
            # condition as one expression, for which (2) holds trivially.
            return "".join(
                self._render_if(
                    _and_expression(item.conjuncts),
                    [_ConditionItem([], item.payload)],
                    False,
                    point,
                    scope,
                    depth,
                    indent,
                    context,
                )
                for item in group.items
            )
        if group.kind == "if":
            return self._render_if(
                group.guard,
                group.entries,
                guard_is_known,
                point,
                scope,
                depth,
                indent,
                context,
            )
        if len(group.items) == 1 and len(group.cases) == 1:
            # A one-armed switch costs more than the equivalent `if`.  The
            # head may carry residual conjuncts (`tag == 1 && a`), so whether
            # it is Known is not the same question as for the discriminant.
            head = group.heads[0]
            return self._render_if(
                head,
                group.all_entries(),
                _expression_is_always_known(head, self.ir, point),
                point,
                scope,
                depth,
                indent,
                context,
            )
        return self._render_switch(
            group, guard_is_known, point, scope, depth, indent, context
        )

    def _render_if(
        self,
        condition,
        entries,
        condition_is_known,
        point,
        scope,
        depth,
        indent,
        context,
    ):
        if not condition_is_known and len(entries) == 1 and not entries[0].conjuncts:
            shortcut = self.render_shortcut(entries[0], depth)
            if shortcut is not None:
                return shortcut
        mark = scope.mark()
        rendered = _render_expression(
            condition, self.ir, self.field_reader, subexpressions=scope
        ).rendered
        inner_scope = scope.child()
        # Inside the `if`, the condition is Known-true.
        inner_point = point.assuming(
            self.ir, [condition], _readable_end_if_true(condition, self.ir)
        )
        body = self.render(
            entries, inner_point, inner_scope, depth + 1, indent + "  ", context
        )
        if condition_is_known and not body:
            # Nothing to test after all; drop the condition's subexpressions.
            scope.discard_since(mark)
            return ""
        lines = []
        if not condition_is_known:
            lines.append(
                "{}if (!{}.Known()) {}\n".format(
                    indent, rendered, self.unknown_statement
                )
            )
        if body:
            lines.append("{}if ({}.ValueOrDefault()) {{\n".format(indent, rendered))
            lines.append(inner_scope.definition_code(indent + "  "))
            lines.append(body)
            lines.append("{}}}\n".format(indent))
        return "".join(lines)

    def _render_switch(
        self, group, discriminant_is_known, point, scope, depth, indent, context
    ):
        mark = scope.mark()
        rendered = _render_expression(
            group.guard, self.ir, self.field_reader, subexpressions=scope
        ).rendered
        # Inside the switch, the discriminant is Known.
        switch_point = point.assuming(
            self.ir, readable_end=_readable_end_if_known(group.guard, self.ir)
        )
        bodies = {}
        for label, case in group.cases.items():
            inner_scope = scope.child()
            body = self.render(
                case.entries,
                switch_point.with_guards(case.implied),
                inner_scope,
                depth + 1,
                indent + "    ",
                context,
            )
            if not body:
                # Nothing to do for this case; let it fall to `default`.
                continue
            body = inner_scope.definition_code(indent + "    ") + body
            bodies.setdefault(body, []).append((case.sort_key, label))
        if discriminant_is_known and not bodies:
            # Nothing to test after all; drop the discriminant's subexpressions.
            scope.discard_since(mark)
            return ""
        lines = []
        if not discriminant_is_known:
            lines.append(
                "{}if (!{}.Known()) {}\n".format(
                    indent, rendered, self.unknown_statement
                )
            )
        if not bodies:
            return "".join(lines)
        # Sort case labels numerically, so that compilers are more likely to
        # emit a jump table, and merge cases with identical bodies.
        arms = sorted((sorted(labels), body) for body, labels in bodies.items())
        lines.append("{}switch ({}.ValueOrDefault()) {{\n".format(indent, rendered))
        for labels, body in arms:
            lines.extend("{}  case {}:\n".format(indent, label) for _, label in labels)
            lines.append("{}  {{\n".format(indent))
            lines.append(body)
            lines.append("{}    break;\n".format(indent))
            lines.append("{}  }}\n".format(indent))
        lines.append("{}  default:\n".format(indent))
        lines.append("{}    break;\n".format(indent))
        lines.append("{}}}\n".format(indent))
        return "".join(lines)


_OkCheck = collections.namedtuple("OkCheck", ["field_name", "needs_ok_check"])


class _OkConditionTree(_ConditionTree):
    """Condition tree for the field checks in a structure's Ok() method.

    Payloads are `_OkCheck`s.  When a check is reached, the field is present,
    so the check reduces to `field().Ok()`; fields which are Ok() whenever
    they are present only participate to get their existence conditions
    tested.
    """

    unknown_statement = "return false;"
    field_reader = _DirectFieldRenderer()

    def __init__(self, ir):
        super(_OkConditionTree, self).__init__(ir)

    def render_payloads(self, payloads, indent, scope, context):
        del scope  # Unused.
        return (
            "".join(
                "{}if (!{}().Ok()) return false;\n".format(indent, check.field_name)
                for check in payloads
                if check.needs_ok_check
            ),
            context,
        )

    def render_shortcut(self, entry, depth):
        if depth != 0:
            return None
        # At the top level, an item's full condition is has_${field}(), which
        # is already generated; reuse it instead of re-rendering the condition.
        if entry.payload.needs_ok_check:
            template = _TEMPLATES.ok_method_test
        else:
            template = _TEMPLATES.ok_method_known_test
        return code_template.format_template(template, field=entry.payload.field_name)


def _generate_optimized_ok_method_body(fields, ir, subexpressions):
    """Generates the per-field checks of a structure's Ok() method.

    For example, given this Emboss definition:

        struct Foo:
          0 [+4]  UInt  tag
          if tag == 0:
            4 [+4]  UInt  var_0
          if tag == 1:
            4 [+4]  UInt  var_1
          if tag == 1 && var_1 == 3:
            8 [+4]  Bar   var_x

    instead of a test per field:

        if (!has_var_0().Known()) return false;
        if (has_var_0().ValueOrDefault() && !var_0().Ok()) return false;
        ...

    this generates nested tests which read `tag` once:

        switch (emboss_reserved_local_ok_subexpr_1.ValueOrDefault()) {
          case 0:
          ...
          case 1:
          {
            if (emboss_reserved_local_ok_subexpr_1_2.ValueOrDefault()) {
              if (!var_x().Ok()) return false;
            }
            break;
          }
          default:
            break;
        }

    with `tag == 0` and `tag == 1` sharing one read of `tag` (defined in
    `subexpressions`), and the `UInt` fields' own `Ok()` checks elided,
    since a `UInt` which is in bounds is always Ok().  `var_x`'s check is
    nested inside the `case 1` arm, where `var_1` is already known to be
    present.

    Arguments:
        fields: The structure's fields, in dependency order.
        ir: The full IR.
        subexpressions: The ExpressionScope for Ok()'s top-level
            subexpressions.

    Returns:
        A string containing the C++ code for the field checks.
    """
    items = []
    for field in fields:
        if _field_ok_check_is_redundant(field, ir):
            continue
        conjuncts = _existence_conjuncts(field.existence_condition, ir)
        if conjuncts is None:
            continue
        needs_ok_check = not _field_is_always_ok_when_present(
            field, ir, _EvaluationPoint().assuming(ir, conjuncts)
        )
        items.append(
            _ConditionItem(
                conjuncts,
                _OkCheck(_cpp_field_name(field.name.name.text), needs_ok_check),
            )
        )
    return _OkConditionTree(ir).render(
        items, _EvaluationPoint(), subexpressions, depth=0, indent="    ", context=None
    )


class _SizeConditionTree(_ConditionTree):
    """Condition tree for the body of $size_in_bits/$size_in_bytes.

    Payloads are IR expressions for the ends of fields; the generated code
    folds them into `emboss_reserved_local_size`.  `context` is the largest
    constant end already folded in on the current path, so that smaller
    constants nested below it can be skipped.
    """

    field_reader = _VirtualViewFieldRenderer()

    def __init__(self, ir, logical_type, intermediate_type):
        super(_SizeConditionTree, self).__init__(ir)
        self.unknown_statement = "return ::emboss::support::Maybe</**/ {}>();".format(
            logical_type
        )
        self.intermediate_type = intermediate_type

    def render_payloads(self, payloads, indent, scope, context):
        lines = []
        constant_floor = context
        dynamic_ends = []
        for end in payloads:
            if _is_constant(end):
                constant_floor = max(
                    constant_floor, int(end.type.integer.modular_value)
                )
            else:
                dynamic_ends.append(end)
        if constant_floor > context:
            rendered = _render_integer(constant_floor)
            lines.append(
                "{0}if (emboss_reserved_local_size < {1}) emboss_reserved_local_size = {1};\n".format(
                    indent, rendered
                )
            )
        for end in dynamic_ends:
            rendered = _render_expression(
                end, self.ir, self.field_reader, subexpressions=scope
            ).rendered
            lines.append(
                "{0}if (!{1}.Known()) {2}\n"
                "{0}if (static_cast</**/ {3}>({1}.ValueOrDefault()) >\n"
                "{0}    emboss_reserved_local_size) {{\n"
                "{0}  emboss_reserved_local_size =\n"
                "{0}      static_cast</**/ {3}>({1}.ValueOrDefault());\n"
                "{0}}}\n".format(
                    indent, rendered, self.unknown_statement, self.intermediate_type
                )
            )
        return "".join(lines), constant_floor


def _generate_optimized_size_read(field_ir, logical_type, ir):
    """Generates (read_subexpressions, read_value) for a $size_in_* field.

    The front end defines the size of a structure as

        $max(0, cond_1 ? end_1 : 0, cond_2 ? end_2 : 0, ...)

    with one clause per physical field.  Evaluating that expression directly
    evaluates every field's existence condition, even though most of the
    conditions in a tagged union are mutually exclusive, and then folds all
    of the clauses with Maybe<> arithmetic.  This instead generates a
    condition tree (see `_SizeConditionTree`) which evaluates shared
    conditions once and folds the ends into a plain integer, with the same
    result as the original expression: un-Known if any evaluated condition
    or end is un-Known, otherwise the maximum.
    """
    size_expression = field_ir.read_transform
    if (
        size_expression.which_expression != "function"
        or size_expression.function.function != ir_data.FunctionMapping.MAXIMUM
    ):
        scope = ExpressionScope("emboss_reserved_local_subexpr_")
        read_value = _render_expression(
            size_expression,
            ir,
            field_reader=_VirtualViewFieldRenderer(),
            subexpressions=scope,
        )
        return scope.definition_code("      "), read_value.rendered

    # Mirror _render_builtin_operation()'s choice of intermediate type, so that
    # the comparisons below are performed in the same C++ type as $max()'s.
    minimum_integers = []
    maximum_integers = []
    for expression in [size_expression] + list(size_expression.function.args):
        assert expression.type.which_type == "integer"
        minimum_integers.append(int(expression.type.integer.minimum_value))
        maximum_integers.append(int(expression.type.integer.maximum_value))
    intermediate_type = _cpp_integer_type_for_range(
        min(minimum_integers), max(maximum_integers)
    )

    constant_floor = 0
    items = []
    for arg in size_expression.function.args:
        if (
            arg.which_expression == "function"
            and arg.function.function == ir_data.FunctionMapping.CHOICE
            and _is_constant(arg.function.args[2])
            and int(arg.function.args[2].type.integer.modular_value) == 0
        ):
            conjuncts = _existence_conjuncts(arg.function.args[0], ir)
            if conjuncts is None:
                # The field is never present.
                continue
            ends = _flatten_function(
                arg.function.args[1], ir_data.FunctionMapping.MAXIMUM
            )
        else:
            conjuncts = []
            ends = _flatten_function(arg, ir_data.FunctionMapping.MAXIMUM)
        for end in ends:
            if not conjuncts and _is_constant(end):
                constant_floor = max(
                    constant_floor, int(end.type.integer.modular_value)
                )
            else:
                items.append(_ConditionItem(conjuncts, end))

    scope = ExpressionScope("emboss_reserved_local_subexpr_")
    tree = _SizeConditionTree(ir, logical_type, intermediate_type).render(
        items,
        _EvaluationPoint(fields_validated=False),
        scope,
        depth=0,
        indent="      ",
        context=constant_floor,
    )
    read_subexpressions = (
        scope.definition_code("      ")
        + "      {} emboss_reserved_local_size = {};\n".format(
            intermediate_type, _render_integer(constant_floor)
        )
        + tree
    )
    read_value = "::emboss::support::Maybe</**/ {0}>(static_cast</**/ {0}>(emboss_reserved_local_size))".format(
        logical_type
    )
    return read_subexpressions, read_value


def _bitwise_compared_location(field, ir):
    """Returns the (start, end) of `field` if its Equals() is a bitwise comparison.

    Two views of an always-present `UInt`, `Int`, `Flag`, or `enum` field
    without `[requires]` at a constant location are Equals() exactly when the
    bits they occupy are equal.  When several such fields overlay the same
    bits (for example a 48-bit field which is also exposed as 16-bit and
    32-bit halves), comparing the largest one compares all of them, and the
    structure's Equals() can skip the others.

    Returns None for every other kind of field.
    """
    if ir_util.field_is_virtual(field):
        return None
    if not _is_constant_true(field.existence_condition):
        return None
    if ir_util.get_attribute(field.attribute, "requires") is not None:
        return None
    if (
        not field.type.has_field("atomic_type")
        or field.type.atomic_type.runtime_parameter
    ):
        return None
    start = ir_util.constant_value(field.location.start)
    size = ir_util.constant_value(field.location.size)
    if start is None or start < 0 or size is None or size <= 0:
        return None
    type_def = ir_util.find_object(field.type.atomic_type.reference, ir)
    if type_def.has_field("external"):
        if type_def.name.canonical_name.module_file != "" or (
            type_def.name.name.text not in ("UInt", "Int", "Flag")
        ):
            return None
    elif not type_def.has_field("enumeration"):
        return None
    return (start, start + size)


def _generate_structure_definition(type_ir, ir, config: Config):
    """Generates C++ for an Emboss structure (struct or bits).

    Arguments:
      type_ir: The IR for the struct definition.
      ir: The full IR; used for type lookups.
      config: The code generation configuration to use.

    Returns:
      A tuple of: (forward declaration for classes, class bodies, method
      bodies), suitable for insertion into the appropriate places in the
      generated header.
    """
    subtype_bodies, subtype_forward_declarations, subtype_method_definitions = (
        _generate_subtype_definitions(type_ir, ir, config)
    )
    type_name = type_ir.name.name.text
    field_helper_type_definitions = []
    field_method_declarations = []
    field_method_definitions = []
    virtual_field_type_definitions = []
    decode_field_clauses = []
    write_field_clauses = []

    equals_method_clauses = []
    unchecked_equals_method_clauses = []
    enum_using_statements = []
    parameter_fields = []
    constructor_parameters = []
    forwarded_parameters = []
    parameter_initializers = []
    parameter_copy_initializers = []
    units = {1: "Bits", 8: "Bytes"}[type_ir.addressable_unit]

    for subtype in type_ir.subtype:
        if subtype.has_field("enumeration"):
            enum_using_statements.append(
                code_template.format_template(
                    _TEMPLATES.enum_using_statement,
                    component=_get_fully_qualified_name(
                        subtype.name.canonical_name, ir
                    ),
                    name=_get_unqualified_name(subtype.name.canonical_name),
                )
            )

    # TODO(bolms): Reorder parameter fields to optimize packing in the view type.
    for parameter in type_ir.runtime_parameter:
        parameter_type = _cpp_basic_type_for_expression_type(parameter.type, ir)
        parameter_name = parameter.name.name.text
        parameter_fields.append("{} {}_;".format(parameter_type, parameter_name))
        constructor_parameters.append("{} {}, ".format(parameter_type, parameter_name))
        forwarded_parameters.append(
            "::std::forward</**/{}>({}),".format(parameter_type, parameter_name)
        )
        parameter_initializers.append(", {0}_({0})".format(parameter_name))
        parameter_copy_initializers.append(
            ", {0}_(emboss_reserved_local_other.{0}_)".format(parameter_name)
        )

        field_method_declarations.append(
            code_template.format_template(
                _TEMPLATES.structure_single_parameter_field_method_declarations,
                name=parameter_name,
                logical_type=parameter_type,
            )
        )
        # TODO(bolms): Should parameters appear in text format?
        equals_method_clauses.append(
            code_template.format_template(
                _TEMPLATES.equals_method_test, field=parameter_name + "()"
            )
        )
        unchecked_equals_method_clauses.append(
            code_template.format_template(
                _TEMPLATES.unchecked_equals_method_test, field=parameter_name + "()"
            )
        )
    if type_ir.runtime_parameter:
        flag_name = "parameters_initialized_"
        parameter_copy_initializers.append(
            ", {0}(emboss_reserved_local_other.{0})".format(flag_name)
        )
        parameters_initialized_flag = "bool {} = false;".format(flag_name)
        initialize_parameters_initialized_true = ", {}(true)".format(flag_name)
        parameter_checks = ["if (!{}) return false;".format(flag_name)]
    else:
        parameters_initialized_flag = ""
        initialize_parameters_initialized_true = ""
        parameter_checks = [""]

    # Generate code using subexpression store.
    ok_subexpressions = ExpressionScope("emboss_reserved_local_ok_subexpr_")
    bitwise_compared_locations = []
    for field_index in type_ir.structure.fields_in_dependency_order:
        field = type_ir.structure.field[field_index]
        helper_types, declaration, definition = _generate_structure_field_methods(
            type_name, field, ir, type_ir.addressable_unit
        )
        field_helper_type_definitions.append(helper_types)
        field_method_definitions.append(definition)
        if not ir_util.field_is_virtual(field):
            # Virtual fields do not participate in equality tests -- they are equal by
            # definition.
            location = _bitwise_compared_location(field, ir)
            if location is not None and any(
                start <= location[0] and location[1] <= end
                for start, end in bitwise_compared_locations
            ):
                # An earlier field's Equals() already compares these bits.
                pass
            elif _is_constant_true(field.existence_condition):
                equals_method_clauses.append(
                    code_template.format_template(
                        _TEMPLATES.unconditional_equals_method_test,
                        field=field.name.name.text + "()",
                    )
                )
                unchecked_equals_method_clauses.append(
                    code_template.format_template(
                        _TEMPLATES.unconditional_unchecked_equals_method_test,
                        field=field.name.name.text + "()",
                    )
                )
            else:
                equals_method_clauses.append(
                    code_template.format_template(
                        _TEMPLATES.equals_method_test,
                        field=field.name.name.text + "()",
                    )
                )
                unchecked_equals_method_clauses.append(
                    code_template.format_template(
                        _TEMPLATES.unchecked_equals_method_test,
                        field=field.name.name.text + "()",
                    )
                )
            if location is not None:
                bitwise_compared_locations.append(location)
        field_method_declarations.append(declaration)
        if not field.name.is_anonymous and not ir_util.field_is_read_only(field):
            # As above, read-only fields cannot be decoded from text format.
            decode_field_clauses.append(
                code_template.format_template(
                    _TEMPLATES.decode_field,
                    field_name=field.name.canonical_name.object_path[-1],
                )
            )
        text_output_attr = ir_util.get_attribute(field.attribute, "text_output")
        if not text_output_attr or text_output_attr.string_constant == "Emit":
            if ir_util.field_is_read_only(field):
                write_field_template = _TEMPLATES.write_read_only_field_to_text_stream
            else:
                write_field_template = _TEMPLATES.write_field_to_text_stream
            write_field_clauses.append(
                code_template.format_template(
                    write_field_template,
                    field_name=field.name.canonical_name.object_path[-1],
                )
            )

    requires_attr = ir_util.get_attribute(type_ir.attribute, "requires")
    if requires_attr is not None:
        requires_clause = _render_expression(
            requires_attr.expression, ir, _DirectFieldRenderer()
        ).rendered
        requires_check = (
            "    if (!({}).ValueOr(false))\n" "      return false;"
        ).format(requires_clause)
    else:
        requires_check = ""

    if config.include_enum_traits:
        text_stream_methods = code_template.format_template(
            _TEMPLATES.struct_text_stream,
            decode_fields="\n".join(decode_field_clauses),
            write_fields="\n".join(write_field_clauses),
        )
    else:
        text_stream_methods = ""

    field_ok_checks_body = _generate_optimized_ok_method_body(
        [
            type_ir.structure.field[i]
            for i in type_ir.structure.fields_in_dependency_order
        ],
        ir,
        ok_subexpressions,
    )

    class_forward_declarations = code_template.format_template(
        _TEMPLATES.structure_view_declaration, name=type_name
    )
    class_bodies = code_template.format_template(
        _TEMPLATES.structure_view_class,
        name=type_ir.name.canonical_name.object_path[-1],
        size_method=_render_size_method(type_ir.structure.field, ir),
        field_method_declarations="".join(field_method_declarations),
        field_ok_checks=field_ok_checks_body,
        ok_subexpressions=ok_subexpressions.definition_code(),
        parameter_ok_checks="\n".join(parameter_checks),
        requires_check=requires_check,
        equals_method_body="\n".join(equals_method_clauses),
        unchecked_equals_method_body="\n".join(unchecked_equals_method_clauses),
        enum_usings="\n".join(enum_using_statements),
        text_stream_methods=text_stream_methods,
        parameter_fields="\n".join(parameter_fields),
        constructor_parameters="".join(constructor_parameters),
        forwarded_parameters="".join(forwarded_parameters),
        parameter_initializers="\n".join(parameter_initializers),
        parameter_copy_initializers="\n".join(parameter_copy_initializers),
        parameters_initialized_flag=parameters_initialized_flag,
        initialize_parameters_initialized_true=(initialize_parameters_initialized_true),
        units=units,
    )
    method_definitions = "\n".join(field_method_definitions)
    early_virtual_field_types = "\n".join(virtual_field_type_definitions)
    all_field_helper_type_definitions = "\n".join(field_helper_type_definitions)
    return (
        early_virtual_field_types
        + subtype_forward_declarations
        + class_forward_declarations,
        all_field_helper_type_definitions + subtype_bodies + class_bodies,
        subtype_method_definitions + method_definitions,
    )


def _split_enum_case_values_into_spans(enum_case_value):
    """Yields spans containing each enum case in an enum_case attribute value.

    Arguments:
        enum_case_value: the value of the `enum_case` attribute to be parsed.

    Returns:
        An iterator over spans, where each span covers one enum case name.
        Each span is a half-open range of the form [start, end), which is the
        start and end position relative to the beginning of the enum_case_value
        string.  The name can be retrieved with `enum_case_value[start:end]`.

        To keep the grammar of this attribute simple, this only splits on
        delimiters and trims whitespace for each case.

    Example: 'SHOUTY_CASE, kCamelCase' -> [(0, 11), (13, 23)]"""
    # Scan the string from left to right, finding commas and trimming whitespace.
    # This is essentially equivalent to (x.trim() fror x in str.split(','))
    # except that this yields spans within the string rather than the strings
    # themselves, and no span is yielded for a trailing comma.
    start, end = 0, len(enum_case_value)
    while start <= end:
        # Find a ',' delimiter to split on
        delimiter = enum_case_value.find(",", start, end)
        if delimiter < 0:
            delimiter = end

        substr_start = start
        substr_end = delimiter

        # Drop leading whitespace
        while substr_start < substr_end and enum_case_value[substr_start].isspace():
            substr_start += 1
        # Drop trailing whitespace
        while substr_start < substr_end and enum_case_value[substr_end - 1].isspace():
            substr_end -= 1

        # Skip a trailing comma
        if substr_start == end and start != 0:
            break

        yield substr_start, substr_end
        start = delimiter + 1


def _split_enum_case_values(enum_case_value):
    """Returns all enum cases in an enum case value.

    Arguments:
        enum_case_value: the value of the enum case attribute to parse.

    Returns:
        All enum case names from `enum_case_value`.

    Example: 'SHOUTY_CASE, kCamelCase' -> ['SHOUTY_CASE', 'kCamelCase']"""
    return [
        enum_case_value[start:end]
        for start, end in _split_enum_case_values_into_spans(enum_case_value)
    ]


def _get_enum_value_names(enum_value):
    """Determines one or more enum names based on attributes."""
    cases = ["SHOUTY_CASE"]
    name = enum_value.name.name.text
    if enum_case := ir_util.get_attribute(
        enum_value.attribute, attributes.Attribute.ENUM_CASE
    ):
        cases = _split_enum_case_values(enum_case.string_constant.text)
    return [name_conversion.convert_case("SHOUTY_CASE", case, name) for case in cases]


def _generate_enum_definition(type_ir, include_traits=True):
    """Generates C++ for an Emboss enum."""
    enum_values = []
    enum_from_string_statements = []
    string_from_enum_statements = []
    enum_is_known_statements = []
    previously_seen_numeric_values = set()
    max_bits = ir_util.get_integer_attribute(type_ir.attribute, "maximum_bits")
    is_signed = ir_util.get_boolean_attribute(type_ir.attribute, "is_signed")
    enum_type = _cpp_integer_type_for_enum(max_bits, is_signed)
    for value in type_ir.enumeration.value:
        numeric_value = ir_util.constant_value(value.value)
        enum_value_names = _get_enum_value_names(value)

        for enum_value_name in enum_value_names:
            enum_values.append(
                code_template.format_template(
                    _TEMPLATES.enum_value,
                    name=enum_value_name,
                    value=_render_integer(numeric_value),
                )
            )
            if include_traits:
                enum_from_string_statements.append(
                    code_template.format_template(
                        _TEMPLATES.enum_from_name_case,
                        enum=type_ir.name.name.text,
                        value=enum_value_name,
                        name=value.name.name.text,
                    )
                )

                if numeric_value not in previously_seen_numeric_values:
                    string_from_enum_statements.append(
                        code_template.format_template(
                            _TEMPLATES.name_from_enum_case,
                            enum=type_ir.name.name.text,
                            value=enum_value_name,
                            name=value.name.name.text,
                        )
                    )

                    enum_is_known_statements.append(
                        code_template.format_template(
                            _TEMPLATES.enum_is_known_case,
                            enum=type_ir.name.name.text,
                            name=enum_value_name,
                        )
                    )
            previously_seen_numeric_values.add(numeric_value)

    declaration = code_template.format_template(
        _TEMPLATES.enum_declaration, enum=type_ir.name.name.text, enum_type=enum_type
    )
    definition = code_template.format_template(
        _TEMPLATES.enum_definition,
        enum=type_ir.name.name.text,
        enum_type=enum_type,
        enum_values="".join(enum_values),
    )
    if include_traits:
        definition += code_template.format_template(
            _TEMPLATES.enum_traits,
            enum=type_ir.name.name.text,
            enum_from_name_cases="\n".join(enum_from_string_statements),
            name_from_enum_cases="\n".join(string_from_enum_statements),
            enum_is_known_cases="\n".join(enum_is_known_statements),
        )

    return (declaration, definition, "")


def _generate_type_definition(type_ir, ir, config: Config):
    """Generates C++ for an Emboss type."""
    if type_ir.has_field("structure"):
        return _generate_structure_definition(type_ir, ir, config)
    elif type_ir.has_field("enumeration"):
        return _generate_enum_definition(type_ir, config.include_enum_traits)
    elif type_ir.has_field("external"):
        # TODO(bolms): This should probably generate an #include.
        return "", "", ""
    else:
        # TODO(bolms): provide error message instead of ICE
        assert False, "Unknown type {}".format(type_ir)


def _generate_header_guard(file_path):
    # TODO(bolms): Make this configurable.
    header_path = file_path + ".h"
    uppercased_path = header_path.upper()
    no_punctuation_path = re.sub(r"[^A-Za-z0-9_]", "_", uppercased_path)
    suffixed_path = no_punctuation_path + "_"
    no_double_underscore_path = re.sub(r"__+", "_", suffixed_path)
    return no_double_underscore_path


def _add_missing_enum_case_attribute_on_enum_value(enum_value, defaults):
    """Adds an `enum_case` attribute if there isn't one but a default is set."""
    if (
        ir_util.get_attribute(enum_value.attribute, attributes.Attribute.ENUM_CASE)
        is None
    ):
        if attributes.Attribute.ENUM_CASE in defaults:
            enum_value.attribute.extend([defaults[attributes.Attribute.ENUM_CASE]])


def _propagate_defaults(ir, targets, ancestors, add_fn):
    """Propagates default values

    Traverses the IR to propagate default values to target nodes.

    Arguments:
        ir: The IR to process.
        targets: A list of target IR types to add attributes to.
        ancestors: Ancestor types which may contain the default values.
        add_fn: Function to add the attribute. May use any parameter available
            in fast_traverse_ir_top_down actions as well as `defaults`
            containing the
            default attributes set by ancestors.

    Returns:
        None
    """
    traverse_ir.fast_traverse_ir_top_down(
        ir,
        targets,
        add_fn,
        incidental_actions={
            ancestor: attribute_util.gather_default_attributes for ancestor in ancestors
        },
        parameters={"defaults": {}},
    )


def _offset_source_location_column(source_location, offset):
    """Adds offsets from the start column of the supplied source location.

    Arguments:
        source_location: the initial source location
        offset: a tuple of (start, end), which are the offsets relative to
            source_location.start.column to set the new start.column and
            end.column.

    Returns:
        A new source location with all of the same properties as the provided
        source location, but with the columns modified by offsets from the
        original start column.
    """

    new_location = source_location._replace(
        start=source_location.start._replace(
            column=source_location.start.column + offset[0]
        ),
        end=source_location.start._replace(
            column=source_location.start.column + offset[1]
        ),
    )

    return new_location


def _verify_namespace_attribute(attr, source_file_name, errors):
    if attr.name.text != attributes.Attribute.NAMESPACE:
        return
    namespace_value = ir_data_utils.reader(attr).value.string_constant
    if not re.fullmatch(_NS_RE, namespace_value.text):
        if re.fullmatch(_NS_EMPTY_RE, namespace_value.text):
            errors.append(
                [
                    error.error(
                        source_file_name,
                        namespace_value.source_location,
                        "Empty namespace value is not allowed.",
                    )
                ]
            )
        elif re.fullmatch(_NS_GLOBAL_RE, namespace_value.text):
            errors.append(
                [
                    error.error(
                        source_file_name,
                        namespace_value.source_location,
                        "Global namespace is not allowed.",
                    )
                ]
            )
        else:
            errors.append(
                [
                    error.error(
                        source_file_name,
                        namespace_value.source_location,
                        'Invalid namespace, must be a valid C++ namespace, such as "abc", '
                        '"abc::def", or "::abc::def::ghi" (ISO/IEC 14882:2017 '
                        "enclosing-namespace-specifier).",
                    )
                ]
            )
        return
    for word in _get_namespace_components(namespace_value.text):
        if word in _CPP_RESERVED_WORDS:
            errors.append(
                [
                    error.error(
                        source_file_name,
                        namespace_value.source_location,
                        f'Reserved word "{word}" is not allowed as a namespace component.',
                    )
                ]
            )


_VALID_CASES = ", ".join(case for case in _SUPPORTED_ENUM_CASES)


def _verify_enum_case_attribute(attr, source_file_name, errors):
    """Verify that `enum_case` values are supported."""
    if attr.name.text != attributes.Attribute.ENUM_CASE:
        return

    enum_case_value = attr.value.string_constant
    case_spans = _split_enum_case_values_into_spans(enum_case_value.text)
    seen_cases = set()

    for start, end in case_spans:
        case_source_location = _offset_source_location_column(
            enum_case_value.source_location, (start, end)
        )
        case = enum_case_value.text[start:end]

        if start == end:
            errors.append(
                [
                    error.error(
                        source_file_name,
                        case_source_location,
                        "Empty enum case (or excess comma).",
                    )
                ]
            )
            continue

        if case in seen_cases:
            errors.append(
                [
                    error.error(
                        source_file_name,
                        case_source_location,
                        f'Duplicate enum case "{case}".',
                    )
                ]
            )
            continue
        seen_cases.add(case)

        if case not in _SUPPORTED_ENUM_CASES:
            errors.append(
                [
                    error.error(
                        source_file_name,
                        case_source_location,
                        f'Unsupported enum case "{case}", '
                        f"supported cases are: {_VALID_CASES}.",
                    )
                ]
            )


def _verify_attribute_values(ir):
    """Verify backend attribute values."""
    errors = []

    traverse_ir.fast_traverse_ir_top_down(
        ir,
        [ir_data.Attribute],
        _verify_namespace_attribute,
        parameters={"errors": errors},
    )
    traverse_ir.fast_traverse_ir_top_down(
        ir,
        [ir_data.Attribute],
        _verify_enum_case_attribute,
        parameters={"errors": errors},
    )

    return errors


def _propagate_defaults_and_verify_attributes(ir):
    """Verify attributes and ensure defaults are set when not overridden.

    Arguments:
        ir: The IR to process.

    Returns:
        A list of errors if there are errors present, or an empty list if
        verification completed successfully."""
    if errors := attribute_util.check_attributes_in_ir(
        ir,
        back_end="cpp",
        types=attributes.TYPES,
        module_attributes=attributes.Scope.MODULE,
        struct_attributes=attributes.Scope.STRUCT,
        bits_attributes=attributes.Scope.BITS,
        enum_attributes=attributes.Scope.ENUM,
        enum_value_attributes=attributes.Scope.ENUM_VALUE,
    ):
        return errors

    if errors := _verify_attribute_values(ir):
        return errors

    # Ensure defaults are set on EnumValues for `enum_case`.
    _propagate_defaults(
        ir,
        targets=[ir_data.EnumValue],
        ancestors=[ir_data.Module, ir_data.TypeDefinition],
        add_fn=_add_missing_enum_case_attribute_on_enum_value,
    )

    return []


def generate_header(ir, config=Config()):
    """Generates a C++ header from an Emboss module.

    Arguments:
      ir: An EmbossIr of the module.

    Returns:
      A tuple of (header, errors), where `header` is either a string containing
      the text of a C++ header which implements Views for the types in the Emboss
      module, or None, and `errors` is a possibly-empty list of error messages to
      display to the user.
    """
    errors = _propagate_defaults_and_verify_attributes(ir)
    if errors:
        return None, errors
    type_declarations = []
    type_definitions = []
    method_definitions = []
    for type_definition in ir.module[0].type:
        declaration, definition, methods = _generate_type_definition(
            type_definition, ir, config
        )
        type_declarations.append(declaration)
        type_definitions.append(definition)
        method_definitions.append(methods)
    body = code_template.format_template(
        _TEMPLATES.body,
        type_declarations="".join(type_declarations),
        type_definitions="".join(type_definitions),
        method_definitions="".join(method_definitions),
    )
    body = _wrap_in_namespace(body, _get_module_namespace(ir.module[0]))
    includes = _get_includes(ir.module[0], config)
    return (
        code_template.format_template(
            _TEMPLATES.outline,
            includes=includes,
            body=body,
            header_guard=_generate_header_guard(ir.module[0].source_file_name),
        ),
        [],
    )
