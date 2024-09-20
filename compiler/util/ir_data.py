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

"""Intermediate representation (IR) for Emboss.

This is limited to purely data and type annotations.
"""

import dataclasses
import enum
import sys
from typing import ClassVar, Optional

from compiler.util import ir_data_fields


@dataclasses.dataclass
class Message:
    """Base class for IR data objects.

    Historically protocol buffers were used for serializing this data which has
    led to some legacy naming conventions and references. In particular this
    class is named `Message` in the sense of a protocol buffer message,
    indicating that it is intended to just be data that is used by other higher
    level services.

    There are some other legacy idioms leftover from the protocol buffer-based
    definition such as support for "oneof" and optional fields.
    """

    IR_DATACLASS: ClassVar[object] = object()
    field_specs: ClassVar[ir_data_fields.FilteredIrFieldSpecs]

    def __post_init__(self):
        """Called by dataclass subclasses after init.

        Post-processes any lists passed in to use our custom list type.
        """
        # Convert any lists passed in to CopyValuesList
        for spec in self.field_specs.sequence_field_specs:
            cur_val = getattr(self, spec.name)
            if isinstance(cur_val, ir_data_fields.TemporaryCopyValuesList):
                copy_val = cur_val.temp_list
            else:
                copy_val = ir_data_fields.CopyValuesList(spec.data_type)
                if cur_val:
                    copy_val.shallow_copy(cur_val)
            setattr(self, spec.name, copy_val)

    # This hook adds a 15% overhead to end-to-end code generation in some cases
    # so we guard it in a `__debug__` block. Users can opt-out of this check by
    # running python with the `-O` flag, ie: `python3 -O ./embossc`.
    if __debug__:

        def __setattr__(self, name: str, value) -> None:
            """Debug-only hook that adds basic type checking for ir_data fields."""
            if spec := self.field_specs.all_field_specs.get(name):
                if not (
                    # Check if it's the expected type
                    isinstance(value, spec.data_type)
                    or
                    # Oneof fields are a special case
                    spec.is_oneof
                    or
                    # Optional fields can be set to None
                    (
                        spec.container is ir_data_fields.FieldContainer.OPTIONAL
                        and value is None
                    )
                    or
                    # Sequences can be a few variants of lists
                    (
                        spec.is_sequence
                        and isinstance(
                            value,
                            (
                                list,
                                ir_data_fields.TemporaryCopyValuesList,
                                ir_data_fields.CopyValuesList,
                            ),
                        )
                    )
                    or
                    # An enum value can be an int
                    (spec.is_enum and isinstance(value, int))
                ):
                    raise AttributeError(
                        f"Cannot set {value} (type {value.__class__}) for type"
                        "{spec.data_type}"
                    )
            object.__setattr__(self, name, value)

    # Non-PEP8 name to mimic the Google Protobuf interface.
    def HasField(self, name):  # pylint:disable=invalid-name
        """Indicates if this class has the given field defined and it is set."""
        return getattr(self, name, None) is not None

    # Non-PEP8 name to mimic the Google Protobuf interface.
    def WhichOneof(self, oneof_name):  # pylint:disable=invalid-name
        """Indicates which field has been set for the oneof value.

        Args:
            oneof_name: the name of the oneof construct to test.

        Returns: the field name, or None if no field has been set.
        """
        for field_name, oneof in self.field_specs.oneof_mappings:
            if oneof == oneof_name and self.HasField(field_name):
                return field_name
        return None


################################################################################
# From here to the end of the file are actual structure definitions.


@dataclasses.dataclass
class Position(Message):
    """A zero-width position within a source file."""

    line: int = 0
    """Line (starts from 1)."""
    column: int = 0
    """Column (starts from 1)."""


