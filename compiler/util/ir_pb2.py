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

This was originally a Google Protocol Buffer file, but as of 2019 it turns
out that a) the public Google Python Protocol Buffer implementation is
extremely slow, and b) all the ways of getting Bazel+Python+Protocol Buffers
to play nice are hacky and fragile.

Thus, this file, which presents a similar-enough interface that the rest of
Emboss can use it with minimal changes.

Protobufs have a really, really strange, un-Pythonic interface, with tricky
implicit semantics -- mostly around magically instantiating protos when you
assign to some deeply-nested field.  I (bolms@) would *strongly* prefer to
have a more explicit interface, but don't (currently) have time to refactor
everything that touches the IR (i.e., the entire compiler).
"""

import json
import sys


if sys.version_info[0] == 2:
  _Text = unicode
  _text_types = (unicode, str)
  _Int = long
  _int_types = (int, long)
else:
  _Text = str
  _text_types = (str,)
  _Int = int
  _int_types = (int,)


_BASIC_TYPES = _text_types + _int_types + (bool,)


class Optional(object):
  """Property implementation for "optional"-like fields."""

  def __init__(self, type_, oneof=None, decode_names=None):
    """Creates a Proto "optional"-like data member.

    Args:
      type_: The type of the field; e.g., _Int or _Text.
      oneof: If set, the name of the proto-like "oneof" that this field is a
          member of.  Within a structure, at most one field of a particular
          "oneof" may be set at a time; setting a member of the "oneof" will
          clear any other member that might be set.
      decode_names: An optional callable that takes a str and returns a
          value of type type_; allows strs to be used to set "enums" using
          their symbolic names.
    """
    self._type = type_
    self._oneof = oneof
    self._decode_names = decode_names

  def __get__(self, obj, type_=None):
    result = obj.raw_fields.get(self.name, None)
    if result is not None:
      return result
    if self.type in _BASIC_TYPES:
      return self._type()
    result = self._type()

    def on_write():
      self._set_value(obj, result)

    result.set_on_write(on_write)
    return result

  def __set__(self, obj, value):
    if issubclass(self._type, _BASIC_TYPES):
      self.set(obj, value)
    else:
      raise AttributeError("Cannot set {} (type {}) for type {}".format(
          value, value.__class__, self._type))

  def _set_value(self, obj, value):
    if self._oneof is not None:
      current = obj.oneofs.get(self._oneof)
      if current in obj.raw_fields:
        del obj.raw_fields[current]
      obj.oneofs[self._oneof] = self.name
    obj.raw_fields[self.name] = value
    obj.on_write()

  def set(self, obj, value):
    """Sets the given value to the property."""

    if value is None:
      return
    if isinstance(value, dict):
      self._set_value(obj, self._type(**value))
    elif isinstance(value, _Text) and self._decode_names:
      self._set_value(obj, self._type(self._decode_names(value)))
    elif (not isinstance(value, self._type) and
          not (self._type == _Int and isinstance(value, _int_types)) and
          not (self._type == _Text and isinstance(value, _text_types))):
      raise AttributeError("Cannot set {} (type {}) for type {}".format(
          value, value.__class__, self._type))
    elif issubclass(self._type, Message):
      self._set_value(obj, self._type(**value.raw_fields))
    else:
      self._set_value(obj, self._type(value))

  def resolve_type(self):
    if isinstance(self._type, type(lambda: None)):
      self._type = self._type()

  @property
  def type(self):
    return self._type


class TypedScopedList(object):
  """A list with typechecking that notifies its parent when written to.

  TypedScopedList implements roughly the same semantics as the value of a
  Protobuf repeated field.  In particular, it checks that any values added
  to the list are of the correct type, and it calls the on_write callable
  when a value is added to the list, in order to implement the Protobuf
  "autovivification" semantics.
  """

  def __init__(self, type_, on_write=lambda: None):
    self._type = type_
    self._list = []
    self._on_write = on_write

  def __iter__(self):
    return iter(self._list)

  def __delitem__(self, key):
    del self._list[key]

  def __getitem__(self, key):
    return self._list[key]

  def extend(self, values):
    """list-like extend()."""

    for value in values:
      if isinstance(value, dict):
        self._list.append(self._type(**value))
      elif (not isinstance(value, self._type) and
            not (self._type == _Int and isinstance(value, _int_types)) and
            not (self._type == _Text and isinstance(value, _text_types))):
        raise TypeError(
            "Needed {}, got {} ({!r})".format(
                self._type, value.__class__, value))
      else:
        if self._type in _BASIC_TYPES:
          self._list.append(self._type(value))
        else:
          self._list.append(self._type(**value.raw_fields))
    self._on_write()

  def __repr__(self):
    return repr(self._list)

  def __len__(self):
    return len(self._list)

  def __eq__(self, other):
    return ((self.__class__ == other.__class__ and
             self._list == other._list) or  # pylint:disable=protected-access
            (isinstance(other, list) and self._list == other))

  def __ne__(self, other):
    return not (self == other)  # pylint:disable=superfluous-parens


class Repeated(object):
  """A proto-"repeated"-like property."""

  def __init__(self, type_):
    self._type = type_

  def __get__(self, obj, type_=None):
    return obj.raw_fields[self.name]

  def __set__(self, obj, value):
    raise AttributeError("Cannot set {}".format(self.name))

  def set(self, obj, values):
    typed_list = obj.raw_fields[self.name]
    if not isinstance(values, (list, TypedScopedList)):
      raise TypeError("Cannot initialize repeated field {} from {}".format(
          self.name, values.__class__))
    del typed_list[:]
    typed_list.extend(values)

  def resolve_type(self):
    if isinstance(self._type, type(lambda: None)):
      self._type = self._type()

  @property
  def type(self):
    return self._type


_deferred_specs = []


def message(cls):
  # TODO(bolms): move this into __init_subclass__ after dropping Python 2
  # support.
  _deferred_specs.append(cls)
  return cls


class Message(object):
  """Base class for proto "message"-like objects."""

  def __init__(self, **field_values):
    self.oneofs = {}
    self._on_write = lambda: None
    self._initialize_raw_fields_from(field_values)

  def _initialize_raw_fields_from(self, field_values):
    self.raw_fields = {}
    for name, type_ in self.repeated_fields.items():
      self.raw_fields[name] = TypedScopedList(type_, self.on_write)
    for k, v in field_values.items():
      spec = self.field_specs.get(k)
      if spec is None:
        raise AttributeError("No field {} on {}.".format(
            k, self.__class__.__name__))
      spec.set(self, v)

  @classmethod
  def from_json(cls, text):
    as_dict = json.loads(text)
    return cls(**as_dict)

  def on_write(self):
    self._on_write()
    self._on_write = lambda: None

  def set_on_write(self, on_write):
    self._on_write = on_write

  def __eq__(self, other):
    return (self.__class__ == other.__class__ and
            self.raw_fields == other.raw_fields)

  # Non-PEP8 name to mimic the Google Protobuf interface.
  def CopyFrom(self, other):  # pylint:disable=invalid-name
    if self.__class__ != other.__class__:
      raise TypeError("{} cannot CopyFrom {}".format(
          self.__class__.__name__, other.__class__.__name__))
    self._initialize_raw_fields_from(other.raw_fields)
    self.on_write()

  # Non-PEP8 name to mimic the Google Protobuf interface.
  def HasField(self, name):  # pylint:disable=invalid-name
    return name in self.raw_fields

  # Non-PEP8 name to mimic the Google Protobuf interface.
  def WhichOneof(self, oneof_name):  # pylint:disable=invalid-name
    return self.oneofs.get(oneof_name)

  def to_dict(self):
    """Converts the message to a dict."""

    result = {}
    for k, v in self.raw_fields.items():
      if isinstance(v, _BASIC_TYPES):
        result[k] = v
      elif isinstance(v, TypedScopedList):
        if v:
          # For compatibility with the proto world, empty lists are just
          # elided.
          result[k] = [
              item if isinstance(item, _BASIC_TYPES) else item.to_dict()
              for item in v
          ]
      else:
        result[k] = v.to_dict()
    return result

  def __repr__(self):
    return self.to_json(separators=(",", ":"), sort_keys=True)

  def to_json(self, *args, **kwargs):
    return json.dumps(self.to_dict(), *args, **kwargs)

  def __str__(self):
    return _Text(self.to_dict())


def _initialize_deferred_specs():
  """Calls any lambdas in specs, to facilitate late binding.

  When two Message subclasses are mutually recursive, the standard way of
  referencing one of the classes will not work, because its name is not
  yet defined.  E.g.:

  class A(Message):
    b = Optional(B)

  class B(Message):
    a = Optional(A)

  In this case, Python complains when trying to construct the class A,
  because it cannot resolve B.

  To accommodate this, Optional and Repeated will accept callables instead of
  types, like:

  class A(Message):
    b = Optional(lambda: B)

  class B(Message):
    a = Optional(A)

  Once all of the message classes have been defined, it is safe to go back and
  resolve all of the names by calling all of the lambdas that were used in place
  of types.  This function just iterates through the message types, and asks
  their Optional and Repeated properties to call the lambdas that were used in
  place of types.
  """

  for cls in _deferred_specs:
    field_specs = {}
    repeated_fields = {}
    for k, v in cls.__dict__.items():
      if k.startswith("_"):
        continue
      if isinstance(v, (Optional, Repeated)):
        v.name = k
        v.resolve_type()
        field_specs[k] = v
        if isinstance(v, Repeated):
          repeated_fields[k] = v.type
    cls.field_specs = field_specs
    cls.repeated_fields = repeated_fields


################################################################################
# From here to (nearly) the end of the file are actual structure definitions.


@message
class Position(Message):
  """A zero-width position within a source file."""
  line = Optional(int)    # Line (starts from 1).
  column = Optional(int)  # Column (starts from 1).


@message
class Location(Message):
  """A half-open start:end range within a source file."""
  start = Optional(Position)  # Beginning of the range.
  end = Optional(Position)    # One column past the end of the range.

  # True if this Location is outside of the parent object's Location.
  is_disjoint_from_parent = Optional(bool)

  # True if this Location's parent was synthesized, and does not directly
  # appear in the source file.  The Emboss front end uses this field to cull
  # irrelevant error messages.
  is_synthetic = Optional(bool)


@message
class Word(Message):
  """IR for a bare word in the source file.

  This is used in NameDefinitions and References.
  """

  text = Optional(_Text)
  source_location = Optional(Location)


@message
class String(Message):
  """IR for a string in the source file."""
  text = Optional(_Text)
  source_location = Optional(Location)


@message
class Documentation(Message):
  text = Optional(_Text)
  source_location = Optional(Location)


@message
class BooleanConstant(Message):
  """IR for a boolean constant."""
  value = Optional(bool)
  source_location = Optional(Location)


@message
class Empty(Message):
  """Placeholder message for automatic element counts for arrays."""
  source_location = Optional(Location)


@message
class NumericConstant(Message):
  """IR for any numeric constant."""

  # Numeric constants are stored as decimal strings; this is the simplest way
  # to store the full -2**63..+2**64 range.
  #
  # TODO(bolms): switch back to int, and just use strings during
  # serialization, now that we're free of proto.
  value = Optional(_Text)
  source_location = Optional(Location)


@message
class Function(Message):
  """IR for a single function (+, -, *, ==, $max, etc.) in an expression."""
  UNKNOWN = 0
  ADDITION = 1           # +
  SUBTRACTION = 2        # -
  MULTIPLICATION = 3     # *
  EQUALITY = 4           # ==
  INEQUALITY = 5         # !=
  AND = 6                # &&
  OR = 7                 # ||
  LESS = 8               # <
  LESS_OR_EQUAL = 9      # <=
  GREATER = 10           # >
  GREATER_OR_EQUAL = 11  # >=
  CHOICE = 12            # ?:
  MAXIMUM = 13           # $max()
  PRESENCE = 14          # $present()
  UPPER_BOUND = 15       # $upper_bound()
  LOWER_BOUND = 16       # $lower_bound()

  # pylint:disable=undefined-variable
  function = Optional(int, decode_names=lambda x: getattr(Function, x))
  args = Repeated(lambda: Expression)
  function_name = Optional(Word)
  source_location = Optional(Location)


@message
class CanonicalName(Message):
  """CanonicalName is the unique, absolute name for some object.

  A CanonicalName is the unique, absolute name for some object (Type, field,
  etc.) in the IR.  It is used both in the definitions of objects ("struct
  Foo"), and in references to objects (a field of type "Foo").
  """

  # The module_file is the Module.source_file_name of the Module in which this
  # object's definition appears.  Note that the Prelude always has a
  # Module.source_file_name of "", and thus references to Prelude names will
  # have module_file == "".
  module_file = Optional(_Text)

  # The object_path is the canonical path to the object definition within its
  # module file.  For example, the field "bar" would have an object path of
  # ["Foo", "bar"]:
  #
  # struct Foo:
  #   0:3  UInt  bar
  #
  #
  # The enumerated name "BOB" would have an object path of ["Baz", "Qux",
  # "BOB"]:
  #
  # struct Baz:
  #   0:3  Qux   qux
  #
  #   enum Qux:
  #     BOB = 0
  object_path = Repeated(_Text)


@message
class NameDefinition(Message):
  """NameDefinition is IR for the name of an object, within the object.

  That is, a TypeDefinition or Field will hold a NameDefinition as its
  name.
  """

  # The name, as directly generated from the source text.  name.text will
  # match the last element of canonical_name.object_path.  Note that in some
  # cases, the exact string in name.text may not appear in the source text.
  name = Optional(Word)

  # The CanonicalName that will appear in References.  This field is
  # technically redundant: canonical_name.module_file should always match the
  # source_file_name of the enclosing Module, and canonical_name.object_path
  # should always match the names of parent nodes.
  canonical_name = Optional(CanonicalName)

  # If true, indicates that this is an automatically-generated name, which
  # should not be visible outside of its immediate namespace.
  is_anonymous = Optional(bool)

  # The location of this NameDefinition in source code.
  source_location = Optional(Location)


@message
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

  # The canonical name of the object being referred to.  This name should be
  # used to find the object in the IR.
  canonical_name = Optional(CanonicalName)

  # The source_name is the name the user entered in the source file; it could
  # be either relative or absolute, and may be an alias (and thus not match
  # any part of the canonical_name).  Back ends should use canonical_name for
  # name lookup, and reserve source_name for error messages.
  source_name = Repeated(Word)

  # If true, then symbol resolution should only look at local names when
  # resolving source_name.  This is used so that the names of inline types
  # aren't "ambiguous" if there happens to be another type with the same name
  # at a parent scope.
  is_local_name = Optional(bool)

  # TODO(bolms): Allow absolute paths starting with ".".

  # Note that this is the source_location of the *Reference*, not of the
  # object to which it refers.
  source_location = Optional(Location)


@message
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

  path = Repeated(Reference)
  source_location = Optional(Location)


@message
class OpaqueType(Message):
  pass


@message
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
  modulus = Optional(_Text)
  modular_value = Optional(_Text)

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
  minimum_value = Optional(_Text)
  maximum_value = Optional(_Text)


@message
class BooleanType(Message):
  value = Optional(bool)


@message
class EnumType(Message):
  name = Optional(Reference)
  value = Optional(_Text)


@message
class ExpressionType(Message):
  opaque = Optional(OpaqueType, "type")
  integer = Optional(IntegerType, "type")
  boolean = Optional(BooleanType, "type")
  enumeration = Optional(EnumType, "type")


@message
class Expression(Message):
  """IR for an expression.

  An Expression is a potentially-recursive data structure.  It can either
  represent a leaf node (constant or reference) or an operation combining
  other Expressions (function).
  """

  constant = Optional(NumericConstant, "expression")
  constant_reference = Optional(Reference, "expression")
  function = Optional(Function, "expression")
  field_reference = Optional(FieldReference, "expression")
  boolean_constant = Optional(BooleanConstant, "expression")
  builtin_reference = Optional(Reference, "expression")

  type = Optional(ExpressionType)
  source_location = Optional(Location)


@message
class ArrayType(Message):
  """IR for an array type ("Int:8[12]" or "Message[2]" or "UInt[3][2]")."""
  base_type = Optional(lambda: Type)

  element_count = Optional(Expression, "size")
  automatic = Optional(Empty, "size")

  source_location = Optional(Location)


@message
class AtomicType(Message):
  """IR for a non-array type ("UInt" or "Foo(Version.SIX)")."""
  reference = Optional(Reference)
  runtime_parameter = Repeated(Expression)
  source_location = Optional(Location)


@message
class Type(Message):
  """IR for a type reference ("UInt", "Int:8[12]", etc.)."""
  atomic_type = Optional(AtomicType, "type")
  array_type = Optional(ArrayType, "type")

  size_in_bits = Optional(Expression)
  source_location = Optional(Location)


@message
class AttributeValue(Message):
  """IR for a attribute value."""
  # TODO(bolms): Make String a type of Expression, and replace
  # AttributeValue with Expression.
  expression = Optional(Expression, "value")
  string_constant = Optional(String, "value")

  source_location = Optional(Location)


@message
class Attribute(Message):
  """IR for a [name = value] attribute."""
  name = Optional(Word)
  value = Optional(AttributeValue)
  back_end = Optional(Word)
  is_default = Optional(bool)
  source_location = Optional(Location)


@message
class WriteTransform(Message):
  """IR which defines an expression-based virtual field write scheme.

  E.g., for a virtual field like `x_plus_one`:

    struct Foo:
     0 [+1]  UInt  x
     let x_plus_one = x + 1

  ... the `WriteMethod` would be `transform`, with `$logical_value - 1` for
  `function_body` and `x` for `destination`.
  """

  function_body = Optional(Expression)
  destination = Optional(FieldReference)


@message
class WriteMethod(Message):
  """IR which defines the method used for writing to a virtual field."""

  # A physical Field can be written directly.
  physical = Optional(bool, "method")

  # A read_only Field cannot be written.
  read_only = Optional(bool, "method")

  # An alias is a direct, untransformed forward of another field; it can be
  # implemented by directly returning a reference to the aliased field.
  #
  # Aliases are the only kind of virtual field that may have an opaque type.
  alias = Optional(FieldReference, "method")

  # A transform is a way of turning a logical value into a value which should
  # be written to another field: A virtual field like `let y = x + 1` would
  # have a transform WriteMethod to subtract 1 from the new `y` value, and
  # write that to `x`.
  transform = Optional(WriteTransform, "method")


@message
class FieldLocation(Message):
  """IR for a field location."""
  start = Optional(Expression)
  size = Optional(Expression)
  source_location = Optional(Location)


@message
class Field(Message):
  """IR for a field in a struct definition.

  There are two kinds of Field: physical fields have location and (physical)
  type; virtual fields have read_transform.  Although there are differences,
  in many situations physical and virtual fields are treated the same way,
  and they can be freely intermingled in the source file.
  """

  location = Optional(FieldLocation)  # The physical location of the field.
  type = Optional(Type)               # The physical type of the field.

  read_transform = Optional(Expression)  # The value of a virtual field.

  # How this virtual field should be written.
  write_method = Optional(WriteMethod)

  name = Optional(NameDefinition)  # The name of the field.
  abbreviation = Optional(Word)  # An optional short name for the field, only
                  # visible inside the enclosing bits/struct.
  attribute = Repeated(Attribute)          # Field-specific attributes.
  documentation = Repeated(Documentation)  # Field-specific documentation.

  # The field only exists when existence_condition evaluates to true.  For
  # example:
  #
  # struct Message:
  #   0 [+4]  UInt         length
  #   4 [+8]  MessageType  message_type
  #   if message_type == MessageType.FOO:
  #     8 [+length]  Foo   foo
  #   if message_type == MessageType.BAR:
  #     8 [+length]  Bar   bar
  #   8+length [+4]  UInt  crc
  #
  # For length, message_type, and crc, existence_condition will be
  # "boolean_constant { value: true }"
  #
  # For "foo", existence_condition will be:
  #     function { function: EQUALITY
  #                args: [reference to message_type]
  #                args: { [reference to MessageType.FOO] } }
  #
  # The "bar" field will have a similar existence_condition to "foo":
  #     function { function: EQUALITY
  #                args: [reference to message_type]
  #                args: { [reference to MessageType.BAR] } }
  #
  # When message_type is MessageType.BAR, the Message struct does not contain
  # field "foo", and vice versa for message_type == MessageType.FOO and field
  # "bar": those fields only conditionally exist in the structure.
  #
  # TODO(bolms): Document conditional fields better, and replace some of this
  # explanation with a reference to the documentation.
  existence_condition = Optional(Expression)
  source_location = Optional(Location)


@message
class Structure(Message):
  """IR for a bits or struct definition."""
  field = Repeated(Field)

  # The fields in `field` are listed in the order they appear in the original
  # .emb.
  #
  # For text format output, this can lead to poor results.  Take the following
  # struct:
  #
  #     struct Foo:
  #       b [+4]  UInt  a
  #       0 [+4]  UInt  b
  #
  # Here, the location of `a` depends on the current value of `b`.  Because of
  # this, if someone calls
  #
  #     emboss::UpdateFromText(foo_view, "{ a: 10, b: 4 }");
  #
  # then foo_view will not be updated the way one would expect: if `b`'s value
  # was something other than 4 to start with, then `UpdateFromText` will write
  # the 10 to some other location, then update `b` to 4.
  #
  # To avoid surprises, `emboss::DumpAsText` should return `"{ b: 4, a: 10
  # }"`.
  #
  # The `fields_in_dependency_order` field provides a permutation of `field`
  # such that each field appears after all of its dependencies.  For example,
  # `struct Foo`, above, would have `{ 1, 0 }` in
  # `fields_in_dependency_order`.
  #
  # The exact ordering of `fields_in_dependency_order` is not guaranteed, but
  # some effort is made to keep the order close to the order fields are listed
  # in the original `.emb` file.  In particular, if the ordering 0, 1, 2, 3,
  # ... satisfies dependency ordering, then `fields_in_dependency_order` will
  # be `{ 0, 1, 2, 3, ... }`.
  fields_in_dependency_order = Repeated(int)

  source_location = Optional(Location)


@message
class External(Message):
  """IR for an external type declaration."""
  # Externals have no values other than name and attribute list, which are
  # common to all type definitions.

  source_location = Optional(Location)


@message
class EnumValue(Message):
  """IR for a single value within an enumerated type."""
  name = Optional(NameDefinition)          # The name of the enum value.
  value = Optional(Expression)             # The value of the enum value.
  documentation = Repeated(Documentation)  # Value-specific documentation.

  source_location = Optional(Location)


@message
class Enum(Message):
  """IR for an enumerated type definition."""
  value = Repeated(EnumValue)
  source_location = Optional(Location)


@message
class Import(Message):
  """IR for an import statement in a module."""
  file_name = Optional(String)  # The file to import.
  local_name = Optional(Word)   # The name to use within this module.
  source_location = Optional(Location)


@message
class RuntimeParameter(Message):
  """IR for a runtime parameter definition."""
  name = Optional(NameDefinition)  # The name of the parameter.
  type = Optional(ExpressionType)  # The type of the parameter.

  # For convenience and readability, physical types may be used in the .emb
  # source instead of a full expression type.  That way, users can write
  # something like:
  #
  #     struct Foo(version :: UInt:8):
  #
  # instead of:
  #
  #     struct Foo(version :: {$int x |: 0 <= x <= 255}):
  #
  # In these cases, physical_type_alias holds the user-supplied type, and type
  # is filled in after initial parsing is finished.
  #
  # TODO(bolms): Actually implement the set builder type notation.
  physical_type_alias = Optional(Type)

  source_location = Optional(Location)


@message
class TypeDefinition(Message):
  """Container IR for a type definition (struct, union, etc.)"""

  # The "addressable unit" is the size of the smallest unit that can be read
  # from the backing store that this type expects.  For `struct`s, this is
  # BYTE; for `enum`s and `bits`, this is BIT, and for `external`s it depends
  # on the specific type.

  NONE = 0
  BIT = 1
  BYTE = 8

  external = Optional(External, "type")
  enumeration = Optional(Enum, "type")
  structure = Optional(Structure, "type")

  name = Optional(NameDefinition)  # The name of the type.
  attribute = Repeated(Attribute)  # All attributes attached to the type.
  documentation = Repeated(Documentation)     # Docs for the type.
  # pylint:disable=undefined-variable
  subtype = Repeated(lambda: TypeDefinition)  # Subtypes of this type.
  addressable_unit = Optional(
      int, decode_names=lambda x: getattr(TypeDefinition, x))

  # If the type requires parameters at runtime, these are its parameters.
  # These are currently only allowed on structures, but in the future they
  # should be allowed on externals.
  runtime_parameter = Repeated(RuntimeParameter)

  source_location = Optional(Location)


@message
class Module(Message):
  """The IR for an individual Emboss module (file)."""
  attribute = Repeated(Attribute)          # Module-level attributes.
  type = Repeated(TypeDefinition)          # Module-level type definitions.
  documentation = Repeated(Documentation)  # Module-level docs.
  foreign_import = Repeated(Import)        # Other modules imported.
  source_location = Optional(Location)    # Source code covered by this IR.
  source_file_name = Optional(_Text)    # Name of the source file.


@message
class EmbossIr(Message):
  """The top-level IR for an Emboss module and all of its dependencies."""
  # All modules.  The first entry will be the main module; back ends should
  # generate code corresponding to that module.  The second entry will be the
  # prelude module.
  module = Repeated(Module)


_initialize_deferred_specs()
