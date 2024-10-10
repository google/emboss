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
    if type_definition.HasField("external"):
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
    elif type_definition.HasField("structure"):
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
    elif type_definition.HasField("enumeration"):
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
        assert type_ir.HasField("atomic_type")
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
    if expression_type.WhichOneof("type") == "integer":
        return _cpp_integer_type_for_range(
            int(expression_type.integer.minimum_value),
            int(expression_type.integer.maximum_value),
        )
    elif expression_type.WhichOneof("type") == "boolean":
        return "bool"
    elif expression_type.WhichOneof("type") == "enumeration":
        return _get_fully_qualified_name(
            expression_type.enumeration.name.canonical_name, ir
        )
    else:
        assert False, "Unknown expression type " + expression_type.WhichOneof("type")


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
    rendered_args = [
        _render_expression(arg, ir, field_reader, subexpressions).rendered
        for arg in args
    ]
    minimum_integers = []
    maximum_integers = []
    enum_types = set()
    have_boolean_types = False
    for subexpression in [expression] + list(args):
        if subexpression.type.WhichOneof("type") == "integer":
            minimum_integers.append(int(subexpression.type.integer.minimum_value))
            maximum_integers.append(int(subexpression.type.integer.maximum_value))
        elif subexpression.type.WhichOneof("type") == "enumeration":
            enum_types.add(_cpp_basic_type_for_expression(subexpression, ir))
        elif subexpression.type.WhichOneof("type") == "boolean":
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
        field = prefix + _render_variable(
            ir_util.hashable_form_of_field_reference(expression.field_reference)
        )
        if subexpressions is None:
            field_expression = field
        else:
            field_expression = subexpressions.add(field)
        expression_cpp_type = _cpp_basic_type_for_expression(expression, ir)
        return (
            "({0}.Ok()"
            "    ? {1}(static_cast</**/{2}>({0}.UncheckedRead()))"
            "    : {1}())".format(
                field_expression, _maybe_type(expression_cpp_type), expression_cpp_type
            )
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


class _SubexpressionStore(object):
    """Holder for subexpressions to be assigned to local variables."""

    def __init__(self, prefix):
        self._prefix = prefix
        self._subexpr_to_name = {}
        self._index_to_subexpr = []

    def add(self, subexpr):
        if subexpr not in self._subexpr_to_name:
            self._index_to_subexpr.append(subexpr)
            self._subexpr_to_name[subexpr] = self._prefix + str(
                len(self._index_to_subexpr)
            )
        return self._subexpr_to_name[subexpr]

    def subexprs(self):
        return [
            (self._subexpr_to_name[subexpr], subexpr)
            for subexpr in self._index_to_subexpr
        ]


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
        subexpressions: A _SubexpressionStore in which to put subexpressions, or
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
    if expression.type.WhichOneof("type") == "integer":
        if expression.type.integer.modulus == "infinity":
            return _ExpressionResult(
                _render_integer_for_expression(
                    int(expression.type.integer.modular_value)
                ),
                True,
            )
    elif expression.type.WhichOneof("type") == "boolean":
        if expression.type.boolean.HasField("value"):
            if expression.type.boolean.value:
                return _ExpressionResult(_maybe_type("bool") + "(true)", True)
            else:
                return _ExpressionResult(_maybe_type("bool") + "(false)", True)
    elif expression.type.WhichOneof("type") == "enumeration":
        if expression.type.enumeration.HasField("value"):
            return _ExpressionResult(
                _render_enum_value(expression.type.enumeration, ir), True
            )
    else:
        # There shouldn't be any "opaque" type expressions here.
        assert False, "Unhandled expression type {}".format(
            expression.type.WhichOneof("type")
        )

    result = None
    # Otherwise, render the operation.
    if expression.WhichOneof("expression") == "function":
        result = _render_builtin_operation(expression, ir, field_reader, subexpressions)
    elif expression.WhichOneof("expression") == "field_reference":
        result = field_reader.render_field(expression, ir, subexpressions)
    elif (
        expression.WhichOneof("expression") == "builtin_reference"
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
    return _render_expression(field.existence_condition, ir, subexpressions)


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
    if field_ir.type.HasField("size_in_bits"):
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
    if field_ir.write_method.WhichOneof("method") == "alias":
        return _generate_field_indirection(field_ir, enclosing_type_name, ir)

    read_subexpressions = _SubexpressionStore("emboss_reserved_local_subexpr_")
    read_value = _render_expression(
        field_ir.read_transform,
        ir,
        field_reader=_VirtualViewFieldRenderer(),
        subexpressions=read_subexpressions,
    )
    field_exists = _render_existence_test(field_ir, ir)
    logical_type = _cpp_basic_type_for_expression(field_ir.read_transform, ir)

    if read_value.is_constant and field_exists.is_constant:
        assert not read_subexpressions.subexprs()
        declaration_template = (
            _TEMPLATES.structure_single_const_virtual_field_method_declarations
        )
        definition_template = (
            _TEMPLATES.structure_single_const_virtual_field_method_definitions
        )
    else:
        declaration_template = (
            _TEMPLATES.structure_single_virtual_field_method_declarations
        )
        definition_template = (
            _TEMPLATES.structure_single_virtual_field_method_definitions
        )

    if field_ir.write_method.WhichOneof("method") == "transform":
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
    if field_ir.read_transform.type.WhichOneof("type") == "integer":
        write_to_text_stream_function = "WriteIntegerViewToTextStream"
    elif field_ir.read_transform.type.WhichOneof("type") == "boolean":
        write_to_text_stream_function = "WriteBooleanViewToTextStream"
    elif field_ir.read_transform.type.WhichOneof("type") == "enumeration":
        write_to_text_stream_function = "WriteEnumViewToTextStream"
    else:
        assert False, "Unexpected read-only virtual field type {}".format(
            field_ir.read_transform.type.WhichOneof("type")
        )

    value_is_ok = _generate_validator_expression_for(field_ir, ir)
    declaration = code_template.format_template(
        declaration_template,
        visibility=_visibility_for_field(field_ir),
        name=name,
        virtual_view_type_name=virtual_view_type_name,
        logical_type=logical_type,
        read_subexpressions="".join(
            [
                "      const auto {} = {};\n".format(subexpr_name, subexpr)
                for subexpr_name, subexpr in read_subexpressions.subexprs()
            ]
        ),
        read_value=read_value.rendered,
        write_to_text_stream_function=write_to_text_stream_function,
        parent_type=enclosing_type_name,
        write_methods=write_methods,
        value_is_ok=value_is_ok,
    )
    definition = code_template.format_template(
        definition_template,
        name=name,
        virtual_view_type_name=virtual_view_type_name,
        logical_type=logical_type,
        read_value=read_value.rendered,
        parent_type=enclosing_type_name,
        field_exists=field_exists.rendered,
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

    subexpressions = _SubexpressionStore("emboss_reserved_local_subexpr_")
    parameter_values = []
    parameters_known = []
    for parameter in parameter_expressions:
        parameter_cpp_expr = _render_expression(
            parameter, ir, subexpressions=subexpressions
        )
        parameter_values.append(
            "{}.ValueOrDefault(), ".format(parameter_cpp_expr.rendered)
        )
        parameters_known.append("{}.Known() && ".format(parameter_cpp_expr.rendered))
    parameter_subexpressions = "".join(
        [
            "  const auto {} = {};\n".format(name, subexpr)
            for name, subexpr in subexpressions.subexprs()
        ]
    )

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

    field_alignment, field_offset = _alignment_of_location(field_ir.location)
    declaration = code_template.format_template(
        _TEMPLATES.structure_single_field_method_declarations,
        type_reader=type_reader,
        visibility=_visibility_for_field(field_ir),
        name=field_name,
    )
    definition = code_template.format_template(
        _TEMPLATES.structure_single_field_method_definitions,
        parent_type=enclosing_type_name,
        name=field_name,
        type_reader=type_reader,
        offset=offset,
        size=size,
        size_and_offset_subexpressions=size_and_offset_subexpressions,
        field_exists=_render_existence_test(field_ir, ir).rendered,
        alignment=field_alignment,
        parameters_known="".join(parameters_known),
        parameter_values="".join(parameter_values),
        parameter_subexpressions=parameter_subexpressions,
        static_offset=field_offset,
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
    declaration = code_template.format_template(
        _TEMPLATES.structure_single_field_indirect_method_declarations,
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
        field_exists=_render_existence_test(field_ir, ir).rendered,
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
    ok_method_clauses = []
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
        if subtype.HasField("enumeration"):
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

    for field_index in type_ir.structure.fields_in_dependency_order:
        field = type_ir.structure.field[field_index]
        helper_types, declaration, definition = _generate_structure_field_methods(
            type_name, field, ir, type_ir.addressable_unit
        )
        field_helper_type_definitions.append(helper_types)
        field_method_definitions.append(definition)
        ok_method_clauses.append(
            code_template.format_template(
                _TEMPLATES.ok_method_test,
                field=_cpp_field_name(field.name.name.text) + "()",
            )
        )
        if not ir_util.field_is_virtual(field):
            # Virtual fields do not participate in equality tests -- they are equal by
            # definition.
            equals_method_clauses.append(
                code_template.format_template(
                    _TEMPLATES.equals_method_test, field=field.name.name.text + "()"
                )
            )
            unchecked_equals_method_clauses.append(
                code_template.format_template(
                    _TEMPLATES.unchecked_equals_method_test,
                    field=field.name.name.text + "()",
                )
            )
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

    class_forward_declarations = code_template.format_template(
        _TEMPLATES.structure_view_declaration, name=type_name
    )
    class_bodies = code_template.format_template(
        _TEMPLATES.structure_view_class,
        name=type_ir.name.canonical_name.object_path[-1],
        size_method=_render_size_method(type_ir.structure.field, ir),
        field_method_declarations="".join(field_method_declarations),
        field_ok_checks="\n".join(ok_method_clauses),
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
    if type_ir.HasField("structure"):
        return _generate_structure_definition(type_ir, ir, config)
    elif type_ir.HasField("enumeration"):
        return _generate_enum_definition(type_ir, config.include_enum_traits)
    elif type_ir.HasField("external"):
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

    new_location = ir_data_utils.copy(source_location)
    new_location.start.column = source_location.start.column + offset[0]
    new_location.end.column = source_location.start.column + offset[1]

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