@dataclasses.dataclass
class Location(Message):
    """A half-open start:end range within a source file."""

    start: Optional[Position] = None
    """Beginning of the range"""
    end: Optional[Position] = None
    """One column past the end of the range."""

    is_disjoint_from_parent: Optional[bool] = None
    """True if this Location is outside of the parent object's Location."""

    is_synthetic: Optional[bool] = None
    """True if this Location's parent was synthesized, and does not directly
  appear in the source file.

  The Emboss front end uses this field to cull
  irrelevant error messages.
  """


@dataclasses.dataclass
class Word(Message):
    """IR for a bare word in the source file.

    This is used in NameDefinitions and References.
    """

    text: Optional[str] = None
    source_location: Optional[Location] = None


@dataclasses.dataclass
class String(Message):
    """IR for a string in the source file."""

    text: Optional[str] = None
    source_location: Optional[Location] = None


@dataclasses.dataclass
class Documentation(Message):
    text: Optional[str] = None
    source_location: Optional[Location] = None


@dataclasses.dataclass
class BooleanConstant(Message):
    """IR for a boolean constant."""

    value: Optional[bool] = None
    source_location: Optional[Location] = None


@dataclasses.dataclass
class Empty(Message):
    """Placeholder message for automatic element counts for arrays."""

    source_location: Optional[Location] = None


@dataclasses.dataclass
class NumericConstant(Message):
    """IR for any numeric constant."""

    # Numeric constants are stored as decimal strings; this is the simplest way
    # to store the full -2**63..+2**64 range.
    #
    # TODO(bolms): switch back to int, and just use strings during
    # serialization, now that we're free of proto.
    value: Optional[str] = None
    source_location: Optional[Location] = None


class FunctionMapping(int, enum.Enum):
    """Enum of supported function types."""

    UNKNOWN = 0
    ADDITION = 1
    """`+`"""
    SUBTRACTION = 2
    """`-`"""
    MULTIPLICATION = 3
    """`*`"""
    EQUALITY = 4
    """`==`"""
    INEQUALITY = 5
    """`!=`"""
    AND = 6
    """`&&`"""
    OR = 7
    """`||`"""
    LESS = 8
    """`<`"""
    LESS_OR_EQUAL = 9
    """`<=`"""
    GREATER = 10
    """`>`"""
    GREATER_OR_EQUAL = 11
    """`>=`"""
    CHOICE = 12
    """`?:`"""
    MAXIMUM = 13
    """`$max()`"""
    PRESENCE = 14
    """`$present()`"""
    UPPER_BOUND = 15
    """`$upper_bound()`"""
    LOWER_BOUND = 16
    """`$lower_bound()`"""


@dataclasses.dataclass
class Function(Message):
    """IR for a single function (+, -, *, ==, $max, etc.) in an expression."""

    function: Optional[FunctionMapping] = None
    args: list["Expression"] = ir_data_fields.list_field(lambda: Expression)
    function_name: Optional[Word] = None
    source_location: Optional[Location] = None


@dataclasses.dataclass
class CanonicalName(Message):
    """CanonicalName is the unique, absolute name for some object.

    A CanonicalName is the unique, absolute name for some object (Type, field,
    etc.) in the IR.  It is used both in the definitions of objects ("struct
    Foo"), and in references to objects (a field of type "Foo").
    """

    module_file: str = ir_data_fields.str_field()
    """The module_file is the Module.source_file_name of the Module in which this
  object's definition appears.

  Note that the Prelude always has a Module.source_file_name of "", and thus
  references to Prelude names will have module_file == "".
  """

    object_path: list[str] = ir_data_fields.list_field(str)
    """The object_path is the canonical path to the object definition within its
  module file.

  For example, the field "bar" would have an object path of
  ["Foo", "bar"]:

  struct Foo:
    0:3  UInt  bar


  The enumerated name "BOB" would have an object path of ["Baz", "Qux",
  "BOB"]:

  struct Baz:
    0:3  Qux   qux

    enum Qux:
      BOB = 0
  """


@dataclasses.dataclass
class NameDefinition(Message):
    """NameDefinition is IR for the name of an object, within the object.

    That is, a TypeDefinition or Field will hold a NameDefinition as its
    name.
    """

    name: Optional[Word] = None
    """The name, as directly generated from the source text.

  name.text will match the last element of canonical_name.object_path. Note
  that in some cases, the exact string in name.text may not appear in the
  source text.
  """

    canonical_name: Optional[CanonicalName] = None
    """The CanonicalName that will appear in References.
  This field is technically redundant: canonical_name.module_file should always
  match the source_file_name of the enclosing Module, and
  canonical_name.object_path should always match the names of parent nodes.
  """

    is_anonymous: Optional[bool] = None
    """If true, indicates that this is an automatically-generated name, which
  should not be visible outside of its immediate namespace.
  """

    source_location: Optional[Location] = None
    """The location of this NameDefinition in source code."""


@dataclasses.dataclass
class Reference(Message):
    """A Reference holds the canonical name of something defined elsewhere.

    For example, take this fragment:

     struct Foo:
      0:3  UInt    size (s)
      4:s  Int:8[] payload

    "Foo", "size", and "payload" will become NameDefinitions in their
    corresponding Field and Message IR objects, while "UInt", the second "s",
    and "Int" are References.  Note that the second "s" will have a
    canonical_name.object_path of ["Foo", "size"], not ["Foo", "s"]: the
    Reference always holds the single "true" name of the object, regardless of
    what appears in the .emb.
    """

    canonical_name: Optional[CanonicalName] = None
    """The canonical name of the object being referred to.

  This name should be used to find the object in the IR.
  """

    source_name: list[Word] = ir_data_fields.list_field(Word)
    """The source_name is the name the user entered in the source file.

  The source_name could be either relative or absolute, and may be an alias
  (and thus not match any part of the canonical_name).  Back ends should use
  canonical_name for name lookup, and reserve source_name for error messages.
  """

    is_local_name: Optional[bool] = None
    """If true, then symbol resolution should only look at local names when
  resolving source_name.

  This is used so that the names of inline types aren't "ambiguous" if there
  happens to be another type with the same name at a parent scope.
  """

    # TODO(bolms): Allow absolute paths starting with ".".

    source_location: Optional[Location] = None
    """Note that this is the source_location of the *Reference*, not of the
  object to which it refers.
  """


@dataclasses.dataclass
class FieldReference(Message):
    """IR for a "field" or "field.sub.subsub" reference in an expression.

    The first element of "path" is the "base" field, which should be directly
    readable in the (runtime) context of the expression.  For example:

      struct Foo:
       0:1  UInt      header_size (h)
       0:h  UInt:8[]  header_bytes

    The "h" will translate to ["Foo", "header_size"], which will be the first
    (and in this case only) element of "path".

    Subsequent path elements should be treated as subfields.  For example, in:

      struct Foo:
       struct Sizes:
        0:1  UInt  header_size
        1:2  UInt  body_size
       0                 [+2]                  Sizes     sizes
       0                 [+sizes.header_size]  UInt:8[]  header
       sizes.header_size [+sizes.body_size]    UInt:8[]  body

    The references to "sizes.header_size" will have a path of [["Foo",
    "sizes"], ["Foo", "Sizes", "header_size"]].  Note that each path element is
    a fully-qualified reference; some back ends (C++, Python) may only use the
    last element, while others (C) may use the complete path.

    This representation is a bit awkward, and is fundamentally limited to a
    dotted list of static field names.  It does not allow an expression like
    `array[n]` on the left side of a `.`.  At this point, it is an artifact of
    the era during which I (bolms@) thought I could get away with skipping
    compiler-y things.
    """

    # TODO(bolms): Add composite types to the expression type system, and
    # replace FieldReference with a "member access" Expression kind.  Further,
    # move the symbol resolution for FieldReferences that is currently in
    # symbol_resolver.py into type_check.py.

    # TODO(bolms): Make the above change before declaring the IR to be "stable".

    path: list[Reference] = ir_data_fields.list_field(Reference)
    source_location: Optional[Location] = None


@dataclasses.dataclass
class OpaqueType(Message):
    pass


@dataclasses.dataclass
class IntegerType(Message):
    """Type of an integer expression."""

    # For optimization, the modular congruence of an integer expression is
    # tracked.  This consists of a modulus and a modular_value, such that for
    # all possible values of expression, expression MOD modulus ==
    # modular_value.
    #
    # The modulus may be the special value "infinity" to indicate that the
    # expression's value is exactly modular_value; otherwise, it should be a
    # positive integer.
    #
    # A modulus of 1 places no constraints on the value.
    #
    # The modular_value should always be a nonnegative integer that is smaller
    # than the modulus.
    #
    # Note that this is specifically the *modulus*, which is not equivalent to
    # the value from C's '%' operator when the dividend is negative: in C, -7 %
    # 4 == -3, but the modular_value here would be 1.  Python uses modulus: in
    # Python, -7 % 4 == 1.
    modulus: Optional[str] = None
    """The modulus portion of the modular congruence of an integer expression.

  The modulus may be the special value "infinity" to indicate that the
  expression's value is exactly modular_value; otherwise, it should be a
  positive integer.

  A modulus of 1 places no constraints on the value.
  """
    modular_value: Optional[str] = None
    """ The modular_value portion of the modular congruence of an integer expression.

  The modular_value should always be a nonnegative integer that is smaller
  than the modulus.
  """

    # The minimum and maximum values of an integer are tracked and checked so
    # that Emboss can implement reliable arithmetic with no operations
    # overflowing either 64-bit unsigned or 64-bit signed 2's-complement
    # integers.
    #
    # Note that constant subexpressions are allowed to overflow, as long as the
    # final, computed constant value of the subexpression fits in a 64-bit
    # value.
    #
    # The minimum_value may take the value "-infinity", and the maximum_value
    # may take the value "infinity".  These sentinel values indicate that
    # Emboss has no bound information for the Expression, and therefore the
    # Expression may only be evaluated during compilation; the back end should
    # never need to compile such an expression into the target language (e.g.,
    # C++).
    minimum_value: Optional[str] = None
    maximum_value: Optional[str] = None


@dataclasses.dataclass
class BooleanType(Message):
    value: Optional[bool] = None


@dataclasses.dataclass
class EnumType(Message):
    name: Optional[Reference] = None
    value: Optional[str] = None


@dataclasses.dataclass
class ExpressionType(Message):
    opaque: Optional[OpaqueType] = ir_data_fields.oneof_field("type")
    integer: Optional[IntegerType] = ir_data_fields.oneof_field("type")
    boolean: Optional[BooleanType] = ir_data_fields.oneof_field("type")
    enumeration: Optional[EnumType] = ir_data_fields.oneof_field("type")


@dataclasses.dataclass
class Expression(Message):
    """IR for an expression.

    An Expression is a potentially-recursive data structure.  It can either
    represent a leaf node (constant or reference) or an operation combining
    other Expressions (function).
    """

    constant: Optional[NumericConstant] = ir_data_fields.oneof_field("expression")
    constant_reference: Optional[Reference] = ir_data_fields.oneof_field("expression")
    function: Optional[Function] = ir_data_fields.oneof_field("expression")
    field_reference: Optional[FieldReference] = ir_data_fields.oneof_field("expression")
    boolean_constant: Optional[BooleanConstant] = ir_data_fields.oneof_field(
        "expression"
    )
    builtin_reference: Optional[Reference] = ir_data_fields.oneof_field("expression")

    type: Optional[ExpressionType] = None
    source_location: Optional[Location] = None


@dataclasses.dataclass
class ArrayType(Message):
    """IR for an array type ("Int:8[12]" or "Message[2]" or "UInt[3][2]")."""

    base_type: Optional["Type"] = None

    element_count: Optional[Expression] = ir_data_fields.oneof_field("size")
    automatic: Optional[Empty] = ir_data_fields.oneof_field("size")

    source_location: Optional[Location] = None


@dataclasses.dataclass
class AtomicType(Message):
    """IR for a non-array type ("UInt" or "Foo(Version.SIX)")."""

    reference: Optional[Reference] = None
    runtime_parameter: list[Expression] = ir_data_fields.list_field(Expression)
    source_location: Optional[Location] = None


@dataclasses.dataclass
class Type(Message):
    """IR for a type reference ("UInt", "Int:8[12]", etc.)."""

    atomic_type: Optional[AtomicType] = ir_data_fields.oneof_field("type")
    array_type: Optional[ArrayType] = ir_data_fields.oneof_field("type")

    size_in_bits: Optional[Expression] = None
    source_location: Optional[Location] = None


@dataclasses.dataclass
class AttributeValue(Message):
    """IR for a attribute value."""

    # TODO(bolms): Make String a type of Expression, and replace
    # AttributeValue with Expression.
    expression: Optional[Expression] = ir_data_fields.oneof_field("value")
    string_constant: Optional[String] = ir_data_fields.oneof_field("value")

    source_location: Optional[Location] = None


@dataclasses.dataclass
class Attribute(Message):
    """IR for a [name = value] attribute."""

    name: Optional[Word] = None
    value: Optional[AttributeValue] = None
    back_end: Optional[Word] = None
    is_default: Optional[bool] = None
    source_location: Optional[Location] = None


@dataclasses.dataclass
class WriteTransform(Message):
    """IR which defines an expression-based virtual field write scheme.

    E.g., for a virtual field like `x_plus_one`:

      struct Foo:
       0 [+1]  UInt  x
       let x_plus_one = x + 1

    ... the `WriteMethod` would be `transform`, with `$logical_value - 1` for
    `function_body` and `x` for `destination`.
    """

    function_body: Optional[Expression] = None
    destination: Optional[FieldReference] = None


@dataclasses.dataclass
class WriteMethod(Message):
    """IR which defines the method used for writing to a virtual field."""

    physical: Optional[bool] = ir_data_fields.oneof_field("method")
    """A physical Field can be written directly."""

    read_only: Optional[bool] = ir_data_fields.oneof_field("method")
    """A read_only Field cannot be written."""

    alias: Optional[FieldReference] = ir_data_fields.oneof_field("method")
    """An alias is a direct, untransformed forward of another field; it can be
  implemented by directly returning a reference to the aliased field.

  Aliases are the only kind of virtual field that may have an opaque type.
  """

    transform: Optional[WriteTransform] = ir_data_fields.oneof_field("method")
    """A transform is a way of turning a logical value into a value which should
  be written to another field.

  A virtual field like `let y = x + 1` would
  have a transform WriteMethod to subtract 1 from the new `y` value, and
  write that to `x`.
  """


@dataclasses.dataclass
class FieldLocation(Message):
    """IR for a field location."""

    start: Optional[Expression] = None
    size: Optional[Expression] = None
    source_location: Optional[Location] = None


@dataclasses.dataclass
class Field(Message):  # pylint:disable=too-many-instance-attributes
    """IR for a field in a struct definition.

    There are two kinds of Field: physical fields have location and (physical)
    type; virtual fields have read_transform.  Although there are differences,
    in many situations physical and virtual fields are treated the same way,
    and they can be freely intermingled in the source file.
    """

    location: Optional[FieldLocation] = None
    """The physical location of the field."""
    type: Optional[Type] = None
    """The physical type of the field."""

    read_transform: Optional[Expression] = None
    """The value of a virtual field."""

    write_method: Optional[WriteMethod] = None
    """How this virtual field should be written."""

    name: Optional[NameDefinition] = None
    """The name of the field."""
    abbreviation: Optional[Word] = None
    """An optional short name for the field, only visible inside the enclosing bits/struct."""
    attribute: list[Attribute] = ir_data_fields.list_field(Attribute)
    """Field-specific attributes."""
    documentation: list[Documentation] = ir_data_fields.list_field(Documentation)
    """Field-specific documentation."""

    # TODO(bolms): Document conditional fields better, and replace some of this
    # explanation with a reference to the documentation.
    existence_condition: Optional[Expression] = None
    """The field only exists when existence_condition evaluates to true.

  For example:
  ```
  struct Message:
    0 [+4]  UInt         length
    4 [+8]  MessageType  message_type
    if message_type == MessageType.FOO:
      8 [+length]  Foo   foo
    if message_type == MessageType.BAR:
      8 [+length]  Bar   bar
    8+length [+4]  UInt  crc
  ```
  For `length`, `message_type`, and `crc`, existence_condition will be
  `boolean_constant { value: true }`

  For `foo`, existence_condition will be:
  ```
      function { function: EQUALITY
                 args: [reference to message_type]
                 args: { [reference to MessageType.FOO] } }
  ```

  The `bar` field will have a similar existence_condition to `foo`:
  ```
      function { function: EQUALITY
                 args: [reference to message_type]
                 args: { [reference to MessageType.BAR] } }
  ```

  When `message_type` is `MessageType.BAR`, the `Message` struct does not contain
  field `foo`, and vice versa for `message_type == MessageType.FOO` and field
  `bar`: those fields only conditionally exist in the structure.
  """

    source_location: Optional[Location] = None


@dataclasses.dataclass
class Structure(Message):
    """IR for a bits or struct definition."""

    field: list[Field] = ir_data_fields.list_field(Field)

    fields_in_dependency_order: list[int] = ir_data_fields.list_field(int)
    """The fields in `field` are listed in the order they appear in the original
  .emb.

  For text format output, this can lead to poor results.  Take the following
  struct:
  ```
      struct Foo:
        b [+4]  UInt  a
        0 [+4]  UInt  b
  ```
  Here, the location of `a` depends on the current value of `b`.  Because of
  this, if someone calls
  ```
      emboss::UpdateFromText(foo_view, "{ a: 10, b: 4 }");
  ```
  then foo_view will not be updated the way one would expect: if `b`'s value
  was something other than 4 to start with, then `UpdateFromText` will write
  the 10 to some other location, then update `b` to 4.

  To avoid surprises, `emboss::DumpAsText` should return `"{ b: 4, a: 10
  }"`.

  The `fields_in_dependency_order` field provides a permutation of `field`
  such that each field appears after all of its dependencies.  For example,
  `struct Foo`, above, would have `{ 1, 0 }` in
  `fields_in_dependency_order`.

  The exact ordering of `fields_in_dependency_order` is not guaranteed, but
  some effort is made to keep the order close to the order fields are listed
  in the original `.emb` file.  In particular, if the ordering 0, 1, 2, 3,
  ... satisfies dependency ordering, then `fields_in_dependency_order` will
  be `{ 0, 1, 2, 3, ... }`.
  """

    source_location: Optional[Location] = None


@dataclasses.dataclass
class External(Message):
    """IR for an external type declaration."""

    # Externals have no values other than name and attribute list, which are
    # common to all type definitions.

    source_location: Optional[Location] = None


@dataclasses.dataclass
class EnumValue(Message):
    """IR for a single value within an enumerated type."""

    name: Optional[NameDefinition] = None
    """The name of the enum value."""
    value: Optional[Expression] = None
    """The value of the enum value."""
    documentation: list[Documentation] = ir_data_fields.list_field(Documentation)
    """Value-specific documentation."""
    attribute: list[Attribute] = ir_data_fields.list_field(Attribute)
    """Value-specific attributes."""

    source_location: Optional[Location] = None


@dataclasses.dataclass
class Enum(Message):
    """IR for an enumerated type definition."""

    value: list[EnumValue] = ir_data_fields.list_field(EnumValue)
    source_location: Optional[Location] = None


@dataclasses.dataclass
class Import(Message):
    """IR for an import statement in a module."""

    file_name: Optional[String] = None
    """The file to import."""
    local_name: Optional[Word] = None
    """The name to use within this module."""
    source_location: Optional[Location] = None


@dataclasses.dataclass
class RuntimeParameter(Message):
    """IR for a runtime parameter definition."""

    name: Optional[NameDefinition] = None
    """The name of the parameter."""
    type: Optional[ExpressionType] = None
    """The type of the parameter."""

    # TODO(bolms): Actually implement the set builder type notation.
    physical_type_alias: Optional[Type] = None
    """For convenience and readability, physical types may be used in the .emb
  source instead of a full expression type.

  That way, users can write
  something like:
  ```
      struct Foo(version :: UInt:8):
  ```
  instead of:
  ```
      struct Foo(version :: {$int x |: 0 <= x <= 255}):
  ```
  In these cases, physical_type_alias holds the user-supplied type, and type
  is filled in after initial parsing is finished.
  """

    source_location: Optional[Location] = None


class AddressableUnit(int, enum.Enum):
    """The 'atom size' for a structure.

    The "addressable unit" is the size of the smallest unit that can be read
    from the backing store that this type expects.  For `struct`s, this is
    BYTE; for `enum`s and `bits`, this is BIT, and for `external`s it depends
    on the specific type
    """

    NONE = 0
    BIT = 1
    BYTE = 8


@dataclasses.dataclass
class TypeDefinition(Message):
    """Container IR for a type definition (struct, union, etc.)"""

    external: Optional[External] = ir_data_fields.oneof_field("type")
    enumeration: Optional[Enum] = ir_data_fields.oneof_field("type")
    structure: Optional[Structure] = ir_data_fields.oneof_field("type")

    name: Optional[NameDefinition] = None
    """The name of the type."""
    attribute: list[Attribute] = ir_data_fields.list_field(Attribute)
    """All attributes attached to the type."""
    documentation: list[Documentation] = ir_data_fields.list_field(Documentation)
    """Docs for the type."""
    # pylint:disable=undefined-variable
    subtype: list["TypeDefinition"] = ir_data_fields.list_field(lambda: TypeDefinition)
    """Subtypes of this type."""
    addressable_unit: Optional[AddressableUnit] = None

    runtime_parameter: list[RuntimeParameter] = ir_data_fields.list_field(
        RuntimeParameter
    )
    """If the type requires parameters at runtime, these are its parameters.

  These are currently only allowed on structures, but in the future they
  should be allowed on externals.
  """
    source_location: Optional[Location] = None


@dataclasses.dataclass
class Module(Message):
    """The IR for an individual Emboss module (file)."""

    attribute: list[Attribute] = ir_data_fields.list_field(Attribute)
    """Module-level attributes."""
    type: list[TypeDefinition] = ir_data_fields.list_field(TypeDefinition)
    """Module-level type definitions."""
    documentation: list[Documentation] = ir_data_fields.list_field(Documentation)
    """Module-level docs."""
    foreign_import: list[Import] = ir_data_fields.list_field(Import)
    """Other modules imported."""
    source_text: Optional[str] = None
    """The original source code."""
    source_location: Optional[Location] = None
    """Source code covered by this IR."""
    source_file_name: Optional[str] = None
    """Name of the source file."""


@dataclasses.dataclass
class EmbossIr(Message):
    """The top-level IR for an Emboss module and all of its dependencies."""

    module: list[Module] = ir_data_fields.list_field(Module)
    """All modules.

  The first entry will be the main module; back ends should
  generate code corresponding to that module.  The second entry will be the
  prelude module.
  """


# Post-process the dataclasses to add cached fields.
ir_data_fields.cache_message_specs(sys.modules[Message.__module__], Message)
